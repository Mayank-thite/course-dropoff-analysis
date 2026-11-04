"""Make the README charts from outputs/: python -m dropoff.charts

Light background for GitHub. The amber and blue are darker versions of the
dashboard's accent and cool colours, so they keep their contrast on white.
"""
from __future__ import annotations

import json
import logging

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402

log = logging.getLogger(__name__)

SURFACE = "#fcfcfb"
INK = "#14161c"
INK_2 = "#4a5060"
GRID = "#e3e5ea"
AMBER = "#B8741A"   # highlight series
BLUE = "#2F6FB5"    # second series
GRAY = "#a4abbd"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 11, "axes.titlesize": 13, "axes.titleweight": "normal",
    "axes.titlelocation": "left", "axes.titlepad": 12, "axes.spines.top": False,
    "axes.spines.right": False, "axes.spines.left": False, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
    "xtick.labelsize": 10, "ytick.labelsize": 10, "axes.labelsize": 10,
})


def _save(fig: plt.Figure, name: str) -> None:
    out = config.DOCS_DIR / "img"
    out.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out / name, dpi=150)
    plt.close(fig)


def funnel(results: dict) -> None:
    stages = results["q1"]["funnel_overall"]
    labels = {"registered": "Registered", "started": "Not withdrawn by day 0",
              "past_week4": "Not withdrawn by day 28", "finished": "Finished (did not withdraw)",
              "passed": "Passed"}
    passed = stages[-1]["of_registered"]
    fig, ax = plt.subplots(figsize=(8.5, 3.6))
    names = [labels[s["stage"]] for s in stages][::-1]
    vals = [s["students"] for s in stages][::-1]
    colors = [AMBER] + [BLUE] * (len(vals) - 1)
    ax.barh(names, vals, color=colors, height=0.6)
    for i, s in enumerate(stages[::-1]):
        ax.text(s["students"] + 300, i, f"{s['students']:,}  ({100 * s['of_registered']:.1f}%)",
                va="center", color=INK_2, fontsize=10)
    ax.set_xlim(0, max(vals) * 1.32)
    ax.xaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", visible=False)
    ax.set_title(f"Fewer than half of registrations end in a pass ({100 * passed:.1f}%)")
    ax.set_xlabel("Registrations, all 22 presentations")
    _save(fig, "funnel.png")


def withdrawal_weeks(results: dict) -> None:
    q1 = results["q1"]
    w = pd.read_csv(config.OUT_DIR / "withdrawals_by_week_total.csv")
    before = int(w.loc[w["week"] <= 0, "withdrawals"].sum())
    # One FFF record has an unregistration day past the end of the module (week 64). Off the axis.
    after = w[(w["week"] >= 1) & (w["week"] <= 40)]
    fig, ax = plt.subplots(figsize=(9, 3.8))
    ax.bar([0], [before], color=AMBER, width=0.8)
    ax.bar(after["week"], after["withdrawals"], color=[AMBER if wk <= 4 else BLUE for wk in after["week"]], width=0.8)
    top = int(after["week"].max())
    ax.set_xticks([0] + list(range(5, top + 1, 5)))
    ax.set_xticklabels(["Before\nstart"] + [str(x) for x in range(5, top + 1, 5)])
    ax.text(0, before + 40, f"{before:,}", ha="center", color=INK_2, fontsize=10)
    peak = after.loc[after["withdrawals"].idxmax()]
    ax.annotate(f"Week {int(peak['week'])}: {int(peak['withdrawals']):,}", (peak["week"], peak["withdrawals"]),
                xytext=(peak["week"] + 3, peak["withdrawals"] - 50), color=INK_2, fontsize=10)
    ax.grid(axis="x", visible=False)
    share = 100 * (q1["withdrawals_before_start_share"] + q1["withdrawals_weeks_1_4_share"])
    ax.set_title(f"{share:.0f}% of dated withdrawals happen before the start or in weeks 1 to 4")
    ax.set_xlabel("Week of the presentation (week 1 = days 0 to 6)")
    ax.set_ylabel("Students withdrawing")
    _save(fig, "withdrawal_weeks.png")


def engagement() -> None:
    e = pd.read_csv(config.OUT_DIR / "engagement_vs_withdrawal.csv")
    names = ["Zero" if b == 0 else f"Q{b}\n{int(lo)}-{int(hi)}"
             for b, lo, hi in zip(e["bucket"], e["min_clicks"], e["max_clicks"], strict=True)]
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.bar(names, 100 * e["withdrawal_rate"], color=[GRAY] * (len(e) - 1) + [BLUE], width=0.6)
    for i, r in enumerate(e["withdrawal_rate"]):
        ax.text(i, 100 * r + 0.4, f"{100 * r:.1f}%", ha="center", color=INK_2, fontsize=10)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, 100 * e["withdrawal_rate"].max() * 1.2)
    ax.set_ylabel("Withdrew later (%)")
    ax.set_xlabel("VLE clicks in weeks 1 to 4 (zero, then quartiles of the rest)")
    hi, lo = 100 * e["withdrawal_rate"].iloc[-1], 100 * e["withdrawal_rate"].iloc[0]
    ax.set_title(f"Even the most active quarter withdraws at {hi:.1f}% (zero clicks: {lo:.1f}%)")
    _save(fig, "engagement_vs_withdrawal.png")


def risk_deciles() -> None:
    s = pd.read_csv(config.OUT_DIR / "early_warning_test_scores.csv")
    s["decile"] = pd.qcut(s["risk_score"].rank(method="first"), 10, labels=range(1, 11))
    d = s.groupby("decile", observed=True)["withdrew"].mean() * 100
    base = s["withdrew"].mean() * 100
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.bar(d.index.astype(int), d.values, color=[BLUE] * 8 + [AMBER] * 2, width=0.6)
    ax.axhline(base, color=INK_2, linewidth=1, linestyle="--")
    ax.text(0.6, base + 0.8, f"Base rate {base:.1f}%", color=INK_2, fontsize=10)
    ax.set_xticks(range(1, 11))
    ax.grid(axis="x", visible=False)
    ax.set_xlabel("Risk score decile, logistic regression (1 = lowest risk)")
    ax.set_ylabel("Withdrew (%)")
    ax.set_title(f"Held-out {config.TEST_PRESENTATION}: the top two deciles withdraw at "
                 f"{d.loc[[9, 10]].mean():.1f}% on average")
    _save(fig, "risk_deciles.png")


def ab_adjusted(results: dict) -> None:
    adj = results["q4"]["adjusted"]
    rows = [("No controls (raw gap)", adj["raw_diff"], None, None)] + [
        (s["controls"], s["ame"], s["ci_low"], s["ci_high"]) for s in adj["steps"]
    ]
    fig, ax = plt.subplots(figsize=(8, 3.4))
    for i, (_, v, lo, hi) in enumerate(rows):
        if lo is not None:
            ax.plot([100 * lo, 100 * hi], [i, i], color=BLUE, linewidth=2, solid_capstyle="round")
        ax.scatter([100 * v], [i], color=AMBER if i == 0 else BLUE, s=70, zorder=3,
                   edgecolor=SURFACE, linewidth=2)
        right = 100 * (hi if hi is not None else v)
        ax.text(right + 0.5, i, f"{100 * v:.1f}", va="center", color=INK_2, fontsize=10)
    ax.axvline(0, color=INK_2, linewidth=1)
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels([r[0] for r in rows])
    ax.invert_yaxis()
    ax.set_xlim(min(100 * r[2] for r in rows[1:]) - 3, 2)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Withdrawal, group A minus group B (percentage points, 95% CI)")
    ax.set_title("Adding controls makes the gap bigger, not smaller")
    _save(fig, "ab_adjusted.png")


def main() -> None:
    results = json.loads((config.OUT_DIR / "results.json").read_text())
    funnel(results)
    withdrawal_weeks(results)
    engagement()
    risk_deciles()
    ab_adjusted(results)
    log.info("charts written to %s", config.DOCS_DIR / "img")


if __name__ == "__main__":
    config.setup_logging()
    main()
