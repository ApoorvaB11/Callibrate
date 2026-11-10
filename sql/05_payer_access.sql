-- =============================================================================
-- 05_payer_access.sql — what happens at the pharmacy counter
--   M-13 first-fill rejection rate, M-14 abandonment rate, M-15 switch rate,
--   and M-18 12-month persistence
--
-- A "first fill" is the first fill (fill number 0) of the patient's first prescription number
-- for a brand, i.e. the moment a new patient tries to start therapy.
-- Reject codes (NCPDP vocabulary): 75 prior authorisation required, 76 plan limitations
-- exceeded, 65 patient not covered, 79 refill too soon.
-- =============================================================================

-- Every first-fill claim, paid or rejected, with the prescriber's territory
CREATE OR REPLACE TABLE mart.first_fill_claim AS
SELECT
    c.claim_id, c.service_date, c.week, c.patient_id,
    c.synthetic_prescriber_id                AS doctor_id,
    d.territory_id, d.district, d.region,
    c.brand, c.plan_id, p.name               AS plan_name, c.line_of_business,
    c.formulary_status, c.response_status, c.reject_code
FROM pharmacy_claims c
JOIN mart.dim_doctor d ON d.doctor_id = c.synthetic_prescriber_id
JOIN plans p           ON p.plan_id   = c.plan_id
WHERE c.fill_number = 0
  AND right(c.rx_number, 2) = '00';

-- What happened after each prior-authorisation rejection (code 75), within 30 days:
--   approved  = a paid claim for the same brand followed
--   switched  = no same-brand paid claim, but a paid claim for a competitor brand
--   abandoned = no paid claim for any brand
--   pending   = the rejection is less than 30 days before the end of the data, so we cannot know yet
CREATE OR REPLACE TABLE mart.pa_rejection_outcome AS
WITH rejected AS (
    SELECT * FROM mart.first_fill_claim WHERE response_status = 'R' AND reject_code = '75'
),
data_end AS (
    SELECT MAX(service_date) AS last_date FROM pharmacy_claims
),
follow_up AS (
    SELECT r.claim_id,
           BOOL_OR(pc.brand =  r.brand) AS same_brand_paid,
           BOOL_OR(pc.brand <> r.brand) AS other_brand_paid
    FROM rejected r
    JOIN pharmacy_claims pc
      ON pc.patient_id = r.patient_id
     AND pc.response_status = 'P'
     AND pc.service_date > r.service_date
     AND pc.service_date <= r.service_date + INTERVAL 30 DAY
    GROUP BY r.claim_id
)
SELECT
    r.*,
    CASE
        WHEN f.same_brand_paid                              THEN 'approved'
        WHEN f.other_brand_paid                             THEN 'switched'
        WHEN r.service_date > de.last_date - INTERVAL 30 DAY THEN 'pending'
        ELSE 'abandoned'
    END AS outcome
FROM rejected r
CROSS JOIN data_end de
LEFT JOIN follow_up f USING (claim_id);

-- Weekly first fills by plan, brand, territory and result, for the Diagnose timeline (FR-71)
CREATE OR REPLACE TABLE mart.first_fill_week AS
SELECT week, plan_id, plan_name, brand, territory_id, district, region,
       COUNT(*)                                                AS first_fill_claims,
       COUNT(*) FILTER (WHERE response_status = 'P')           AS paid,
       COUNT(*) FILTER (WHERE reject_code = '75')              AS rejected_prior_auth,
       COUNT(*) FILTER (WHERE response_status = 'R' AND reject_code <> '75') AS rejected_other
FROM mart.first_fill_claim
WHERE week BETWEEN 1 AND 104
GROUP BY ALL;

-- Payer summary for any period, by plan, by territory, by territory and plan, and by brand overall
--   M-13 first-fill rejection rate = rejected first-fill claims ÷ all first-fill claims submitted
--   M-14 abandonment rate          = abandoned ÷ prior-auth rejections with a known outcome
--   M-15 switch rate               = switched  ÷ prior-auth rejections with a known outcome
CREATE OR REPLACE MACRO mart.payer_summary(w0, w1) AS TABLE
WITH claims AS (
    SELECT f.*, o.outcome
    FROM mart.first_fill_claim f
    LEFT JOIN mart.pa_rejection_outcome o USING (claim_id)
    WHERE f.week BETWEEN w0 AND w1
)
SELECT
    CASE WHEN plan_id IS NOT NULL AND territory_id IS NOT NULL THEN 'territory_plan'
         WHEN plan_id IS NOT NULL                              THEN 'plan'
         WHEN territory_id IS NOT NULL                         THEN 'territory'
         ELSE 'all' END                                                        AS level,
    plan_id, CASE WHEN plan_id IS NOT NULL THEN ANY_VALUE(plan_name) END       AS plan_name,
    territory_id, brand,
    COUNT(*)                                                                   AS first_fill_claims,
    COUNT(*) FILTER (WHERE response_status = 'R') * 1.0 / COUNT(*)             AS first_fill_rejection_rate,
    COUNT(*) FILTER (WHERE reject_code = '75') * 1.0 / COUNT(*)                AS prior_auth_rejection_rate,
    COUNT(*) FILTER (WHERE reject_code = '75')                                 AS prior_auth_rejections,
    COUNT(*) FILTER (WHERE outcome = 'approved') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE outcome IN ('approved', 'switched', 'abandoned')), 0) AS approval_rate,
    COUNT(*) FILTER (WHERE outcome = 'abandoned') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE outcome IN ('approved', 'switched', 'abandoned')), 0) AS abandonment_rate,
    COUNT(*) FILTER (WHERE outcome = 'switched') * 1.0
        / NULLIF(COUNT(*) FILTER (WHERE outcome IN ('approved', 'switched', 'abandoned')), 0) AS switch_rate
FROM claims
GROUP BY GROUPING SETS ((plan_id, territory_id, brand), (plan_id, brand), (territory_id, brand), (brand));

-- M-18 12-month persistence.
-- Cohort: new-to-brand index fills in weeks 1–52. A patient is persistent if they have a paid
-- fill of the brand 48 or more weeks after the index fill, with no gap longer than 13 weeks
-- between fills (a 28-day supply plus a 60-day allowed gap).
CREATE OR REPLACE TABLE mart.persistence_12m AS
WITH paid AS (
    SELECT patient_id, brand, week, line_of_business,
           LAG(week) OVER (PARTITION BY patient_id, brand ORDER BY week, claim_id) AS previous_week
    FROM pharmacy_claims
    WHERE response_status = 'P'
),
index_fill AS (
    SELECT patient_id, brand, week AS index_week, line_of_business
    FROM paid
    WHERE (previous_week IS NULL OR week - previous_week > 52)
      AND week BETWEEN 1 AND 52
),
follow AS (
    SELECT i.patient_id, i.brand, i.index_week, i.line_of_business, p.week,
           p.week - LAG(p.week) OVER (PARTITION BY i.patient_id, i.brand, i.index_week ORDER BY p.week) AS gap
    FROM index_fill i
    JOIN paid p USING (patient_id, brand)
    WHERE p.week BETWEEN i.index_week AND i.index_week + 52
),
per_patient AS (
    SELECT patient_id, brand, index_week, line_of_business,
           MAX(week) AS last_week, COALESCE(MAX(gap), 0) AS longest_gap
    FROM follow
    GROUP BY ALL
)
SELECT brand, line_of_business,
       COUNT(*)                                                               AS new_to_brand_patients,
       AVG(CASE WHEN last_week >= index_week + 48 AND longest_gap <= 13 THEN 1 ELSE 0 END) AS persistence_12m
FROM per_patient
GROUP BY GROUPING SETS ((brand, line_of_business), (brand));
