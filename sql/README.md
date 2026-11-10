# Callibrate — SQL metric layer

Every number Callibrate shows is calculated here, once, in SQL (DuckDB). Each file covers one metric group and is commented in plain English, so any number on screen can be traced to its formula. Metric IDs (M-01 to M-18) match the [FRD](../docs/FRD.md#metric-definitions).

```bash
python sql/build.py    # runs every file in order, then all checks; writes docs/METRICS_CHECK.md
```

## Files

| File | What it calculates | Metrics | Main objects |
| --- | --- | --- | --- |
| `01_base.sql` | Clean doctor and interaction tables, quarter helper, NPI check-digit test | — | `mart.dim_doctor`, `mart.fct_interaction`, `mart.npi_is_valid()` |
| `02_prescriptions.sql` | Prescriptions and market share by territory, district, region and nation | M-01 to M-05 | `mart.rx_territory_week`, `mart.rx_summary(w0, w1)` |
| `03_targeting.sql` | Volume-weighted deciles each quarter; where calls go; the misallocation quadrant | M-06, M-11, M-12 | `mart.doctor_decile`, `mart.targeting(w0, w1)`, `mart.targeting_summary(w0, w1)` |
| `04_coverage_execution.sql` | Reach, frequency and adherence against the call plan; rep scorecard; missed doctors | M-07 to M-10, M-16, M-17 | `mart.coverage(w0, w1)`, `mart.coverage_summary(w0, w1)`, `mart.coverage_by_access(w0, w1)`, `mart.rep_scorecard(w0, w1)`, `mart.missed_targets(w0, w1)` |
| `05_payer_access.sql` | First-fill rejections, what happens after a prior-authorisation rejection, persistence | M-13 to M-15, M-18 | `mart.first_fill_claim`, `mart.pa_rejection_outcome`, `mart.first_fill_week`, `mart.payer_summary(w0, w1)`, `mart.persistence_12m` |
| `06_priority_score.sql` | The four opportunity drivers and their plain-English reasons | C1 | `mart.priority_drivers(as_of)` |
| `07_diagnose.sql` | Before/after comparison of effort, outcome and access around a chosen week | FR-70, FR-73 | `mart.before_after(week, n)`, `mart.before_after_rollup(week, n)` |
| `90_checks.sql` | Reconciliation checks and data-level acceptance tests | FR-82 | `mart.check_results` |

## How to read the objects

- **Tables** (`mart.dim_doctor`, `mart.doctor_decile` and so on) are built once per run.
- **Table macros** with `(w0, w1)` take any period in weeks, so the app's period filter (FR-02) reuses the same logic. Weeks 1–104 run Saturday to Friday; the latest full quarter is weeks 92–104.
- **Summaries** use `GROUPING SETS` to return territory, district, region and national rows from the same calculation. That is why the reconciliation checks can prove each level adds up to the next.

```sql
-- Coverage for the latest quarter, every level at once
SELECT * FROM mart.coverage_summary(92, 104) ORDER BY level, area;

-- Top 20 doctors by default opportunity score as of week 104
SELECT doctor_name, territory_id, decile, access_tier, default_score, reason_potential, reason_momentum
FROM mart.priority_drivers(104)
WHERE eligible_for_list AND NOT resting_after_recent_calls
ORDER BY default_score DESC
LIMIT 20;

-- The formulary shock: 12 weeks after week 88 against the 12 weeks before, by region
SELECT * FROM mart.before_after_rollup(88, 12) WHERE level = 'region';
```

## Conventions that apply everywhere

- Only **paid** claims count as prescriptions; TRx, NRx and NBRx are synthetic paid-claim counts, not licensed audit data.
- Only in-person and remote interactions count as **calls**; emails count as touches.
- The **call plan and decile** for a period are those of the quarter containing its last week.
- Planned calls are **scaled to the period length**, and adherence caps each doctor's calls at their plan.
- Findings are **associations** in synthetic data, never proof of cause.
