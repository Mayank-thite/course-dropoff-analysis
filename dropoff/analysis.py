"""Run every SQL question, compute the stats, and write outputs/.

python -m dropoff.analysis

Writes:
  outputs/*.csv           one file per SQL query
  outputs/results.json    every number used in the README
  outputs/findings.md     the same numbers as short sentences
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config
from .db import Database
from .model import fit_and_evaluate
from .stats import funnel_conversion, rate, two_proportion_test

FUNNEL_STAGES = ["registered", "started", "past_week4", "finished", "passed"]


def q1_funnel(db: Database) -> tuple[dict, dict[str, pd.DataFrame]]:
    funnel = db.run_file("01_funnel.sql")
    weeks = db.run_file("02_withdrawal_week.sql")
    funnel["finish_rate"] = funnel["finished"] / funnel["registered"]
    funnel["first_assessment_rate"] = funnel["submitted_first_assessment"] / funnel["registered"]

    overall = funnel_conversion(funnel, FUNNEL_STAGES)
    by_week = weeks.groupby("week", as_index=False)["withdrawals"].sum()
    total_w = int(by_week["withdrawals"].sum())
    before = int(by_week.loc[by_week["week"] <= 0, "withdrawals"].sum())
    w1_4 = int(by_week.loc[by_week["week"].between(1, 4), "withdrawals"].sum())
    after_start = by_week[by_week["week"] >= 1]
    peak = after_start.loc[after_start["withdrawals"].idxmax()]
    # median week among withdrawals after the start
    expanded = np.repeat(after_start["week"].values, after_start["withdrawals"].values)

    no_date = int(db.query(
        "SELECT COUNT(*) AS n FROM student_info i JOIN student_registration r "
        "ON r.code_module = i.code_module AND r.code_presentation = i.code_presentation "
        "AND r.id_student = i.id_student "
        "WHERE i.final_result = 'Withdrawn' AND r.date_unregistration IS NULL")["n"].iloc[0])

    worst = funnel.loc[funnel["finish_rate"].idxmin()]
    best = funnel.loc[funnel["finish_rate"].idxmax()]
    res = {
        "presentations": int(len(funnel)),
        "funnel_overall": overall,
        "withdrawals_with_date": total_w,
        "withdrawals_without_date": no_date,
        "withdrawals_before_start": before,
        "withdrawals_before_start_share": rate(before, total_w),
        "withdrawals_weeks_1_4": w1_4,
        "withdrawals_weeks_1_4_share": rate(w1_4, total_w),
        "peak_week_after_start": int(peak["week"]),
        "peak_week_withdrawals": int(peak["withdrawals"]),
        "median_week_after_start": float(np.median(expanded)),
        "lowest_finish": {"module": worst["code_module"], "presentation": worst["code_presentation"],
                          "finish_rate": float(worst["finish_rate"])},
        "highest_finish": {"module": best["code_module"], "presentation": best["code_presentation"],
                           "finish_rate": float(best["finish_rate"])},
    }
    return res, {"funnel_by_presentation": funnel, "withdrawals_by_week": weeks,
                 "withdrawals_by_week_total": by_week}


def q2_hardest(db: Database) -> tuple[dict, dict[str, pd.DataFrame]]:
    a = db.run_file("03_hardest_assessments.sql")
    a = a[a["expected"] > 0].copy()
    a["non_submission_rate"] = 1 - a["submitted"] / a["expected"]
    a["below_40_share"] = a["scored_below_40"] / a["submitted"].where(a["submitted"] > 0)
    cols = ["code_module", "code_presentation", "id_assessment", "assessment_type", "due_day",
            "expected", "submitted", "non_submission_rate", "avg_score", "below_40_share"]
    top_skip = a.sort_values("non_submission_rate", ascending=False).head(5)[cols]
    low_score = a.sort_values("avg_score").head(5)[cols]

    # Is non-submission higher for later assessments? Rank each assessment within its presentation.
    a["order_in_presentation"] = a.groupby(["code_module", "code_presentation"])["due_day"].rank(method="first")
    first = a[a["order_in_presentation"] == 1]
    a["is_last"] = a["order_in_presentation"] == a.groupby(["code_module", "code_presentation"])["order_in_presentation"].transform("max")
    last = a[a["is_last"]]

    eng = db.run_file("05_engagement_vs_withdrawal.sql")
    eng["withdrawal_rate"] = eng["withdrew"] / eng["students"]
    res = {
        "assessments_ranked": int(len(a)),
        "top_non_submission": top_skip.to_dict(orient="records"),
        "lowest_avg_score": low_score.to_dict(orient="records"),
        "mean_non_submission_first_assessment": float(first["non_submission_rate"].mean()),
        "mean_non_submission_last_assessment": float(last["non_submission_rate"].mean()),
        "engagement_buckets": eng.to_dict(orient="records"),
    }
    return res, {"assessment_difficulty": a.drop(columns=["is_last"]), "engagement_vs_withdrawal": eng}


def q3_model(db: Database) -> tuple[dict, dict[str, pd.DataFrame]]:
    feats = db.query("SELECT * FROM early_features")
    out = fit_and_evaluate(feats, config.TEST_PRESENTATION)
    scores = out.pop("test_scores")
    return out, {"early_warning_test_scores": scores, "early_features": feats}


def q4_ab(db: Database) -> tuple[dict, dict[str, pd.DataFrame]]:
    g = db.run_file("06_ab_groups.sql")
    tot = g.groupby("grp")[["students", "withdrew", "passed"]].sum()
    A, B = tot.loc["A_pre_start_vle"], tot.loc["B_no_pre_start_vle"]
    withdraw = two_proportion_test(int(A.withdrew), int(A.students), int(B.withdrew), int(B.students))
    passed = two_proportion_test(int(A.passed), int(A.students), int(B.passed), int(B.students))

    # Same comparison inside each module, to check the gap is not just a module mix effect.
    rows = []
    for mod, sub in g.groupby("code_module"):
        s = sub.set_index("grp")
        t = two_proportion_test(int(s.loc["A_pre_start_vle", "withdrew"]), int(s.loc["A_pre_start_vle", "students"]),
                                int(s.loc["B_no_pre_start_vle", "withdrew"]), int(s.loc["B_no_pre_start_vle", "students"]))
        rows.append({"code_module": mod, "n_a": int(s.loc["A_pre_start_vle", "students"]),
                     "n_b": int(s.loc["B_no_pre_start_vle", "students"]), **t})
    per_mod = pd.DataFrame(rows)
    res = {
        "group_a": {"label": "opened the VLE before day 0", "students": int(A.students),
                    "withdrew": int(A.withdrew), "passed": int(A.passed)},
        "group_b": {"label": "did not open the VLE before day 0", "students": int(B.students),
                    "withdrew": int(B.withdrew), "passed": int(B.passed)},
        "withdrawal": withdraw,
        "pass": passed,
        "modules_where_a_withdraws_less": int((per_mod["diff"] < 0).sum()),
        "modules_where_a_less_and_significant": int(((per_mod["diff"] < 0) & (per_mod["p_value"] < 0.05)).sum()),
        "modules": int(len(per_mod)),
    }
    return res, {"ab_groups": g, "ab_by_module": per_mod}


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%"


def write_findings(r: dict) -> str:
    q1, q2, q3, q4 = r["q1"], r["q2"], r["q3"], r["q4"]
    f = {s["stage"]: s for s in q1["funnel_overall"]}
    lines = ["# Findings (generated by dropoff/analysis.py, do not edit by hand)", ""]
    lines.append(f"Database: {r['database']}. Rows loaded: " +
                 ", ".join(f"{t} {n:,}" for t, n in r["row_counts"].items()) + ".")
    lines.append("")
    lines += ["## Q1. Where students drop off", ""]
    lines.append(f"- Across {q1['presentations']} module presentations, {f['registered']['students']:,} registrations.")
    for s in FUNNEL_STAGES[1:]:
        lines.append(f"- {s}: {f[s]['students']:,} ({pct(f[s]['of_previous'])} of previous stage, "
                     f"{pct(f[s]['of_registered'])} of registered)")
    lines.append(f"- Withdrawals with a recorded day: {q1['withdrawals_with_date']:,}. "
                 f"Before the start: {q1['withdrawals_before_start']:,} ({pct(q1['withdrawals_before_start_share'])}). "
                 f"Weeks 1-4: {q1['withdrawals_weeks_1_4']:,} ({pct(q1['withdrawals_weeks_1_4_share'])}). "
                 f"Withdrawn with no recorded day: {q1['withdrawals_without_date']:,}.")
    lines.append(f"- After the start, the busiest week is week {q1['peak_week_after_start']} "
                 f"({q1['peak_week_withdrawals']:,} withdrawals). Median week after the start: {q1['median_week_after_start']:g}.")
    lines.append(f"- Lowest finish rate: {q1['lowest_finish']['module']} {q1['lowest_finish']['presentation']} "
                 f"({pct(q1['lowest_finish']['finish_rate'])}). Highest: {q1['highest_finish']['module']} "
                 f"{q1['highest_finish']['presentation']} ({pct(q1['highest_finish']['finish_rate'])}).")
    lines += ["", "## Q2. What is hardest", ""]
    lines.append(f"- {q2['assessments_ranked']} non-exam assessments ranked.")
    lines.append("- Highest non-submission (students still registered on the due day who sent nothing):")
    for x in q2["top_non_submission"]:
        lines.append(f"  - {x['code_module']} {x['code_presentation']} {x['assessment_type']} {x['id_assessment']} "
                     f"(day {x['due_day']}): {pct(x['non_submission_rate'])} of {x['expected']:,}")
    lines.append("- Lowest average score:")
    for x in q2["lowest_avg_score"]:
        lines.append(f"  - {x['code_module']} {x['code_presentation']} {x['assessment_type']} {x['id_assessment']} "
                     f"(day {x['due_day']}): mean {x['avg_score']:.1f}, {pct(x['below_40_share'])} below 40")
    lines.append(f"- Mean non-submission, first assessment of a presentation: {pct(q2['mean_non_submission_first_assessment'])}; "
                 f"last assessment: {pct(q2['mean_non_submission_last_assessment'])}.")
    lines.append("- Withdrawal rate by weeks 1-4 VLE clicks (students still registered at day 28):")
    for b in q2["engagement_buckets"]:
        name = "zero clicks" if b["bucket"] == 0 else f"quartile {b['bucket']} ({int(b['min_clicks'])}-{int(b['max_clicks'])} clicks)"
        lines.append(f"  - {name}: {pct(b['withdrawal_rate'])} of {b['students']:,}")
    lines += ["", "## Q3. Early warning from weeks 1-4", ""]
    m, ru = q3["model"], q3["rule"]
    lines.append(f"- Train: {', '.join(q3['train_presentations'])} ({q3['n_train']:,} students). "
                 f"Test: {q3['test_presentation']} ({q3['n_test']:,} students).")
    lines.append(f"- Test withdrawal base rate: {pct(q3['base_rate_test'])}. AUC: {q3['auc_test']:.3f}.")
    lines.append(f"- Withdrawal rate in the highest risk decile: {pct(q3['top_decile_withdrawal_rate'])}; "
                 f"lowest decile: {pct(q3['bottom_decile_withdrawal_rate'])}.")
    lines.append(f"- Lift of the model's flagged group over the base rate: {m['precision'] / q3['base_rate_test']:.2f}x.")
    lines.append(f"- Flagging the top {pct(q3['flag_share'], 0)} by risk (cut set on train): flagged {m['flagged']:,}, "
                 f"precision {pct(m['precision'])}, recall {pct(m['recall'])}.")
    lines.append(f"- Simple rule (active on {q3['rule_active_days_cut']:g} or fewer days in weeks 1-4): flagged {ru['flagged']:,}, "
                 f"precision {pct(ru['precision'])}, recall {pct(ru['recall'])}.")
    lines.append("- Coefficients (per standard deviation, positive = more likely to withdraw): " +
                 ", ".join(f"{k} {v:+.2f}" for k, v in q3["coefficients_per_sd"].items()))
    lines += ["", "## Q4. Observational A/B: opened the VLE before the start vs not", ""]
    a, b, w, p = q4["group_a"], q4["group_b"], q4["withdrawal"], q4["pass"]
    lines.append(f"- Group A ({a['label']}): {a['students']:,} students, withdrawal {pct(w['p1'])}, pass {pct(p['p1'])}.")
    lines.append(f"- Group B ({b['label']}): {b['students']:,} students, withdrawal {pct(w['p2'])}, pass {pct(p['p2'])}.")
    lines.append(f"- Withdrawal difference A - B: {100 * w['diff']:.1f} points, 95% CI {100 * w['ci_low']:.1f} to "
                 f"{100 * w['ci_high']:.1f}, z = {w['z']:.1f}, p = {w['p_value']:.2g}.")
    lines.append(f"- Pass difference A - B: {100 * p['diff']:.1f} points, 95% CI {100 * p['ci_low']:.1f} to {100 * p['ci_high']:.1f}.")
    lines.append(f"- Inside each module: A withdraws less in {q4['modules_where_a_withdraws_less']} of {q4['modules']} modules, "
                 f"significant at 5% in {q4['modules_where_a_less_and_significant']}.")
    return "\n".join(lines) + "\n"


def main() -> None:
    config.OUT_DIR.mkdir(parents=True, exist_ok=True)
    db = Database()
    db.execute_script((config.SQL_DIR / "04_early_features.sql").read_text())
    results, tables = {"database": db.engine}, {}
    results["row_counts"] = {t: int(db.query(f"SELECT COUNT(*) AS n FROM {t}")["n"].iloc[0])
                             for t in config.TABLES.values()}
    for key, fn in [("q1", q1_funnel), ("q2", q2_hardest), ("q3", q3_model), ("q4", q4_ab)]:
        res, tbls = fn(db)
        results[key] = res
        tables.update(tbls)
    db.close()

    for name, df in tables.items():
        if name == "early_features":
            continue  # large; exported in tidy form by dropoff.powerbi
        df.to_csv(config.OUT_DIR / f"{name}.csv", index=False)
    (config.OUT_DIR / "results.json").write_text(json.dumps(results, indent=2, default=str))
    findings = write_findings(results)
    (config.OUT_DIR / "findings.md").write_text(findings)
    print(findings)


if __name__ == "__main__":
    main()
