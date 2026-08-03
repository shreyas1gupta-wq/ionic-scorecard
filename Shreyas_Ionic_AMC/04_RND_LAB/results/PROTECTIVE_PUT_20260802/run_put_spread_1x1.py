"""PROTECTIVE_PUT_20260802 -- CORRECTION: Principal meant a 1:1 ratio (buy 1 near-OTM PE, sell 1
far-OTM PE, same expiry) -- a standard DEFINED-RISK put debit spread, NOT the 1x2 ratio tested in
run_protective_put.py (which had uncapped risk beyond the short strike). This is a materially
different, capped-both-ways structure: max loss = net debit, max gain = (near_strike - far_strike)
- net debit, achieved once spot falls to/through the far strike (no longer an "uncapped tail" zone
-- deltas roughly cancel there since both legs are the same size).
Same NIFTY index data, same 3%/8% OTM targets, same 30D/T-5 roll cadence as the original ratio test
for direct comparability.
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
TARGET_DTE = 30
ROLL_OFFSET = 5
NEAR_OTM, FAR_OTM = 0.03, 0.08


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading data ...")
tbl = pd.read_parquet(ALL_TRADED).set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(tbl.index.get_level_values(0).unique())
LAST_OK = trading_days.max()


def spot_on_or_before(d):
    pos = trading_days.searchsorted(pd.Timestamp(d), side="right") - 1
    return None if pos < 0 else (trading_days[pos], float(sv["spot_close"].iloc[pos]))


def on_or_after(d):
    pos = trading_days.searchsorted(pd.Timestamp(d))
    return trading_days[pos] if pos < len(trading_days) else None


def find_target_expiry(target_dte, avail_from, expiry_list, min_dte=3, band_mult=3):
    best, bestdiff = None, 1e9
    for e in expiry_list:
        d = (e - avail_from).days
        if d < min_dte:
            continue
        if d > target_dte * band_mult + 45:
            break
        diff = abs(d - target_dte)
        if diff < bestdiff:
            bestdiff, best = diff, e
    return best


def pe_close_series(expiry, K):
    try:
        return tbl.loc[(expiry, K, "PE")]["CLOSE"]
    except KeyError:
        return None


def mark_at_or_before(series, target_date, max_fwd_td=3):
    idx = series.index
    pos = idx.searchsorted(pd.Timestamp(target_date))
    if pos < len(idx) and idx[pos] == pd.Timestamp(target_date):
        return float(series.iloc[pos]), idx[pos]
    for k in range(1, max_fwd_td + 1):
        p2 = pos + k - 1
        if p2 < len(idx):
            cand = idx[p2]
            if (cand - pd.Timestamp(target_date)).days <= 7:
                return float(series.iloc[p2]), cand
    return None, None


def find_strike_series(expiry, target_strike, avail_from, tol_days=5):
    for off in (0, 50, -50, 100, -100, 150, -150, 200, -200):
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


def build_spread_rung(entry_avail_from):
    exp = find_target_expiry(TARGET_DTE, entry_avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        return None
    ref = spot_on_or_before(entry_avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    near_target = round(ref_spot * (1 - NEAR_OTM) / 50) * 50
    far_target = round(ref_spot * (1 - FAR_OTM) / 50) * 50
    Kn, sn, d1 = find_strike_series(exp, near_target, entry_avail_from)
    if Kn is None:
        return None
    Kf, sf, d2 = find_strike_series(exp, far_target, entry_avail_from)
    if Kf is None or Kf >= Kn:
        return None
    entry_date = max(d1, d2)
    if (entry_date - entry_avail_from).days > 5:
        return None
    near_px = float(sn.loc[d1]) if d1 == entry_date else mark_at_or_before(sn, entry_date, 0)[0]
    far_px = float(sf.loc[d2]) if d2 == entry_date else mark_at_or_before(sf, entry_date, 0)[0]
    if near_px is None or far_px is None:
        return None

    roll_target = exp - pd.Timedelta(days=ROLL_OFFSET)
    if roll_target <= entry_date:
        return None
    roll_date = on_or_after(roll_target)
    if roll_date is None or roll_date > LAST_OK or roll_date <= entry_date:
        return None
    near_x, _ = mark_at_or_before(sn, roll_date)
    far_x, _ = mark_at_or_before(sf, roll_date)
    if near_x is None or far_x is None:
        return None

    net_debit = near_px - far_px    # BUY near (pay), SELL far (receive) -- 1x1, standard bear-put debit spread
    max_gain_theoretical = (Kn - Kf) - net_debit
    gross_pnl = (near_x - near_px) + (far_px - far_x)   # long-near P&L (1x) + short-far P&L (1x)
    net_pnl_pts = gross_pnl - 2 * COST_PER_LEG_RT        # 2 legs only

    spot_res = spot_on_or_before(roll_date)
    in_max_gain_zone = bool(spot_res is not None and spot_res[1] <= Kf)

    return dict(entry_date=entry_date, roll_date=roll_date, expiry=exp, near_strike=Kn, far_strike=Kf,
                spot_entry=ref_spot, near_entry=near_px, far_entry=far_px, near_exit=near_x, far_exit=far_x,
                net_debit=net_debit, max_gain_theoretical=max_gain_theoretical,
                gross_pnl_pts=gross_pnl, net_pnl_pts=net_pnl_pts, in_max_gain_zone=in_max_gain_zone)


def walk(max_cycles=250):
    rows = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        r = build_spread_rung(avail_from)
        if r is None:
            nxt = on_or_after(avail_from + pd.Timedelta(days=7))
            if nxt is None or nxt > LAST_OK or nxt <= avail_from:
                break
            avail_from = nxt
            continue
        rows.append(r)
        nxt = on_or_after(r["roll_date"])
        if nxt is None or nxt > LAST_OK or nxt <= avail_from:
            break
        avail_from = nxt
    return pd.DataFrame(rows)


def tstat(x):
    x = np.asarray(x, dtype=float)
    return np.nan if len(x) < 2 else x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def crash_window_stats(df):
    cw = df[(df["roll_date"] >= pd.Timestamp("2020-02-20")) & (df["roll_date"] <= pd.Timestamp("2020-04-10"))]
    return dict(n=len(cw), total=float(cw["net_pnl_pts"].sum()) if len(cw) else np.nan,
                worst=float(cw["net_pnl_pts"].min()) if len(cw) else np.nan)


def main():
    log(f"=== SPREAD_1x1: buy {NEAR_OTM:.0%} OTM PE + sell {FAR_OTM:.0%} OTM PE (1x1, defined-risk), "
        f"30D target, roll T-5 ===")
    df = walk()
    df.to_csv(f"{OUT}/trades_SPREAD_1x1.csv", index=False)
    net = df["net_pnl_pts"].values
    log(f"  n={len(df)} net_mean={net.mean():+.2f} net_median={np.median(net):+.2f} "
        f"hit={(net>0).mean():.1%} t={tstat(net):+.2f}")
    log(f"  mean net_debit={df['net_debit'].mean():+.2f} pts | mean max_gain_theoretical={df['max_gain_theoretical'].mean():+.2f} pts")
    log(f"  rungs in max-gain zone (spot<=far strike at roll): {int(df['in_max_gain_zone'].sum())}/{len(df)}")
    cw = crash_window_stats(df)
    log(f"  CRASH WINDOW (20Feb-10Apr 2020): n={cw['n']} total={cw['total']:+.1f} worst={cw['worst']:+.1f}")
    log(f"  worst single rung: {net.min():+.1f} pts | best single rung: {net.max():+.1f} pts "
        f"(sanity: worst should be >= -net_debit-costs, best should be <= max_gain_theoretical-ish)")


if __name__ == "__main__":
    main()
