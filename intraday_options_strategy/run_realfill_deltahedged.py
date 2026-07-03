"""REAL-FILL delta-hedged 0DTE backtest.

Uses HuggingFace india-index-options-1m data (actual 1-min option prices) +
real index prices. Simulates the exact strategy from run_today_live.py:
  - 09:20 SELL ATM CE+PE (real fill = market close price - 0.5% slip)
  - Rebalance delta every bar (band 0.25) using real IV implied from market
  - 15:15 BUY BACK straddle + flatten hedge (real fills + 0.5% slip)

No synthetic BS for pricing — options prices are real. Only BS is used to
compute real-time delta from implied vol (which we back out from real price).
"""
from __future__ import annotations
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import norm
import warnings; warnings.filterwarnings("ignore")

# ── paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent
B    = ROOT / "datasets" / "raw" / "hf_index_options_1m"
IDX  = "NIFTY"; STEP = 50; LOT = 75

# ── costs ────────────────────────────────────────────────────────────────────
OPT_SLIP    = 0.005     # 0.5% per option leg
FUT_SLIP    = 0.5       # Nifty futures points per hedge rebalance (one side)
HEDGE_BAND  = 0.25      # delta units, rebalance when |Δtarget - Δheld| > band
BROK        = 20 * 1.18 # per order (₹20 + 18% GST)
STT_SELL    = 0.000625  # 0.0625% on sell premium (options)
NSE_TXN     = 0.00053   # 0.053% (× GST) on both sides
SEBI        = 10 / 1e7  # ₹10/Cr turnover
TMIN_YEAR   = 252 * 375
r, q        = 0.065, 0.01

# ── BS helpers ───────────────────────────────────────────────────────────────
def _d1(S, K, T, sig):
    return (np.log(S / K) + (r - q + 0.5 * sig**2) * T) / (sig * np.sqrt(T))

def bs_delta(S, K, T, sig, is_call: bool) -> float:
    d1 = _d1(S, K, T, sig)
    return float(np.exp(-q * T) * (norm.cdf(d1) if is_call else norm.cdf(d1) - 1))

def bs_price_fn(S, K, T, sig, is_call: bool) -> float:
    d1 = _d1(S, K, T, sig)
    d2 = d1 - sig * np.sqrt(T)
    F  = S * np.exp((r - q) * T)
    df = np.exp(-r * T)
    return float(df * (F * norm.cdf(d1) - K * norm.cdf(d2)) if is_call
                 else df * (K * norm.cdf(-d2) - F * norm.cdf(-d1)))

def implied_vol(mkt: float, S, K, T, is_call: bool, tol=1e-5, maxiter=50) -> float:
    if mkt <= 0 or T <= 0:
        return np.nan
    lo, hi = 0.01, 10.0
    for _ in range(maxiter):
        mid = (lo + hi) / 2
        v   = bs_price_fn(S, K, T, mid, is_call)
        if abs(v - mkt) < tol:
            return mid
        (lo if v < mkt else hi).__class__  # type: ignore
        if v < mkt:
            lo = mid
        else:
            hi = mid
    return mid

# ── load index ───────────────────────────────────────────────────────────────
idx_raw = pd.read_parquet(B / "index" / f"{IDX}.parquet")
idx_raw["t"] = pd.to_datetime(idx_raw["timestamp"]).dt.tz_localize(None)
idx_raw = idx_raw.set_index("t")["close"].sort_index()
idx_raw = idx_raw[~idx_raw.index.duplicated(keep="last")]

# ── gather expiry files ───────────────────────────────────────────────────────
opt_dir = B / "options" / IDX
files   = sorted([f for f in opt_dir.glob("*.parquet") if f.stat().st_size > 100_000])
print(f"{IDX}: {len(files)} expiry files (>=100KB) to process\n")

rows = []
for fi, f in enumerate(files):
    exp = f.stem
    exp_ts = pd.Timestamp(exp)

    # load only this expiry day's data
    d = pd.read_parquet(f).drop_duplicates(["timestamp", "strike", "option_type"])
    d["t"] = pd.to_datetime(d["timestamp"]).dt.tz_localize(None)
    d = d[d["trading_day"].astype(str) == exp].copy()
    if d.empty:
        continue

    t_entry  = exp_ts + pd.Timedelta("09:20:00")
    t_exit   = exp_ts + pd.Timedelta("15:15:00")
    exp_close = exp_ts + pd.Timedelta("15:30:00")

    # ATM from first available index price ≥ 09:20
    idx_day  = idx_raw[exp_ts.date().isoformat()]
    if len(idx_day) == 0:
        continue
    t_avail  = idx_day.index[idx_day.index >= t_entry]
    if len(t_avail) == 0:
        continue
    spot0    = float(idx_day[t_avail[0]])
    atm      = round(spot0 / STEP) * STEP

    # entry prices
    def price_at(typ, ts):
        sub = d[(d["strike"] == atm) & (d["option_type"] == typ)].set_index("t")["close"]
        if sub.empty: return None
        near = sub.reindex([ts], method="nearest", tolerance=pd.Timedelta("5min"))
        v = near.iloc[0]
        return float(v) if not np.isnan(v) else None

    ce0 = price_at("CE", t_entry)
    pe0 = price_at("PE", t_entry)
    if ce0 is None or pe0 is None:
        continue
    strd0 = ce0 + pe0

    # intraday walk
    # common timestamps between CE, PE, and index (09:20 .. 15:15)
    ce_bars = (d[(d["strike"] == atm) & (d["option_type"] == "CE")]
               .set_index("t")["close"].sort_index())
    pe_bars = (d[(d["strike"] == atm) & (d["option_type"] == "PE")]
               .set_index("t")["close"].sort_index())
    ce_bars = ce_bars[~ce_bars.index.duplicated(keep="last")]
    pe_bars = pe_bars[~pe_bars.index.duplicated(keep="last")]

    # resample to 1-min grid covering session
    tgrid = pd.date_range(t_entry, t_exit, freq="1min")
    idx_s = idx_day.reindex(tgrid, method="nearest", tolerance=pd.Timedelta("2min")).ffill()
    ce_s  = ce_bars.reindex(tgrid, method="nearest", tolerance=pd.Timedelta("5min")).ffill()
    pe_s  = pe_bars.reindex(tgrid, method="nearest", tolerance=pd.Timedelta("5min")).ffill()

    # walk
    hedge     = 0.0
    hedge_pnl = 0.0
    hedge_cost = 0.0
    n_reb     = 0
    prev_s    = spot0
    last_iv   = 0.15  # fallback IV

    for t in tgrid:
        if pd.isna(idx_s[t]):
            continue
        s     = float(idx_s[t])
        hedge_pnl += hedge * (s - prev_s)
        prev_s = s

        ce_p = ce_s.get(t, np.nan)
        pe_p = pe_s.get(t, np.nan)
        if np.isnan(ce_p) or np.isnan(pe_p) or ce_p <= 0 or pe_p <= 0:
            continue

        T_yr = max((exp_close - t).total_seconds() / 60, 1.0) / TMIN_YEAR
        # back out IV from market price
        iv_c = implied_vol(ce_p, s, atm, T_yr, True)
        iv_p = implied_vol(pe_p, s, atm, T_yr, False)
        iv   = np.nanmean([v for v in [iv_c, iv_p] if 0.01 < v < 5.0])
        if np.isnan(iv):
            iv = last_iv
        else:
            last_iv = iv

        dC = bs_delta(s, atm, T_yr, iv, True)
        dP = bs_delta(s, atm, T_yr, iv, False)
        target = dC + dP   # net delta of short straddle (per straddle unit)

        if abs(target - hedge) > HEDGE_BAND:
            hedge_cost += abs(target - hedge) * FUT_SLIP
            n_reb += 1
            hedge = target

    # exit: flatten hedge
    if abs(hedge) > 1e-9:
        hedge_cost += abs(hedge) * FUT_SLIP
        n_reb += 1
        hedge = 0.0

    # exit option prices
    ce_x = price_at("CE", t_exit)
    pe_x = price_at("PE", t_exit)
    if ce_x is None or pe_x is None:
        continue
    strdX = ce_x + pe_x

    entry_fill = strd0 * (1 - OPT_SLIP)
    exit_fill  = strdX * (1 + OPT_SLIP)

    straddle_pnl_lot = (entry_fill - exit_fill) * LOT
    hedge_pnl_lot    = hedge_pnl * LOT

    # costs
    units = LOT  # per-lot basis
    sell_t = entry_fill * units; buy_t = exit_fill * units
    opt_cost = (STT_SELL * sell_t
                + NSE_TXN * (sell_t + buy_t) * 1.18
                + SEBI * (sell_t + buy_t))
    fixed    = BROK * (4 + n_reb)
    hcost    = hedge_cost * units

    net_lot = straddle_pnl_lot + hedge_pnl_lot - opt_cost - fixed - hcost

    spot_x = float(idx_day.reindex([t_exit], method="nearest").iloc[0])
    rows.append({
        "expiry"     : exp,
        "spot"       : round(spot0),
        "atm"        : atm,
        "move_pct"   : spot_x / spot0 - 1,
        "strd_in"    : round(strd0, 1),
        "strd_out"   : round(strdX, 1),
        "strpnl_lot" : round(straddle_pnl_lot),
        "hedgpnl_lot": round(hedge_pnl_lot),
        "costs_lot"  : round(opt_cost + fixed + hcost),
        "net_lot"    : round(net_lot),
        "n_reb"      : n_reb,
    })
    if (fi + 1) % 25 == 0:
        print(f"  {fi+1}/{len(files)}  last={exp}  net_lot={net_lot:+,.0f}  rebal={n_reb}")

print()
res = pd.DataFrame(rows)
res["expiry"] = pd.to_datetime(res["expiry"])
res = res.sort_values("expiry").reset_index(drop=True)
print(res[["expiry","spot","move_pct","strd_in","strd_out","strpnl_lot","hedgpnl_lot","net_lot","n_reb"]].to_string(index=False))

# ── summary stats ─────────────────────────────────────────────────────────────
CAP0 = 1e7
cap  = CAP0; caps = []; lots_arr = []
for _, row in res.iterrows():
    strd = row["strd_in"]
    maxloss_lot = 0.25 * strd * LOT
    lots = max(1, int(0.006 * cap / max(maxloss_lot, 1)))
    cap += row["net_lot"] / LOT * lots * LOT
    caps.append(cap); lots_arr.append(lots)

res["cap"]     = caps
res["lots"]    = lots_arr
res["pnl_cap"] = res["net_lot"] / LOT * res["lots"] * LOT

equity = pd.Series(caps, index=res["expiry"])
wr     = (res["net_lot"] > 0).mean()
yrs    = (res["expiry"].iloc[-1] - res["expiry"].iloc[0]).days / 365.25
cagr   = (caps[-1] / CAP0) ** (1 / yrs) - 1
mdd    = float(((equity.cummax() - equity) / equity.cummax()).max())
ret    = res["pnl_cap"] / CAP0
ann_r  = ret.mean() * 52
ann_v  = ret.std() * np.sqrt(52)
sharpe = (ann_r - 0.065) / ann_v if ann_v > 0 else 0

print(f"\n{'='*65}")
print(f"REAL-FILL DELTA-HEDGED NIFTY 0DTE — {len(res)} expiries, {yrs:.1f} yrs")
print(f"{'='*65}")
print(f"Rs.1Cr -> Rs.{caps[-1]/1e7:.2f}Cr   CAGR {cagr:+.1%}")
print(f"Sharpe {sharpe:.2f}   MaxDD {mdd:.1%}   WR {wr:.0%}")
print(f"Ann return {ann_r:.1%}   Ann vol {ann_v:.1%}")
print(f"Avg net/lot  win: Rs.{res.loc[res['net_lot']>0,'net_lot'].mean():,.0f}"
      f"  loss: Rs.{res.loc[res['net_lot']<0,'net_lot'].mean():,.0f}")
print()
print("Year-by-year:")
res["year"] = res["expiry"].dt.year
for yr, g in res.groupby("year"):
    yr_wr  = (g["net_lot"] > 0).mean()
    yr_avg = g["net_lot"].mean()
    yr_tot = g["pnl_cap"].sum()
    print(f"  {yr}: {len(g):2d} exp  WR {yr_wr:.0%}  avg/lot Rs.{yr_avg:+,.0f}  "
          f"total cap Rs.{yr_tot:+,.0f}")

# save
out_path = ROOT / "results" / "realfill_deltahedged_nifty.csv"
out_path.parent.mkdir(exist_ok=True)
res.to_csv(out_path, index=False)
print(f"\nSaved -> {out_path}")
