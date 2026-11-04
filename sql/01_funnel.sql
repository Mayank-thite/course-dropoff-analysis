-- Q1a. Registration-to-completion funnel per module presentation.
-- Each stage is a subset of the one before it.
--   registered        : every registration row
--   started           : had not withdrawn before day 0 (includes 234 people who
--                       registered after day 0, so it is not "enrolled on day 0")
--   past_week4        : had not withdrawn before day 28
--   finished          : did not withdraw (Pass, Distinction or Fail)
--   passed            : Pass or Distinction
-- A student leaves on date_unregistration only if final_result = 'Withdrawn'.
-- 9 Fail rows also carry an unregistration day; I keep them in every stage.
-- 93 withdrawn students have no unregistration day. They stay in the day 0 and
-- day 28 stages because I can't place them, and drop out at "finished".
-- submitted_first_assessment is reported alongside, it is not a funnel stage.
WITH base AS (
    SELECT
        i.code_module,
        i.code_presentation,
        i.id_student,
        i.final_result,
        CASE WHEN i.final_result = 'Withdrawn' THEN r.date_unregistration END AS left_day
    FROM student_info i
    JOIN student_registration r
      ON r.code_module = i.code_module
     AND r.code_presentation = i.code_presentation
     AND r.id_student = i.id_student
),
first_assessment AS (
    -- earliest non-exam assessment in each presentation
    SELECT code_module, code_presentation, MIN(id_assessment) AS id_assessment
    FROM assessments a
    WHERE assessment_type <> 'Exam'
      AND date = (
          SELECT MIN(a2.date) FROM assessments a2
          WHERE a2.code_module = a.code_module
            AND a2.code_presentation = a.code_presentation
            AND a2.assessment_type <> 'Exam'
      )
    GROUP BY code_module, code_presentation
),
flags AS (
    SELECT
        b.*,
        (b.left_day IS NULL OR b.left_day >= 0)  AS is_started,
        (b.left_day IS NULL OR b.left_day >= 28) AS is_past_week4,
        EXISTS (
            SELECT 1 FROM student_assessment sa
            JOIN first_assessment fa ON fa.id_assessment = sa.id_assessment
            WHERE fa.code_module = b.code_module
              AND fa.code_presentation = b.code_presentation
              AND sa.id_student = b.id_student
        ) AS did_first_assessment
    FROM base b
)
SELECT
    code_module,
    code_presentation,
    COUNT(*)                                                         AS registered,
    COUNT(*) FILTER (WHERE is_started)                               AS started,
    COUNT(*) FILTER (WHERE is_started AND is_past_week4)             AS past_week4,
    COUNT(*) FILTER (WHERE is_started AND is_past_week4
                       AND final_result <> 'Withdrawn')              AS finished,
    COUNT(*) FILTER (WHERE is_started AND is_past_week4
                       AND final_result IN ('Pass', 'Distinction'))  AS passed,
    COUNT(*) FILTER (WHERE final_result = 'Withdrawn')               AS withdrawn,
    COUNT(*) FILTER (WHERE did_first_assessment)                     AS submitted_first_assessment
FROM flags
GROUP BY code_module, code_presentation
ORDER BY code_module, code_presentation;
