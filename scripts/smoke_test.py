#!/usr/bin/env python3
"""Hit every API once and say which ones work from where you are sitting.

Run this FIRST THING on hack day, before you write anything:

    make smoke

Everything in this repo was written against the documented API shapes but could
not be executed from the machine that built it, because outbound access to
these hosts was blocked there. So this script is the real integration test. If
something here fails, fix the client before you build on it, and send a PR.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CHECKS = []


def check(name):
    def wrap(fn):
        CHECKS.append((name, fn))
        return fn
    return wrap


@check("PubMed esearch (count)")
def _pubmed_count():
    from pephack import pubmed
    n = pubmed.count("BPC-157")
    assert n > 0, "expected a non-zero count for BPC-157"
    return f"{n} records"


@check("PubMed efetch + MeSH classification")
def _pubmed_fetch():
    from pephack import pubmed
    ids = pubmed.search("BPC-157 AND Animals[Mesh]", retmax=3)
    papers = pubmed.fetch(ids)
    assert papers, "no papers parsed"
    classes = [p.classify()["species"] for p in papers]
    return f"{len(papers)} papers, species={classes}"


@check("PubMed species breakdown")
def _pubmed_breakdown():
    from pephack import pubmed
    b = pubmed.species_breakdown("BPC-157")
    return ", ".join(f"{k}={v}" for k, v in b.items())


@check("Europe PMC search")
def _epmc():
    from pephack import europepmc
    n = europepmc.hit_count("BPC-157")
    return f"{n} hits"


@check("Europe PMC citations")
def _epmc_cit():
    from pephack import europepmc
    rows = europepmc.citations("22300085")
    return f"{len(rows)} citing records"


@check("ClinicalTrials.gov v2 search")
def _ctgov():
    from pephack import ctgov
    studies = ctgov.search("semaglutide", max_results=20)
    assert studies, "expected registered studies for semaglutide"
    return f"{len(studies)} studies; summary={ctgov.summarise(studies)}"


@check("openFDA FAERS")
def _faers():
    from pephack import openfda
    n = openfda.total_reports("SEMAGLUTIDE")
    return f"{n} reports for semaglutide"


@check("openFDA label")
def _label():
    from pephack import openfda
    rows = openfda.labels("semaglutide")
    return f"{len(rows)} labels"


@check("Open Targets GraphQL")
def _ot():
    from pephack import opentargets
    res = opentargets.human_genetic_support("GLP1R")
    return f"resolved={res['resolved']}, genetic_support={res.get('any_genetic_support')}"


@check("Scorers import and run offline")
def _scorers():
    from pephack.scoring import prediction
    seqs = ["ACDEFGHIKL", "KKKRRRLLLA", "GGGGSSSSAA", "WWYYFFAACC"] * 10
    labels = [0, 1, 0, 1] * 10
    res = prediction.evaluate(seqs[:30], labels[:30], seqs[30:], labels[30:])
    return f"shortcut probe AUC {res['baselines']['shortcut_probe']}"


def main() -> int:
    failures = 0
    print("=" * 70)
    for name, fn in CHECKS:
        try:
            detail = fn()
            print(f"PASS  {name}\n        {detail}")
        except Exception as exc:
            failures += 1
            print(f"FAIL  {name}\n        {type(exc).__name__}: {exc}")
    print("=" * 70)
    print(f"{len(CHECKS) - failures}/{len(CHECKS)} passed")
    if failures:
        print("\nA failure here is a bug in this repo, not in your code. Fix it and PR it;\n"
              "everyone else in the room is about to hit the same thing.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
