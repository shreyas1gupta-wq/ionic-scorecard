"""Tara Singh (E-015) — realistic-cost re-run of swing_momentum's V2 (survivorship-safe)
backtest, per BROAD_RESEARCH_2036/MSQ_BASE_ASSESSMENT.md follow-on task.

Reuses run_swing.py's EXACT selection engine (trend-template, RS rank, regime gate, 15%
weekly trailing stop) verbatim (read-only legacy file, not modified) and replaces ONLY the
flat 30bps cost line with the firm's APPROVED COST_STANDARDS.md tiered/dynamic model:
  - slippage floors by liquidity tier (large 10 / mid 20 / small 35 / micro 50 bps, one-way)
  - volume-conditional multiplier (1x/2x/3x/NO-FILL) via lib/execution_realism.py
  - circuit-lock = NO FILL (entry deferred / exit deferred to next rebalance)
  - ADV cap measurement (10%/5% of 20d ADV) at an assumed AUM = strategy's own Rs 10cr ceiling

Liquidity/OHLCV coverage: raw/nifty500/*.csv (239 files, 238 symbols overlap the 976-symbol
close panel) is the ONLY source in this repo with per-name OHLCV going back far enough to
cover most of 2005-2025. Names outside this 238-set get a CONSERVATIVE DEFAULT (small-cap
35bps tier, 1x multiplier, no lock-check possible) — flagged, not measured. This is a real,
disclosed data gap, not a silent assumption.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
from execution_realism import circuit_locked, slippage_multiplier  # noqa: E402

P = ROOT / "swing_momentum" / "processed"
COST_BPS_ORIG = 30
TOP_N = 20
STOP = 0.15
RF = 0.06
AUM = 10_00_00_000.0  # Rs 10cr — the strategy's own stated capacity ceiling (PLAN.md)

TIER_BPS = {"large": 10.0, "mid": 20.0, "small": 35.0, "micro": 50.0}
# statutory per-order charges (equity DELIVERY, not intraday — this is a days/weeks swing
# strategy) from COST_STANDARDS.md's charges table, independent of the slippage floors and
# NOT covered by them — the original flat 30bps claimed to already bundle "brokerage+STT+
# slippage" but at 30bps ROUND-TRIP that is arithmetically impossible once STT delivery alone
# (0.1% BOTH sides = 20bps RT) is counted; catching this is the point of this re-run.
STT_BPS = 10.0           # 0.1% delivery, one-way (both buy and sell legs, per COST_STANDARDS)
STAMP_BUY_BPS = 1.5      # 0.015% delivery buy only
EXCH_SEBI_GST_BPS = 0.5  # ~0.00297% exchange + Rs10/cr SEBI + 18% GST thereon + Rs20 flat brokerage
                          # (all sub-bp at this position size; bundled as a small constant)
STAT_BUY_BPS = STT_BPS + STAMP_BUY_BPS + EXCH_SEBI_GST_BPS     # ~12.0 bps one-way buy
STAT_SELL_BPS = STT_BPS + EXCH_SEBI_GST_BPS                     # ~10.5 bps one-way sell
# liquidity-tier cutoffs on 20d avg TRADED VALUE (Rs), proxy for market-cap tier since we
# lack a full-universe market-cap series 2005-2025 — [INFERENCE], documented in report.
TIER_CUTS = [(25_00_00_000, "large"), (5_00_00_000, "mid"), (50_00_000, "small")]


def tier_of(adv_value: float) -> str:
    if pd.isna(adv_value):
        return "small"  # conservative default
    for cut, name in TIER_CUTS:
        if adv_value >= cut:
            return name
    return "micro"


# ---------- 1. reproduce run_swing.py's signal engine verbatim ----------
close_long = pd.read_parquet(P / "eq_close.parquet")
mem = pd.read_parquet(P / "membership.parquet")
close = close_long.pivot_table(index="date", columns="symbol", values="close").sort_index()
close = close[~close.index.duplicated()]
close = close.ffill(limit=10)
print(f"panel {close.shape}", flush=True)

DELIST_LOSS = -0.50
try:
    dl = pd.read_excel(ROOT / "Nifty500_Delisted_2005_2025.xlsx", sheet_name="Sheet1")
    dl = dl.rename(columns={dl.columns[0]: "date"})
    dl["date"] = pd.to_datetime(dl["date"], errors="coerce")
    dl = dl.dropna(subset=["date"]).set_index("date")
    delist_date = {}
    for s in dl.columns:
        col = pd.to_numeric(dl[s], errors="coerce").dropna()
        if len(col):
            delist_date[str(s).upper()] = col.index.max()
except Exception as e:
    delist_date = {}
    print(f"delist load failed ({str(e)[:80]})")

mem["month"] = pd.to_datetime(mem["month"])
mwide = (mem.assign(v=True).pivot_table(index="month", columns="symbol", values="v",
         aggfunc="any").reindex(columns=close.columns))
memmask = mwide.reindex(close.index, method="ffill").fillna(False).astype(bool)

sma50 = close.rolling(50, min_periods=40).mean()
sma150 = close.rolling(150, min_periods=120).mean()
sma200 = close.rolling(200, min_periods=150).mean()
hi52 = close.rolling(252, min_periods=180).max()
lo52 = close.rolling(252, min_periods=180).min()
ret6 = close / close.shift(126) - 1
ret12 = close / close.shift(252) - 1
rising200 = sma200 > sma200.shift(21)

trend_ok = ((close > sma150) & (sma150 > sma200) & rising200 & (close > sma50)
            & (sma50 > sma150) & (close >= 1.25 * lo52) & (close >= 0.75 * hi52))
elig = trend_ok & memmask & ret12.notna() & (close >= 20)

rs = (0.6 * ret12 + 0.4 * ret6)
rs_elig = rs.where(elig)
rs_rank = rs_elig.rank(axis=1, pct=True)

nif = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/nifty50_daily.csv",
                  parse_dates=["Date"]).set_index("Date")["Close"].sort_index()
nif = nif[~nif.index.duplicated()].reindex(close.index).ffill()
nif_sma200 = nif.rolling(200, min_periods=200).mean()
nif_sma50 = nif.rolling(50, min_periods=50).mean()
breadth = (close > sma200).where(memmask).mean(axis=1)
regime_green = (nif > nif_sma200) & (nif > nif_sma50) & (breadth > 0.40)
regime_green = regime_green.fillna(False)

rebal = close.index[::5]
fwd = close.shift(-5) / close - 1

# ---------- 2. load OHLCV coverage (raw/nifty500) for realistic cost overlay ----------
import glob, os
raw_files = glob.glob(str(ROOT / "raw" / "nifty500" / "*.csv"))
ohlcv = {}
for f in raw_files:
    sym = os.path.splitext(os.path.basename(f))[0].upper()
    try:
        d = pd.read_csv(f, parse_dates=["Date"]).set_index("Date").sort_index()
        d = d[~d.index.duplicated()]
        d["prevclose"] = d["Close"].shift(1)
        d["tval"] = d["Close"] * d["Volume"]
        d["adv20"] = d["tval"].rolling(20, min_periods=10).mean().shift(1)   # PIT: excl. today
        d["vol_med20"] = d["Volume"].rolling(20, min_periods=10).median().shift(1)
        ohlcv[sym] = d
    except Exception:
        pass
print(f"OHLCV coverage: {len(ohlcv)} symbols loaded from raw/nifty500", flush=True)
covered = set(ohlcv.keys()) & set(close.columns)
print(f"overlap with close panel: {len(covered)} symbols", flush=True)


def event_cost_bps(sym: str, t, side: str) -> tuple[float, str, bool]:
    """One-way effective cost bps (slippage tier x volume-multiplier + statutory STT/stamp/
    exchange/GST) for a buy ('entry') or sell ('exit') event on stock `sym` at date `t`.
    Returns (bps, tag, covered). bps = inf means NO FILL (circuit lock or zero/absent volume)."""
    stat = STAT_BUY_BPS if side == "entry" else STAT_SELL_BPS
    d = ohlcv.get(sym)
    if d is None or t not in d.index:
        return TIER_BPS["small"] + stat, "uncovered_default_small", False
    row = d.loc[t]
    o, h, l, c, pc, vol, med20, adv20 = (row["Open"], row["High"], row["Low"], row["Close"],
                                         row["prevclose"], row["Volume"], row["vol_med20"],
                                         row["adv20"])
    if pd.isna(pc):
        return TIER_BPS["small"] + stat, "uncovered_default_small", False
    if circuit_locked(o, h, l, c, pc, vol):
        return float("inf"), "circuit_locked", True
    mult = slippage_multiplier(vol, med20)
    if not np.isfinite(mult):
        return float("inf"), "no_volume", True
    tier = tier_of(adv20)
    return TIER_BPS[tier] * mult + stat, f"{tier}_{mult:.0f}x", True


def adv_breach(sym: str, t) -> bool | None:
    d = ohlcv.get(sym)
    if d is None or t not in d.index:
        return None
    adv20 = d.loc[t, "adv20"]
    if pd.isna(adv20) or adv20 <= 0:
        return None
    tier = tier_of(adv20)
    cap_frac = 0.05 if tier == "micro" else 0.10
    pos_notional = AUM / TOP_N
    return pos_notional > cap_frac * adv20


# ---------- 3. re-run with realistic cost + circuit no-fill ----------
def run(use_regime: bool, realistic: bool):
    eq = [1.0]; dates = [close.index[0]]; held = {}; held_peak = {}
    turn_hist = []
    n_entry_evt = n_exit_evt = 0
    n_entry_nofill = n_exit_nofill = 0
    n_circuit = n_novol = 0
    n_adv_checked = n_adv_breach = 0
    n_evt_covered = 0

    for t in rebal:
        if t not in rs_rank.index:
            continue
        green = bool(regime_green.get(t, False)) if use_regime else True
        if green:
            row = rs_rank.loc[t].dropna()
            picks = list(row.sort_values(ascending=False).head(TOP_N).index)
        else:
            picks = []

        newheld = {}
        for s in picks:
            newheld[s] = held.get(s, close.at[t, s] if s in close.columns else np.nan)
        keep = {}
        stop_drop = []
        for s, entry in newheld.items():
            px = close.at[t, s] if s in close.columns else np.nan
            pk = max(held_peak.get(s, entry), px)
            if px >= pk * (1 - STOP):
                keep[s] = entry; held_peak[s] = pk
            else:
                stop_drop.append(s)

        prev_held = set(held.keys())
        proposed_cur = set(keep.keys())          # top-N & still above stop
        added = proposed_cur - prev_held
        removed = prev_held - proposed_cur        # dropped: stop-out OR fell out of rank

        events = {}  # sym -> ('entry'|'exit', bps or inf, tag)
        final_added = set(added)
        final_removed = set(removed)

        if realistic:
            for s in added:
                n_entry_evt += 1
                bps, tag, cov = event_cost_bps(s, t, "entry")
                n_evt_covered += int(cov)
                if not np.isfinite(bps):
                    n_entry_nofill += 1
                    if tag == "circuit_locked":
                        n_circuit += 1
                    elif tag == "no_volume":
                        n_novol += 1
                    final_added.discard(s)   # NO FILL: deferred, not entered this week
                    continue
                events[s] = ("entry", bps, tag)
                br = adv_breach(s, t)
                if br is not None:
                    n_adv_checked += 1
                    n_adv_breach += int(br)
            for s in removed:
                n_exit_evt += 1
                bps, tag, cov = event_cost_bps(s, t, "exit")
                n_evt_covered += int(cov)
                if not np.isfinite(bps):
                    n_exit_nofill += 1
                    if tag == "circuit_locked":
                        n_circuit += 1
                    elif tag == "no_volume":
                        n_novol += 1
                    final_removed.discard(s)  # NO FILL: exit deferred -> keep held
                    continue
                events[s] = ("exit", bps, tag)
        else:
            final_added, final_removed = added, removed

        # rebuild final keep set: deferred exits stay held (with prior peak/entry);
        # deferred entries are simply not added this week.
        final_keep = {}
        for s in keep:
            if s in final_removed:
                continue
            final_keep[s] = keep[s]
        for s in (prev_held - proposed_cur):
            if s not in final_removed:  # exit deferred -> revert to still-held
                final_keep[s] = held[s]
                held_peak[s] = held_peak.get(s, held[s])
        # (added names already in `keep` if not dropped as no-fill; nothing extra to add
        #  since `keep` built from `picks`, and non-fillable adds are excluded via final_removed
        #  logic only for `removed` — for `added`, exclude directly:)
        for s in added:
            if s not in final_added and s in final_keep:
                del final_keep[s]

        picks_final = list(final_keep.keys())
        if picks_final:
            rr = fwd.loc[t, picks_final].replace([np.inf, -np.inf], np.nan)
            vals = []
            for s in picks_final:
                v = rr.get(s, np.nan)
                if np.isnan(v):
                    dd = delist_date.get(s)
                    if dd is not None and t <= dd <= t + pd.Timedelta(days=12):
                        v = DELIST_LOSS
                    else:
                        continue
                vals.append(v)
            port = float(np.mean(vals)) if vals else 0.0
        else:
            port = 0.0

        if realistic:
            cost_bps_sum = sum(b for (_, b, _) in events.values())
            cost = (cost_bps_sum / 1e4) / TOP_N
            turn = len(final_added) + len(final_removed)
        else:
            turn = len(prev_held.symmetric_difference(proposed_cur))
            cost = (turn / TOP_N) * (COST_BPS_ORIG / 1e4)
        turn_hist.append(turn / TOP_N)

        eq.append(eq[-1] * (1 + port - cost))
        dates.append(t)
        held = dict(final_keep)

    e = pd.Series(eq[1:], index=pd.DatetimeIndex(dates[1:]))
    stats_extra = dict(n_entry_evt=n_entry_evt, n_exit_evt=n_exit_evt,
                        n_entry_nofill=n_entry_nofill, n_exit_nofill=n_exit_nofill,
                        n_circuit=n_circuit, n_novol=n_novol,
                        n_adv_checked=n_adv_checked, n_adv_breach=n_adv_breach,
                        n_evt_covered=n_evt_covered)
    return e, np.mean(turn_hist), stats_extra


def stats(e, label):
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(52)
    sharpe = (r.mean() * 52 - RF) / vol if vol > 0 else 0
    peak = e.cummax(); mdd = ((peak - e) / peak).max()
    calmar = cagr / mdd if mdd > 0 else 0
    print(f"{label:26} CAGR {cagr:+7.1%}  vol {vol:5.1%}  Sharpe {sharpe:5.2f}  "
          f"MaxDD {mdd:5.1%}  Calmar {calmar:4.2f}")
    return dict(cagr=cagr, mdd=mdd, sharpe=sharpe, calmar=calmar)


print("\n=== ORIGINAL (flat 30bps, as published) ===")
eg0, tg0, _ = run(use_regime=True, realistic=False)
n_is0 = int(len(eg0) * 0.70)
stats(eg0, "REGIME-GATED (full)")
stats(eg0.iloc[:n_is0] / eg0.iloc[0], "  IS")
stats(eg0.iloc[n_is0:] / eg0.iloc[n_is0], "  OOS")

print("\n=== REALISTIC (tiered slippage + circuit/no-fill + volume multiplier) ===")
eg1, tg1, s1 = run(use_regime=True, realistic=True)
n_is1 = int(len(eg1) * 0.70)
stats(eg1, "REGIME-GATED (full)")
stats(eg1.iloc[:n_is1] / eg1.iloc[0], "  IS")
stats(eg1.iloc[n_is1:] / eg1.iloc[n_is1], "  OOS")
ea1, ta1, s1a = run(use_regime=False, realistic=True)
stats(ea1, "ALWAYS-ON (no regime)")

print("\n=== 2x-stress on realistic costs (promotion gate check) ===")
# crude 2x: double every realized event's effective bps by re-running with tier table x2
TIER_BPS = {k: v * 2 for k, v in TIER_BPS.items()}
eg2, tg2, s2 = run(use_regime=True, realistic=True)
n_is2 = int(len(eg2) * 0.70)
stats(eg2, "REGIME-GATED (full) 2x")
stats(eg2.iloc[n_is2:] / eg2.iloc[n_is2], "  OOS 2x")

print("\n=== Circuit-lock / no-fill materiality (measured on covered subset) ===")
tot_evt = s1["n_entry_evt"] + s1["n_exit_evt"]
tot_nofill = s1["n_entry_nofill"] + s1["n_exit_nofill"]
tot_cov = s1["n_evt_covered"]
print(f"total entry+exit events: {tot_evt}  (OHLCV-checkable: {tot_cov}, "
      f"{tot_cov/tot_evt:.1%} of all events)")
print(f"  of ALL events, NO-FILL (circuit or zero-vol): {tot_nofill} ({tot_nofill/tot_evt:.1%})")
if tot_cov:
    print(f"  of CHECKABLE (covered) events only, NO-FILL rate: {tot_nofill/tot_cov:.1%}")
print(f"  circuit-locked: {s1['n_circuit']}  zero/absent-volume: {s1['n_novol']}")
print(f"ADV-cap check: {s1['n_adv_checked']} events checked, "
      f"{s1['n_adv_breach']} breach (Rs10cr AUM assumption)")

print(f"\ncoverage: {len(covered)}/{close.shape[1]} panel symbols have OHLCV "
      f"({len(covered)/close.shape[1]:.1%})")
