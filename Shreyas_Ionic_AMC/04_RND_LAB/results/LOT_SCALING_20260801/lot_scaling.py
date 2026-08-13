"""MDD-AWARE LOT SCALING — does the Principal's compounding plan survive its own sequencing risk?

THE PLAN AS STATED (2026-08-01):
  "there will be strategies with 10-30 point avg mean profit and 10-30 trade per month totaling
   300-1000 point and 300*65=20000+ in which we can buy 1-2 more lot and next month scale the
   strategy and next month win 40000+. scaling in a mdd aware and buffer way to avoid wipeouts."

REALITY CHECK FIRST (measured, CANDLE_MTF_20260730/nonoverlap_cells.csv):
  8 cells DO meet "10-30 pts avg AND 10-30 trades/month". ZERO reach 300 pts/month.
  Best in-spec cell: THREE_SOLDIERS|none|BE_1R_trail 1-session hold - 13.0 trades/mo, +18.52 pts,
  RR 1.45, t_NW 7.10 => 241 pts/month, i.e. Rs15,650/month on one lot, not Rs20,000+.
  Best overall: same signal at 3-session hold - 5.5 trades/mo, +45.52 pts => 250 pts/month.
  So the arithmetic is close at the bottom of his range and the top of it does not exist in our book.

THE THING THAT ACTUALLY DECIDES THIS PLAN, AND IT IS NOT THE MEAN:
  Monthly lot-adding is a POSITIVE-FEEDBACK sizing rule. You add size after good months, so you are
  MAXIMALLY SIZED entering the bad one. The mean per-trade edge is unchanged by sizing; what sizing
  changes is the ORDER-DEPENDENCE of the outcome. A strategy with a perfectly good expectancy can
  still wipe out under aggressive scaling purely because of sequence.
  So the deliverable here is not "what does it compound to" (that is arithmetic). It is:
    (a) the DISTRIBUTION of outcomes over resampled orderings, not the single historical path,
    (b) P(hit the 25% MDD ceiling) and P(ruin) per policy,
    (c) how much of the scaled result is just LEVERAGED BETA rather than edge.

  (c) matters enormously here and is why this script carries a benchmark arm. CANDLE_MTF measured an
  unconditional random LONG with the same wide stop/trail/hold earning +29.25 pts (exp_R 0.432) on a
  sample where NIFTY went +186%. 7 of 8 formations were that trail in costume; only THREE_SOLDIERS
  added incrementally (+18.7 pts over matched-random, p=0.000). Scaling a 60%-beta strategy is
  scaling leveraged index exposure - and beta does not diversify, so a bear market hits every lot at
  once. The random-long arm below is therefore not a curiosity, it is the control that says how much
  of any compounding result the Principal should actually attribute to the signal.

SIZING POLICIES COMPARED (all on the SAME trade sequence, so differences are pure sizing):
  P0 FIXED_1          one lot forever. The honest baseline.
  P1 NAIVE_MONTHLY    +1 lot after any profitable month. The plan at its most optimistic.
  P2 MARGIN_ONLY      lots = floor(equity / margin_per_lot). Grow as fast as margin allows.
  P3 MDD_BUFFER       lots = floor(BUFFER_FRAC * equity / (historical_maxDD_per_lot)). The
                      Principal's "mdd aware and buffer way", implemented literally: never hold more
                      lots than a repeat of the worst observed drawdown could absorb.
  P4 CPPI_FLOOR       lots sized off (equity - floor), floor ratcheting up at FLOOR_RATCHET of peak.
                      This is the policy that ALREADY worked on the portfolio (MaxDD -24.71% ->
                      -14.4%, Calmar 1.23 -> 1.70).
  All policies: lots capped at MAX_LOTS, and a hard RUIN floor - if equity < RUIN_FRAC of start,
  trading STOPS and the path is marked RUINED. That guard exists because an earlier sizing run
  without it produced maxDD -266%/-409% and CAGR 8.2e10% by letting equity go negative.

HONESTY NOTES
  - Margin per lot is computed from the CONTEMPORANEOUS index level, not a fixed number: 10% of
    notional per the Principal's ruling, notional = spot x 65. Using today's spot for 2015 trades
    would understate early leverage badly.
  - Costs are already inside the per-trade P&L from the source run (era-correct 4.47/5.97 + 0.5).
  - Sequencing is tested by STATIONARY BLOCK BOOTSTRAP on MONTHS (not trades), because the plan
    re-sizes monthly and within-month trade order matters far less than the month-to-month sequence.
    Block resampling preserves autocorrelation and volatility clustering; iid trade shuffling would
    flatter every policy by destroying exactly the clustering that causes wipeouts.
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
from pathsafe import ExitResult, simulate_exit      # noqa: E402

OUT = Path(__file__).parent
OUT.mkdir(parents=True, exist_ok=True)
IDX = BASE + r"\intraday_options_strategy\datasets\processed\nifty_1min.parquet"
RNG = np.random.default_rng(20260801)

LOT = 65
CAP0 = 1_000_000.0          # Rs10 lakh starting capital
MARGIN_PCT = 0.10           # Principal ruling: 10% of notional unhedged
RUIN_FRAC = 0.50            # equity below 50% of start => stop, mark RUINED
MAX_LOTS = 40
MDD_CEILING = 0.25          # the firm's standing drawdown ceiling
BUFFER_FRAC = 0.60          # P3: allow a repeat of worst-DD to consume at most 60% of equity
FLOOR_RATCHET = 0.80        # P4: CPPI floor at 80% of running peak
CPPI_MULT = 3.0
N_BOOT = 2000
BLOCK_MONTHS = 3
BREAK = pd.Timestamp("2024-10-01")
SCH = {"2024-06-04", "2024-06-03", "2024-02-01", "2023-02-01", "2022-02-01",
       "2025-02-01", "2026-02-01", "2024-07-23"}

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
    """ONE POSITION AT A TIME, stop=trail=max(prior-candle range, 0.4 ATR). Long only."""
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
        ct = (4.47 if pd.Timestamp(days[i]) < BREAK else 5.97) + 0.5
        rows.append(dict(t=TS[i], day=pd.Timestamp(days[i]), spot=entry, stop=stop,
                         pts=r.pnl_pessimistic - ct))
        blocked = i + min(hold_bars, len(seg))
    d = pd.DataFrame(rows)
    d["label"] = label
    print(f"[trades] {label:<22} n={len(d):>5}  mean {d.pts.mean():+7.2f}  "
          f"/mo {len(d) / max(len(pd.PeriodIndex(d.day, freq='M').unique()), 1):5.1f}", flush=True)
    return d


REAL26 = build_trades(SOLDIERS, 26, "SOLDIERS hold26")
REAL78 = build_trades(SOLDIERS, 78, "SOLDIERS hold78")

# the BETA CONTROL: random long entries, same count, same machinery.
rand_mask = np.zeros(N, bool)
elig = np.arange(30, N - 80)
rand_mask[RNG.choice(elig, size=int(np.nan_to_num(SOLDIERS).sum()), replace=False)] = True
BETA26 = build_trades(rand_mask, 26, "RANDOM-LONG hold26")

# ------------------------------------------------------------------ the sizing engine
def run_policy(monthly_pts, monthly_spot, policy, worst_dd_per_lot):
    """Walk months, sizing lots by policy. Returns the equity path and diagnostics.

    monthly_pts  : list of per-month TOTAL points on ONE lot
    monthly_spot : list of per-month mean spot (for contemporaneous margin)
    """
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
            lots = min(lots, max_by_margin, MAX_LOTS)
        elif policy == "P2_MARGIN_ONLY":
            lots = min(max_by_margin, MAX_LOTS)
        elif policy == "P3_MDD_BUFFER":
            # never hold more lots than a REPEAT of the worst observed per-lot DD can absorb
            allow = int(np.floor(BUFFER_FRAC * eq / max(worst_dd_per_lot, 1)))
            lots = min(allow, max_by_margin, MAX_LOTS)
        elif policy == "P4_CPPI_FLOOR":
            cushion = max(eq - floor, 0.0)
            allow = int(np.floor(CPPI_MULT * cushion / max(worst_dd_per_lot, 1)))
            lots = min(allow, max_by_margin, MAX_LOTS)
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
    return dict(policy=policy, end_equity=float(p[-1]),
                total_return=float(p[-1] / CAP0 - 1), maxDD=mdd,
                ruined=ruined_at is not None, ruin_month=ruined_at,
                median_lots=int(np.median(lots_hist)) if lots_hist else 0,
                max_lots=int(np.max(lots_hist)) if lots_hist else 0,
                months=len(lots_hist), breached_ceiling=bool(mdd < -MDD_CEILING))


def monthly_series(tr_):
    g = tr_.copy()
    g["m"] = pd.PeriodIndex(g.day, freq="M")
    agg = g.groupby("m").agg(pts=("pts", "sum"), spot=("spot", "mean"))
    return agg.pts.to_numpy(float), agg.spot.to_numpy(float), agg.index


def worst_per_lot_dd(pts_series):
    """Worst peak-to-trough of the 1-lot RUPEE curve, in rupees. The buffer's input."""
    eq = np.cumsum(pts_series) * LOT
    pk = np.maximum.accumulate(np.r_[0.0, eq])[1:]
    return float(max((pk - eq).max(), 1.0))


POLICIES = ["P0_FIXED_1", "P1_NAIVE_MONTHLY", "P2_MARGIN_ONLY", "P3_MDD_BUFFER", "P4_CPPI_FLOOR"]
ARMS = [("SOLDIERS hold26 (in-spec: 13/mo)", REAL26),
        ("SOLDIERS hold78 (best pts/mo)", REAL78),
        ("RANDOM-LONG hold26 (BETA control)", BETA26)]

print("\n" + "=" * 122)
print("HISTORICAL PATH — the single realised ordering (this is what a naive backtest would show)")
print("=" * 122)
print(f"{'arm':<36}{'policy':<20}{'end equity':>14}{'total ret':>11}{'maxDD':>9}"
      f"{'medLots':>9}{'maxLots':>9}{'ruined':>8}{'>25%DD':>8}", flush=True)
hist = []
for name, tr_ in ARMS:
    pts, spot, midx = monthly_series(tr_)
    wdd = worst_per_lot_dd(pts)
    for pol in POLICIES:
        r = run_policy(pts, spot, pol, wdd)
        r["arm"] = name
        r["worst_dd_per_lot"] = round(wdd)
        hist.append(r)
        print(f"{name:<36}{pol:<20}{r['end_equity']:>14,.0f}{r['total_return']:>10.1%}"
              f"{r['maxDD']:>9.1%}{r['median_lots']:>9}{r['max_lots']:>9}"
              f"{'YES' if r['ruined'] else '-':>8}{'YES' if r['breached_ceiling'] else '-':>8}",
              flush=True)

H = pd.DataFrame(hist)
H.to_csv(OUT / "historical_paths.csv", index=False)

# ------------------------------------------------------------------ sequencing risk
print("\n" + "=" * 122)
print(f"SEQUENCING RISK — stationary block bootstrap on MONTHS (block={BLOCK_MONTHS}, "
      f"{N_BOOT} paths). Same months, different order.")
print("  This is the number that decides the plan. The historical path above is ONE draw.")
print("=" * 122)
print(f"{'arm':<36}{'policy':<20}{'med ret':>10}{'p5 ret':>10}{'p95 ret':>10}"
      f"{'P(ruin)':>9}{'P(>25%DD)':>11}{'med maxDD':>11}", flush=True)
boot = []
for name, tr_ in ARMS:
    pts, spot, midx = monthly_series(tr_)
    wdd = worst_per_lot_dd(pts)
    nm = len(pts)
    if nm < 12:
        continue
    for pol in POLICIES:
        rets, dds, ruins, ceils = [], [], 0, 0
        for _ in range(N_BOOT):
            idx = []
            while len(idx) < nm:
                s = int(RNG.integers(0, nm))
                idx.extend([(s + k) % nm for k in range(BLOCK_MONTHS)])
            idx = np.array(idx[:nm])
            r = run_policy(pts[idx], spot[idx], pol, wdd)
            rets.append(r["total_return"]); dds.append(r["maxDD"])
            ruins += int(r["ruined"]); ceils += int(r["breached_ceiling"])
        rets = np.array(rets); dds = np.array(dds)
        row = dict(arm=name, policy=pol, med_ret=float(np.median(rets)),
                   p5_ret=float(np.quantile(rets, .05)), p95_ret=float(np.quantile(rets, .95)),
                   p_ruin=ruins / N_BOOT, p_breach=ceils / N_BOOT,
                   med_maxDD=float(np.median(dds)))
        boot.append(row)
        print(f"{name:<36}{pol:<20}{row['med_ret']:>9.1%}{row['p5_ret']:>10.1%}"
              f"{row['p95_ret']:>10.1%}{row['p_ruin']:>9.1%}{row['p_breach']:>11.1%}"
              f"{row['med_maxDD']:>11.1%}", flush=True)

B = pd.DataFrame(boot)
B.to_csv(OUT / "bootstrap_paths.csv", index=False)
json.dump(dict(capital=CAP0, lot=LOT, margin_pct=MARGIN_PCT, ruin_frac=RUIN_FRAC,
               mdd_ceiling=MDD_CEILING, buffer_frac=BUFFER_FRAC, floor_ratchet=FLOOR_RATCHET,
               cppi_mult=CPPI_MULT, n_boot=N_BOOT, block_months=BLOCK_MONTHS,
               policies=POLICIES), open(OUT / "meta.json", "w"), indent=2)
print("\nwrote historical_paths.csv, bootstrap_paths.csv, meta.json", flush=True)
print("\nHOW TO READ: compare each policy's P(ruin) and P(>25%DD) against P0_FIXED_1, and compare the\n"
      "REAL arms against the RANDOM-LONG BETA CONTROL. If a policy's compounding looks similar on the\n"
      "beta control, the compounding is coming from leveraged index exposure, not from the signal.",
      flush=True)
