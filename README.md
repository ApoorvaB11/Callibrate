# Callibrate

US pharma sales-force effectiveness and doctor-targeting analytics on fully synthetic data. Portfolio project by Apoorva Bhardwaj.

> **All data in this project is synthetic.** No real doctor, rep, company, brand or prescription appears anywhere. Callibrate, Glyvexa and Corvane Pharma are working names.

## What it is

Pharma brand teams send reps to visit doctors, but access is shrinking and target lists are hard to trust. Callibrate shows a commercial analyst, in one explainable view:

- **Where field effort goes:** reach, frequency and call-plan adherence by territory, rep and doctor segment.
- **Where it is wasted:** calls spent on low-potential doctors and high-value doctors left uncovered.
- **Who to see next, and why:** a transparent priority score with a plain-English reason for every doctor.
- **Who is drifting away:** a back-tested lapsing-prescriber flag, labelled as illustrative.
- **Why performance moved:** a planted scenario where a health plan adds prior authorisation and new-to-brand prescriptions fall, traceable down to pharmacy-claim reject codes.

The setting is a fictional once-weekly GLP-1-class brand for type 2 diabetes in the US market.

## Documents

| Document | What it covers |
| --- | --- |
| [Business Requirements (BRD)](docs/BRD.md) | Problem, scope, personas, objectives, business requirements, data and compliance rules |
| [Functional Requirements (FRD)](docs/FRD.md) | Screens, metric formulas, priority score, lapsing model, data generation, acceptance tests |

## Build progress

- [x] Research: market need, existing products, public data sources
- [x] Business Requirements Document
- [x] Functional Requirements Document
- [ ] Synthetic data specification and planted-scenario answer key
- [ ] Data generator
- [ ] SQL metric layer and reconciliation checks
- [ ] App screens (8)
- [ ] Priority score and lapsing model
- [ ] Limitations page, demo script and deployment

## How data is handled

Public US government data (Medicare Part D, NPPES, CMS formulary files, CDC PLACES) is used only to calibrate **aggregate distributions**. Identifiers are discarded, raw public files are never stored in this repository, and every doctor ID is deliberately invalid so it cannot be mistaken for a real NPI.
