# Course drop-off analysis

Built in 2026 on public data, to show the kind of retention and drop-off analysis I did at an ed-tech startup, where the data was private.

I wanted to know where students leave an online course, which parts are hardest, whether the first four weeks can warn us early, and how to compare two groups of students without fooling myself. The SQL runs in PostgreSQL (or DuckDB). Python does the stats, the model and the charts. There are tables and DAX measures for Power BI, and a small HTML dashboard.

The short version: half of all dated withdrawals happen before day 28, so onboarding matters more than the final exam. A day 28 warning model works, but only modestly (AUC 0.660), and the "students who log in early stay" gap does not shrink when I control for course and background. It gets bigger.

![Dashboard](docs/img/dashboard.png)

## Data

The [Open University Learning Analytics Dataset (OULAD)](https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset) from the UCI Machine Learning Repository. It covers 7 anonymised modules, 22 presentations in 2013 and 2014, 32,593 registrations, and 10,655,280 rows of daily click counts on the online learning platform (the VLE).

Citation: Kuzilek, J., Hlosta, M. and Zdrahal, Z. (2017). Open University Learning Analytics dataset. *Scientific Data* 4, 170171. https://doi.org/10.1038/sdata.2017.171. Dataset DOI: https://doi.org/10.24432/C5KK69. License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

All days in OULAD count from the start of the presentation, so day 0 is the first day. Week 1 means days 0 to 6.

A few data rules I apply everywhere, because the raw tables disagree with themselves in small ways:

- A student leaves on their unregistration day only if their final result is Withdrawn. 9 students marked Fail also have an unregistration day. I keep them as finishers.
- 93 withdrawn students have no unregistration day. I keep them in the early funnel stages (I can't place them), but the model and the A/B leave them out, because I can't tell if they were still enrolled at day 28.
- 234 people registered after day 0. They count in the "not withdrawn by day 0" stage, which is why I don't call it "enrolled on day 0". They are out of the A/B, since they couldn't have opened the VLE before the start.
- An assessment only "expects" a student who had registered by its due day.

## How to run

I tested it with Python 3.13 and PostgreSQL 16. With Postgres running locally:

```bash
# one time: a database and user (change these to suit you)
sudo -u postgres psql -c "CREATE ROLE oulad LOGIN PASSWORD 'oulad';" -c "CREATE DATABASE oulad OWNER oulad;"

make all        # venv, download (47 MB zip), load, analysis, charts, Power BI tables, dashboard, tests
```

The connection string defaults to `postgresql://oulad:oulad@localhost:5432/oulad`. Set `DATABASE_URL` to use another one. No Postgres? `make all DB_ENGINE=duckdb` does the same thing in a local DuckDB file.

Offline, on the small committed sample in `data/sample/` (2 modules, 100 students per presentation). Its numbers are only for checking the code runs:

```bash
make sample     # writes to build/sample/
make test
make lint
```

On my machine `make all` takes under a minute once the data is downloaded. I ran the full data through both engines and the generated `findings.md` is identical apart from the line that names the engine. Getting there needed one fix: the gradient boosting model saw rows in a different order on each engine, so I sort the feature table and turned off its random early-stopping split.

Every number below is copied from `outputs/findings.md`, which `dropoff/analysis.py` writes.

## 1. Where students drop off

![Funnel](docs/img/funnel.png)

| Stage | Students | Of previous stage | Of registered |
|---|---|---|---|
| Registered | 32,593 | | |
| Not withdrawn by day 0 | 29,917 | 91.8% | 91.8% |
| Not withdrawn by day 28 | 27,561 | 92.1% | 84.6% |
| Finished (did not withdraw) | 22,437 | 81.4% | 68.8% |
| Passed | 15,385 | 68.6% | 47.2% |

![Withdrawals by week](docs/img/withdrawal_weeks.png)

10,063 withdrawals have a recorded day. 2,676 of them (26.6%) happened before the course even started, and another 2,356 (23.4%) in weeks 1 to 4. After the start the busiest week is week 2, with 1,068 withdrawals, and then it settles into a long, low tail. Finish rates vary a lot by course: CCC 2014B is lowest at 53.6% and GGG 2013J highest at 93.1%.

So a lot of the loss happens before or right at the start. That points at onboarding and the first two weeks as the place to act.

## 2. What is hardest

Non-submission means a student had registered by the due day, hadn't withdrawn, and sent nothing. I left exams out, because OULAD has no exam results for several modules.

| Presentation | Assessment | Due day | Non-submission |
|---|---|---|---|
| GGG 2013J | CMA 37423 | 229 | 47.0% of 887 |
| CCC 2014B | TMA 24284 | 151 | 46.9% of 1,154 |
| CCC 2014B | TMA 24285 | 200 | 46.7% of 1,094 |
| GGG 2014B | CMA 37433 | 222 | 46.2% of 733 |
| CCC 2014B | TMA 24283 | 102 | 45.4% of 1,262 |

Skipping grows through a course: average non-submission is 10.1% on the first assessment of a presentation and 30.3% on the last one. Many of these students never formally withdraw. They just stop.

The lowest average score is BBB 2014J TMA 15020, due on day 19, with a mean of 59.1 and 40.9% of submissions below the pass mark of 40. It's an early assessment, so it's a good candidate for a closer look at the material before it. It also broke my first model, see below.

![Engagement vs withdrawal](docs/img/engagement_vs_withdrawal.png)

Among students still enrolled at day 28, withdrawal falls as week 1 to 4 clicks rise, from 21.9% with zero clicks to 13.9% in the top quarter. The pattern is real but gentler than I expected.

## 3. Early warning at day 28

The question: on day 28, which students still enrolled should an advisor call? I trained on 2013B, 2013J and 2014B (18,323 students) and tested on 2014J (9,127 students), like using last year's model on a new intake. The withdrawal base rate in 2014J is 18.6%, which is also what a random guess scores on PR-AUC. Each scorer flags the top 20% of students by risk, with the cut set on the training years.

| Scorer | AUC | PR-AUC | Flagged | Precision | Recall |
|---|---|---|---|---|---|
| Rule: fewest active days | 0.586 | 0.225 | 1,915 | 24.5% | 27.7% |
| Logistic regression, first version (5 features) | 0.589 | 0.262 | 1,730 | 28.5% | 29.1% |
| Logistic regression (14 features) | 0.660 | 0.325 | 1,410 | 38.2% | 31.7% |
| Gradient boosting (14 features) | 0.675 | 0.342 | 1,455 | 39.5% | 33.8% |

The first version used five click and assessment counts and got an AUC of 0.599. Two things were wrong with it. Its population included the 93 withdrawn students with no unregistration day, who were easy to spot because many of them had no clicks at all and had probably already left. Taking them out drops that model to 0.589. And it was missing what an advisor would look at: how recently a student was active, whether clicks are rising or falling, how they scored on the first assessment, when they registered and how many credits they're taking on.

The 14 features add those. Two details mattered more than I expected. Raw click counts mean different things in different modules, so I rank clicks inside each cohort. Raw scores were worse: BBB 2014J's first TMA was much harder than in earlier years, and the model flagged hundreds of BBB students for low scores who then stayed. Ranking the score inside the cohort fixed that. The top risk decile now withdraws at 41.4%. I left demographics out on purpose. I don't want a call list that picks people for who they are.

![Risk deciles](docs/img/risk_deciles.png)

Gradient boosting is a bit better than the logistic regression (PR-AUC 0.342 vs 0.325). I still use the logistic regression as the main model, because an advisor team can see why someone is on the list and the gap is small. The strongest signals are the early score rank (-0.51 per standard deviation) and missed early assessments (+0.31). The click features overlap a lot, so I wouldn't read their single coefficients.

The cut set on the training years flags only 1,410 students in 2014J instead of 20%, because 2014J's scores sit a bit lower. In practice I'd set the cut as "the top N students this week", not as a fixed probability.

My honest read: this is a useful short call list, about twice the base rate, not a verdict. Two thirds of the students who later withdraw still look fine at day 28.

## 4. Observational A/B: opened the VLE before the start vs not

Group A opened the online platform at least once before day 0. Group B did not. Both registered before day 0 and had not withdrawn by then.

| | Students | Withdrew | Passed |
|---|---|---|---|
| A: opened VLE before start | 23,314 | 22.6% | 56.5% |
| B: did not | 6,266 | 33.0% | 33.3% |

The raw withdrawal gap is -10.4 points (95% CI -11.7 to -9.1, two-proportion z = -17.0). Inside each module, A withdraws less in 7 of 7 modules and the gap is significant in 6, still 6 after Holm's correction for testing seven at once. AAA is the exception, with only 40 students in group B.

Students chose their own group, so the raw gap mixes the effect of logging in with who these students are and which course they took. I fitted a logistic regression of withdrawal on group, adding controls in steps, and report the average marginal effect. Standard errors are clustered by module presentation, since students in the same presentation share a course and a start date.

![A/B adjusted](docs/img/ab_adjusted.png)

| Controls | Gap (points) | 95% CI |
|---|---|---|
| None (raw) | -10.4 | -11.7 to -9.1 |
| Module presentation | -15.1 | -17.4 to -12.9 |
| + registration timing | -15.4 | -17.7 to -13.2 |
| + education, age, IMD band, gender, disability, previous attempts, credits | -14.5 | -16.7 to -12.3 |

Inverse probability weighting with the same controls gives -15.5 points.

I expected the gap to shrink. It grew, because the modules where most students log in early (CCC, DDD, FFF) are also the ones with the most withdrawals, which hides part of the gap in the pooled numbers. Comparing students inside the same presentation removes that.

That still doesn't make it causal. The controls are what OULAD records. Motivation, spare time and how much someone wanted the course aren't in the data, and they plausibly drive both logging in early and staying. The adjusted number says the gap isn't explained by course or background. It doesn't say that getting students to log in early would cut withdrawals by 14.5 points. To find that out I'd randomise something, for example a pre-start welcome email to half of new registrants, and compare withdrawal between the halves.

## Power BI

I can't build a .pbix file on Linux, so the repo has what you need to build one:

- `outputs/powerbi/`: four tidy CSV tables (enrolments, assessments, presentations, 2014J risk scores)
- `outputs/powerbi/measures.dax`: DAX measures for a retention dashboard (funnel stages, finish rate, withdrawals by week, non-submission rate, flag precision and recall)
- `docs/powerbi.md`: how to load the tables, set the relationships and lay out the pages

`docs/dashboard.html` is a self-contained HTML version with no scripts.

## Tests

`make test` runs pytest. The SQL tests use a nine-student fixture in `tests/fixtures/` where I worked out every answer by hand, including the awkward cases: a withdrawal with no date, a Fail with an unregistration day, a late registrant. They cover the funnel, withdrawal weeks, non-submission, the early-feature window, the A/B grouping and the portability rules. The Python tests check the z-test and Holm correction against known values, that the model really holds out its test presentation, and that the adjusted A/B removes a confounder I planted in fake data. Everything runs on DuckDB, so CI needs no database server.

## Limitations

- The data is from a UK distance-learning university in 2013 and 2014. A paid online course in 2026 may behave differently.
- Modules are anonymised, so I can't say what a "hard" assessment was about. Clicks are counts, not time spent.
- OULAD has no marking date, so the early score assumes marks were back by day 28.
- The model is tested on one presentation. Another year could give different numbers.
- One FFF record has an unregistration day after the module ended (week 64). It's in the data but off the weekly chart.

## Repo layout

```
sql/            schema and one file per question (PostgreSQL and DuckDB)
dropoff/        Python package: db layer, stats, model, causal, charts, exports
scripts/        download_data.py, make_sample.py
data/sample/    small sample for offline runs (raw data downloads to data/raw/)
outputs/        query results, results.json, findings.md, powerbi/
docs/           charts, dashboard.html, powerbi.md
tests/          pytest with a hand-checked fixture
```

## Problems I ran into

- **Students who had already left.** 93 withdrawn students had no unregistration date and were being counted as still enrolled at day 28. Most had no clicks at all. They made the early-warning model look better than it was, so I took them out of the prediction population.
- **A harder test in one year.** Raw scores flagged hundreds of BBB students as high risk who then stayed, because the first assignment in BBB 2014J was much harder than in earlier years. Ranking each score within its own course run fixed it.
- **Confounding in the A/B comparison.** Courses where most students log in early also lose more students overall, which hid part of the gap. Adding controls made the gap bigger (from 10.4 to 14.5 points), not smaller. It's still observational, not causal.
- **Two databases, one answer.** Gradient boosting gave slightly different AUCs on PostgreSQL and DuckDB because the row order differed. Sorting the features and turning off random early stopping made the findings identical on both.

## License

Code: MIT, see `LICENSE`. Data: OULAD by The Open University, CC BY 4.0. The sample in `data/sample/` and the tables in `outputs/` are derived from it.
