"""PROTECTIVE_PUT_20260802 -- rolling long OTM PE + 1x2 put ratio spread, NIFTY index.
See PRE_REGISTRATION.md. Reuses nifty_optidx_all_traded.parquet (2016-2026, incl. real COVID data).
"""
import os
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


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading data ...")
tbl = pd.read_parquet(ALL_TRADED).set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(tbl.index.get_level_values(0).unique())
LAST_OK = trading_days.max()
log(f"tbl {len(tbl):,} rows | trading days {len(trading_days)} ({trading_days.min().date()}..{LAST_OK.date()})")


def spot_on_or_before(d):
    pos = trading_days.searchsorted(pd.Timestamp(d), side="right") - 1
    if pos < 0:
        return None
    return trading_days[pos], float(sv["spot_close"].iloc[pos])


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


def find_strike_series(expiry, target_strike, avail_from, tol_days=5, search_range=(0, 50, -50, 100, -100, 150, -150, 200, -200)):
    for off in search_range:
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


def build_prot_put_rung(entry_avail_from, otm_pct=0.05):
    exp = find_target_expiry(TARGET_DTE, entry_avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        return None
    ref = spot_on_or_before(entry_avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    target_K = round(ref_spot * (1 - otm_pct) / 50) * 50
    K, s, entry_date = find_strike_series(exp, target_K, entry_avail_from)
    if K is None:
        return None
    entry_px = float(s.loc[entry_date])

    roll_target = exp - pd.Timedelta(days=ROLL_OFFSET)
    if roll_target <= entry_date:
        return None
    roll_date = on_or_after(roll_target)
    if roll_date is None or roll_date > LAST_OK or roll_date <= entry_date:
        return None
    exit_px, _ = mark_at_or_before(s, roll_date)
    if exit_px is None:
        return None

    net_pnl_pts = (exit_px - entry_px) - COST_PER_LEG_RT
    return dict(entry_date=entry_date, roll_date=roll_date, expiry=exp, strike=K, spot_entry=ref_spot,
                entry_px=entry_px, exit_px=exit_px, net_debit=entry_px, net_pnl_pts=net_pnl_pts)


def build_ratio_rung(entry_avail_from, near_otm=0.03, far_otm=0.08):
    exp = find_target_expiry(TARGET_DTE, entry_avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        return None
    ref = spot_on_or_before(entry_avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    near_target = round(ref_spot * (1 - near_otm) / 50) * 50
    far_target = round(ref_spot * (1 - far_otm) / 50) * 50
    Kn, sn, d1 = find_strike_series(exp, near_target, entry_avail_from)
    if Kn is None:
        return None
    Kf, sf, d2 = find_strike_series(exp, far_target, entry_avail_from)
    if Kf is None or Kf >= Kn:
        return None
    entry_date = max(d1, d2)
    if (entry_date - entry_avail_from).days > 5:
        return None
    near_px, _ = mark_at_or_before(sn, entry_date, max_fwd_td=0) if entry_date != d1 else (float(sn.loc[d1]), d1)
    far_px, _ = mark_at_or_before(sf, entry_date, max_fwd_td=0) if entry_date != d2 else (float(sf.loc[d2]), d2)
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

    net_debit = near_px - 2 * far_px           # can be negative (net credit)
    gross_pnl = (near_x - near_px) + 2 * (far_px - far_x)   # long-near P&L + 2x short-far P&L
    net_pnl_pts = gross_pnl - 3 * COST_PER_LEG_RT  # 3 legs total (1 long + 2 short)

    # tail-breach check: did spot at roll_date fall THROUGH the far (short) strike? (uncapped-risk zone)
    spot_at_roll = spot_on_or_before(roll_date)
    breach = bool(spot_at_roll is not None and spot_at_roll[1] < Kf)

    return dict(entry_date=entry_date, roll_date=roll_date, expiry=exp, near_strike=Kn, far_strike=Kf,
                spot_entry=ref_spot, near_entry=near_px, far_entry=far_px, near_exit=near_x, far_exit=far_x,
                net_debit=net_debit, gross_pnl_pts=gross_pnl, net_pnl_pts=net_pnl_pts, tail_breach=breach)


def walk(builder_fn, max_cycles=250, **kwargs):
    rows = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        r = builder_fn(avail_from, **kwargs)
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


def crash_window_stats(df, col="net_pnl_pts", date_col="roll_date"):
    cw = df[(df[date_col] >= pd.Timestamp("2020-02-20")) & (df[date_col] <= pd.Timestamp("2020-04-10"))]
    return dict(n=len(cw), total=float(cw[col].sum()) if len(cw) else np.nan,
                worst=float(cw[col].min()) if len(cw) else np.nan)


def tstat(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    return np.nan if n < 2 else x.mean() / (x.std(ddof=1) / np.sqrt(n))


def main():
    log("=== PROT_PUT: buy 5% OTM PE, 30D target, roll T-5 ===")
    pp = walk(build_prot_put_rung, otm_pct=0.05)
    pp.to_csv(f"{OUT}/trades_PROT_PUT.csv", index=False)
    net = pp["net_pnl_pts"].values
    log(f"  n={len(pp)} net_mean={net.mean():+.2f} net_median={np.median(net):+.2f} "
        f"hit={ (net>0).mean():.1%} t={tstat(net):+.2f} mean_premium_paid={pp['net_debit'].mean():.2f}")
    cw = crash_window_stats(pp)
    log(f"  CRASH WINDOW (20Feb-10Apr 2020): n={cw['n']} total={cw['total']:+.1f} worst={cw['worst']:+.1f}")

    log("\n=== RATIO_1x2: buy 3% OTM PE + sell 2x 8% OTM PE, 30D target, roll T-5 ===")
    rt = walk(build_ratio_rung, near_otm=0.03, far_otm=0.08)
    rt.to_csv(f"{OUT}/trades_RATIO_1x2.csv", index=False)
    net_r = rt["net_pnl_pts"].values
    log(f"  n={len(rt)} net_mean={net_r.mean():+.2f} net_median={np.median(net_r):+.2f} "
        f"hit={(net_r>0).mean():.1%} t={tstat(net_r):+.2f} mean_net_debit={rt['net_debit'].mean():+.2f} "
        f"(negative=net credit) credit_rungs={int((rt['net_debit']<0).sum())}")
    cw_r = crash_window_stats(rt)
    log(f"  CRASH WINDOW (20Feb-10Apr 2020): n={cw_r['n']} total={cw_r['total']:+.1f} worst={cw_r['worst']:+.1f}")
    breaches = int(rt["tail_breach"].sum())
    log(f"  TAIL BREACH (spot fell through the short/far strike at roll date): {breaches}/{len(rt)} rungs")
    if breaches:
        bdf = rt[rt["tail_breach"]]
        log(f"    breach dates: {list(bdf['roll_date'].dt.date.astype(str))[:10]}"
            f"{'...' if len(bdf) > 10 else ''} | worst breached-rung pnl: {bdf['net_pnl_pts'].min():+.1f} pts")

    summary = pd.DataFrame([
        dict(label="PROT_PUT", n=len(pp), net_mean=net.mean(), t_stat=tstat(net),
             crash_n=cw["n"], crash_total=cw["total"], crash_worst=cw["worst"]),
        dict(label="RATIO_1x2", n=len(rt), net_mean=net_r.mean(), t_stat=tstat(net_r),
             crash_n=cw_r["n"], crash_total=cw_r["total"], crash_worst=cw_r["worst"],
             tail_breaches=breaches),
    ])
    summary.to_csv(f"{OUT}/summary.csv", index=False)
    log("\nDONE")


if __name__ == "__main__":
    main()
