# Track 4 — Prediction checks

**Deliverable:** whether a model can predict a measured property on sequences
it has never seen — and whether its score means what it appears to mean.

```python
from pephack.scoring.prediction import evaluate, report
print(report(evaluate(train_seqs, train_y, test_seqs, test_y, my_predictions)))
```

```bash
python -m pephack.scoring.prediction --train train.csv --test test.csv \
    --predictions preds.txt      # CSVs with columns sequence,label
```

## Datasets

**PepBenchmark** — 35 datasets with fixed splits and published baselines.
`pip install pepbenchmark`. Use *their* splits: they are built with k-mer
grouping plus MMseqs2 clustering at 30% identity to stop near-duplicate leakage,
and a split you invent will be leakier. `pephack.datasets.pepbenchmark.describe()`
carries a per-dataset warning.

One correction worth having before you pick a dataset: the set called
`toxicity` is **toxin-like peptides defined by a UniProt keyword** — venom
provenance, not human safety. Do not label it "is this safe".

**MegaScale** — 776,298 folding stabilities across mutants of 479 small domains,
CC-BY on HuggingFace. The only set here big enough to train on rather than
overfit. Split by wild-type domain, never by row: mutants of one domain are
nearly identical sequences and a random split puts siblings on both sides.
`megascale.split_by_domain()` does it, deterministically, so two teams get the
same split.

## The three numbers the scorer prints next to yours

- **random**, averaged over 200 draws, plus the **noise floor**: how far from 0.5
  a random scorer gets by luck at your sample size. A margin smaller than that
  is not a result.
- **nearest neighbour** — copy the label of the most similar training sequence.
  The memorisation baseline.
- **shortcut probe** — logistic regression on four features: length, net charge,
  mean hydrophobicity, aromaticity. No sequence information beyond bulk
  composition.

**The probe is the important one.** These datasets are usually assembled by
taking positives from one database and negatives from somewhere convenient,
which leaves the classes differing in length and charge. PepBenchmark itself
notes that positive and negative distributions still differ enough for shortcut
features to remain possible on some sets: the hemolytic negatives come from a
single source set, and the cell-penetration negatives are random peptides.

If your model is within 0.02 of the probe, you have not built a predictor of the
property. You have built a detector of how the dataset was assembled. **That is
a finding — report it.** A documented leakage audit plus a corrected split is a
more useful output from this day than another tenth of a point of AUC.

The scorer also splits the test set by similarity to training data and reports
AUC on the near and far halves separately. A model that only works near its
training data is memorising, and the size of that gap is the honest number.
