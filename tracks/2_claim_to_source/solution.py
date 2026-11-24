#!/usr/bin/env python3
"""Your claim-to-source agent. Fill in resolve_claim()."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from pephack import ctgov, europepmc, pubmed
from pephack.scoring.claims import VERDICTS, load_jsonl


def resolve_claim(claim: dict[str, Any]) -> dict[str, Any]:
    """Return a verdict and the documents behind it.

    claim has: id, compound, claim, claim_source, status_group.

    Return: {"verdict": one of VERDICTS, "cited_ids": [...], "note": "..."}

    Things worth doing that the baseline does not:
      - read the claim, not just the compound name. "heals tendons in humans"
        and "is safe in humans" need different searches.
      - check that a cited paper is about the claim, not merely about the
        compound.
      - check what a cited study actually measured and in what species.
      - say not_a_factual_claim when the claim names no outcome or population.
      - search non-English sources before concluding nothing exists.
      - cite ClinicalTrials.gov registrations as registrations, not results:
        ctgov.summarise() separates registered from results-posted.
    """
    raise NotImplementedError("your agent goes here")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default="data/gold/claims.jsonl",
                    help="path to the gold set (clone the core repo, or point at your own)")
    ap.add_argument("--out", default="out/mine.jsonl")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for item in load_jsonl(args.gold):
            try:
                answer = resolve_claim(item)
            except NotImplementedError:
                raise SystemExit("implement resolve_claim() in solution.py")
            except Exception as exc:
                answer = {"verdict": "no_evidence_found", "cited_ids": [],
                          "note": f"agent error: {type(exc).__name__}: {exc}"}
            assert answer["verdict"] in VERDICTS, answer["verdict"]
            fh.write(json.dumps({"id": item["id"], **answer}) + "\n")
            print(f"{item['id']:>5}  {item['compound']:<16} -> {answer['verdict']}")
    print(f"\nwrote {out}\nnow: python -m pephack.scoring.claims --submission {out} --resolve")


if __name__ == "__main__":
    main()
