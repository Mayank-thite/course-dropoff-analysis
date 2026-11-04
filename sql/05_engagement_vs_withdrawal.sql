-- Q2b. Withdrawal rate by how much a student used the VLE in weeks 1-4.
-- Population: still registered at day 28, so the outcome is not already known.
-- Students with zero clicks are their own group. The rest are split at the
-- 25th, 50th and 75th percentile of clicks (ties stay in the same group).
WITH pop AS (
    SELECT * FROM early_features WHERE registered_at_day28
),
cuts AS (
    SELECT
        PERCENTILE_DISC(0.25) WITHIN GROUP (ORDER BY clicks_w1_4) AS p25,
        PERCENTILE_DISC(0.50) WITHIN GROUP (ORDER BY clicks_w1_4) AS p50,
        PERCENTILE_DISC(0.75) WITHIN GROUP (ORDER BY clicks_w1_4) AS p75
    FROM pop
    WHERE clicks_w1_4 > 0
),
bucketed AS (
    SELECT
        p.clicks_w1_4,
        p.withdrew,
        CASE WHEN p.clicks_w1_4 = 0     THEN 0
             WHEN p.clicks_w1_4 <= c.p25 THEN 1
             WHEN p.clicks_w1_4 <= c.p50 THEN 2
             WHEN p.clicks_w1_4 <= c.p75 THEN 3
             ELSE 4
        END AS bucket
    FROM pop p
    CROSS JOIN cuts c
)
SELECT
    bucket,
    COUNT(*)                                  AS students,
    MIN(clicks_w1_4)                          AS min_clicks,
    MAX(clicks_w1_4)                          AS max_clicks,
    COUNT(*) FILTER (WHERE withdrew)          AS withdrew
FROM bucketed
GROUP BY bucket
ORDER BY bucket;
