"""Assemble an evidence card for one compound.

This is a baseline, not a target. It makes about ten API calls and produces a
card with no LLM involved at all. Your agent has to beat it, and "beat it"
means adding things it cannot do: dose, route, sample size, what the paper
actually concluded, whether the cited study even supports the claim.

Run it first so you know what free looks like:
    python tracks/1_evidence_graph/run.py --compound BPC-157
"""
from __future__ import annotations

import datetime as _dt
from typing import Any

from . import concentration, ctgov, openfda, pubmed
from .compounds import Compound, by_name


def build(compound: str | Compound, *, max_papers: int = 300,
          fetch_full: bool = True) -> dict[str, Any]:
    c = by_name(compound) if isinstance(compound, str) else compound

    counts = pubmed.species_breakdown(c.pubmed_query)

    papers: list[pubmed.Paper] = []
    conc: dict[str, Any] = {"n_papers": 0, "note": "not fetched"}
    design_mix: dict[str, int] = {}
    years: list[int] = []
    if fetch_full:
        pmids = pubmed.search(c.pubmed_query, retmax=max_papers)
        papers = pubmed.fetch(pmids)
        conc = concentration.author_concentration(papers)
        for p in papers:
            cls = p.classify()
            design_mix[cls["design"]] = design_mix.get(cls["design"], 0) + 1
            if p.year:
                years.append(p.year)

    trials = ctgov.search(c.name)
    trial_summary = ctgov.summarise(trials)
    safety = openfda.summarise(c.faers_name or c.name)

    human_n = counts.get("human", 0)
    animal_n = counts.get("animal", 0)
    ratio = round(animal_n / human_n, 1) if human_n else None

    return {
        "compound": c.name,
        "aliases": c.aliases,
        "status_hypothesis": c.status_hypothesis,
        "status_hypothesis_warning": (
            "Unverified. Check against the FDA record and cite the document."
        ),
        "common_claim": c.common_claim,
        "generated_utc": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        "literature": {
            **counts,
            "animal_to_human_ratio": ratio,
            "earliest_year": min(years) if years else None,
            "latest_year": max(years) if years else None,
            "design_mix": dict(sorted(design_mix.items(), key=lambda kv: -kv[1])),
            "papers_analysed": len(papers),
        },
        "concentration": conc,
        "concentration_verdict": concentration.verdict(conc),
        "trials": trial_summary,
        "safety": safety,
        "sources": {
            "pubmed_query": c.pubmed_query,
            "ctgov_query": c.name,
            "faers_query": c.faers_name or c.name,
        },
        "known_gaps": [
            "No dose, route or sample size extraction - that is the agent's job.",
            "No check that any paper supports the common_claim.",
            "Non-English literature is undercounted by PubMed queries in English.",
            "Registered trials are not results; see trials.with_posted_results.",
        ],
    }


def headline(card: dict[str, Any]) -> str:
    """One line a human can read out at demo time."""
    lit = card["literature"]
    t = card["trials"]
    return (
        f"{card['compound']}: {lit['total']} records "
        f"({lit['human']} human, {lit['animal']} animal"
        + (f", {lit['animal_to_human_ratio']}:1" if lit["animal_to_human_ratio"] else "")
        + f"), {lit['randomized']} randomised trials in PubMed, "
        f"{t['registered']} registered studies of which {t['with_posted_results']} "
        f"have posted results. {card['concentration_verdict']}."
    )
