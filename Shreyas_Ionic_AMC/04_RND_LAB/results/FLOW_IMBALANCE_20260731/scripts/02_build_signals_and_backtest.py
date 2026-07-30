"""Stage B: build the value-weighted flow-imbalance signal, apply the two-stage
price-confirmation gate, simulate the trade with pathsafe (pessimistic bound),
run the matched random-entry placebo, and write cells.csv + trades_detail.parquet.

Reads:  bucket_flow/{expiry}.parquet  (Stage A output)
        NIFTY spot 1-min via chain.load_index()
Writes: signals_all.parquet   (every candidate signal, confirmed or not)
        trades_detail_raw.parquet (every simulated trade, all W x RR x dte_bucket combos)
        cells.csv              (aggregated cell table)
        trial_ledger.csv       (every cell attempted, incl. ones with too few trades)
        expiry_vs_nonexpiry.csv
"""
import sys, time
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
BUCKET_DIR = RES_DIR / "bucket_flow"
LOG_DIR = RES_DIR / "logs"

Z_THRESH = 2.0
MIN_PRIOR = 6                     # warm-up buckets before a signal is eligible
WINDOWS = [3, 5, 10, 15, 20]       # confirmation windows, minutes
MAX_CONF_HORIZON = max(WINDOWS)
RRS = [1.0, 1.5, 2.0]
STOP_PTS = 15.0
CUTOFF_TIME = dt.time(15, 20)
COST_PRE = 4.47 + 0.5              # RT + slippage, pre-2024-10-01
COST_POST = 5.97 + 0.5
BREAK_DATE = dt.date(2024, 10, 1)
HOLDOUT_START = dt.date(2026, 1, 1)
N_PLACEBO = 100
PLACEBO_MAX_N = 200        # cap trades-per-replicate for large cells (speed; proportional subsample)
RNG = np.random.default_rng(20260731)


def log(msg):
    line = f"[{dt.datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG_DIR / "02_build_signals.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _pessimistic_exit_index(bars: pd.DataFrame, entry: float, direction: int, stop: float, target: float) -> int:
    """Local helper (does NOT touch pathsafe.py): re-derives ONLY the bar index of the
    pessimistic exit, mirroring pathsafe's internal adverse-first resolution, so the
    one-position-at-a-time scheduler knows when a trade's capital is actually free again.
    PnL itself is always taken from pathsafe.simulate_exit(), never from this helper."""
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


def dte_bucket(dte):
    if dte == 0:
        return "0DTE"
    if dte == 1:
        return "1DTE"
    if 2 <= dte <= 4:
        return "2-4DTE"
    return "5+DTE"


def era_of(tday: dt.date):
    return "pre-Oct2024" if tday < BREAK_DATE else "post-Oct2024"


def load_all_flow():
    files = sorted(BUCKET_DIR.glob("*.parquet"))
    frames = []
    for f in files:
        try:
            d = pd.read_parquet(f)
        except Exception as e:
            log(f"WARN could not read {f.name}: {e}")
            continue
        if d.empty:
            continue
        frames.append(d)
    out = pd.concat(frames, ignore_index=True)
    log(f"loaded {len(files)} non-empty files -> {len(out):,} bucket-rows")
    return out


def build_signals(flow: pd.DataFrame) -> pd.DataFrame:
    flow = flow.copy()
    for c in ["CE_buying", "CE_writing", "PE_buying", "PE_writing"]:
        if c not in flow.columns:
            flow[c] = 0.0
    flow["net_bullish"] = ((flow["PE_writing"] + flow["CE_buying"])
                            - (flow["CE_writing"] + flow["PE_buying"]))
    flow["metric_a"] = flow["PE_writing"] - flow["CE_writing"]
    flow["trading_day_d"] = pd.to_datetime(flow["trading_day"]).dt.date
    flow = flow.sort_values(["expiry", "trading_day", "bucket"]).reset_index(drop=True)

    z_all = np.full(len(flow), np.nan)
    for _, idx in flow.groupby(["expiry", "trading_day"]).groups.items():
        pos = flow.index.get_indexer(idx)
        x = flow.loc[idx, "net_bullish"].to_numpy()
        n = len(x)
        for k in range(MIN_PRIOR, n):
            prior = x[:k]
            mu, sd = prior.mean(), prior.std(ddof=1)
            if sd > 1e-9:
                z_all[pos[k]] = (x[k] - mu) / sd
    flow["z"] = z_all
    flow["direction"] = 0
    flow.loc[flow["z"] >= Z_THRESH, "direction"] = 1
    flow.loc[flow["z"] <= -Z_THRESH, "direction"] = -1
    return flow


def build_day_groups(spot_idx: pd.DataFrame):
    """date -> day dataframe (open/high/low/close), plus a tod_bucket column."""
    spot_idx = spot_idx.copy()
    spot_idx["tod_bucket"] = spot_idx.index.hour * 2 + spot_idx.index.minute // 30
    groups = {d: g for d, g in spot_idx.groupby(spot_idx.index.date)}
    return groups


def confirm_and_simulate(signals: pd.DataFrame, day_groups: dict):
    trades = []
    n_sig = 0
    for row in signals.itertuples(index=False):
        n_sig += 1
        tday = row.trading_day_d
        day_spot = day_groups.get(tday)
        if day_spot is None or day_spot.empty:
            continue
        bucket_end = row.bucket + pd.Timedelta(minutes=5)
        horizon_end = bucket_end + pd.Timedelta(minutes=MAX_CONF_HORIZON)
        conf_window = day_spot[(day_spot.index > bucket_end) & (day_spot.index <= horizon_end)]
        if conf_window.empty:
            continue
        if row.direction > 0:
            hit = conf_window[conf_window["close"] > row.spot_high]
        else:
            hit = conf_window[conf_window["close"] < row.spot_low]
        if hit.empty:
            continue
        t_conf = hit.index[0]
        minutes_to_confirm = (t_conf - bucket_end).total_seconds() / 60.0
        after_conf = day_spot[day_spot.index > t_conf]
        if after_conf.empty:
            continue
        entry_time = after_conf.index[0]
        entry_price = float(after_conf.iloc[0]["open"])
        trade_bars = day_spot[(day_spot.index > entry_time) & (day_spot.index.time <= CUTOFF_TIME)]
        if len(trade_bars) < 3:
            continue
        era = era_of(tday)
        cost = COST_PRE if tday < BREAK_DATE else COST_POST
        for W in WINDOWS:
            if minutes_to_confirm > W:
                continue
            for RR in RRS:
                try:
                    res = simulate_exit(trade_bars, entry_price, direction=int(row.direction),
                                         stop=STOP_PTS, trail=0.0, target=RR * STOP_PTS)
                except PathSafeError:
                    continue
                k = _pessimistic_exit_index(trade_bars, entry_price, int(row.direction),
                                             STOP_PTS, RR * STOP_PTS)
                exit_time = trade_bars.index[k]
                trades.append(dict(
                    expiry=row.expiry, trading_day=tday, dte=row.dte, is_monthly=row.is_monthly,
                    dte_bucket=dte_bucket(row.dte), era=era, W=W, RR=RR,
                    direction=int(row.direction), z=row.z, entry_time=entry_time,
                    exit_time=exit_time, minutes_to_confirm=minutes_to_confirm,
                    pnl_pess=res.pnl_pessimistic, pnl_opt=res.pnl_optimistic,
                    reason_pess=res.reason_pessimistic, cost=cost,
                    net_pess=res.pnl_pessimistic - cost, net_opt=res.pnl_optimistic - cost,
                    held_out_2026=(tday >= HOLDOUT_START),
                    tod_bucket=entry_time.hour * 2 + entry_time.minute // 30,
                ))
        if n_sig % 500 == 0:
            log(f"  ...{n_sig}/{len(signals)} signals scanned, {len(trades)} trade-rows so far")
    return pd.DataFrame(trades)


def one_at_a_time(df_cell: pd.DataFrame):
    """Greedy non-overlap filter: keep a trade only if its entry is at/after the previous
    KEPT trade's actual exit time (exit_time = exact pessimistic-path exit bar)."""
    df_cell = df_cell.sort_values("entry_time").reset_index(drop=True)
    keep = []
    last_exit = None
    for r in df_cell.itertuples(index=False):
        if last_exit is not None and r.entry_time < last_exit:
            continue
        keep.append(r)
        last_exit = r.exit_time
    return pd.DataFrame(keep)


def build_placebo_pools(day_groups: dict):
    """Precompute, ONCE, per (era, tod_bucket): a list of (date, timestamp) candidates
    with time < CUTOFF_TIME, so placebo draws are O(1) lookups, not per-call rescans."""
    pools = {}
    for d, g in day_groups.items():
        era = era_of(d)
        elig = g[g.index.time < CUTOFF_TIME]
        for t, tb in zip(elig.index, elig["tod_bucket"]):
            pools.setdefault((era, int(tb)), []).append((d, t))
    return pools


def run_placebo_for_cell(build_cell: pd.DataFrame, RR, day_groups, pools, n_placebo=N_PLACEBO):
    """N_PLACEBO replicate means of matched (era, tod_bucket) entries with RANDOM direction,
    identical exit rule. Returns array of replicate mean NET pts.
    For cells with n > PLACEBO_MAX_N, subsamples the stratum list proportionally (documented
    speed cap - the placebo tests whether the MATCHED time/DTE/era context alone produces
    the edge, so a representative subsample of the same strata mix is a valid substitute for
    exhaustively replaying every real trade's stratum)."""
    strata_full = list(zip(build_cell["era"], build_cell["tod_bucket"], build_cell["cost"]))
    if len(strata_full) > PLACEBO_MAX_N:
        idx = RNG.choice(len(strata_full), size=PLACEBO_MAX_N, replace=False)
        strata = [strata_full[i] for i in idx]
    else:
        strata = strata_full
    n = len(strata)
    means = np.full(n_placebo, np.nan)
    for rep in range(n_placebo):
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
    t0 = time.time()
    flow = load_all_flow()
    signals = build_signals(flow)
    signals.to_parquet(RES_DIR / "signals_all.parquet", index=False)
    n_candidates = int((signals["direction"] != 0).sum())
    log(f"candidate signals (|z|>={Z_THRESH}): {n_candidates} of {len(signals):,} eligible buckets")
    sig_fire = signals[signals["direction"] != 0].copy()

    spot_idx = chain.load_index()
    day_groups = build_day_groups(spot_idx)
    log(f"day_groups built: {len(day_groups)} trading days")
    pools = build_placebo_pools(day_groups)
    log(f"placebo pools built: {len(pools)} (era,tod_bucket) strata")

    trades = confirm_and_simulate(sig_fire, day_groups)
    log(f"raw trade-rows (all W x RR combos, pre-overlap-filter): {len(trades)}")
    if trades.empty:
        log("NO TRADES CONFIRMED AT ALL. Writing empty cells.csv and stopping.")
        pd.DataFrame().to_csv(RES_DIR / "cells.csv", index=False)
        return
    trades.to_parquet(RES_DIR / "trades_detail_raw.parquet", index=False)

    cell_rows = []
    trial_ledger = []
    for W in WINDOWS:
        for RR in RRS:
            for dte_b in ["0DTE", "1DTE", "2-4DTE", "5+DTE"]:
                sub = trades[(trades.W == W) & (trades.RR == RR) & (trades.dte_bucket == dte_b)]
                trial_ledger.append(dict(W=W, RR=RR, dte_bucket=dte_b, n_raw=len(sub)))
                if len(sub) < 5:
                    continue
                kept = one_at_a_time(sub)
                if len(kept) < 5:
                    continue
                build = kept[~kept.held_out_2026]
                held = kept[kept.held_out_2026]
                if len(build) < 5:
                    continue
                mean_pts = build.pnl_pess.mean()
                mean_net = build.net_pess.mean()
                win = (build.pnl_pess > 0).mean()
                null_hit = 1.0 / (1.0 + RR)
                t_stat = (build.pnl_pess.mean() / (build.pnl_pess.std(ddof=1) / np.sqrt(len(build)))
                          if len(build) > 1 and build.pnl_pess.std(ddof=1) > 0 else np.nan)
                pre = build[build.era == "pre-Oct2024"]
                post = build[build.era == "post-Oct2024"]
                placebo_dist = run_placebo_for_cell(build, RR, day_groups, pools)
                if len(placebo_dist):
                    p_val = float((placebo_dist >= mean_net).mean())
                    placebo_mean = float(placebo_dist.mean())
                else:
                    p_val, placebo_mean = np.nan, np.nan
                span_days = max(1.0, (build.entry_time.max() - build.entry_time.min()).days)
                months_spanned = max(1.0, span_days / 30.4)
                cum = build.sort_values("entry_time").pnl_pess.cumsum()
                max_dd = float((cum.cummax() - cum).max())
                pos_pnl = build.pnl_pess.clip(lower=0)
                profit_conc = float(pos_pnl.max() / pos_pnl.sum()) if pos_pnl.sum() > 0 else np.nan
                cell_rows.append(dict(
                    metric="net_bullish(b)", W=W, RR=RR, dte_bucket=dte_b,
                    n=len(build), n_held_out_2026=len(held),
                    trades_per_month=round(len(build) / months_spanned, 3),
                    win_pct=round(win * 100, 1), null_hit_pct=round(null_hit * 100, 1),
                    excess_hit_pp=round((win - null_hit) * 100, 1),
                    mean_pts_gross=round(mean_pts, 3), mean_pts_net=round(mean_net, 3),
                    t_stat=round(t_stat, 3) if pd.notna(t_stat) else np.nan,
                    placebo_mean_net=round(placebo_mean, 3) if pd.notna(placebo_mean) else np.nan,
                    placebo_p=round(p_val, 4) if pd.notna(p_val) else np.nan,
                    n_pre=len(pre), mean_net_pre=round(pre.net_pess.mean(), 3) if len(pre) else np.nan,
                    n_post=len(post), mean_net_post=round(post.net_pess.mean(), 3) if len(post) else np.nan,
                    mean_net_2026=round(held.net_pess.mean(), 3) if len(held) else np.nan,
                    max_dd_pts=round(max_dd, 2),
                    profit_conc=round(profit_conc, 3) if pd.notna(profit_conc) else np.nan,
                ))
                log(f"cell W={W} RR={RR} {dte_b}: n={len(build)} win={win:.1%} "
                    f"mean_net={mean_net:+.2f} t={t_stat:.2f} placebo_p={p_val}")
                # checkpoint after every cell so nothing is lost on a token/time cut
                pd.DataFrame(cell_rows).to_csv(RES_DIR / "cells.csv", index=False)
                pd.DataFrame(trial_ledger).to_csv(RES_DIR / "trial_ledger.csv", index=False)

    pd.DataFrame(trial_ledger).to_csv(RES_DIR / "trial_ledger.csv", index=False)
    cells = pd.DataFrame(cell_rows)
    cells.to_csv(RES_DIR / "cells.csv", index=False)
    log(f"wrote {len(cells)} cells to cells.csv, {len(trial_ledger)} trials to trial_ledger.csv")

    # expiry-day vs non-expiry-day dedicated comparison (metric b, RR=1.5, pooled across W)
    exp_rows = []
    for label, sub in [("expiry_day(0DTE)", trades[trades.dte_bucket == "0DTE"]),
                        ("non_expiry_day(1DTE+)", trades[trades.dte_bucket != "0DTE"])]:
        s = sub[sub.RR == 1.5]
        if len(s) < 5:
            continue
        kept = one_at_a_time(s)
        build = kept[~kept.held_out_2026]
        if len(build) < 3:
            continue
        placebo_dist = run_placebo_for_cell(build, 1.5, day_groups, pools)
        p_val = float((placebo_dist >= build.net_pess.mean()).mean()) if len(placebo_dist) else np.nan
        t_val = (build.pnl_pess.mean() / (build.pnl_pess.std(ddof=1) / np.sqrt(len(build)))
                 if len(build) > 1 and build.pnl_pess.std(ddof=1) > 0 else np.nan)
        exp_rows.append(dict(bucket=label, n=len(build), win_pct=round((build.pnl_pess > 0).mean() * 100, 1),
                              mean_net_pts=round(build.net_pess.mean(), 3),
                              t_stat=round(t_val, 3) if pd.notna(t_val) else np.nan,
                              placebo_p=round(p_val, 4) if pd.notna(p_val) else np.nan))
    pd.DataFrame(exp_rows).to_csv(RES_DIR / "expiry_vs_nonexpiry.csv", index=False)
    log(f"DONE total_elapsed={time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
