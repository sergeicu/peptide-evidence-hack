#!/usr/bin/env python3
"""Baseline claim-to-source: the dumbest thing that is not cheating.

For each gold claim it runs two PubMed counts - does any human-indexed record
exist, is any of it randomised - and picks a verdict from that alone. No LLM,
no reading, no judgement about whether a paper supports the claim.

    python tracks/2_claim_to_source/run.py --out out/baseline.jsonl
    python -m pephack.scoring.claims --submission out/baseline.jsonl --allow-unconfirmed

This exists so that on demo night nobody can claim a win without having beaten
counting. It will get some items right for the wrong reasons, which is exactly
the point: your agent has to beat a thing that never reads a paper.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pephack import pubmed  # noqa: E402
from pephack.scoring.claims import load_jsonl  # noqa: E402

REPO = Path(__file__).resolve().parents[2]


def baseline_verdict(compound: str) -> tuple[str, list[str]]:
    rct = pubmed.count(f"({compound}) AND Randomized Controlled Trial[Publication Type]")
    if rct:
        ids = pubmed.search(f"({compound}) AND Randomized Controlled Trial[Publication Type]", retmax=3)
        return "rct_supported", [f"PMID:{i}" for i in ids]
    human = pubmed.count(f"({compound}) AND Humans[Mesh]")
    if human:
        ids = pubmed.search(f"({compound}) AND Humans[Mesh]", retmax=3)
        return "human_uncontrolled", [f"PMID:{i}" for i in ids]
    animal = pubmed.count(f"({compound}) AND Animals[Mesh]")
    if animal:
        ids = pubmed.search(f"({compound}) AND Animals[Mesh]", retmax=3)
        return "animal_only", [f"PMID:{i}" for i in ids]
    return "no_evidence_found", []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=str(REPO / "data" / "gold" / "claims.jsonl"))
    ap.add_argument("--out", default="out/baseline.jsonl")
    args = ap.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w") as fh:
        for item in load_jsonl(args.gold):
            verdict, ids = baseline_verdict(item["compound"])
            fh.write(json.dumps({
                "id": item["id"],
                "verdict": verdict,
                "cited_ids": ids,
                "note": "counts-only baseline; never read a paper",
            }) + "\n")
            print(f"{item['id']:>5}  {item['compound']:<16} -> {verdict}")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
