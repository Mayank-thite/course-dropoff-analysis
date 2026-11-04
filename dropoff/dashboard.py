"""Build docs/dashboard.html, a single self-contained page (inline SVG, no external scripts).

python -m dropoff.dashboard
"""
from __future__ import annotations

import html
import json

import pandas as pd

from . import config


def bar_svg(labels, values, fmt, width=640, height=220, highlight=None, value_labels=True, label_every=1):
    """Vertical bar chart as an SVG string. Native <title> elements give hover tooltips."""
    pad_l, pad_b, pad_t = 8, 34, 18
    n = len(values)
    vmax = max(values) or 1
    slot = (width - pad_l * 2) / n
    bw = max(2.0, slot * 0.72)
    parts = [f'<svg viewBox="0 0 {width} {height}" role="img" class="chart">']
    base = height - pad_b
    parts.append(f'<line x1="{pad_l}" y1="{base}" x2="{width - pad_l}" y2="{base}" class="axis"/>')
    for i, (lab, v) in enumerate(zip(labels, values)):
        h = (base - pad_t) * v / vmax
        x = pad_l + i * slot + (slot - bw) / 2
        cls = "bar muted" if highlight and highlight(i) else "bar"
        parts.append(
            f'<g><title>{html.escape(str(lab))}: {fmt(v)}</title>'
            f'<rect class="hit" x="{pad_l + i * slot:.1f}" y="{pad_t}" width="{slot:.1f}" height="{base - pad_t}"/>'
            f'<rect class="{cls}" x="{x:.1f}" y="{base - h:.1f}" width="{bw:.1f}" height="{h:.1f}" rx="2"/></g>'
        )
        if value_labels:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{base - h - 5:.1f}" class="val">{fmt(v)}</text>')
        if i % label_every == 0:
            parts.append(f'<text x="{x + bw / 2:.1f}" y="{base + 16}" class="lab">{html.escape(str(lab))}</text>')
    parts.append("</svg>")
    return "".join(parts)


def hbar_rows(rows):
    """Horizontal funnel rows built from divs."""
    top = rows[0]["students"]
    out = []
    for r in rows:
        w = 100 * r["students"] / top
        out.append(
            f'<div class="frow" title="{r["label"]}: {r["students"]:,}">'
            f'<span class="flabel">{r["label"]}</span>'
            f'<span class="ftrack"><span class="fbar" style="width:{w:.1f}%"></span></span>'
            f'<span class="fval">{r["students"]:,} <em>{100 * r["of_registered"]:.1f}%</em></span></div>'
        )
    return "".join(out)


def main() -> None:
    r = json.loads((config.OUT_DIR / "results.json").read_text())
    q1, q2, q3, q4 = r["q1"], r["q2"], r["q3"], r["q4"]
    names = {"registered": "Registered", "started": "On day 0", "past_week4": "At week 4",
             "finished": "Finished", "passed": "Passed"}
    funnel_rows = [{**s, "label": names[s["stage"]]} for s in q1["funnel_overall"]]
    f = {s["stage"]: s for s in q1["funnel_overall"]}

    w = pd.read_csv(config.OUT_DIR / "withdrawals_by_week_total.csv")
    before = int(w.loc[w["week"] <= 0, "withdrawals"].sum())
    after = w[(w["week"] >= 1) & (w["week"] <= 40)]
    wk_labels = ["Pre"] + [str(int(x)) for x in after["week"]]
    wk_vals = [before] + after["withdrawals"].astype(int).tolist()
    weeks_svg = bar_svg(wk_labels, wk_vals, lambda v: f"{v:,}", highlight=lambda i: i == 0,
                        value_labels=False, label_every=5, width=960, height=240)

    e = pd.read_csv(config.OUT_DIR / "engagement_vs_withdrawal.csv")
    e_labels = ["Zero" if b == 0 else f"Q{b}" for b in e["bucket"]]
    eng_svg = bar_svg(e_labels, (100 * e["withdrawal_rate"]).tolist(), lambda v: f"{v:.1f}%",
                      width=480, height=240, highlight=lambda i: i == 0)

    m = pd.read_csv(config.OUT_DIR / "ab_by_module.csv")
    ab_rows = "".join(
        f"<tr><td>{x.code_module}</td><td>{x.n_a:,}</td><td>{100 * x.p1:.1f}%</td><td>{x.n_b:,}</td>"
        f"<td>{100 * x.p2:.1f}%</td><td>{100 * x.diff:.1f} ({100 * x.ci_low:.1f} to {100 * x.ci_high:.1f})</td></tr>"
        for x in m.itertuples()
    )
    hard_rows = "".join(
        f"<tr><td>{x['code_module']} {x['code_presentation']}</td><td>{x['assessment_type']} {x['id_assessment']}</td>"
        f"<td>{x['due_day']}</td><td>{100 * x['non_submission_rate']:.1f}%</td><td>{x['avg_score']:.1f}</td></tr>"
        for x in q2["top_non_submission"]
    )
    mod, rule, ab = q3["model"], q3["rule"], q4["withdrawal"]

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Course Drop-off Dashboard</title>
<style>
:root {{
  color-scheme: light;
  --bg: #f5f4f1; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --ink-3: #7a7974;
  --line: #e4e3df; --series-1: #2a78d6; --muted: #a3a29c;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    color-scheme: dark;
    --bg: #111110; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --ink-3: #9a9990;
    --line: #33332f; --series-1: #3987e5; --muted: #6b6a64;
  }}
}}
:root[data-theme="dark"] {{
  color-scheme: dark;
  --bg: #111110; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --ink-3: #9a9990;
  --line: #33332f; --series-1: #3987e5; --muted: #6b6a64;
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
main {{ max-width: 1040px; margin: 0 auto; padding: 32px 16px 48px; }}
h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
h2 {{ font-size: 1.05rem; margin: 0 0 4px; }}
p.sub, .note {{ color: var(--ink-2); margin: 0 0 12px; }}
.note {{ font-size: 0.85rem; }}
.grid {{ display: grid; gap: 16px; grid-template-columns: repeat(auto-fit, minmax(min(100%, 420px), 1fr)); }}
.tiles {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); margin: 20px 0; }}
.card {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 16px; min-width: 0; }}
.tile .k {{ color: var(--ink-2); font-size: 0.8rem; }}
.tile .v {{ font-size: 1.7rem; font-weight: 650; font-variant-numeric: tabular-nums; }}
.wide {{ grid-column: 1 / -1; }}
.chart {{ width: 100%; height: auto; display: block; }}
.chart .bar {{ fill: var(--series-1); }}
.chart .bar.muted {{ fill: var(--muted); }}
.chart .hit {{ fill: transparent; }}
.chart g:hover .bar {{ opacity: 0.8; }}
.chart .axis {{ stroke: var(--line); }}
.chart text {{ fill: var(--ink-2); font-size: 11px; text-anchor: middle; }}
.frow {{ display: grid; grid-template-columns: 90px 1fr 120px; align-items: center; gap: 8px; margin: 6px 0; }}
.flabel {{ color: var(--ink-2); font-size: 0.85rem; }}
.ftrack {{ background: var(--line); border-radius: 4px; height: 14px; overflow: hidden; }}
.fbar {{ display: block; height: 100%; background: var(--series-1); border-radius: 4px; }}
.fval {{ font-variant-numeric: tabular-nums; font-size: 0.85rem; text-align: right; }}
.fval em {{ color: var(--ink-3); font-style: normal; }}
.scroll {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; font-variant-numeric: tabular-nums; }}
th, td {{ text-align: left; padding: 6px 8px; border-bottom: 1px solid var(--line); white-space: nowrap; }}
th {{ color: var(--ink-2); font-weight: 600; }}
dl {{ display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 8px 0 0; font-size: 0.9rem; }}
dt {{ color: var(--ink-2); }} dd {{ margin: 0; font-variant-numeric: tabular-nums; }}
footer {{ margin-top: 24px; color: var(--ink-3); font-size: 0.8rem; }}
a {{ color: var(--series-1); }}
</style>
</head>
<body>
<main>
<h1>Course drop-off dashboard</h1>
<p class="sub">Open University Learning Analytics Dataset: 7 modules, {q1['presentations']} presentations, 2013 to 2014.
Every number on this page is generated by the repo's scripts.</p>

<section class="tiles">
  <div class="card tile"><div class="k">Registrations</div><div class="v">{f['registered']['students']:,}</div></div>
  <div class="card tile"><div class="k">Finished (not withdrawn)</div><div class="v">{100 * f['finished']['of_registered']:.1f}%</div></div>
  <div class="card tile"><div class="k">Passed</div><div class="v">{100 * f['passed']['of_registered']:.1f}%</div></div>
  <div class="card tile"><div class="k">Withdrawals before day 0</div><div class="v">{100 * q1['withdrawals_before_start_share']:.1f}%</div></div>
</section>

<section class="grid">
  <div class="card">
    <h2>Funnel</h2>
    <p class="note">Each stage is a subset of the one above. Percent of registrations.</p>
    {hbar_rows(funnel_rows)}
  </div>
  <div class="card">
    <h2>Withdrawal rate by weeks 1 to 4 VLE clicks</h2>
    <p class="note">Students still registered at day 28. Zero clicks, then quartiles of the rest.</p>
    {eng_svg}
  </div>
  <div class="card wide">
    <h2>Withdrawals by week</h2>
    <p class="note">Gray bar: before the module started. Busiest week after the start: week {q1['peak_week_after_start']} ({q1['peak_week_withdrawals']:,}).</p>
    {weeks_svg}
  </div>
  <div class="card wide">
    <h2>Highest non-submission assessments</h2>
    <p class="note">Share of students still registered on the due day who submitted nothing.</p>
    <div class="scroll"><table>
      <thead><tr><th>Presentation</th><th>Assessment</th><th>Due day</th><th>Non-submission</th><th>Mean score</th></tr></thead>
      <tbody>{hard_rows}</tbody></table></div>
  </div>
  <div class="card">
    <h2>Early warning (held-out {q3['test_presentation']})</h2>
    <p class="note">Logistic regression on weeks 1 to 4 behaviour. Flags the top {100 * q3['flag_share']:.0f}%.</p>
    <dl>
      <dt>Base rate</dt><dd>{100 * q3['base_rate_test']:.1f}%</dd>
      <dt>AUC</dt><dd>{q3['auc_test']:.3f}</dd>
      <dt>Model precision</dt><dd>{100 * mod['precision']:.1f}%</dd>
      <dt>Model recall</dt><dd>{100 * mod['recall']:.1f}%</dd>
      <dt>Rule precision</dt><dd>{100 * rule['precision']:.1f}% (active on {q3['rule_active_days_cut']:g} or fewer days)</dd>
      <dt>Rule recall</dt><dd>{100 * rule['recall']:.1f}%</dd>
    </dl>
  </div>
  <div class="card">
    <h2>Observational A/B: VLE before day 0</h2>
    <p class="note">Not an experiment. Students picked their own group.</p>
    <dl>
      <dt>Opened VLE early</dt><dd>{100 * ab['p1']:.1f}% withdrew ({q4['group_a']['students']:,})</dd>
      <dt>Did not</dt><dd>{100 * ab['p2']:.1f}% withdrew ({q4['group_b']['students']:,})</dd>
      <dt>Difference</dt><dd>{100 * ab['diff']:.1f} pts, 95% CI {100 * ab['ci_low']:.1f} to {100 * ab['ci_high']:.1f}</dd>
    </dl>
  </div>
  <div class="card wide">
    <h2>A/B by module</h2>
    <div class="scroll"><table>
      <thead><tr><th>Module</th><th>n early</th><th>Withdrew</th><th>n not early</th><th>Withdrew</th><th>Diff, pts (95% CI)</th></tr></thead>
      <tbody>{ab_rows}</tbody></table></div>
  </div>
</section>
<footer>Data: Kuzilek, Hlosta and Zdrahal (2017), Open University Learning Analytics dataset, Scientific Data 4, 170171.
CC BY 4.0, via the <a href="https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset">UCI Machine Learning Repository</a>.
Analysis by Mayank Thite.</footer>
</main>
</body>
</html>
"""
    out = config.DOCS_DIR / "dashboard.html"
    out.write_text(page)
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
