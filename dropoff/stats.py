"""Small, dependency-light statistics helpers. Each one is unit tested."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
from scipy import stats


def rate(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else float("nan")


def two_proportion_test(x1: int, n1: int, x2: int, n2: int, alpha: float = 0.05) -> dict:
    """Two-sided z-test for p1 - p2 (pooled SE) with a Wald CI (unpooled SE)."""
    p1, p2 = x1 / n1, x2 / n2
    diff = p1 - p2
    pooled = (x1 + x2) / (n1 + n2)
    se_pooled = math.sqrt(pooled * (1 - pooled) * (1 / n1 + 1 / n2))
    z = diff / se_pooled
    p_value = 2 * stats.norm.sf(abs(z))
    se = math.sqrt(p1 * (1 - p1) / n1 + p2 * (1 - p2) / n2)
    zc = stats.norm.ppf(1 - alpha / 2)
    return {
        "p1": p1, "p2": p2, "diff": diff, "z": z, "p_value": float(p_value),
        "ci_low": diff - zc * se, "ci_high": diff + zc * se,
    }


def holm_adjust(p_values: pd.Series) -> pd.Series:
    """Holm step-down adjusted p-values, in the same order as the input."""
    p = p_values.sort_values()
    m = len(p)
    adj = (p * (m - np.arange(m))).cummax().clip(upper=1)
    return adj.reindex(p_values.index)


def precision_recall(y_true, y_flag) -> dict:
    y_true = np.asarray(y_true).astype(bool)
    y_flag = np.asarray(y_flag).astype(bool)
    tp = int((y_true & y_flag).sum())
    fp = int((~y_true & y_flag).sum())
    fn = int((y_true & ~y_flag).sum())
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "flagged": int(y_flag.sum()),
        "precision": rate(tp, tp + fp),
        "recall": rate(tp, tp + fn),
    }


def funnel_conversion(df, stages: list[str]) -> list[dict]:
    """Step-to-step and overall conversion for a funnel table with one column per stage."""
    totals = {s: int(df[s].sum()) for s in stages}
    out = []
    for i, s in enumerate(stages):
        prev = totals[stages[i - 1]] if i else totals[s]
        out.append({
            "stage": s,
            "students": totals[s],
            "of_previous": rate(totals[s], prev),
            "of_registered": rate(totals[s], totals[stages[0]]),
        })
    return out
