-- Q4. Observational comparison: students who opened the VLE before the
-- module started vs students who did not.
-- Population: had not withdrawn before day 0, registered before day 0 (someone who
-- signs up after the start can't be in group A), and a known withdrawal day.
-- This is NOT an experiment. Students chose which group they are in.
SELECT
    code_module,
    CASE WHEN clicks_pre_start > 0 THEN 'A_pre_start_vle' ELSE 'B_no_pre_start_vle' END AS grp,
    COUNT(*)                          AS students,
    COUNT(*) FILTER (WHERE withdrew)  AS withdrew,
    COUNT(*) FILTER (WHERE passed)    AS passed
FROM early_features
WHERE withdrawal_day_known AND date_registration < 0
GROUP BY code_module,
         CASE WHEN clicks_pre_start > 0 THEN 'A_pre_start_vle' ELSE 'B_no_pre_start_vle' END
ORDER BY code_module, grp;
