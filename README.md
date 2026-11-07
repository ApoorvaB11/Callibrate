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
| [Data specification](docs/DATA_SPEC.md) | What the synthetic data contains and how it is generated |
| [Planted scenario answer key](docs/ANSWER_KEY.md) | The five patterns hidden in the data, and where to find them |
| [Calibration report](docs/CALIBRATION.md) | How close the data lands to its targets, regenerated with every build |

## Build progress

- [x] Research: market need, existing products, public data sources
- [x] Business Requirements Document
- [x] Functional Requirements Document
- [x] Synthetic data specification and planted-scenario answer key
- [x] Data generator, calibration checks and report
- [ ] SQL metric layer and reconciliation checks
- [ ] App screens (8)
- [ ] Priority score and lapsing model
- [ ] Limitations page, demo script and deployment

## Rebuild the data

```bash
pip install duckdb numpy pandas pyyaml scikit-learn faker zipcodes
python generator/generate.py     # about 30 seconds; writes data/callibrate.duckdb
python generator/calibrate.py    # checks the data and rewrites docs/CALIBRATION.md
```

## How data is handled

The data is calibrated to **published aggregates and stated assumptions**, listed in the BRD's data provenance register; checking those targets against CMS Part D and NPPES files is planned. The generator never reads a file containing real identifiers, no raw public file is stored in this repository, and every doctor ID is deliberately invalid so it cannot be mistaken for a real NPI. Prescription measures are synthetic paid-claim counts, not licensed audit data, and every finding is an association in synthetic data, not proof of cause.
