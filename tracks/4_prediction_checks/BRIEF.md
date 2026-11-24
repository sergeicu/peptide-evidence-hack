# Track 4 — Prediction checks

**Build:** graders that tell you whether a model can predict a measured
property — red blood cell lysis, permeability, stability — on sequences it has
never seen, so you know whether a model's opinion about a peptide is worth
anything.

```bash
python -m pip install -e ".[dev]"

python tracks/4_prediction_checks/run.py --dataset hemolytic           # k-mer TF-IDF + logistic regression
python tracks/4_prediction_checks/run.py --train train.csv --test test.csv
```

## The baseline is two seconds of sklearn and it is not a toy

`baseline.py` is character k-mer TF-IDF into logistic regression. No pretrained
model, no GPU. On several of these datasets it lands near published numbers,
which is itself the finding: if a 2-second model matches the literature, the
literature is measuring something easy.

## Three numbers print next to yours. The third is the one that matters.

- **random**, averaged over 200 draws, plus the **noise floor** — how far from
  0.5 a random scorer gets by luck at your sample size. A margin smaller than
  that is not a result.
- **nearest neighbour** — copy the label of the most similar training sequence.
  The memorisation baseline.
- **shortcut probe** — logistic regression on four features only: length, net
  charge, mean hydrophobicity, aromaticity. No sequence information beyond bulk
  composition.

These datasets are typically built by taking positives from one database and
negatives from somewhere convenient, which leaves the classes differing in
length and charge. The hemolytic negatives come from a single source set; the
cell-penetration negatives are random peptides.

**If your model is within 0.02 of the probe you have not built a predictor of
the property — you have built a detector of how the dataset was assembled.**
That is a finding. Report it. A documented leakage audit plus a corrected split
is a better output from this day than another tenth of a point of AUC.

The scorer also splits the test set by similarity to training data and reports
AUC on the near and far halves separately. A model that only works near its
training data is memorising, and that gap is the honest number.

## One correction before you choose a dataset

PepBenchmark's `toxicity` set is **toxin-like peptides defined by a UniProt
keyword** — venom provenance, not human safety. Do not label it "is this safe".
`pephack.datasets.pepbenchmark.describe(name)` carries a warning per dataset.

For MegaScale, split by wild-type domain and never by row: mutants of one
domain are nearly identical sequences, and a random split puts siblings on both
sides. `megascale.split_by_domain()` does it deterministically so two teams get
the same split.

See `README.md`.
