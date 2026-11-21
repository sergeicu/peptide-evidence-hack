"""PepBenchmark loader.

PepBenchmark ships 35 peptide datasets with fixed splits and published
baselines as an installable package. Use THEIR splits. They are built with
k-mer grouping plus MMseqs2 clustering at 30% identity specifically to stop
near-duplicate leakage between train and test, and a split you invent yourself
will almost certainly be more leaky than theirs.

    pip install pepbenchmark        # or clone the repo if the package name moved
    https://github.com/ZGCI-AI4S-Pep/PepBenchmark

Datasets worth starting with, with sizes from the paper:
    hemolytic          4,306   binary   does it rupture red blood cells
    hemolytic HC50     1,926   regress  concentration causing 50% lysis
    toxicity           4,056   binary   NOTE: this is 'toxin-like peptide',
                                        from a UniProt keyword. It is venom
                                        provenance, NOT human safety. Do not
                                        label it 'is this safe'.
    cpp                2,296   binary   does it get into cells
    bbp                  665   binary   blood-brain barrier. Tiny, high variance.
    nc-cpp pampa       6,970   regress  passive permeability, artificial membrane,
                                        non-canonical peptides
    antimicrobial     52,941   binary   the biggest set here

Before you trust any score on these, run the shortcut probe in
pephack.scoring.prediction. The hemolytic negatives come from a single source
set, and the cell-penetration negatives are random peptides, so bulk
composition alone carries real signal on several of these datasets.
"""
from __future__ import annotations

from typing import Any

DATASET_NOTES: dict[str, dict[str, Any]] = {
    "hemolytic": {"n": 4306, "task": "binary",
                  "measures": "lysis of red blood cells",
                  "watch_out": "negatives drawn from one source set; ~47% redundancy in raw positives"},
    "hemolytic_hc50": {"n": 1926, "task": "regression",
                       "measures": "pHC50",
                       "watch_out": "labels average multiple assay conditions"},
    "toxicity": {"n": 4056, "task": "binary",
                 "measures": "toxin-like peptide by UniProt keyword",
                 "watch_out": "this is venom provenance, not human safety"},
    "cpp": {"n": 2296, "task": "binary",
            "measures": "cell penetration",
            "watch_out": "negatives are random peptides; length and charge differ between classes"},
    "bbp": {"n": 665, "task": "binary",
            "measures": "blood-brain barrier penetration",
            "watch_out": "very small; model-to-model variance exceeds most reported gains"},
    "antimicrobial": {"n": 52941, "task": "binary",
                      "measures": "antimicrobial activity",
                      "watch_out": "negative-set choice is a known source of inflated scores in this literature"},
}


def load(name: str, split: str = "train"):
    """Load a PepBenchmark dataset using the official package and splits.

    Returns (sequences, labels). Raises with instructions if the package is
    not installed, because guessing at a local copy is how leakage happens.
    """
    try:
        from pepbenchmark.single_peptide.singeltask_dataset import SingleTaskDatasetManager  # type: ignore
    except Exception as exc:  # pragma: no cover - depends on local install
        raise SystemExit(
            "PepBenchmark is not importable.\n"
            "  pip install pepbenchmark\n"
            "or clone https://github.com/ZGCI-AI4S-Pep/PepBenchmark and install it.\n"
            "Use their splits, not your own.\n"
            f"(import error: {exc})"
        )

    manager = SingleTaskDatasetManager(dataset_name=name, official_feature_names=["fasta", "label"])
    data = manager.get_official_feature(["fasta", "label"])
    splits = manager.get_official_split_indices()
    idx = getattr(splits, split, None) if not isinstance(splits, dict) else splits.get(split)
    seqs, labels = data["fasta"], data["label"]
    if idx is None:
        return list(seqs), list(labels)
    return [seqs[i] for i in idx], [labels[i] for i in idx]


def describe(name: str) -> str:
    note = DATASET_NOTES.get(name)
    if not note:
        return f"{name}: no local note. Read the PepBenchmark appendix before using it."
    return (f"{name}: n={note['n']}, {note['task']}, measures {note['measures']}. "
            f"Watch out: {note['watch_out']}")
