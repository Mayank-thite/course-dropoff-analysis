import math

import numpy as np
import pandas as pd

from dropoff.model import FLAG_SHARE, fit_and_evaluate
from dropoff.stats import funnel_conversion, precision_recall, two_proportion_test


def test_two_proportion_known_values():
    # 30/100 vs 20/100: pooled p = 0.25, SE = sqrt(0.25*0.75*0.02)
    r = two_proportion_test(30, 100, 20, 100)
    se_pooled = math.sqrt(0.25 * 0.75 * 0.02)
    assert abs(r["diff"] - 0.10) < 1e-12
    assert abs(r["z"] - 0.10 / se_pooled) < 1e-9
    assert abs(r["p_value"] - 0.1025) < 1e-3
    se = math.sqrt(0.3 * 0.7 / 100 + 0.2 * 0.8 / 100)
    assert abs(r["ci_low"] - (0.10 - 1.959964 * se)) < 1e-5


def test_two_proportion_no_difference():
    r = two_proportion_test(50, 100, 50, 100)
    assert r["diff"] == 0 and r["p_value"] == 1.0


def test_precision_recall():
    r = precision_recall([1, 1, 0, 0, 1], [1, 0, 1, 0, 1])
    assert (r["tp"], r["fp"], r["fn"]) == (2, 1, 1)
    assert abs(r["precision"] - 2 / 3) < 1e-12 and abs(r["recall"] - 2 / 3) < 1e-12


def test_funnel_conversion():
    df = pd.DataFrame({"a": [10, 10], "b": [8, 6], "c": [4, 3]})
    out = funnel_conversion(df, ["a", "b", "c"])
    assert [o["students"] for o in out] == [20, 14, 7]
    assert abs(out[2]["of_previous"] - 0.5) < 1e-12
    assert abs(out[2]["of_registered"] - 0.35) < 1e-12


def test_model_holds_out_presentation_and_flags_share():
    rng = np.random.default_rng(0)
    n = 2000
    active = rng.integers(0, 28, n)
    withdrew = rng.random(n) < 1 / (1 + np.exp(0.3 * (active - 8)))
    df = pd.DataFrame({
        "code_module": "XXX",
        "code_presentation": rng.choice(["2013J", "2014B", "2014J"], n),
        "id_student": range(n),
        "registered_at_day28": True,
        "clicks_pre_start": rng.integers(0, 50, n),
        "clicks_w1_4": active * 10,
        "clicks_w3_4": active * 5,
        "active_days_w1_4": active,
        "early_assessments_missed": 0,
        "withdrew": withdrew,
    })
    r = fit_and_evaluate(df, "2014J")
    assert "2014J" not in r["train_presentations"]
    assert r["n_test"] == int((df["code_presentation"] == "2014J").sum())
    assert abs(r["model"]["flagged"] / r["n_test"] - FLAG_SHARE) < 0.05
    assert r["auc_test"] > 0.7  # signal is planted, so the model should find it
    assert r["coefficients_per_sd"]["active_days_w1_4"] < 0
