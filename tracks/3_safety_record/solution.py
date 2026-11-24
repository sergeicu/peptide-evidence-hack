#!/usr/bin/env python3
"""Your safety agent. Fill in safety_profile()."""
from __future__ import annotations

import argparse
import json
from typing import Any

from pephack import openfda, pubmed
from pephack.compounds import by_name, load


def safety_profile(compound_name: str) -> dict[str, Any]:
    """What has actually been reported about this compound in humans.

    Build this out of, at minimum:
      - openfda.summarise(name): FAERS reports and whether an FDA label exists
      - pubmed case reports: pubmed.search(f"({q}) AND Case Reports[Publication Type]")
      - the approved analogue's label, where one exists, as the comparison
      - what is NOT known, stated explicitly

    Hard requirement for this track: every number you print carries its
    denominator or an explicit statement that there isn't one. A count with no
    denominator, next to a compound people inject, is the failure mode.
    """
    c = by_name(compound_name)
    faers = openfda.summarise(c.faers_name or c.name)
    case_ids = pubmed.search(f"({c.pubmed_query}) AND Case Reports[Publication Type]", retmax=50)

    return {
        "compound": c.name,
        "status_hypothesis": c.status_hypothesis,
        "faers": faers,
        "published_case_reports": [f"PMID:{i}" for i in case_ids],
        "n_case_reports": len(case_ids),
        "approved_analogue": None,          # TODO
        "analogue_label_adverse_effects": None,  # TODO
        "what_is_not_known": [],            # TODO: be specific and complete
        "denominator": "unknown - FAERS has no exposure denominator",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compound")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out")
    args = ap.parse_args()
    if not args.compound and not args.all:
        ap.error("pass --compound NAME or --all")

    names = [c.name for c in load()] if args.all else [args.compound]
    rows = {n: safety_profile(n) for n in names}
    text = json.dumps(rows, indent=2)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
