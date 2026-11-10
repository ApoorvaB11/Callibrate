-- =============================================================================
-- 01_base.sql — clean building blocks every other file uses
--
-- Everything Callibrate calculates lives in the "mart" schema, so the raw
-- synthetic tables (doctors, calls, pharmacy_claims, ...) stay untouched.
-- Week numbers: weeks 1–104 are the reporting period, Saturday to Friday.
-- A quarter (one call cycle) is 13 weeks: quarter = (week - 1) // 13 + 1.
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS mart;

-- Doctor dimension: one row per doctor, with geography and a simple specialty group
CREATE OR REPLACE TABLE mart.dim_doctor AS
SELECT
    d.doctor_id,
    d.doctor_name,
    d.credential,
    d.specialty,
    d.specialty_label,
    CASE
        WHEN d.specialty IN ('family_medicine', 'internal_medicine')       THEN 'Primary care physician'
        WHEN d.specialty IN ('nurse_practitioner', 'physician_assistant')  THEN 'NP or PA'
        WHEN d.specialty = 'endocrinology'                                 THEN 'Endocrinology'
        ELSE 'Other specialty'
    END                     AS specialty_group,
    d.city, d.county, d.state, d.zip, d.lat, d.lon,
    d.territory_id,
    t.territory_name,
    t.district,
    t.district_label,
    t.region,
    t.region_label,
    d.access_tier,          -- open, limited or no_see
    d.pdrp_optout           -- AMA PDRP opt-out: hide doctor-level prescribing in manager views
FROM doctors d
JOIN territories t ON t.territory_id = d.territory_id;

-- Calls: every rep interaction, with its quarter and whether it counts as a "call".
-- Convention (FRD): in-person and remote interactions are calls; emails are touches.
CREATE OR REPLACE TABLE mart.fct_interaction AS
SELECT
    c.call_id,
    c.call_date,
    c.week,
    (c.week - 1) // 13 + 1                      AS quarter,
    c.rep_id,
    c.doctor_id,
    c.territory_id,
    c.channel,                                  -- in_person, remote or email
    c.channel IN ('in_person', 'remote')        AS is_call
FROM calls c;

-- Helper: which quarter a week belongs to
CREATE OR REPLACE MACRO mart.quarter_of(w) AS ((w - 1) // 13 + 1);

-- Helper: does a 10-digit ID pass the real NPI check digit?
-- NPI rule: Luhn check over the prefix 80840 plus the first nine digits.
-- Every Callibrate doctor ID is built to FAIL this test, so none can be mistaken for a real NPI.
CREATE OR REPLACE MACRO mart.npi_is_valid(id) AS (
    length(id) = 10
    AND left(id, 1) IN ('1', '2')
    AND (10 - list_sum(list_transform(range(1, 15), lambda k:
            CASE
                WHEN k % 2 = 1 THEN
                    CASE WHEN 2 * CAST(substr('80840' || left(id, 9), 15 - k, 1) AS INT) > 9
                         THEN 2 * CAST(substr('80840' || left(id, 9), 15 - k, 1) AS INT) - 9
                         ELSE 2 * CAST(substr('80840' || left(id, 9), 15 - k, 1) AS INT) END
                ELSE CAST(substr('80840' || left(id, 9), 15 - k, 1) AS INT)
            END)) % 10) % 10 = CAST(right(id, 1) AS INT)
);
