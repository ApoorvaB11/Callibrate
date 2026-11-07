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

# --- patients
pers = one("""
    WITH starts AS (SELECT patient_id, brand, MIN(week) w0 FROM pharmacy_claims
                    WHERE response_status = 'P' AND fill_number = 0 GROUP BY 1, 2 HAVING MIN(week) BETWEEN -40 AND 40)
    SELECT AVG(CASE WHEN EXISTS (SELECT 1 FROM pharmacy_claims c WHERE c.patient_id = s.patient_id
               AND c.brand = s.brand AND c.response_status = 'P' AND c.week BETWEEN s.w0 + 48 AND s.w0 + 56) THEN 1 ELSE 0 END)
    FROM starts s""")
check("12-month persistence", "About 60%", pct(pers))

# --- identifiers
ids = [r[0] for r in q("SELECT doctor_id FROM doctors")]
valid = sum(is_valid_npi(i) for i in ids)
check("Doctor IDs that pass the NPI check digit", "0", f"{valid}", valid == 0)

# --- planted scenarios
facts = dict(((s, f), v) for s, f, v in q("SELECT * FROM scenario_facts"))
heavy = facts[("P1", "heavy_territories")].split(", ")
scen = []
p1 = q("""
    SELECT CASE WHEN week < 88 THEN 'before' ELSE 'after' END AS period,
           COUNT(*) FILTER (WHERE response_status = 'R') * 1.0 / COUNT(*) AS reject_rate
    FROM pharmacy_claims WHERE plan_id = 'PL03' AND brand = 'glyvexa' AND fill_number = 0 AND week BETWEEN 72 AND 104
    GROUP BY 1 ORDER BY 1 DESC""")
p1d = dict(p1)
nb_change = q("""
    WITH t AS (SELECT d.territory_id IN (SELECT UNNEST(?)) AS heavy, r.week, r.nbrx, r.trx
               FROM weekly_rx r JOIN doctors d USING (doctor_id) WHERE r.brand = 'glyvexa')
    SELECT heavy,
           SUM(nbrx) FILTER (WHERE week BETWEEN 91 AND 104) / SUM(nbrx) FILTER (WHERE week BETWEEN 74 AND 87) - 1,
           SUM(trx)  FILTER (WHERE week BETWEEN 91 AND 104) / SUM(trx)  FILTER (WHERE week BETWEEN 74 AND 87) - 1
    FROM t GROUP BY 1 ORDER BY 1 DESC""", heavy)
calls_change = one("""
    SELECT COUNT(*) FILTER (WHERE week BETWEEN 91 AND 104) * 1.0 / COUNT(*) FILTER (WHERE week BETWEEN 74 AND 87) - 1
    FROM calls WHERE channel <> 'email' AND territory_id IN (SELECT UNNEST(?))""", heavy)
hv, other = nb_change[0], nb_change[1]
scen.append(("P1 Formulary shock (Bayou Senior Advantage, week 88)",
             f"Glyvexa first-fill rejection on the plan {pct(p1d.get('before', 0))} before, {pct(p1d.get('after', 0))} after. "
             f"In the six affected territories Glyvexa NBRx changed {hv[1] * 100:+.0f}% and TRx {hv[2] * 100:+.0f}% "
             f"(two weeks after the change against the 14 weeks before), while calls changed {calls_change * 100:+.0f}%. "
             f"Other territories: NBRx {other[1] * 100:+.0f}%, TRx {other[2] * 100:+.0f}%."))

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

n_lapse = one("SELECT COUNT(*) FROM answer_key_lapses")
by_cause = q("SELECT cause, COUNT(*) FROM answer_key_lapses GROUP BY 1 ORDER BY 1")
scen.append(("P5 Lapsing writers", f"{n_lapse} planted lapses: " + ", ".join(f"{c} {n}" for c, n in by_cause) + "."))

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
lines += ["", "## Planted scenarios", "", "| Scenario | What the data shows |", "| --- | --- |"]
lines += [f"| {a} | {b} |" for a, b in scen]
(ROOT / "docs" / "CALIBRATION.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
fails = [r for r in rows if r[3] == "Fail"]
print(f"\n{len(fails)} failing checks")
