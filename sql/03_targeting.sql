-- =============================================================================
-- 03_targeting.sql — M-06 deciles, M-11 non-target call share, M-12 low-potential call share,
--                    the potential-by-penetration matrix and the misallocation quadrant
-- =============================================================================

-- M-06 Market-volume-weighted decile, as at the end of each quarter.
--   Universe: all 10,000 doctors. Measure: TRx of all four brands over the 52 weeks ending
--   at the quarter's last week. Sort high to low (ties broken by doctor ID) and cut the
--   cumulative volume into ten bands of about 10% each: decile 10 = the few biggest
--   prescribers, decile 1 = the many smallest, decile 0 = no GLP-1 prescriptions at all.
CREATE OR REPLACE TABLE mart.doctor_decile AS
WITH quarters AS (
    SELECT DISTINCT quarter FROM call_plan
),
volume AS (
    SELECT q.quarter, d.doctor_id,
           COALESCE(SUM(r.trx), 0)                                   AS market_trx_52w,
           COALESCE(SUM(r.trx) FILTER (WHERE r.brand = 'glyvexa'), 0) AS glyvexa_trx_52w
    FROM quarters q
    CROSS JOIN doctors d
    LEFT JOIN weekly_rx r
           ON r.doctor_id = d.doctor_id
          AND r.week BETWEEN q.quarter * 13 - 51 AND q.quarter * 13
    GROUP BY ALL
),
ranked AS (
    SELECT *,
           SUM(market_trx_52w) OVER (PARTITION BY quarter ORDER BY market_trx_52w DESC, doctor_id
                                     ROWS UNBOUNDED PRECEDING)
         / SUM(market_trx_52w) OVER (PARTITION BY quarter)          AS cumulative_share
    FROM volume
)
SELECT
    quarter, doctor_id, market_trx_52w, glyvexa_trx_52w,
    CASE WHEN market_trx_52w = 0 THEN 0
         ELSE 10 - LEAST(9, FLOOR((cumulative_share - 1e-9) * 10))::INT
    END                                                              AS decile,
    CASE WHEN market_trx_52w = 0 THEN NULL
         ELSE glyvexa_trx_52w / market_trx_52w END                   AS glyvexa_share_52w
FROM ranked;

-- Doctor-level targeting view for any period [w0, w1].
-- The call plan and decile used are those of the quarter containing w1.
-- Planned calls are scaled to the period length (a 13-week period = the full quarterly plan).
CREATE OR REPLACE MACRO mart.targeting(w0, w1) AS TABLE
WITH calls AS (
    SELECT doctor_id, COUNT(*) AS calls
    FROM mart.fct_interaction
    WHERE is_call AND week BETWEEN w0 AND w1
    GROUP BY doctor_id
)
SELECT
    d.doctor_id, d.doctor_name, d.specialty_group, d.access_tier, d.pdrp_optout,
    d.territory_id, d.territory_name, d.district, d.region,
    dec.decile,
    dec.market_trx_52w,
    dec.glyvexa_share_52w,
    COALESCE(p.segment, 'Non-target')                                AS segment,
    COALESCE(p.planned_calls, 0) * (w1 - w0 + 1) / 13.0              AS planned_calls,
    COALESCE(c.calls, 0)                                             AS calls,
    -- potential band and brand-penetration band for the matrix (FR-21)
    CASE WHEN dec.decile >= 8 THEN 'High (8–10)'
         WHEN dec.decile >= 5 THEN 'Medium (5–7)'
         ELSE 'Low (0–4)' END                                        AS potential_band,
    CASE WHEN dec.glyvexa_share_52w IS NULL   THEN 'No market volume'
         WHEN dec.glyvexa_share_52w < 0.15    THEN 'Low share (<15%)'
         WHEN dec.glyvexa_share_52w < 0.35    THEN 'Medium share (15–35%)'
         ELSE 'High share (35%+)' END                                AS share_band,
    -- misallocation quadrant (FR-22)
    (dec.decile >= 8 AND COALESCE(c.calls, 0) < COALESCE(p.planned_calls, 0) * (w1 - w0 + 1) / 13.0)
        OR (dec.decile >= 8 AND p.doctor_id IS NULL AND COALESCE(c.calls, 0) = 0)
                                                                     AS under_called_high_potential,
    dec.decile <= 4 AND COALESCE(c.calls, 0) > 0
        AND (p.doctor_id IS NULL OR c.calls > p.planned_calls * (w1 - w0 + 1) / 13.0)
                                                                     AS over_called_low_potential
FROM mart.dim_doctor d
JOIN mart.doctor_decile dec
  ON dec.doctor_id = d.doctor_id AND dec.quarter = mart.quarter_of(w1)
LEFT JOIN call_plan p
  ON p.doctor_id = d.doctor_id AND p.quarter = mart.quarter_of(w1)
LEFT JOIN calls c
  ON c.doctor_id = d.doctor_id;

-- Targeting summary for any period, at every geography level.
--   M-11 non-target call share  = calls on non-target doctors ÷ all calls
--   M-12 low-potential call share = calls on decile 0–4 doctors ÷ all calls
CREATE OR REPLACE MACRO mart.targeting_summary(w0, w1) AS TABLE
SELECT
    CASE WHEN territory_id IS NOT NULL THEN 'territory'
         WHEN district     IS NOT NULL THEN 'district'
         WHEN region       IS NOT NULL THEN 'region'
         ELSE 'national' END                                         AS level,
    COALESCE(territory_id, district, region, 'National')             AS area,
    SUM(calls)                                                       AS calls,
    SUM(calls) FILTER (WHERE segment = 'Non-target') / NULLIF(SUM(calls), 0)   AS non_target_call_share,
    SUM(calls) FILTER (WHERE decile <= 4)          / NULLIF(SUM(calls), 0)     AS low_potential_call_share,
    COUNT(*) FILTER (WHERE under_called_high_potential)                         AS under_called_high_potential_doctors,
    COUNT(*) FILTER (WHERE over_called_low_potential)                           AS over_called_low_potential_doctors,
    SUM(calls) FILTER (WHERE over_called_low_potential) / NULLIF(SUM(calls), 0) AS share_of_calls_on_over_called
FROM mart.targeting(w0, w1)
GROUP BY GROUPING SETS ((region, district, territory_id), (region, district), (region), ());
