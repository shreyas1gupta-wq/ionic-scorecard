"""
122_ma_rsi_and_break.py -- Arjun Rao, 2026-07-30.

PART A: MA/RSI regime-conditional gate battery, extending REGIME_GATE_20260730 methodology
        (same placebo, same monthly resolution, +1 sleeve). Eval window 2019-03..2025-12,
        2026 held out entirely (Principal window instruction, mid-task).
PART B: Oct-2024 structural-break diagnostic on the SWEEP_E flagship + NIFTY microstructure.
        Full history used (NOT window-restricted); 2026 included.

Spec: MA_RSI_BREAK_20260730/PRE_REGISTRATION.md (written BEFORE this ran; do not edit after).
Self-contained, argument-free. Writes all outputs to MA_RSI_BREAK_20260730/.
Reads the full 1.05M-row nifty_1min.parquet -> queued per BACKTEST_QUEUE_20260730 architecture.
"""
from __future__ import annotations

import datetime as dt
import math
import traceback
from pathlib import Path

import numpy as np
import pandas as pd

rng = np.random.default_rng(20260730)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/MA_RSI_BREAK_20260730"
OUT.mkdir(parents=True, exist_ok=True)
LOG: list[str] = []


def log(msg):
    print(msg, flush=True)
    LOG.append(str(msg))


NIFTY_1MIN = ROOT / "intraday_options_strategy/datasets/processed/nifty_1min.parquet"
SWEEP_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SWEEP_11YR_20260729"
RATIO_CAL_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/RATIO_CALENDAR_20260730"
STACKED_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711"
SWING_DIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SWING_DELTA1_20260729"
INDICES_DIR = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/indices_close"

EVAL_START = pd.Period("2019-03", freq="M")
EVAL_END = pd.Period("2025-12", freq="M")
CUM_M_BEFORE = 410          # OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv row 10
N_NEW_CELLS = 56            # 14 signals x 4 sleeves
CUM_M_AFTER = CUM_M_BEFORE + N_NEW_CELLS
BONF_BAR = 0.05 / CUM_M_AFTER

LOT = 75
STT_OLD, STT_NEW = 0.0125 / 100, 0.020 / 100
BROK, EXCH, GST, STAMP, SEBI_CR = 20.0, 0.0019 / 100, 0.18, 0.002 / 100, 10.0
STT_SWITCH = dt.date(2024, 10, 1)
TRAIL_STOP_PTS = 60.0       # SWEEP_E = trades_E_swing3_trail60_1lot.csv


# ============================================================================ shared: NSE index closes
def load_market_daily():
    idxf = [pd.read_parquet(p) for p in sorted(INDICES_DIR.glob("indices_*.parquet"))]
    IC = pd.concat(idxf, ignore_index=True)
    IC["nm"] = IC["Index Name"].str.strip().str.upper()
    IC["date"] = pd.to_datetime(IC["file_date"])

    def series(nm):
        g = IC[IC.nm == nm].set_index("date").sort_index()
        s = pd.to_numeric(g["Closing Index Value"], errors="coerce")
        return s[~s.index.duplicated()]

    return series("NIFTY 50"), series("INDIA VIX")


def rsi_wilder(close: pd.Series, period: int) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out[avg_loss == 0] = 100.0
    out[avg_gain.isna() | avg_loss.isna()] = np.nan
    return out


def norm_cdf(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def nw_variance(x: np.ndarray, lags: int = 5) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.nan
    m = x.mean()
    d = x - m
    g0 = (d @ d) / n
    var = g0
    for L in range(1, min(lags, n - 1) + 1):
        gL = (d[L:] @ d[:-L]) / n
        var += 2 * (1 - L / (lags + 1)) * gL
    return max(var, 0.0)


def nw_tstat(x: np.ndarray, lags: int = 5) -> float:
    x = np.asarray(x, float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return np.nan
    m = x.mean()
    var = nw_variance(x, lags)
    if var <= 0:
        return np.nan
    return m / math.sqrt(var / n)


# ============================================================================ PART A signals
def build_ma_rsi_signals(nifty: pd.Series) -> pd.DataFrame:
    sig = {}
    mas = {n: nifty.rolling(n, min_periods=n).mean() for n in (10, 20, 65, 200)}
    for n in (10, 20, 65):
        s = (nifty > mas[n]).astype(float)
        s[mas[n].isna()] = np.nan
        sig[f"MA{n}_price_above"] = s
    for n in (10, 20, 65):
        slope = mas[n].pct_change(20)
        s = (slope > 0).astype(float)
        s[slope.isna()] = np.nan
        sig[f"MA{n}_slope_up"] = s
    cx1 = (mas[20] > mas[65]).astype(float)
    cx1[mas[20].isna() | mas[65].isna()] = np.nan
    sig["MA20_gt_MA65"] = cx1
    cx2 = (mas[65] > mas[200]).astype(float)
    cx2[mas[65].isna() | mas[200].isna()] = np.nan
    sig["MA65_gt_MA200"] = cx2
    for p in (5, 14, 28):
        r = rsi_wilder(nifty, p)
        os_ = (r < 30).astype(float)
        os_[r.isna()] = np.nan
        ob_ = (r > 70).astype(float)
        ob_[r.isna()] = np.nan
        sig[f"RSI{p}_oversold"] = os_
        sig[f"RSI{p}_overbought"] = ob_
    return pd.DataFrame(sig)


# ============================================================================ sleeve loaders
def load_sweep(tag, fname):
    d = pd.read_csv(SWEEP_DIR / fname)
    d["t"] = pd.to_datetime(d["t"])
    exit_ts = d["t"] + pd.to_timedelta(d["hold_min"], unit="m")
    d["exit_month"] = exit_ts.dt.to_period("M")
    m = d.groupby("exit_month")["net"].sum()
    m.name = tag
    return m


def load_calendar():
    d = pd.read_csv(RATIO_CAL_DIR / "grid_a_trades_raw.csv",
                     usecols=["exit_day", "strike_struct", "ratio", "exit_variant", "net_pts"])
    sub = d[(d.strike_struct == "ATM_ATM") & (d.ratio == "1x1") & (d.exit_variant == "3d_before")].copy()
    sub["exit_day"] = pd.to_datetime(sub["exit_day"])
    sub["exit_month"] = sub["exit_day"].dt.to_period("M")
    m = sub.groupby("exit_month")["net_pts"].sum()
    m.name = "CALENDAR_1x1_3d"
    return m


def load_s1f():
    d = pd.read_csv(STACKED_DIR / "book_daily_pnl.csv", index_col=0, parse_dates=True)
    s = d["s1f"]
    s.index = s.index.to_period("M")
    m = s.groupby(level=0).sum()
    m.name = "S1F"
    return m


def load_swing_priorweek():
    d = pd.read_csv(SWING_DIR / "all_trades.csv")
    sub = d[d.cell == "D_priorweek_sweep_long__fixed_10"].copy()
    sub["exit_date"] = pd.to_datetime(sub["exit_date"])
    sub["exit_month"] = sub["exit_date"].dt.to_period("M")
    m = sub.groupby("exit_month")["net"].sum()
    m.name = "SWING_priorweek_f10"
    return m


# ============================================================================ PART A: cell test
def block_permute_diff(states, targets, block=6, n=1000):
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


def run_cell_partA(sig_name, sig_monthly, sleeve_name, pnl_monthly_full):
    full = pd.DataFrame(index=pnl_monthly_full.index)
    full["target"] = pnl_monthly_full
    full["state"] = sig_monthly.reindex(full.index)
    full["target_next"] = full["target"].shift(-1)
    full["predicted_month"] = full.index + 1
    full = full.dropna(subset=["state", "target_next"])

    heldout = full[full["predicted_month"].astype(str).str.startswith("2026")]
    eval_df = full[(full["predicted_month"] >= EVAL_START) & (full["predicted_month"] <= EVAL_END)]
    n = len(eval_df)
    ho_hi = heldout.loc[heldout.state == 1, "target_next"]
    ho_lo = heldout.loc[heldout.state == 0, "target_next"]
    base = dict(signal=sig_name, sleeve=sleeve_name, n=n,
                heldout2026_n=int(len(heldout)),
                heldout2026_mean_hi=round(float(ho_hi.mean()), 3) if len(ho_hi) else None,
                heldout2026_mean_lo=round(float(ho_lo.mean()), 3) if len(ho_lo) else None)

    if n < 12:
        base["verdict"] = "UNDERPOWERED"
        return base
    hi = eval_df.loc[eval_df.state == 1, "target_next"]
    lo = eval_df.loc[eval_df.state == 0, "target_next"]
    if len(hi) < 4 or len(lo) < 4:
        base.update(n_hi=len(hi), n_lo=len(lo), verdict="UNDERPOWERED")
        return base

    real_diff = float(hi.mean() - lo.mean())
    nulls = block_permute_diff(eval_df.state.values, eval_df.target_next.values, block=6, n=1000)
    p = float((np.abs(nulls) >= abs(real_diff)).mean()) if len(nulls) >= 50 else np.nan
    plac95 = float(np.percentile(np.abs(nulls), 95)) if len(nulls) >= 50 else np.nan
    fixed_control = float(eval_df.target_next.mean())
    bonf_pass = bool(np.isfinite(p) and p < BONF_BAR)
    placebo_pass = bool(np.isfinite(p) and p < 0.05)

    # sign-flip check within the eval window: pre-Oct2024 (2019-03..2024-09) vs post (2024-10..2025-12)
    pm = eval_df["predicted_month"]
    pre = eval_df[pm <= pd.Period("2024-09", freq="M")]
    post = eval_df[pm >= pd.Period("2024-10", freq="M")]

    def _diff(sub):
        h = sub.loc[sub.state == 1, "target_next"]
        l = sub.loc[sub.state == 0, "target_next"]
        return float(h.mean() - l.mean()) if len(h) >= 2 and len(l) >= 2 else None

    diff_pre, diff_post = _diff(pre), _diff(post)
    sign_flip = (diff_pre is not None and diff_post is not None and
                 np.sign(diff_pre) != np.sign(diff_post) and diff_pre != 0 and diff_post != 0)

    if not placebo_pass:
        verdict = "DEAD"
    elif not bonf_pass:
        verdict = "SUGGESTIVE"
    elif sign_flip:
        verdict = "SUGGESTIVE_signflip"
    elif abs(real_diff) <= abs(fixed_control):
        verdict = "SUGGESTIVE_no_control_beat"
    else:
        verdict = "CANDIDATE"

    base.update(n_hi=len(hi), n_lo=len(lo), mean_hi=round(float(hi.mean()), 3),
                mean_lo=round(float(lo.mean()), 3), real_diff=round(real_diff, 3),
                placebo95_abs=round(plac95, 3) if np.isfinite(plac95) else None,
                p_placebo=round(p, 4) if np.isfinite(p) else None,
                fixed_control_mean=round(fixed_control, 3), cum_bonferroni_pass=bonf_pass,
                diff_pre_oct2024=round(diff_pre, 3) if diff_pre is not None else None,
                diff_post_oct2024=round(diff_post, 3) if diff_post is not None else None,
                sign_flip=bool(sign_flip), verdict=verdict)
    return base


# ============================================================================ PART B: 1-min data
def load_nifty_1min() -> pd.DataFrame:
    d = pd.read_parquet(NIFTY_1MIN, columns=["open", "high", "low", "close"])
    d = d[~d.index.duplicated()].sort_index()
    tod = d.index.time
    return d[(tod >= dt.time(9, 15)) & (tod <= dt.time(15, 30))]


def to_15min(spot: pd.DataFrame) -> pd.DataFrame:
    parts = []
    for _, day in spot.groupby(spot.index.date):
        r = day.resample("15min", origin=day.index[0], label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna()
        parts.append(r)
    return pd.concat(parts).sort_index()


def daily_bars(spot: pd.DataFrame) -> pd.DataFrame:
    g = spot.groupby(spot.index.date)
    d = g.agg(open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
    d.index = pd.to_datetime(d.index)
    return d


def era_of(d: dt.date) -> str:
    if d < dt.date(2019, 1, 1):
        return "pre_2019"
    if d < dt.date(2024, 10, 1):
        return "y2019_sep2024"
    if d < dt.date(2026, 1, 1):
        return "y_oct2024_2025"
    return "y2026_ytd"


ERA_ORDER = ["pre_2019", "y2019_sep2024", "y_oct2024_2025", "y2026_ytd"]


def sweep_reclaim_extended(bars15: pd.DataFrame) -> pd.DataFrame:
    """priorday_reclaim, VERBATIM entry logic from measure_signal_budget.py::sweep_signals,
    extended with penetration depth / bars-since-first-pierce / time-of-day (metrics only)."""
    daily_hi = bars15.groupby(bars15.index.date)["high"].max()
    daily_lo = bars15.groupby(bars15.index.date)["low"].min()
    days_sorted = sorted(daily_hi.index)
    prior_hi = {d: daily_hi[days_sorted[i - 1]] for i, d in enumerate(days_sorted) if i > 0}
    prior_lo = {d: daily_lo[days_sorted[i - 1]] for i, d in enumerate(days_sorted) if i > 0}
    rows = []
    for d, day in bars15.groupby(bars15.index.date):
        if d not in prior_hi:
            continue
        ph, pl = prior_hi[d], prior_lo[d]
        pierce_hi_since = pierce_lo_since = None
        for i, (t, row) in enumerate(day.iterrows()):
            hi, lo, close = row["high"], row["low"], row["close"]
            if hi > ph:
                if pierce_hi_since is None:
                    pierce_hi_since = i
                if close < ph:
                    rows.append({"t": t, "date": d, "dir": -1, "penetration": float(hi - ph),
                                 "level": float(ph), "bars_since_pierce": i - pierce_hi_since,
                                 "tod_min": (t.hour * 60 + t.minute) - 555})
                    pierce_hi_since = None
            else:
                pierce_hi_since = None
            if lo < pl:
                if pierce_lo_since is None:
                    pierce_lo_since = i
                if close > pl:
                    rows.append({"t": t, "date": d, "dir": 1, "penetration": float(pl - lo),
                                 "level": float(pl), "bars_since_pierce": i - pierce_lo_since,
                                 "tod_min": (t.hour * 60 + t.minute) - 555})
                    pierce_lo_since = None
            else:
                pierce_lo_since = None
    return pd.DataFrame(rows)


def part_b_sweep_mechanism(bars15, daily):
    ev = sweep_reclaim_extended(bars15)
    log(f"[partB] sweep priorday_reclaim events: {len(ev)}")
    ev["era"] = ev["date"].apply(era_of)
    d_close = daily["close"]
    d_range = (daily["high"] - daily["low"])
    d_index = daily.index

    def fwd_ret(date, sgn, n_days):
        dt_ts = pd.Timestamp(date)
        pos = d_index.searchsorted(dt_ts)
        if pos >= len(d_index) or d_index[pos] != dt_ts:
            return np.nan
        if pos + n_days >= len(d_index):
            return np.nan
        e = d_close.iloc[pos]
        px = d_close.iloc[pos + n_days]
        return sgn * (px / e - 1) * 100

    rows = []
    for era in ERA_ORDER:
        sub = ev[ev.era == era]
        n_days_era = len({d for d in daily.index.date if era_of(d) == era})
        n_months = max(n_days_era / 21.0, 1e-9)
        rec = {"era": era, "n_events": int(len(sub)),
               "events_per_month": round(len(sub) / n_months, 2),
               "mean_penetration_pts": round(float(sub["penetration"].mean()), 2) if len(sub) else None,
               "mean_bars_since_pierce": round(float(sub["bars_since_pierce"].mean()), 2) if len(sub) else None,
               "mean_tod_min_since_open": round(float(sub["tod_min"].mean()), 1) if len(sub) else None}
        for nd, lbl in [(1, "1d"), (3, "3d"), (5, "5d")]:
            if len(sub):
                fr = sub.apply(lambda r: fwd_ret(r["date"], r["dir"], nd), axis=1).dropna()
                rec[f"followthrough_{lbl}_signed_pct"] = round(float(fr.mean()), 4) if len(fr) else None
                rec[f"followthrough_{lbl}_hitrate"] = round(float((fr > 0).mean()), 4) if len(fr) else None
                rec[f"followthrough_{lbl}_n"] = int(len(fr))
                rec[f"followthrough_{lbl}_t_nw"] = round(nw_tstat(fr.values), 3) if len(fr) >= 10 else None
            else:
                rec[f"followthrough_{lbl}_signed_pct"] = None
        rows.append(rec)
    return pd.DataFrame(rows)


def avg_run_length(sign_seq: np.ndarray) -> float:
    s = sign_seq[sign_seq != 0]
    if len(s) < 2:
        return np.nan
    runs, cur = [], 1
    for i in range(1, len(s)):
        if s[i] == s[i - 1]:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    return float(np.mean(runs))


def variance_ratio(r: np.ndarray, q: int) -> float:
    r = r[np.isfinite(r)]
    n = len(r)
    if n < q * 10:
        return np.nan
    mu = r.mean()
    var1 = np.sum((r - mu) ** 2) / (n - 1)
    rq = pd.Series(r).rolling(q).sum().dropna().values
    m = len(rq)
    if m < 10:
        return np.nan
    varq = np.sum((rq - q * mu) ** 2) / (m - 1)
    return (varq / q) / var1 if var1 > 0 else np.nan


def part_b_persistence(daily, bars15, ma_signals_1min):
    dclose = daily["close"]
    dret = dclose.pct_change()
    daily["_era"] = [era_of(d.date()) for d in daily.index]
    intraday15 = []
    for _, day in bars15.groupby(bars15.index.date):
        c = day["close"]
        intraday15.append(pd.DataFrame({"ret": c.pct_change(), "date": day.index.date}))
    i15 = pd.concat(intraday15).dropna()
    i15["era"] = i15["date"].apply(era_of)

    rows = []
    for era in ERA_ORDER:
        mask = daily["_era"] == era
        r = dret[mask].dropna()
        rec = {"era": era, "n_days": int(mask.sum())}
        rec["daily_ret_autocorr_lag1"] = round(float(r.autocorr(1)), 4) if len(r) > 30 else None
        rec["vr5"] = round(variance_ratio(r.values, 5), 3) if len(r) > 60 else None
        rec["vr10"] = round(variance_ratio(r.values, 10), 3) if len(r) > 120 else None
        sign = np.sign(r.values)
        rec["avg_run_length_days"] = round(avg_run_length(sign), 2) if len(r) > 30 else None
        sub15 = i15[i15.era == era]["ret"]
        rec["min15_ret_autocorr_lag1"] = round(float(sub15.autocorr(1)), 4) if len(sub15) > 200 else None
        for n in (20, 65, 200):
            col = f"MA{n}_price_above"
            if col in ma_signals_1min.columns:
                s = ma_signals_1min.loc[ma_signals_1min.index.isin(daily.index[mask]), col].dropna()
                st = s.values * 2 - 1  # {0,1}->{-1,1}
                rec[f"avg_run_length_{col}"] = round(avg_run_length(st), 2) if len(st) > 30 else None
        rows.append(rec)
    daily.drop(columns=["_era"], inplace=True)
    return pd.DataFrame(rows)


def part_b_rsi_behavior(daily):
    dclose = daily["close"]
    fwd5 = dclose.shift(-5) / dclose - 1
    fwd10 = dclose.shift(-10) / dclose - 1
    eras = pd.Series([era_of(d.date()) for d in daily.index], index=daily.index)
    rows = []
    for p in (5, 14, 28):
        r = rsi_wilder(dclose, p)
        for era in ERA_ORDER:
            mask = eras == era
            rr = r[mask].dropna()
            os_mask = mask & (r < 30)
            ob_mask = mask & (r > 70)
            neu_mask = mask & (r >= 30) & (r <= 70)
            rows.append(dict(
                rsi_period=p, era=era, n=int(rr.shape[0]),
                pct_oversold=round(float((rr < 30).mean()), 4) if len(rr) else None,
                pct_overbought=round(float((rr > 70).mean()), 4) if len(rr) else None,
                rsi_p5=round(float(rr.quantile(0.05)), 1) if len(rr) else None,
                rsi_p50=round(float(rr.quantile(0.50)), 1) if len(rr) else None,
                rsi_p95=round(float(rr.quantile(0.95)), 1) if len(rr) else None,
                fwd5_ret_oversold_pct=round(float(fwd5[os_mask].dropna().mean() * 100), 3) if os_mask.sum() > 5 else None,
                fwd5_ret_overbought_pct=round(float(fwd5[ob_mask].dropna().mean() * 100), 3) if ob_mask.sum() > 5 else None,
                fwd5_ret_neutral_pct=round(float(fwd5[neu_mask].dropna().mean() * 100), 3) if neu_mask.sum() > 5 else None,
                fwd10_ret_oversold_pct=round(float(fwd10[os_mask].dropna().mean() * 100), 3) if os_mask.sum() > 5 else None,
                fwd10_ret_overbought_pct=round(float(fwd10[ob_mask].dropna().mean() * 100), 3) if ob_mask.sum() > 5 else None,
                n_oversold=int(os_mask.sum()), n_overbought=int(ob_mask.sum()),
            ))
    return pd.DataFrame(rows)


def part_b_vol_structure(daily, vix):
    dclose, dopen, dhigh, dlow = daily["close"], daily["open"], daily["high"], daily["low"]
    dret = dclose.pct_change()
    rv20 = dret.rolling(20, min_periods=20).std() * np.sqrt(252) * 100
    overnight = dopen / dclose.shift(1) - 1
    intraday = dclose / dopen - 1
    rng_pct = (dhigh - dlow) / dclose * 100
    rng_pts = (dhigh - dlow)
    eras = pd.Series([era_of(d.date()) for d in daily.index], index=daily.index)
    vix_al = vix.reindex(daily.index, method="ffill")

    rows = []
    for era in ERA_ORDER:
        mask = eras == era
        r = dret[mask].dropna()
        sq = (r ** 2)
        rows.append(dict(
            era=era, n_days=int(mask.sum()),
            realized_vol_20d_ann_pct_mean=round(float(rv20[mask].dropna().mean()), 2) if rv20[mask].notna().sum() else None,
            sq_ret_autocorr_lag1=round(float(sq.autocorr(1)), 4) if len(sq) > 30 else None,
            intraday_range_pct_of_close_mean=round(float(rng_pct[mask].dropna().mean()), 3),
            intraday_range_pts_mean=round(float(rng_pts[mask].dropna().mean()), 2),
            range_to_60pt_stop_ratio=round(float(rng_pts[mask].dropna().mean()) / TRAIL_STOP_PTS, 3),
            var_overnight=float(overnight[mask].dropna().var()),
            var_intraday=float(intraday[mask].dropna().var()),
            overnight_share_of_var=round(
                float(overnight[mask].dropna().var() /
                      (overnight[mask].dropna().var() + intraday[mask].dropna().var())), 3)
            if (overnight[mask].dropna().var() + intraday[mask].dropna().var()) > 0 else None,
            vix_mean=round(float(vix_al[mask].dropna().mean()), 2) if vix_al[mask].notna().sum() else None,
            vix_minus_rv_mean=round(float((vix_al[mask] - rv20[mask]).dropna().mean()), 2)
            if (vix_al[mask] - rv20[mask]).notna().sum() else None,
        ))
    return pd.DataFrame(rows)


def rt_cost(entry_px, exit_px, lots, stt_rate):
    qty = lots * LOT
    turn = (entry_px + exit_px) * qty
    brok = BROK * 2
    exch = EXCH * turn
    stt = stt_rate * exit_px * qty
    gst = GST * (brok + exch)
    stamp = STAMP * entry_px * qty
    sebi = SEBI_CR * turn / 1e7
    return brok + exch + stt + gst + stamp + sebi


def part_b_cost_and_power():
    d = pd.read_csv(SWEEP_DIR / "trades_E_swing3_trail60_1lot.csv")
    d["t"] = pd.to_datetime(d["t"])
    exit_ts = d["t"] + pd.to_timedelta(d["hold_min"], unit="m")
    d["exit_date"] = exit_ts.dt.date
    d["era"] = d["exit_date"].apply(era_of)

    post_all = d[d.era.isin(["y_oct2024_2025", "y2026_ytd"])].copy()
    log(f"[partB] trades_E post-Oct2024-all n={len(post_all)} "
        f"(motivating fact cites n=600 for post_Oct2024 window)")

    post_all["cost_counterfactual_stt_old"] = post_all.apply(
        lambda r: rt_cost(r["entry"], r["exit"], r["lots"], STT_OLD), axis=1)
    post_all["cost_actual_stt_new"] = post_all.apply(
        lambda r: rt_cost(r["entry"], r["exit"], r["lots"], STT_NEW), axis=1)
    stt_delta_rupees = float((post_all["cost_actual_stt_new"] - post_all["cost_counterfactual_stt_old"]).mean())
    stt_delta_pts = stt_delta_rupees / LOT

    mean_net_pre = float(d.loc[d.era == "y2019_sep2024", "net"].mean())
    mean_net_post = float(post_all["net"].mean())
    gap_rupees = mean_net_pre - mean_net_post
    pct_gap_explained_by_stt = (stt_delta_rupees / gap_rupees * 100) if gap_rupees != 0 else None

    cost_df = pd.DataFrame([{
        "era_reference": "y2019_sep2024", "n_reference": int((d.era == "y2019_sep2024").sum()),
        "mean_net_reference": round(mean_net_pre, 2),
        "n_post_all": int(len(post_all)), "mean_net_post_all": round(mean_net_post, 2),
        "gap_rupees_per_trade": round(gap_rupees, 2),
        "stt_only_delta_rupees_per_trade": round(stt_delta_rupees, 2),
        "stt_only_delta_pts_per_trade": round(stt_delta_pts, 3),
        "pct_gap_explained_by_stt": round(pct_gap_explained_by_stt, 1) if pct_gap_explained_by_stt is not None else None,
        "mean_cost_pts_reference_era": round(float(d.loc[d.era == "y2019_sep2024", "cost"].mean() / LOT), 3),
        "mean_cost_pts_post_all": round(float(post_all["cost_actual_stt_new"].mean() / LOT), 3),
    }])

    # ---- power calculation ----
    ref = d.loc[d.era == "y2019_sep2024", "net"].dropna()
    mu, sigma, n_ref = float(ref.mean()), float(ref.std(ddof=1)), len(ref)
    n_post = len(post_all)
    obs_mean_post = float(post_all["net"].mean())
    se = sigma / math.sqrt(n_post) if n_post > 0 else np.nan
    z = (obs_mean_post - mu) / se if se and np.isfinite(se) and se > 0 else np.nan
    p_one_sided = norm_cdf(z) if np.isfinite(z) else None

    # monthly-resolution cross-check with NW long-run variance
    monthly = d.groupby(pd.to_datetime(d.exit_date).values.astype("datetime64[M]"))["net"].sum()
    monthly.index = pd.to_datetime(monthly.index).to_period("M")
    monthly_era = monthly.index.map(lambda p: era_of(p.to_timestamp().date()))
    ref_m = monthly[monthly_era == "y2019_sep2024"]
    post_m = monthly[monthly_era.isin(["y_oct2024_2025", "y2026_ytd"])]
    mu_m = float(ref_m.mean())
    var_nw_m = nw_variance(ref_m.values, lags=5)
    n_m_ref = len(ref_m)
    n_m_post = len(post_m)
    obs_mean_post_m = float(post_m.mean()) if n_m_post else np.nan
    se_m = math.sqrt(var_nw_m / n_m_post) if var_nw_m and n_m_post > 0 else np.nan
    z_m = (obs_mean_post_m - mu_m) / se_m if se_m and np.isfinite(se_m) and se_m > 0 else np.nan
    p_m = norm_cdf(z_m) if np.isfinite(z_m) else None

    power_df = pd.DataFrame([{
        "level": "per_trade", "reference_era": "y2019_sep2024", "n_reference": n_ref,
        "mu_reference": round(mu, 2), "sigma_reference": round(sigma, 2),
        "n_observed": n_post, "observed_mean": round(obs_mean_post, 2),
        "z": round(z, 3) if np.isfinite(z) else None,
        "p_one_sided_leq_observed": round(p_one_sided, 5) if p_one_sided is not None else None,
        "note": "iid CLT approximation on trade-level net P&L; trades from a 3-day-swing "
                "strategy can overlap/cluster in time so this likely OVERSTATES effective n "
                "(understates the true p-value) -- see monthly cross-check below",
    }, {
        "level": "monthly_NW", "reference_era": "y2019_sep2024", "n_reference": n_m_ref,
        "mu_reference": round(mu_m, 2), "sigma_reference": round(math.sqrt(var_nw_m), 2) if var_nw_m else None,
        "n_observed": n_m_post, "observed_mean": round(obs_mean_post_m, 2) if n_m_post else None,
        "z": round(z_m, 3) if np.isfinite(z_m) else None,
        "p_one_sided_leq_observed": round(p_m, 5) if p_m is not None else None,
        "note": "monthly-aggregated net P&L, Newey-West (lag5) long-run variance on the "
                "reference era -- more defensible independence assumption than per-trade",
    }])
    return cost_df, power_df


# ============================================================================ main
def main():
    try:
        # ---------------- shared loads ----------------
        nifty, vix = load_market_daily()
        log(f"[shared] NSE NIFTY50/VIX daily {nifty.index.min().date()}..{nifty.index.max().date()}, n={len(nifty)}")
        ma_rsi_sig = build_ma_rsi_signals(nifty)
        log(f"[partA] built {ma_rsi_sig.shape[1]} MA/RSI signals on NSE NIFTY50 close")

        # ---------------- PART A ----------------
        sig_monthly = ma_rsi_sig.resample("ME").last()
        sig_monthly.index = sig_monthly.index.to_period("M")

        sleeves = {
            "SWEEP_E": load_sweep("SWEEP_E", "trades_E_swing3_trail60_1lot.csv"),
            "CALENDAR_1x1_3d": load_calendar(),
            "S1F": load_s1f(),
            "SWING_priorweek_f10": load_swing_priorweek(),
        }
        for k, v in sleeves.items():
            log(f"[partA] sleeve {k}: n_months={len(v)} span {v.index.min()}..{v.index.max()}")

        cellsA = []
        for sig_name in sig_monthly.columns:
            for sleeve_name, pnl in sleeves.items():
                cellsA.append(run_cell_partA(sig_name, sig_monthly[sig_name], sleeve_name, pnl))
        cellA_df = pd.DataFrame(cellsA)
        cellA_df.to_csv(OUT / "partA_cell_results.csv", index=False)
        log(f"[partA] wrote partA_cell_results.csv ({len(cellA_df)} rows, expect {N_NEW_CELLS})")
        vc = cellA_df["verdict"].value_counts().to_dict() if "verdict" in cellA_df else {}
        log(f"[partA] VERDICT COUNTS: {vc}")
        cellA_df.to_csv(OUT / "partA_era_splits.csv", index=False)  # sign-flip cols already embedded

        # ---------------- PART B ----------------
        log("[partB] loading nifty_1min.parquet (11.34y, ~1.05M rows)...")
        spot = load_nifty_1min()
        log(f"[partB] spot {len(spot):,} bars {spot.index[0]}..{spot.index[-1]}")
        bars15 = to_15min(spot)
        daily = daily_bars(spot)
        log(f"[partB] daily bars n={len(daily)}, 15min bars n={len(bars15)}")

        ma_signals_1min = build_ma_rsi_signals(daily["close"])[["MA20_price_above", "MA65_price_above"]].copy()
        ma200 = daily["close"].rolling(200, min_periods=200).mean()
        s200 = (daily["close"] > ma200).astype(float)
        s200[ma200.isna()] = np.nan
        ma_signals_1min["MA200_price_above"] = s200

        mech_df = part_b_sweep_mechanism(bars15, daily)
        mech_df.to_csv(OUT / "partB_sweep_mechanism.csv", index=False)
        log("[partB] wrote partB_sweep_mechanism.csv")

        pers_df = part_b_persistence(daily, bars15, ma_signals_1min)
        pers_df.to_csv(OUT / "partB_persistence.csv", index=False)
        log("[partB] wrote partB_persistence.csv")

        rsi_df = part_b_rsi_behavior(daily)
        rsi_df.to_csv(OUT / "partB_rsi_behavior.csv", index=False)
        log("[partB] wrote partB_rsi_behavior.csv")

        vol_df = part_b_vol_structure(daily, vix)
        vol_df.to_csv(OUT / "partB_vol_structure.csv", index=False)
        log("[partB] wrote partB_vol_structure.csv")

        cost_df, power_df = part_b_cost_and_power()
        cost_df.to_csv(OUT / "partB_cost_decomp.csv", index=False)
        power_df.to_csv(OUT / "partB_power_calc.csv", index=False)
        log("[partB] wrote partB_cost_decomp.csv and partB_power_calc.csv")
        log("[partB] POWER CALC (per_trade): " + power_df.iloc[0].to_json())
        log("[partB] POWER CALC (monthly_NW): " + power_df.iloc[1].to_json())

        log("DONE")
    except Exception:
        log("EXCEPTION:\n" + traceback.format_exc())
    finally:
        (OUT / "run_log.txt").write_text("\n".join(LOG), encoding="utf-8")


if __name__ == "__main__":
    main()
