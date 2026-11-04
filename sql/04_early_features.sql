-- Q2b / Q3 / Q4. One row per registration that had not withdrawn before day 0,
-- with behaviour from the first four weeks only (days 0 to 27) plus pre-start clicks.
-- Outcome columns (withdrew, passed) are kept apart from the features.
--
-- Rules I use everywhere:
--   * A student leaves on date_unregistration only if final_result = 'Withdrawn'.
--     (9 Fail rows also have an unregistration day. I treat them as still enrolled.)
--   * 93 withdrawn students have no unregistration day. I can't tell when they left,
--     so withdrawal_day_known is false for them and the model and A/B leave them out.
--   * The early score is the mean score on assessments due by day 27 and sent by day 27.
--     OULAD has no marking date, so this assumes marks are back by day 28.
DROP TABLE IF EXISTS early_features;

CREATE TABLE early_features AS
WITH reg AS (
    SELECT i.code_module, i.code_presentation, i.id_student, i.final_result,
           i.gender, i.highest_education, i.imd_band, i.age_band, i.disability,
           i.num_of_prev_attempts, i.studied_credits,
           r.date_registration,
           CASE WHEN i.final_result = 'Withdrawn' THEN r.date_unregistration END AS left_day,
           (i.final_result <> 'Withdrawn' OR r.date_unregistration IS NOT NULL) AS withdrawal_day_known
    FROM student_info i
    JOIN student_registration r
      ON r.code_module = i.code_module
     AND r.code_presentation = i.code_presentation
     AND r.id_student = i.id_student
),
started AS (
    SELECT * FROM reg WHERE left_day IS NULL OR left_day >= 0
),
clicks AS (
    SELECT
        code_module, code_presentation, id_student,
        SUM(CASE WHEN date < 0 THEN sum_click ELSE 0 END)                 AS clicks_pre_start,
        COUNT(DISTINCT CASE WHEN date < 0 THEN date END)                  AS active_days_pre_start,
        SUM(CASE WHEN date BETWEEN 0 AND 27 THEN sum_click ELSE 0 END)    AS clicks_w1_4,
        SUM(CASE WHEN date BETWEEN 0 AND 13 THEN sum_click ELSE 0 END)    AS clicks_w1_2,
        SUM(CASE WHEN date BETWEEN 14 AND 27 THEN sum_click ELSE 0 END)   AS clicks_w3_4,
        COUNT(DISTINCT CASE WHEN date BETWEEN 0 AND 27 THEN date END)     AS active_days_w1_4,
        COUNT(DISTINCT CASE WHEN date BETWEEN 14 AND 27 THEN date END)    AS active_days_w3_4,
        MAX(CASE WHEN date BETWEEN 0 AND 27 THEN date END)                AS last_active_day
    FROM student_vle
    WHERE date < 28
    GROUP BY code_module, code_presentation, id_student
),
early_assessments AS (
    SELECT code_module, code_presentation, id_assessment
    FROM assessments
    WHERE assessment_type <> 'Exam' AND date <= 27
),
assess_due AS (
    SELECT
        s.code_module, s.code_presentation, s.id_student,
        COUNT(ea.id_assessment)                                         AS early_assessments_due,
        COUNT(sa.id_assessment)                                         AS early_assessments_submitted,
        AVG(sa.score)                                                   AS early_avg_score
    FROM started s
    JOIN early_assessments ea
      ON ea.code_module = s.code_module
     AND ea.code_presentation = s.code_presentation
    LEFT JOIN student_assessment sa
      ON sa.id_assessment = ea.id_assessment
     AND sa.id_student = s.id_student
     AND sa.date_submitted <= 27
    GROUP BY s.code_module, s.code_presentation, s.id_student
)
SELECT
    s.code_module,
    s.code_presentation,
    s.id_student,
    s.withdrawal_day_known,
    (s.left_day IS NULL OR s.left_day >= 28)                          AS registered_at_day28,
    s.date_registration,
    s.gender, s.highest_education, s.imd_band, s.age_band, s.disability,
    s.num_of_prev_attempts,
    s.studied_credits,
    COALESCE(c.clicks_pre_start, 0)                                   AS clicks_pre_start,
    COALESCE(c.active_days_pre_start, 0)                              AS active_days_pre_start,
    COALESCE(c.clicks_w1_4, 0)                                        AS clicks_w1_4,
    COALESCE(c.clicks_w1_2, 0)                                        AS clicks_w1_2,
    COALESCE(c.clicks_w3_4, 0)                                        AS clicks_w3_4,
    COALESCE(c.active_days_w1_4, 0)                                   AS active_days_w1_4,
    COALESCE(c.active_days_w3_4, 0)                                   AS active_days_w3_4,
    c.last_active_day,
    COALESCE(a.early_assessments_due, 0)                              AS early_assessments_due,
    COALESCE(a.early_assessments_submitted, 0)                        AS early_assessments_submitted,
    COALESCE(a.early_assessments_due, 0)
      - COALESCE(a.early_assessments_submitted, 0)                    AS early_assessments_missed,
    a.early_avg_score,
    (s.final_result = 'Withdrawn')                                    AS withdrew,
    (s.final_result IN ('Pass', 'Distinction'))                       AS passed
FROM started s
LEFT JOIN clicks c
  ON c.code_module = s.code_module
 AND c.code_presentation = s.code_presentation
 AND c.id_student = s.id_student
LEFT JOIN assess_due a
  ON a.code_module = s.code_module
 AND a.code_presentation = s.code_presentation
 AND a.id_student = s.id_student;
