"""Check the SQL logic against a six-student fixture where every answer is known.

Fixture (module XXX, 2014J, 100 days):
  1 Pass        never unregistered, both assessments on time, VLE before and during weeks 1-4
  2 Distinction never unregistered, both assessments
  3 Fail        never unregistered, first assessment submitted late (day 30), no VLE
  4 Withdrawn   unregistered day 10 (week 2)
  5 Withdrawn   unregistered day -3 (before the start)
  6 Withdrawn   unregistered day 40 (week 6), first assessment submitted
"""
from dropoff.db import read_sql


def test_row_counts(db):
    assert db.query("SELECT COUNT(*) AS n FROM student_info")["n"][0] == 6
    # "?" is loaded as NULL
    assert db.query("SELECT COUNT(*) AS n FROM student_registration WHERE date_unregistration IS NULL")["n"][0] == 3
    assert db.query("SELECT COUNT(*) AS n FROM assessments WHERE date IS NULL")["n"][0] == 1


def test_funnel(db):
    f = db.run_file("01_funnel.sql").iloc[0]
    assert f["registered"] == 6
    assert f["started"] == 5          # student 5 left before day 0
    assert f["past_week4"] == 4       # student 4 left on day 10
    assert f["finished"] == 3         # 1, 2, 3
    assert f["passed"] == 2           # 1, 2
    assert f["withdrawn"] == 3
    assert f["submitted_first_assessment"] == 4


def test_funnel_stages_are_nested(db):
    f = db.run_file("01_funnel.sql")
    stages = ["registered", "started", "past_week4", "finished", "passed"]
    for a, b in zip(stages, stages[1:]):
        assert (f[a] >= f[b]).all()


def test_withdrawal_week(db):
    w = db.run_file("02_withdrawal_week.sql").set_index("week")["withdrawals"].to_dict()
    assert w == {0: 1, 2: 1, 6: 1}


def test_hardest_assessments(db):
    a = db.run_file("03_hardest_assessments.sql").set_index("id_assessment")
    assert 103 not in a.index  # exams are excluded
    assert a.loc[101, "expected"] == 4 and a.loc[101, "submitted"] == 4
    assert abs(a.loc[101, "avg_score"] - 58.75) < 1e-9
    assert a.loc[101, "scored_below_40"] == 2
    assert a.loc[102, "expected"] == 3 and a.loc[102, "submitted"] == 2
    assert abs(a.loc[102, "avg_score"] - 82.5) < 1e-9


def test_early_features(db):
    f = db.query("SELECT * FROM early_features ORDER BY id_student").set_index("id_student")
    assert list(f.index) == [1, 2, 3, 4, 6]  # student 5 never started
    assert f.loc[1, "clicks_pre_start"] == 10
    assert f.loc[1, "clicks_w1_4"] == 10
    assert f.loc[1, "clicks_w3_4"] == 5
    assert f.loc[1, "active_days_w1_4"] == 2
    assert f.loc[6, "clicks_w1_4"] == 3          # the day-40 clicks are outside the window
    assert f.loc[3, "early_assessments_missed"] == 1  # submitted on day 30, after the window
    assert f.loc[1, "early_assessments_missed"] == 0
    assert not bool(f.loc[4, "registered_at_day28"])
    assert bool(f.loc[6, "registered_at_day28"]) and bool(f.loc[6, "withdrew"])


def test_engagement_buckets(db):
    e = db.run_file("05_engagement_vs_withdrawal.sql").set_index("bucket")
    assert e.loc[0, "students"] == 1 and e.loc[0, "withdrew"] == 0  # student 3
    assert e["students"].sum() == 4  # student 4 left before day 28


def test_ab_groups(db):
    g = db.run_file("06_ab_groups.sql").set_index("grp")
    assert g.loc["A_pre_start_vle", "students"] == 2   # 1 and 6
    assert g.loc["A_pre_start_vle", "withdrew"] == 1
    assert g.loc["B_no_pre_start_vle", "students"] == 3  # 2, 3, 4
    assert g.loc["B_no_pre_start_vle", "passed"] == 1


def test_sql_files_avoid_engine_specific_syntax():
    """Keep the SQL portable between PostgreSQL and DuckDB."""
    for name in ["01_funnel.sql", "02_withdrawal_week.sql", "03_hardest_assessments.sql",
                 "04_early_features.sql", "05_engagement_vs_withdrawal.sql", "06_ab_groups.sql",
                 "07_powerbi_enrolment.sql"]:
        sql = read_sql(name).upper()
        for bad in ["ILIKE", "QUALIFY", "::", "DATEDIFF", " TOP "]:
            assert bad not in sql, f"{bad} in {name}"
