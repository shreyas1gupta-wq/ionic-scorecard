"""Standing firm rule: auto-test the REVERSE of any strongly-negative-gross result (only
rescues DIRECTIONAL losses, never cost-dominated ones). The 1DTE bucket showed consistent
NEGATIVE gross pts (-6 to -7, well beyond cost noise) across ALL 5 confirmation windows and
all 3 RR - a directional loss, not a friction story - so it is tested here in reverse using
the SAME entry times/prices already found in Stage B (only the trade DIRECTION flips: fade
the confirmed move instead of following it). Reuses trades_detail_raw.parquet for
(trading_day, entry_time, W, RR, era, cost, held_out_2026) - re-simulates from there.
"""
import sys
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
from pathsafe import simulate_exit, PathSafeError  # noqa: E402

RES_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/FLOW_IMBALANCE_20260731"
STOP_PTS = 15.0
CUTOFF_TIME = dt.time(15, 20)
N_PLACEBO = 100
PLACEBO_MAX_N = 200
RNG = np.random.default_rng(20260731)


def _pessimistic_exit_index(bars, entry, direction, stop, target):
    hi = bars["high"].to_numpy(float)
    lo = bars["low"].to_numpy(float)
    s = int(direction)
    for k in range(len(hi)):
        fav = (hi[k] - entry) if s > 0 else (entry - lo[k])
        adv = (lo[k] - entry) if s > 0 else (entry - hi[k])
        if bool(stop) and adv <= -stop:
            return k
        if bool(target) and fav >= target:
            return k
    return len(hi) - 1


def one_at_a_time(df_cell):
    df_cell = df_cell.sort_values("entry_time").reset_index(drop=True)
    keep, last_exit = [], None
    for r in df_cell.itertuples(index=False):
        if last_exit is not None and r.entry_time < last_exit:
            continue
        keep.append(r)
        last_exit = r.exit_time
    return pd.DataFrame(keep)


def build_day_groups(spot_idx):
    spot_idx = spot_idx.copy()
    spot_idx["tod_bucket"] = spot_idx.index.hour * 2 + spot_idx.index.minute // 30
    return {d: g for d, g in spot_idx.groupby(spot_idx.index.date)}


def build_placebo_pools(day_groups):
    pools = {}
    BREAK_DATE = dt.date(2024, 10, 1)
    for d, g in day_groups.items():
        era = "pre-Oct2024" if d < BREAK_DATE else "post-Oct2024"
        elig = g[g.index.time < CUTOFF_TIME]
        for t, tb in zip(elig.index, elig["tod_bucket"]):
            pools.setdefault((era, int(tb)), []).append((d, t))
    return pools


def run_placebo(build_cell, RR, day_groups, pools):
    strata_full = list(zip(build_cell["era"], build_cell["tod_bucket"], build_cell["cost"]))
    if len(strata_full) > PLACEBO_MAX_N:
        idx = RNG.choice(len(strata_full), size=PLACEBO_MAX_N, replace=False)
        strata = [strata_full[i] for i in idx]
    else:
        strata = strata_full
    means = np.full(N_PLACEBO, np.nan)
    for rep in range(N_PLACEBO):
        pnl_vals = []
        for era, tod_b, cost in strata:
            cands = pools.get((era, int(tod_b)))
            if not cands:
                continue
            d, t = cands[RNG.integers(0, len(cands))]
            day_spot = day_groups[d]
            entry_price = float(day_spot.loc[t, "open"])
            trade_bars = day_spot[(day_spot.index > t) & (day_spot.index.time <= CUTOFF_TIME)]
            if len(trade_bars) < 3:
                continue
            direction = 1 if RNG.random() < 0.5 else -1
            try:
                res = simulate_exit(trade_bars, entry_price, direction=direction,
                                     stop=STOP_PTS, trail=0.0, target=RR * STOP_PTS)
            except PathSafeError:
                continue
            pnl_vals.append(res.pnl_pessimistic - cost)
        if pnl_vals:
            means[rep] = np.mean(pnl_vals)
    return means[~np.isnan(means)]


def main():
    trades = pd.read_parquet(RES_DIR / "trades_detail_raw.parquet")
    t1 = trades[trades.dte_bucket == "1DTE"].copy()
    print(f"1DTE original trade-rows: {len(t1)}")

    spot_idx = chain.load_index()
    day_groups = build_day_groups(spot_idx)
    pools = build_placebo_pools(day_groups)

    out_rows = []
    for W in sorted(t1.W.unique()):
        for RR in sorted(t1.RR.unique()):
            sub = t1[(t1.W == W) & (t1.RR == RR)].copy()
            if len(sub) < 5:
                continue
            rev_rows = []
            for r in sub.itertuples(index=False):
                day_spot = day_groups.get(r.trading_day)
                if day_spot is None:
                    continue
                entry_price = float(day_spot.loc[r.entry_time, "open"])
                trade_bars = day_spot[(day_spot.index > r.entry_time) & (day_spot.index.time <= CUTOFF_TIME)]
                if len(trade_bars) < 3:
                    continue
                rev_dir = -int(r.direction)
                try:
                    res = simulate_exit(trade_bars, entry_price, direction=rev_dir,
                                         stop=STOP_PTS, trail=0.0, target=RR * STOP_PTS)
                except PathSafeError:
                    continue
                k = _pessimistic_exit_index(trade_bars, entry_price, rev_dir, STOP_PTS, RR * STOP_PTS)
                rev_rows.append(dict(
                    trading_day=r.trading_day, era=r.era, cost=r.cost, tod_bucket=r.tod_bucket,
                    entry_time=r.entry_time, exit_time=trade_bars.index[k],
                    pnl_pess=res.pnl_pessimistic, net_pess=res.pnl_pessimistic - r.cost,
                    held_out_2026=r.held_out_2026,
                ))
            if len(rev_rows) < 5:
                continue
            revdf = pd.DataFrame(rev_rows)
            kept = one_at_a_time(revdf)
            build = kept[~kept.held_out_2026]
            held = kept[kept.held_out_2026]
            if len(build) < 5:
                continue
            mean_net = build.net_pess.mean()
            win = (build.pnl_pess > 0).mean()
            null_hit = 1.0 / (1.0 + RR)
            t_stat = (build.pnl_pess.mean() / (build.pnl_pess.std(ddof=1) / np.sqrt(len(build)))
                      if len(build) > 1 and build.pnl_pess.std(ddof=1) > 0 else np.nan)
            pre = build[build.era == "pre-Oct2024"]
            post = build[build.era == "post-Oct2024"]
            placebo_dist = run_placebo(build, RR, day_groups, pools)
            p_val = float((placebo_dist >= mean_net).mean()) if len(placebo_dist) else np.nan
            out_rows.append(dict(
                metric="net_bullish(b)_REVERSED_1DTE", W=W, RR=RR, dte_bucket="1DTE",
                n=len(build), n_held_out_2026=len(held), win_pct=round(win * 100, 1),
                null_hit_pct=round(null_hit * 100, 1),
                mean_pts_net=round(mean_net, 3), t_stat=round(t_stat, 3) if pd.notna(t_stat) else np.nan,
                placebo_p=round(p_val, 4) if pd.notna(p_val) else np.nan,
                n_pre=len(pre), mean_net_pre=round(pre.net_pess.mean(), 3) if len(pre) else np.nan,
                n_post=len(post), mean_net_post=round(post.net_pess.mean(), 3) if len(post) else np.nan,
                mean_net_2026=round(held.net_pess.mean(), 3) if len(held) else np.nan,
            ))
            print(f"REVERSED W={W} RR={RR} 1DTE: n={len(build)} win={win:.1%} "
                  f"mean_net={mean_net:+.2f} t={t_stat:.2f} placebo_p={p_val}")
            pd.DataFrame(out_rows).to_csv(RES_DIR / "reverse_1dte_cells.csv", index=False)

    pd.DataFrame(out_rows).to_csv(RES_DIR / "reverse_1dte_cells.csv", index=False)
    print("DONE")


if __name__ == "__main__":
    main()
