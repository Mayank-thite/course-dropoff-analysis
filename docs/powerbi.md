# Loading the model into Power BI

I built this on Linux, so there is no .pbix file in the repo. The tables and measures are ready to load in Power BI Desktop on Windows.

## 1. Get the tables

Run `make all` (or use the CSVs already committed in `outputs/powerbi/`):

| File | Grain | Use |
|---|---|---|
| `dim_presentation.csv` | one row per module presentation (22) | slicers: module, year, start month |
| `fact_enrolment.csv` | one row per registration (32,593) | funnel, withdrawal week, early activity |
| `fact_assessment.csv` | one row per non-exam assessment (182) | hardest assessments |
| `fact_risk_score_2014J.csv` | one row per student in the held-out presentation | early-warning view |

## 2. Load and relate

1. Home > Get data > Text/CSV, and load the four files.
2. In Power Query, check that `date_unregistration`, `withdrawal_week` and the click columns are Whole Number. Blank means "not applicable" (for example, a student who never withdrew), so leave blanks as null.
3. In Model view, create:
   - `dim_presentation[presentation_key]` 1 to many `fact_enrolment[presentation_key]`
   - `dim_presentation[presentation_key]` 1 to many `fact_assessment[presentation_key]`
4. `fact_risk_score_2014J` stands on its own. Relate it on `code_module` through a small module table if you want a module slicer on it.

## 3. Add the measures

Create a blank table called `_Measures`, then paste each measure from `outputs/powerbi/measures.dax` (New measure, one at a time). Format the rate measures as percentages.

## 4. Suggested pages

1. **Funnel**: a funnel visual with Registrations, Started, Past Week 4, Finished, Passed. Slicers for module and presentation.
2. **When students leave**: a column chart of Withdrawals In Week by `withdrawal_week`, plus a card for Share Withdrawn Before Start.
3. **Hard assessments**: a table of `fact_assessment` sorted by Non Submission Rate, with conditional formatting on avg_score.
4. **Early warning**: cards for Flagged Students, Flag Precision and Flag Recall, and a histogram of risk_score.

The numbers on these pages should match `outputs/findings.md`. If they don't, the relationship or a filter on the measure is the usual cause.
