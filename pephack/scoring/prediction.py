"""Score a sequence-property prediction, and check whether the dataset is
solvable for the wrong reasons.

Three things happen here, and the second and third matter more than the first.

1. Your model's score on the held-out split.

2. Three mandatory baselines.
     random              random scores, averaged over 200 draws, plus the noise
                      floor: how far from 0.5 a random scorer gets by luck at
                      your sample size. A margin under that is not a result.
     nearest_neighbour   copy the label of the most similar training sequence,
                         by character 3-gram cosine. This is the memorisation
                         baseline. If you cannot beat it you have not learned
                         anything that generalises.
     shortcut_probe      logistic regression on FOUR trivial features only:
                         length, net charge, mean hydrophobicity, aromaticity.
                         No sequence information beyond bulk composition.

   The shortcut probe is the important one. Peptide activity datasets are
   usually built by taking positives from one database and negatives from
   somewhere convenient, which leaves the two classes differing in length and
   charge. A model can score well by reading that difference and knowing
   nothing about biology. PepBenchmark itself reports that positive and
   negative distributions still differ enough for shortcut features to remain
   possible on some of its sets.

   If your model is close to the shortcut probe, you have not built a predictor
   of the property. You have built a detector of how the dataset was assembled.
   That is a finding. Report it.

3. A near/far split of the test set by similarity to training data. A model
   that only works on test sequences close to something it trained on is
   memorising. The gap between near AUC and far AUC is the honest measure.

Usage:
    from pephack.scoring.prediction import evaluate
    result = evaluate(train_seqs, train_y, test_seqs, test_y, my_predictions)
    print(report(result))
"""
from __future__ import annotations

import json
from typing import Any, Sequence

import numpy as np

# Kyte-Doolittle hydropathy
KD = {
    "A": 1.8, "R": -4.5, "N": -3.5, "D": -3.5, "C": 2.5, "Q": -3.5, "E": -3.5,
    "G": -0.4, "H": -3.2, "I": 4.5, "L": 3.8, "K": -3.9, "M": 1.9, "F": 2.8,
    "P": -1.6, "S": -0.8, "T": -0.7, "W": -0.9, "Y": -1.3, "V": 4.2,
}
POSITIVE = {"K": 1.0, "R": 1.0, "H": 0.1}
NEGATIVE = {"D": 1.0, "E": 1.0}
AROMATIC = set("FWY")


def bulk_features(seq: str) -> list[float]:
    """The four features a model must beat. Deliberately dumb."""
    s = "".join(ch for ch in seq.upper() if ch.isalpha())
    n = max(len(s), 1)
    charge = sum(POSITIVE.get(c, 0.0) for c in s) - sum(NEGATIVE.get(c, 0.0) for c in s)
    hydro = sum(KD.get(c, 0.0) for c in s) / n
    aromatic = sum(1 for c in s if c in AROMATIC) / n
    return [float(len(s)), charge, hydro, aromatic]


def auroc(y_true: Sequence[float], scores: Sequence[float]) -> float:
    """Rank-based AUC. Handles ties. Returns 0.5 if only one class is present."""
    y = np.asarray(y_true, dtype=float)
    s = np.asarray(scores, dtype=float)
    pos, neg = y == 1, y == 0
    n_pos, n_neg = int(pos.sum()), int(neg.sum())
    if n_pos == 0 or n_neg == 0:
        return 0.5
    order = np.argsort(s, kind="mergesort")
    ranks = np.empty(len(s), dtype=float)
    ranks[order] = np.arange(1, len(s) + 1)
    # average ranks within ties
    _, inv, counts = np.unique(s, return_inverse=True, return_counts=True)
    sums = np.bincount(inv, weights=ranks)
    ranks = (sums / counts)[inv]
    return float((ranks[pos].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg))


def _ngram_matrix(seqs: Sequence[str], n: int = 3):
    from sklearn.feature_extraction.text import TfidfVectorizer
    vec = TfidfVectorizer(analyzer="char", ngram_range=(1, n), lowercase=False)
    return vec, vec.fit_transform(seqs)


def nearest_neighbour_scores(train_seqs: Sequence[str], train_y: Sequence[float],
                             test_seqs: Sequence[str]) -> tuple[np.ndarray, np.ndarray]:
    """Returns (predicted_score, max_similarity_to_train) for each test sequence."""
    from sklearn.metrics.pairwise import cosine_similarity
    vec, train_x = _ngram_matrix(list(train_seqs))
    test_x = vec.transform(list(test_seqs))
    sim = cosine_similarity(test_x, train_x)
    nearest = sim.argmax(axis=1)
    return np.asarray(train_y, dtype=float)[nearest], sim.max(axis=1)


def shortcut_probe(train_seqs: Sequence[str], train_y: Sequence[float],
                   test_seqs: Sequence[str]) -> np.ndarray:
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    from sklearn.pipeline import make_pipeline

    x_train = np.array([bulk_features(s) for s in train_seqs])
    x_test = np.array([bulk_features(s) for s in test_seqs])
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
    model.fit(x_train, np.asarray(train_y))
    return model.predict_proba(x_test)[:, 1]


def evaluate(train_seqs: Sequence[str], train_y: Sequence[float],
             test_seqs: Sequence[str], test_y: Sequence[float],
             predictions: Sequence[float] | None = None,
             *, near_threshold: float = 0.9, seed: int = 0) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    test_y_arr = np.asarray(test_y, dtype=float)

    nn_scores, max_sim = nearest_neighbour_scores(train_seqs, train_y, test_seqs)
    probe_scores = shortcut_probe(train_seqs, train_y, test_seqs)

    # A single random draw is noisy: at n=150 it lands 0.04 off 0.5 on average and
    # 0.09 off at the 95th percentile. So average over many draws, and report the
    # 95th percentile as the noise floor - a margin smaller than that is not a result.
    draws = [auroc(test_y_arr, rng.random(len(test_seqs))) for _ in range(200)]
    random_auc = float(np.mean(draws))
    random_p95 = float(np.percentile(np.abs(np.array(draws) - 0.5), 95))

    result: dict[str, Any] = {
        "n_train": len(train_seqs),
        "n_test": len(test_seqs),
        "test_positive_rate": round(float(test_y_arr.mean()), 3),
        "baselines": {
            "random": round(random_auc, 3),
            "nearest_neighbour": round(auroc(test_y_arr, nn_scores), 3),
            "shortcut_probe": round(auroc(test_y_arr, probe_scores), 3),
        },
        "noise_floor_auc": round(random_p95, 3),
        "leakage": {
            "mean_max_similarity_to_train": round(float(max_sim.mean()), 3),
            "near_threshold": near_threshold,
            "n_near": int((max_sim >= near_threshold).sum()),
            "n_far": int((max_sim < near_threshold).sum()),
        },
    }

    probe_auc = result["baselines"]["shortcut_probe"]
    result["dataset_verdict"] = (
        f"shortcut probe reaches AUC {probe_auc:.3f} using only length, charge, "
        "hydrophobicity and aromaticity. "
        + ("That is close to chance, so the labels are not trivially separable by bulk "
           "composition." if probe_auc < 0.65 else
           "Any model scoring near this has probably learned how the dataset was "
           "assembled rather than the property.")
    )

    if predictions is not None:
        pred = np.asarray(predictions, dtype=float)
        model_auc = auroc(test_y_arr, pred)
        near, far = max_sim >= near_threshold, max_sim < near_threshold
        result["model"] = {
            "auroc": round(model_auc, 3),
            "auroc_near_train": (round(auroc(test_y_arr[near], pred[near]), 3)
                                 if near.sum() > 1 else None),
            "auroc_far_from_train": (round(auroc(test_y_arr[far], pred[far]), 3)
                                     if far.sum() > 1 else None),
            "beats_random": model_auc > result["baselines"]["random"],
            "exceeds_noise_floor": abs(model_auc - 0.5) > random_p95,
            "beats_nearest_neighbour": model_auc > result["baselines"]["nearest_neighbour"],
            "margin_over_shortcut_probe": round(model_auc - probe_auc, 3),
        }
        margin = result["model"]["margin_over_shortcut_probe"]
        if margin < 0.02:
            result["model"]["read"] = (
                "Your model does not beat four trivial features. Whatever it learned, "
                "it is not the property."
            )
        elif margin < 0.05:
            result["model"]["read"] = (
                "Barely above the shortcut probe. Report this margin, not your raw AUC."
            )
        else:
            result["model"]["read"] = (
                f"{margin:.3f} above the shortcut probe, which is the only part of your "
                "AUC that is evidence of learning the property."
            )
        near_auc, far_auc = result["model"]["auroc_near_train"], result["model"]["auroc_far_from_train"]
        if near_auc is not None and far_auc is not None and near_auc - far_auc > 0.1:
            result["model"]["read"] += (
                f" Also: AUC drops from {near_auc:.3f} to {far_auc:.3f} on test sequences "
                "far from anything in training, which is what memorisation looks like."
            )
    return result


def report(result: dict[str, Any]) -> str:
    lines = ["=" * 64,
             f"test n={result['n_test']}  positives {result['test_positive_rate']:.3f}",
             "baselines:"]
    for name, value in result["baselines"].items():
        lines.append(f"  {name:<20} AUC {value:.3f}")
    if "model" in result:
        m = result["model"]
        lines.append(f"  {'YOUR MODEL':<20} AUC {m['auroc']:.3f}")
        lines.append(f"    near train AUC {m['auroc_near_train']}   far from train AUC {m['auroc_far_from_train']}")
        lines.append(f"    margin over shortcut probe: {m['margin_over_shortcut_probe']:+.3f}")
        lines.append(f"  -> {m['read']}")
    lines.append(f"noise floor at this n: a random scorer reaches |AUC-0.5| of "
                 f"{result['noise_floor_auc']:.3f} five percent of the time")
    lines.append(f"dataset: {result['dataset_verdict']}")
    lines.append("=" * 64)
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Score a prediction submission.")
    ap.add_argument("--train", required=True, help="CSV with columns sequence,label")
    ap.add_argument("--test", required=True, help="CSV with columns sequence,label")
    ap.add_argument("--predictions", help="text file, one score per test row, same order")
    args = ap.parse_args()

    import csv

    def read(path: str) -> tuple[list[str], list[float]]:
        seqs, ys = [], []
        with open(path, newline="") as fh:
            for row in csv.DictReader(fh):
                seqs.append(row["sequence"])
                ys.append(float(row["label"]))
        return seqs, ys

    tr_s, tr_y = read(args.train)
    te_s, te_y = read(args.test)
    preds = None
    if args.predictions:
        preds = [float(x) for x in open(args.predictions).read().split()]
    print(report(evaluate(tr_s, tr_y, te_s, te_y, preds)))
    print(json.dumps(evaluate(tr_s, tr_y, te_s, te_y, preds), indent=2)[:0] or "", end="")
