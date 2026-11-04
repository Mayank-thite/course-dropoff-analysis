-- Q4. Observational comparison: students who opened the VLE before the
-- module started vs students who did not. Population: still registered on day 0.
-- This is NOT an experiment; students chose which group they are in.
SELECT
    code_module,
    CASE WHEN clicks_pre_start > 0 THEN 'A_pre_start_vle' ELSE 'B_no_pre_start_vle' END AS grp,
    COUNT(*)                          AS students,
    COUNT(*) FILTER (WHERE withdrew)  AS withdrew,
    COUNT(*) FILTER (WHERE passed)    AS passed
FROM early_features
GROUP BY code_module,
         CASE WHEN clicks_pre_start > 0 THEN 'A_pre_start_vle' ELSE 'B_no_pre_start_vle' END
ORDER BY code_module, grp;
