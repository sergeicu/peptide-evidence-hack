"""Open Targets Platform: does a claimed target have human evidence behind it.

This is the bridge from "a forum says peptide X works via target Y" to
"is there any human genetic support that Y matters in that disease".

Open Targets aggregates evidence per target-disease pair and splits it by
datatype: genetic_association, somatic_mutation, known_drug, literature,
animal_model, rna_expression. The datatype is the useful part. A score driven
by animal_model and literature is a different claim from one driven by
genetic_association, and that distinction is the whole point of the mechanism
track.

Free GraphQL API, no key. Docs: https://platform-docs.opentargets.org/
"""
from __future__ import annotations

from typing import Any

import requests

from .http import offline, FIXTURE_DIR, ApiError
import json

API = "https://api.platform.opentargets.org/api/v4/graphql"

SEARCH_TARGET = """
query SearchTarget($q: String!) {
  search(queryString: $q, entityNames: ["target"], page: {index: 0, size: 5}) {
    hits { id name entity description }
  }
}
"""

TARGET_DISEASES = """
query TargetAssoc($ensemblId: String!, $size: Int!) {
  target(ensemblId: $ensemblId) {
    id
    approvedSymbol
    biotype
    associatedDiseases(page: {index: 0, size: $size}) {
      count
      rows {
        score
        disease { id name }
        datatypeScores { id score }
      }
    }
  }
}
"""


def query(gql: str, variables: dict[str, Any], *, fixture: str) -> dict[str, Any]:
    if offline():
        path = FIXTURE_DIR / fixture
        if not path.exists():
            raise ApiError(f"offline fixture missing: {path}")
        return json.loads(path.read_text())
    resp = requests.post(API, json={"query": gql, "variables": variables}, timeout=40)
    if not resp.ok:
        raise ApiError(f"{resp.status_code} from Open Targets: {resp.text[:300]}")
    payload = resp.json()
    if "errors" in payload:
        raise ApiError(f"Open Targets GraphQL errors: {payload['errors']}")
    return payload["data"]


def find_target(symbol: str) -> list[dict[str, Any]]:
    """Resolve a gene symbol or name to Ensembl ids."""
    data = query(SEARCH_TARGET, {"q": symbol}, fixture="opentargets_search.json")
    return data.get("search", {}).get("hits", [])


def target_diseases(ensembl_id: str, size: int = 25) -> dict[str, Any]:
    data = query(TARGET_DISEASES, {"ensemblId": ensembl_id, "size": size},
                 fixture="opentargets_target.json")
    return data.get("target") or {}


def human_genetic_support(symbol: str, disease_substring: str = "") -> dict[str, Any]:
    """Is there human genetic evidence linking this target to a disease?

    Returns the association rows whose evidence includes a non-zero
    genetic_association datatype score, which is the closest thing in public
    data to "this matters in humans, not just in a dish".
    """
    hits = find_target(symbol)
    if not hits:
        return {"symbol": symbol, "resolved": False, "rows": []}

    target = target_diseases(hits[0]["id"])
    rows = []
    for row in target.get("associatedDiseases", {}).get("rows", []):
        name = row.get("disease", {}).get("name", "")
        if disease_substring and disease_substring.lower() not in name.lower():
            continue
        by_type = {d["id"]: d["score"] for d in row.get("datatypeScores", [])}
        rows.append({
            "disease": name,
            "overall_score": row.get("score"),
            "genetic_association": by_type.get("genetic_association", 0.0),
            "animal_model": by_type.get("animal_model", 0.0),
            "literature": by_type.get("literature", 0.0),
            "known_drug": by_type.get("known_drug", 0.0),
            "driven_by": max(by_type, key=by_type.get) if by_type else None,
        })
    rows.sort(key=lambda r: r["genetic_association"], reverse=True)
    return {
        "symbol": symbol,
        "resolved": True,
        "ensembl_id": hits[0]["id"],
        "rows": rows,
        "any_genetic_support": any(r["genetic_association"] > 0 for r in rows),
    }
