"""Make the README charts from outputs/: python -m dropoff.charts"""
from __future__ import annotations

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from . import config  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
GRAY = "#a3a29c"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK_2, "xtick.color": INK_2, "ytick.color": INK_2,
    "text.color": INK, "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8, "axes.axisbelow": True,
})


def _save(fig, name: str) -> None:
    out = config.DOCS_DIR / "img"
    out.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(out / name, dpi=150)
    plt.close(fig)


def funnel(results: dict) -> None:
    stages = results["q1"]["funnel_overall"]
    labels = {"registered": "Registered", "started": "Still registered on day 0",
              "past_week4": "Still registered at week 4", "finished": "Finished (not withdrawn)",
              "passed": "Passed"}
    fig, ax = plt.subplots(figsize=(8, 3.6))
    names = [labels[s["stage"]] for s in stages][::-1]
    vals = [s["students"] for s in stages][::-1]
    ax.barh(names, vals, color=BLUE, height=0.6)
    for i, s in enumerate(stages[::-1]):
        ax.text(s["students"] + 300, i, f"{s['students']:,}  ({100 * s['of_registered']:.1f}%)",
                va="center", color=INK_2, fontsize=9)
    ax.set_xlim(0, max(vals) * 1.3)
    ax.grid(axis="y", visible=False)
    ax.set_title("Registration to pass, all 22 presentations")
    ax.set_xlabel("Students")
    _save(fig, "funnel.png")


def withdrawal_weeks() -> None:
    w = pd.read_csv(config.OUT_DIR / "withdrawals_by_week_total.csv")
    before = int(w.loc[w["week"] <= 0, "withdrawals"].sum())
    # One FFF record has an unregistration day past the end of the module (week 64); leave it off the axis.
    after = w[(w["week"] >= 1) & (w["week"] <= 40)]
    fig, ax = plt.subplots(figsize=(9, 3.6))
    ax.bar([0], [before], color=GRAY, width=0.8)
    ax.bar(after["week"], after["withdrawals"], color=BLUE, width=0.8)
    ax.set_xticks([0] + list(range(5, int(after["week"].max()) + 1, 5)))
    ax.set_xticklabels(["Before\nstart"] + [str(x) for x in range(5, int(after["week"].max()) + 1, 5)])
    ax.text(0, before + 40, f"{before:,}", ha="center", color=INK_2, fontsize=9)
    peak = after.loc[after["withdrawals"].idxmax()]
    ax.annotate(f"Week {int(peak['week'])}: {int(peak['withdrawals']):,}", (peak["week"], peak["withdrawals"]),
                xytext=(peak["week"] + 3, peak["withdrawals"] - 50), color=INK_2, fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_title("Withdrawals by week of the presentation")
    ax.set_xlabel("Week (week 1 = days 0 to 6)")
    ax.set_ylabel("Students withdrawing")
    _save(fig, "withdrawal_weeks.png")


def engagement() -> None:
    e = pd.read_csv(config.OUT_DIR / "engagement_vs_withdrawal.csv")
    names = ["Zero" if b == 0 else f"Q{b}\n{int(lo)}-{int(hi)}" for b, lo, hi in zip(e["bucket"], e["min_clicks"], e["max_clicks"])]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(names, 100 * e["withdrawal_rate"], color=[GRAY] + [BLUE] * (len(e) - 1), width=0.6)
    for i, r in enumerate(e["withdrawal_rate"]):
        ax.text(i, 100 * r + 0.4, f"{100 * r:.1f}%", ha="center", color=INK_2, fontsize=9)
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Withdrew later (%)")
    ax.set_xlabel("VLE clicks in weeks 1 to 4 (quartiles of students with any clicks)")
    ax.set_title("Withdrawal rate by early online activity")
    _save(fig, "engagement_vs_withdrawal.png")


def risk_deciles() -> None:
    s = pd.read_csv(config.OUT_DIR / "early_warning_test_scores.csv")
    s["decile"] = pd.qcut(s["risk_score"].rank(method="first"), 10, labels=range(1, 11))
    d = s.groupby("decile", observed=True)["withdrew"].mean() * 100
    base = s["withdrew"].mean() * 100
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(d.index.astype(int), d.values, color=BLUE, width=0.6)
    ax.axhline(base, color=INK_2, linewidth=1, linestyle="--")
    ax.text(0.6, base + 0.8, f"Base rate {base:.1f}%", color=INK_2, fontsize=9)
    ax.set_xticks(range(1, 11))
    ax.grid(axis="x", visible=False)
    ax.set_xlabel("Risk score decile (1 = lowest risk)")
    ax.set_ylabel("Withdrew (%)")
    ax.set_title(f"Held-out {config.TEST_PRESENTATION}: withdrawal rate by risk decile")
    _save(fig, "risk_deciles.png")


def ab_by_module() -> None:
    m = pd.read_csv(config.OUT_DIR / "ab_by_module.csv")
    fig, ax = plt.subplots(figsize=(7, 3.8))
    y = range(len(m))
    for i, r in m.iterrows():
        ax.plot([100 * r["p1"], 100 * r["p2"]], [i, i], color=GRID, linewidth=2, zorder=1)
    ax.scatter(100 * m["p1"], y, color=BLUE, s=60, zorder=2, label="Opened VLE before start", edgecolor=SURFACE, linewidth=2)
    ax.scatter(100 * m["p2"], y, color=ORANGE, s=60, zorder=2, label="Did not", edgecolor=SURFACE, linewidth=2)
    ax.set_yticks(list(y))
    ax.set_yticklabels(m["code_module"])
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Withdrew (%)")
    ax.set_title("Withdrawal rate by group, inside each module")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    _save(fig, "ab_by_module.png")


def main() -> None:
    results = json.loads((config.OUT_DIR / "results.json").read_text())
    funnel(results)
    withdrawal_weeks()
    engagement()
    risk_deciles()
    ab_by_module()
    print(f"Charts written to {config.DOCS_DIR / 'img'}")


if __name__ == "__main__":
    main()
