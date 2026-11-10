-- =============================================================================
-- 02_prescriptions.sql — M-01 TRx, M-02 NRx, M-03 NBRx, M-04 TRx share, M-05 NBRx share
--
-- weekly_rx is built by the generator from PAID pharmacy claims only:
--   TRx  = all paid claims (new + refill)
--   NRx  = paid claims with fill number 0 (first fill of a new prescription number) — a proxy
--   NBRx = paid claims where the patient had no paid fill of that brand in the previous 52 weeks
--          (new starts, switches, add-ons, restarts) — a proxy; it counts prescriptions, not patients
-- These are synthetic paid-claim counts, not a licensed, projected audit such as IQVIA Xponent.
-- =============================================================================

-- Weekly prescriptions by territory and brand (reporting weeks 1–104)
CREATE OR REPLACE TABLE mart.rx_territory_week AS
SELECT
    d.territory_id, d.territory_name, d.district, d.district_label, d.region, d.region_label,
    r.brand,
    r.week,
    SUM(r.trx)  AS trx,
    SUM(r.nrx)  AS nrx,
    SUM(r.nbrx) AS nbrx
FROM weekly_rx r
JOIN mart.dim_doctor d ON d.doctor_id = r.doctor_id
WHERE r.week BETWEEN 1 AND 104
GROUP BY ALL;

-- Prescription summary for any period [w0, w1], at every level of the geography at once.
-- GROUPING SETS gives one row per territory, district, region and the nation, so the same
-- numbers can be checked to add up (see 90_checks.sql).
--   Example: SELECT * FROM mart.rx_summary(92, 104) WHERE level = 'national';
CREATE OR REPLACE MACRO mart.rx_summary(w0, w1) AS TABLE
WITH base AS (
    SELECT region, district, territory_id, brand,
           SUM(trx) AS trx, SUM(nrx) AS nrx, SUM(nbrx) AS nbrx
    FROM mart.rx_territory_week
    WHERE week BETWEEN w0 AND w1
    GROUP BY GROUPING SETS ((region, district, territory_id, brand),
                            (region, district, brand),
                            (region, brand),
                            (brand))
)
SELECT
    CASE WHEN territory_id IS NOT NULL THEN 'territory'
         WHEN district     IS NOT NULL THEN 'district'
         WHEN region       IS NOT NULL THEN 'region'
         ELSE 'national' END                                        AS level,
    COALESCE(territory_id, district, region, 'National')            AS area,
    brand, trx, nrx, nbrx,
    -- M-04 and M-05: brand share of the four-brand market in the same area and period
    trx  / SUM(trx)  OVER (PARTITION BY region, district, territory_id)  AS trx_share,
    nbrx / SUM(nbrx) OVER (PARTITION BY region, district, territory_id)  AS nbrx_share
FROM base;
