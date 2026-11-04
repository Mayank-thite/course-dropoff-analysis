-- Q2b / Q3 / Q4. One row per student who was still registered on day 0,
-- with behaviour from the first four weeks only (days 0-27) plus pre-start clicks.
-- Outcome columns (withdrew, passed) are kept separate from the features.
DROP TABLE IF EXISTS early_features;

CREATE TABLE early_features AS
WITH started AS (
    SELECT i.code_module, i.code_presentation, i.id_student, i.final_result,
           r.date_unregistration
    FROM student_info i
    JOIN student_registration r
      ON r.code_module = i.code_module
     AND r.code_presentation = i.code_presentation
     AND r.id_student = i.id_student
    WHERE r.date_unregistration IS NULL OR r.date_unregistration >= 0
),
clicks AS (
    SELECT
        code_module, code_presentation, id_student,
        SUM(CASE WHEN date < 0 THEN sum_click ELSE 0 END)                AS clicks_pre_start,
        SUM(CASE WHEN date BETWEEN 0 AND 27 THEN sum_click ELSE 0 END)   AS clicks_w1_4,
        SUM(CASE WHEN date BETWEEN 14 AND 27 THEN sum_click ELSE 0 END)  AS clicks_w3_4,
        COUNT(DISTINCT CASE WHEN date BETWEEN 0 AND 27 THEN date END)    AS active_days_w1_4
    FROM student_vle
    WHERE date < 28
    GROUP BY code_module, code_presentation, id_student
),
early_assessments AS (
    SELECT code_module, code_presentation, id_assessment
    FROM assessments
    WHERE assessment_type <> 'Exam' AND date <= 27
),
assess AS (
    SELECT
        s.code_module, s.code_presentation, s.id_student,
        COUNT(ea.id_assessment)                                AS early_assessments_due,
        COUNT(sa.id_assessment)                                AS early_assessments_submitted
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
    (s.date_unregistration IS NULL OR s.date_unregistration >= 28)   AS registered_at_day28,
    COALESCE(c.clicks_pre_start, 0)                                   AS clicks_pre_start,
    COALESCE(c.clicks_w1_4, 0)                                        AS clicks_w1_4,
    COALESCE(c.clicks_w3_4, 0)                                        AS clicks_w3_4,
    COALESCE(c.active_days_w1_4, 0)                                   AS active_days_w1_4,
    COALESCE(a.early_assessments_due, 0)                              AS early_assessments_due,
    COALESCE(a.early_assessments_submitted, 0)                        AS early_assessments_submitted,
    COALESCE(a.early_assessments_due, 0)
      - COALESCE(a.early_assessments_submitted, 0)                    AS early_assessments_missed,
    (s.final_result = 'Withdrawn')                                    AS withdrew,
    (s.final_result IN ('Pass', 'Distinction'))                       AS passed
FROM started s
LEFT JOIN clicks c
  ON c.code_module = s.code_module
 AND c.code_presentation = s.code_presentation
 AND c.id_student = s.id_student
LEFT JOIN assess a
  ON a.code_module = s.code_module
 AND a.code_presentation = s.code_presentation
 AND a.id_student = s.id_student;
