"""Calibration and scenario checks for the Callibrate synthetic data.

Reads data/callibrate.duckdb, compares the data with the targets in generator/config.yaml
and the planted scenarios in docs/ANSWER_KEY.md, and writes docs/CALIBRATION.md.

Run from the repository root after generating the data:
    python generator/calibrate.py
"""
from __future__ import annotations

import datetime as dt
import pathlib

import duckdb
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
cfg = yaml.safe_load((ROOT / "generator" / "config.yaml").read_text())
con = duckdb.connect(str(ROOT / "data" / "callibrate.duckdb"), read_only=True)
tol = cfg["targets"]["tolerance_pts"]


def q(sql, *a):
    return con.execute(sql, list(a)).fetchall()


def one(sql, *a):
    return con.execute(sql, list(a)).fetchone()[0]


def pct(x):
    return f"{100 * x:.1f}%"


rows = []  # (check, target, actual, within)


def check(name, target, actual, ok=None):
    rows.append((name, target, actual, "" if ok is None else ("Pass" if ok else "Fail")))


def is_valid_npi(npi: str) -> bool:
    digits = [int(c) for c in "80840" + npi[:9]]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return len(npi) == 10 and npi[0] in "12" and (10 - total % 10) % 10 == int(npi[9])


# --- deciles (market TRx, latest 52 weeks), as defined in the FRD (M-06)
con.execute("""
CREATE TEMP TABLE dec AS
WITH vol AS (
    SELECT d.doctor_id, COALESCE(SUM(r.trx), 0) AS trx
    FROM doctors d LEFT JOIN weekly_rx r ON r.doctor_id = d.doctor_id AND r.week BETWEEN 53 AND 104
    GROUP BY d.doctor_id
), ranked AS (
    SELECT *, SUM(trx) OVER (ORDER BY trx DESC, doctor_id ROWS UNBOUNDED PRECEDING) / SUM(trx) OVER () AS cum
    FROM vol
)
SELECT doctor_id, trx, CASE WHEN trx = 0 THEN 0 ELSE 10 - LEAST(9, FLOOR((cum - 1e-9) * 10))::INT END AS decile
FROM ranked
""")

# --- specialty mix of GLP-1 volume
spec = dict(q("""SELECT d.specialty, SUM(r.trx) / (SELECT SUM(trx) FROM weekly_rx WHERE week >= 1)
                 FROM weekly_rx r JOIN doctors d USING (doctor_id) WHERE r.week >= 1 GROUP BY 1"""))
for k, v in cfg["specialties"].items():
    check(f"Share of GLP-1 volume: {v['label']}", pct(v["volume_share"]), pct(spec.get(k, 0)),
          abs(spec.get(k, 0) - v["volume_share"]) * 100 <= tol)

prescribers = one("SELECT COUNT(*) FROM dec WHERE decile > 0")
top = one("SELECT COUNT(*) FROM dec WHERE decile >= 8")
t = cfg["targets"]["prescribers_in_deciles_8_10"]
check("Prescribers in deciles 8–10", pct(t), pct(top / prescribers), abs(top / prescribers - t) * 100 <= tol)

# --- brand shares
nb = dict(q("SELECT brand, SUM(nbrx) / (SELECT SUM(nbrx) FROM weekly_rx WHERE week >= 1) FROM weekly_rx WHERE week >= 1 GROUP BY 1"))
t = cfg["targets"]["glyvexa_nbrx_share"]
check("Glyvexa NBRx share (weeks 1–104)", pct(t), pct(nb["glyvexa"]), abs(nb["glyvexa"] - t) * 100 <= tol)
tr = dict(q("SELECT brand, SUM(trx) / (SELECT SUM(trx) FROM weekly_rx WHERE week >= 1) FROM weekly_rx WHERE week >= 1 GROUP BY 1"))
check("TRx share: Glyvexa / Sucrelo / Metaryn / Orvalis", "Illustrative",
      " / ".join(pct(tr[b]) for b in ["glyvexa", "sucrelo", "metaryn", "orvalis"]))

# --- field force
ch = dict(q("SELECT channel, COUNT(*) / (SELECT COUNT(*) FROM calls) FROM calls GROUP BY 1"))
check("Channel mix: in person / remote / email", "55% / 15% / 30%",
      f"{pct(ch.get('in_person', 0))} / {pct(ch.get('remote', 0))} / {pct(ch.get('email', 0))}")
per_rep_week = one("SELECT COUNT(*) / 40.0 / 104 FROM calls WHERE channel = 'in_person'")
check("In-person calls per rep per field day", "About 7 (range 5–9)", f"{per_rep_week / 5:.1f}")
adh = one("""
    WITH made AS (SELECT c.doctor_id, w.quarter, COUNT(*) n FROM calls c JOIN weeks w USING (week)
                  WHERE c.channel <> 'email' GROUP BY ALL)
    SELECT SUM(LEAST(COALESCE(m.n, 0), p.planned_calls)) / SUM(p.planned_calls)
    FROM call_plan p LEFT JOIN made m ON m.doctor_id = p.doctor_id AND m.quarter = p.quarter""")
check("National call-plan adherence (M-09)", "Illustrative, 70–85%", pct(adh))
acc = dict(q("SELECT access_tier, COUNT(*) / 10000 FROM doctors GROUP BY 1"))
check("Access tiers: open / limited / no-see", "60% / 32% / 8%",
      f"{pct(acc['open'])} / {pct(acc['limited'])} / {pct(acc['no_see'])}")

# --- patients: 12-month persistence (cohort rule documented in docs/FRD.md, M-18)
pers = one("""
    WITH paid AS (SELECT patient_id, brand, week,
                         LAG(week) OVER (PARTITION BY patient_id, brand ORDER BY week) AS prev
                  FROM pharmacy_claims WHERE response_status = 'P'),
    idx AS (SELECT patient_id, brand, week AS w0 FROM paid
            WHERE (prev IS NULL OR week - prev > 52) AND week BETWEEN 1 AND 52),
    f AS (SELECT i.patient_id, i.brand, i.w0, p.week,
                 p.week - LAG(p.week) OVER (PARTITION BY i.patient_id, i.brand, i.w0 ORDER BY p.week) AS gap
          FROM idx i JOIN paid p USING (patient_id, brand) WHERE p.week BETWEEN i.w0 AND i.w0 + 52),
    s AS (SELECT patient_id, brand, w0, MAX(week) AS last_w, COALESCE(MAX(gap), 0) AS max_gap FROM f GROUP BY ALL)
    SELECT AVG(CASE WHEN last_w >= w0 + 48 AND max_gap <= 13 THEN 1 ELSE 0 END) FROM s""")
check("12-month persistence (new-to-brand starts in weeks 1–52)", "About 60%", pct(pers))

# --- decile construction
dv = q("SELECT decile, SUM(trx) / (SELECT SUM(trx) FROM dec) FROM dec WHERE decile > 0 GROUP BY 1")
lo_, hi_ = min(v for _, v in dv), max(v for _, v in dv)
check("Each decile's share of market volume", "9–11%", f"{pct(lo_)}–{pct(hi_)}", lo_ >= 0.09 and hi_ <= 0.11)

# --- identifiers
ids = [r[0] for r in q("SELECT doctor_id FROM doctors")]
valid = sum(is_valid_npi(i) for i in ids)
check("Synthetic prescriber IDs that pass the NPI check digit", "0", f"{valid}", valid == 0)

# --- new-prescription funnel and reject reasons
fn = dict(q("SELECT stage, prescriptions FROM generation_funnel"))
w = fn["written"]
funnel = [
    ("New prescriptions written (weeks 1–104)", f"{w:,}", "100%"),
    ("Never taken to a pharmacy (invisible in claims data)", f"{fn['never_presented']:,}", pct(fn["never_presented"] / w)),
    ("Presented at a pharmacy", f"{fn['presented']:,}", pct(fn["presented"] / w)),
    ("Rejected at first fill for prior authorisation (code 75)", f"{fn['rejected_pa']:,}", pct(fn["rejected_pa"] / w)),
    ("then approved and paid", f"{fn['approved_after_pa']:,}", pct(fn["approved_after_pa"] / w)),
    ("then abandoned (no paid claim)", f"{fn['abandoned_after_pa']:,}", pct(fn["abandoned_after_pa"] / w)),
    ("then switched to a competitor", f"{fn['switched_after_pa']:,}", pct(fn["switched_after_pa"] / w)),
]
unfilled = (fn["never_presented"] + fn["abandoned_after_pa"]) / w
check("Written prescriptions that never become a paid fill of any brand", "27–40% (published range)", pct(unfilled),
      0.27 <= unfilled <= 0.40)
codes = q("""SELECT reject_code, COUNT(*), COUNT(*) / SUM(COUNT(*)) OVER () FROM pharmacy_claims
             WHERE response_status = 'R' AND week >= 1 GROUP BY 1 ORDER BY 2 DESC""")
code_label = {"75": "Prior authorisation required", "76": "Plan limitations exceeded",
              "65": "Patient not covered", "79": "Refill too soon"}

# --- planted scenarios
facts = dict(((s, f), v) for s, f, v in q("SELECT * FROM scenario_facts"))
heavy = facts[("P1", "heavy_territories")].split(", ")
scen = []
p1 = dict(q("""
    SELECT CASE WHEN week < 88 THEN 'before' ELSE 'after' END,
           COUNT(*) FILTER (WHERE reject_code = '75') * 1.0 / COUNT(*)
    FROM pharmacy_claims WHERE plan_id = 'PL03' AND brand = 'glyvexa' AND fill_number = 0
      AND week BETWEEN 76 AND 99 GROUP BY 1"""))
did = q("""
    WITH t AS (SELECT d.territory_id IN (SELECT UNNEST(?)) AS affected, r.week, r.nbrx, r.trx
               FROM weekly_rx r JOIN doctors d USING (doctor_id) WHERE r.brand = 'glyvexa')
    SELECT affected,
           SUM(nbrx) FILTER (WHERE week BETWEEN 89 AND 100) / SUM(nbrx) FILTER (WHERE week BETWEEN 76 AND 87) - 1,
           SUM(trx)  FILTER (WHERE week BETWEEN 89 AND 100) / SUM(trx)  FILTER (WHERE week BETWEEN 76 AND 87) - 1
    FROM t GROUP BY 1 ORDER BY 1 DESC""", heavy)
calls_change = one("""
    SELECT COUNT(*) FILTER (WHERE week BETWEEN 89 AND 100) * 1.0 / COUNT(*) FILTER (WHERE week BETWEEN 76 AND 87) - 1
    FROM calls WHERE channel <> 'email' AND territory_id IN (SELECT UNNEST(?))""", heavy)
aff, oth = did[0], did[1]
scen.append(("P1 Formulary shock (Bayou Senior Advantage, week 88)",
             f"Share of new Glyvexa prescriptions on the plan rejected for prior authorisation: "
             f"{pct(p1.get('before', 0))} in the 12 weeks before, {pct(p1.get('after', 0))} in the 12 weeks after. "
             f"Glyvexa NBRx, 12 weeks after (89–100) against 12 weeks before (76–87): affected territories "
             f"{aff[1] * 100:+.0f}%, other territories {oth[1] * 100:+.0f}%, a gap of {(aff[1] - oth[1]) * 100:+.0f} points. "
             f"TRx in affected territories {aff[2] * 100:+.0f}%; calls there {calls_change * 100:+.0f}%. "
             f"A synthetic association designed into the data, not evidence of real-world cause."))

p2 = q("""
    WITH c AS (SELECT c.territory_id, d.decile FROM calls c JOIN dec d USING (doctor_id) WHERE c.channel <> 'email')
    SELECT territory_id, AVG(CASE WHEN decile <= 4 THEN 1 ELSE 0 END) s FROM c GROUP BY 1 ORDER BY 2 DESC LIMIT 5""")
p2t = facts[("P2", "territories")].split(", ")
top3 = [r[0] for r in p2[:3]]
scen.append(("P2 Over-calling",
             f"Planted territories {', '.join(p2t)}. Highest low-potential call share: "
             + "; ".join(f"{r[0]} {pct(r[1])}" for r in p2)
             + (". The three planted territories rank top three." if set(top3) == set(p2t) else ". Not all planted territories rank top three.")))

p3t = facts[("P3", "territory")]
p3 = q("""
    WITH tgt AS (SELECT p.doctor_id FROM call_plan p JOIN dec d USING (doctor_id)
                 WHERE p.quarter = 4 AND p.territory_id = ? AND d.decile >= 8),
         seen AS (SELECT DISTINCT doctor_id, CASE WHEN week BETWEEN 40 AND 47 THEN 'gap' ELSE 'normal' END AS w
                  FROM calls WHERE territory_id = ? AND channel <> 'email' AND week BETWEEN 32 AND 47)
    SELECT w, COUNT(DISTINCT s.doctor_id) * 1.0 / (SELECT COUNT(*) FROM tgt) FROM seen s JOIN tgt USING (doctor_id) GROUP BY 1""", p3t, p3t)
p3d = dict(p3)
scen.append(("P3 Vacancy", f"{p3t}: share of decile 8–10 targets seen in weeks 32–39 {pct(p3d.get('normal', 0))}, "
                           f"in the vacancy weeks 40–47 {pct(p3d.get('gap', 0))}."))

p4 = q("""
    SELECT d.county IN ('Fulton County','DeKalb County','Cobb County','Gwinnett County') AND d.state = 'GA' AS metro,
           AVG(CASE WHEN d.access_tier = 'no_see' THEN 1 ELSE 0 END)
    FROM doctors d WHERE d.specialty = 'endocrinology' GROUP BY 1 ORDER BY 1 DESC""")
scen.append(("P4 Restricted cluster", f"No-see share among endocrinologists: metro Atlanta {pct(p4[0][1])}, elsewhere {pct(p4[1][1])}."))

n_lapse = one("SELECT COUNT(*) FROM answer_key_lapses WHERE is_lapse")
by_cause = q("SELECT cause, COUNT(*) FROM answer_key_lapses GROUP BY 1 ORDER BY ANY_VALUE(is_lapse) DESC, 1")
scen.append(("P5 Lapsing writers", f"{n_lapse} planted lapses plus decoys that do not lapse: "
             + ", ".join(f"{c.replace('_', ' ')} {n}" for c, n in by_cause) + "."))

# --- write report
today = dt.date.today().isoformat()
lines = [
    "# Callibrate — calibration report",
    "",
    f"Generated {today} by `generator/calibrate.py` from seed {cfg['seed']}. "
    f"Checks with a target of ±{tol:g} percentage points show Pass or Fail; the rest are reported for review.",
    "",
    "## Calibration checks",
    "",
    "| Check | Target | Actual | Result |",
    "| --- | --- | --- | --- |",
]
lines += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
lines += ["", "## New-prescription funnel", "",
          "Only the rows from \"Presented at a pharmacy\" down can be seen in claims data; prescriptions never taken "
          "to a pharmacy leave no claim.", "",
          "| Stage | Prescriptions | Share of written |", "| --- | --- | --- |"]
lines += [f"| {a} | {b} | {c} |" for a, b, c in funnel]
lines += ["", "## Rejected claims by reason (weeks 1–104)", "", "| NCPDP code | Meaning | Claims | Share |", "| --- | --- | --- | --- |"]
lines += [f"| {c} | {code_label.get(c, '')} | {n:,} | {pct(sh)} |" for c, n, sh in codes]
lines += ["", "## Planted scenarios", "", "| Scenario | What the data shows |", "| --- | --- |"]
lines += [f"| {a} | {b} |" for a, b in scen]
(ROOT / "docs" / "CALIBRATION.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
fails = [r for r in rows if r[3] == "Fail"]
print(f"\n{len(fails)} failing checks")
