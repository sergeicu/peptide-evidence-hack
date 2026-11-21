#!/usr/bin/env python3
"""Baseline evidence card. No LLM. About ten API calls.

    python tracks/1_evidence_graph/run.py --compound BPC-157
    python tracks/1_evidence_graph/run.py --all --out out/

Beat this by adding what it cannot do: dose, route, sample size, and whether
any paper actually supports the claim.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pephack import compounds, evidence_card  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compound")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default="out")
    ap.add_argument("--max-papers", type=int, default=300)
    ap.add_argument("--counts-only", action="store_true",
                    help="skip full record fetch: 6 requests per compound instead of many")
    args = ap.parse_args()

    if not args.compound and not args.all:
        ap.error("pass --compound NAME or --all")

    targets = compounds.load() if args.all else [compounds.by_name(args.compound)]
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    for c in targets:
        try:
            card = evidence_card.build(c, max_papers=args.max_papers,
                                       fetch_full=not args.counts_only)
        except Exception as exc:
            print(f"{c.name}: FAILED {type(exc).__name__}: {exc}", file=sys.stderr)
            continue
        path = out_dir / f"{c.name.lower().replace(' ', '_')}.json"
        path.write_text(json.dumps(card, indent=2))
        print(evidence_card.headline(card))
        print(f"  -> {path}")


if __name__ == "__main__":
    main()
