"""openFDA: adverse event reports (FAERS), drug labels, recalls.

Read this before you build on it, or your card will be wrong:

FAERS is a spontaneous reporting system. A report is not proof the drug caused
the event, reporting is voluntary, and the same case can appear twice. Counts
are not rates - you cannot divide by anything, because nobody knows the
denominator.

For compounds that were never approved, expect very few reports. That absence
is not safety. It means the reporting pathway barely exists for a compound
people buy from a website. Say so on the card instead of printing a zero.

Docs: https://open.fda.gov/apis/
Limits: 240 requests/min and 1000/day without a key; set OPENFDA_API_KEY to raise it.
"""
from __future__ import annotations

import os
from typing import Any

from .http import get

BASE = "https://api.fda.gov"


def _key() -> dict[str, str]:
    k = os.environ.get("OPENFDA_API_KEY", "")
    return {"api_key": k} if k else {}


def events(drug: str, limit: int = 100, skip: int = 0) -> dict[str, Any]:
    """Raw FAERS reports mentioning a drug name."""
    return get(
        f"{BASE}/drug/event.json",
        params={"search": f'patient.drug.medicinalproduct:"{drug}"',
                "limit": min(limit, 1000), "skip": skip, **_key()},
        fixture="openfda_event.json",
    )


def event_count(drug: str, field: str = "patient.reaction.reactionmeddrapt.exact",
                limit: int = 50) -> list[dict[str, Any]]:
    """Top reported reactions for a drug. Returns [{term, count}, ...]."""
    data = get(
        f"{BASE}/drug/event.json",
        params={"search": f'patient.drug.medicinalproduct:"{drug}"',
                "count": field, "limit": limit, **_key()},
        fixture="openfda_count.json",
    )
    return list(data.get("results", []))


def total_reports(drug: str) -> int:
    """How many FAERS reports mention this drug name at all."""
    try:
        data = events(drug, limit=1)
    except Exception:
        return 0
    return int(data.get("meta", {}).get("results", {}).get("total", 0))


def labels(drug: str, limit: int = 10) -> list[dict[str, Any]]:
    """Approved drug labels. An empty result is itself informative: no label
    means no FDA-approved product under that name."""
    try:
        data = get(
            f"{BASE}/drug/label.json",
            params={"search": f'openfda.generic_name:"{drug}" OR openfda.brand_name:"{drug}"',
                    "limit": limit, **_key()},
            fixture="openfda_label.json",
        )
    except Exception:
        return []
    return list(data.get("results", []))


def summarise(drug: str) -> dict[str, Any]:
    """The safety block for an evidence card, with the caveats attached."""
    n = total_reports(drug)
    reactions = event_count(drug) if n else []
    has_label = bool(labels(drug))
    return {
        "drug_queried": drug,
        "faers_reports": n,
        "top_reactions": reactions[:15],
        "has_fda_label": has_label,
        "interpretation_notes": [
            "FAERS counts are reports, not confirmed causal events.",
            "Counts are not rates: the exposed population is unknown.",
            "Few or zero reports for an unapproved compound reflects a missing "
            "reporting pathway, not demonstrated safety.",
        ],
    }
