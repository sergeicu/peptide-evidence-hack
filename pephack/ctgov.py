"""ClinicalTrials.gov API v2.

Registration is not evidence. A compound can have a dozen registered studies
and no published results, and that gap is one of the most useful things you can
show on a card: registered vs completed vs results-posted.

Docs: https://clinicaltrials.gov/data-api/api
"""
from __future__ import annotations

from typing import Any

from .http import get

BASE = "https://clinicaltrials.gov/api/v2"

# The fields worth pulling for an evidence card. Add more as you need them.
DEFAULT_FIELDS = [
    "NCTId", "BriefTitle", "OverallStatus", "Phase", "StudyType",
    "EnrollmentCount", "EnrollmentType", "StartDate", "CompletionDate",
    "PrimaryCompletionDate", "LeadSponsorName", "LocationCountry",
    "HasResults", "InterventionName", "Condition",
]


def search(term: str, *, fields: list[str] | None = None, page_size: int = 100,
           status: list[str] | None = None, max_results: int = 1000) -> list[dict[str, Any]]:
    """Search studies by free text term.

    status: optional list of overall-status values, e.g.
      ["COMPLETED", "TERMINATED", "WITHDRAWN", "RECRUITING", "UNKNOWN"]
    """
    out: list[dict[str, Any]] = []
    token: str | None = None
    while len(out) < max_results:
        params: dict[str, Any] = {
            "query.term": term,
            "fields": ",".join(fields or DEFAULT_FIELDS),
            "pageSize": min(page_size, 1000),
            "countTotal": "true",
            "format": "json",
        }
        if status:
            params["filter.overallStatus"] = "|".join(status)
        if token:
            params["pageToken"] = token
        data = get(f"{BASE}/studies", params=params, fixture="ctgov_studies.json")
        batch = data.get("studies", [])
        out.extend(batch)
        token = data.get("nextPageToken")
        if not batch or not token:
            break
    return out[:max_results]


def study(nct_id: str) -> dict[str, Any]:
    """One study by NCT id. Use this to check that a cited NCT id is real."""
    return get(f"{BASE}/studies/{nct_id}", params={"format": "json"},
               fixture="ctgov_study.json")


def summarise(studies: list[dict[str, Any]]) -> dict[str, Any]:
    """Collapse a study list into the numbers a card needs."""
    def dig(s: dict[str, Any], *path: str) -> Any:
        node: Any = s
        for key in path:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    statuses: dict[str, int] = {}
    with_results = 0
    enrolled = 0
    for s in studies:
        status = dig(s, "protocolSection", "statusModule", "overallStatus") or "UNKNOWN"
        statuses[status] = statuses.get(status, 0) + 1
        if dig(s, "hasResults"):
            with_results += 1
        n = dig(s, "protocolSection", "designModule", "enrollmentInfo", "count")
        if isinstance(n, int):
            enrolled += n

    return {
        "registered": len(studies),
        "by_status": statuses,
        "completed": statuses.get("COMPLETED", 0),
        "with_posted_results": with_results,
        "total_enrollment_registered": enrolled,
    }
