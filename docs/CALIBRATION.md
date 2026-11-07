# Callibrate — calibration report

Generated 2026-11-07 by `generator/calibrate.py` from seed 20261107. Checks with a target of ±2 percentage points show Pass or Fail; the rest are reported for review.

## Calibration checks

| Check | Target | Actual | Result |
| --- | --- | --- | --- |
| Share of GLP-1 volume: Family medicine | 28.0% | 28.3% | Pass |
| Share of GLP-1 volume: Internal medicine | 22.0% | 21.9% | Pass |
| Share of GLP-1 volume: Nurse practitioner | 17.0% | 17.7% | Pass |
| Share of GLP-1 volume: Physician assistant | 8.0% | 8.0% | Pass |
| Share of GLP-1 volume: Endocrinology | 12.0% | 12.5% | Pass |
| Share of GLP-1 volume: Cardiology | 6.0% | 5.4% | Pass |
| Share of GLP-1 volume: Nephrology | 3.0% | 2.7% | Pass |
| Share of GLP-1 volume: Other | 4.0% | 3.5% | Pass |
| Prescribers in deciles 8–10 | 12.0% | 11.3% | Pass |
| Glyvexa NBRx share (weeks 1–104) | 28.0% | 27.2% | Pass |
| TRx share: Glyvexa / Sucrelo / Metaryn / Orvalis | Illustrative | 25.5% / 40.3% / 11.5% / 22.7% |  |
| Channel mix: in person / remote / email | 55% / 15% / 30% | 56.3% / 18.0% / 25.6% |  |
| In-person calls per rep per field day | About 7 (range 5–9) | 6.2 |  |
| National call-plan adherence (M-09) | Illustrative, 70–85% | 82.7% |  |
| Access tiers: open / limited / no-see | 60% / 32% / 8% | 60.2% / 31.5% / 8.3% |  |
| 12-month persistence | About 60% | 58.2% |  |
| Doctor IDs that pass the NPI check digit | 0 | 0 | Pass |

## Planted scenarios

| Scenario | What the data shows |
| --- | --- |
| P1 Formulary shock (Bayou Senior Advantage, week 88) | Glyvexa first-fill rejection on the plan 0.0% before, 41.3% after. In the six affected territories Glyvexa NBRx changed -17% and TRx +5% (two weeks after the change against the 14 weeks before), while calls changed -3%. Other territories: NBRx -3%, TRx +7%. |
| P2 Over-calling | Planted territories AL_MS-03, FL_NORTH-01, GEORGIA-08. Highest low-potential call share: GEORGIA-08 54.4%; FL_NORTH-01 54.3%; AL_MS-03 47.7%; FL_NORTH-06 44.1%; AL_MS-02 42.4%. The three planted territories rank top three. |
| P3 Vacancy | FL_NORTH-04: share of decile 8–10 targets seen in weeks 32–39 87.0%, in the vacancy weeks 40–47 0.0%. |
| P4 Restricted cluster | No-see share among endocrinologists: metro Atlanta 91.7%, elsewhere 7.7%. |
| P5 Lapsing writers | 30 planted lapses: call_gap 8, competitor_push 13, silent 9. |
