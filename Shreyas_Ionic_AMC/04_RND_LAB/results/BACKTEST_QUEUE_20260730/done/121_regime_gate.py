"""
121_regime_gate.py -- Arjun Rao, 2026-07-30.
Pre-registered regime-conditional gate battery: 7 signals x 4 sleeves = 28 cells.
Spec: Shreyas_Ionic_AMC/04_RND_LAB/results/REGIME_GATE_20260730/PRE_REGISTRATION.md
Self-contained, argument-free. Writes all outputs to REGIME_GATE_20260730/.
Data used here is all small (daily index closes, trade-level CSVs a few thousand rows,
term_structure.csv 3.6k rows) -- no 1-min files touched, RAM footprint trivial.
"""
import numpy as np
import pandas as pd
from pathlib import Path
import traceback

rng = np.random.default_rng(20260730)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/REGIME_GATE_20260730"
OUT.mkdir(parents=True, exist_ok=True)
LOG = []


def log(msg):
    print(msg, flush=True)
    LOG.append(str(msg))


# ---------------------------------------------------------------- market signals
def load_market():
    idxf = [pd.read_parquet(p) for p in sorted(
        (ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close").glob("indices_*.parquet"))]
    IC = pd.concat(idxf, ignore_index=True)
    IC["nm"] = IC["Index Name"].str.strip().str.upper()
    IC["date"] = pd.to_datetime(IC["file_date"])

    def series(nm):
        g = IC[IC.nm == nm].set_index("date").sort_index()
        s = pd.to_numeric(g["Closing Index Value"], errors="coerce")
        return s[~s.index.duplicated()]

    nifty = series("NIFTY 50")
    vix = series("INDIA VIX")
    return nifty, vix


def build_market_signals():
    nifty, vix = load_market()
    idx = nifty.index.union(vix.index)
    nifty = nifty.reindex(idx).ffill()
    vix = vix.reindex(idx).ffill()

    s1 = vix.rolling(252, min_periods=252).rank(pct=True)  # VIX level, reuses VBT construction
    vov = vix.diff().rolling(20, min_periods=20).std()
    s2 = (vov >= vov.expanding(min_periods=252).median()).astype(float)
    s2[vov.isna()] = np.nan

    nret = nifty.pct_change()
    rv20 = nret.rolling(20, min_periods=20).std() * np.sqrt(252)
    s3 = (rv20 >= rv20.expanding(min_periods=252).median()).astype(float)
    s3[rv20.isna()] = np.nan

    ma200 = nifty.rolling(200, min_periods=200).mean()
    s4 = (nifty > ma200).astype(float)
    s4[ma200.isna()] = np.nan

    slope = ma200.pct_change(20)
    s5 = (slope > 0).astype(float)
    s5[slope.isna()] = np.nan

    s1b = (s1 >= 0.5).astype(float)
    s1b[s1.isna()] = np.nan

    df = pd.DataFrame({"S1_vix_level": s1b, "S2_vol_of_vol": s2, "S3_realized_vol": s3,
                        "S4_trend_sign": s4, "S5_trend_slope": s5}, index=idx)
    return df, nifty.index.min(), nifty.index.max()


def build_termstruct_signal():
    ts = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/RATIO_CALENDAR_20260730/term_structure.csv",
                      usecols=["day", "iv_spread"])
    ts["day"] = pd.to_datetime(ts["day"])
    ts = ts.set_index("day").sort_index()
    pct = ts["iv_spread"].expanding(min_periods=250).rank(pct=True)
    s6 = (pct >= 0.5).astype(float)
    s6[pct.isna()] = np.nan
    return s6.rename("S6_term_structure")


# ---------------------------------------------------------------- sleeve monthly P&L
def monthly_own_dd_state(monthly_pnl: pd.Series) -> pd.Series:
    """State=1 if currently in a deeper-than-typical (own trailing history) drawdown.
    Uses cumulative P&L in the sleeve's native unit, causal (expanding) throughout."""
    equity = monthly_pnl.cumsum()
    peak = equity.cummax()
    dd = (equity - peak).abs()  # native-unit drawdown, >=0
    dd_med = dd.expanding(min_periods=6).median()
    state = (dd >= dd_med).astype(float)
    state[dd_med.isna()] = np.nan
    return state


def load_sweep(tag, fname):
    d = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SWEEP_11YR_20260729" / fname)
    d["t"] = pd.to_datetime(d["t"])
    exit_ts = d["t"] + pd.to_timedelta(d["hold_min"], unit="m")
    d["exit_month"] = exit_ts.dt.to_period("M")
    m = d.groupby("exit_month")["net"].sum()
    # convert to points-equivalent for a stable, lot-size-free unit (net rupees / notional lots -> use net_pts proxy)
    # gross_pts already point-denominated; use net rupees / (Rs per point per lot) is unknown here, so report in
    # native points using gross_pts-cost_pts approximation is not exact -- use rupee 'net' directly, native unit = INR (1 lot).
    m.name = tag
    return m


def load_calendar():
    d = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/RATIO_CALENDAR_20260730/grid_a_trades_raw.csv",
                     usecols=["exit_day", "strike_struct", "ratio", "exit_variant", "net_pts"])
    sub = d[(d.strike_struct == "ATM_ATM") & (d.ratio == "1x1") & (d.exit_variant == "3d_before")].copy()
    sub["exit_day"] = pd.to_datetime(sub["exit_day"])
    sub["exit_month"] = sub["exit_day"].dt.to_period("M")
    m = sub.groupby("exit_month")["net_pts"].sum()
    m.name = "CALENDAR_1x1_3d"
    return m


def load_s1f():
    d = pd.read_csv(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711/book_daily_pnl.csv",
                     index_col=0, parse_dates=True)
    s = d["s1f"]
    s.index = s.index.to_period("M")
    m = s.groupby(level=0).sum()
    m.name = "S1F"
    return m


# ---------------------------------------------------------------- placebo + test
def block_permute_diff(states: np.ndarray, targets: np.ndarray, block=6, n=1000):
    """Circular block-permutation placebo: shuffle contiguous BLOCKS of the state sequence
    (block=6 months) to preserve within-block autocorrelation/persistence, recompute
    diff-of-means vs the (fixed, original-order) target sequence."""
    N = len(states)
    n_blocks = int(np.ceil(N / block))
    padded = np.array(list(states) + [np.nan] * (n_blocks * block - N))
    blocks = padded.reshape(n_blocks, block)
    nulls = []
    for _ in range(n):
        order = rng.permutation(n_blocks)
        perm = blocks[order].reshape(-1)[:N]
        hi = targets[perm == 1]
        lo = targets[perm == 0]
        if len(hi) >= 2 and len(lo) >= 2:
            nulls.append(np.nanmean(hi) - np.nanmean(lo))
    return np.array(nulls)


def run_cell(sig_name, sig_monthly, sleeve_name, pnl_monthly):
    df = pd.DataFrame({"state": sig_monthly, "target": pnl_monthly}).dropna(subset=["state"])
    df["target_next"] = df["target"].reindex(df.index).shift(-1)
    # align: state at month t -> target at month t+1 (shift target series by -1 in the SAME index)
    # rebuild properly against the full pnl index to avoid gaps:
    full = pd.DataFrame(index=pnl_monthly.index)
    full["target"] = pnl_monthly
    full["state"] = sig_monthly.reindex(full.index)
    full["target_next"] = full["target"].shift(-1)
    full = full.dropna(subset=["state", "target_next"])
    n = len(full)
    if n < 12:
        return dict(signal=sig_name, sleeve=sleeve_name, n=n, verdict="TOO_FEW_OBS")
    hi = full.loc[full.state == 1, "target_next"]
    lo = full.loc[full.state == 0, "target_next"]
    if len(hi) < 4 or len(lo) < 4:
        return dict(signal=sig_name, sleeve=sleeve_name, n=n, n_hi=len(hi), n_lo=len(lo), verdict="TOO_FEW_OBS")
    real_diff = float(hi.mean() - lo.mean())
    nulls = block_permute_diff(full.state.values, full.target_next.values, block=6, n=1000)
    p = float((np.abs(nulls) >= abs(real_diff)).mean()) if len(nulls) >= 50 else np.nan
    plac95 = float(np.percentile(np.abs(nulls), 95)) if len(nulls) >= 50 else np.nan
    fixed_control = float(full.target_next.mean())
    bonferroni_pass = bool(np.isfinite(p) and p < 0.05 / 28)
    placebo_pass = bool(np.isfinite(p) and p < 0.05)
    if not placebo_pass:
        verdict = "DEAD"
    elif not bonferroni_pass:
        verdict = "SUGGESTIVE"
    else:
        verdict = "CANDIDATE_PRELIM"  # era-split + fixed-weight-beat checked separately
    return dict(signal=sig_name, sleeve=sleeve_name, n=n, n_hi=len(hi), n_lo=len(lo),
                mean_hi=round(float(hi.mean()), 3), mean_lo=round(float(lo.mean()), 3),
                real_diff=round(real_diff, 3), placebo95_abs=round(plac95, 3) if np.isfinite(plac95) else None,
                p_placebo=round(p, 4) if np.isfinite(p) else None, fixed_control_mean=round(fixed_control, 3),
                bonferroni_m28_pass=bonferroni_pass, verdict=verdict)


def era_split(sig_name, sig_monthly, sleeve_name, pnl_monthly):
    full = pd.DataFrame(index=pnl_monthly.index)
    full["target"] = pnl_monthly
    full["state"] = sig_monthly.reindex(full.index)
    full["target_next"] = full["target"].shift(-1)
    full = full.dropna(subset=["state", "target_next"])
    full["year"] = full.index.year
    eras = {"pre_2019": full.year < 2019, "y2019_2024": (full.year >= 2019) & (full.year < 2024),
            "y2024_plus": full.year >= 2024}
    rows = []
    for era, mask in eras.items():
        sub = full[mask]
        hi = sub.loc[sub.state == 1, "target_next"]
        lo = sub.loc[sub.state == 0, "target_next"]
        diff = float(hi.mean() - lo.mean()) if len(hi) >= 2 and len(lo) >= 2 else None
        rows.append(dict(signal=sig_name, sleeve=sleeve_name, era=era, n=len(sub),
                          n_hi=len(hi), n_lo=len(lo), diff=round(diff, 3) if diff is not None else None))
    return rows


def main():
    try:
        market, mkt_min, mkt_max = build_market_signals()
        log(f"market signals built {mkt_min.date()}..{mkt_max.date()}, {len(market)} rows")
        s6 = build_termstruct_signal()
        log(f"term structure signal built {s6.index.min().date()}..{s6.index.max().date()}, n={s6.notna().sum()}")

        market_m = market.resample("ME").last()
        s6_m = s6.resample("ME").last()
        market_m.index = market_m.index.to_period("M")
        s6_m.index = s6_m.index.to_period("M")

        sleeves = {
            "SWEEP_E": load_sweep("SWEEP_E", "trades_E_swing3_trail60_1lot.csv"),
            "SWEEP_D": load_sweep("SWEEP_D", "trades_D_overnight1_trail40_1lot.csv"),
            "CALENDAR_1x1_3d": load_calendar(),
            "S1F": load_s1f(),
        }
        for k, v in sleeves.items():
            log(f"sleeve {k}: n_months={len(v)} span {v.index.min()}..{v.index.max()}")

        signals = {**{c: market_m[c] for c in market_m.columns}, "S6_term_structure": s6_m}

        cell_rows, era_rows = [], []
        for sig_name, sig_series in signals.items():
            for sleeve_name, pnl in sleeves.items():
                own_dd = monthly_own_dd_state(pnl)
                cell_rows.append(run_cell(sig_name, sig_series, sleeve_name, pnl))
                era_rows.extend(era_split(sig_name, sig_series, sleeve_name, pnl))
            # own-drawdown signal handled once per sleeve below (not per market signal loop)

        for sleeve_name, pnl in sleeves.items():
            own_dd = monthly_own_dd_state(pnl)
            cell_rows.append(run_cell("S8_own_drawdown", own_dd, sleeve_name, pnl))
            era_rows.extend(era_split("S8_own_drawdown", own_dd, sleeve_name, pnl))

        cell_df = pd.DataFrame(cell_rows)
        era_df = pd.DataFrame(era_rows)
        cell_df.to_csv(OUT / "cell_results.csv", index=False)
        era_df.to_csv(OUT / "era_splits.csv", index=False)
        log(f"wrote cell_results.csv ({len(cell_df)} rows) and era_splits.csv ({len(era_df)} rows)")
        n_candidate = (cell_df.verdict == "CANDIDATE_PRELIM").sum() if "verdict" in cell_df else 0
        n_suggestive = (cell_df.verdict == "SUGGESTIVE").sum() if "verdict" in cell_df else 0
        n_dead = (cell_df.verdict == "DEAD").sum() if "verdict" in cell_df else 0
        log(f"VERDICT COUNTS: candidate_prelim={n_candidate} suggestive={n_suggestive} dead={n_dead} total={len(cell_df)}")
    except Exception:
        log("EXCEPTION:\n" + traceback.format_exc())
    finally:
        (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
