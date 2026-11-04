import math

import numpy as np
import pandas as pd

from dropoff import causal
from dropoff.config import FLAG_SHARE
from dropoff.model import fit_and_evaluate, model_population
from dropoff.stats import funnel_conversion, holm_adjust, precision_recall, two_proportion_test


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


def _synthetic_features(n: int = 3000, seed: int = 0) -> pd.DataFrame:
    """Fake early_features rows with every column the model and the A/B code read."""
    rng = np.random.default_rng(seed)
    active = rng.integers(0, 28, n)
    module = rng.choice(["XXX", "YYY"], n)
    return pd.DataFrame({
        "code_module": module,
        "code_presentation": rng.choice(["2013J", "2014B", "2014J"], n),
        "id_student": range(n),
        "withdrawal_day_known": True,
        "registered_at_day28": True,
        "date_registration": -rng.integers(1, 120, n),
        "gender": rng.choice(["F", "M"], n),
        "highest_education": rng.choice(["A Level or Equivalent", "Lower Than A Level"], n),
        "imd_band": rng.choice(["0-10%", "50-60%", None], n),
        "age_band": rng.choice(["0-35", "35-55"], n),
        "disability": rng.choice(["N", "Y"], n),
        "num_of_prev_attempts": rng.integers(0, 3, n),
        "studied_credits": rng.choice([60, 120], n),
        "clicks_pre_start": rng.integers(0, 50, n),
        "active_days_pre_start": rng.integers(0, 5, n),
        "clicks_w1_4": active * 10,
        "clicks_w1_2": active * 5,
        "clicks_w3_4": active * 5,
        "active_days_w1_4": active,
        "active_days_w3_4": active // 2,
        "last_active_day": np.where(active > 0, 27, np.nan),
        "early_assessments_due": 1,
        "early_assessments_submitted": 1,
        "early_assessments_missed": 0,
        "early_avg_score": rng.uniform(40, 100, n),
        "withdrew": rng.random(n) < 1 / (1 + np.exp(0.3 * (active - 8))),
        "passed": False,
    })


def test_model_holds_out_presentation_and_flags_share():
    df = _synthetic_features()
    r = fit_and_evaluate(df, "2014J")
    assert "2014J" not in r["train_presentations"]
    assert r["n_test"] == int((df["code_presentation"] == "2014J").sum())
    assert abs(r["model"]["flagged"] / r["n_test"] - FLAG_SHARE) < 0.05
    assert r["auc_test"] > 0.7  # signal is planted, so the model should find it
    assert 0 < r["pr_auc_test"] <= 1
    assert r["coefficients_per_sd"]["active_days_w1_4"] < 0
    assert [s["name"] for s in r["scorers"]][0].startswith("Rule")


def test_model_population_drops_unknown_and_late_registrants():
    df = _synthetic_features(n=10)
    df.loc[0, "withdrawal_day_known"] = False
    df.loc[1, "date_registration"] = 30
    df.loc[2, "registered_at_day28"] = False
    assert set(model_population(df)["id_student"]) == set(range(3, 10))


def test_adjustment_removes_planted_confounding():
    """Group A is mostly in an easy module. True effect of A is zero."""
    rng = np.random.default_rng(1)
    df = _synthetic_features(n=6000, seed=1)
    easy = df["code_module"] == "XXX"
    df["clicks_pre_start"] = (rng.random(len(df)) < np.where(easy, 0.9, 0.3)).astype(int)
    df["withdrew"] = rng.random(len(df)) < np.where(easy, 0.10, 0.40)
    r = causal.run(df)
    assert r["raw_diff"] < -0.10                      # looks like A helps a lot
    assert abs(r["steps"][0]["ame"]) < 0.03           # but not inside a presentation
    assert r["steps"][0]["ci_low"] < 0 < r["steps"][0]["ci_high"]


def test_holm_adjust():
    # sorted p = 0.01, 0.02, 0.04 -> 0.03, 0.04, 0.04 (step-down, monotone)
    out = holm_adjust(pd.Series([0.04, 0.01, 0.02]))
    assert np.allclose(out.to_numpy(), [0.04, 0.03, 0.04])
