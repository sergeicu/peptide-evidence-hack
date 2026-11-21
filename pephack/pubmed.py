"""PubMed via NCBI E-utilities.

The single most useful thing in this file is classify(): PubMed already tells
you whether a paper is about humans or rats, and whether it is a randomised
trial or a case report, through MeSH headings and publication types. You do not
need an LLM for that, and an LLM will be worse at it.

Use MeSH for species and study design. Use an LLM for the things MeSH does not
carry: dose, route, sample size, what the paper actually concluded. Then score
your LLM extraction against MeSH on the fields where both exist - that is a
free accuracy check on your own pipeline.

Docs: https://www.ncbi.nlm.nih.gov/books/NBK25501/
An API key (free, from an NCBI account) raises you from 3 to 10 requests/sec.
Set NCBI_API_KEY and it is used automatically.
"""
from __future__ import annotations

import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from typing import Any

from .http import get

BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# MeSH headings that settle the species question.
HUMAN_MESH = {"Humans"}
ANIMAL_MESH = {
    "Animals", "Rats", "Mice", "Rabbits", "Dogs", "Swine", "Cats",
    "Rats, Wistar", "Rats, Sprague-Dawley", "Mice, Inbred C57BL",
    "Zebrafish", "Guinea Pigs", "Macaca mulatta", "Chickens",
}
# Publication types that settle the design question, strongest first.
DESIGN_ORDER = [
    "Meta-Analysis",
    "Systematic Review",
    "Randomized Controlled Trial",
    "Controlled Clinical Trial",
    "Clinical Trial, Phase III",
    "Clinical Trial, Phase II",
    "Clinical Trial, Phase I",
    "Clinical Trial",
    "Observational Study",
    "Case Reports",
    "Review",
    "Comparative Study",
    "Journal Article",
]


@dataclass
class Paper:
    pmid: str
    title: str = ""
    journal: str = ""
    year: int | None = None
    doi: str = ""
    abstract: str = ""
    authors: list[str] = field(default_factory=list)
    affiliations: list[str] = field(default_factory=list)
    mesh: list[str] = field(default_factory=list)
    publication_types: list[str] = field(default_factory=list)

    @property
    def first_author(self) -> str:
        return self.authors[0] if self.authors else ""

    @property
    def last_author(self) -> str:
        return self.authors[-1] if self.authors else ""

    def classify(self) -> dict[str, Any]:
        """Species and design from MeSH. Returns 'unknown' rather than guessing.

        in_humans is True only when the Humans heading is present. Papers with
        both Humans and Animals are tagged 'both' - usually a human cell line
        plus an animal model, and worth a human look.
        """
        mesh = set(self.mesh)
        human = bool(mesh & HUMAN_MESH)
        animal = bool(mesh & ANIMAL_MESH)
        if human and animal:
            species = "both"
        elif human:
            species = "human"
        elif animal:
            species = "animal"
        else:
            species = "unknown"

        design = "unknown"
        for candidate in DESIGN_ORDER:
            if candidate in self.publication_types:
                design = candidate
                break

        return {
            "pmid": self.pmid,
            "species": species,
            "in_humans": human,
            "design": design,
            "is_trial": any("Trial" in p for p in self.publication_types),
            "indexed_with_mesh": bool(self.mesh),
        }

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classify()
        return d


def _key() -> dict[str, str]:
    k = os.environ.get("NCBI_API_KEY", "")
    return {"api_key": k} if k else {}


def search(term: str, retmax: int = 500) -> list[str]:
    """Return PMIDs for a query. Use PubMed syntax, e.g. 'BPC-157 AND Humans[Mesh]'."""
    data = get(
        f"{BASE}/esearch.fcgi",
        params={"db": "pubmed", "term": term, "retmode": "json",
                "retmax": retmax, **_key()},
        fixture="pubmed_esearch.json",
        min_interval=0.34 if not os.environ.get("NCBI_API_KEY") else 0.11,
    )
    return list(data.get("esearchresult", {}).get("idlist", []))


def count(term: str) -> int:
    """How many PubMed records match. Cheap: retmax=0."""
    data = get(
        f"{BASE}/esearch.fcgi",
        params={"db": "pubmed", "term": term, "retmode": "json", "retmax": 0, **_key()},
        fixture="pubmed_esearch.json",
    )
    return int(data.get("esearchresult", {}).get("count", 0))


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def parse_efetch(xml_text: str) -> list[Paper]:
    """Parse a PubmedArticleSet into Paper objects."""
    root = ET.fromstring(xml_text)
    papers: list[Paper] = []
    for art in root.findall(".//PubmedArticle"):
        medline = art.find("MedlineCitation")
        if medline is None:
            continue
        pmid = _text(medline.find("PMID"))
        article = medline.find("Article")
        if article is None:
            continue

        year = None
        for path in ("Journal/JournalIssue/PubDate/Year", "Journal/JournalIssue/PubDate/MedlineDate"):
            raw = _text(article.find(path))
            if raw:
                digits = "".join(ch for ch in raw[:4] if ch.isdigit())
                if len(digits) == 4:
                    year = int(digits)
                break

        doi = ""
        for eid in article.findall(".//ELocationID"):
            if eid.get("EIdType") == "doi":
                doi = _text(eid)
                break

        authors, affiliations = [], []
        for a in article.findall(".//Author"):
            last, initials = _text(a.find("LastName")), _text(a.find("Initials"))
            collective = _text(a.find("CollectiveName"))
            if last:
                authors.append(f"{last} {initials}".strip())
            elif collective:
                authors.append(collective)
            for aff in a.findall(".//Affiliation"):
                val = _text(aff)
                if val:
                    affiliations.append(val)

        abstract = " ".join(
            _text(seg) for seg in article.findall(".//Abstract/AbstractText")
        ).strip()

        papers.append(Paper(
            pmid=pmid,
            title=_text(article.find("ArticleTitle")),
            journal=_text(article.find("Journal/Title")),
            year=year,
            doi=doi,
            abstract=abstract,
            authors=authors,
            affiliations=sorted(set(affiliations)),
            mesh=[_text(m) for m in medline.findall(".//MeshHeading/DescriptorName")],
            publication_types=[_text(p) for p in article.findall(".//PublicationType")],
        ))
    return papers


def fetch(pmids: list[str], batch: int = 200) -> list[Paper]:
    """Fetch full records for PMIDs, in batches."""
    out: list[Paper] = []
    for i in range(0, len(pmids), batch):
        chunk = pmids[i:i + batch]
        xml_text = get(
            f"{BASE}/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(chunk), "retmode": "xml", **_key()},
            fixture="pubmed_efetch.xml",
            parse="text",
        )
        out.extend(parse_efetch(xml_text))
    return out


def species_breakdown(term: str) -> dict[str, int]:
    """Human vs animal record counts for a compound, using MeSH, in 3 requests.

    This is the cheapest version of the headline number for track 1.
    """
    return {
        "total": count(term),
        "human": count(f"({term}) AND Humans[Mesh]"),
        "animal": count(f"({term}) AND Animals[Mesh] NOT Humans[Mesh]"),
        "trials": count(f"({term}) AND (Clinical Trial[Publication Type])"),
        "randomized": count(f"({term}) AND (Randomized Controlled Trial[Publication Type])"),
        "case_reports": count(f"({term}) AND (Case Reports[Publication Type])"),
    }
