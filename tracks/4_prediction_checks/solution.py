#!/usr/bin/env python3
"""Your model, scored honestly. Fill in fit_predict()."""
from __future__ import annotations

import argparse
from typing import Sequence

from pephack.scoring.prediction import evaluate, report


def fit_predict(train_seqs: Sequence[str], train_y: Sequence[float],
                test_seqs: Sequence[str]) -> Sequence[float]:
    """Train on train_seqs/train_y, return one score per test sequence.

    Ideas, roughly in order of effort:
      - ESM embeddings + logistic regression (needs torch + fair-esm)
      - fine-tune a small protein language model
      - hand-built physicochemical features beyond the four the probe uses
      - an ensemble, with the k-mer baseline as one member

    Before you report anything, look at the margin over the shortcut probe.
    That margin, not your AUC, is the part that is evidence of learning the
    property.
    """
    raise NotImplementedError("your model goes here")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", help="PepBenchmark dataset name")
    ap.add_argument("--train")
    ap.add_argument("--test")
    args = ap.parse_args()

    if args.dataset:
        from pephack.datasets import pepbenchmark
        print(pepbenchmark.describe(args.dataset), "\n")
        tr_s, tr_y = pepbenchmark.load(args.dataset, "train")
        te_s, te_y = pepbenchmark.load(args.dataset, "test")
    elif args.train and args.test:
        from baseline import read_csv
        tr_s, tr_y = read_csv(args.train)
        te_s, te_y = read_csv(args.test)
    else:
        ap.error("pass --dataset NAME, or both --train and --test")

    preds = fit_predict(tr_s, tr_y, te_s)
    print(report(evaluate(tr_s, tr_y, te_s, te_y, preds)))


if __name__ == "__main__":
    main()
