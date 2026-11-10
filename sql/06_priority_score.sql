-- =============================================================================
-- 06_priority_score.sql — drivers of the Commercial Targeting Priority Score (C1)
--
-- The score is an illustrative decision-support ranking, not a prediction of sales.
-- This file produces the four opportunity drivers (each 0–100) and a plain-English reason for
-- each. The app applies the analyst's weights, so changing a slider never needs new SQL:
--     opportunity score = 0.35 × potential + 0.25 × headroom + 0.20 × momentum risk + 0.20 × overdue
-- Access is NOT a driver: it is shown beside the score as a constraint, so a hard-to-reach
-- doctor with high opportunity still ranks high.
-- =============================================================================

-- Drivers as of any week (as_of). Uses only data up to that week.
--   Example: SELECT * FROM mart.priority_drivers(104) ORDER BY default_score DESC LIMIT 50;
CREATE OR REPLACE MACRO mart.priority_drivers(as_of) AS TABLE
WITH
-- Decile and brand share from the last quarter completed by as_of (when call plans are refreshed)
volume AS (
    SELECT doctor_id, decile, market_trx_52w, glyvexa_share_52w
    FROM mart.doctor_decile
    WHERE quarter = GREATEST(1, as_of // 13)
),
-- Glyvexa NBRx in the latest 13 weeks against the 13 weeks before
momentum AS (
    SELECT doctor_id,
           SUM(nbrx) FILTER (WHERE week BETWEEN as_of - 12 AND as_of)      AS nbrx_latest_13w,
           SUM(nbrx) FILTER (WHERE week BETWEEN as_of - 25 AND as_of - 13) AS nbrx_prior_13w
    FROM weekly_rx
    WHERE brand = 'glyvexa' AND week BETWEEN as_of - 25 AND as_of
    GROUP BY doctor_id
),
calls AS (
    SELECT doctor_id,
           MAX(week)                                          AS last_call_week,
           COUNT(*) FILTER (WHERE week >= as_of - 1)          AS calls_last_2_weeks
    FROM mart.fct_interaction
    WHERE is_call AND week <= as_of
    GROUP BY doctor_id
),
base AS (
    SELECT
        d.doctor_id, d.doctor_name, d.specialty_label, d.specialty_group,
        d.territory_id, d.territory_name, d.district, d.region,
        d.access_tier, d.pdrp_optout,
        COALESCE(p.segment, 'Non-target')                         AS segment,
        p.planned_calls,
        v.decile, v.market_trx_52w, v.glyvexa_share_52w,
        COALESCE(m.nbrx_latest_13w, 0)                            AS nbrx_latest_13w,
        COALESCE(m.nbrx_prior_13w, 0)                             AS nbrx_prior_13w,
        c.last_call_week,
        COALESCE(c.calls_last_2_weeks, 0)                         AS calls_last_2_weeks,
        -- headroom input: market volume not yet on Glyvexa
        PERCENT_RANK() OVER (ORDER BY v.market_trx_52w) * (1 - COALESCE(v.glyvexa_share_52w, 0)) AS headroom_raw,
        CASE WHEN COALESCE(m.nbrx_prior_13w, 0) >= 4  -- ignore tiny counts, which are mostly noise
                 
                  AND COALESCE(m.nbrx_latest_13w, 0) < m.nbrx_prior_13w
             THEN (m.nbrx_prior_13w - COALESCE(m.nbrx_latest_13w, 0)) * 1.0 / m.nbrx_prior_13w
             ELSE 0 END                                           AS nbrx_drop
    FROM mart.dim_doctor d
    JOIN volume v ON v.doctor_id = d.doctor_id
    LEFT JOIN call_plan p ON p.doctor_id = d.doctor_id AND p.quarter = mart.quarter_of(as_of)
    LEFT JOIN momentum m  ON m.doctor_id = d.doctor_id
    LEFT JOIN calls c     ON c.doctor_id = d.doctor_id
    WHERE v.decile > 0
),
scored AS (
    SELECT *,
        decile * 10.0                                                         AS d_potential,
        100.0 * headroom_raw                                                  AS d_headroom,
        CASE WHEN nbrx_drop > 0
             THEN 100.0 * PERCENT_RANK() OVER (PARTITION BY nbrx_drop > 0 ORDER BY nbrx_drop)
             ELSE 0 END                                                       AS d_momentum,
        CASE WHEN planned_calls IS NULL THEN 0
             ELSE 100.0 * LEAST(3, (as_of - COALESCE(last_call_week, 0)) / (13.0 / planned_calls)) / 3
        END                                                                   AS d_overdue
    FROM base
)
SELECT
    doctor_id, doctor_name, specialty_label, specialty_group,
    territory_id, territory_name, district, region, segment, decile,
    access_tier, pdrp_optout,
    -- contact options are illustrative and always subject to the doctor's consent and company policy
    CASE access_tier
        WHEN 'open'    THEN 'In person or remote'
        WHEN 'limited' THEN 'Remote preferred; in person by appointment'
        ELSE                'Non-personal channels only, if the doctor has consented'
    END                                                                       AS contact_options,
    ROUND(d_potential, 1)  AS d_potential,
    ROUND(d_headroom, 1)   AS d_headroom,
    ROUND(d_momentum, 1)   AS d_momentum,
    ROUND(d_overdue, 1)    AS d_overdue,
    ROUND(0.35 * d_potential + 0.25 * d_headroom + 0.20 * d_momentum + 0.20 * d_overdue, 1) AS default_score,
    -- one plain-English reason per driver; the app shows the three with the largest weighted contribution
    CASE WHEN decile >= 8 THEN 'Top-decile GLP-1 prescriber (decile ' || decile || ')'
         ELSE 'Decile ' || decile || ' GLP-1 prescriber' END                  AS reason_potential,
    'About ' || ROUND(100 * (1 - COALESCE(glyvexa_share_52w, 0)))::INT
        || '% of this doctor''s GLP-1 prescriptions go to competitors'        AS reason_headroom,
    CASE WHEN nbrx_drop > 0
         THEN 'New Glyvexa patients down ' || ROUND(100 * nbrx_drop)::INT || '% in the last 13 weeks ('
              || nbrx_prior_13w || ' to ' || nbrx_latest_13w || ')'
         ELSE 'New Glyvexa patients steady or rising' END                    AS reason_momentum,
    CASE WHEN planned_calls IS NULL THEN 'Not on the call plan'
         WHEN last_call_week IS NULL THEN 'No call on record against a ' || ROUND(13.0 / planned_calls, 1) || '-week plan'
         ELSE 'Last seen ' || (as_of - last_call_week) || ' weeks ago against a '
              || ROUND(13.0 / planned_calls, 1) || '-week plan' END          AS reason_overdue,
    -- list rules (FRD): rest doctors called 3+ times in the last 2 weeks; show non-targets only if decile 8–10
    calls_last_2_weeks >= 3                                                   AS resting_after_recent_calls,
    CASE WHEN segment = 'Non-target' THEN 'Consider adding to call plan' END  AS tag,
    segment <> 'Non-target' OR decile >= 8                                    AS eligible_for_list
FROM scored;
