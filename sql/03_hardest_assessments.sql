-- Q2a. Which assessments are hardest?
-- expected  : students still registered on the due day (exams without a date use the last day)
-- submitted : of those, how many have a submission row
-- avg_score : mean score of submissions (0-100); pass mark is 40
-- Exams are left out: OULAD does not include exam results for several modules,
-- so a missing exam row does not mean the student skipped it.
WITH a AS (
    SELECT
        a.id_assessment,
        a.code_module,
        a.code_presentation,
        a.assessment_type,
        a.weight,
        COALESCE(a.date, c.module_presentation_length) AS due_day
    FROM assessments a
    JOIN courses c
      ON c.code_module = a.code_module
     AND c.code_presentation = a.code_presentation
    WHERE a.assessment_type <> 'Exam'
),
expected AS (
    SELECT a.id_assessment, r.id_student
    FROM a
    JOIN student_registration r
      ON r.code_module = a.code_module
     AND r.code_presentation = a.code_presentation
    WHERE r.date_unregistration IS NULL OR r.date_unregistration > a.due_day
),
joined AS (
    SELECT e.id_assessment, e.id_student, sa.score,
           (sa.id_student IS NOT NULL) AS has_submission
    FROM expected e
    LEFT JOIN student_assessment sa
      ON sa.id_assessment = e.id_assessment
     AND sa.id_student = e.id_student
)
SELECT
    a.code_module,
    a.code_presentation,
    a.id_assessment,
    a.assessment_type,
    a.due_day,
    a.weight,
    COUNT(j.id_student)                                         AS expected,
    COUNT(*) FILTER (WHERE j.has_submission)                    AS submitted,
    AVG(j.score)                                                AS avg_score,
    COUNT(*) FILTER (WHERE j.score < 40)                        AS scored_below_40
FROM a
LEFT JOIN joined j ON j.id_assessment = a.id_assessment
GROUP BY a.code_module, a.code_presentation, a.id_assessment,
         a.assessment_type, a.due_day, a.weight
ORDER BY a.code_module, a.code_presentation, a.due_day, a.id_assessment;
