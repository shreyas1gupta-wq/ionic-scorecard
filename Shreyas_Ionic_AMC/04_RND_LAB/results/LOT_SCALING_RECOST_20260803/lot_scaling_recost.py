"""MDD-AWARE LOT SCALING, RE-COST — does the 2026-08-01 sizing recommendation survive the
Budget-2026 STT hike (STT_RECOST_20260803, 7.27 -> 14.47 pts RT at spot 24,000)?

THIS IS A REBUILD OF LOT_SCALING_20260801/lot_scaling.py, COST MODEL ONLY CHANGED.
Everything else — signal (THREE_SOLDIERS), hold windows (1-session=26 bars, 3-session=78 bars),
the RANDOM-LONG beta control, the 5 sizing policies, MAX_LOTS=40, RUIN_FRAC=0.50, MARGIN_PCT=0.10
from contemporaneous spot, N_BOOT=2000 stationary block bootstrap at block=3 months, one position
at a time, pathsafe pessimistic bound — is identical to the 2026-08-01 run. See that file's full
docstring for the original rationale; this header only documents what changed.

WHAT CHANGED
  OLD basis (unchanged from the original script, kept for explicit side-by-side comparison):
    ct_old = (4.47 if day < 2024-10-01 else 5.97) + 0.5      # flat, era-stepped, NOT spot-scaled
  NEW basis (STT_RECOST_20260803's confirmed Budget-2026 rate, applied throughout the sample —
  this is the FORWARD convention used in PORTFOLIOS_RECOST_20260803: "as if every historical trade
  had instead paid the post-Budget-2026 rate", the number that matters for a forward capital call):
    ct_new = 0.0005 * entry_spot + 1.97 + 0.5                # STT on CONTEMPORANEOUS spot, 0.05%
  At spot 24,000: ct_new = 12.00 + 1.97 + 0.5 = 14.47, matching STT_RECOST_20260803 exactly.

WHY BOTH COST BASES ARE REPLAYED WITH THE SAME BOOTSTRAP DRAWS
  A flat per-trade subtraction (report -7.2 avg pts and call it done) would miss that the stop/trail
  exit path interacts with cost nonlinearly (a trade that would have been a marginal winner net of
  the old cost can flip to a net loser at the new cost, which changes which months are "positive"
  under NAIVE_MONTHLY's add-after-a-win rule, which changes the lot path, which changes maxDD). So:
  trades are built ONCE (identical entries/exits/gross P&L under both bases — only the cost
  subtraction differs), and the SAME block-bootstrap month-ordering draws (same RNG stream, same
  index arrays) are replayed against the OLD monthly series and the NEW monthly series. This isolates
  the cost effect from resampling noise and answers "does the edge survive" from the actual replay,
  not from arithmetic.

HONESTY NOTES (carried over unchanged)
  - The 6,000-8,000% medians in the original run were ARITHMETIC, not a forecast: MAX_LOTS=40 binds
    almost immediately (median lots = 40 in most policies), so those are "max-permitted-leverage held
    for 11 years" paths, and over half the compounding is leveraged index beta on a +186% sample. The
    same caveat applies here, harder, because costs are higher.
  - CAPACITY: the capacity desk has since confirmed 40 lots = 0.047% of NIFTY futures ADV. The 40-lot
    cap is NOT a liquidity constraint; it is an arbitrary number in the script. A supplementary pass
    below relaxes MAX_LOTS to see what actually binds once it is not the cap (spoiler: margin does,
    for naive-monthly; for CPPI_FLOOR specifically, relaxing the cap makes tail risk WORSE — see
    "MAX_LOTS relaxed" section).
"""
from __future__ import annotations

import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
BASE = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
from pathsafe import simulate_exit      # noqa: E402

OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)
IDX = BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
RNG = np.random.default_rng(20260801)          # same seed as the original run (reproducible mask)

LOT = 65
CAP0 = 1_000_000.0
MARGIN_PCT = 0.10
RUIN_FRAC = 0.50
MAX_LOTS = 40
MAX_LOTS_RELAXED = 100_000                     # supplementary pass: cap effectively off, margin binds
MDD_CEILING = 0.25
BUFFER_FRAC = 0.60
FLOOR_RATCHET = 0.80
CPPI_MULT = 3.0
N_BOOT = 2000
BLOCK_MONTHS = 3
BREAK = pd.Timestamp("2024-10-01")
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}

# cost model constants
STT_FUT_NEW = 0.0005      # Budget-2026, effective 2026-04-01
NON_STT_FUT_PTS = 1.97
SLIP_FUT_RT = 0.5


def cost_old(day_ts: pd.Timestamp) -> float:
    """UNCHANGED from LOT_SCALING_20260801: flat, era-stepped, not spot-scaled."""
    return (4.47 if day_ts < BREAK else 5.97) + 0.5


def cost_new(spot: float) -> float:
    """STT_RECOST_20260803 basis: STT from CONTEMPORANEOUS spot at the new 0.05% rate."""
    return STT_FUT_NEW * spot + NON_STT_FUT_PTS + SLIP_FUT_RT


# ------------------------------------------------------------------ rebuild the trade series
print("[load] 1-min -> 15-min", flush=True)
p1 = pd.read_parquet(IDX, columns=["open", "high", "low", "close"]).sort_index()
p1 = p1[(p1.index.time >= pd.Timestamp("09:15").time()) &
        (p1.index.time <= pd.Timestamp("15:30").time())]
b = (p1.resample("15min", origin="start_day", offset="9h15min")
     .agg(o=("open", "first"), h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna())
b = b[(b.index.time >= pd.Timestamp("09:15").time()) &
      (b.index.time <= pd.Timestamp("15:15").time())]
b["d"] = b.index.normalize()
dly = p1.resample("1D").agg(h=("high", "max"), l=("low", "min"), c=("close", "last")).dropna()
tr = pd.concat([dly.h - dly.l, (dly.h - dly.c.shift()).abs(),
                (dly.l - dly.c.shift()).abs()], axis=1).max(axis=1)
dly["atr14"] = tr.rolling(14).mean()
b = b.join(dly[["atr14"]], on="d")

o, h, l, c = (b[x].to_numpy(float) for x in ("o", "h", "l", "c"))
body = c - o
green = body > 0
p_c = np.r_[np.nan, c[:-1]]
pp_c = np.r_[np.nan, np.nan, c[:-2]]
p_l = np.r_[np.nan, l[:-1]]
p_h = np.r_[np.nan, h[:-1]]
g1 = np.r_[False, green[:-1]]
g2 = np.r_[False, False, green[:-2]]
SOLDIERS = green & g1 & g2 & (c > p_c) & (p_c > pp_c)
atr = b.atr14.to_numpy(float)
ds = b.d.dt.strftime("%Y-%m-%d").to_numpy()
days = b.d.to_numpy()
HLC = np.ascontiguousarray(b[["h", "l", "c"]].to_numpy(float))
COLS = ["high", "low", "close"]
TS = b.index.to_numpy()
N = len(b)
print(f"       {N:,} bars; SOLDIERS fires {int(np.nan_to_num(SOLDIERS).sum()):,}", flush=True)


def build_trades(mask, hold_bars, label):
    """ONE POSITION AT A TIME, stop=trail=max(prior-candle range, 0.4 ATR). Long only.
    Identical trade selection/exit machinery to the original; carries BOTH cost bases."""
    rows, blocked = [], -1
    for i in np.where(np.nan_to_num(mask.astype(float)) > .5)[0]:
        i = int(i)
        if i <= blocked or i + 4 >= N or ds[i] in SCH:
            continue
        a = atr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        entry = c[i]
        raw = entry - min(l[i], p_l[i])
        stop = max(raw, 0.4 * a)
        if not np.isfinite(stop) or stop <= 0 or stop > 3 * a:
            continue
        seg = HLC[i + 1:i + 1 + hold_bars]
        if len(seg) < 4:
            continue
        r = simulate_exit(pd.DataFrame(seg, columns=COLS), entry, +1, stop=stop, trail=stop)
        day_ts = pd.Timestamp(days[i])
        co = cost_old(day_ts)
        cn = cost_new(entry)
        rows.append(dict(t=TS[i], day=day_ts, spot=entry, stop=stop, gross=r.pnl_pessimistic,
                         pts_old=r.pnl_pessimistic - co, pts_new=r.pnl_pessimistic - cn,
                         ct_old=co, ct_new=cn))
        blocked = i + min(hold_bars, len(seg))
    d = pd.DataFrame(rows)
    d["label"] = label
    nmo = max(len(pd.PeriodIndex(d.day, freq="M").unique()), 1)
    print(f"[trades] {label:<22} n={len(d):>5}  mean_old {d.pts_old.mean():+7.2f}  "
          f"mean_new {d.pts_new.mean():+7.2f}  delta {d.pts_new.mean()-d.pts_old.mean():+6.2f}  "
          f"/mo {len(d)/nmo:5.1f}  mean_spot {d.spot.mean():,.0f}", flush=True)
    return d


REAL26 = build_trades(SOLDIERS, 26, "SOLDIERS hold26 (1-session)")
REAL78 = build_trades(SOLDIERS, 78, "SOLDIERS hold78 (3-session)")

rand_mask = np.zeros(N, bool)
elig = np.arange(30, N - 80)
rand_mask[RNG.choice(elig, size=int(np.nan_to_num(SOLDIERS).sum()), replace=False)] = True
BETA26 = build_trades(rand_mask, 26, "RANDOM-LONG hold26 (BETA control)")


# ------------------------------------------------------------------ the sizing engine (unchanged)
def run_policy(monthly_pts, monthly_spot, policy, worst_dd_per_lot, max_lots=MAX_LOTS):
    eq = CAP0
    peak = CAP0
    floor = CAP0 * FLOOR_RATCHET
    path, lots_hist = [CAP0], []
    ruined_at = None
    prev_month_pos = True
    lots = 1
    for m, (pts, spot) in enumerate(zip(monthly_pts, monthly_spot)):
        if eq < RUIN_FRAC * CAP0:
            ruined_at = m
            break
        margin_per_lot = MARGIN_PCT * spot * LOT
        max_by_margin = int(np.floor(eq / max(margin_per_lot, 1)))
        if policy == "P0_FIXED_1":
            lots = 1
        elif policy == "P1_NAIVE_MONTHLY":
            if m > 0 and prev_month_pos:
                lots += 1
            lots = min(lots, max_by_margin, max_lots)
        elif policy == "P2_MARGIN_ONLY":
            lots = min(max_by_margin, max_lots)
        elif policy == "P3_MDD_BUFFER":
            allow = int(np.floor(BUFFER_FRAC * eq / max(worst_dd_per_lot, 1)))
            lots = min(allow, max_by_margin, max_lots)
        elif policy == "P4_CPPI_FLOOR":
            cushion = max(eq - floor, 0.0)
            allow = int(np.floor(CPPI_MULT * cushion / max(worst_dd_per_lot, 1)))
            lots = min(allow, max_by_margin, max_lots)
        lots = max(int(lots), 0)
        pnl = pts * LOT * lots
        eq += pnl
        peak = max(peak, eq)
        floor = max(floor, peak * FLOOR_RATCHET)
        prev_month_pos = pnl > 0
        lots_hist.append(lots)
        path.append(eq)
    p = np.array(path, float)
    run_peak = np.maximum.accumulate(p)
    mdd = float(((p - run_peak) / run_peak).min())
    nm_total = len(monthly_pts)
    tot_ret = float(p[-1] / CAP0 - 1)
    cagr = float((p[-1] / CAP0) ** (12.0 / max(nm_total, 1)) - 1) if p[-1] > 0 else -1.0
    calmar = float(cagr / abs(mdd)) if mdd < -1e-9 else float("nan")
    return dict(policy=policy, end_equity=float(p[-1]),
                total_return=tot_ret, maxDD=mdd, cagr=cagr, calmar=calmar,
                ruined=ruined_at is not None, ruin_month=ruined_at,
                median_lots=int(np.median(lots_hist)) if lots_hist else 0,
                max_lots=int(np.max(lots_hist)) if lots_hist else 0,
                months=len(lots_hist), breached_ceiling=bool(mdd < -MDD_CEILING))


def monthly_series(tr_, col):
    g = tr_.copy()
    g["m"] = pd.PeriodIndex(g.day, freq="M")
    agg = g.groupby("m").agg(pts=(col, "sum"), spot=("spot", "mean"))
    return agg.pts.to_numpy(float), agg.spot.to_numpy(float), agg.index


def worst_per_lot_dd(pts_series):
    eq = np.cumsum(pts_series) * LOT
    pk = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    return float(max((pk - eq).max(), 1.0))


POLICIES = ["P0_FIXED_1", "P1_NAIVE_MONTHLY", "P2_MARGIN_ONLY", "P3_MDD_BUFFER", "P4_CPPI_FLOOR"]
ARMS = [("SOLDIERS 1-session (in-spec: 13/mo)", REAL26),
        ("SOLDIERS 3-session (best pts/mo)", REAL78),
        ("RANDOM-LONG (BETA control)", BETA26)]
BASES = [("OLD", "pts_old"), ("NEW", "pts_new")]

# ------------------------------------------------------------------ HISTORICAL path, both bases
print("\n" + "=" * 132)
print("HISTORICAL PATH — single realised ordering, OLD vs NEW cost basis side by side")
print("=" * 132)
print(f"{'arm':<38}{'policy':<20}{'basis':<6}{'end equity':>14}{'total ret':>11}{'maxDD':>9}"
      f"{'calmar':>9}{'medLots':>9}{'ruined':>8}{'>25%DD':>8}", flush=True)
hist = []
for name, tr_ in ARMS:
    for basis, col in BASES:
        pts, spot, midx = monthly_series(tr_, col)
        wdd = worst_per_lot_dd(pts)
        for pol in POLICIES:
            r = run_policy(pts, spot, pol, wdd)
            r["arm"] = name
            r["basis"] = basis
            r["worst_dd_per_lot"] = round(wdd)
            hist.append(r)
            print(f"{name:<38}{pol:<20}{basis:<6}{r['end_equity']:>14,.0f}{r['total_return']:>10.1%}"
                  f"{r['maxDD']:>9.1%}{r['calmar']:>9.3f}{r['median_lots']:>9}"
                  f"{'YES' if r['ruined'] else '-':>8}{'YES' if r['breached_ceiling'] else '-':>8}",
                  flush=True)

H = pd.DataFrame(hist)
H.to_csv(OUT / "historical_paths_recost.csv", index=False)

# ------------------------------------------------------------------ SEQUENCING RISK, paired bootstrap
print("\n" + "=" * 132)
print(f"SEQUENCING RISK — stationary block bootstrap on MONTHS (block={BLOCK_MONTHS}, {N_BOOT} paths).")
print("  SAME draws replayed against OLD and NEW monthly point series per arm (paired, not resampled")
print("  twice) so the only thing that differs between OLD/NEW rows is the cost, not the resample.")
print("=" * 132)
print(f"{'arm':<38}{'policy':<20}{'basis':<6}{'med ret':>10}{'p5 ret':>10}"
      f"{'P(ruin)':>9}{'P(>25%DD)':>11}{'med maxDD':>11}{'medCalmar':>10}", flush=True)
boot = []
for name, tr_ in ARMS:
    series = {}
    nm = None
    for basis, col in BASES:
        pts, spot, midx = monthly_series(tr_, col)
        wdd = worst_per_lot_dd(pts)
        series[basis] = (pts, spot, wdd)
        nm = len(pts)
    if nm < 12:
        continue
    # pre-generate the paired block-bootstrap index draws ONCE per arm (shared across OLD/NEW/policy)
    idx_draws = []
    for _ in range(N_BOOT):
        idx = []
        while len(idx) < nm:
            s = int(RNG.integers(0, nm))
            idx.extend([(s + k) % nm for k in range(BLOCK_MONTHS)])
        idx_draws.append(np.array(idx[:nm]))

    for pol in POLICIES:
        for basis, col in BASES:
            pts, spot, wdd = series[basis]
            rets, dds, calmars, ruins, ceils = [], [], [], 0, 0
            for idx in idx_draws:
                r = run_policy(pts[idx], spot[idx], pol, wdd)
                rets.append(r["total_return"]); dds.append(r["maxDD"])
                if np.isfinite(r["calmar"]):
                    calmars.append(r["calmar"])
                ruins += int(r["ruined"]); ceils += int(r["breached_ceiling"])
            rets = np.array(rets); dds = np.array(dds); calmars = np.array(calmars)
            row = dict(arm=name, policy=pol, basis=basis, med_ret=float(np.median(rets)),
                       p5_ret=float(np.quantile(rets, .05)), p95_ret=float(np.quantile(rets, .95)),
                       p_ruin=ruins / N_BOOT, p_breach=ceils / N_BOOT,
                       med_maxDD=float(np.median(dds)),
                       med_calmar=float(np.median(calmars)) if len(calmars) else float("nan"))
            boot.append(row)
            print(f"{name:<38}{pol:<20}{basis:<6}{row['med_ret']:>9.1%}{row['p5_ret']:>10.1%}"
                  f"{row['p_ruin']:>9.1%}{row['p_breach']:>11.1%}{row['med_maxDD']:>11.1%}"
                  f"{row['med_calmar']:>10.3f}", flush=True)

B = pd.DataFrame(boot)
B.to_csv(OUT / "bootstrap_paths_recost.csv", index=False)

# ------------------------------------------------------------------ SUPPLEMENTARY: MAX_LOTS relaxed
# Capacity desk: 40 lots = 0.047% of NIFTY futures ADV -> the cap is NOT a liquidity constraint.
# What actually binds once it is removed? Same paired draws, NEW cost basis only, best arm/policies.
print("\n" + "=" * 132)
print("SUPPLEMENTARY — MAX_LOTS relaxed 40 -> 100,000 (capacity desk: 40 lots is 0.047% of ADV, not")
print("  a liquidity constraint). NEW cost basis only. Tests whether margin becomes the real cap.")
print("=" * 132)
print(f"{'arm':<38}{'policy':<20}{'med ret':>12}{'P(ruin)':>9}{'P(>25%DD)':>11}"
      f"{'med maxDD':>11}{'med maxLots':>13}", flush=True)
relax = []
for name, tr_ in ARMS:
    pts, spot, midx = monthly_series(tr_, "pts_new")
    wdd = worst_per_lot_dd(pts)
    nm = len(pts)
    if nm < 12:
        continue
    idx_draws = []
    for _ in range(N_BOOT):
        idx = []
        while len(idx) < nm:
            s = int(RNG.integers(0, nm))
            idx.extend([(s + k) % nm for k in range(BLOCK_MONTHS)])
        idx_draws.append(np.array(idx[:nm]))
    for pol in ["P1_NAIVE_MONTHLY", "P4_CPPI_FLOOR"]:
        rets, dds, ruins, ceils, mlots = [], [], 0, 0, []
        for idx in idx_draws:
            r = run_policy(pts[idx], spot[idx], pol, wdd, max_lots=MAX_LOTS_RELAXED)
            rets.append(r["total_return"]); dds.append(r["maxDD"])
            ruins += int(r["ruined"]); ceils += int(r["breached_ceiling"])
            mlots.append(r["max_lots"])
        rets = np.array(rets)
        row = dict(arm=name, policy=pol, med_ret=float(np.median(rets)),
                   p_ruin=ruins / N_BOOT, p_breach=ceils / N_BOOT,
                   med_maxDD=float(np.median(dds)), med_max_lots=int(np.median(mlots)))
        relax.append(row)
        print(f"{name:<38}{pol:<20}{row['med_ret']:>11.0%}{row['p_ruin']:>9.1%}"
              f"{row['p_breach']:>11.1%}{row['med_maxDD']:>11.1%}{row['med_max_lots']:>13}", flush=True)
RLX = pd.DataFrame(relax)
RLX.to_csv(OUT / "maxlots_relaxed_recost.csv", index=False)

# ------------------------------------------------------------------ save trades + meta
REAL26.to_csv(OUT / "trades_1session.csv", index=False)
REAL78.to_csv(OUT / "trades_3session.csv", index=False)
BETA26.to_csv(OUT / "trades_beta.csv", index=False)
json.dump(dict(capital=CAP0, lot=LOT, margin_pct=MARGIN_PCT, ruin_frac=RUIN_FRAC,
               mdd_ceiling=MDD_CEILING, buffer_frac=BUFFER_FRAC, floor_ratchet=FLOOR_RATCHET,
               cppi_mult=CPPI_MULT, n_boot=N_BOOT, block_months=BLOCK_MONTHS,
               max_lots=MAX_LOTS, max_lots_relaxed=MAX_LOTS_RELAXED,
               stt_fut_new=STT_FUT_NEW, non_stt_fut_pts=NON_STT_FUT_PTS, slip_fut_rt=SLIP_FUT_RT,
               policies=POLICIES,
               mean_pts_old=dict(hold26=float(REAL26.pts_old.mean()), hold78=float(REAL78.pts_old.mean()),
                                  beta=float(BETA26.pts_old.mean())),
               mean_pts_new=dict(hold26=float(REAL26.pts_new.mean()), hold78=float(REAL78.pts_new.mean()),
                                  beta=float(BETA26.pts_new.mean()))),
          open(OUT / "meta.json", "w"), indent=2)
print("\nwrote historical_paths_recost.csv, bootstrap_paths_recost.csv, maxlots_relaxed_recost.csv, "
      "trades_*.csv, meta.json", flush=True)
