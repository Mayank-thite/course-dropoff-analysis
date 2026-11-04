-- Q1b. In which week do withdrawals happen?
-- Week 1 = days 0-6 of the presentation. Week 0 or lower = before the start.
-- Only students with final_result = 'Withdrawn' and a recorded unregistration day.
SELECT
    i.code_module,
    CAST(FLOOR(r.date_unregistration / 7.0) AS INTEGER) + 1 AS week,
    COUNT(*)                                                AS withdrawals
FROM student_info i
JOIN student_registration r
  ON r.code_module = i.code_module
 AND r.code_presentation = i.code_presentation
 AND r.id_student = i.id_student
WHERE i.final_result = 'Withdrawn'
  AND r.date_unregistration IS NOT NULL
GROUP BY i.code_module, CAST(FLOOR(r.date_unregistration / 7.0) AS INTEGER) + 1
ORDER BY i.code_module, week;
