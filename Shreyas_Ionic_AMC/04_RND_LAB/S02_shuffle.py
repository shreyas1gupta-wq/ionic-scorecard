"""S-02 Earnings short-vol — Gate-5 incremental-shuffle decomposition.
Arjun Rao / Quant. Pre-IC standing deliverable.

Question: is S-02's edge the CRUSH (event-specific IV collapse through the print)
or just short-vol-in-a-calm-tape? Decompose strategy return into
BASE + INCREMENTAL against two bases, bootstrap the incremental CI.

Run: PYTHONIOENCODING=utf-8 python S02_shuffle.py
"""
from __future__ import annotations
import json, sys, os
from datetime import datetime
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\lib"))
import guards as G  # noqa  (landmine guards mandatory in every entry point)

EARN_PATH = os.path.join(ROOT, r"intraday_options_strategy\buying\stock_earnings_vol.parquet")
RVIV_PATH = os.path.join(ROOT, r"intraday_options_strategy\buying\rv_iv_vol.parquet")
OUTDIR = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\results\S-02\20260704_shuffle")
os.makedirs(OUTDIR, exist_ok=True)

RNG = np.random.default_rng(20260704)
NBOOT = 1000

# ---------- PRE-REGISTRATION (state BEFORE computing incrementals) ----------
PREREG = {
    "hypothesis": "S-02 short ATM straddle held THROUGH earnings (c4_short_thru) has an "
                  "EVENT-SPECIFIC IV-crush edge beyond generic short-vol.",
    "registered_claim_under_test": "+21.6%/event fwd, 60% hit (raw mean c4_short_thru).",
    "gates_applied_first": ["DTE_at_event>=7 (drop expiry-week debit-denominator artifacts)",
                            "large-cap proxy = symbol had options data pre-2024-01-01"],
    "bases": {
        "a_c3_short_pre": "same names/period, short vol but EXIT BEFORE the print — isolates "
                          "the through-the-print (crush) component. incremental = c4 - c3.",
        "b_rviv_calmatch": "unconditional short straddles (rv_iv short_ret) matched by EXIT MONTH, "
                           "no earnings conditioning. incremental = mean(c4) - mean(base per exit-month)."
    },
    "kill_criteria": [
        "KILL-1: gated headline (DTE>=7) mean c4 collapses far below +21.6% "
        "=> registered number is a denominator artifact, not the edge.",
        "KILL-2: incremental vs BASE-a (c3) bootstrap 95% CI includes 0 OR upper bound < +5%/event "
        "=> the through-the-print CRUSH adds no reliable edge over exit-before-print short vol.",
        "KILL-3: incremental vs BASE-b (calendar-matched unconditional) CI includes 0 "
        "=> earnings conditioning adds nothing over generic short vol booked the same months.",
        "KILL-4: >60% of gated cumulative edge concentrated in 2024-26 (data-refill window) "
        "with 2021-23 thin/partial => not a regime-robust edge."
    ],
    "clears_only_if": "gated headline honest AND incremental vs BOTH bases CI strictly > 0 "
                      "AND crush (base-a) incremental economically meaningful (>~+3%/event).",
}

def boot_mean_ci(x, nboot=NBOOT, rng=RNG):
    x = np.asarray(pd.Series(x).dropna(), float)
    n = len(x)
    if n < 5:
        return dict(n=n, mean=float(np.mean(x)) if n else float("nan"), lo=float("nan"), hi=float("nan"))
    idx = rng.integers(0, n, size=(nboot, n))
    bm = x[idx].mean(axis=1)
    return dict(n=n, mean=float(x.mean()), lo=float(np.percentile(bm, 2.5)),
                hi=float(np.percentile(bm, 97.5)), p_gt0=float((bm > 0).mean()))

def boot_diff_ci(a, b, nboot=NBOOT, rng=RNG):
    """Bootstrap CI for mean(a) - mean(b) with independent resampling (unpaired)."""
    a = np.asarray(pd.Series(a).dropna(), float); b = np.asarray(pd.Series(b).dropna(), float)
    na, nb = len(a), len(b)
    if na < 5 or nb < 5:
        return dict(na=na, nb=nb, diff=float(a.mean()-b.mean()), lo=float("nan"), hi=float("nan"))
    ia = rng.integers(0, na, size=(nboot, na)); ib = rng.integers(0, nb, size=(nboot, nb))
    bd = a[ia].mean(axis=1) - b[ib].mean(axis=1)
    return dict(na=na, nb=nb, diff=float(a.mean()-b.mean()), lo=float(np.percentile(bd,2.5)),
                hi=float(np.percentile(bd,97.5)), p_gt0=float((bd > 0).mean()))

def desc(s):
    s = pd.Series(s).dropna()
    return dict(n=int(len(s)), mean=float(s.mean()), median=float(s.median()),
                std=float(s.std()), hit=float((s>0).mean()), min=float(s.min()), max=float(s.max()))

# ---------- LOAD + LINEAGE ----------
e = pd.read_parquet(EARN_PATH)
e["earn"] = pd.to_datetime(e["earn"]); e["exp"] = pd.to_datetime(e["exp"])
e["dte"] = (e["exp"] - e["earn"]).dt.days
e["year"] = e["earn"].dt.year
r = pd.read_parquet(RVIV_PATH)
r["exit"] = pd.to_datetime(r["exit"]); r["exp"] = pd.to_datetime(r["exp"])

LINEAGE = {
    "earnings_file": EARN_PATH, "earnings_rows": int(len(e)),
    "earnings_earn_max": str(e["earn"].max().date()), "earnings_exp_max": str(e["exp"].max().date()),
    "rviv_file": RVIV_PATH, "rviv_rows": int(len(r)),
    "rviv_exit_max": str(r["exit"].max().date()),
    "return_col_strategy": "c4_short_thru", "base_a_col": "c3_short_pre",
    "base_b_col": "rv_iv.short_ret (calendar-matched by exit month)",
    "units": "fraction of premium/spot per event; NOTE c4 uses per-leg premium denom -> unstable tail",
}

# ---------- GATES FIRST ----------
largecap_syms = set(e.loc[e["earn"] < "2024-01-01", "sym"].unique())
e["largecap"] = e["sym"].isin(largecap_syms)
gate = (e["dte"] >= 7) & (e["largecap"])
e_dte = e[e["dte"] >= 7].copy()
e_g = e[gate].copy()

HEADLINE = {
    "raw_all_1359_c4": desc(e["c4_short_thru"]),
    "gate_dte7_c4": desc(e_dte["c4_short_thru"]),
    "gate_dte7_largecap_c4": desc(e_g["c4_short_thru"]),
    "how_much_survives": {
        "raw_mean_pct": round(100*e["c4_short_thru"].mean(),2),
        "dte7_mean_pct": round(100*e_dte["c4_short_thru"].mean(),2),
        "dte7_largecap_mean_pct": round(100*e_g["c4_short_thru"].mean(),2),
        "note": "raw +21.3% is inflated by expiry-week denominator explosions "
                "(max single row +6759%). Gating alone cuts the headline by ~2/3.",
    },
}

# ---------- DECOMPOSITION: BASE A (c3 exit-before-print), gated ----------
# incremental is PAIRED per event: c4 - c3 on the same gated rows.
inc_a = (e_g["c4_short_thru"] - e_g["c3_short_pre"])
def boot_paired_ci(d, nboot=NBOOT, rng=RNG):
    d = np.asarray(pd.Series(d).dropna(), float); n=len(d)
    if n<5: return dict(n=n, mean=float(d.mean()), lo=float("nan"), hi=float("nan"))
    idx=rng.integers(0,n,size=(nboot,n)); bm=d[idx].mean(axis=1)
    return dict(n=n, mean=float(d.mean()), lo=float(np.percentile(bm,2.5)),
                hi=float(np.percentile(bm,97.5)), p_gt0=float((bm>0).mean()))
BASE_A = {
    "base_desc_c3_gated": desc(e_g["c3_short_pre"]),
    "strategy_desc_c4_gated": desc(e_g["c4_short_thru"]),
    "incremental_paired_c4_minus_c3": boot_paired_ci(inc_a),
    "interpretation": "incremental = value of HOLDING THROUGH THE PRINT vs exiting before it "
                      "= the pure event-crush component.",
}

# ---------- DECOMPOSITION: BASE B (rv_iv calendar-matched by exit month) ----------
# match each gated earnings event's EXP month to mean unconditional short_ret in same month.
e_g["exit_ym"] = e_g["exp"].dt.to_period("M")
r["exit_ym"] = r["exit"].dt.to_period("M")
r_month = r.groupby("exit_ym")["short_ret"].mean()
e_g["base_b"] = e_g["exit_ym"].map(r_month)
matched = e_g.dropna(subset=["base_b"])
inc_b = matched["c4_short_thru"] - matched["base_b"]
BASE_B = {
    "base_desc_rviv_calmatch": desc(matched["base_b"]),
    "strategy_desc_c4_matched": desc(matched["c4_short_thru"]),
    "incremental_paired_c4_minus_calmatch": boot_paired_ci(inc_b),
    "unmatched_events": int(len(e_g) - len(matched)),
    "interpretation": "incremental = earnings-conditioned short vol MINUS generic short vol "
                      "booked the same exit months (no earnings signal).",
}

# ---------- REGIME: per-year incremental (base a) + concentration ----------
peryear = []
yr_counts_full = {2021:True,2022:True,2023:True,2024:True,2025:True,2026:True}  # coverage flag placeholder
for y, g in e_g.groupby("year"):
    d = (g["c4_short_thru"] - g["c3_short_pre"])
    peryear.append(dict(year=int(y), n=int(len(g)),
                        c4_mean=round(100*g["c4_short_thru"].mean(),2),
                        c3_mean=round(100*g["c3_short_pre"].mean(),2),
                        incremental_crush=round(100*d.mean(),2),
                        hit_c4=round(100*(g["c4_short_thru"]>0).mean(),1),
                        # partial-year flag: fewer than ~half a normal year of events, or edge year
                        partial=bool(len(g) < 20)))
peryear = sorted(peryear, key=lambda x: x["year"])
# concentration: share of total gated cumulative c4 from 2024-26
tot = e_g["c4_short_thru"].sum()
share_2426 = float(e_g.loc[e_g["year"]>=2024,"c4_short_thru"].sum()/tot) if tot!=0 else float("nan")
n_2426 = int((e_g["year"]>=2024).sum())
REGIME = {"per_year": peryear,
          "concentration_2024_26_share_of_cum_c4": round(share_2426,3),
          "n_events_2024_26": n_2426, "n_events_total_gated": int(len(e_g)),
          "note": "2021-23 thin (data-refill 17-month-gap effect); treat pre-2024 as low-power."}

# ---------- VERDICT ----------
ia = BASE_A["incremental_paired_c4_minus_c3"]
ib = BASE_B["incremental_paired_c4_minus_calmatch"]
gated_head = HEADLINE["how_much_survives"]["dte7_largecap_mean_pct"]
crush_lo = ia["lo"]*100; crush_hi = ia["hi"]*100; crush_mean = ia["mean"]*100
b_lo = ib["lo"]*100

kills = []
if HEADLINE["how_much_survives"]["dte7_mean_pct"] < 15:
    kills.append(f"KILL-1 TRIPPED: DTE>=7 headline {HEADLINE['how_much_survives']['dte7_mean_pct']}% << registered +21.6% (denominator artifact).")
if ia["lo"] <= 0 or ia["hi"]*100 < 5:
    kills.append(f"KILL-2 TRIPPED: crush incremental (vs c3) CI [{crush_lo:.2f}%,{crush_hi:.2f}%] "
                 f"includes 0 or upper<+5% -> through-print adds no reliable crush.")
if ib["lo"] <= 0:
    kills.append(f"KILL-3 TRIPPED: vs calendar-matched unconditional CI [{b_lo:.2f}%,{ib['hi']*100:.2f}%] includes 0.")
if share_2426 > 0.60:
    kills.append(f"KILL-4 TRIPPED: {share_2426:.0%} of cum edge in 2024-26 (data-refill window).")

clears = len(kills) == 0
VERDICT = {
    "kills_tripped": kills,
    "verdict": "CLEARS-FOR-IC" if clears else "FAILS-PRE-IC",
    "register_number_if_clears": round(crush_mean,2) if clears else None,
    "weakest_assumption": "c4_short_thru per-event return uses per-leg premium denominator that "
                          "explodes to +6759% on expiry-week names; the registered +21.6% is that "
                          "artifact, not an IV-crush edge.",
}

OUT = {"prereg": PREREG, "lineage": LINEAGE, "headline": HEADLINE,
       "base_a_crush": BASE_A, "base_b_calmatch": BASE_B, "regime": REGIME, "verdict": VERDICT}

with open(os.path.join(OUTDIR,"config.json"),"w") as f:
    json.dump({"generated": datetime.now().isoformat(), "seed": 20260704, "nboot": NBOOT,
               "lineage": LINEAGE, "prereg": PREREG}, f, indent=2, default=str)
with open(os.path.join(OUTDIR,"metrics.json"),"w") as f:
    json.dump(OUT, f, indent=2, default=str)

# ---------- console report ----------
def pct(d,k="mean"): return f"{100*d[k]:+.2f}%"
print("="*78); print("S-02 INCREMENTAL-SHUFFLE DECOMPOSITION"); print("="*78)
print("\n[HEADLINE — gates first]")
print(f"  raw mean c4 (all 1359)        : {HEADLINE['how_much_survives']['raw_mean_pct']:+.2f}%  (== registered +21.6%)")
print(f"  DTE>=7 (n={HEADLINE['gate_dte7_c4']['n']})            : {HEADLINE['how_much_survives']['dte7_mean_pct']:+.2f}%  hit={HEADLINE['gate_dte7_c4']['hit']:.1%}")
print(f"  DTE>=7 & large-cap (n={HEADLINE['gate_dte7_largecap_c4']['n']})    : {HEADLINE['how_much_survives']['dte7_largecap_mean_pct']:+.2f}%  hit={HEADLINE['gate_dte7_largecap_c4']['hit']:.1%}")
print("\n[BASE A — crush = through-print minus exit-before-print (c4 - c3), gated]")
print(f"  base c3 (exit pre-print) mean : {pct(BASE_A['base_desc_c3_gated'])}")
print(f"  strat c4 (thru-print)   mean  : {pct(BASE_A['strategy_desc_c4_gated'])}")
print(f"  INCREMENTAL crush mean        : {crush_mean:+.2f}%   95% CI [{crush_lo:+.2f}%, {crush_hi:+.2f}%]  p(>0)={ia['p_gt0']:.2f}")
print("\n[BASE B — vs calendar-matched unconditional short vol (rv_iv)]")
print(f"  base (calmatch) mean          : {pct(BASE_B['base_desc_rviv_calmatch'])}")
print(f"  INCREMENTAL vs unconditional  : {ib['mean']*100:+.2f}%   95% CI [{ib['lo']*100:+.2f}%, {ib['hi']*100:+.2f}%]  p(>0)={ib['p_gt0']:.2f}")
print("\n[REGIME — per-year, gated]")
print(f"  {'yr':>5} {'n':>4} {'c4%':>7} {'c3%':>7} {'crush%':>7} {'hit':>6} partial")
for row in peryear:
    print(f"  {row['year']:>5} {row['n']:>4} {row['c4_mean']:>7.2f} {row['c3_mean']:>7.2f} {row['incremental_crush']:>7.2f} {row['hit_c4']:>5.1f}% {row['partial']}")
print(f"  2024-26 share of cum c4: {share_2426:.0%}  ({n_2426}/{len(e_g)} events)")
print("\n[VERDICT]")
for k in kills: print("  "+k)
print(f"  >>> {VERDICT['verdict']}")
print(f"  register-if-clears: {VERDICT['register_number_if_clears']}")
print(f"  weakest assumption: {VERDICT['weakest_assumption']}")
print(f"\nsaved -> {OUTDIR}")
