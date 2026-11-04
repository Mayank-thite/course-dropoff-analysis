# Course drop-off analysis

Built in 2026 on public data, to show the kind of retention and drop-off analysis I did at an ed-tech startup, where the data was private.

This project asks where students leave an online course, which parts are hardest, whether the first four weeks can warn us early, and how to compare two groups without fooling ourselves. The SQL runs in PostgreSQL. Python (Pandas) does the stats and charts. There are tables and DAX measures for Power BI, and a small HTML dashboard.

![Withdrawals by week](docs/img/withdrawal_weeks.png)

## The questions

1. **Where do students drop off?** A registration-to-pass funnel for each module presentation, and the weeks in which withdrawals happen.
2. **What is hardest?** The assessments with the most non-submission and the lowest scores, and how online activity in the first weeks relates to withdrawing.
3. **Can we see it coming?** A simple early-warning model that only uses weeks 1 to 4, tested on a presentation it never saw.
4. **Does early engagement go with staying?** An A/B-style comparison with a significance test and confidence interval. It is observational, and I explain why that matters.

## Data

The [Open University Learning Analytics Dataset (OULAD)](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset), downloaded from the UCI Machine Learning Repository. It covers 7 anonymised modules, 22 presentations in 2013 and 2014, 32,593 registrations, and 10,655,280 rows of daily click counts on the online learning platform (the VLE).

Citation: Kuzilek, J., Hlosta, M. and Zdrahal, Z. (2017). Open University Learning Analytics dataset. *Scientific Data* 4, 170171. https://doi.org/10.1038/sdata.2017.171. Dataset DOI: https://doi.org/10.24432/C5KK69. License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

The raw files are about 450 MB, so they are not in the repo. `scripts/download_data.py` fetches them. `data/sample/` holds a small sample (2 modules, 100 students per presentation, VLE rows before day 28) so the pipeline runs offline. The sample is only for running the code. Its numbers are not the findings.

All days in OULAD count from the start of the presentation, so day 0 is the first day. In this repo, week 1 means days 0 to 6.

## Approach

```mermaid
flowchart LR
    A[UCI download<br/>scripts/download_data.py] --> B[(PostgreSQL<br/>sql/00_schema.sql)]
    B --> C[SQL questions<br/>sql/01 to 07]
    C --> D[Python<br/>stats, model]
    D --> E[outputs/findings.md<br/>results.json, CSVs]
    D --> F[docs/img charts]
    E --> G[outputs/powerbi<br/>CSVs + measures.dax]
    E --> H[docs/dashboard.html]
```

| Step | File |
|---|---|
| Schema and load | `sql/00_schema.sql`, `dropoff/load.py` |
| Q1 funnel | `sql/01_funnel.sql` |
| Q1 withdrawal week | `sql/02_withdrawal_week.sql` |
| Q2 hardest assessments | `sql/03_hardest_assessments.sql` |
| Q2 to Q4 early features (one row per student) | `sql/04_early_features.sql` |
| Q2 engagement vs withdrawal | `sql/05_engagement_vs_withdrawal.sql` |
| Q4 groups | `sql/06_ab_groups.sql` |
| Power BI fact table | `sql/07_powerbi_enrolment.sql` |
| Stats, model, findings | `dropoff/stats.py`, `dropoff/model.py`, `dropoff/analysis.py` |

I ran everything on PostgreSQL 16. The SQL avoids engine-specific syntax, so it also runs on DuckDB for people who don't have Postgres. I ran the full dataset through both and got the same `findings.md`.

Every number below is copied from `outputs/findings.md`, which `dropoff/analysis.py` writes. Nothing is typed in by hand.

## How to run

I tested it with Python 3.13. With PostgreSQL running locally:

```bash
# one time: a database and user (change these to suit you)
sudo -u postgres psql -c "CREATE ROLE oulad LOGIN PASSWORD 'oulad';" -c "CREATE DATABASE oulad OWNER oulad;"

make all        # venv, download, load, analysis, charts, Power BI tables, dashboard, tests
```

The connection string defaults to `postgresql://oulad:oulad@localhost:5432/oulad`. Set `DATABASE_URL` to use another one.

No Postgres? Use DuckDB instead:

```bash
make all DB_ENGINE=duckdb
```

Offline, on the small sample (writes to `build/sample/`):

```bash
make sample
make test
```

On my machine `make all` runs in under a minute once the data is downloaded.

## Findings

### 1. Where students drop off

![Funnel](docs/img/funnel.png)

| Stage | Students | Of previous stage | Of registered |
|---|---|---|---|
| Registered | 32,593 | | |
| Still registered on day 0 | 29,915 | 91.8% | 91.8% |
| Still registered at day 28 | 27,553 | 92.1% | 84.5% |
| Finished (did not withdraw) | 22,429 | 81.4% | 68.8% |
| Passed | 15,385 | 68.6% | 47.2% |

- 10,063 withdrawals have a recorded day. 2,676 of them (26.6%) happened before the course even started. Another 2,356 (23.4%) happened in weeks 1 to 4.
- After the start, the busiest week is week 2, with 1,068 withdrawals. Then it settles into a long, low tail. The median withdrawal after the start is in week 10.
- Finish rates vary a lot by course. The lowest is CCC 2014B at 53.6%. The highest is GGG 2013J at 93.1%.

What I take from it: a lot of the loss happens before or right at the start. That points to onboarding and the first two weeks as the place to act, not the final exam.

### 2. What is hardest

Non-submission here means a student was still registered on the due day but sent nothing. I left exams out, because OULAD does not include exam results for several modules.

Highest non-submission, out of 182 assessments:

| Presentation | Assessment | Due day | Non-submission |
|---|---|---|---|
| GGG 2013J | CMA 37423 | 229 | 47.0% of 887 |
| CCC 2014B | TMA 24284 | 151 | 46.9% of 1,154 |
| CCC 2014B | TMA 24285 | 200 | 46.7% of 1,094 |
| GGG 2014B | CMA 37433 | 222 | 46.2% of 733 |
| CCC 2014B | TMA 24283 | 102 | 45.4% of 1,262 |

- Skipping grows through a course. Average non-submission is 10.1% on the first assessment of a presentation and 30.3% on the last one.
- The lowest average score is BBB 2014J TMA 15020, due on day 19, with a mean of 59.1 and 40.9% of submissions below the pass mark of 40. That is an early assessment, so it is a good candidate for a closer look at the material before it.

![Engagement vs withdrawal](docs/img/engagement_vs_withdrawal.png)

Among students still registered at day 28, withdrawal falls as week 1 to 4 clicks rise:

| VLE clicks in weeks 1 to 4 | Students | Withdrew later |
|---|---|---|
| Zero | 1,249 | 24.3% |
| 1 to 79 | 6,608 | 21.0% |
| 80 to 188 | 6,593 | 20.4% |
| 189 to 383 | 6,542 | 17.8% |
| 384 to 6,084 | 6,561 | 14.0% |

The pattern is real but gentler than I expected. Even the most active quarter still withdraws at 14.0%.

### 3. Early warning from the first four weeks

I trained a logistic regression on five features from weeks 1 to 4: total clicks, clicks in weeks 3 and 4, active days, early assessments missed, and clicks before the start. It uses no demographics. I trained on 2013B, 2013J and 2014B (18,334 students) and tested on 2014J (9,219 students), which is like using last year's model on a new intake. The flag cut-off was set on the training data so that 20% of students get flagged.

| | Flagged | Precision | Recall |
|---|---|---|---|
| Logistic regression, top 20% | 1,783 | 31.2% | 31.2% |
| Simple rule: active on 4 or fewer days | 1,981 | 26.9% | 29.8% |

- The base withdrawal rate in 2014J is 19.4%. The model's flagged group withdraws at 1.61 times that rate.
- AUC is 0.599. That is weak. Clicks in the first month only tell part of the story.
- The highest-risk tenth of students withdraws at 40.6%, against 13.6% for the lowest tenth.
- The strongest features are missed early assessments (+0.39 per standard deviation) and active days (-0.25). The clicks in weeks 3 and 4 get a positive weight (+0.17) only because they overlap with active days, so I would not read single coefficients on their own.

![Risk deciles](docs/img/risk_deciles.png)

My honest read: this is useful as a short call list for an advisor team, not as a verdict on a student. Most withdrawals still come from students who look fine in month one. A simple "who has barely logged in" rule gets most of the way there and is easier to explain.

### 4. Observational A/B: opened the VLE before the start vs not

Group A opened the online platform at least once before day 0. Group B did not. Both groups were still registered on day 0.

| | Students | Withdrew | Passed |
|---|---|---|---|
| A: opened VLE before start | 23,370 | 22.8% | 56.4% |
| B: did not | 6,545 | 32.9% | 33.8% |

- Withdrawal difference (A minus B): -10.1 points, 95% CI -11.4 to -8.9, two-proportion z = -16.7, p = 6.2e-63.
- Pass difference: 22.6 points, 95% CI 21.3 to 23.9.
- Inside each module, A withdraws less in 7 of 7 modules, and the gap is significant at 5% in 6 of them. AAA is the exception, with only 48 students in group B.

![A/B by module](docs/img/ab_by_module.png)

**Why this is not a real experiment.** Students chose their own group. Keen students both log in early and stay, so the gap mixes the effect of logging in with who the students are. Registration timing is another confounder: someone who registers the day before the start has little chance to log in early. Checking inside each module removes one confounder (course mix) but not the others. The p-value only says the gap is unlikely to be noise. It does not say that getting students to log in early would cut withdrawals by 10 points. To find that out, I would randomise something, for example a pre-start welcome email to half of new registrants, and compare withdrawal between the two halves.

## Power BI

I can't build a .pbix file on Linux, so the repo has what you need to build one:

- `outputs/powerbi/`: four tidy CSV tables (enrolments, assessments, presentations, 2014J risk scores)
- `outputs/powerbi/measures.dax`: the DAX measures for a retention dashboard (funnel stages, finish rate, withdrawals by week, non-submission rate, flag precision and recall)
- `docs/powerbi.md`: how to load the tables, set the relationships and lay out the pages

There is also a self-contained HTML version, `docs/dashboard.html`, with no external scripts.

## Tests

`make test` runs pytest on a six-student fixture in `tests/fixtures/`, where I worked out every answer by hand. The tests check the funnel stages, withdrawal weeks, the non-submission logic (including late submissions and exams), the early-feature window, the A/B grouping, the z-test and confidence interval, and that the model really holds out its test presentation. They run on DuckDB, so they need no database server.

## Limitations

- The data is from a UK distance-learning university in 2013 and 2014. Students, courses and platforms have changed since then, and a paid online course may behave differently.
- Modules are anonymised, so I can't say what a "hard" assessment was about. Clicks are counts, not time spent or what was read.
- A withdrawal is only dated if the student formally unregistered. 93 withdrawn students have no date and are left out of the weekly view.
- One FFF record has an unregistration day after the module ended (week 64). It is in the data but off the weekly chart.
- The early-warning model is tested on one presentation. A different year could give different numbers.
- With samples this large, very small gaps become "significant". The confidence intervals are the better guide to size.

## Repo layout

```
sql/            schema and one file per question (PostgreSQL and DuckDB)
dropoff/        Python package: db layer, stats, model, charts, exports
scripts/        download_data.py, make_sample.py
data/sample/    small sample for offline runs (raw data is downloaded to data/raw/)
outputs/        query results, results.json, findings.md, powerbi/
docs/           charts, dashboard.html, powerbi.md
tests/          pytest with a hand-checked fixture
```

## License

Code: MIT, see `LICENSE`. Data: OULAD by The Open University, CC BY 4.0. The sample in `data/sample/` and the tables in `outputs/` are derived from it.
