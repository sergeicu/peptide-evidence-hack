"""Tests for the scorers. These are the numbers teams will be judged on."""
import json
import os
from pathlib import Path

import numpy as np
import pytest

os.environ["PEPHACK_OFFLINE"] = "1"

from pephack.scoring import claims, prediction

GOLD = Path(__file__).resolve().parents[1] / "data" / "gold" / "claims.jsonl"


def _gold():
    return claims.load_jsonl(GOLD)


def _sub(verdict_fn, cited=()):
    return [{"id": g["id"], "verdict": verdict_fn(g), "cited_ids": list(cited)} for g in _gold()]


def test_gold_set_is_wellformed():
    rows = _gold()
    assert len(rows) >= 10
    assert len({r["id"] for r in rows}) == len(rows)
    for r in rows:
        assert r["verdict"] in claims.VERDICTS, r
        assert r["compound"] and r["claim"]
    # controls must be present or the scorer cannot catch a lazy agent
    assert any(r["verdict"] == "rct_supported" for r in rows)
    assert any(r["verdict"] == "contradicted" for r in rows)
    assert any(r["verdict"] == "not_a_factual_claim" for r in rows)


def test_unconfirmed_gold_blocks_scoring_by_default():
    with pytest.raises(SystemExit) as exc:
        claims.score(_gold(), _sub(lambda g: g["verdict"]))
    assert "confirmed_by" in str(exc.value)


def test_perfect_submission():
    res = claims.score(_gold(), _sub(lambda g: g["verdict"]), allow_unconfirmed=True)
    assert res["accuracy"] == 1.0
    assert res["macro_f1"] == 1.0
    assert res["control_accuracy"] == 1.0
    assert res["beats_baseline_on_macro_f1"] is True


def test_constant_answer_loses_on_macro_f1():
    """The whole point: 'no_evidence_found' for everything must not look good."""
    res = claims.score(_gold(), _sub(lambda g: "no_evidence_found"), allow_unconfirmed=True)
    assert res["beats_baseline_on_macro_f1"] is False
    assert res["macro_f1"] < 0.2
    assert res["control_accuracy"] == 0.0


def test_baseline_is_best_constant_predictor():
    res = claims.score(_gold(), _sub(lambda g: g["verdict"]), allow_unconfirmed=True)
    base = res["majority_baseline"]
    # no single constant answer may beat the reported baseline
    for candidate in claims.VERDICTS:
        other = claims.score(_gold(), _sub(lambda g, c=candidate: c), allow_unconfirmed=True)
        assert other["macro_f1"] <= base["macro_f1"] + 1e-9


def test_missing_items_are_reported_not_ignored():
    sub = _sub(lambda g: g["verdict"])[:-3]
    res = claims.score(_gold(), sub, allow_unconfirmed=True)
    assert len(res["missing_from_submission"]) == 3
    assert res["accuracy"] < 1.0


def test_invalid_verdict_flagged():
    sub = _sub(lambda g: "probably_fine")
    res = claims.score(_gold(), sub, allow_unconfirmed=True)
    assert res["invalid_verdicts"]


def test_citation_format_checking():
    res = claims.score(_gold(), _sub(lambda g: g["verdict"], cited=["PMID:123", "garbage"]),
                       allow_unconfirmed=True)
    assert res["citations"]["format_ok_rate"] == 0.5


def test_id_kinds():
    assert claims.id_kind("PMID:22300085") == "pmid"
    assert claims.id_kind("NCT01234567") == "nct"
    assert claims.id_kind("10.1038/s41586-023-06328-6") == "doi"
    assert claims.id_kind("PMC10412457") == "pmcid"
    assert claims.id_kind("NCT123") is None
    assert claims.id_kind("") is None


# ---------- prediction scorer ----------

def test_auroc_matches_sklearn():
    from sklearn.metrics import roc_auc_score
    rng = np.random.default_rng(0)
    for _ in range(40):
        y = rng.integers(0, 2, 120)
        if y.sum() in (0, len(y)):
            continue
        s = rng.choice([0.0, 0.5, 1.0], size=120)  # heavy ties
        assert abs(prediction.auroc(y, s) - roc_auc_score(y, s)) < 1e-12


def test_bulk_features():
    assert prediction.bulk_features("KKKK")[1] == 4.0      # net charge
    assert prediction.bulk_features("DDDD")[1] == -4.0
    assert prediction.bulk_features("AAAA")[0] == 4.0      # length
    assert prediction.bulk_features("FFFF")[3] == 1.0      # aromaticity


def test_shortcut_probe_detects_planted_shortcut():
    """Positives long and cationic, negatives short and neutral."""
    rng = np.random.default_rng(3)
    pos = ["".join(rng.choice(list("KRLA"), 30)) for _ in range(150)]
    neg = ["".join(rng.choice(list("GSTAD"), 9)) for _ in range(150)]
    seqs, y = pos + neg, [1] * 150 + [0] * 150
    res = prediction.evaluate(seqs[:100] + seqs[150:250], y[:100] + y[150:250],
                              seqs[100:150] + seqs[250:], y[100:150] + y[250:])
    assert res["baselines"]["shortcut_probe"] > 0.95
    assert "learned how the dataset was assembled" in res["dataset_verdict"]


def test_shortcut_probe_clean_on_composition_matched_data():
    """Same residues in both classes; only ORDER carries the label."""
    rng = np.random.default_rng(4)
    base = list("WTPYACDEFGHIKLMNQRSV")
    seqs, y = [], []
    for _ in range(400):
        s = list(rng.permutation(base))
        label = 0
        if rng.random() < 0.5:
            for ch in "WTPY":
                s.remove(ch)
            s = list("WTPY") + s
            label = 1
        seqs.append("".join(s))
        y.append(label)
    res = prediction.evaluate(seqs[:300], y[:300], seqs[300:], y[300:])
    assert res["baselines"]["shortcut_probe"] < 0.6
    assert "not trivially separable" in res["dataset_verdict"]


def test_random_baseline_is_centred_and_reports_noise_floor():
    rng = np.random.default_rng(5)
    seqs = ["".join(rng.choice(list("ACDEFG"), 15)) for _ in range(300)]
    y = list(rng.integers(0, 2, 300))
    res = prediction.evaluate(seqs[:200], y[:200], seqs[200:], y[200:])
    assert abs(res["baselines"]["random"] - 0.5) < 0.03
    assert 0.0 < res["noise_floor_auc"] < 0.25


def test_model_read_calls_out_shortcut_equivalent_model():
    rng = np.random.default_rng(6)
    pos = ["".join(rng.choice(list("KR"), 28)) for _ in range(120)]
    neg = ["".join(rng.choice(list("GS"), 8)) for _ in range(120)]
    seqs, y = pos + neg, [1] * 120 + [0] * 120
    tr_s, tr_y = seqs[:90] + seqs[120:210], y[:90] + y[120:210]
    te_s, te_y = seqs[90:120] + seqs[210:], y[90:120] + y[210:]
    # a "model" that is literally just the length feature
    preds = [len(s) for s in te_s]
    res = prediction.evaluate(tr_s, tr_y, te_s, te_y, preds)
    assert res["model"]["margin_over_shortcut_probe"] < 0.02
    assert "not the property" in res["model"]["read"]


def test_megascale_split_never_leaks_a_domain():
    from pephack.datasets import megascale
    rows = [{"wt_name": f"domain{i // 37}"} for i in range(1000)]
    tr, te = megascale.split_by_domain(rows)
    assert tr and te
    check = megascale.leakage_check([rows[i]["wt_name"] for i in tr],
                                    [rows[i]["wt_name"] for i in te])
    assert check["clean"] is True
    assert check["overlapping_domains"] == 0
