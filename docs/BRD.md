# Callibrate — Business Requirements Document

Last updated 7 Nov 2026 · Product owner: Apoorva Bhardwaj

## Summary

Callibrate is a portfolio web app that helps a US pharma commercial team calibrate its field effort: where rep calls go, whether they reach the right doctors, and which doctors to prioritise next. It runs entirely on synthetic data for a fictional once-weekly GLP-1-class brand for type 2 diabetes. Every doctor, rep, prescription, company and brand name is invented.

| Item | Detail |
| --- | --- |
| Product owner | Apoorva Bhardwaj |
| Status | Draft 0.1; version 1 scope agreed 7 Nov 2026 |
| Market setting | United States, type 2 diabetes, GLP-1 class |
| Fictional brand | Glyvexa (once-weekly injectable) from Corvane Pharma, competing with three fictional brands |
| Primary user | Commercial or sales-operations analyst at the brand team |
| Secondary user | District sales manager |
| Version 1 features | A1–A5, B1–B4, C1, C3, D1–D3 (see Scope) |
| Build approach | Python web app; every metric calculated in SQL so the product owner can read and defend each number |

The name Callibrate joins "call" and "calibrate". It and all brand and company names will be checked against real trademarks before publishing.

## Business context and problem

US pharma field teams must choose which doctors to see with fewer reps and less access, and the targeting tools they use are hard to trust.

- **Access is shrinking.** The share of US doctors accessible to reps fell from 60% in 2022 to 45% in 2024 ([Veeva Pulse](https://veeva.com/wp-content/uploads/2024/05/Veeva-Pulse-Report-Top-Insights-1Q24.pdf)).
- **Leaders name targeting and data as the problem.** In a survey of 130 biopharma executives, 81% struggle to make sellers effective, 79% struggle with targeting and 85% cite data silos ([IQVIA](https://www.iqvia.com/-/media/iqvia/pdfs/library/insight-brief/overcoming-7-top-challenges-of-commercial-leaders.pdf)).
- **Reps ignore lists they cannot explain.** Vendors are moving from quarterly target lists to weekly re-ranking with a stated reason per doctor ([ZS ZAIDYN](https://zaidyn.zs.com/products/zaidyn-commercial/customer-engagement/dynamic-targeting)).
- **Measurement is shifting from activity to outcomes.** Leaders still track call counts while the industry moves towards new-patient starts ([Deloitte](https://www.deloitte.com/us/en/industries/life-sciences-health-care/blogs/health-care/can-ai-help-biopharma-sales-reps-become-more-effective.html)).

**Why the GLP-1 class.** Type 2 diabetes is a crowded, high-volume market where payer coverage decides much of what doctors can prescribe. Price pressure is rising: Medicare's negotiated price for semaglutide (Ozempic) is $274 a month against a $959 list price, effective 2027 ([Fierce Healthcare](https://www.fiercehealthcare.com/pharma/medicare-unveils-price-reductions-15-drugs-including-novos-semaglutide)). With margins under pressure, wasted field effort costs more.

**Problem statement.** The analyst on a GLP-1-class brand team has no single view tying rep activity, doctor value, payer coverage and prescription outcomes together. As a result, call plans are set quarterly from static deciles, misallocated calls go unnoticed, and doctors who are drifting away from the brand are found too late.

Most figures above come from vendors and consultancies, so Callibrate treats them as context, not proof.

## Scope

Version 1 has 14 features: five core views, four differentiators, two AI features and three trust foundations. Everything else is either a later phase or out of scope.

**Version 1 (in scope)**

| ID | Feature | Group | Main user |
| --- | --- | --- | --- |
| A1 | Decile and segment matrix | Core | Analyst |
| A2 | Reach and frequency against target, by segment | Core | Both |
| A3 | Call-plan adherence scorecard by rep and district, with missed doctors | Core | Manager |
| A4 | Prescription trends: TRx, NRx, NBRx and market share | Core | Analyst |
| A5 | Territory coverage map | Core | Analyst |
| B1 | Misallocation quadrant: over-called and under-called doctors | Differentiator | Analyst |
| B2 | Access tiers: open, limited and restricted doctors | Differentiator | Both |
| B3 | Planted diagnostic story in the data | Differentiator | Analyst |
| B4 | Activity against outcome panel | Differentiator | Analyst |
| C1 | Explainable priority score with reasons and adjustable weights | AI | Both |
| C3 | Lapsing-prescriber flag, back-tested and labelled synthetic | AI | Analyst |
| D1 | Synthetic data shaped on public US data | Trust | All |
| D2 | Compliance by design | Trust | All |
| D3 | Metric definitions, data dictionary, reconciliation and limitations | Trust | All |

**Out of scope**

- Real company, brand, doctor or rep data
- CRM integration or a rep-facing mobile app
- Incentive compensation and quota setting (B6), channel mix (B7) and multi-brand collision (B8)
- Plain-English question answering (C6) and black-box machine-learning models (C7)
- Cosmetic Botox, which uses a different, account-based sales model

## Users and personas

Callibrate serves three people who share one question: is our field effort landing on the doctors who matter? Two are analysts (one in-house, one consulting) and one is a front-line manager. All three are fictional.

### Priya, commercial analyst at Corvane Pharma (primary)

It is Monday morning and the Glyvexa brand lead wants to know, by Wednesday's review, why new-to-brand prescriptions dipped last month. Priya's data sits in four places: CRM call extracts, a weekly prescription file, a payer coverage sheet and the territory alignment. Stitching them together usually eats two days, and by then the conversation has moved on. Each quarter she also rebuilds the call plan from static deciles, knowing reps will ignore half of it because the list never says why a doctor is on it.

**With Callibrate**, Priya opens one app, sees that the dip sits in one region, traces it to a health plan that moved Glyvexa to prior authorisation, and walks into Wednesday's meeting with a cause, not a guess. Her refreshed target list now carries a reason beside every doctor.

### Arjun, associate consultant at a commercial analytics firm (primary)

Arjun joined a pharma consulting firm from a healthcare IT role. His client, the Glyvexa brand team, has asked for a field-force effectiveness diagnostic ahead of next year's call-plan reset, and the steering committee meets in two weeks. He needs to show, in a handful of slides, where calls are wasted, which high-value doctors are uncovered, and what to change. He also needs every number to survive a sceptical client VP asking "how did you calculate that?"

**With Callibrate**, Arjun pulls the misallocation view, the coverage gaps and the access-tier split straight into his storyline. The written metric definitions answer the VP's question before it is asked.

### Marcus, district sales manager (secondary)

Marcus leads 8 reps across two states. On Friday afternoons he plans next week's ride-alongs, but his report only shows call totals, so a rep who hit 100% of calls on low-value doctors looks like a top performer. Nearly half of his high-value endocrinologists now only take remote meetings, and he has no view of that at all.

**With Callibrate**, Marcus sees each rep's call-plan adherence, the high-value doctors each rep missed, and which doctors need remote contact. His coaching conversations start from evidence.

### At a glance

|  | Priya (analyst) | Arjun (consultant) | Marcus (manager) |
| --- | --- | --- | --- |
| Rhythm | Weekly review, quarterly call-plan reset | Project-based diagnostics, steering-committee decks | Weekly coaching |
| Core question | Why did performance move, and who do we target next? | Where is field effort misallocated, and what should change? | Which reps and doctors need attention this week? |
| Must trust | Every number traces to a definition | Every number survives client challenge | The list reflects what really matters |
| Main features | Prescription trends, planted-story diagnosis, priority score, lapsing flag | Misallocation quadrant, coverage map, access tiers, decile matrix | Adherence scorecard, access tiers, district priority list |

**Not a user in version 1:** sales reps (no rep-facing app), compliance teams and brand marketing. Their needs appear only where they shape the personas above.

## Objectives and success measures

**Value hypothesis:** a brand team that sees field activity, prescribing and payer coverage in one explainable view will redeploy field effort faster and with more confidence. Version 1 tests this across three outcomes: targeting precision, field execution and decision confidence. Because the data is synthetic, each objective is proven in a demo walkthrough; the KPI a live deployment would track is shown alongside.

| Outcome | Objective | Enabled by | Demo proof point | KPI in a live deployment |
| --- | --- | --- | --- | --- |
| Targeting precision | Close coverage gaps on high-value doctors | Reach and frequency view, coverage map | The three most under-covered territories are identified in under 2 minutes | Reach to decile 8–10 doctors |
| Targeting precision | Redeploy wasted calls | Decile matrix, misallocation quadrant | The planted over-calling pattern surfaces, with the share of calls on low-potential doctors quantified | Share of calls on low-potential doctors |
| Targeting precision | Prioritise with a transparent rationale | Priority score | Each of the top 50 doctors carries a plain-English reason; changing a weight re-ranks instantly | Rep adoption of the target list |
| Field execution | Sharpen weekly coaching | Adherence scorecard, access tiers | Each rep's missed high-value doctors are visible, split by access tier | Call-plan adherence |
| Field execution | Intervene before prescribers lapse | Lapsing flag | Precision and recall on the planted pattern are shown and labelled synthetic | Lapsed prescribers recovered |
| Decision confidence | Diagnose performance shifts at root cause | Planted story, activity against outcome panel, prescription trends | A regional NBRx decline is traced to a formulary change in five steps or fewer | Time from signal to root cause |
| Decision confidence | One trusted source of truth | Metric definitions, reconciliation checks | Every total reconciles and every metric has a written definition | Reconciliation breaks per refresh |

For portfolio reviewers, Callibrate also evidences three capabilities: end-to-end product ownership from problem framing to requirements, fluency in US pharma commercial analytics, and a responsible, explainable use of AI.

## Business requirements

Each version 1 feature has one business requirement and testable acceptance criteria. Exact formulas, thresholds and screen layouts belong in the [FRD](FRD.md).

| BR | Feature | The business needs to… | Accepted when… |
| --- | --- | --- | --- |
| BR-01 | A1 Decile matrix | Rank every doctor by market prescribing volume and see brand value against potential | Every doctor has exactly one decile (1–10, 10 highest); deciles follow the industry convention of each holding about 10% of market volume; the matrix shows doctor count and share of calls per cell |
| BR-02 | A2 Reach and frequency | Know whether target doctors are seen, and seen often enough for their segment | Reach and frequency compliance are shown per cycle and segment, filterable by region, district and territory, using the definitions in D3 |
| BR-03 | A3 Adherence scorecard | See which reps are behind their call plan and which important doctors they missed | Adherence is shown per rep and district; a drill-down lists missed planned doctors, sorted by decile |
| BR-04 | A4 Prescription trends | Track the brand's prescriptions and share over time | Weekly TRx, NRx, NBRx (counted from paid pharmacy claims) and market share are shown for the brand and its three fictional competitors, by territory |
| BR-05 | A5 Coverage map | See where coverage of high-value doctors is thin | Territories are shaded by reach to high-decile doctors; those below 70% reach to decile 8–10 doctors are flagged (threshold configurable) |
| BR-06 | B1 Misallocation quadrant | Find calls spent on low-potential doctors and high-potential doctors left uncalled | Doctors are placed on potential against calls received; both problem quadrants list their doctors with counts and share of calls |
| BR-07 | B2 Access tiers | Plan for doctors who limit or refuse rep visits | Every doctor carries an access tier; key views split by tier; restricted doctors show remote and email contact separately |
| BR-08 | B3 Planted story | Give the dashboard a realistic problem to diagnose | The data contains at least one documented scenario: a region where calls hold steady but NBRx falls after a health plan adds prior authorisation, visible as code 75 rejections in the pharmacy claims. A written answer key exists, and the cause is reachable in five steps or fewer |
| BR-09 | B4 Activity against outcome | Judge territories on results, not just effort | Calls and NBRx appear side by side per territory, and territories with high effort but falling outcome are highlighted |
| BR-10 | C1 Priority score | Get a weekly, explainable ranking of which doctors to see next | The score combines stated drivers (for example potential, NBRx trend, share gap, access tier, days since last call); each doctor shows its top reasons in plain English; the analyst can change weights and the ranking updates; no hidden inputs |
| BR-11 | C3 Lapsing flag | Spot doctors likely to reduce brand prescribing before it shows in totals | A rule-based baseline and a simple statistical model (logistic regression) are compared on a planted pattern with added noise; precision, recall and the confusion matrix are shown; every output is labelled synthetic and illustrative; the main drivers of each flag are listed |
| BR-12 | D1 Realistic synthetic data | Make the data look like the real US market without containing real people | Specialty mix follows public NPI registry patterns and prescribing skew follows Medicare Part D patterns for the GLP-1 class; no real names or NPIs appear |
| BR-13 | D2 Compliance by design | Show awareness of pharma data rules | Every page shows a synthetic-data banner; doctor IDs cannot be mistaken for real NPIs; doctors opted out under the AMA PDRP are hidden from the manager view |
| BR-14 | D3 Definitions and reconciliation | Trust every number on screen | Every metric has a written definition and formula; territory totals add up to district, region and national totals; a limitations page states what the data cannot prove |

## Data, compliance and honesty requirements

Callibrate uses eight synthetic data sets that mirror what a real brand team receives. The project generates them itself, because no credible, licensed rep-activity data set exists publicly, and calibrates them on free US government data.

| Data set | One row per | Key fields | Calibrated on |
| --- | --- | --- | --- |
| Doctor master | Doctor | Synthetic ID, specialty taxonomy code, ZIP, territory, decile, access tier, PDRP opt-out flag | Specialty mix and MD/NP/PA ratio from the [NPPES NPI files](https://download.cms.gov/nppes/NPI_Files.html) and NUCC taxonomy codes |
| Pharmacy claims | Claim | Prescriber, product, fill date, new or refill, days' supply, plan, formulary status, paid or rejected, reject code (75 = prior authorisation required) | NCPDP pharmacy-claim vocabulary; prescribing skew and brand mix from [Medicare Part D Prescribers by Provider and Drug](https://catalog.data.gov/dataset/medicare-part-d-prescribers-by-provider-and-drug) |
| Weekly prescriptions | Doctor, brand and week (Saturday to Friday) | TRx, NRx, NBRx, counted from paid claims | Week and metric definitions from the [IQVIA Xponent product description](https://www.iqvia.com/-/media/iqvia/pdfs/us/brochures/iqvia-xponent-xpo--xponent-family-product-description-brochure-2026.pdf) |
| Calls | Interaction | Rep, doctor, date, channel (in person, remote, email) | Realism defaults below |
| Call plan | Doctor and quarter | Segment (A, B, C), planned frequency | Realism defaults below |
| Alignment | ZIP code | Territory, district, region | [HUD-USPS ZIP crosswalk](https://www.huduser.gov/PORTAL/node/6572); territory demand weighted by [CDC PLACES](https://catalog.data.gov/dataset/places-zcta-data-gis-friendly-format-2025-release-ace75) diabetes prevalence |
| Rep roster | Rep and territory | Rep, territory, start and end dates | Realism defaults below |
| Payer coverage | Health plan, region and brand | Tier, prior authorisation, step therapy, quantity limit, effective date | Structure and patterns of the [CMS Part D formulary files](https://www.cms.gov/Research-Statistics-Data-and-Systems/Files-for-Order/NonIdentifiableDataFiles/PrescriptionDrugPlanFormularyPharmacyNetworkandPricingInformationFiles); state Medicaid volume from [Medicaid State Drug Utilization Data](https://catalog.data.gov/dataset/state-drug-utilization-data-2025) |

**How prescriptions are built.** As in industry audits, only paid claims count towards prescriptions. When a plan adds prior authorisation, first fills start rejecting with code 75. Some of those patients abandon therapy or switch to a competitor, so NBRx falls faster than TRx while existing patients keep refilling. This is the mechanism behind the planted story in BR-08.

**Realism defaults.** Public benchmarks for field-sales operations are thin and mostly vendor-sourced, so these values are modelling choices, labelled illustrative in the app.

| Parameter | Default | Basis |
| --- | --- | --- |
| Universe | 10,000 doctors, 40 reps, 5 districts of 8 reps, 2 regions | 40 reps × 150 targets = 6,000 targeted doctors |
| Field days | 220 a year | Vendor guidance of 18–20 field days a month |
| In-person calls | About 7 per rep per day (range 5–9) | Set below the vendor-quoted 8–10 ([PharmExec](https://pharmexec.com/view/how-valuable-are-tactical-call-rate-goals)) |
| Target list | 150 doctors per rep: 25 A, 55 B, 70 C | Illustrative vendor example |
| Planned calls per quarter | A: 6, B: 3, C: 1 | Common planning convention |
| Access | About 40% of targets limited or restricted; 20% of those see no reps | US access at 45% in 2024 ([Veeva Pulse](https://veeva.com/wp-content/uploads/2024/05/Veeva-Pulse-Report-Top-Insights-1Q24.pdf)) |
| Channel mix | 55% in person, 15% remote, 30% email | Doctor preference survey, 2025 ([IQVIA](https://www.iqvia.com/locations/emea/blogs/2025/11/from-preference-to-practice)) |
| Prescriber mix | Primary care and internal medicine 50%, NPs and PAs 25%, endocrinology 12%, other 13% | GLP-1 prescribing by provider type ([ISPOR 2025](https://www.ispor.org/heor-resources/presentations-database/presentation-cti/ispor-2025/poster-session-1/assessing-prescribing-trends-for-select-glucagon-like-peptide-receptor-agonists-glp-1s-by-patient-demographics-providers-and-indication)) |
| First-fill abandonment | About 30% | Published range of 27–40% |
| 12-month persistence | About 60% (commercial 65%, Medicare 55%) | Once-weekly GLP-1 claims study ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC8099966/), manufacturer-funded) |
| Prior authorisation | 70% of Medicare and 40% of commercial scripts | Near-universal in Part D plans ([TechTarget](https://www.techtarget.com/healthcarepayers/news/366631930/Nearly-all-Medicare-Part-D-plans-require-prior-auth-for-GLP-1s)) |
| Formulary changes | Twice a year, January and July | PBM annual and mid-year cycle ([AIS Health](https://aishealth.mmitnetwork.com/blogs/spotlight-on-market-access/humira-diabetes-drugs-are-among-therapies-excluded-by-big-three-pbms-in-2025)) |

**Compliance rules**

- No real doctor, rep, company or brand appears anywhere in the app or its data.
- Public files that name real providers (NPPES, Part D) are used only to compute aggregate distributions. Identifiers are discarded, and raw files are not stored in the project repository.
- Doctor IDs follow the NPI format but deliberately fail its check digit, so they cannot be mistaken for real NPIs.
- No real name or identifier ever reaches an AI component.
- A PDRP opt-out flag mirrors the [AMA Physician Data Restriction Program](https://www.ama-assn.org/about/ama-physician-professional-data/ama-physician-data-restriction-program), hiding opted-out doctors' prescribing from manager views.
- NCPDP, X12 and IQVIA formats are licensed, so Callibrate mimics their vocabulary and structure only and claims no conformance.
- Payments to doctors (Sunshine Act, Open Payments) are not modelled; the limitations page says so.

**Honesty rules**

- Every page carries a banner stating the data is synthetic.
- Model outputs are labelled illustrative, and no lift, ROI or accuracy is claimed for the real world.
- The planted patterns are documented, so a viewer can see what the models were expected to find.

## Assumptions, constraints and risks

The biggest risk is overclaiming what synthetic data proves; most mitigations exist to prevent that.

**Assumptions**

- A call cycle is one quarter of 13 weeks, and the data covers 104 weeks.
- The universe is 10,000 doctors, 40 reps, 5 districts and 2 regions (see Realism defaults).
- A territory is flagged as thin when reach to decile 8–10 doctors falls below 70%; the threshold is configurable.

**Constraints**

- One product owner, without Python experience; the build is AI-assisted, and all metric logic is in SQL.
- Free hosting and free public data only.
- Synthetic data only.

**Risks**

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Predictions read as real insight | Credibility lost in interview | Label outputs illustrative; show the planted pattern and where the model fails |
| Circular data: the score is tested on data generated from the same rule | Results prove nothing | Generate data from drivers with noise and confounders that differ from the scoring rule |
| CV wording implies hands-on coding | Interviewer asks to walk through code | Describe the role as product owner with AI-assisted build; be ready to defend metrics and logic, not syntax |
| Placeholder names clash with real trademarks | Looks like real company data | Check names before publishing |
| Scope creep from later-phase ideas | Version 1 slips | Later-phase features stay out until version 1 ships |

## Future roadmap

These features are held back so version 1 ships focused; each builds on the version 1 data without new sources.

| Release | Feature | Why it waits |
| --- | --- | --- |
| 2 | Response curve and "stop calling" flag | Needs stated response assumptions agreed first |
| 2 | AI pre-call brief, grounded only in the app's own data | Builds on the priority score and lapsing flag |
| 2 | Rep feedback loop on suggestions | Needs the priority score in use first |
| 3 | What-if call reallocation | Depends on the response curve |
| 3 | Test against control lift analysis | Needs a planted promotional effect in the data |
| Future | Botox therapeutic extension (neurology, Medicare Part B data) | A separate market and data model |

## Glossary

| Term | Plain-English meaning |
| --- | --- |
| Access tier | How freely a doctor sees reps: open, limited or restricted |
| Call (detail) | One rep interaction with a doctor about a product |
| Call plan | The list of target doctors and how often each should be seen in a cycle |
| Call-plan adherence | Planned calls actually made, as a share of planned calls |
| Decile | Doctors ranked into 10 groups by prescribing volume; decile 10 holds the biggest prescribers |
| Formulary status | Whether a health plan covers a drug as preferred, non-preferred or only with prior authorisation |
| Frequency | How many times a reached doctor was called in a cycle |
| HCP | Healthcare professional; here, any doctor, NP or PA who prescribes |
| Logistic regression | A simple statistical model that estimates the probability of a yes/no outcome, such as a doctor lapsing |
| NBRx | New-to-brand prescriptions: patients starting or switching to the brand |
| NPI | The unique 10-digit US ID for every healthcare provider |
| NRx | New prescriptions, excluding refills |
| PDRP | AMA programme that lets doctors stop reps seeing their individual prescribing data |
| Reach | Share of target doctors called at least once in a cycle |
| SFE | Sales force effectiveness: making field effort land on the right doctors |
| Territory alignment | The mapping of ZIP codes to territories, districts and regions |
| TRx | Total prescriptions: new plus refills |

## Sources

- [Veeva Pulse report, 1Q24](https://veeva.com/wp-content/uploads/2024/05/Veeva-Pulse-Report-Top-Insights-1Q24.pdf)
- [IQVIA: overcoming 7 top challenges of commercial leaders](https://www.iqvia.com/-/media/iqvia/pdfs/library/insight-brief/overcoming-7-top-challenges-of-commercial-leaders.pdf)
- [ZS ZAIDYN Dynamic Targeting](https://zaidyn.zs.com/products/zaidyn-commercial/customer-engagement/dynamic-targeting)
- [Deloitte: can AI help biopharma sales reps become more effective?](https://www.deloitte.com/us/en/industries/life-sciences-health-care/blogs/health-care/can-ai-help-biopharma-sales-reps-become-more-effective.html)
- [Fierce Healthcare: Medicare price reductions including semaglutide](https://www.fiercehealthcare.com/pharma/medicare-unveils-price-reductions-15-drugs-including-novos-semaglutide)
- [CMS Medicare Part D Prescribers by Provider and Drug](https://catalog.data.gov/dataset/medicare-part-d-prescribers-by-provider-and-drug)
- [CMS Part D formulary files](https://www.cms.gov/Research-Statistics-Data-and-Systems/Files-for-Order/NonIdentifiableDataFiles/PrescriptionDrugPlanFormularyPharmacyNetworkandPricingInformationFiles)
- [CMS NPPES NPI files](https://download.cms.gov/nppes/NPI_Files.html)
- [CDC PLACES, ZCTA data, 2025 release](https://catalog.data.gov/dataset/places-zcta-data-gis-friendly-format-2025-release-ace75)
- [HUD-USPS ZIP crosswalk](https://www.huduser.gov/PORTAL/node/6572)
- [Medicaid State Drug Utilization Data, 2025](https://catalog.data.gov/dataset/state-drug-utilization-data-2025)
- [IQVIA Xponent product description](https://www.iqvia.com/-/media/iqvia/pdfs/us/brochures/iqvia-xponent-xpo--xponent-family-product-description-brochure-2026.pdf)
- [Medi-Cal Rx NCPDP reject codes](https://medi-calrx.dhcs.ca.gov/cms/medicalrx/static-assets/documents/provider/forms-and-information/manuals/Appendix_D_-_NCPDP_Reject_Codes.pdf)
- [Florida Medicaid GLP-1 criteria, Oct 2026](https://ahca.myflorida.com/file/medicaid/Drug%20Criteria/Glucagon-like_Peptide-1_%28GLP-1%29_Receptor_Agonist_10.01.2026.pdf)
- [AMA Physician Data Restriction Program](https://www.ama-assn.org/about/ama-physician-professional-data/ama-physician-data-restriction-program)
