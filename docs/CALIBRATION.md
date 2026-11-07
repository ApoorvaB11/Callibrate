# Callibrate — calibration report

Generated 2026-11-07 by `generator/calibrate.py` from seed 20261107. Checks with a target of ±2 percentage points show Pass or Fail; the rest are reported for review.

## Calibration checks

| Check | Target | Actual | Result |
| --- | --- | --- | --- |
| Share of GLP-1 volume: Family medicine | 28.0% | 28.1% | Pass |
| Share of GLP-1 volume: Internal medicine | 22.0% | 22.1% | Pass |
| Share of GLP-1 volume: Nurse practitioner | 17.0% | 17.8% | Pass |
| Share of GLP-1 volume: Physician assistant | 8.0% | 8.0% | Pass |
| Share of GLP-1 volume: Endocrinology | 12.0% | 12.4% | Pass |
| Share of GLP-1 volume: Cardiology | 6.0% | 5.5% | Pass |
| Share of GLP-1 volume: Nephrology | 3.0% | 2.7% | Pass |
| Share of GLP-1 volume: Other | 4.0% | 3.4% | Pass |
| Prescribers in deciles 8–10 | 12.0% | 11.4% | Pass |
| Glyvexa NBRx share (weeks 1–104) | 28.0% | 27.4% | Pass |
| TRx share: Glyvexa / Sucrelo / Metaryn / Orvalis | Illustrative | 25.7% / 39.9% / 11.8% / 22.6% |  |
| Channel mix: in person / remote / email | 55% / 15% / 30% | 56.1% / 18.1% / 25.8% |  |
| In-person calls per rep per field day | About 7 (range 5–9) | 6.2 |  |
| National call-plan adherence (M-09) | Illustrative, 70–85% | 82.8% |  |
| Access tiers: open / limited / no-see | 60% / 32% / 8% | 60.2% / 31.5% / 8.3% |  |
| 12-month persistence (new-to-brand starts in weeks 1–52) | About 60% | 58.3% |  |
| Each decile's share of market volume | 9–11% | 10.0%–10.0% | Pass |
| Synthetic prescriber IDs that pass the NPI check digit | 0 | 0 | Pass |
| Written prescriptions that never become a paid fill of any brand | 27–40% (published range) | 28.7% | Pass |

## New-prescription funnel

Only the rows from "Presented at a pharmacy" down can be seen in claims data; prescriptions never taken to a pharmacy leave no claim.

| Stage | Prescriptions | Share of written |
| --- | --- | --- |
| New prescriptions written (weeks 1–104) | 287,501 | 100% |
| Never taken to a pharmacy (invisible in claims data) | 71,921 | 25.0% |
| Presented at a pharmacy | 215,580 | 75.0% |
| Rejected at first fill for prior authorisation (code 75) | 73,669 | 25.6% |
| then approved and paid | 54,709 | 19.0% |
| then abandoned (no paid claim) | 10,493 | 3.6% |
| then switched to a competitor | 8,467 | 2.9% |

## Rejected claims by reason (weeks 1–104)

| NCPDP code | Meaning | Claims | Share |
| --- | --- | --- | --- |
| 75 | Prior authorisation required | 73,669 | 53.3% |
| 79 | Refill too soon | 43,858 | 31.8% |
| 76 | Plan limitations exceeded | 18,536 | 13.4% |
| 65 | Patient not covered | 2,036 | 1.5% |

## Planted scenarios

| Scenario | What the data shows |
| --- | --- |
| P1 Formulary shock (Bayou Senior Advantage, week 88) | Share of new Glyvexa prescriptions on the plan rejected for prior authorisation: 0.0% in the 12 weeks before, 41.8% in the 12 weeks after. Glyvexa NBRx, 12 weeks after (89–100) against 12 weeks before (76–87): affected territories -21%, other territories -1%, a gap of -20 points. TRx in affected territories +3%; calls there -2%. A synthetic association designed into the data, not evidence of real-world cause. |
| P2 Over-calling | Planted territories AL_MS-03, FL_NORTH-01, GEORGIA-08. Highest low-potential call share: FL_NORTH-01 52.0%; GEORGIA-08 51.0%; AL_MS-03 50.8%; FL_NORTH-03 41.8%; FL_NORTH-06 41.4%. The three planted territories rank top three. |
| P3 Vacancy | FL_NORTH-04: share of decile 8–10 targets seen in weeks 32–39 80.8%, in the vacancy weeks 40–47 0.0%. |
| P4 Restricted cluster | No-see share among endocrinologists: metro Atlanta 91.7%, elsewhere 7.7%. |
| P5 Lapsing writers | 27 planted lapses plus decoys that do not lapse: call gap 9, competitor push 11, silent 7, decoy call gap 15, decoy dip 15. |
