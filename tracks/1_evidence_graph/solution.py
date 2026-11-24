#!/usr/bin/env python3
"""Your evidence-graph agent. Fill in extract().

Everything in pephack is importable:
    from pephack import pubmed, europepmc, ctgov, openfda, opentargets, concentration
    from pephack.compounds import by_name, load
    from pephack.evidence_card import build, headline
"""
from __future__ import annotations

import argparse
import json
from typing import Any

from pephack import concentration, pubmed
from pephack.compounds import by_name
from pephack.evidence_card import build


def extract(paper: pubmed.Paper) -> dict[str, Any]:
    """Pull what MeSH does not carry out of one paper.

    The fields that matter, none of which exist in any structured field:
        species_detail   e.g. "Wistar rat" rather than just "animal"
        n_subjects       how many animals or people
        dose             with units, as reported
        route            oral, intraperitoneal, subcutaneous, topical...
        outcome          what they measured
        direction        positive / null / negative for the claimed effect

    You have paper.title, paper.abstract, paper.mesh, paper.publication_types.
    For full text, Europe PMC has it for open-access records.

    Score yourself: also predict species and design here, then compare against
    paper.classify(), which is ground truth from MeSH. That error rate is your
    only honest estimate of how wrong the fields above are.
    """
    mesh_truth = paper.classify()
    return {
        "pmid": paper.pmid,
        "species_detail": None,   # TODO
        "n_subjects": None,       # TODO
        "dose": None,             # TODO
        "route": None,            # TODO
        "outcome": None,          # TODO
        "direction": None,        # TODO
        "_mesh_ground_truth": mesh_truth,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compound", required=True)
    ap.add_argument("--max-papers", type=int, default=100)
    ap.add_argument("--out")
    args = ap.parse_args()

    c = by_name(args.compound)
    card = build(c, max_papers=args.max_papers)

    pmids = pubmed.search(c.pubmed_query, retmax=args.max_papers)
    papers = pubmed.fetch(pmids)
    card["extracted"] = [extract(p) for p in papers]

    filled = sum(1 for e in card["extracted"] if e["dose"] is not None)
    card["extraction_coverage"] = {
        "papers": len(papers),
        "with_dose": filled,
        "coverage": round(filled / len(papers), 3) if papers else 0.0,
    }
    card["concentration_verdict"] = concentration.verdict(card["concentration"])

    text = json.dumps(card, indent=2)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out}")
    else:
        print(text)


if __name__ == "__main__":
    main()
