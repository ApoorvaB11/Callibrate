"""Build the Callibrate SQL metric layer and run every check.

Runs the SQL files in sql/ in order against data/callibrate.duckdb, creating the "mart" schema
the app reads from. Then runs the reconciliation checks and acceptance tests, adds two hand
calculations done independently in Python (AT-02, AT-03), and writes docs/METRICS_CHECK.md.

Run from the repository root after generating the data:
    python sql/build.py
"""
from __future__ import annotations

import datetime as dt
import pathlib
import sys
import time

import duckdb
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "callibrate.duckdb"
LATEST = (92, 104)  # latest full quarter, the app's default period


def hand_checks(con) -> list[dict]:
    """Recompute two numbers from the raw tables in pandas, without using any mart SQL."""
    out = []
    w0, w1 = LATEST
    plan = con.execute("SELECT * FROM call_plan WHERE quarter = 8").df()
    calls = con.execute("SELECT * FROM calls WHERE channel <> 'email' AND week BETWEEN ? AND ?", [w0, w1]).df()

    # AT-02: reach and average frequency for one territory
    terr = "GEORGIA-03"
    tp = plan[plan.territory_id == terr]
    n = calls[calls.doctor_id.isin(tp.doctor_id)].groupby("doctor_id").size()
    reached = tp.doctor_id.isin(n.index)
    hand_reach = reached.mean()
    hand_freq = n.sum() / reached.sum()
    sql = con.execute("SELECT reach, average_frequency FROM mart.coverage_summary(?, ?) WHERE area = ?",
                      [w0, w1, terr]).fetchone()
    ok = abs(sql[0] - hand_reach) < 1e-9 and abs(sql[1] - hand_freq) < 1e-9
    out.append(dict(check_id="AT-02", category="Acceptance test AT-02",
                    check_name=f"Reach and average frequency for {terr} (weeks {w0}–{w1}), recalculated by hand in Python",
                    expected="SQL equals hand calculation",
                    actual=f"SQL {sql[0]:.1%} reach, {sql[1]:.2f} calls; hand {hand_reach:.1%}, {hand_freq:.2f}",
                    passed=ok))

    # AT-03: one rep's call-plan adherence, and the missed-doctor list
    rep = con.execute("SELECT rep_id FROM reps WHERE territory_id = ? AND start_week <= ? AND end_week >= ?",
                      [terr, w0, w1]).fetchone()[0]
    rc = calls[calls.rep_id == rep].groupby("doctor_id").size()
    made = tp.doctor_id.map(rc).fillna(0)
    hand_adh = (made.clip(upper=tp.planned_calls.values)).sum() / tp.planned_calls.sum()
    sql_adh = con.execute("SELECT call_plan_adherence FROM mart.rep_scorecard(?, ?) WHERE rep_id = ?",
                          [w0, w1, rep]).fetchone()[0]
    hand_missed = set(tp.doctor_id[made.values == 0])
    sql_missed = {r[0] for r in con.execute("SELECT doctor_id FROM mart.missed_targets(?, ?) WHERE territory_id = ?",
                                            [w0, w1, terr]).fetchall()}
    ok = abs(sql_adh - hand_adh) < 1e-9 and hand_missed == sql_missed
    out.append(dict(check_id="AT-03", category="Acceptance test AT-03",
                    check_name=f"Call-plan adherence for rep {rep} ({terr}, weeks {w0}–{w1}) and the missed-doctor list, recalculated by hand",
                    expected="SQL equals hand calculation; same missed doctors",
                    actual=f"SQL {sql_adh:.1%}, hand {hand_adh:.1%}; missed doctors {len(sql_missed)} in SQL, {len(hand_missed)} by hand",
                    passed=ok))
    return out


def pct(x):
    return "" if x is None or pd.isna(x) else f"{100 * x:.1f}%"


def main():
    if not DB.exists():
        sys.exit("data/callibrate.duckdb not found. Run python generator/generate.py first.")
    con = duckdb.connect(str(DB))
    for f in sorted((ROOT / "sql").glob("*.sql")):
        t = time.time()
        con.execute(f.read_text())
        print(f"ran {f.name:<28} {time.time() - t:5.1f}s")

    checks = con.execute("SELECT * FROM mart.check_results").df().to_dict("records") + hand_checks(con)
    checks.sort(key=lambda r: (not r["check_id"].startswith("R"), r["check_id"]))
    passed = sum(bool(c["passed"]) for c in checks)

    w0, w1 = LATEST
    nat = con.execute("SELECT * FROM mart.coverage_summary(?, ?) WHERE level = 'national'", [w0, w1]).df().iloc[0]
    tgt = con.execute("SELECT * FROM mart.targeting_summary(?, ?) WHERE level = 'national'", [w0, w1]).df().iloc[0]
    rx = con.execute("SELECT * FROM mart.rx_summary(?, ?) WHERE level = 'national' AND brand = 'glyvexa'", [w0, w1]).df().iloc[0]
    rx_prev = con.execute("SELECT * FROM mart.rx_summary(79, 91) WHERE level = 'national' AND brand = 'glyvexa'").df().iloc[0]
    pay = con.execute("SELECT * FROM mart.payer_summary(89, 100) WHERE level = 'plan' AND brand = 'glyvexa' AND plan_id = 'PL03'").df().iloc[0]
    acc = con.execute("SELECT * FROM mart.coverage_by_access(?, ?) ORDER BY targets DESC", [w0, w1]).df()
    pers = con.execute("SELECT persistence_12m FROM mart.persistence_12m WHERE brand = 'glyvexa' AND line_of_business IS NULL").fetchone()[0]
    ba = con.execute("SELECT * FROM mart.before_after_rollup(88, 12) WHERE level IN ('region', 'national') ORDER BY area").df()

    lines = [
        "# Callibrate — metric layer checks",
        "",
        f"Generated {dt.date.today().isoformat()} by `sql/build.py`. **{passed} of {len(checks)} checks pass.** "
        "Reconciliation checks prove the numbers add up and tie back to the raw data; acceptance tests come from the FRD. "
        "AT-08, AT-10, AT-11 and the app-facing parts of AT-13 are tested once the app is built; AT-12 is in "
        "[CALIBRATION.md](CALIBRATION.md).",
        "",
        "| ID | Type | Check | Expected | Actual | Result |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {c['check_id']} | {c['category']} | {c['check_name']} | {c['expected']} | {c['actual']} | "
              f"{'Pass' if c['passed'] else 'Fail'} |" for c in checks]
    lines += [
        "",
        f"## Headline numbers, latest quarter (weeks {w0}–{w1})",
        "",
        "Synthetic data: these describe the fictional market, not any real brand.",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Glyvexa TRx (M-01) | {rx.trx:,.0f} ({rx.trx / rx_prev.trx - 1:+.1%} on the previous quarter) |",
        f"| Glyvexa NBRx (M-03) | {rx.nbrx:,.0f} ({rx.nbrx / rx_prev.nbrx - 1:+.1%}) |",
        f"| Glyvexa TRx share / NBRx share (M-04, M-05) | {pct(rx.trx_share)} / {pct(rx.nbrx_share)} |",
        f"| Reach, all targets / decile 8–10 targets (M-07) | {pct(nat.reach)} / {pct(nat.reach_decile_8_10)} |",
        f"| In-person reach / omnichannel reach (M-16, M-17) | {pct(nat.in_person_reach)} / {pct(nat.omnichannel_reach)} |",
        f"| Average frequency of reached targets (M-08) | {nat.average_frequency:.1f} calls |",
        f"| Call-plan adherence (M-09) | {pct(nat.call_plan_adherence)} |",
        f"| Calls on non-targets / on decile 0–4 doctors (M-11, M-12) | {pct(tgt.non_target_call_share)} / {pct(tgt.low_potential_call_share)} |",
        f"| Under-called decile 8–10 doctors / over-called decile 0–4 doctors | {tgt.under_called_high_potential_doctors:,} / {tgt.over_called_low_potential_doctors:,} |",
        f"| Glyvexa 12-month persistence (M-18) | {pct(pers)} |",
        "",
        "**Reach by access tier**",
        "",
        "| Access tier | Targets | In-person reach | Remote reach | Email reach | Omnichannel reach |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    lines += [f"| {r.access_tier} | {r.targets:,} | {pct(r.in_person_reach)} | {pct(r.remote_reach)} | {pct(r.email_reach)} | "
              f"{pct(r.omnichannel_reach)} |" for r in acc.itertuples()]
    lines += [
        "",
        "**Formulary shock (P1): 12 weeks after week 88 against the 12 weeks before**",
        "",
        f"Bayou Senior Advantage, weeks 89–100: {pct(pay.prior_auth_rejection_rate)} of new Glyvexa prescriptions rejected for prior "
        f"authorisation; of those, {pct(pay.approval_rate)} were approved, {pct(pay.abandonment_rate)} abandoned and "
        f"{pct(pay.switch_rate)} switched to a competitor within 30 days.",
        "",
        "| Area | Glyvexa NBRx | Glyvexa TRx | Calls |",
        "| --- | --- | --- | --- |",
    ]
    lines += [f"| {r.area.title()} | {r.nbrx_change:+.1%} | {r.trx_change:+.1%} | {r.calls_change:+.1%} |" for r in ba.itertuples()]
    lines += ["", "An association designed into synthetic data, not evidence of a real-world cause."]
    (ROOT / "docs" / "METRICS_CHECK.md").write_text("\n".join(lines) + "\n")
    con.close()

    for c in checks:
        print(f"{'PASS' if c['passed'] else 'FAIL'}  {c['check_id']:<6} {c['actual']}")
    print(f"\n{passed} of {len(checks)} checks pass; report written to docs/METRICS_CHECK.md")
    if passed < len(checks):
        sys.exit(1)


if __name__ == "__main__":
    main()
