-- =============================================================================
-- 04_coverage_execution.sql — coverage and field execution for the call plan's targets
--   M-07 reach, M-08 average frequency, M-09 call-plan adherence, M-10 frequency attainment,
--   M-16 in-person reach, M-17 omnichannel reach, and the rep scorecard
--
-- Three different questions, kept apart on purpose:
--   adherence (M-09)  = did reps execute the plan?
--   targeting (03_)   = is the effort going to the right doctors?
--   impact (02_)      = what happened to prescribing? (an association, never proof of cause)
-- =============================================================================

-- Target-level coverage for any period [w0, w1].
-- Targets are the call plan of the quarter containing w1; planned calls are scaled to the period.
CREATE OR REPLACE MACRO mart.coverage(w0, w1) AS TABLE
WITH touches AS (
    SELECT doctor_id,
           COUNT(*) FILTER (WHERE is_call)                AS calls,
           COUNT(*) FILTER (WHERE channel = 'in_person')  AS in_person_calls,
           COUNT(*) FILTER (WHERE channel = 'remote')     AS remote_calls,
           COUNT(*) FILTER (WHERE channel = 'email')      AS emails,
           MAX(week) FILTER (WHERE is_call)               AS last_call_week
    FROM mart.fct_interaction
    WHERE week BETWEEN w0 AND w1
    GROUP BY doctor_id
)
SELECT
    p.doctor_id, d.doctor_name, d.specialty_group, d.access_tier, d.pdrp_optout,
    p.territory_id, d.territory_name, d.district, d.region,
    p.segment,
    dec.decile,
    p.planned_calls * (w1 - w0 + 1) / 13.0                                AS planned_calls,
    COALESCE(t.calls, 0)                                                  AS calls,
    COALESCE(t.in_person_calls, 0)                                        AS in_person_calls,
    COALESCE(t.remote_calls, 0)                                           AS remote_calls,
    COALESCE(t.emails, 0)                                                 AS emails,
    t.last_call_week,
    COALESCE(t.calls, 0) >= 1                                             AS reached,            -- M-07
    COALESCE(t.in_person_calls, 0) >= 1                                   AS reached_in_person,  -- M-16
    COALESCE(t.calls, 0) + COALESCE(t.emails, 0) >= 1                     AS touched_any,        -- M-17
    COALESCE(t.calls, 0) >= p.planned_calls * (w1 - w0 + 1) / 13.0        AS frequency_attained, -- M-10
    -- M-09 numerator: calls made, capped at the plan, so extra calls on one doctor
    -- cannot hide a missed doctor elsewhere
    LEAST(COALESCE(t.calls, 0), p.planned_calls * (w1 - w0 + 1) / 13.0)   AS capped_calls
FROM call_plan p
JOIN mart.dim_doctor d    ON d.doctor_id = p.doctor_id
JOIN mart.doctor_decile dec
  ON dec.doctor_id = p.doctor_id AND dec.quarter = p.quarter
LEFT JOIN touches t       ON t.doctor_id = p.doctor_id
WHERE p.quarter = mart.quarter_of(w1);

-- Coverage summary at every geography level, overall and for decile 8–10 targets
CREATE OR REPLACE MACRO mart.coverage_summary(w0, w1) AS TABLE
SELECT
    CASE WHEN territory_id IS NOT NULL THEN 'territory'
         WHEN district     IS NOT NULL THEN 'district'
         WHEN region       IS NOT NULL THEN 'region'
         ELSE 'national' END                                              AS level,
    COALESCE(territory_id, district, region, 'National')                  AS area,
    COUNT(*)                                                              AS targets,
    AVG(reached::INT)                                                     AS reach,                 -- M-07
    AVG(reached_in_person::INT)                                           AS in_person_reach,       -- M-16
    AVG(touched_any::INT)                                                 AS omnichannel_reach,     -- M-17
    SUM(calls) FILTER (WHERE reached) / NULLIF(COUNT(*) FILTER (WHERE reached), 0)
                                                                          AS average_frequency,     -- M-08
    AVG(frequency_attained::INT)                                          AS frequency_attainment,  -- M-10
    SUM(capped_calls) / NULLIF(SUM(planned_calls), 0)                     AS call_plan_adherence,   -- M-09
    AVG(reached::INT) FILTER (WHERE decile >= 8)                          AS reach_decile_8_10,
    COUNT(*) FILTER (WHERE decile >= 8)                                   AS targets_decile_8_10
FROM mart.coverage(w0, w1)
GROUP BY GROUPING SETS ((region, district, territory_id), (region, district), (region), ());

-- Coverage by access tier (FR-32): shows in-person, remote and email reach side by side
CREATE OR REPLACE MACRO mart.coverage_by_access(w0, w1) AS TABLE
SELECT
    access_tier,
    COUNT(*)                                AS targets,
    AVG(reached_in_person::INT)             AS in_person_reach,
    AVG((remote_calls > 0)::INT)            AS remote_reach,
    AVG((emails > 0)::INT)                  AS email_reach,
    AVG(touched_any::INT)                   AS omnichannel_reach,
    SUM(in_person_calls)                    AS in_person_calls,
    SUM(remote_calls)                       AS remote_calls,
    SUM(emails)                             AS emails
FROM mart.coverage(w0, w1)
GROUP BY access_tier;

-- Rep scorecard (FR-40). A territory can change rep mid-period (P3 vacancy), so each rep's
-- planned calls are pro-rated by the share of the period they were in post.
CREATE OR REPLACE MACRO mart.rep_scorecard(w0, w1) AS TABLE
WITH rep_window AS (
    SELECT r.rep_id, r.rep_name, r.territory_id,
           GREATEST(r.start_week, w0)                                         AS active_from,
           LEAST(r.end_week, w1)                                              AS active_to,
           (LEAST(r.end_week, w1) - GREATEST(r.start_week, w0) + 1) / (w1 - w0 + 1.0) AS share_of_period
    FROM reps r
    WHERE r.start_week <= w1 AND r.end_week >= w0
),
plan AS (
    SELECT rw.rep_id, p.doctor_id, p.planned_calls * (w1 - w0 + 1) / 13.0 * rw.share_of_period AS planned
    FROM rep_window rw
    JOIN call_plan p ON p.territory_id = rw.territory_id AND p.quarter = mart.quarter_of(w1)
),
rep_calls AS (
    SELECT rep_id, doctor_id, COUNT(*) AS calls
    FROM mart.fct_interaction
    WHERE is_call AND week BETWEEN w0 AND w1
    GROUP BY ALL
),
per_doctor AS (
    SELECT pl.rep_id, pl.doctor_id, pl.planned, COALESCE(rc.calls, 0) AS calls
    FROM plan pl
    LEFT JOIN rep_calls rc USING (rep_id, doctor_id)
),
off_plan AS (
    SELECT rc.rep_id, SUM(rc.calls) AS calls_on_non_targets
    FROM rep_calls rc
    ANTI JOIN plan pl USING (rep_id, doctor_id)
    GROUP BY rc.rep_id
),
per_rep AS (
    SELECT rep_id,
           SUM(planned)                                       AS planned_calls,
           SUM(calls)                                         AS calls_on_planned_doctors,
           SUM(LEAST(calls, planned)) / NULLIF(SUM(planned), 0) AS call_plan_adherence,
           AVG((calls > 0)::INT)                              AS reach
    FROM per_doctor
    GROUP BY rep_id
)
SELECT
    rw.rep_id, rw.rep_name, rw.territory_id, t.territory_name, t.district, t.district_label, t.region,
    rw.active_from, rw.active_to,
    ROUND(pr.planned_calls, 1)                                       AS planned_calls,
    pr.calls_on_planned_doctors,
    pr.call_plan_adherence,
    pr.reach,
    COALESCE(op.calls_on_non_targets, 0)                             AS calls_on_non_targets,
    RANK() OVER (PARTITION BY t.district ORDER BY pr.call_plan_adherence DESC) AS rank_in_district
FROM rep_window rw
JOIN territories t ON t.territory_id = rw.territory_id
JOIN per_rep pr    ON pr.rep_id = rw.rep_id
LEFT JOIN off_plan op ON op.rep_id = rw.rep_id;

-- Missed doctors (FR-41): planned targets with no call in the period, highest decile first
CREATE OR REPLACE MACRO mart.missed_targets(w0, w1) AS TABLE
SELECT
    c.territory_id, c.doctor_id, c.doctor_name, c.specialty_group, c.segment, c.decile,
    c.access_tier, c.pdrp_optout,
    (SELECT MAX(f.week) FROM mart.fct_interaction f
      WHERE f.doctor_id = c.doctor_id AND f.is_call AND f.week <= w1)        AS last_call_week
FROM mart.coverage(w0, w1) c
WHERE NOT c.reached
ORDER BY c.decile DESC, c.segment;
