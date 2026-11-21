"""Score a claim-to-source submission against the gold set.

Submission format: JSONL, one object per gold item.
    {"id": "c005",
     "verdict": "animal_only",
     "cited_ids": ["PMID:12345678", "NCT01234567"],
     "note": "optional free text"}

What gets measured, and why each one is here:

  accuracy            the number everyone quotes. On its own it is misleading
                      here, because no_evidence_found is the modal answer.
  macro_f1            the number to actually report: averages F1 over verdict
                      classes, so always answering no_evidence_found scores badly.
  majority_baseline   the best constant predictor: whichever single verdict,
                      answered every time, would have scored highest. Printed
                      next to your score. Beat it on macro F1.
  control_accuracy    accuracy restricted to approved / failed / investigational
                      compounds, where the right answer is knowable. A system
                      that fails here is broken regardless of its overall score.
  citation_format_ok  fraction of cited ids that are well-formed identifiers.
  unresolvable_rate   fraction that do not resolve against the live APIs.
                      This is your hallucinated-citation rate. Needs --resolve.
  citation_precision  of the ids you cited, how many are in the gold supporting
  citation_recall     set, and how much of that set you found. Only computed
                      over gold items that have supporting_ids filled in.

Usage:
    python -m pephack.scoring.claims --submission out/sub.jsonl
    python -m pephack.scoring.claims --submission out/sub.jsonl --resolve
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

VERDICTS = [
    "rct_supported",
    "human_uncontrolled",
    "animal_only",
    "contradicted",
    "no_evidence_found",
    "not_a_factual_claim",
]

CONTROL_GROUPS = {"approved", "approved_withdrawn", "approved_elsewhere",
                  "failed", "investigational", "research_only"}

ID_PATTERNS = {
    "pmid": re.compile(r"^PMID:\d{1,9}$", re.I),
    "pmcid": re.compile(r"^PMC\d{4,9}$", re.I),
    "nct": re.compile(r"^NCT\d{8}$", re.I),
    "doi": re.compile(r"^(DOI:)?10\.\d{4,9}/\S+$", re.I),
    "url": re.compile(r"^https?://\S+$", re.I),
}


def load_jsonl(path: str | Path) -> list[dict[str, Any]]:
    rows = []
    with open(path) as fh:
        for i, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{i}: bad JSON: {exc}")
    return rows


def id_kind(identifier: str) -> str | None:
    for kind, pattern in ID_PATTERNS.items():
        if pattern.match(identifier.strip()):
            return kind
    return None


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1


def macro_f1(pairs: list[tuple[str, str]]) -> tuple[float, dict[str, Any]]:
    """pairs: list of (gold, predicted). Returns macro F1 over classes present in gold."""
    classes = sorted({g for g, _ in pairs})
    per_class: dict[str, Any] = {}
    f1s = []
    for cls in classes:
        tp = sum(1 for g, p in pairs if g == cls and p == cls)
        fp = sum(1 for g, p in pairs if g != cls and p == cls)
        fn = sum(1 for g, p in pairs if g == cls and p != cls)
        precision, recall, f1 = _prf(tp, fp, fn)
        per_class[cls] = {"n": sum(1 for g, _ in pairs if g == cls),
                          "precision": round(precision, 3),
                          "recall": round(recall, 3),
                          "f1": round(f1, 3)}
        f1s.append(f1)
    return (sum(f1s) / len(f1s) if f1s else 0.0), per_class


def resolve_id(identifier: str) -> bool:
    """Does this identifier point at something real? Needs network."""
    from .. import ctgov, pubmed
    from ..http import ApiError

    kind = id_kind(identifier)
    try:
        if kind == "pmid":
            num = identifier.split(":", 1)[1]
            return pubmed.count(f"{num}[uid]") > 0
        if kind == "nct":
            study = ctgov.study(identifier.upper())
            return bool(study)
        if kind in {"doi", "pmcid", "url"}:
            # Treat as unverified rather than claiming it resolves.
            return True
    except (ApiError, Exception):
        return False
    return False


def score(gold: list[dict[str, Any]], submission: list[dict[str, Any]],
          *, resolve: bool = False, allow_unconfirmed: bool = False) -> dict[str, Any]:
    gold_by_id = {g["id"]: g for g in gold}
    sub_by_id = {s["id"]: s for s in submission if "id" in s}

    unconfirmed = [g["id"] for g in gold if not g.get("confirmed_by")]
    if unconfirmed and not allow_unconfirmed:
        raise SystemExit(
            f"{len(unconfirmed)} of {len(gold)} gold items have no confirmed_by.\n"
            "The seed labels shipped with this repo are a starting point written by "
            "whoever built the pack, not ground truth. Somebody in the room has to "
            "check each one against the primary documents and put their name in "
            "confirmed_by before a score means anything.\n"
            "Pass --allow-unconfirmed to score anyway, and say so when you demo."
        )

    missing = [gid for gid in gold_by_id if gid not in sub_by_id]
    extra = [sid for sid in sub_by_id if sid not in gold_by_id]

    pairs: list[tuple[str, str]] = []
    by_group: dict[str, list[tuple[str, str]]] = defaultdict(list)
    bad_verdicts: list[str] = []
    confusion: Counter[tuple[str, str]] = Counter()

    cited_total = cited_format_ok = 0
    unresolvable: list[str] = []
    cit_tp = cit_fp = cit_fn = 0
    citation_scored_items = 0

    for gid, g in gold_by_id.items():
        s = sub_by_id.get(gid)
        predicted = (s or {}).get("verdict", "__missing__")
        if predicted not in VERDICTS and predicted != "__missing__":
            bad_verdicts.append(f"{gid}: {predicted!r}")
        pairs.append((g["verdict"], predicted))
        by_group[g.get("status_group", "unknown")].append((g["verdict"], predicted))
        confusion[(g["verdict"], predicted)] += 1

        cited = [str(x) for x in (s or {}).get("cited_ids", [])]
        for identifier in cited:
            cited_total += 1
            if id_kind(identifier):
                cited_format_ok += 1
            if resolve and not resolve_id(identifier):
                unresolvable.append(f"{gid}:{identifier}")

        gold_support = {x.upper() for x in g.get("supporting_ids", []) if x}
        if gold_support:
            citation_scored_items += 1
            pred_support = {x.upper() for x in cited}
            cit_tp += len(gold_support & pred_support)
            cit_fp += len(pred_support - gold_support)
            cit_fn += len(gold_support - pred_support)

    n = len(pairs)
    accuracy = sum(1 for g, p in pairs if g == p) / n if n else 0.0
    macro, per_class = macro_f1(pairs)

    # The honest baseline is the BEST constant predictor, not an arbitrary tie-break:
    # whichever single verdict, answered every time, would have scored highest.
    majority, baseline_acc, baseline_macro = "", 0.0, 0.0
    for candidate in sorted({g for g, _ in pairs}):
        cand_pairs = [(g, candidate) for g, _ in pairs]
        acc = sum(1 for g, p in cand_pairs if g == p) / n if n else 0.0
        mac, _ = macro_f1(cand_pairs)
        if (mac, acc) > (baseline_macro, baseline_acc):
            majority, baseline_acc, baseline_macro = candidate, acc, mac

    control_pairs = [pair for grp, prs in by_group.items() if grp in CONTROL_GROUPS for pair in prs]
    control_acc = (sum(1 for g, p in control_pairs if g == p) / len(control_pairs)
                   if control_pairs else None)

    cit_p, cit_r, cit_f = _prf(cit_tp, cit_fp, cit_fn)

    return {
        "n_gold": len(gold),
        "n_scored": n,
        "missing_from_submission": missing,
        "ids_not_in_gold": extra,
        "invalid_verdicts": bad_verdicts,
        "gold_items_unconfirmed": len(unconfirmed),
        "accuracy": round(accuracy, 3),
        "macro_f1": round(macro, 3),
        "per_class": per_class,
        "per_status_group": {
            grp: {"n": len(prs),
                  "accuracy": round(sum(1 for g, p in prs if g == p) / len(prs), 3)}
            for grp, prs in sorted(by_group.items())
        },
        "control_accuracy": None if control_acc is None else round(control_acc, 3),
        "majority_baseline": {
            "always_answers": majority,
            "accuracy": round(baseline_acc, 3),
            "macro_f1": round(baseline_macro, 3),
        },
        "beats_baseline_on_macro_f1": macro > baseline_macro,
        "citations": {
            "cited_total": cited_total,
            "format_ok_rate": round(cited_format_ok / cited_total, 3) if cited_total else None,
            "resolved": resolve,
            "unresolvable_rate": (round(len(unresolvable) / cited_total, 3)
                                  if resolve and cited_total else None),
            "unresolvable_examples": unresolvable[:10],
            "scored_against_gold_items": citation_scored_items,
            "precision": round(cit_p, 3) if citation_scored_items else None,
            "recall": round(cit_r, 3) if citation_scored_items else None,
            "f1": round(cit_f, 3) if citation_scored_items else None,
        },
        "confusion": {f"{g} -> {p}": c for (g, p), c in sorted(confusion.items(), key=lambda kv: -kv[1])},
    }


def report(result: dict[str, Any]) -> str:
    lines = [
        "=" * 64,
        f"scored {result['n_scored']} items   "
        f"accuracy {result['accuracy']:.3f}   macro F1 {result['macro_f1']:.3f}",
        f"baseline (always '{result['majority_baseline']['always_answers']}')   "
        f"accuracy {result['majority_baseline']['accuracy']:.3f}   "
        f"macro F1 {result['majority_baseline']['macro_f1']:.3f}",
        f"beats baseline on macro F1: {result['beats_baseline_on_macro_f1']}",
    ]
    if result["control_accuracy"] is not None:
        lines.append(f"control accuracy (knowable answers): {result['control_accuracy']:.3f}")
    cit = result["citations"]
    if cit["cited_total"]:
        line = f"citations: {cit['cited_total']} cited, format ok {cit['format_ok_rate']:.3f}"
        if cit["unresolvable_rate"] is not None:
            line += f", unresolvable {cit['unresolvable_rate']:.3f}"
        lines.append(line)
    else:
        lines.append("citations: none submitted - a verdict with no document is not an answer")
    if result["missing_from_submission"]:
        lines.append(f"MISSING {len(result['missing_from_submission'])} gold items: "
                     f"{result['missing_from_submission'][:5]}")
    if result["invalid_verdicts"]:
        lines.append(f"INVALID verdicts: {result['invalid_verdicts'][:5]}")
    if result["gold_items_unconfirmed"]:
        lines.append(f"WARNING: {result['gold_items_unconfirmed']} gold labels are unconfirmed")
    lines.append("=" * 64)
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--submission", required=True)
    ap.add_argument("--gold", default=str(Path(__file__).resolve().parents[2] / "data" / "gold" / "claims.jsonl"))
    ap.add_argument("--resolve", action="store_true", help="check cited ids against the live APIs")
    ap.add_argument("--allow-unconfirmed", action="store_true")
    ap.add_argument("--json", help="write the full result here")
    args = ap.parse_args()

    result = score(load_jsonl(args.gold), load_jsonl(args.submission),
                   resolve=args.resolve, allow_unconfirmed=args.allow_unconfirmed)
    print(report(result))
    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json).write_text(json.dumps(result, indent=2))
        print(f"wrote {args.json}")


if __name__ == "__main__":
    main()
