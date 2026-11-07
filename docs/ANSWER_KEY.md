# Callibrate — planted scenario answer key

Last updated 7 Nov 2026 · Product owner: Apoorva Bhardwaj

Five patterns are planted in the synthetic data so the app has real problems to find. This page says where each one is and what a user should see; [CALIBRATION.md](CALIBRATION.md) shows the measured signal from the current build. The app never reads this answer key to make its findings.

| ID | Scenario | Where | When | What a user should find | Screen |
| --- | --- | --- | --- | --- | --- |
| P1 | Formulary shock | Bayou Senior Advantage (PL03), Gulf region; strongest in AL_MS-04, LOUISIANA-01, -02, -04, -07 and -08, where the plan covers more Medicare patients | From week 88 (4 July 2026), after the plan's 1 July update | Glyvexa moves from preferred to non-preferred with prior authorisation. New Glyvexa prescriptions on the plan start rejecting with code 75; some patients abandon or switch. NBRx falls about 17% in the affected territories while calls hold steady and TRx keeps growing on refills | S7 Diagnose, S1 alert |
| P2 | Over-calling | AL_MS-03, FL_NORTH-01, GEORGIA-08 | All 104 weeks | About 30% of each rep's calls go to non-target, low-potential doctors near the rep's base. These three territories rank highest on low-potential call share | S2 Targeting, S1 |
| P3 | Vacancy | FL_NORTH-04 | Weeks 40–47 (2 Aug to 26 Sep 2025) | The rep leaves; no calls for 8 weeks. Reach to decile 8–10 doctors drops to zero, then a new rep starts in week 48 | S3 Coverage, S4 Field execution |
| P4 | Restricted cluster | Endocrinologists in Fulton, DeKalb, Cobb and Gwinnett counties, Georgia (metro Atlanta) | All 104 weeks | About 90% of these endocrinologists see no reps, against about 8% elsewhere. In-person reach is low and contact is remote or by email | S3 Coverage |
| P5 | Lapsing writers | 30 active Glyvexa writers, listed in the `answer_key_lapses` table | Lapse weeks 41–96 | Glyvexa new prescribing falls to about 30% of its former level. 13 lapse after a competitor push (gradual decline, competitor rising), 8 after a gap in calls, and 9 with no warning sign at all | S6 Lapsing watchlist |

## How to use this key

- **Demo walkthrough.** Start from the S1 alert for the Louisiana territories and follow the drill path to the code 75 rejections on Bayou Senior Advantage (BR-08: five steps or fewer).
- **Acceptance tests.** AT-05 to AT-09 and AT-11 in the FRD check that the app surfaces these patterns.
- **Model honesty.** The lapsing model is tested against outcomes in the data, not against this list. Natural noise also creates lapses that were never planted, and 9 planted lapses give no early signal, so neither the rule nor the model can catch everything.
