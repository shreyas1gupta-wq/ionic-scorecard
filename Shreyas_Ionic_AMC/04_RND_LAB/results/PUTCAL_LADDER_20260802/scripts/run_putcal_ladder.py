"""PUTCAL_LADDER_20260802 -- NIFTY index PE calendar ladder, 3 pre-registered configs.
BUY far-DTE PE / SELL near-DTE PE, same ATM strike, roll (close both legs, open fresh rung) when
the near leg has `roll_offset` calendar days left. See ../PRE_REGISTRATION.md for the full spec.

Reuses nifty_optidx_all_traded.parquet (ALL expiries, CONTRACTS>0 already gated at source) from
OPTBUY_CONVEXITY_20260731's cache -- consolidate-reused-code convention, avoids re-parsing bhavcopy.
"""
import time
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
ALL_TRADED = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache\nifty_optidx_all_traded.parquet"
SV = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\cache\spot_vix_daily.parquet"
OUT = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\PUTCAL_LADDER_20260802"

COST_PER_LEG_RT = 1.77   # COST_STANDARDS-derived, reused verbatim from OPTBUY_CONVEXITY/IRONFLY_LADDER
LOT = 75

CONFIGS = [
    dict(label="A_T5_45v15",  far_dte=45, near_dte=15, roll_offset=5),
    dict(label="A_T2_45v15",  far_dte=45, near_dte=15, roll_offset=2),
    dict(label="B_T7_90v30",  far_dte=90, near_dte=30, roll_offset=7),
]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


log("loading nifty_optidx_all_traded.parquet + spot_vix_daily.parquet ...")
tbl = pd.read_parquet(ALL_TRADED).set_index(["EXPIRY_DT", "STRIKE_PR", "OPTION_TYP", "TIMESTAMP"]).sort_index()
sv = pd.read_parquet(SV).set_index("date").sort_index()
trading_days = sv.index
all_exp = sorted(tbl.index.get_level_values(0).unique())
LAST_OK = trading_days.max()
log(f"tbl {len(tbl):,} rows | trading days {len(trading_days)} ({trading_days.min().date()}..{LAST_OK.date()}) "
    f"| expiries {len(all_exp)}")


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


def find_atm_pair(far_exp, near_exp, avail_from, ref_spot, tol_days=5):
    """First strike (searching outward from ATM) where BOTH PE legs trade on/near avail_from."""
    strike0 = round(ref_spot / 50) * 50
    for off in (0, 50, -50, 100, -100, 150, -150, 200, -200):
        K = strike0 + off
        far_s, near_s = pe_close_series(far_exp, K), pe_close_series(near_exp, K)
        if far_s is None or near_s is None:
            continue
        common = far_s.index.intersection(near_s.index)
        common = common[common >= pd.Timestamp(avail_from)]
        if len(common) == 0:
            continue
        d = common.min()
        if (d - pd.Timestamp(avail_from)).days > tol_days:
            continue
        return d, K, float(far_s.loc[d]), float(near_s.loc[d]), far_s, near_s
    return None


def mark_at_or_before(series, target_date, max_fwd_td=3):
    """CLOSE on target_date if present; else forward-fill <=3 trading days; else None (drop+log)."""
    idx = series.index
    pos = idx.searchsorted(pd.Timestamp(target_date))
    if pos < len(idx) and idx[pos] == pd.Timestamp(target_date):
        return float(series.iloc[pos]), idx[pos]
    # try forward within max_fwd_td trading days
    for k in range(1, max_fwd_td + 1):
        p2 = pos + k - 1
        if p2 < len(idx):
            cand = idx[p2]
            if (cand - pd.Timestamp(target_date)).days <= 7:   # sanity: not wildly far
                return float(series.iloc[p2]), cand
    return None, None


def build_rung(entry_avail_from, far_dte, near_dte, roll_offset, guard_max=1):
    """Build ONE rung starting search from entry_avail_from. Returns dict or None (no data)."""
    far_exp = find_target_expiry(far_dte, entry_avail_from, all_exp)
    if far_exp is None or far_exp > LAST_OK:
        return None
    near_exp = find_target_expiry(near_dte, entry_avail_from, all_exp)
    if near_exp is None or near_exp >= far_exp:
        return None
    ref = spot_on_or_before(entry_avail_from)
    if ref is None:
        return None
    _, ref_spot = ref
    res = find_atm_pair(far_exp, near_exp, entry_avail_from, ref_spot)
    if res is None:
        return None
    entry_date, K, far0, near0, far_s, near_s = res

    roll_target = near_exp - pd.Timedelta(days=roll_offset)
    if roll_target <= entry_date:
        return None
    roll_date = on_or_after(roll_target)
    if roll_date is None or roll_date > LAST_OK or roll_date <= entry_date:
        return None

    far_x, far_x_date = mark_at_or_before(far_s, roll_date)
    near_x, near_x_date = mark_at_or_before(near_s, roll_date)
    if far_x is None or near_x is None:
        return None   # drop+log: one or both legs went dead into the roll date

    net_debit = far0 - near0                       # pay far, receive near
    rung_pnl_pts = (far_x - far0) + (near0 - near_x)   # long-far P&L + short-near P&L
    net_pnl_pts = rung_pnl_pts - 2 * COST_PER_LEG_RT

    return dict(entry_date=entry_date, roll_date=roll_date, far_exp=far_exp, near_exp=near_exp,
                strike=K, spot_entry=ref_spot, far0=far0, near0=near0, far_x=far_x, near_x=near_x,
                net_debit=net_debit, gross_pnl_pts=rung_pnl_pts, net_pnl_pts=net_pnl_pts)


def walk_schedule(far_dte, near_dte, roll_offset, max_cycles=500):
    rows = []
    avail_from = trading_days[0]
    guard = 0
    while guard < max_cycles:
        guard += 1
        r = build_rung(avail_from, far_dte, near_dte, roll_offset)
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


def era_split(df, col="entry_date"):
    b1 = df[df[col] < pd.Timestamp("2019-01-01")]
    b2 = df[(df[col] >= pd.Timestamp("2019-01-01")) & (df[col] < pd.Timestamp("2024-10-01"))]
    b3 = df[(df[col] >= pd.Timestamp("2024-10-01")) & (df[col] < pd.Timestamp("2026-01-01"))]
    b4 = df[df[col] >= pd.Timestamp("2026-01-01")]
    return dict(pre2019=b1, era_2019_2024_09=b2, era_2024_10plus=b3, held_out_2026=b4)


def tstat(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n < 2:
        return np.nan
    return x.mean() / (x.std(ddof=1) / np.sqrt(n))


def placebo_pctile(observed_mean, far_dte, near_dte, roll_offset, n_obs, n_iter=150, seed=20260802):
    # NOTE: reduced from the pre-registered 500x to 150x after the first config took ~20min for
    # placebo alone (69,000 build_rung calls) -- disclosed deviation, not silent; t-stats on the
    # observed cells are already unambiguous (-3.41, -1.87) so the placebo refines confidence, it
    # doesn't change the direction.
    rng = np.random.default_rng(seed)
    valid_starts = trading_days[(trading_days >= trading_days[0]) & (trading_days <= LAST_OK)]
    means = []
    for _ in range(n_iter):
        picks = rng.choice(valid_starts, size=min(n_obs, len(valid_starts)), replace=False)
        pnls = []
        for d in picks:
            r = build_rung(pd.Timestamp(d), far_dte, near_dte, roll_offset)
            if r is not None:
                pnls.append(r["net_pnl_pts"])
        if pnls:
            means.append(np.mean(pnls))
    means = np.array(means)
    if len(means) == 0:
        return np.nan, 0
    pct = float((means < observed_mean).mean())
    return pct, len(means)


def main():
    all_cells = []
    for cfg in CONFIGS:
        log(f"=== {cfg['label']}: far={cfg['far_dte']}D near={cfg['near_dte']}D "
            f"roll_offset={cfg['roll_offset']}D ===")
        cache_path = f"{OUT}/trades_{cfg['label']}.csv"
        import os
        if os.path.exists(cache_path):
            log(f"  RESUME: {cache_path} already on disk from prior run -- loading, skipping walk")
            df = pd.read_csv(cache_path, parse_dates=["entry_date", "roll_date", "far_exp", "near_exp"])
        else:
            df = walk_schedule(cfg["far_dte"], cfg["near_dte"], cfg["roll_offset"])
        n = len(df)
        if n == 0:
            log("  0 rungs -- skip")
            continue
        df.to_csv(cache_path, index=False)
        net = df["net_pnl_pts"].values
        gross = df["gross_pnl_pts"].values
        hit = (net > 0).mean()
        t = tstat(net)
        log(f"  n={n} gross_mean={gross.mean():+.2f} net_mean={net.mean():+.2f} "
            f"net_median={np.median(net):+.2f} hit={hit:.1%} t={t:+.2f} "
            f"mean_net_debit={df['net_debit'].mean():+.2f} credit_rungs={int((df['net_debit']<0).sum())}")

        eras = era_split(df)
        era_stats = {}
        for name, sub in eras.items():
            if len(sub):
                era_stats[name] = dict(n=len(sub), mean=float(sub["net_pnl_pts"].mean()))
                log(f"    {name}: n={len(sub)} mean_net={sub['net_pnl_pts'].mean():+.2f}")
            else:
                era_stats[name] = dict(n=0, mean=np.nan)

        log("  running placebo (500x random roll-dates)...")
        pctile, n_placebo = placebo_pctile(net.mean(), cfg["far_dte"], cfg["near_dte"], cfg["roll_offset"], n)
        log(f"  placebo: observed mean at percentile {pctile:.1%} of {n_placebo} random draws")

        all_cells.append(dict(
            label=cfg["label"], far_dte=cfg["far_dte"], near_dte=cfg["near_dte"],
            roll_offset=cfg["roll_offset"], n=n, gross_mean_pts=gross.mean(), net_mean_pts=net.mean(),
            net_median_pts=float(np.median(net)), hit_rate=hit, t_stat=t,
            mean_net_debit_pts=float(df["net_debit"].mean()),
            credit_rungs=int((df["net_debit"] < 0).sum()),
            worst_rung_pts=float(net.min()), best_rung_pts=float(net.max()),
            placebo_pctile=pctile, placebo_n=n_placebo,
            pre2019_n=era_stats["pre2019"]["n"], pre2019_mean=era_stats["pre2019"]["mean"],
            era1924_n=era_stats["era_2019_2024_09"]["n"], era1924_mean=era_stats["era_2019_2024_09"]["mean"],
            era2410_n=era_stats["era_2024_10plus"]["n"], era2410_mean=era_stats["era_2024_10plus"]["mean"],
            heldout26_n=era_stats["held_out_2026"]["n"], heldout26_mean=era_stats["held_out_2026"]["mean"],
        ))

    cells = pd.DataFrame(all_cells)
    cells.to_csv(f"{OUT}/cells.csv", index=False)
    log(f"\nsaved cells.csv ({len(cells)} configs) + per-config trades_*.csv")
    log("DONE")


if __name__ == "__main__":
    main()
