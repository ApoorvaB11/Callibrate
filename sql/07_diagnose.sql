-- =============================================================================
-- 07_diagnose.sql — before/after comparison for the Diagnose screen (FR-70, FR-73)
--
-- For a chosen week, compares the n weeks after it with the n weeks before it, per territory:
-- calls (effort), Glyvexa NBRx and TRx (outcome), and prior-authorisation rejections (access).
-- Findings are associations in synthetic data, never proof of cause (FR-06).
--   Example: SELECT * FROM mart.before_after(88, 12) ORDER BY nbrx_change;
-- =============================================================================

CREATE OR REPLACE MACRO mart.before_after(change_week, n_weeks) AS TABLE
WITH rx AS (
    SELECT territory_id,
           SUM(nbrx) FILTER (WHERE week BETWEEN change_week - n_weeks AND change_week - 1) AS nbrx_before,
           SUM(nbrx) FILTER (WHERE week BETWEEN change_week + 1 AND change_week + n_weeks) AS nbrx_after,
           SUM(trx)  FILTER (WHERE week BETWEEN change_week - n_weeks AND change_week - 1) AS trx_before,
           SUM(trx)  FILTER (WHERE week BETWEEN change_week + 1 AND change_week + n_weeks) AS trx_after
    FROM mart.rx_territory_week
    WHERE brand = 'glyvexa'
    GROUP BY territory_id
),
effort AS (
    SELECT territory_id,
           COUNT(*) FILTER (WHERE week BETWEEN change_week - n_weeks AND change_week - 1) AS calls_before,
           COUNT(*) FILTER (WHERE week BETWEEN change_week + 1 AND change_week + n_weeks) AS calls_after
    FROM mart.fct_interaction
    WHERE is_call
    GROUP BY territory_id
),
access AS (
    SELECT territory_id,
           SUM(rejected_prior_auth) FILTER (WHERE week BETWEEN change_week - n_weeks AND change_week - 1) * 1.0
             / NULLIF(SUM(first_fill_claims) FILTER (WHERE week BETWEEN change_week - n_weeks AND change_week - 1), 0)
                                                                                    AS pa_rejection_before,
           SUM(rejected_prior_auth) FILTER (WHERE week BETWEEN change_week + 1 AND change_week + n_weeks) * 1.0
             / NULLIF(SUM(first_fill_claims) FILTER (WHERE week BETWEEN change_week + 1 AND change_week + n_weeks), 0)
                                                                                    AS pa_rejection_after
    FROM mart.first_fill_week
    WHERE brand = 'glyvexa'
    GROUP BY territory_id
)
SELECT
    t.territory_id, t.territory_name, t.district, t.district_label, t.region,
    rx.nbrx_before, rx.nbrx_after, rx.nbrx_after * 1.0 / NULLIF(rx.nbrx_before, 0) - 1  AS nbrx_change,
    rx.trx_before,  rx.trx_after,  rx.trx_after  * 1.0 / NULLIF(rx.trx_before, 0)  - 1  AS trx_change,
    e.calls_before, e.calls_after, e.calls_after * 1.0 / NULLIF(e.calls_before, 0) - 1  AS calls_change,
    a.pa_rejection_before, a.pa_rejection_after,
    -- quadrant for the scatter (FR-70): effort broadly held (calls down less than 10%) but NBRx down 10% or more.
    -- Territory-level NBRx moves by about ±8% from noise alone, so read single territories with care.
    (e.calls_after * 1.0 / NULLIF(e.calls_before, 0) - 1 > -0.10
       AND rx.nbrx_after * 1.0 / NULLIF(rx.nbrx_before, 0) - 1 <= -0.10)              AS effort_held_outcome_fell
FROM territories t
JOIN rx     USING (territory_id)
JOIN effort e USING (territory_id)
LEFT JOIN access a USING (territory_id);

-- The same comparison rolled up to districts, regions and the nation, where noise is smaller
CREATE OR REPLACE MACRO mart.before_after_rollup(change_week, n_weeks) AS TABLE
SELECT
    CASE WHEN district IS NOT NULL THEN 'district'
         WHEN region   IS NOT NULL THEN 'region'
         ELSE 'national' END                                    AS level,
    COALESCE(district, region, 'National')                      AS area,
    SUM(nbrx_after) * 1.0 / SUM(nbrx_before) - 1                AS nbrx_change,
    SUM(trx_after)  * 1.0 / SUM(trx_before)  - 1                AS trx_change,
    SUM(calls_after) * 1.0 / SUM(calls_before) - 1              AS calls_change,
    COUNT(*) FILTER (WHERE effort_held_outcome_fell)            AS territories_effort_held_outcome_fell,
    COUNT(*)                                                    AS territories
FROM mart.before_after(change_week, n_weeks)
GROUP BY GROUPING SETS ((region, district), (region), ());
