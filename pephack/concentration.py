"""How concentrated is a body of literature?

This is the quantitative core of the evidence graph track. "500 papers" and
"500 papers from one lab" are completely different evidence bases, and the
difference is computable from author lists.

The metrics:
  n_papers              how many records you are measuring over
  top_author_share      fraction of papers containing the single most frequent author
  hhi_authors           Herfindahl index over author appearance shares.
                        1.0 = one author on everything. Near 0 = very diffuse.
  distinct_last_authors how many different people are senior author
  n_groups              crude affiliation clusters, see cluster_affiliations
  largest_group_share   fraction of papers from the biggest affiliation cluster
  independent_groups    groups that do not share the top author at all

The affiliation clustering here is deliberately crude: normalise the string,
take the significant words, and group on the first few. It will merge two
departments at one university and split one lab that renamed itself. Improving
it is a legitimate afternoon of work and a real contribution - your improved
version should disagree with this one on specific compounds, and you should be
able to say which answer is right.
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Any, Iterable, Sequence

STOPWORDS = {
    "department", "dept", "of", "the", "and", "for", "school", "faculty",
    "institute", "center", "centre", "laboratory", "lab", "division", "unit",
    "research", "medicine", "medical", "sciences", "science", "university",
    "hospital", "clinic", "college", "group", "a", "in", "at",
}


def normalise_affiliation(raw: str) -> str:
    text = raw.lower()
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", " ", text)      # emails
    text = re.sub(r"https?://\S+", " ", text)                  # urls
    text = re.sub(r"[^a-z\s]", " ", text)                      # punctuation, digits
    return re.sub(r"\s+", " ", text).strip()


def affiliation_key(raw: str, depth: int = 2) -> str:
    """A crude institution key: the first `depth` significant words."""
    words = [w for w in normalise_affiliation(raw).split() if w not in STOPWORDS and len(w) > 2]
    return " ".join(words[:depth]) if words else "unknown"


def cluster_affiliations(affiliations: Iterable[str], depth: int = 2) -> dict[str, int]:
    return dict(Counter(affiliation_key(a, depth) for a in affiliations if a))


def _hhi(counts: Sequence[int]) -> float:
    total = sum(counts)
    if total == 0:
        return 0.0
    return sum((c / total) ** 2 for c in counts)


def author_concentration(papers: Sequence[Any]) -> dict[str, Any]:
    """papers: objects with .authors (list[str]) and .affiliations (list[str]).

    Works with pephack.pubmed.Paper directly.
    """
    n = len(papers)
    if n == 0:
        return {"n_papers": 0, "note": "no papers to measure"}

    appearances: Counter[str] = Counter()
    for p in papers:
        for a in set(getattr(p, "authors", []) or []):
            appearances[a] += 1

    last_authors = Counter(
        getattr(p, "authors", [])[-1]
        for p in papers
        if getattr(p, "authors", None)
    )

    all_affs: list[str] = []
    for p in papers:
        all_affs.extend(getattr(p, "affiliations", []) or [])
    groups = cluster_affiliations(all_affs)

    top_author, top_count = (appearances.most_common(1) or [("", 0)])[0]

    papers_without_top = [
        p for p in papers if top_author not in (getattr(p, "authors", []) or [])
    ]

    return {
        "n_papers": n,
        "n_distinct_authors": len(appearances),
        "top_author": top_author,
        "top_author_papers": top_count,
        "top_author_share": round(top_count / n, 3),
        "hhi_authors": round(_hhi(list(appearances.values())), 4),
        "distinct_last_authors": len(last_authors),
        "most_frequent_last_author": (last_authors.most_common(1) or [("", 0)])[0][0],
        "n_groups": len(groups),
        "largest_group": max(groups, key=groups.get) if groups else None,
        "largest_group_share": round(max(groups.values()) / max(sum(groups.values()), 1), 3) if groups else 0.0,
        "papers_without_top_author": len(papers_without_top),
        "share_independent_of_top_author": round(len(papers_without_top) / n, 3),
        "caveats": [
            "Author name collapsing is by 'Lastname Initials' and will merge distinct people.",
            "Affiliation clustering is crude; see cluster_affiliations.",
            "Papers with no affiliation data are invisible to the group metrics.",
        ],
    }


def verdict(metrics: dict[str, Any]) -> str:
    """A blunt one-line read. Thresholds are arguable - argue with them."""
    n = metrics.get("n_papers", 0)
    if n < 5:
        return "too few papers to say anything about concentration"
    share = metrics.get("top_author_share", 0.0)
    indep = metrics.get("share_independent_of_top_author", 1.0)
    if share >= 0.5:
        return (f"highly concentrated: one author appears on {share:.0%} of papers; "
                f"only {indep:.0%} of the literature is independent of them")
    if share >= 0.25:
        return f"moderately concentrated: top author on {share:.0%} of papers"
    return f"diffuse: top author on {share:.0%} of papers"
