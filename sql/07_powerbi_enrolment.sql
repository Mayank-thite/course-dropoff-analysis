-- Tidy enrolment fact table for Power BI. One row per registration.
SELECT
    i.code_module,
    i.code_presentation,
    i.code_module || '-' || i.code_presentation                   AS presentation_key,
    i.id_student,
    i.gender,
    i.age_band,
    i.imd_band,
    i.highest_education,
    i.final_result,
    r.date_registration,
    r.date_unregistration,
    CASE WHEN i.final_result = 'Withdrawn' AND r.date_unregistration IS NOT NULL
         THEN CAST(FLOOR(r.date_unregistration / 7.0) AS INTEGER) + 1 END AS withdrawal_week,
    CASE WHEN r.date_unregistration IS NULL OR r.date_unregistration >= 0  THEN 1 ELSE 0 END AS is_started,
    CASE WHEN r.date_unregistration IS NULL OR r.date_unregistration >= 28 THEN 1 ELSE 0 END AS is_past_week4,
    CASE WHEN i.final_result = 'Withdrawn' THEN 1 ELSE 0 END                AS is_withdrawn,
    CASE WHEN i.final_result IN ('Pass', 'Distinction') THEN 1 ELSE 0 END   AS is_passed,
    f.clicks_pre_start,
    f.clicks_w1_4,
    f.active_days_w1_4,
    f.early_assessments_missed
FROM student_info i
JOIN student_registration r
  ON r.code_module = i.code_module
 AND r.code_presentation = i.code_presentation
 AND r.id_student = i.id_student
LEFT JOIN early_features f
  ON f.code_module = i.code_module
 AND f.code_presentation = i.code_presentation
 AND f.id_student = i.id_student
ORDER BY i.code_module, i.code_presentation, i.id_student;
