-- =============================================================================
-- 90_checks.sql — reconciliation checks (FR-82) and data-level acceptance tests (FRD)
--
-- Writes one row per check to mart.check_results. Every check states what is expected,
-- what was found, and whether it passed. sql/build.py adds two hand calculations (AT-02,
-- AT-03) that recompute numbers in Python, independently of this SQL.
-- =============================================================================

CREATE OR REPLACE TABLE mart.check_results AS

-- R01–R03: totals add up at every level of the geography
WITH s AS (SELECT * FROM mart.rx_summary(1, 104)),
roll_terr AS (
    SELECT t.district AS parent, s.brand, SUM(s.trx) AS trx
    FROM s JOIN territories t ON t.territory_id = s.area WHERE s.level = 'territory' GROUP BY ALL
),
roll_dist AS (
    SELECT t.region AS parent, s.brand, SUM(s.trx) AS trx
    FROM s JOIN (SELECT DISTINCT district, region FROM territories) t ON t.district = s.area
    WHERE s.level = 'district' GROUP BY ALL
),
roll_region AS (
    SELECT 'National' AS parent, brand, SUM(trx) AS trx FROM s WHERE level = 'region' GROUP BY ALL
)
SELECT 'R01' AS check_id, 'Reconciliation' AS category,
       'Territory TRx adds up to district TRx, every brand (weeks 1–104)' AS check_name,
       '0 mismatches' AS expected,
       COUNT(*) FILTER (WHERE r.trx <> s.trx) || ' mismatches across ' || COUNT(*) || ' district-brand totals' AS actual,
       COUNT(*) FILTER (WHERE r.trx <> s.trx) = 0 AND COUNT(*) = 20 AS passed
FROM roll_terr r JOIN s ON s.level = 'district' AND s.area = r.parent AND s.brand = r.brand
UNION ALL
SELECT 'R02', 'Reconciliation', 'District TRx adds up to region TRx, every brand', '0 mismatches',
       COUNT(*) FILTER (WHERE r.trx <> s.trx) || ' mismatches across ' || COUNT(*) || ' region-brand totals',
       COUNT(*) FILTER (WHERE r.trx <> s.trx) = 0 AND COUNT(*) = 8
FROM roll_dist r JOIN s ON s.level = 'region' AND s.area = r.parent AND s.brand = r.brand
UNION ALL
SELECT 'R03', 'Reconciliation', 'Region TRx adds up to national TRx, every brand', '0 mismatches',
       COUNT(*) FILTER (WHERE r.trx <> s.trx) || ' mismatches across ' || COUNT(*) || ' brand totals',
       COUNT(*) FILTER (WHERE r.trx <> s.trx) = 0 AND COUNT(*) = 4
FROM roll_region r JOIN s ON s.level = 'national' AND s.brand = r.brand

-- R04: prescription metrics tie back to the raw claims they are built from
UNION ALL
SELECT 'R04', 'Reconciliation', 'National TRx equals the count of paid pharmacy claims (weeks 1–104)',
       'Equal',
       (SELECT SUM(trx) FROM mart.rx_summary(1, 104) WHERE level = 'national') || ' TRx vs '
         || (SELECT COUNT(*) FROM pharmacy_claims WHERE response_status = 'P' AND week BETWEEN 1 AND 104) || ' paid claims',
       (SELECT SUM(trx) FROM mart.rx_summary(1, 104) WHERE level = 'national')
         = (SELECT COUNT(*) FROM pharmacy_claims WHERE response_status = 'P' AND week BETWEEN 1 AND 104)

-- R05: calls in the targeting view tie back to the raw call log
UNION ALL
SELECT 'R05', 'Reconciliation', 'National calls in the targeting view equal the raw call log (weeks 1–104, emails excluded)',
       'Equal',
       (SELECT calls FROM mart.targeting_summary(1, 104) WHERE level = 'national')::BIGINT || ' vs '
         || (SELECT COUNT(*) FROM calls WHERE channel <> 'email' AND week BETWEEN 1 AND 104),
       (SELECT calls FROM mart.targeting_summary(1, 104) WHERE level = 'national')
         = (SELECT COUNT(*) FROM calls WHERE channel <> 'email' AND week BETWEEN 1 AND 104)

-- R06: the three prescription counts nest correctly
UNION ALL
SELECT 'R06', 'Data integrity', 'NBRx ≤ NRx ≤ TRx for every doctor, brand and week', '0 violations',
       COUNT(*) FILTER (WHERE NOT (nbrx <= nrx AND nrx <= trx)) || ' violations in ' || COUNT(*) || ' rows',
       COUNT(*) FILTER (WHERE NOT (nbrx <= nrx AND nrx <= trx)) = 0
FROM weekly_rx

-- R07–R08 (AT-01): deciles
UNION ALL
SELECT 'R07', 'Acceptance test AT-01', 'Every doctor has exactly one decile in every quarter', '80,000 doctor-quarters, no duplicates',
       COUNT(*) || ' rows, ' || COUNT(DISTINCT (doctor_id, quarter)) || ' distinct doctor-quarters',
       COUNT(*) = 80000 AND COUNT(DISTINCT (doctor_id, quarter)) = 80000
FROM mart.doctor_decile
UNION ALL
SELECT 'R08', 'Acceptance test AT-01', 'Each decile 1–10 holds 9–11% of market volume, every quarter', 'All between 9% and 11%',
       'Range ' || ROUND(100 * MIN(share), 1) || '%–' || ROUND(100 * MAX(share), 1) || '%',
       MIN(share) >= 0.09 AND MAX(share) <= 0.11
FROM (SELECT quarter, decile, SUM(market_trx_52w) * 1.0 / SUM(SUM(market_trx_52w)) OVER (PARTITION BY quarter) AS share
      FROM mart.doctor_decile WHERE decile > 0 GROUP BY quarter, decile)

-- R09: every record points to something that exists
UNION ALL
SELECT 'R09', 'Data integrity', 'Every call, call-plan row and claim points to a known doctor, and every call to a known rep', '0 orphans',
       ((SELECT COUNT(*) FROM calls c ANTI JOIN doctors d ON d.doctor_id = c.doctor_id)
      + (SELECT COUNT(*) FROM calls c ANTI JOIN reps r ON r.rep_id = c.rep_id)
      + (SELECT COUNT(*) FROM call_plan p ANTI JOIN doctors d ON d.doctor_id = p.doctor_id)
      + (SELECT COUNT(*) FROM pharmacy_claims c ANTI JOIN doctors d ON d.doctor_id = c.synthetic_prescriber_id)) || ' orphans',
       ((SELECT COUNT(*) FROM calls c ANTI JOIN doctors d ON d.doctor_id = c.doctor_id)
      + (SELECT COUNT(*) FROM calls c ANTI JOIN reps r ON r.rep_id = c.rep_id)
      + (SELECT COUNT(*) FROM call_plan p ANTI JOIN doctors d ON d.doctor_id = p.doctor_id)
      + (SELECT COUNT(*) FROM pharmacy_claims c ANTI JOIN doctors d ON d.doctor_id = c.synthetic_prescriber_id)) = 0

-- R10: every rate is a real proportion
UNION ALL
SELECT 'R10', 'Data integrity', 'Reach, frequency attainment and adherence lie between 0% and 100% at every level (latest quarter)', 'All between 0 and 1',
       COUNT(*) FILTER (WHERE reach NOT BETWEEN 0 AND 1 OR frequency_attainment NOT BETWEEN 0 AND 1
                           OR call_plan_adherence NOT BETWEEN 0 AND 1) || ' out of range in ' || COUNT(*) || ' rows',
       COUNT(*) FILTER (WHERE reach NOT BETWEEN 0 AND 1 OR frequency_attainment NOT BETWEEN 0 AND 1
                           OR call_plan_adherence NOT BETWEEN 0 AND 1) = 0
FROM mart.coverage_summary(92, 104)

-- R11–R12 (part of AT-13): identifiers cannot be mistaken for real NPIs
UNION ALL
SELECT 'R11', 'Acceptance test AT-13', 'No synthetic doctor ID passes the NPI check digit', '0 of 10,000',
       COUNT(*) FILTER (WHERE mart.npi_is_valid(doctor_id)) || ' of ' || COUNT(*),
       COUNT(*) FILTER (WHERE mart.npi_is_valid(doctor_id)) = 0
FROM doctors
UNION ALL
SELECT 'R12', 'Data integrity', 'The NPI checker accepts a known valid test NPI and rejects a one-digit change', 'True, then False',
       mart.npi_is_valid('1993999998') || ', then ' || mart.npi_is_valid('1993999997'),
       mart.npi_is_valid('1993999998') AND NOT mart.npi_is_valid('1993999997')

-- R13: every prior-authorisation rejection gets exactly one outcome
UNION ALL
SELECT 'R13', 'Data integrity', 'Every prior-authorisation rejection has exactly one outcome (approved, switched, abandoned or pending)',
       'Counts equal',
       (SELECT COUNT(*) FROM mart.pa_rejection_outcome) || ' outcomes for '
         || (SELECT COUNT(*) FROM mart.first_fill_claim WHERE reject_code = '75') || ' rejections',
       (SELECT COUNT(*) FROM mart.pa_rejection_outcome) = (SELECT COUNT(*) FROM mart.first_fill_claim WHERE reject_code = '75')

-- AT-04: TRx equals paid claims for every territory, brand and week
UNION ALL
SELECT 'AT-04', 'Acceptance test AT-04', 'TRx equals the count of paid claims for every territory, brand and week', '0 mismatches',
       COUNT(*) FILTER (WHERE r.trx IS DISTINCT FROM c.paid) || ' mismatches in ' || COUNT(*) || ' territory-brand-weeks',
       COUNT(*) FILTER (WHERE r.trx IS DISTINCT FROM c.paid) = 0
FROM mart.rx_territory_week r
FULL JOIN (SELECT d.territory_id, pc.brand, pc.week, COUNT(*) AS paid
           FROM pharmacy_claims pc JOIN doctors d ON d.doctor_id = pc.synthetic_prescriber_id
           WHERE pc.response_status = 'P' AND pc.week BETWEEN 1 AND 104 GROUP BY ALL) c
  USING (territory_id, brand, week)

-- AT-05: the P3 vacancy territory is flagged below the 70% reach threshold during the vacancy
UNION ALL
SELECT 'AT-05', 'Acceptance test AT-05',
       'P3 vacancy: ' || (SELECT value FROM scenario_facts WHERE fact = 'territory')
         || ' reach to decile 8–10 targets falls below 70% in weeks 40–47 and is above 70% in weeks 27–39',
       'Below 70% during, above 70% before',
       ROUND(100 * (SELECT reach_decile_8_10 FROM mart.coverage_summary(40, 47)
                    WHERE area = (SELECT value FROM scenario_facts WHERE fact = 'territory')), 1) || '% during, '
         || ROUND(100 * (SELECT reach_decile_8_10 FROM mart.coverage_summary(27, 39)
                         WHERE area = (SELECT value FROM scenario_facts WHERE fact = 'territory')), 1) || '% before',
       (SELECT reach_decile_8_10 FROM mart.coverage_summary(40, 47) WHERE area = (SELECT value FROM scenario_facts WHERE fact = 'territory')) < 0.70
       AND (SELECT reach_decile_8_10 FROM mart.coverage_summary(27, 39) WHERE area = (SELECT value FROM scenario_facts WHERE fact = 'territory')) >= 0.70

-- AT-06: the three P2 territories rank highest on low-potential call share (latest quarter)
UNION ALL
SELECT 'AT-06', 'Acceptance test AT-06', 'P2 over-calling: the three planted territories rank top three on low-potential call share (weeks 92–104)',
       (SELECT value FROM scenario_facts WHERE fact = 'territories'),
       STRING_AGG(area || ' ' || ROUND(100 * low_potential_call_share) || '%', ', ' ORDER BY low_potential_call_share DESC),
       LIST_SORT(LIST(area)) = LIST_SORT(STRING_SPLIT((SELECT value FROM scenario_facts WHERE fact = 'territories'), ', '))
FROM (SELECT area, low_potential_call_share FROM mart.targeting_summary(92, 104)
      WHERE level = 'territory' ORDER BY low_potential_call_share DESC LIMIT 3)

-- AT-07: the P4 cluster shows low in-person reach but much higher omnichannel reach (latest quarter)
UNION ALL
SELECT 'AT-07', 'Acceptance test AT-07',
       'P4 restricted cluster: metro-Atlanta endocrinologist targets have in-person reach below 25% and omnichannel reach above 75% (weeks 92–104)',
       'In person < 25%, omnichannel > 75%',
       ROUND(100 * AVG(reached_in_person::INT)) || '% in person, ' || ROUND(100 * AVG(touched_any::INT)) || '% omnichannel ('
         || COUNT(*) || ' targets; ' || ROUND(100 * AVG(reached::INT)) || '% reached by any call)',
       AVG(reached_in_person::INT) < 0.25 AND AVG(touched_any::INT) > 0.75
FROM mart.coverage(92, 104) c
JOIN doctors d USING (doctor_id)
WHERE d.specialty = 'endocrinology' AND d.state = 'GA'
  AND d.county IN ('Fulton County', 'DeKalb County', 'Cobb County', 'Gwinnett County')

-- AT-09: after the P1 formulary change, the Gulf region shows effort held but new patients falling
UNION ALL
SELECT 'AT-09', 'Acceptance test AT-09',
       'P1 formulary shock (12 weeks after week 88 vs 12 before): Gulf NBRx falls at least 10 points more than the Southeast while Gulf calls stay within ±5%, and most Gulf territories sit in the effort-held, outcome-fell quadrant',
       'Gap ≤ −10 points; calls within ±5%; >50% of Gulf territories in quadrant',
       'Gulf NBRx ' || ROUND(100 * g.nbrx_change) || '% vs Southeast ' || ROUND(100 * s.nbrx_change) || '%; Gulf calls '
         || ROUND(100 * g.calls_change) || '%; quadrant: ' || g.territories_effort_held_outcome_fell || ' of ' || g.territories
         || ' Gulf territories, ' || s.territories_effort_held_outcome_fell || ' of ' || s.territories || ' Southeast',
       g.nbrx_change - s.nbrx_change <= -0.10
       AND ABS(g.calls_change) <= 0.05
       AND g.territories_effort_held_outcome_fell * 2 > g.territories
FROM mart.before_after_rollup(88, 12) g, mart.before_after_rollup(88, 12) s
WHERE g.area = 'gulf' AND s.area = 'southeast';
