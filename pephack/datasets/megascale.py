"""MegaScale stability loader (Tsuboyama et al., Nature 2023).

776,298 folding stability measurements across mutants of 479 small protein
domains, 40-72 residues, measured by cDNA display proteolysis. CC-BY-4.0.

    https://huggingface.co/datasets/RosettaCommons/MegaScale

This is the only dataset in the pack large enough to train on rather than
overfit. Two warnings:

1. Mutants of the same wild-type domain are nearly identical sequences. A
   random split puts siblings in both train and test and your score becomes
   meaningless. Split by WILD-TYPE DOMAIN, never by row. split_by_domain below
   does that.

2. It measures folding stability of small domains, not the stability of a
   15-mer therapeutic peptide in blood. Those are different quantities. If your
   write-up says 'predicts peptide stability', say which one you mean.
"""
from __future__ import annotations

import hashlib
from typing import Any, Iterable, Sequence


def load(split: str = "train"):
    """Load MegaScale via the datasets library."""
    try:
        from datasets import load_dataset  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise SystemExit(
            "huggingface datasets is not installed.\n"
            "  pip install datasets\n"
            f"(import error: {exc})"
        )
    return load_dataset("RosettaCommons/MegaScale", split=split)


def split_by_domain(rows: Sequence[dict[str, Any]], domain_key: str = "wt_name",
                    test_fraction: float = 0.2, seed: str = "pephack") -> tuple[list[int], list[int]]:
    """Group-aware split: every mutant of a domain lands on the same side.

    Deterministic and dependency-free: hash the domain name, take the bottom
    fraction of hash space as test. Same inputs always give the same split, so
    two teams can compare numbers.
    """
    train_idx, test_idx = [], []
    cutoff = int(test_fraction * (1 << 32))
    for i, row in enumerate(rows):
        domain = str(row.get(domain_key, ""))
        digest = hashlib.sha256(f"{seed}:{domain}".encode()).digest()
        bucket = int.from_bytes(digest[:4], "big")
        (test_idx if bucket < cutoff else train_idx).append(i)
    return train_idx, test_idx


def leakage_check(train_domains: Iterable[str], test_domains: Iterable[str]) -> dict[str, Any]:
    tr, te = set(train_domains), set(test_domains)
    overlap = tr & te
    return {
        "train_domains": len(tr),
        "test_domains": len(te),
        "overlapping_domains": len(overlap),
        "clean": not overlap,
        "examples": sorted(overlap)[:10],
    }
