"""
Factor builders for the H010-H013 vol-family hypotheses (ALPHA_RANKER research loop).
Owner: worker agent, vol cat. Never touches weights — writes only via harness.run_experiment().

H010: low-vol anomaly       -> factor = -vol_252 (inverse realized vol; from panel, PIT)
H011: idiosyncratic vol     -> factor = -idio_vol_252 (inverse FF6-residual vol; from panel, PIT)
H012: downside beta / semidev -> computed from cube_close/cube_bench (panel has no downside-risk
                                 column); trailing 252d window ending at t, t-only info.
H013: vol term-structure    -> factor = vol_21 / vol_252 (contraction<1 vs expansion>1; from panel)

All factors are oriented so a HIGHER factor value = hypothesized HIGHER forward return (i.e. sign
flipped where the underlying construct is a risk metric), so the harness's un-signed IC_IR check
in verdict() doesn't spuriously KILL a real-but-inverted relationship.
"""
from pathlib import Path
import numpy as np
import pandas as pd

PANEL_DIR = Path(__file__).resolve().parent.parent / "panel"
CLOSE_PATH = PANEL_DIR / "cube_close.parquet"
BENCH_PATH = PANEL_DIR / "cube_bench.parquet"

MIN_TOTAL_OBS = 126   # min paired daily obs in the 252d window (matches panel's own beta_252 rule)
MIN_DOWN_OBS = 40     # min down-market-day obs for a stable downside beta


def build_h010_lowvol(panel: pd.DataFrame) -> pd.Series:
    """H010: low-vol anomaly. factor = -vol_252 (inverse trailing realized vol)."""
    f = panel[["date", "symbol", "vol_252"]].dropna(subset=["vol_252"]).copy()
    f["factor"] = -f["vol_252"]
    return f.set_index(["date", "symbol"])["factor"]


def build_h011_idiovol(panel: pd.DataFrame) -> pd.Series:
    """H011: idiosyncratic vol anomaly. factor = -idio_vol_252 (inverse FF6-residual vol)."""
    f = panel[["date", "symbol", "idio_vol_252"]].dropna(subset=["idio_vol_252"]).copy()
    f["factor"] = -f["idio_vol_252"]
    return f.set_index(["date", "symbol"])["factor"]


def build_h013_termstructure(panel: pd.DataFrame) -> pd.Series:
    """H013: vol term-structure. factor = vol_21/vol_252 (>1 = expansion, <1 = contraction).
    Sign is 'context' per backlog (regime-dependent) - no flip applied here; read
    regime_breakdown on the card rather than assuming a universal sign."""
    f = panel[["date", "symbol", "vol_21", "vol_252"]].dropna(subset=["vol_21", "vol_252"]).copy()
    f = f[f["vol_252"] > 0]
    f["factor"] = f["vol_21"] / f["vol_252"]
    return f.set_index(["date", "symbol"])["factor"]


def _load_cubes():
    close = pd.read_parquet(CLOSE_PATH)
    close.index = pd.to_datetime(close.index)
    bench = pd.read_parquet(BENCH_PATH)
    bench.index = pd.to_datetime(bench.index)
    # close (751 stocks) and bench (_NSEI) calendars differ by a handful of dates
    # (data-source artifact, not a real trading-day mismatch) -> intersect first
    # so downstream .loc[window_idx] never KeyErrors.
    common_idx = close.index.intersection(bench.index).sort_values()
    ret = close.loc[common_idx].pct_change()
    mkt_ret = bench.loc[common_idx].iloc[:, 0].pct_change()
    return ret, mkt_ret


def build_h012_downside(panel: pd.DataFrame) -> pd.Series:
    """H012: downside beta / semideviation composite.
    downside_beta_t   = cov(stock_ret, mkt_ret | mkt_ret<0) / var(mkt_ret | mkt_ret<0),
                        trailing 252d window ending at t (t-only info, no lookahead).
    semidev_t         = sqrt(252 * mean(min(stock_ret,0)^2)) over the same window (MAR=0).
    factor = -(zscore(downside_beta) + zscore(semidev)) averaged cross-sectionally per date,
    i.e. LOW downside-beta AND LOW downside-deviation -> HIGH factor (matches sign='-' hypothesis:
    downside risk predicts LOWER forward return, so we invert to keep IC sign convention positive
    if the anomaly holds).
    """
    ret, mkt_ret = _load_cubes()
    dates = sorted(panel["date"].unique())
    symbols = [c for c in ret.columns]

    rows = []
    for d in dates:
        d = pd.Timestamp(d)
        window_idx = ret.index[ret.index <= d]
        if len(window_idx) < MIN_TOTAL_OBS:
            continue
        window_idx = window_idx[-252:]
        r = ret.loc[window_idx]
        m = mkt_ret.loc[window_idx]
        down_mask = m < 0
        n_down = int(down_mask.sum())
        if n_down < MIN_DOWN_OBS:
            continue
        m_down = m[down_mask].values
        var_down = np.var(m_down, ddof=1)
        if var_down <= 0:
            continue

        r_valid_counts = r.notna().sum(axis=0)
        r_down = r.loc[down_mask]
        down_valid_counts = r_down.notna().sum(axis=0)

        # downside beta per symbol: cov(stock,mkt|down)/var(mkt|down)
        r_down_arr = r_down.values  # (n_down, n_sym)
        m_down_b = m_down.reshape(-1, 1)
        mean_r = np.nanmean(r_down_arr, axis=0, keepdims=True)
        mean_m = np.nanmean(m_down_b, axis=0, keepdims=True)
        cov = np.nanmean((r_down_arr - mean_r) * (m_down_b - mean_m), axis=0)
        down_beta = cov / var_down

        # semideviation (MAR=0) over full window
        r_full = r.values
        neg = np.minimum(r_full, 0.0)
        semidev = np.sqrt(252.0 * np.nanmean(neg ** 2, axis=0))

        valid = (r_valid_counts.values >= MIN_TOTAL_OBS) & (down_valid_counts.values >= MIN_DOWN_OBS)
        if valid.sum() < 20:
            continue

        df = pd.DataFrame({
            "symbol": symbols, "down_beta": down_beta, "semidev": semidev, "valid": valid
        })
        df = df[df["valid"]].drop(columns="valid")
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        if len(df) < 20:
            continue
        # cross-sectional z-score per date, then invert (low downside risk = high factor)
        for col in ("down_beta", "semidev"):
            mu, sd = df[col].mean(), df[col].std(ddof=1)
            df[col + "_z"] = 0.0 if sd == 0 or np.isnan(sd) else (df[col] - mu) / sd
        df["factor"] = -(df["down_beta_z"] + df["semidev_z"]) / 2.0
        df["date"] = d
        rows.append(df[["date", "symbol", "factor"]])

    if not rows:
        return pd.Series(dtype=float, name="factor")
    out = pd.concat(rows, ignore_index=True)
    return out.set_index(["date", "symbol"])["factor"]
