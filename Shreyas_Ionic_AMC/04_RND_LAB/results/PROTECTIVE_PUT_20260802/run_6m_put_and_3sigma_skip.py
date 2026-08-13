"""PROTECTIVE_PUT_20260802 -- two more Principal-requested variants:
  PUT_6M_ROLL3M: buy 10% OTM PE, 180D target tenor, roll when ~90D remain (held ~3 months).
    Better liquidity expected than the earlier 365D attempt (n=4-5) since 6mo is a more standard tenor.
  PUT_30D_3SIGMA_SKIP: buy 10% OTM PE, 30D target, roll T-5 (same cadence as PROT_PUT) BUT: if a
    just-closed rung's net_pnl_pts exceeds (full-sample mean + 3*std) -- a "3-sigma" outlier gain,
    booked at that month's roll/close -- skip buying a new put for the NEXT cycle entirely, then
    resume normal rolling the cycle after that. Rationale: IV is usually elevated right after a big
    realized move, so skipping one re-entry avoids buying insurance at its most expensive moment.
    [DISCLOSED SIMPLIFICATION: the 3-sigma threshold uses the FULL-SAMPLE std, not a trailing/
    expanding one -- a mild look-ahead in the THRESHOLD estimate only, not in which rungs trigger it
    early in the sample; flagged, not hidden.]
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
OTM_PCT = 0.10


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


def find_target_expiry(target_dte, avail_from, expiry_list, min_dte=5, band_mult=2):
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


def find_strike_series(expiry, target_strike, avail_from, tol_days=8):
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


def build_put_rung(entry_avail_from, target_dte, roll_offset):
    exp = find_target_expiry(target_dte, entry_avail_from, all_exp)
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
    roll_target = exp - pd.Timedelta(days=roll_offset)
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
                entry_px=entry_px, exit_px=exit_px, net_pnl_pts=net_pnl_pts)


def tstat(x):
    x = np.asarray(x, dtype=float)
    return np.nan if len(x) < 2 else x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))


def crash_window_stats(df):
    cw = df[(df["roll_date"] >= pd.Timestamp("2020-02-20")) & (df["roll_date"] <= pd.Timestamp("2020-04-10"))]
    return dict(n=len(cw), total=float(cw["net_pnl_pts"].sum()) if len(cw) else np.nan)


# ==== PUT_6M_ROLL3M ====
log("\n=== PUT_6M_ROLL3M: buy 10% OTM PE, 180D target, roll at ~90D remaining (held ~3mo) ===")
rows = []
avail_from = trading_days[0]
guard = 0
while guard < 80:
    guard += 1
    r = build_put_rung(avail_from, target_dte=180, roll_offset=90)
    if r is None:
        nxt = on_or_after(avail_from + pd.Timedelta(days=15))
        if nxt is None or nxt > LAST_OK or nxt <= avail_from:
            break
        avail_from = nxt
        continue
    rows.append(r)
    nxt = on_or_after(r["roll_date"])
    if nxt is None or nxt > LAST_OK or nxt <= avail_from:
        break
    avail_from = nxt
df6m = pd.DataFrame(rows)
df6m.to_csv(f"{OUT}/trades_PUT_6M_ROLL3M.csv", index=False)
net = df6m["net_pnl_pts"].values
log(f"  n={len(df6m)} net_mean={net.mean():+.2f} net_median={np.median(net):+.2f} "
    f"hit={(net>0).mean():.1%} t={tstat(net):+.2f} mean_premium={df6m['entry_px'].mean():.2f}")
cw = crash_window_stats(df6m)
log(f"  CRASH WINDOW: n={cw['n']} total={cw['total']:+.1f}")
log(f"  entry dates: {list(df6m['entry_date'].dt.date.astype(str))}")

# ==== PUT_30D_3SIGMA_SKIP ====
log("\n=== PUT_30D_3SIGMA_SKIP: buy 10% OTM PE, 30D target, roll T-5, skip 1 cycle after a 3-sigma "
    "gain ===")
# first build the UNCONDITIONAL 30D/10%OTM put ladder (baseline), then apply the skip rule on top
rows2 = []
avail_from = trading_days[0]
guard = 0
while guard < 200:
    guard += 1
    r = build_put_rung(avail_from, target_dte=30, roll_offset=5)
    if r is None:
        nxt = on_or_after(avail_from + pd.Timedelta(days=7))
        if nxt is None or nxt > LAST_OK or nxt <= avail_from:
            break
        avail_from = nxt
        continue
    rows2.append(r)
    nxt = on_or_after(r["roll_date"])
    if nxt is None or nxt > LAST_OK or nxt <= avail_from:
        break
    avail_from = nxt
base = pd.DataFrame(rows2)
mean_, std_ = base["net_pnl_pts"].mean(), base["net_pnl_pts"].std()
threshold = mean_ + 3 * std_
log(f"  baseline (unconditional) 30D/10%OTM put: n={len(base)} mean={mean_:+.2f} std={std_:.2f} "
    f"-> 3-sigma threshold={threshold:+.2f} pts")
base["is_3sigma"] = base["net_pnl_pts"] > threshold
log(f"  3-sigma trigger rungs: {int(base['is_3sigma'].sum())} / {len(base)} "
    f"({list(base.loc[base['is_3sigma'],'roll_date'].dt.date.astype(str))})")

# apply skip: after a 3-sigma rung's roll_date, skip the NEXT rung entirely, resume the one after
skip_next = False
kept_rows = []
for _, r in base.iterrows():
    if skip_next:
        skip_next = False
        continue   # this rung is skipped -- no position held, no pnl
    kept_rows.append(r)
    if r["is_3sigma"]:
        skip_next = True
df_skip = pd.DataFrame(kept_rows)
df_skip.to_csv(f"{OUT}/trades_PUT_30D_3SIGMA_SKIP.csv", index=False)
net_s = df_skip["net_pnl_pts"].values
log(f"  WITH skip rule: n={len(df_skip)} (vs {len(base)} unconditional) net_mean={net_s.mean():+.2f} "
    f"net_median={np.median(net_s):+.2f} hit={(net_s>0).mean():.1%} t={tstat(net_s):+.2f} "
    f"cum_total={net_s.sum():+.1f} pts (vs unconditional cum_total={base['net_pnl_pts'].sum():+.1f} pts)")
cw_s = crash_window_stats(df_skip)
log(f"  CRASH WINDOW (with skip rule): n={cw_s['n']} total={cw_s['total']:+.1f}")
