"""Early-warning model built on what is known at day 28.

I train on the three earlier presentations and test on the last one (2014J), so
the test looks like using last year's model on a new intake. Three scorers are
compared on the same held-out students: a one-line rule, a logistic regression
and a gradient-boosted tree model.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .config import FLAG_SHARE, SEED
from .stats import precision_recall

log = logging.getLogger(__name__)

# What the first version used. Kept so the README can show what the new features add.
BASELINE_FEATURES = [
    "log_clicks_w1_4",
    "log_clicks_w3_4",
    "active_days_w1_4",
    "early_assessments_missed",
    "log_clicks_pre_start",
]

# Behaviour in weeks 1 to 4, plus registration timing and study load.
# No demographics: I don't want a call list that targets people for who they are.
FEATURES = [
    "log_clicks_w1_4",
    "click_trend",
    "active_days_w1_4",
    "active_days_w3_4",
    "days_since_active",
    "click_rank_in_presentation",
    "log_clicks_pre_start",
    "early_assessments_due",
    "early_assessments_missed",
    "has_early_score",
    "early_score_rank_in_presentation",
    "days_registered_before_start",
    "log_studied_credits",
    "num_of_prev_attempts",
]


def model_population(features: pd.DataFrame) -> pd.DataFrame:
    """Students still enrolled at day 28 whose withdrawal day (if any) is known.

    Students who registered after day 27 have no week 1 to 4 behaviour at all, so
    they are out too.
    """
    keep = (
        features["registered_at_day28"].astype(bool)
        & features["withdrawal_day_known"].astype(bool)
        & ~(features["date_registration"].astype(float) > 27)
    )
    return features[keep].copy()


def build_xy(features: pd.DataFrame) -> pd.DataFrame:
    """Add the model columns. Every input is known by day 28."""
    df = model_population(features)
    num = lambda c: df[c].astype(float)  # noqa: E731
    df["log_clicks_w1_4"] = np.log1p(num("clicks_w1_4"))
    df["log_clicks_w3_4"] = np.log1p(num("clicks_w3_4"))
    df["log_clicks_pre_start"] = np.log1p(num("clicks_pre_start"))
    # positive = more clicks in weeks 3 and 4 than in weeks 1 and 2
    df["click_trend"] = df["log_clicks_w3_4"] - np.log1p(num("clicks_w1_2"))
    # 28 if never active in the window
    df["days_since_active"] = 27 - df["last_active_day"].astype(float).fillna(-1)
    # Clicks mean different things in different modules, so rank inside the cohort.
    # This only uses the same cohort at day 28, so it is available at prediction time.
    df["click_rank_in_presentation"] = (
        df.groupby(["code_module", "code_presentation"])["clicks_w1_4"].rank(pct=True)
    )
    # Score on assessments due by day 27, ranked inside the cohort. Raw scores aren't
    # comparable: BBB 2014J's first TMA was much harder than in earlier years, and raw
    # scores made the model flag hundreds of BBB students who then stayed.
    # Students with no score get 0 plus a flag, so the flag carries "nothing to mark".
    df["has_early_score"] = df["early_avg_score"].notna().astype(float)
    df["early_score_rank_in_presentation"] = (
        df.groupby(["code_module", "code_presentation"])["early_avg_score"].rank(pct=True).fillna(0.0)
    )
    reg = -num("date_registration")
    df["days_registered_before_start"] = reg.fillna(reg.median())
    df["log_studied_credits"] = np.log(num("studied_credits"))
    for c in ["active_days_w1_4", "active_days_w3_4", "early_assessments_due",
              "early_assessments_missed", "num_of_prev_attempts"]:
        df[c] = num(c)
    df["withdrew"] = df["withdrew"].astype(bool)
    return df


def _logit() -> object:
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))


def _boosted() -> HistGradientBoostingClassifier:
    return HistGradientBoostingClassifier(
        max_iter=200, learning_rate=0.05, max_leaf_nodes=15, min_samples_leaf=100,
        early_stopping=False, random_state=SEED,
    )


def _score(name: str, y_test: pd.Series, p_test: np.ndarray, p_train: np.ndarray) -> dict:
    """AUC, PR-AUC and precision/recall when flagging FLAG_SHARE (cut set on train)."""
    threshold = float(np.quantile(p_train, 1 - FLAG_SHARE))
    return {
        "name": name,
        "auc": float(roc_auc_score(y_test, p_test)),
        "pr_auc": float(average_precision_score(y_test, p_test)),
        "threshold": threshold,
        **precision_recall(y_test, p_test >= threshold),
    }


def fit_and_evaluate(features: pd.DataFrame, test_presentation: str) -> dict:
    """Fit on every presentation except test_presentation and score that one."""
    df = build_xy(features)
    train = df[df["code_presentation"] != test_presentation]
    test = df[df["code_presentation"] == test_presentation]
    y_tr, y_te = train["withdrew"], test["withdrew"]
    log.info("train %d students, test %d students", len(train), len(test))

    results = []
    # Rule: fewest active days in weeks 1 to 4. Negated so higher = riskier.
    results.append(_score("Rule: fewest active days", y_te,
                          -test["active_days_w1_4"].to_numpy(), -train["active_days_w1_4"].to_numpy()))

    base = _logit().fit(train[BASELINE_FEATURES], y_tr)
    results.append(_score("Logistic regression, first version (5 features)", y_te,
                          base.predict_proba(test[BASELINE_FEATURES])[:, 1],
                          base.predict_proba(train[BASELINE_FEATURES])[:, 1]))

    logit = _logit().fit(train[FEATURES], y_tr)
    p_test = logit.predict_proba(test[FEATURES])[:, 1]
    results.append(_score("Logistic regression (14 features)", y_te, p_test,
                          logit.predict_proba(train[FEATURES])[:, 1]))

    gb = _boosted().fit(train[FEATURES], y_tr)
    results.append(_score("Gradient boosting (14 features)", y_te,
                          gb.predict_proba(test[FEATURES])[:, 1],
                          gb.predict_proba(train[FEATURES])[:, 1]))

    main = results[2]
    decile = pd.qcut(pd.Series(p_test).rank(method="first"), 10, labels=False).to_numpy() + 1
    coefs = logit.named_steps["logisticregression"].coef_[0]
    return {
        "train_presentations": sorted(train["code_presentation"].unique().tolist()),
        "test_presentation": test_presentation,
        "n_train": int(len(train)),
        "n_test": int(len(test)),
        "base_rate_test": float(y_te.mean()),
        "flag_share": FLAG_SHARE,
        "scorers": results,
        "auc_test": main["auc"],
        "pr_auc_test": main["pr_auc"],
        "model": main,
        "top_decile_withdrawal_rate": float(y_te.to_numpy()[decile == 10].mean()),
        "bottom_decile_withdrawal_rate": float(y_te.to_numpy()[decile == 1].mean()),
        "decile_withdrawal_rates": [float(y_te.to_numpy()[decile == k].mean()) for k in range(1, 11)],
        "coefficients_per_sd": dict(zip(FEATURES, map(float, coefs), strict=True)),
        "test_scores": pd.DataFrame({
            "code_module": test["code_module"].to_numpy(),
            "id_student": test["id_student"].to_numpy(),
            "risk_score": p_test,
            "flagged": p_test >= main["threshold"],
            "withdrew": y_te.to_numpy(),
        }),
    }
