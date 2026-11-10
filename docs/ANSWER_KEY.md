# Callibrate — planted scenario answer key

Last updated 7 Nov 2026 (revised after independent review) · Product owner: Apoorva Bhardwaj

Five patterns are planted in the synthetic data so the app has real problems to find. This page says where each one is and what a user should see; [CALIBRATION.md](CALIBRATION.md) shows the measured signal from the current build. The app and the lapsing model never read this answer key to make their findings.

| ID | Scenario | Where | When | What a user should find | Screen |
| --- | --- | --- | --- | --- | --- |
| P1 | Formulary shock | Bayou Senior Advantage (PL03), which covers the whole Gulf region; strongest in AL_MS-02, AL_MS-05, AL_MS-06, LOUISIANA-02, LOUISIANA-03 and LOUISIANA-07, where the plan covers more Medicare patients | From week 88 (4 July 2026), after the plan's 1 July update | Glyvexa moves from preferred to non-preferred with prior authorisation. About 64% of Glyvexa first-fill claims on the plan now reject with code 75 (none did before). Of blocked patients, about 35% are approved and paid a week or two later, 31% abandon and 34% switch to a competitor. Comparing 12 weeks after with 12 weeks before, Glyvexa NBRx falls about 17% across the Gulf region (about 21% in the six heaviest territories) against a 5% rise in the Southeast, while calls hold steady and TRx keeps growing on refills. Single territories vary by about ±8% from noise, so the region view is the clearest | S7 Diagnose, S1 alert |
| P2 | Over-calling | AL_MS-03, FL_NORTH-01, GEORGIA-08 | All 104 weeks | About 30% of each rep's calls go to non-target, low-potential doctors near the rep's base. These three territories rank highest on low-potential call share | S2 Targeting, S1 |
| P3 | Vacancy | FL_NORTH-04 | Weeks 40–47 (2 Aug to 26 Sep 2025) | The rep leaves; no calls for 8 weeks. Reach to decile 8–10 doctors drops to zero, then a new rep starts in week 48 | S3 Coverage, S4 Field execution |
| P4 | Restricted cluster | Endocrinologists in Fulton, DeKalb, Cobb and Gwinnett counties, Georgia (metro Atlanta) | All 104 weeks | About 90% of these endocrinologists see no reps, against about 8% elsewhere. In-person reach is low; omnichannel reach is higher | S3 Coverage |
| P5 | Lapsing writers and decoys | 27 active Glyvexa writers that lapse, and 30 decoys, all listed in the `answer_key_lapses` table | Weeks 40–96 | Lapsers' Glyvexa new prescribing falls to about 30% of its former level: 11 after a competitor push (gradual decline, competitor rising), 9 after a gap in calls, 7 with no warning sign. Decoys look risky but do not lapse: 15 have a long call gap with no change in prescribing, 15 dip for a few weeks and recover | S6 Lapsing watchlist |

**Background noise.** Besides prior authorisation, claims also reject for plan limitations exceeded (76), patient not covered (65) and refill too soon (79). These rejections are resolved by a paid resubmission and are not a planted pattern.

## How to use this key

- **Demo walkthrough.** Start from the S1 alert for the Gulf region and follow the drill path to the code 75 rejections on Bayou Senior Advantage (BR-08: five steps or fewer). The analyst panel should then suggest checking prior authorisation approvals, abandonment and switching before any change to the call plan.
- **Acceptance tests.** AT-05 to AT-09 and AT-11 in the FRD check that the app surfaces these patterns.
- **Model honesty.** The lapsing model is tested against outcomes measured in the claims data, not against this list. Natural noise creates lapses that were never planted, decoys create false alarms, and silent lapses give no early signal, so neither the rule nor the model can catch everything.
- **Associations, not causes.** Every pattern here was designed into synthetic data. Finding it shows the analysis works; it is not evidence about any real plan, brand or market.
