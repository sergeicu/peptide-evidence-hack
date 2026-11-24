#!/usr/bin/env python3
"""Baseline sequence-property model: k-mer TF-IDF + logistic regression.

This is the "half an hour with sklearn" baseline the hack description refers
to. It takes about two seconds to train and it is not a toy - on several of
these datasets it is competitive with published numbers, which is itself the
interesting finding.

    python tracks/4_prediction_checks/run.py --train train.csv --test test.csv
    python tracks/4_prediction_checks/run.py --dataset hemolytic

CSVs need columns: sequence,label

It prints your AUC next to the three mandatory baselines and the shortcut
probe. Read the probe line before you celebrate.
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pephack.scoring.prediction import evaluate, report  # noqa: E402


def read_csv(path: str) -> tuple[list[str], list[float]]:
    seqs, labels = [], []
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh)
        for col in ("sequence", "label"):
            if col not in (reader.fieldnames or []):
                raise SystemExit(f"{path}: expected a '{col}' column, found {reader.fieldnames}")
        for row in reader:
            seqs.append(row["sequence"].strip())
            labels.append(float(row["label"]))
    return seqs, labels


def fit_predict(train_seqs, train_y, test_seqs, max_k: int = 4):
    """Character k-mer TF-IDF into logistic regression. No pretrained model."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    model = make_pipeline(
        TfidfVectorizer(analyzer="char", ngram_range=(1, max_k), lowercase=False, min_df=2),
        LogisticRegression(max_iter=4000, C=1.0, class_weight="balanced"),
    )
    model.fit(list(train_seqs), list(train_y))
    return model.predict_proba(list(test_seqs))[:, 1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--train", help="CSV with sequence,label")
    ap.add_argument("--test", help="CSV with sequence,label")
    ap.add_argument("--dataset", help="PepBenchmark dataset name, e.g. hemolytic")
    ap.add_argument("--max-k", type=int, default=4)
    args = ap.parse_args()

    if args.dataset:
        from pephack.datasets import pepbenchmark
        print(pepbenchmark.describe(args.dataset), "\n")
        train_seqs, train_y = pepbenchmark.load(args.dataset, "train")
        test_seqs, test_y = pepbenchmark.load(args.dataset, "test")
    elif args.train and args.test:
        train_seqs, train_y = read_csv(args.train)
        test_seqs, test_y = read_csv(args.test)
    else:
        ap.error("pass --dataset NAME, or both --train and --test")

    print(f"training on {len(train_seqs)} sequences, testing on {len(test_seqs)}")
    preds = fit_predict(train_seqs, train_y, test_seqs, args.max_k)
    print(report(evaluate(train_seqs, train_y, test_seqs, test_y, preds)))


if __name__ == "__main__":
    main()
