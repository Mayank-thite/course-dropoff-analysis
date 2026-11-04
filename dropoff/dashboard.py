"""Build docs/dashboard.html: one self-contained page, inline SVG, no scripts.

python -m dropoff.dashboard

Every number comes from outputs/results.json and the CSVs next to it.
"""
from __future__ import annotations

import html
import json
import logging
from collections.abc import Callable
from datetime import date

import pandas as pd

from . import config

log = logging.getLogger(__name__)

SOURCE_URL = "https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset"


def bar_svg(labels: list[str], values: list[float], fmt: Callable[[float], str], *, width: int = 640,
            height: int = 240, accent: Callable[[int], bool] = lambda i: False, value_labels: bool = True,
            label_every: int = 1, y_title: str = "", extra_class: str = "") -> str:
    """Vertical bars from a zero baseline. Native <title> gives a hover tooltip."""
    pad_l, pad_r, pad_b, pad_t = 8, 8, 30, 22
    n = len(values)
    vmax = max(values) or 1
    slot = (width - pad_l - pad_r) / n
    bw = max(2.0, slot * 0.7)
    base = height - pad_b
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart {extra_class}" role="img" '
             f'aria-label="{html.escape(y_title)}">']
    parts.append(f'<line x1="{pad_l}" y1="{base}" x2="{width - pad_r}" y2="{base}" class="axis"/>')
    for i, (lab, v) in enumerate(zip(labels, values, strict=True)):
        h = (base - pad_t) * v / vmax
        x = pad_l + i * slot + (slot - bw) / 2
        cls = "bar accent" if accent(i) else "bar"
        parts.append(f'<g><title>{html.escape(str(lab))}: {fmt(v)}</title>'
                     f'<rect class="hit" x="{pad_l + i * slot:.1f}" y="{pad_t}" width="{slot:.1f}" '
                     f'height="{base - pad_t}"/>'
                     f'<rect class="{cls}" x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" '
                     f'rx="2"/></g>')
        if value_labels:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{base - h - 6:.1f}" class="val">{fmt(v)}</text>')
        if i % label_every == 0:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{base + 18}" class="lab">{html.escape(str(lab))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def hbar_rows(rows: list[dict], value: Callable[[dict], float], text: Callable[[dict], str],
              accent: Callable[[dict], bool] = lambda r: False, vmax: float | None = None) -> str:
    """Horizontal bars built from divs, each with a direct label."""
    top = vmax or max(value(r) for r in rows)
    out = []
    for r in rows:
        w = 100 * value(r) / top
        cls = "fbar accent" if accent(r) else "fbar"
        out.append(f'<div class="frow"><span class="flabel">{html.escape(r["label"])}</span>'
                   f'<span class="ftrack"><span class="{cls}" style="width:{w:.1f}%"></span></span>'
                   f'<span class="fval">{text(r)}</span></div>')
    return "".join(out)


def ci_svg(rows: list[tuple[str, float, float | None, float | None]], width: int = 480) -> str:
    """Dot and 95% CI per row, in percentage points, with a zero line. Row label sits above its line."""
    row_h, pad_l, pad_r, pad_t = 56, 8, 16, 8
    height = pad_t + row_h * len(rows) + 26
    lo = min(r[2] if r[2] is not None else r[1] for r in rows) * 100 - 2
    hi = 1.0
    sx = lambda v: pad_l + (100 * v - lo) / (hi - lo) * (width - pad_l - pad_r)  # noqa: E731
    parts = [f'<svg viewBox="0 0 {width} {height}" class="chart ci" role="img" '
             'aria-label="Withdrawal gap with and without controls">']
    zero = sx(0)
    parts.append(f'<line x1="{zero:.1f}" y1="{pad_t}" x2="{zero:.1f}" y2="{height - 26}" class="axis"/>')
    parts.append(f'<text x="{zero:.1f}" y="{height - 8}" class="lab">0</text>')
    for i, (name, v, a, b) in enumerate(rows):
        top = pad_t + i * row_h
        y = top + 38
        parts.append(f'<text x="{pad_l}" y="{top + 18}" class="rowlab">{html.escape(name)}</text>')
        if a is not None:
            parts.append(f'<line x1="{sx(a):.1f}" y1="{y}" x2="{sx(b):.1f}" y2="{y}" class="whisker"/>')
        cls = "dot accent" if i == 0 else "dot"
        tip = f"{name}: {100 * v:.1f} pts" + (f" (95% CI {100 * a:.1f} to {100 * b:.1f})" if a is not None else "")
        parts.append(f'<g><title>{html.escape(tip)}</title><circle cx="{sx(v):.1f}" cy="{y}" r="6" '
                     f'class="{cls}"/></g>')
        right = sx(b if b is not None else v) + 12
        parts.append(f'<text x="{right:.1f}" y="{y + 4}" class="val start">{100 * v:.1f}</text>')
    parts.append("</svg>")
    return "".join(parts)


CSS = """
:root {
  color-scheme: dark;
  --bg: #04050A; --ink: #ECEEF3; --text-2: #A4ABBD; --body: #C9CEDA;
  --line: rgba(220,226,240,.12); --panel: #0B0D15; --accent: #FFC77A; --cool: #9CCBFF;
  --track: rgba(220,226,240,.06);
}
@media (prefers-color-scheme: light) {
  :root {
    color-scheme: light;
    --bg: #F7F7F4; --ink: #14161C; --text-2: #4A5060; --body: #2A2E38;
    --line: rgba(20,22,28,.12); --panel: #FFFFFF; --accent: #B8741A; --cool: #2F6FB5;
    --track: rgba(20,22,28,.05);
  }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body { margin: 0; background: var(--bg); color: var(--body);
  font: 300 16px/1.6 "Geist", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1080px; margin: 0 auto; padding: 56px 16px 64px; }
.mono, .eyebrow, .k, th, .flabel, .fval, footer, .chart text {
  font-family: "Geist Mono", ui-monospace, SFMono-Regular, Menlo, monospace; }
.eyebrow { font-size: 12px; letter-spacing: .08em; text-transform: uppercase; color: var(--text-2); margin: 0 0 14px; }
h1 { color: var(--ink); font-weight: 400; font-size: clamp(26px, 4vw, 38px); line-height: 1.2;
  letter-spacing: -.01em; margin: 0 0 14px; max-width: 26ch; }
h2 { color: var(--ink); font-weight: 500; font-size: 17px; margin: 0 0 4px; }
p { margin: 0 0 12px; }
.lede { max-width: 68ch; color: var(--body); }
.note { color: var(--text-2); font-size: 14px; }
.tiles { display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 220px), 1fr));
  margin: 36px 0 28px; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 20px; min-width: 0; }
.k { color: var(--text-2); font-size: 11px; letter-spacing: .08em; text-transform: uppercase; }
.v { color: var(--ink); font-size: 34px; font-weight: 300; font-variant-numeric: tabular-nums;
  margin: 6px 0 2px; line-height: 1.1; }
.v.accent { color: var(--accent); }
.tile .note { font-size: 13px; margin: 0; }
.grid { display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 440px), 1fr)); }
.wide { grid-column: 1 / -1; }
.chart { width: 100%; height: auto; display: block; margin-top: 12px; overflow: visible; }
.chart .bar { fill: var(--cool); }
.chart .accent { fill: var(--accent); }
.chart .hit { fill: transparent; }
.chart g:hover .bar { opacity: .75; }
.chart .axis { stroke: var(--line); stroke-width: 1; }
.chart .whisker { stroke: var(--cool); stroke-width: 2; stroke-linecap: round; }
.chart .dot { fill: var(--cool); stroke: var(--panel); stroke-width: 2; }
.chart .dot.accent { fill: var(--accent); }
.chart text { fill: var(--text-2); font-size: 12px; text-anchor: middle; font-variant-numeric: tabular-nums; }
.chart .start { text-anchor: start; }
.chart .rowlab { text-anchor: start; fill: var(--body); font-family: "Geist", system-ui, sans-serif; font-size: 13px; }
.frow { display: grid; grid-template-columns: minmax(0, 11rem) 1fr auto; align-items: center; gap: 10px;
  margin: 10px 0; }
.flabel { color: var(--text-2); font-size: 12px; }
.ftrack { background: var(--track); border-radius: 4px; height: 12px; overflow: hidden; }
.fbar { display: block; height: 100%; background: var(--cool); border-radius: 0 4px 4px 0; }
.fbar.accent { background: var(--accent); }
.fval { font-variant-numeric: tabular-nums; font-size: 12px; color: var(--ink); text-align: right; min-width: 7.5rem; }
.fval em { color: var(--text-2); font-style: normal; }
.scroll { overflow-x: auto; margin-top: 8px; }
.scroll:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
table { width: 100%; border-collapse: collapse; font-size: 14px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 8px 10px 8px 0; border-bottom: 1px solid var(--line); white-space: nowrap; }
th { color: var(--text-2); font-weight: 400; font-size: 11px; letter-spacing: .06em; text-transform: uppercase; }
td.num, th.num { text-align: right; }
.caveats { margin-top: 28px; }
.caveats ul { margin: 8px 0 0; padding-left: 18px; color: var(--body); font-size: 14px; max-width: 80ch; }
.caveats li { margin: 4px 0; }
footer { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--text-2);
  font-size: 12px; line-height: 1.7; }
a { color: var(--accent); text-underline-offset: 3px; }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; border-radius: 2px; }
.narrow-only { display: none; }
@media (max-width: 600px) {
  main { padding-top: 36px; }
  .wide-only { display: none; }
  .narrow-only { display: block; }
  .chart text { font-size: 18px; }
  .chart.narrow-only text { font-size: 13px; }
  .chart.ci text { font-size: 18px; }
  .chart .rowlab { font-size: 18px; }
  .frow { grid-template-columns: 1fr auto; }
  .frow .ftrack { grid-column: 1 / -1; grid-row: 2; }
  .fval { min-width: 0; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; animation: none !important; } }
"""


def main() -> None:
    r = json.loads((config.OUT_DIR / "results.json").read_text())
    q1, q2, q3, q4 = r["q1"], r["q2"], r["q3"], r["q4"]
    f = {s["stage"]: s for s in q1["funnel_overall"]}
    adj = q4["adjusted"]
    full = adj["steps"][-1]
    main_model = q3["model"]
    early_share = q1["withdrawals_before_start_share"] + q1["withdrawals_weeks_1_4_share"]

    names = {"registered": "Registered", "started": "Not withdrawn by day 0",
             "past_week4": "Not withdrawn by day 28", "finished": "Finished", "passed": "Passed"}
    funnel_html = hbar_rows(
        [{**s, "label": names[s["stage"]]} for s in q1["funnel_overall"]],
        value=lambda x: x["students"],
        text=lambda x: f'{x["students"]:,} <em>{100 * x["of_registered"]:.1f}%</em>',
        accent=lambda x: x["stage"] == "passed",
    )

    w = pd.read_csv(config.OUT_DIR / "withdrawals_by_week_total.csv")
    before = int(w.loc[w["week"] <= 0, "withdrawals"].sum())
    after = w[(w["week"] >= 1) & (w["week"] <= 40)]
    wk_labels = ["Pre"] + [str(int(x)) for x in after["week"]]
    wk_vals = [before] + after["withdrawals"].astype(int).tolist()
    # A wide version for desktop and a narrow one for phones, so labels stay readable.
    weeks_svg = (
        bar_svg(wk_labels, wk_vals, lambda v: f"{v:,.0f}", accent=lambda i: i <= 4, value_labels=False,
                label_every=5, width=960, height=260, y_title="Withdrawals by week", extra_class="wide-only")
        + bar_svg(wk_labels, wk_vals, lambda v: f"{v:,.0f}", accent=lambda i: i <= 4, value_labels=False,
                  label_every=10, width=360, height=240, y_title="Withdrawals by week", extra_class="narrow-only")
    )

    e = pd.read_csv(config.OUT_DIR / "engagement_vs_withdrawal.csv")
    eng_svg = bar_svg(["Zero" if b == 0 else f"Q{b}" for b in e["bucket"]],
                      (100 * e["withdrawal_rate"]).tolist(), lambda v: f"{v:.1f}%", width=480, height=240,
                      y_title="Withdrawal rate by weeks 1 to 4 clicks")

    scorer_html = hbar_rows(
        [{"label": s["name"].replace("Logistic regression", "Logistic").replace(" (14 features)", ", 14 features")
          .replace(", first version (5 features)", ", first version"), **s} for s in q3["scorers"]]
        + [{"label": "Random guess", "pr_auc": q3["base_rate_test"], "auc": 0.5}],
        value=lambda x: x["pr_auc"],
        text=lambda x: f'{x["pr_auc"]:.3f} <em>AUC {x["auc"]:.3f}</em>',
        accent=lambda x: x["label"].startswith("Logistic, 14"),
        vmax=0.4,
    )

    ci_rows = [("No controls (raw gap)", adj["raw_diff"], None, None)] + [
        (s["controls"], s["ame"], s["ci_low"], s["ci_high"]) for s in adj["steps"]]
    ab_svg = ci_svg(ci_rows)

    hard_rows = "".join(
        f"<tr><td>{x['code_module']} {x['code_presentation']}</td><td>{x['assessment_type']} {x['id_assessment']}</td>"
        f"<td class='num'>{x['due_day']}</td><td class='num'>{100 * x['non_submission_rate']:.1f}%</td>"
        f"<td class='num'>{x['expected']:,}</td></tr>"
        for x in q2["top_non_submission"]
    )

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Course Drop-off Dashboard</title>
<meta name="description" content="Where students leave online courses, on public OULAD data.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500&family=Geist+Mono:wght@400;500&display=swap"
  rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<main>
<p class="eyebrow">Course drop-off analysis / OULAD 2013 to 2014</p>
<h1>{100 * early_share:.0f}% of withdrawals happen before the course starts or in its first four weeks</h1>
<p class="lede">I followed {f['registered']['students']:,} registrations across {q1['presentations']} presentations of
7 Open University modules to see where students leave, and whether the first month can warn us.
Rebuilt in 2026 on public data. Every number here is written by the repo's pipeline.</p>

<section class="tiles" aria-label="Headline numbers">
  <div class="card tile"><div class="k">Pass rate</div><div class="v">{100 * f['passed']['of_registered']:.1f}%</div>
    <p class="note">of all registrations, 2013 to 2014</p></div>
  <div class="card tile"><div class="k">Early withdrawals</div><div class="v accent">{100 * early_share:.1f}%</div>
    <p class="note">of {q1['withdrawals_with_date']:,} dated withdrawals fall before day 28</p></div>
  <div class="card tile"><div class="k">Early-warning recall</div>
    <div class="v">{100 * main_model['recall']:.1f}%</div>
    <p class="note">of later withdrawals caught, flagging {main_model['flagged']:,} of {q3['n_test']:,} students
    at day 28 ({q3['test_presentation']})</p></div>
  <div class="card tile"><div class="k">Pre-start login gap</div><div class="v">{100 * full['ame']:.1f} pts</div>
    <p class="note">withdrawal, after controls. Observational, not causal</p></div>
</section>

<section class="grid">
  <div class="card wide">
    <h2>Withdrawals by week of the presentation</h2>
    <p class="note">Amber: before the start and weeks 1 to 4. Busiest week after the start: week
    {q1['peak_week_after_start']} ({q1['peak_week_withdrawals']:,}). {q1['withdrawals_without_date']} withdrawals have
    no date and are not shown.</p>
    {weeks_svg}
  </div>
  <div class="card">
    <h2>Registration to pass</h2>
    <p class="note">Each stage is inside the one above. Share of all registrations.</p>
    {funnel_html}
  </div>
  <div class="card">
    <h2>Withdrawal by clicks in weeks 1 to 4</h2>
    <p class="note">Students still enrolled at day 28. Zero clicks, then quartiles of the rest.</p>
    {eng_svg}
  </div>
  <div class="card">
    <h2>Early warning on a new intake</h2>
    <p class="note">Trained on 2013B to 2014B, tested on {q3['n_test']:,} students in {q3['test_presentation']}.
    Bar is PR-AUC (higher is better). Random guessing scores the base rate,
    {100 * q3['base_rate_test']:.1f}%.</p>
    {scorer_html}
  </div>
  <div class="card">
    <h2>Opened the VLE before day 0: gap in withdrawal</h2>
    <p class="note">Group A minus group B, percentage points with 95% CI. Logistic regression, errors clustered by
    presentation, n = {adj['n']:,}. Adding controls makes the gap bigger.</p>
    {ab_svg}
  </div>
  <div class="card wide">
    <h2>Assessments most often skipped</h2>
    <p class="note">Students enrolled on the due day who sent nothing. Exams left out.</p>
    <div class="scroll" tabindex="0" role="region" aria-label="Assessments table"><table>
      <thead><tr><th>Presentation</th><th>Assessment</th><th class="num">Due day</th>
      <th class="num">Not submitted</th><th class="num">Expected</th></tr></thead>
      <tbody>{hard_rows}</tbody></table></div>
  </div>
</section>

<section class="caveats">
  <h2>Before you act on this</h2>
  <ul>
    <li>The A/B is observational. Students picked their own group, so motivation I can't measure could explain
    all of the gap. A randomised pre-start email would answer it.</li>
    <li>The early-warning model is weak. At day 28 most later withdrawals still look like everyone else, so I'd
    use it for a short advisor call list, not a verdict on anyone.</li>
    <li>2013 to 2014 data from one UK distance-learning university. Modules are anonymised.</li>
  </ul>
</section>

<footer>
  As of {date.today():%Y-%m-%d}. Data: Kuzilek, Hlosta and Zdrahal (2017), Open University Learning Analytics
  dataset, CC BY 4.0, via the <a href="{SOURCE_URL}">UCI Machine Learning Repository</a>.
  Analysis by Mayank Thite.
</footer>
</main>
</body>
</html>
"""
    out = config.DOCS_DIR / "dashboard.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    log.info("wrote %s", out)


if __name__ == "__main__":
    config.setup_logging()
    main()
