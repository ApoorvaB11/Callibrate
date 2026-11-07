"""Callibrate synthetic data generator.

Builds the eight synthetic data sets described in docs/DATA_SPEC.md and writes them
to data/callibrate.duckdb. Every value comes from generator/config.yaml and one random
seed, so the same command always rebuilds the same data.

Run from the repository root:
    python generator/generate.py

No real doctor, rep, company, brand or prescription is produced. Public US data is used
only as aggregate targets written into config.yaml; nothing here reads a real identifier.
"""
from __future__ import annotations

import datetime as dt
import math
import pathlib
import time

import duckdb
import numpy as np
import pandas as pd
import yaml
import zipcodes
from faker import Faker
from sklearn.cluster import KMeans

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONFIG = ROOT / "generator" / "config.yaml"
DB_PATH = ROOT / "data" / "callibrate.duckdb"

BRANDS = ["glyvexa", "sucrelo", "metaryn", "orvalis"]
GLY = 0  # index of our brand


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def luhn_check_digit(body: str) -> int:
    """NPI check digit: Luhn over the prefix 80840 plus the first nine digits."""
    digits = [int(c) for c in "80840" + body]
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return (10 - total % 10) % 10


def is_valid_npi(npi: str) -> bool:
    return len(npi) == 10 and npi[0] in "12" and luhn_check_digit(npi[:9]) == int(npi[9])


def make_invalid_npis(n: int, rng: np.random.Generator) -> list[str]:
    """10-digit IDs that look like NPIs but deliberately fail the check digit."""
    out: set[str] = set()
    while len(out) < n:
        body = str(rng.integers(1, 3)) + "".join(str(x) for x in rng.integers(0, 10, 8))
        good = luhn_check_digit(body)
        bad = (good + int(rng.integers(1, 10))) % 10
        out.add(body + str(bad))
    ids = sorted(out)
    rng.shuffle(ids)
    return ids


def softmax(x: np.ndarray) -> np.ndarray:
    x = x - x.max(axis=1, keepdims=True)
    e = np.exp(x)
    return e / e.sum(axis=1, keepdims=True)


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------
class Generator:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.rng = np.random.default_rng(cfg["seed"])
        self.fake = Faker("en_US")
        Faker.seed(cfg["seed"])
        cal = cfg["calendar"]
        self.weeks = cal["weeks"]
        self.warm = cal["warmup_weeks"]
        self.week0 = dt.date.fromisoformat(cal["first_week_start"])
        # simulation weeks run from 1 - warm to weeks (inclusive); index = week + warm - 1
        self.sim_weeks = np.arange(1 - self.warm, self.weeks + 1)
        self.W = len(self.sim_weeks)

    def widx(self, week):
        return np.asarray(week) + self.warm - 1

    # ----------------------------------------------------------------- geography
    def build_geography(self):
        cfg = self.cfg["geography"]
        rows = []
        for rkey, region in cfg["regions"].items():
            for dkey, d in region["districts"].items():
                for st in d["states"]:
                    for z in zipcodes.filter_by(state=st):
                        if not z["active"] or z["zip_code_type"] != "STANDARD" or not z["lat"]:
                            continue
                        lat, lon = float(z["lat"]), float(z["long"])
                        if "lat_min" in d and lat < d["lat_min"]:
                            continue
                        if "lat_max" in d and lat >= d["lat_max"]:
                            continue
                        rows.append(dict(zip=z["zip_code"], city=z["city"], county=z["county"], state=st,
                                         lat=lat, lon=lon, region=rkey, region_label=region["label"],
                                         district=dkey, district_label=d["label"]))
        self.zips = pd.DataFrame(rows).drop_duplicates("zip").reset_index(drop=True)
        log(f"geography: {len(self.zips):,} ZIP codes across {self.zips.district.nunique()} districts")

    # ------------------------------------------------------------------ doctors
    def build_doctors(self):
        cfg, rng = self.cfg, self.rng
        n = cfg["universe"]["doctors"]
        sp = cfg["specialties"]
        keys = list(sp)
        # doctor counts derived from volume share / relative volume per doctor
        w = np.array([sp[k]["volume_share"] / sp[k]["relative_volume"] for k in keys])
        w = w / w.sum()
        specialty = rng.choice(keys, size=n, p=w)

        districts = self.zips[["district", "region"]].drop_duplicates().reset_index(drop=True)
        per_d = n // len(districts)
        district = np.repeat(districts.district.values, per_d)
        district = np.concatenate([district, districts.district.values[: n - len(district)]])
        rng.shuffle(district)
        region = districts.set_index("district").region.loc[district].values

        # each doctor practises in a ZIP within their district
        zip_choice = np.empty(n, dtype=object)
        for dkey in districts.district:
            idx = np.where(district == dkey)[0]
            pool = self.zips[self.zips.district == dkey].zip.values
            zip_choice[idx] = rng.choice(pool, size=len(idx))
        z = self.zips.set_index("zip").loc[zip_choice]

        rel = np.array([sp[s]["relative_volume"] for s in specialty])
        spread = rng.lognormal(0.0, cfg["prescribing"]["volume_spread_sigma"], n)
        potential = rel * spread
        zero_w = np.where(np.isin(specialty, ["other", "cardiology", "nephrology"]), 3.0, 1.0)
        zero_idx = rng.choice(n, size=int(n * cfg["universe"]["zero_potential_share"]), replace=False,
                              p=zero_w / zero_w.sum())
        potential[zero_idx] = 0.0
        prescribers = potential > 0
        scale = cfg["prescribing"]["mean_new_starts_per_doctor_week"] * prescribers.sum() / potential.sum()
        lam = potential * scale  # expected new GLP-1 starts per week (all brands)

        # access tiers, with the P4 restricted cluster of endocrinologists in metro Atlanta
        tiers = cfg["field_force"]["access_tiers"]
        access = rng.choice(list(tiers), size=n, p=list(tiers.values()))
        p4 = cfg["scenarios"]["p4_restricted_cluster"]
        in_cluster = (z.state.values == p4["state"]) & np.isin(z.county.values, p4["counties"]) & (specialty == "endocrinology")
        roll = rng.random(n)
        access = np.where(in_cluster & (roll < p4["endocrinology_no_see_share"]), "no_see", access)
        access = np.where(in_cluster & (roll >= p4["endocrinology_no_see_share"]), "limited", access)

        pdrp = rng.random(n) < cfg["universe"]["pdrp_optout_share"]
        ids = make_invalid_npis(n, rng)

        names, creds = [], []
        for s in specialty:
            first, last = self.fake.first_name(), self.fake.last_name()
            if s == "nurse_practitioner":
                names.append(f"{first} {last}, NP"); creds.append("NP")
            elif s == "physician_assistant":
                names.append(f"{first} {last}, PA-C"); creds.append("PA")
            else:
                names.append(f"Dr. {first} {last}"); creds.append("MD")

        self.doctors = pd.DataFrame(dict(
            doctor_id=ids, doctor_name=names, credential=creds, specialty=specialty,
            specialty_label=[sp[s]["label"] for s in specialty],
            taxonomy_code=[sp[s]["taxonomy"] for s in specialty],
            zip=zip_choice, city=z.city.values, county=z.county.values, state=z.state.values,
            lat=z.lat.values + rng.normal(0, 0.01, n), lon=z.lon.values + rng.normal(0, 0.01, n),
            region=region, district=district, access_tier=access, pdrp_optout=pdrp,
        ))
        self.lam = lam
        self.in_p4 = in_cluster
        log(f"doctors: {n:,} ({prescribers.sum():,} GLP-1 prescribers)")

    # -------------------------------------------------------------- territories
    def build_territories(self):
        rng, k = self.rng, self.cfg["geography"]["territories_per_district"]
        d = self.doctors
        terr = np.empty(len(d), dtype=object)
        cents = []
        for dkey in sorted(d.district.unique()):
            idx = np.where(d.district.values == dkey)[0]
            xy = d.loc[idx, ["lat", "lon"]].values
            km = KMeans(n_clusters=k, n_init=5, random_state=int(rng.integers(1e6))).fit(xy)
            # capacity-balanced assignment so every territory has a workable doctor count
            cap = math.ceil(len(idx) / k)
            dist = ((xy[:, None, :] - km.cluster_centers_[None, :, :]) ** 2).sum(-1)
            order = np.argsort(np.sort(dist, axis=1)[:, 1] - np.sort(dist, axis=1)[:, 0])[::-1]
            load = np.zeros(k, dtype=int)
            assign = np.empty(len(idx), dtype=int)
            for i in order:
                for c in np.argsort(dist[i]):
                    if load[c] < cap:
                        assign[i] = c; load[c] += 1; break
            # order territories north to south so IDs are stable and readable
            rank = np.argsort(np.argsort(-km.cluster_centers_[:, 0]))
            for c in range(k):
                tid = f"{dkey.upper()}-{rank[c] + 1:02d}"
                terr[idx[assign == c]] = tid
                members = idx[assign == c]
                cents.append(dict(territory_id=tid, district=dkey,
                                  lat=d.lat.values[members].mean(), lon=d.lon.values[members].mean()))
        self.doctors["territory_id"] = terr
        dist_lab = self.zips.drop_duplicates("district").set_index("district")
        t = pd.DataFrame(cents)
        t["district_label"] = dist_lab.loc[t.district, "district_label"].values
        t["region"] = dist_lab.loc[t.district, "region"].values
        t["region_label"] = dist_lab.loc[t.district, "region_label"].values
        t = t.sort_values("territory_id").reset_index(drop=True)
        t["territory_name"] = [f"{r.district_label} {r.territory_id[-2:]}" for r in t.itertuples()]
        self.territories = t

        # ZIP alignment: every ZIP goes to the nearest territory centre in its district
        al = []
        for dkey, zg in self.zips.groupby("district"):
            tc = t[t.district == dkey]
            dd = ((zg[["lat", "lon"]].values[:, None, :] - tc[["lat", "lon"]].values[None, :, :]) ** 2).sum(-1)
            zg = zg.copy(); zg["territory_id"] = tc.territory_id.values[dd.argmin(1)]
            al.append(zg)
        self.alignment = pd.concat(al)[["zip", "city", "county", "state", "territory_id", "district",
                                        "district_label", "region", "region_label"]]
        log(f"territories: {len(t)}; doctors per territory {self.doctors.territory_id.value_counts().min()}–"
            f"{self.doctors.territory_id.value_counts().max()}")

    # -------------------------------------------------------------------- reps
    def build_reps(self):
        rng, ff, sc = self.rng, self.cfg["field_force"], self.cfg["scenarios"]
        t = self.territories
        lo, hi = ff["rep_execution_range"]
        reps = []
        for i, tid in enumerate(t.territory_id):
            reps.append(dict(rep_id=f"R{i + 1:03d}", rep_name=self.fake.name(), territory_id=tid,
                             start_week=1, end_week=self.weeks, execution=rng.uniform(lo, hi)))
        reps = pd.DataFrame(reps)
        # P3 vacancy: one territory loses its rep, then a new rep starts
        cand = t[t.region == "southeast"].territory_id.values
        self.p3_territory = rng.choice(cand)
        v0, v1 = sc["p3_vacancy"]["weeks"]
        old = reps.territory_id == self.p3_territory
        reps.loc[old, "end_week"] = v0 - 1
        new = reps[old].copy()
        new["rep_id"] = f"R{len(reps) + 1:03d}"; new["rep_name"] = self.fake.name()
        new["start_week"] = v1 + 1; new["end_week"] = self.weeks; new["execution"] = rng.uniform(lo, hi)
        self.reps = pd.concat([reps, new], ignore_index=True)
        # P2 over-calling territories (not the vacancy territory)
        others = [x for x in t.territory_id if x != self.p3_territory]
        self.p2_territories = sorted(rng.choice(others, size=sc["p2_over_calling"]["territories"], replace=False))
        log(f"reps: {len(self.reps)}; P2 territories {self.p2_territories}; P3 vacancy {self.p3_territory}")

    # ----------------------------------------------------------------- call plan
    def build_call_plan(self):
        rng, ff = self.rng, self.cfg["field_force"]
        d = self.doctors
        est = self.lam * rng.lognormal(0, 0.35, len(d))  # last year's noisy view of each doctor
        seg = np.full(len(d), "", dtype=object)
        quotas = ff["targets_per_rep"]
        for tid, idx in d.groupby("territory_id").indices.items():
            idx = idx[self.lam[idx] > 0]
            order = idx[np.argsort(-est[idx])]
            a, b, c = quotas["A"], quotas["B"], quotas["C"]
            seg[order[:a]] = "A"; seg[order[a:a + b]] = "B"; seg[order[a + b:a + b + c]] = "C"
        self.segment = seg
        rows = []
        targets = np.where(seg != "")[0]
        for q in range(1, self.weeks // 13 + 1):
            rows.append(pd.DataFrame(dict(quarter=q, doctor_id=d.doctor_id.values[targets],
                                          territory_id=d.territory_id.values[targets], segment=seg[targets],
                                          planned_calls=[ff["planned_calls_per_quarter"][s] for s in seg[targets]])))
        self.call_plan = pd.concat(rows, ignore_index=True)
        log(f"call plan: {len(targets):,} targets per quarter × {self.weeks // 13} quarters")

    # ------------------------------------------------------------ lapse scenario
    def choose_lapsers(self):
        """P5: pick ~8% of expected active Glyvexa writers to lapse, with a cause and week."""
        rng, sc = self.rng, self.cfg["scenarios"]["p5_lapsing"]
        base = np.array([self.cfg["brands"][b]["base_preference"] for b in BRANDS])
        exp_gly = self.lam * (base[GLY] / base.sum()) * (1 - self.cfg["prescribing"]["never_filled_share"]) * 26
        active = np.where(exp_gly >= sc["active_writer_min_nbrx_26w"])[0]
        n = int(round(len(active) * sc["share_of_active_writers"]))
        chosen = rng.choice(active, size=n, replace=False)
        causes = rng.choice(list(sc["causes"]), size=n, p=list(sc["causes"].values()))
        lo, hi = sc["lapse_week_range"]
        weeks = rng.integers(lo, hi + 1, size=n)
        self.lapse = pd.DataFrame(dict(doc_idx=chosen, cause=causes, lapse_week=weeks))
        log(f"P5: {n} lapsing writers out of {len(active)} expected active writers")

    # --------------------------------------------------------------------- calls
    def build_calls(self):
        rng, ff, sc = self.rng, self.cfg["field_force"], self.cfg["scenarios"]
        d = self.doctors
        seg = self.segment
        execu = ff["access_execution"]
        chan = ff["channel_by_access"]
        rep_by_t = self.reps.sort_values("start_week")
        v0, v1 = sc["p3_vacancy"]["weeks"]
        gap = {}
        for r in self.lapse[self.lapse.cause == "call_gap"].itertuples():
            gap[r.doc_idx] = (r.lapse_week - 10, r.lapse_week + 4)

        rows = []
        planned = np.array([ff["planned_calls_per_quarter"].get(s, 0) for s in seg])
        terr_cent = self.territories.set_index("territory_id")
        for q in range(1, self.weeks // 13 + 1):
            wk_lo = (q - 1) * 13 + 1
            for tid, idx in d.groupby("territory_id").indices.items():
                rep_rows = rep_by_t[rep_by_t.territory_id == tid]
                p_rep = rep_rows.execution.values[0]
                tidx = idx[seg[idx] != ""]
                p = p_rep * np.array([execu[a] for a in d.access_tier.values[tidx]])
                made = rng.binomial(planned[tidx], p)
                # occasional bonus calls on A targets
                made += (seg[tidx] == "A") * rng.binomial(1, 0.25, len(tidx))
                doc = np.repeat(tidx, made)
                n_target_calls = len(doc)
                share = sc["p2_over_calling"]["low_potential_call_share"] if tid in self.p2_territories else ff["non_target_call_share"]
                # reps fill their week: total calls ≈ field days × calls per day ÷ in-person share
                cap = int(13 * ff["field_days_per_week"] * ff["in_person_calls_per_day"]
                          / ff["in_person_share_of_calls"] * rng.uniform(0.9, 1.05) * p_rep / 0.85)
                n_extra = int(round(cap * share))
                n_bonus = max(0, cap - n_target_calls - n_extra)
                # bonus calls go to targets the rep already sees (favourites), weighted by segment
                wts = made * np.array([{"A": 3, "B": 2, "C": 1}[s] for s in seg[tidx]])
                if wts.sum() > 0 and n_bonus:
                    doc = np.concatenate([doc, rng.choice(tidx, size=n_bonus, p=wts / wts.sum())])
                pool = idx[seg[idx] == ""]
                if tid in self.p2_territories:
                    # convenient low-potential doctors close to the rep's base
                    c = terr_cent.loc[tid]
                    dist = (d.lat.values[idx] - c.lat) ** 2 + (d.lon.values[idx] - c.lon) ** 2
                    low = idx[(self.lam[idx] < np.quantile(self.lam[idx], 0.5))]
                    near = low[np.argsort(dist[np.isin(idx, low)])][: max(30, len(low) // 3)]
                    pool = near
                extra = rng.choice(pool, size=n_extra) if len(pool) and n_extra else np.array([], dtype=int)
                doc = np.concatenate([doc, extra]).astype(int)
                week = wk_lo + rng.integers(0, 13, len(doc))
                tier = d.access_tier.values[doc]
                remote_p = np.array([chan[a]["remote"] for a in tier])
                channel = np.where(rng.random(len(doc)) < remote_p, "remote", "in_person")
                df = pd.DataFrame(dict(doc_idx=doc, week=week, channel=channel, territory_id=tid))
                # emails to targets
                rate = np.array([ff["emails_per_target_per_quarter"][a] for a in d.access_tier.values[tidx]])
                ne = rng.poisson(rate)
                edoc = np.repeat(tidx, ne)
                df = pd.concat([df, pd.DataFrame(dict(doc_idx=edoc, week=wk_lo + rng.integers(0, 13, len(edoc)),
                                                      channel="email", territory_id=tid))])
                rows.append(df)
        calls = pd.concat(rows, ignore_index=True)
        # P3 vacancy: no calls of any kind in that territory during the gap
        calls = calls[~((calls.territory_id == self.p3_territory) & calls.week.between(v0, v1))]
        # P5 call gap: the rep stops seeing those doctors
        if gap:
            g = calls.doc_idx.map(lambda i: gap.get(i, (0, -1)))
            lo = g.map(lambda x: x[0]); hi = g.map(lambda x: x[1])
            calls = calls[~calls.week.between(lo, hi) | (calls.channel == "email")]
        # assign the rep on duty that week
        calls["rep_id"] = ""
        for r in self.reps.itertuples():
            m = (calls.territory_id == r.territory_id) & calls.week.between(r.start_week, r.end_week)
            calls.loc[m, "rep_id"] = r.rep_id
        calls = calls[calls.rep_id != ""]
        wd = rng.integers(2, 7, len(calls))  # Monday..Friday within a Saturday-start week
        calls["call_date"] = [self.week0 + dt.timedelta(days=int((w - 1) * 7 + x)) for w, x in zip(calls.week, wd)]
        calls = calls.sort_values(["call_date", "rep_id"]).reset_index(drop=True)
        calls["call_id"] = [f"C{i + 1:07d}" for i in range(len(calls))]
        self.calls_idx = calls
        log(f"calls: {len(calls):,} interactions ({(calls.channel != 'email').sum():,} calls, "
            f"{(calls.channel == 'email').sum():,} emails)")

    # ------------------------------------------------------------- payers
    def build_payers(self):
        p = self.cfg["payers"]
        plans = pd.DataFrame(p["plans"])
        self.plans = plans
        base = {
            "PL01": dict(glyvexa="preferred_pa", sucrelo="preferred_pa", metaryn="preferred_pa", orvalis="preferred_pa"),
            "PL02": dict(glyvexa="preferred_pa", sucrelo="preferred_pa", metaryn="preferred_pa", orvalis="preferred_pa"),
            "PL03": dict(glyvexa="preferred", sucrelo="preferred_pa", metaryn="preferred_pa", orvalis="preferred_pa"),
            "PL04": dict(glyvexa="preferred_pa", sucrelo="preferred", metaryn="preferred", orvalis="preferred_pa"),
            "PL05": dict(glyvexa="preferred", sucrelo="preferred_pa", metaryn="preferred", orvalis="preferred"),
            "PL06": dict(glyvexa="non_preferred_pa", sucrelo="preferred", metaryn="preferred", orvalis="non_preferred_pa"),
            "PL07": dict(glyvexa="non_preferred_pa", sucrelo="preferred", metaryn="preferred", orvalis="non_preferred_pa"),
        }
        s1 = self.cfg["scenarios"]["p1_formulary_shock"]
        rows = []
        first = int(self.sim_weeks[0])
        for pid, m in base.items():
            for b, st in m.items():
                if pid == s1["plan_id"] and b == s1["brand"]:
                    rows.append(dict(plan_id=pid, brand=b, status=st, effective_week=first, end_week=s1["week"] - 1))
                    rows.append(dict(plan_id=pid, brand=b, status=s1["to_status"], effective_week=s1["week"], end_week=self.weeks))
                else:
                    rows.append(dict(plan_id=pid, brand=b, status=st, effective_week=first, end_week=self.weeks))
        f = pd.DataFrame(rows)
        f["tier"] = f.status.map({"preferred": 2, "preferred_pa": 3, "non_preferred_pa": 4})
        f["prior_auth"] = f.status != "preferred"
        f["step_therapy"] = f.status == "non_preferred_pa"
        f["quantity_limit"] = True
        self.formulary = f
        # status lookup: plan x brand x simulation week
        self.plan_ids = list(plans.plan_id)
        stat_names = ["preferred", "preferred_pa", "non_preferred_pa"]
        self.status_grid = np.zeros((len(self.plan_ids), len(BRANDS), self.W), dtype=int)
        for r in f.itertuples():
            pi, bi = self.plan_ids.index(r.plan_id), BRANDS.index(r.brand)
            lo, hi = self.widx(r.effective_week), self.widx(r.end_week)
            self.status_grid[pi, bi, lo:hi + 1] = stat_names.index(r.status)
        self.status_names = stat_names

    # ------------------------------------------------------------- prescribing
    def build_claims(self):
        rng, cfg = self.rng, self.cfg
        pr = cfg["prescribing"]
        d = self.doctors
        n = len(d)
        W = self.W

        # calls in the prior 8 weeks, per doctor and simulation week (warm-up uses each doctor's plan rate)
        cmat = np.zeros((n, W))
        c = self.calls_idx[self.calls_idx.channel != "email"]
        np.add.at(cmat, (c.doc_idx.values, self.widx(c.week.values)), 1)
        rate = np.zeros(n)
        for q_doc, cnt in c[c.week <= 13].groupby("doc_idx").size().items():
            rate[q_doc] = cnt / 13
        cmat[:, : self.warm] = rate[:, None]
        cs = np.cumsum(np.pad(cmat, ((0, 0), (8, 0))), axis=1)
        prior8 = cs[:, 8:] - cs[:, :-8]  # calls in the 8 weeks before each week

        # Glyvexa adjustments over time: launch growth and P5 lapses
        adj = np.zeros((n, W))
        adj_comp = np.zeros((n, W))
        trend = 0.004 * (self.sim_weeks - self.sim_weeks[0])
        mult = math.log(cfg["scenarios"]["p5_lapsing"]["post_lapse_multiplier"])
        for r in self.lapse.itertuples():
            lw = self.widx(r.lapse_week)
            if r.cause == "silent":
                adj[r.doc_idx, lw:] = mult
            else:
                ramp = 8 if r.cause == "competitor_push" else 6
                adj[r.doc_idx, lw - ramp:lw] = np.linspace(0, mult, ramp)
                adj[r.doc_idx, lw:] = mult
                if r.cause == "competitor_push":
                    adj_comp[r.doc_idx, lw - ramp:lw] = np.linspace(0, 0.8, ramp)
                    adj_comp[r.doc_idx, lw:] = 0.8

        # doctor brand affinity
        base = np.array([cfg["brands"][b]["base_preference"] for b in BRANDS])
        affinity = rng.dirichlet(base * 6, size=n)

        # new patient starts: Poisson per doctor-week
        counts = rng.poisson(self.lam[:, None] * np.ones((1, W)))
        doc, wi = np.nonzero(counts)
        reps = counts[doc, wi]
        doc = np.repeat(doc, reps); wi = np.repeat(wi, reps)
        log(f"new prescriptions written (all brands, incl. warm-up): {len(doc):,}")

        # payer per patient: line of business, then a plan available in the doctor's region
        lob_mix = cfg["payers"]["line_of_business_mix"]
        lob = rng.choice(list(lob_mix), size=len(doc), p=list(lob_mix.values()))
        region = d.region.values[doc]
        plan = np.empty(len(doc), dtype=object)
        pl = self.plans
        for lb in lob_mix:
            for rg in ["southeast", "gulf"]:
                m = (lob == lb) & (region == rg)
                opts = pl[(pl.lob == lb) & ((pl.region == rg) | (pl.region == "all"))]
                plan[m] = rng.choice(opts.plan_id.values, size=m.sum(), p=(opts.weight / opts.weight.sum()).values)
        # P1: tilt Gulf Medicare towards the Bayou plan in some territories, so the shock is local
        terr = d.territory_id.values[doc]
        gulf_t = self.territories[self.territories.region == "gulf"].territory_id.values
        heavy = set(rng.choice(gulf_t, size=6, replace=False))
        self.p1_heavy = sorted(heavy)
        hm = np.isin(terr, list(heavy)) & (lob == "medicare") & (rng.random(len(doc)) < 0.60)
        plan[hm] = "PL03"
        plan_i = np.array([self.plan_ids.index(x) for x in plan])

        # brand choice (multinomial logit), with Glyvexa's intercept tuned to hit the NBRx share target
        logits = np.log(affinity[doc])
        logits[:, GLY] += pr["call_effect"] * np.log1p(prior8[doc, wi]) + trend[wi] + adj[doc, wi]
        logits[:, 1:] += adj_comp[doc, wi][:, None] * np.array([1, 0, 0])[None, :]
        out = wi >= self.warm  # output weeks only
        target = cfg["targets"]["glyvexa_nbrx_share"]
        rules = cfg["payers"]["status_rules"]
        st_now = self.status_grid[plan_i, :, wi]  # status of each brand for this patient
        keep = np.array([1 - rules[s]["reject"] * (1 - rules[s]["approved_later"]) for s in self.status_names])
        paidp = keep[st_now]
        shift = 0.0
        for _ in range(30):
            l2 = logits.copy(); l2[:, GLY] += shift
            pr_ = softmax(l2) * paidp
            share = (pr_[out, GLY].sum() / pr_[out].sum())
            shift += (math.log(target) - math.log(share)) * 0.9
        logits[:, GLY] += shift
        probs = softmax(logits)
        u = rng.random(len(doc))[:, None]
        brand = (probs.cumsum(1) < u).sum(1)
        brand = np.minimum(brand, len(BRANDS) - 1)

        # some prescriptions are never taken to the pharmacy
        filled = rng.random(len(doc)) >= pr["never_filled_share"]
        doc, wi, lob, plan_i, brand, affinity_d = doc[filled], wi[filled], lob[filled], plan_i[filled], brand[filled], affinity[doc[filled]]
        npat = len(doc)
        patient = np.arange(npat)

        # pharmacy adjudication of the first fill
        status = self.status_grid[plan_i, brand, wi]
        rj = np.array([rules[s]["reject"] for s in self.status_names])[status]
        rejected = rng.random(npat) < rj
        outcome = np.full(npat, "paid", dtype=object)
        idx = np.where(rejected)[0]
        st = status[idx]
        r = rng.random(len(idx))
        a = np.array([rules[s]["approved_later"] for s in self.status_names])[st]
        ab = np.array([rules[s]["abandon"] for s in self.status_names])[st]
        sw = 1 - a - ab
        outcome[idx] = np.where(r < a, "approved_later", np.where(r < a + ab, "abandon", "switch"))

        claims = []
        # rejected first-fill claims (reject code 75 = prior authorisation required)
        claims.append(pd.DataFrame(dict(patient=patient[idx], doc_idx=doc[idx], wi=wi[idx], brand=brand[idx],
                                        plan_i=plan_i[idx], fill_number=0, rx_seq=0,
                                        response_status="R", reject_code="75")))
        # first paid fill: same brand (paid now or after PA approval) or a competitor after a switch
        paid_brand = brand.copy()
        paid_w = wi.copy()
        delay = rng.integers(1, 3, npat)
        appr = outcome == "approved_later"
        paid_w[appr] += delay[appr]
        swm = outcome == "switch"
        if swm.any():
            aff = affinity_d[swm].copy()
            aff[np.arange(swm.sum()), brand[swm]] = 0
            aff = aff / aff.sum(1, keepdims=True)
            paid_brand[swm] = (aff.cumsum(1) < rng.random(swm.sum())[:, None]).sum(1)
            paid_w[swm] += 1
        has_paid = outcome != "abandon"
        lob_drop = cfg["prescribing"]["refill_dropout_per_fill"]
        drop = np.array([lob_drop[x] for x in lob])
        nfills = rng.geometric(drop)  # total paid fills including the first
        pi_ = np.where(has_paid)[0]
        nf = nfills[pi_]
        rows = np.repeat(pi_, nf)
        k = np.concatenate([np.arange(m) for m in nf])
        jitter = (rng.random(len(rows)) < 0.15).astype(int)
        jitter[k == 0] = 0
        # cumulative jitter within each patient
        jc = pd.Series(jitter).groupby(rows).cumsum().values
        fw = paid_w[rows] + k * pr["fill_interval_weeks"] + jc
        ren = pr["renewal_every_n_fills"]
        claims.append(pd.DataFrame(dict(patient=rows, doc_idx=doc[rows], wi=fw, brand=paid_brand[rows],
                                        plan_i=plan_i[rows], fill_number=k % ren, rx_seq=k // ren,
                                        response_status="P", reject_code="")))
        cl = pd.concat(claims, ignore_index=True)
        cl = cl[cl.wi < W]
        cl["week"] = self.sim_weeks[cl.wi.values]
        self.patient_outcome = pd.DataFrame(dict(patient=patient, doc_idx=doc, wi=wi, brand=brand, lob=lob,
                                                 plan_i=plan_i, outcome=outcome))
        self.n_written = len(filled)
        self.n_never_filled = int((~filled).sum())
        self.claims_raw = cl
        log(f"claims: {len(cl):,} rows ({(cl.response_status == 'R').sum():,} rejected); Glyvexa intercept shift {shift:+.3f}")

    # ------------------------------------------------------------- assemble
    def assemble(self):
        rng = self.rng
        d = self.doctors
        cl = self.claims_raw
        plan_ids = np.array(self.plan_ids)
        lob_of_plan = self.plans.set_index("plan_id").lob
        ndc = {b: self.cfg["brands"][b]["ndc11"] for b in BRANDS}
        brand_names = np.array(BRANDS)
        out = pd.DataFrame(dict(
            week=cl.week.values,
            patient_id=["PT" + format(int(p), "07d") for p in cl.patient.values],
            prescriber_id=d.doctor_id.values[cl.doc_idx.values],
            brand=brand_names[cl.brand.values],
            plan_id=plan_ids[cl.plan_i.values],
            fill_number=cl.fill_number.values,
            rx_seq=cl.rx_seq.values,
            response_status=cl.response_status.values,
            reject_code=cl.reject_code.values,
        ))
        out["ndc11"] = out.brand.map(ndc)
        out["line_of_business"] = out.plan_id.map(lob_of_plan)
        out["rx_number"] = out.patient_id.str[2:] + out.rx_seq.astype(str).str.zfill(2)
        out["days_supply"] = 28
        out["quantity"] = np.where(out.brand == "orvalis", 30, 4)
        out["pharmacy_channel"] = np.where(rng.random(len(out)) < 0.12, "mail", "retail")
        wd = rng.integers(0, 7, len(out))
        out["service_date"] = (pd.to_datetime(self.week0) + pd.to_timedelta((out.week.values - 1) * 7 + wd, unit="D"))
        # formulary status at fill
        st = self.status_grid[cl.plan_i.values, cl.brand.values, cl.wi.values]
        out["formulary_status"] = np.array(self.status_names)[st]
        out = out.sort_values(["service_date", "patient_id"]).reset_index(drop=True)
        out["claim_id"] = ["CL" + format(i + 1, "08d") for i in range(len(out))]
        self.claims = out[["claim_id", "service_date", "week", "patient_id", "prescriber_id", "brand", "ndc11",
                           "rx_number", "fill_number", "days_supply", "quantity", "plan_id", "line_of_business",
                           "formulary_status", "response_status", "reject_code", "pharmacy_channel"]]

        c = self.calls_idx
        self.calls = pd.DataFrame(dict(call_id=c.call_id, call_date=c.call_date, week=c.week,
                                       rep_id=c.rep_id, doctor_id=d.doctor_id.values[c.doc_idx.values],
                                       territory_id=c.territory_id, channel=c.channel))
        self.weeks_table = pd.DataFrame(dict(week=self.sim_weeks))
        self.weeks_table["week_start"] = [self.week0 + dt.timedelta(days=int((w - 1) * 7)) for w in self.sim_weeks]
        self.weeks_table["week_end"] = self.weeks_table.week_start + dt.timedelta(days=6)
        self.weeks_table["quarter"] = np.where(self.sim_weeks >= 1, (self.sim_weeks - 1) // 13 + 1, 0)
        self.weeks_table["is_history"] = self.sim_weeks < 1

        lp = self.lapse.copy()
        lp["doctor_id"] = d.doctor_id.values[lp.doc_idx]
        self.answer_lapses = lp[["doctor_id", "cause", "lapse_week"]].sort_values("lapse_week")

    # ------------------------------------------------------------------ write
    def write(self):
        DB_PATH.parent.mkdir(exist_ok=True)
        if DB_PATH.exists():
            DB_PATH.unlink()
        con = duckdb.connect(str(DB_PATH))
        doctors = self.doctors.drop(columns=["lat", "lon"]).assign(
            lat=self.doctors.lat.round(4), lon=self.doctors.lon.round(4))
        tables = {
            "doctors": doctors,
            "territories": self.territories.round({"lat": 4, "lon": 4}),
            "zip_alignment": self.alignment,
            "reps": self.reps.drop(columns=["execution"]),
            "call_plan": self.call_plan,
            "calls": self.calls,
            "plans": self.plans.drop(columns=["weight"]),
            "formulary": self.formulary,
            "pharmacy_claims": self.claims,
            "weeks": self.weeks_table,
            "brands": pd.DataFrame([dict(brand=k, **v) for k, v in self.cfg["brands"].items()]).drop(columns=["base_preference"]),
            "answer_key_lapses": self.answer_lapses,
        }
        for name, df in tables.items():
            con.register("tmp_df", df)
            con.execute(f"CREATE TABLE {name} AS SELECT * FROM tmp_df")
            con.unregister("tmp_df")
        con.execute("ALTER TABLE pharmacy_claims ALTER service_date TYPE DATE")
        con.execute("ALTER TABLE calls ALTER call_date TYPE DATE")
        # weekly prescriptions, counted from paid claims (NBRx = first paid fill of the brand in 52 weeks)
        con.execute("""
            CREATE TABLE weekly_rx AS
            WITH paid AS (
                SELECT *, LAG(week) OVER (PARTITION BY patient_id, brand ORDER BY service_date, claim_id) AS prev_week
                FROM pharmacy_claims WHERE response_status = 'P'
            )
            SELECT prescriber_id AS doctor_id, brand, week,
                   COUNT(*) AS trx,
                   COUNT(*) FILTER (WHERE fill_number = 0) AS nrx,
                   COUNT(*) FILTER (WHERE prev_week IS NULL OR week - prev_week > 52) AS nbrx
            FROM paid GROUP BY ALL
        """)
        con.execute("""CREATE TABLE scenario_facts AS SELECT * FROM (VALUES
            ('P1', 'plan_id', 'PL03'), ('P1', 'week', '88'), ('P1', 'heavy_territories', ?),
            ('P2', 'territories', ?), ('P3', 'territory', ?), ('P3', 'weeks', '40-47'),
            ('P4', 'area', 'Fulton, DeKalb, Cobb and Gwinnett counties, GA')) t(scenario, fact, value)""",
                    [", ".join(self.p1_heavy), ", ".join(self.p2_territories), self.p3_territory])
        sizes = {t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in list(tables) + ["weekly_rx"]}
        con.close()
        for t, s in sizes.items():
            log(f"  {t:<18} {s:>10,} rows")
        log(f"written {DB_PATH.relative_to(ROOT)} ({DB_PATH.stat().st_size / 1e6:.0f} MB)")

    def run(self):
        self.build_geography()
        self.build_doctors()
        self.build_territories()
        self.build_reps()
        self.build_call_plan()
        self.choose_lapsers()
        self.build_calls()
        self.build_payers()
        self.build_claims()
        self.assemble()
        self.write()


def main():
    cfg = yaml.safe_load(CONFIG.read_text())
    t0 = time.time()
    Generator(cfg).run()
    log(f"done in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
