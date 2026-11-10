# Callibrate — metric layer checks

Generated 2026-11-10 by `sql/build.py`. **20 of 20 checks pass.** Reconciliation checks prove the numbers add up and tie back to the raw data; acceptance tests come from the FRD. AT-08, AT-10, AT-11 and the app-facing parts of AT-13 are tested once the app is built; AT-12 is in [CALIBRATION.md](CALIBRATION.md).

| ID | Type | Check | Expected | Actual | Result |
| --- | --- | --- | --- | --- | --- |
| R01 | Reconciliation | Territory TRx adds up to district TRx, every brand (weeks 1–104) | 0 mismatches | 0 mismatches across 20 district-brand totals | Pass |
| R02 | Reconciliation | District TRx adds up to region TRx, every brand | 0 mismatches | 0 mismatches across 8 region-brand totals | Pass |
| R03 | Reconciliation | Region TRx adds up to national TRx, every brand | 0 mismatches | 0 mismatches across 4 brand totals | Pass |
| R04 | Reconciliation | National TRx equals the count of paid pharmacy claims (weeks 1–104) | Equal | 3092890 TRx vs 3092890 paid claims | Pass |
| R05 | Reconciliation | National calls in the targeting view equal the raw call log (weeks 1–104, emails excluded) | Equal | 170250 vs 170250 | Pass |
| R06 | Data integrity | NBRx ≤ NRx ≤ TRx for every doctor, brand and week | 0 violations | 0 violations in 2056358 rows | Pass |
| R07 | Acceptance test AT-01 | Every doctor has exactly one decile in every quarter | 80,000 doctor-quarters, no duplicates | 80000 rows, 80000 distinct doctor-quarters | Pass |
| R08 | Acceptance test AT-01 | Each decile 1–10 holds 9–11% of market volume, every quarter | All between 9% and 11% | Range 10.0%–10.0% | Pass |
| R09 | Data integrity | Every call, call-plan row and claim points to a known doctor, and every call to a known rep | 0 orphans | 0 orphans | Pass |
| R10 | Data integrity | Reach, frequency attainment and adherence lie between 0% and 100% at every level (latest quarter) | All between 0 and 1 | 0 out of range in 48 rows | Pass |
| R11 | Acceptance test AT-13 | No synthetic doctor ID passes the NPI check digit | 0 of 10,000 | 0 of 10000 | Pass |
| R12 | Data integrity | The NPI checker accepts a known valid test NPI and rejects a one-digit change | True, then False | true, then false | Pass |
| R13 | Data integrity | Every prior-authorisation rejection has exactly one outcome (approved, switched, abandoned or pending) | Counts equal | 109606 outcomes for 109606 rejections | Pass |
| AT-02 | Acceptance test AT-02 | Reach and average frequency for GEORGIA-03 (weeks 92–104), recalculated by hand in Python | SQL equals hand calculation | SQL 78.7% reach, 3.91 calls; hand 78.7%, 3.91 | Pass |
| AT-03 | Acceptance test AT-03 | Call-plan adherence for rep R027 (GEORGIA-03, weeks 92–104) and the missed-doctor list, recalculated by hand | SQL equals hand calculation; same missed doctors | SQL 79.5%, hand 79.5%; missed doctors 32 in SQL, 32 by hand | Pass |
| AT-04 | Acceptance test AT-04 | TRx equals the count of paid claims for every territory, brand and week | 0 mismatches | 0 mismatches in 16640 territory-brand-weeks | Pass |
| AT-05 | Acceptance test AT-05 | P3 vacancy: FL_NORTH-04 reach to decile 8–10 targets falls below 70% in weeks 40–47 and is above 70% in weeks 27–39 | Below 70% during, above 70% before | 0.0% during, 92.3% before | Pass |
| AT-06 | Acceptance test AT-06 | P2 over-calling: the three planted territories rank top three on low-potential call share (weeks 92–104) | AL_MS-03, FL_NORTH-01, GEORGIA-08 | FL_NORTH-01 53.0%, GEORGIA-08 51.0%, AL_MS-03 50.0% | Pass |
| AT-07 | Acceptance test AT-07 | P4 restricted cluster: metro-Atlanta endocrinologist targets have in-person reach below 25% and omnichannel reach above 75% (weeks 92–104) | In person < 25%, omnichannel > 75% | 8.0% in person, 100.0% omnichannel (12 targets; 67.0% reached by any call) | Pass |
| AT-09 | Acceptance test AT-09 | P1 formulary shock (12 weeks after week 88 vs 12 before): Gulf NBRx falls at least 10 points more than the Southeast while Gulf calls stay within ±5%, and most Gulf territories sit in the effort-held, outcome-fell quadrant | Gap ≤ −10 points; calls within ±5%; >50% of Gulf territories in quadrant | Gulf NBRx -17.0% vs Southeast 5.0%; Gulf calls -3.0%; quadrant: 11 of 16 Gulf territories, 1 of 24 Southeast | Pass |

## Headline numbers, latest quarter (weeks 92–104)

Synthetic data: these describe the fictional market, not any real brand.

| Metric | Value |
| --- | --- |
| Glyvexa TRx (M-01) | 127,564 (+5.0% on the previous quarter) |
| Glyvexa NBRx (M-03) | 7,225 (-4.2%) |
| Glyvexa TRx share / NBRx share (M-04, M-05) | 27.2% / 28.6% |
| Reach, all targets / decile 8–10 targets (M-07) | 82.8% / 93.9% |
| In-person reach / omnichannel reach (M-16, M-17) | 71.4% / 96.3% |
| Average frequency of reached targets (M-08) | 3.9 calls |
| Call-plan adherence (M-09) | 82.7% |
| Calls on non-targets / on decile 0–4 doctors (M-11, M-12) | 9.0% / 35.1% |
| Under-called decile 8–10 doctors / over-called decile 0–4 doctors | 262 / 2,212 |
| Glyvexa 12-month persistence (M-18) | 58.6% |

**Reach by access tier**

| Access tier | Targets | In-person reach | Remote reach | Email reach | Omnichannel reach |
| --- | --- | --- | --- | --- | --- |
| open | 3,619 | 90.0% | 23.3% | 46.6% | 95.8% |
| limited | 1,885 | 54.6% | 64.5% | 86.9% | 97.3% |
| no_see | 496 | 0.0% | 31.2% | 94.4% | 96.4% |

**Formulary shock (P1): 12 weeks after week 88 against the 12 weeks before**

Bayou Senior Advantage, weeks 89–100: 63.9% of new Glyvexa prescriptions rejected for prior authorisation; of those, 35.0% were approved, 31.1% abandoned and 33.9% switched to a competitor within 30 days.

| Area | Glyvexa NBRx | Glyvexa TRx | Calls |
| --- | --- | --- | --- |
| National | -3.8% | +5.6% | -1.9% |
| Gulf | -16.7% | +3.9% | -2.6% |
| Southeast | +5.2% | +6.7% | -1.5% |

An association designed into synthetic data, not evidence of a real-world cause.
