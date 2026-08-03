"""PROTECTIVE_PUT_20260802 -- 1-year (365D target), 10% OTM NIFTY PE, deep tail-hedge layer.
Two variants per Principal ask:
  1Y_ROLL6M: roll (close at CLOSE, open fresh 365D put) when ~182 calendar days remain -- i.e. held
             ~183 days (6 months) before refreshing back out to a full year.
  1Y_NOROLL: hold each put to its OWN expiry, cash-settled at INTRINSIC from real underlying spot
             close (never expiry-day option SETTLE_PR -- landmine #9), then immediately open a
             fresh 365D put (still a repeating ladder, just held-to-expiry rather than rolled early).
Liquidity caveat: NIFTY options this far out (12mo) trade far less than the 15-90D range tested
elsewhere this session -- expect a much smaller n and wider strike-search tolerance than the 30D
structures; reported honestly, not smoothed over.
"""
import time
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
ALL_TRADED = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache\nifty_optidx_all_traded.parquet"
SV = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache\spot_vix_daily.parquet"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PROTECTIVE_PUT_20260802"

COST_PER_LEG_RT = 1.77
LOT = 75
TARGET_DTE = 365
OTM_PCT = 0.10
TOL_DAYS = 15   # widened vs the 5-day tolerance used at 30-90D -- far-dated strikes trade less often


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading data ...")
tbl = pd.read_parquet(ALL_TRADED).set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(tbl.index.get_level_values(0).unique())
LAST_OK = trading_days.max()
log(f"tbl {len(tbl):,} rows | trading days {len(trading_days)} ({trading_days.min().date()}..{LAST_OK.date()}) "
    f"| expiries {len(all_exp)} (max DTE from earliest day: {(all_exp[-1]-trading_days[0]).days}d)")


def spot_on_or_before(d):
    pos = trading_days.searchsorted(pd.Timestamp(d), side="right") - 1
    return None if pos < 0 else (trading_days[pos], float(sv["spot_close"].iloc[pos]))


def on_or_after(d):
    pos = trading_days.searchsorted(pd.Timestamp(d))
    return trading_days[pos] if pos < len(trading_days) else None


def find_target_expiry(target_dte, avail_from, expiry_list, min_dte=30, band_mult=2):
    best, bestdiff = None, 1e9
    for e in expiry_list:
        dd = (e - avail_from).days
        if dd < min_dte:
            continue
        if dd > target_dte * band_mult:
            break
        diff = abs(dd - target_dte)
        if diff < bestdiff:
            bestdiff, best = diff, e
    return best


def pe_close_series(expiry, K):
    try:
        return tbl.loc[(expiry, K, "PE")]["CLOSE"]
    except KeyError:
        return None


def mark_at_or_before(series, target_date, max_fwd_td=5):
    idx = series.index
    pos = idx.searchsorted(pd.Timestamp(target_date))
    if pos < len(idx) and idx[pos] == pd.Timestamp(target_date):
        return float(series.iloc[pos]), idx[pos]
    for k in range(1, max_fwd_td + 1):
        p2 = pos + k - 1
        if p2 < len(idx):
            cand = idx[p2]
            if (cand - pd.Timestamp(target_date)).days <= 10:
                return float(series.iloc[p2]), cand
    return None, None


def find_strike_series(expiry, target_strike, avail_from, tol_days=TOL_DAYS):
    for off in (0, 50, -50, 100, -100, 150, -150, 200, -200, 250, -250, 300, -300):
        K = target_strike + off
        s = pe_close_series(expiry, K)
        if s is None:
            continue
        avail = s.index[s.index >= pd.Timestamp(avail_from)]
        if len(avail) == 0:
            continue
        d = avail.min()
        if (d - pd.Timestamp(avail_from)).days > tol_days:
            continue
        return K, s, d
    return None, None, None


def build_rung(entry_avail_from, hold_to_expiry):
    exp = find_target_expiry(TARGET_DTE, entry_avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        return None
    ref = spot_on_or_before(entry_avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    target_K = round(ref_spot * (1 - OTM_PCT) / 50) * 50
    K, s, entry_date = find_strike_series(exp, target_K, entry_avail_from)
    if K is None:
        return None
    entry_px = float(s.loc[entry_date])

    if hold_to_expiry:
        if exp > LAST_OK:
            return None
        exit_date = exp
        spot_res = spot_on_or_before(exp)
        if spot_res is None:
            return None
        _, spot_exp = spot_res
        exit_px = max(K - spot_exp, 0.0)     # cash-settle at INTRINSIC, real underlying close -- landmine #9
        settled_intrinsic = True
    else:
        roll_target = exp - pd.Timedelta(days=182)
        if roll_target <= entry_date:
            return None
        exit_date = on_or_after(roll_target)
        if exit_date is None or exit_date > LAST_OK or exit_date <= entry_date:
            return None
        px, _ = mark_at_or_before(s, exit_date)
        if px is None:
            return None
        exit_px, settled_intrinsic = px, False

    net_pnl_pts = (exit_px - entry_px) - COST_PER_LEG_RT
    return dict(entry_date=entry_date, exit_date=exit_date, expiry=exp, strike=K, spot_entry=ref_spot,
                entry_px=entry_px, exit_px=exit_px, settled_intrinsic=settled_intrinsic,
                net_pnl_pts=net_pnl_pts, net_debit=entry_px)


def walk(hold_to_expiry, max_cycles=40):
    rows = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        r = build_rung(avail_from, hold_to_expiry)
        if r is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=30))
            if nxt is None or nxt > LAST_OK or nxt <= avail_from:
                break
            avail_from = nxt
            continue
        rows.append(r)
        nxt = on_or_after(r["exit_date"])
        if nxt is None or nxt > LAST_OK or nxt <= avail_from:
            break
        avail_from = nxt
    return pd.DataFrame(rows)


def tstat(x):
    x = np.asarray(x, dtype=float)
    return np.nan if len(x) < 2 else x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def crash_window_stats(df, date_col):
    cw = df[(df[date_col] >= pd.Timestamp("2020-02-20")) & (df[date_col] <= pd.Timestamp("2020-04-10"))]
    return dict(n=len(cw), total=float(cw["net_pnl_pts"].sum()) if len(cw) else np.nan)


def main():
    for label, hold in [("1Y_ROLL6M", False), ("1Y_NOROLL", True)]:
        log(f"\n=== {label}: buy {OTM_PCT:.0%} OTM PE, {TARGET_DTE}D target "
            f"({'hold to own expiry, intrinsic settle' if hold else 'roll at 182D remaining'}) ===")
        df = walk(hold)
        if len(df) == 0:
            log("  0 rungs -- no liquid 365D strikes found at this tolerance, skipping")
            continue
        df.to_csv(f"{OUT}/trades_{label}.csv", index=False)
        net = df["net_pnl_pts"].values
        date_col = "exit_date"
        log(f"  n={len(df)} net_mean={net.mean():+.2f} net_median={np.median(net):+.2f} "
            f"hit={(net>0).mean():.1%} t={tstat(net):+.2f} mean_premium_paid={df['net_debit'].mean():.2f}")
        log(f"  entry dates: {list(df['entry_date'].dt.date.astype(str))}")
        log(f"  per-rung net pnl (pts): {[round(x,1) for x in net]}")
        cw = crash_window_stats(df, date_col)
        log(f"  CRASH WINDOW (20Feb-10Apr 2020) resolved BY {date_col}: n={cw['n']} total={cw['total']:+.1f}")


if __name__ == "__main__":
    main()
