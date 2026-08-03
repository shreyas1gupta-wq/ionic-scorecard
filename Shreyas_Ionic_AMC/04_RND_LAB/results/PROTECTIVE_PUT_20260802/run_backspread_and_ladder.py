"""PROTECTIVE_PUT_20260802 -- two more variants on the credit-spread family (sell 2.5% OTM as the
financing leg), 30D target, roll T-5, same as run_credit_spread_1x1.py's cadence:
  BACKSPREAD_1x2_10pct: SELL 1x 2.5% OTM PE + BUY 2x 10% OTM PE -- now net LONG 1 put beyond the
    10% strike (uncapped gain on a real crash, unlike the 1:1 credit spread's capped max loss zone
    which was actually a capped max GAIN zone from the short side's perspective... here the extra
    long put flips that zone to open-ended profit).
  LADDER_75_125: SELL 1x 2.5% OTM PE + BUY 1x 7.5% OTM PE + BUY 1x 12.5% OTM PE -- protection spread
    across two strikes instead of doubled up at one; still only 1x short so likely a net DEBIT
    (2 long legs vs 1 short) unless the 12.5% leg is very cheap.
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
NEAR_OTM = 0.025


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
        dd = (e - avail_from).days
        if dd < min_dte:
            continue
        if dd > target_dte * band_mult + 45:
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


def get_leg(expiry, otm_pct, ref_spot, avail_from):
    target_K = round(ref_spot * (1 - otm_pct) / 50) * 50
    K, s, d = find_strike_series(expiry, target_K, avail_from)
    return K, s, d


def build_backspread_rung(entry_avail_from):
    exp = find_target_expiry(TARGET_DTE, entry_avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        return None
    ref = spot_on_or_before(entry_avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    Kn, sn, d1 = get_leg(exp, NEAR_OTM, ref_spot, entry_avail_from)
    Kf, sf, d2 = get_leg(exp, 0.10, ref_spot, entry_avail_from)
    if Kn is None or Kf is None or Kf >= Kn:
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

    net_debit = near_px - 2 * far_px    # SELL 1x near (receive), BUY 2x far (pay) -- negative = net credit
    gross_pnl = (near_px - near_x) + 2 * (far_x - far_px)
    net_pnl_pts = gross_pnl - 3 * COST_PER_LEG_RT   # 3 legs: 1 short + 2 long

    spot_res = spot_on_or_before(roll_date)
    below_far = bool(spot_res is not None and spot_res[1] < Kf)

    return dict(entry_date=entry_date, roll_date=roll_date, expiry=exp, near_strike=Kn, far_strike=Kf,
                spot_entry=ref_spot, near_entry=near_px, far_entry=far_px, near_exit=near_x, far_exit=far_x,
                net_debit=net_debit, gross_pnl_pts=gross_pnl, net_pnl_pts=net_pnl_pts, below_far_strike=below_far)


def build_ladder_rung(entry_avail_from):
    exp = find_target_expiry(TARGET_DTE, entry_avail_from, all_exp)
    if exp is None or exp > LAST_OK:
        return None
    ref = spot_on_or_before(entry_avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    Kn, sn, d1 = get_leg(exp, NEAR_OTM, ref_spot, entry_avail_from)
    Kf1, sf1, d2 = get_leg(exp, 0.075, ref_spot, entry_avail_from)
    Kf2, sf2, d3 = get_leg(exp, 0.125, ref_spot, entry_avail_from)
    if Kn is None or Kf1 is None or Kf2 is None or not (Kf2 < Kf1 < Kn):
        return None
    entry_date = max(d1, d2, d3)
    if (entry_date - entry_avail_from).days > 5:
        return None
    near_px = float(sn.loc[d1]) if d1 == entry_date else mark_at_or_before(sn, entry_date, 0)[0]
    far1_px = float(sf1.loc[d2]) if d2 == entry_date else mark_at_or_before(sf1, entry_date, 0)[0]
    far2_px = float(sf2.loc[d3]) if d3 == entry_date else mark_at_or_before(sf2, entry_date, 0)[0]
    if near_px is None or far1_px is None or far2_px is None:
        return None

    roll_target = exp - pd.Timedelta(days=ROLL_OFFSET)
    if roll_target <= entry_date:
        return None
    roll_date = on_or_after(roll_target)
    if roll_date is None or roll_date > LAST_OK or roll_date <= entry_date:
        return None
    near_x, _ = mark_at_or_before(sn, roll_date)
    far1_x, _ = mark_at_or_before(sf1, roll_date)
    far2_x, _ = mark_at_or_before(sf2, roll_date)
    if near_x is None or far1_x is None or far2_x is None:
        return None

    net_debit = near_px - far1_px - far2_px   # SELL 1x near (receive), BUY 1x + 1x far (pay both)
    gross_pnl = (near_px - near_x) + (far1_x - far1_px) + (far2_x - far2_px)
    net_pnl_pts = gross_pnl - 3 * COST_PER_LEG_RT

    spot_res = spot_on_or_before(roll_date)
    below_far2 = bool(spot_res is not None and spot_res[1] < Kf2)

    return dict(entry_date=entry_date, roll_date=roll_date, expiry=exp, near_strike=Kn,
                far1_strike=Kf1, far2_strike=Kf2, spot_entry=ref_spot,
                near_entry=near_px, far1_entry=far1_px, far2_entry=far2_px,
                near_exit=near_x, far1_exit=far1_x, far2_exit=far2_x,
                net_debit=net_debit, gross_pnl_pts=gross_pnl, net_pnl_pts=net_pnl_pts,
                below_far2_strike=below_far2)


def walk(builder_fn, max_cycles=250):
    rows = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        r = builder_fn(avail_from)
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
    log("=== BACKSPREAD_1x2_10pct: SELL 1x 2.5% OTM PE + BUY 2x 10% OTM PE ===")
    df = walk(build_backspread_rung)
    df.to_csv(f"{OUT}/trades_BACKSPREAD_1x2_10pct.csv", index=False)
    net = df["net_pnl_pts"].values
    log(f"  n={len(df)} net_mean={net.mean():+.2f} net_median={np.median(net):+.2f} "
        f"hit={(net>0).mean():.1%} t={tstat(net):+.2f} mean_net_debit={df['net_debit'].mean():+.2f} "
        f"(negative=net credit) credit_rungs={int((df['net_debit']<0).sum())}")
    log(f"  rungs where spot < far(10%) strike at roll: {int(df['below_far_strike'].sum())}/{len(df)}")
    cw = crash_window_stats(df)
    log(f"  CRASH WINDOW: n={cw['n']} total={cw['total']:+.1f} worst={cw['worst']:+.1f}")
    log(f"  worst single rung: {net.min():+.1f} | best single rung: {net.max():+.1f}")

    log("\n=== LADDER_75_125: SELL 1x 2.5% OTM PE + BUY 1x 7.5% OTM PE + BUY 1x 12.5% OTM PE ===")
    df2 = walk(build_ladder_rung)
    df2.to_csv(f"{OUT}/trades_LADDER_75_125.csv", index=False)
    net2 = df2["net_pnl_pts"].values
    log(f"  n={len(df2)} net_mean={net2.mean():+.2f} net_median={np.median(net2):+.2f} "
        f"hit={(net2>0).mean():.1%} t={tstat(net2):+.2f} mean_net_debit={df2['net_debit'].mean():+.2f} "
        f"(negative=net credit) credit_rungs={int((df2['net_debit']<0).sum())}")
    log(f"  rungs where spot < far2(12.5%) strike at roll: {int(df2['below_far2_strike'].sum())}/{len(df2)}")
    cw2 = crash_window_stats(df2)
    log(f"  CRASH WINDOW: n={cw2['n']} total={cw2['total']:+.1f} worst={cw2['worst']:+.1f}")
    log(f"  worst single rung: {net2.min():+.1f} | best single rung: {net2.max():+.1f}")


if __name__ == "__main__":
    main()
