"""Adjusted versions of the observational A/B comparison.

The raw gap mixes "opened the VLE early" with who those students are and which
course they took. Here I add controls step by step and report the average
marginal effect in percentage points: the change in withdrawal probability if
every student's group flipped, holding their other columns fixed.

Standard errors are clustered by module presentation, because students in the
same presentation share a course, a tutor team and a start date.
"""
from __future__ import annotations

import logging

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

log = logging.getLogger(__name__)

CONTROLS = {
    "Module presentation only": "C(presentation)",
    "+ registration timing": "C(presentation) + C(reg_lead)",
    "+ study load and background": (
        "C(presentation) + C(reg_lead) + C(highest_education) + C(age_band) + C(imd)"
        " + C(gender) + C(disability) + C(prev_attempts) + np.log(studied_credits)"
    ),
}

REG_LEAD_BINS = [0, 14, 30, 60, 90, np.inf]
REG_LEAD_LABELS = ["1-14 days", "15-30", "31-60", "61-90", "91+"]


def ab_frame(features: pd.DataFrame) -> pd.DataFrame:
    """Same population as sql/06_ab_groups.sql, with model-ready columns."""
    keep = features["withdrawal_day_known"].astype(bool) & (features["date_registration"].astype(float) < 0)
    d = features[keep].copy()
    d["treated"] = (d["clicks_pre_start"].astype(float) > 0).astype(int)
    d["y"] = d["withdrew"].astype(int)
    d["presentation"] = d["code_module"] + "-" + d["code_presentation"]
    d["reg_lead"] = pd.cut(-d["date_registration"].astype(float), REG_LEAD_BINS, labels=REG_LEAD_LABELS)
    d["imd"] = d["imd_band"].fillna("missing")
    d["prev_attempts"] = d["num_of_prev_attempts"].astype(int).clip(upper=2)
    d["studied_credits"] = d["studied_credits"].astype(float)
    return d


def adjusted_effect(d: pd.DataFrame, controls: str) -> dict:
    """Logistic regression of withdrawal on group plus controls. Returns the AME of group."""
    groups = pd.factorize(d["presentation"])[0]
    fit = smf.logit(f"y ~ treated + {controls}", d).fit(
        disp=0, maxiter=200, cov_type="cluster", cov_kwds={"groups": groups}
    )
    me = fit.get_margeff(at="overall", dummy=True).summary_frame().loc["treated"]
    return {
        "ame": float(me["dy/dx"]),
        "ci_low": float(me["Conf. Int. Low"]),
        "ci_high": float(me["Cont. Int. Hi."]),
        "p_value": float(me["Pr(>|z|)"]),
        "odds_ratio": float(np.exp(fit.params["treated"])),
    }


def ipw_effect(d: pd.DataFrame, controls: str) -> dict:
    """Inverse probability weighting as a cross-check. Propensities clipped to 0.02 to 0.98."""
    ps = smf.logit(f"treated ~ {controls}", d).fit(disp=0, maxiter=200).predict(d).clip(0.02, 0.98)
    w = np.where(d["treated"] == 1, 1 / ps, 1 / (1 - ps))
    t = d["treated"].to_numpy() == 1
    y = d["y"].to_numpy()
    return {
        "ate": float(np.average(y[t], weights=w[t]) - np.average(y[~t], weights=w[~t])),
        "propensity_min": float(ps.min()),
        "propensity_max": float(ps.max()),
    }


def run(features: pd.DataFrame) -> dict:
    d = ab_frame(features)
    raw = float(d.loc[d["treated"] == 1, "y"].mean() - d.loc[d["treated"] == 0, "y"].mean())
    steps = []
    for name, controls in CONTROLS.items():
        steps.append({"controls": name, **adjusted_effect(d, controls)})
        log.info("A/B adjusted (%s): %.3f", name, steps[-1]["ame"])
    full = CONTROLS["+ study load and background"]
    return {
        "n": int(len(d)),
        "raw_diff": raw,
        "steps": steps,
        "ipw": ipw_effect(d, full),
        "share_of_raw_gap_left": steps[-1]["ame"] / raw,
    }
