"""Europe PMC: full text where it exists, plus citations and references.

Why this as well as PubMed: Europe PMC gives you the citation and reference
edges, which is what you need to find out whether a body of literature is one
lab citing itself. It also carries preprints and some full text.

Docs: https://europepmc.org/RestfulWebService
"""
from __future__ import annotations

from typing import Any, Iterator

from .http import get

BASE = "https://www.ebi.ac.uk/europepmc/webservices/rest"


def search(query: str, page_size: int = 100, result_type: str = "core",
           max_results: int = 1000) -> list[dict[str, Any]]:
    """Search Europe PMC. result_type: 'idlist' | 'lite' | 'core'.

    'core' includes the abstract, full author list with affiliations, MeSH and
    grant data. Use 'lite' if you only need titles and ids.
    """
    results: list[dict[str, Any]] = []
    cursor = "*"
    while len(results) < max_results:
        data = get(
            f"{BASE}/search",
            params={"query": query, "format": "json", "resultType": result_type,
                    "pageSize": min(page_size, 1000), "cursorMark": cursor},
            fixture="europepmc_search.json",
        )
        batch = data.get("resultList", {}).get("result", [])
        results.extend(batch)
        next_cursor = data.get("nextCursorMark")
        if not batch or not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
    return results[:max_results]


def hit_count(query: str) -> int:
    data = get(
        f"{BASE}/search",
        params={"query": query, "format": "json", "resultType": "idlist", "pageSize": 1},
        fixture="europepmc_search.json",
    )
    return int(data.get("hitCount", 0))


def _linked(source: str, ext_id: str, kind: str, page_size: int = 1000) -> list[dict[str, Any]]:
    data = get(
        f"{BASE}/{source}/{ext_id}/{kind}",
        params={"format": "json", "pageSize": page_size},
        fixture=f"europepmc_{kind}.json",
    )
    container = f"{kind[:-1]}List" if kind.endswith("s") else f"{kind}List"
    block = data.get(container, {})
    for key in ("reference", "citation"):
        if key in block:
            return block[key]
    return []


def references(pmid: str, source: str = "MED") -> list[dict[str, Any]]:
    """What this paper cites."""
    return _linked(source, pmid, "references")


def citations(pmid: str, source: str = "MED") -> list[dict[str, Any]]:
    """What cites this paper."""
    return _linked(source, pmid, "citations")


def iter_authors(record: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """Yield (full_name, affiliation) from a 'core' result."""
    for a in record.get("authorList", {}).get("author", []):
        name = a.get("fullName") or " ".join(
            x for x in (a.get("lastName"), a.get("initials")) if x
        )
        aff = a.get("authorAffiliationDetailsList", {}).get("authorAffiliation", [{}])
        aff_text = aff[0].get("affiliation", "") if aff else ""
        yield name, aff_text
