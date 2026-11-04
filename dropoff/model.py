"""Early-warning model: logistic regression on first-four-weeks behaviour only.

Train on the three earlier presentations, test on the last one (2014J),
so the test looks like using last year's model on a new intake.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .stats import precision_recall

FEATURES = [
    "log_clicks_w1_4",
    "log_clicks_w3_4",
    "active_days_w1_4",
    "early_assessments_missed",
    "log_clicks_pre_start",
]

# Share of students an advisor team could contact. The model flags this share.
FLAG_SHARE = 0.20


def build_xy(features: pd.DataFrame) -> pd.DataFrame:
    df = features[features["registered_at_day28"].astype(bool)].copy()
    df["log_clicks_w1_4"] = np.log1p(df["clicks_w1_4"].astype(float))
    df["log_clicks_w3_4"] = np.log1p(df["clicks_w3_4"].astype(float))
    df["log_clicks_pre_start"] = np.log1p(df["clicks_pre_start"].astype(float))
    df["active_days_w1_4"] = df["active_days_w1_4"].astype(float)
    df["early_assessments_missed"] = df["early_assessments_missed"].astype(float)
    df["withdrew"] = df["withdrew"].astype(bool)
    return df


def fit_and_evaluate(features: pd.DataFrame, test_presentation: str) -> dict:
    df = build_xy(features)
    train = df[df["code_presentation"] != test_presentation]
    test = df[df["code_presentation"] == test_presentation]

    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(train[FEATURES], train["withdrew"])
    p_train = model.predict_proba(train[FEATURES])[:, 1]
    p_test = model.predict_proba(test[FEATURES])[:, 1]

    # Threshold chosen on TRAIN so that FLAG_SHARE of training students are flagged.
    threshold = float(np.quantile(p_train, 1 - FLAG_SHARE))
    model_eval = precision_recall(test["withdrew"], p_test >= threshold)

    # Simple rule for comparison: fewest active days in weeks 1-4, same share, cut set on train.
    day_cut = float(np.quantile(train["active_days_w1_4"], FLAG_SHARE))
    rule_eval = precision_recall(test["withdrew"], test["active_days_w1_4"] <= day_cut)

    decile = pd.qcut(pd.Series(p_test).rank(method="first"), 10, labels=False) + 1
    top_decile_rate = float(test["withdrew"].values[decile.values == 10].mean())
    bottom_decile_rate = float(test["withdrew"].values[decile.values == 1].mean())

    coefs = model.named_steps["logisticregression"].coef_[0]
    return {
        "train_presentations": sorted(train["code_presentation"].unique().tolist()),
        "test_presentation": test_presentation,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "base_rate_test": float(test["withdrew"].mean()),
        "auc_test": float(roc_auc_score(test["withdrew"], p_test)),
        "top_decile_withdrawal_rate": top_decile_rate,
        "bottom_decile_withdrawal_rate": bottom_decile_rate,
        "threshold": threshold,
        "flag_share": FLAG_SHARE,
        "model": model_eval,
        "rule_active_days_cut": day_cut,
        "rule": rule_eval,
        "coefficients_per_sd": dict(zip(FEATURES, map(float, coefs))),
        "test_scores": pd.DataFrame({
            "code_module": test["code_module"].values,
            "id_student": test["id_student"].values,
            "risk_score": p_test,
            "flagged": p_test >= threshold,
            "withdrew": test["withdrew"].values,
        }),
    }
