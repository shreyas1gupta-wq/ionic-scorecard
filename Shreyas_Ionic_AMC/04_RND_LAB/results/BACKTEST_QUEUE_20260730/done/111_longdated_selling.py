"""
111_longdated_selling.py -- Long-dated / multi-week NIFTY premium-selling backtest.
Self-contained, argument-free (BACKTEST_QUEUE_20260730 contract). Writes its own outputs.

Pre-registration: Shreyas_Ionic_AMC/04_RND_LAB/results/LONGDATED_SELLING_20260730/PREREG.md
Do NOT tune anything here after results exist -- any change is a NEW pre-registration.

Owner: Vikram Shah (FM). Question: does selling a LONGER tenor LESS OFTEN beat a SHORTER
tenor MORE OFTEN, after real costs, risk-adjusted? Naked-10%-margin vs hedged-5%-margin?
Does the IV-percentile-high SELL gate (reversal finding, INVERSE_VRP_NICHE) help?
"""
from __future__ import annotations
import sys, time, json, bisect
import numpy as np, pandas as pd
from pathlib import Path
from scipy.stats import norm

t_start = time.time()

ROOT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BHAV_DIR = ROOT / "Shreyas_Ionic_AMC" / "05_DATA_OFFICE" / "data" / "fo_bhavcopy_hist"
OUT = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "LONGDATED_SELLING_20260730"
IV_CSV = ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "results" / "INVERSE_VRP_NICHE_20260729" / "daily_vol_series.csv"
SPOT_PARQUET = ROOT / "datasets" / "index_daily" / "nse_official_all_indices.parquet"
OUT.mkdir(parents=True, exist_ok=True)

def log(*a):
    print(*a, flush=True)

# ---------------------------------------------------------------- constants (pre-registered)
LOT = 75
R = 0.065                      # flat risk-free proxy [INFERENCE], matches firm convention
BROKERAGE_RS = 25.0            # Rs per lot per SIDE per leg-execution (SHARED_CONTEXT mandate)
SLIP_PT = 0.4                  # index points per side per leg-execution, always against us
WING_PCT = 0.03                # condor wing = short strike +/- ~3% of spot, dynamic
MARGIN_NAKED_PCT = 0.10
MARGIN_HEDGED_PCT = 0.05
STT_EXERCISE_PCT = 0.00125     # 0.125% of intrinsic, LONG legs only (COST_STANDARDS), see note below
STRIKE_TOL_FRAC = 0.07         # snap-to-liquid-strike tolerance vs target (7% of spot) else drop

TENORS = {  # name: (dte_lo, dte_hi, dte_target) -- bands match SHARED_CONTEXT liquidity table
    "biweekly": (7, 20, 12),
    "monthly": (20, 45, 30),
    "bimonthly": (45, 100, 60),
}
DELTAS = [0.10, 0.15, 0.25]
STRUCTURES = ["naked", "condor"]
MGMTS = ["hold", "buyback50", "stop2x"]

BUILD_END = pd.Timestamp("2023-12-31")
HELDOUT_START = pd.Timestamp("2024-01-01")
OVERALL_END = pd.Timestamp("2026-06-30")
IV_WIN_START = pd.Timestamp("2021-05-24")
IV_WIN_END = pd.Timestamp("2026-06-03")

# NOTE on exercise STT: NSE charges 0.125% of intrinsic on EXERCISE to the option BUYER/holder,
# not the writer. Our SHORT legs (writer side) never pay it directly -- the writer's cost is
# already the intrinsic cash settlement itself (modeled in the P&L). Only the CONDOR's WING
# legs (which we are LONG) can trigger this cost, and only if the wing itself finishes ITM
# (rare, since wings are ~3%+ OTM by construction) -- exactly a tail-event cost, applied below.

# ---------------------------------------------------------------- 1. load option chain 2011-2026
log("[1] loading NIFTY OPTIDX bhavcopy 2011-2026 ...")
opt_frames = []
for y in range(2011, 2027):
    p = BHAV_DIR / f"fo_idx_{y}.parquet"
    if not p.exists():
        log(f"    missing {p.name}, skip")
        continue
    df = pd.read_parquet(p, columns=["SYMBOL", "INSTRUMENT", "EXPIRY_DT", "STRIKE_PR",
                                       "OPTION_TYP", "CLOSE", "CONTRACTS", "TIMESTAMP"])
    df = df[(df.SYMBOL == "NIFTY") & (df.INSTRUMENT == "OPTIDX")]
    opt_frames.append(df)
opt = pd.concat(opt_frames, ignore_index=True)
opt["EXPIRY_DT"] = pd.to_datetime(opt["EXPIRY_DT"], format="mixed", dayfirst=True)
opt["TIMESTAMP"] = pd.to_datetime(opt["TIMESTAMP"], format="mixed", dayfirst=True)
opt["STRIKE_PR"] = opt["STRIKE_PR"].astype("float64")
opt["CONTRACTS"] = opt["CONTRACTS"].fillna(0).astype("float64")
opt["OPTION_TYP"] = opt["OPTION_TYP"].astype(str)
log(f"    {len(opt):,} NIFTY OPTIDX rows, {opt.EXPIRY_DT.nunique()} distinct expiries, "
    f"{opt.CONTRACTS.gt(0).mean():.1%} rows CONTRACTS>0")

by_strike = opt.set_index(["EXPIRY_DT", "OPTION_TYP", "STRIKE_PR", "TIMESTAMP"]).sort_index()[["CLOSE", "CONTRACTS"]]
by_day = opt.set_index(["EXPIRY_DT", "OPTION_TYP", "TIMESTAMP", "STRIKE_PR"]).sort_index()[["CLOSE", "CONTRACTS"]]
EXPIRIES = sorted(opt["EXPIRY_DT"].unique())
del opt_frames

# ---------------------------------------------------------------- 2. underlying / spot proxy
log("[2] building underlying spot proxy (official Nifty50 close 2016+, FUTIDX near-month pre-2016) ...")
sp = pd.read_parquet(SPOT_PARQUET, columns=["index_name", "date", "close"])
sp = sp[sp.index_name == "Nifty 50"][["date", "close"]].copy()
sp["date"] = pd.to_datetime(sp["date"])
sp = sp.rename(columns={"close": "S"}).set_index("date").sort_index()

fut_frames = []
for y in range(2011, 2016):
    p = BHAV_DIR / f"fo_idx_{y}.parquet"
    df = pd.read_parquet(p, columns=["SYMBOL", "INSTRUMENT", "EXPIRY_DT", "CLOSE", "TIMESTAMP"])
    df = df[(df.SYMBOL == "NIFTY") & (df.INSTRUMENT == "FUTIDX")]
    df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"], format="mixed", dayfirst=True)
    df["EXPIRY_DT"] = pd.to_datetime(df["EXPIRY_DT"], format="mixed", dayfirst=True)
    fut_frames.append(df)
fut = pd.concat(fut_frames, ignore_index=True)
fut = fut.sort_values(["TIMESTAMP", "EXPIRY_DT"])
near = fut[fut.EXPIRY_DT >= fut.TIMESTAMP].groupby("TIMESTAMP", as_index=False).first()
near = near[["TIMESTAMP", "CLOSE"]].rename(columns={"TIMESTAMP": "date", "CLOSE": "S"}).set_index("date")
spot = pd.concat([near[near.index < "2016-01-01"], sp]).sort_index()
spot = spot[~spot.index.duplicated(keep="last")]
SPOT = spot["S"]
log(f"    spot proxy: {len(SPOT)} days, {SPOT.index.min().date()}..{SPOT.index.max().date()} "
    f"({(SPOT.index < '2016-01-01').sum()} days on FUTIDX proxy, basis validated <1% typical, see PREREG)")

TRADING_DAYS = sorted(opt["TIMESTAMP"].unique()) if False else sorted(pd.Index(by_day.index.get_level_values("TIMESTAMP").unique()))
TRADING_DAYS = [d for d in TRADING_DAYS if d <= OVERALL_END]

# ---------------------------------------------------------------- 3. realized vol + no-lookahead pct
log("[3] trailing realized vol + expanding no-lookahead percentile (self-computed, full 2011-2026) ...")
logret = np.log(SPOT).diff()
rv20 = logret.rolling(20).std() * np.sqrt(252)
rv20 = rv20.shift(1)  # value known AT START of day t uses t-1..t-20 only

def expanding_pct_nolookahead(s: pd.Series, min_obs=60) -> pd.Series:
    vals = s.values
    hist = []
    out_pct = np.full(len(vals), np.nan)
    for i, v in enumerate(vals):
        if len(hist) >= min_obs and np.isfinite(v):
            lo = bisect.bisect_left(hist, v)
            hi = bisect.bisect_right(hist, v)
            out_pct[i] = 100.0 * (lo + hi) / 2.0 / len(hist)
        if np.isfinite(v):
            bisect.insort(hist, v)
    return pd.Series(out_pct, index=s.index)

RV_PCT = expanding_pct_nolookahead(rv20)
log(f"    rv20 valid {rv20.notna().sum()}, rv_pct valid {RV_PCT.notna().sum()}")

# ---------------------------------------------------------------- 4. IV-gate series (reused, not rebuilt)
log("[4] loading reused IV series (INVERSE_VRP_NICHE_20260729/daily_vol_series.csv) ...")
ivdf = pd.read_csv(IV_CSV, usecols=["day", "iv_pct"])
ivdf["day"] = pd.to_datetime(ivdf["day"])
IV_PCT = ivdf.set_index("day")["iv_pct"]
log(f"    {IV_PCT.notna().sum()} valid iv_pct rows, window {IV_PCT.index.min().date()}..{IV_PCT.index.max().date()}")

# ---------------------------------------------------------------- 5. BS helpers
def strike_for_target_delta(S, T, r, sigma, target_delta, is_call):
    if sigma <= 0 or T <= 0:
        return None
    if is_call:
        d1 = norm.ppf(target_delta)
    else:
        d1 = norm.ppf(1.0 + target_delta)
    lnSK = d1 * sigma * np.sqrt(T) - (r + 0.5 * sigma ** 2) * T
    return S * np.exp(-lnSK)

def nearest_liquid_strike(expiry, otype, day, target_K, min_strike=None, max_strike=None):
    try:
        sub = by_day.loc[(expiry, otype, day)]
    except KeyError:
        return None
    if isinstance(sub, pd.Series):  # single-row slice
        sub = sub.to_frame().T
    liquid = sub[sub["CONTRACTS"] > 0]
    if min_strike is not None:
        liquid = liquid[liquid.index > min_strike]
    if max_strike is not None:
        liquid = liquid[liquid.index < max_strike]
    if liquid.empty:
        return None
    diffs = np.abs(liquid.index.to_numpy() - target_K)
    return float(liquid.index[np.argmin(diffs)])

def expiry_is_tradeable(expiry, day, spot_today):
    try:
        sub = by_day.loc[(expiry, "CE", day)]
    except KeyError:
        return False
    if isinstance(sub, pd.Series):
        sub = sub.to_frame().T
    liquid = sub[sub["CONTRACTS"] > 0]
    if len(liquid) < 3:
        return False
    near_money = liquid[np.abs(liquid.index.to_numpy() - spot_today) <= 0.10 * spot_today]
    return len(near_money) > 0

def price_path(expiry, otype, strike, entry_day):
    try:
        s = by_strike.loc[(expiry, otype, strike)]
    except KeyError:
        return None
    s = s[(s.index > entry_day) & (s.index <= expiry)].sort_index()
    if s.empty:
        return None
    close_liquid = s["CLOSE"].where(s["CONTRACTS"] > 0)
    return pd.DataFrame({"close_ffill": close_liquid.ffill(), "contracts": s["CONTRACTS"]})

# ---------------------------------------------------------------- 6. entry-sequence per tenor
log("[5] building canonical entry sequences per tenor (independent of delta/structure/mgmt) ...")

def build_entry_sequence(band):
    lo, hi, target = band
    seq = []
    n = len(TRADING_DAYS)
    i = 0
    idx_of_day = {d: k for k, d in enumerate(TRADING_DAYS)}
    while i < n:
        day = TRADING_DAYS[i]
        if day > OVERALL_END - pd.Timedelta(days=lo):
            break
        spot_today = SPOT.get(day)
        if spot_today is None or not np.isfinite(spot_today):
            i += 1; continue
        cands = [e for e in EXPIRIES if lo <= (e - day).days <= hi]
        cands.sort(key=lambda e: abs((e - day).days - target))
        chosen = None
        for e in cands:
            if expiry_is_tradeable(e, day, spot_today):
                chosen = e; break
        if chosen is not None:
            seq.append((day, chosen))
            j = bisect.bisect_right(TRADING_DAYS, chosen)
            i = j
        else:
            i += 1
    return seq

entry_seqs = {name: build_entry_sequence(band) for name, band in TENORS.items()}
for name, seq in entry_seqs.items():
    log(f"    {name}: {len(seq)} entry cycles, {seq[0][0].date() if seq else None} .. "
        f"{seq[-1][0].date() if seq else None}")

# ---------------------------------------------------------------- 7. raw trade construction (18 combos)
log("[6] constructing raw trades per (tenor, delta, structure) -- 18 price-path passes ...")
raw_trades = {}  # (tenor, delta, structure) -> list of trade dicts
n_dropped = {"strike": 0, "wing": 0, "T": 0}

for tenor, seq in entry_seqs.items():
    for entry_day, expiry in seq:
        spot_entry = SPOT.get(entry_day)
        spot_expiry = SPOT.get(expiry)
        sigma = rv20.get(entry_day)
        T = (expiry - entry_day).days / 365.0
        if spot_entry is None or spot_expiry is None or sigma is None or not np.isfinite(sigma) or T <= 0:
            n_dropped["T"] += 1
            continue
        for target_delta in DELTAS:
            Kc_t = strike_for_target_delta(spot_entry, T, R, sigma, target_delta, True)
            Kp_t = strike_for_target_delta(spot_entry, T, R, sigma, -target_delta, False)
            Kc = nearest_liquid_strike(expiry, "CE", entry_day, Kc_t)
            Kp = nearest_liquid_strike(expiry, "PE", entry_day, Kp_t)
            if Kc is None or Kp is None or abs(Kc - Kc_t) / spot_entry > STRIKE_TOL_FRAC \
               or abs(Kp - Kp_t) / spot_entry > STRIKE_TOL_FRAC:
                n_dropped["strike"] += 1
                continue
            ce_path = price_path(expiry, "CE", Kc, entry_day)
            pe_path = price_path(expiry, "PE", Kp, entry_day)
            if ce_path is None or pe_path is None:
                n_dropped["strike"] += 1
                continue
            ce_entry_row = by_day.loc[(expiry, "CE", entry_day)]
            pe_entry_row = by_day.loc[(expiry, "PE", entry_day)]
            ce_entry_row = ce_entry_row.loc[[Kc]] if not isinstance(ce_entry_row, pd.Series) else ce_entry_row
            pe_entry_row = pe_entry_row.loc[[Kp]] if not isinstance(pe_entry_row, pd.Series) else pe_entry_row
            ce_entry_px = float(by_strike.loc[(expiry, "CE", Kc, entry_day), "CLOSE"])
            pe_entry_px = float(by_strike.loc[(expiry, "PE", Kp, entry_day), "CLOSE"])
            base = dict(tenor=tenor, delta=target_delta, entry_day=entry_day, expiry=expiry,
                        spot_entry=spot_entry, spot_expiry=spot_expiry, sigma=sigma,
                        Kc=Kc, Kp=Kp, ce_entry_px=ce_entry_px, pe_entry_px=pe_entry_px,
                        ce_path=ce_path, pe_path=pe_path)
            raw_trades.setdefault((tenor, target_delta, "naked"), []).append(base)

            # condor wings
            Kc_w = nearest_liquid_strike(expiry, "CE", entry_day, Kc * (1 + WING_PCT), min_strike=Kc)
            Kp_w = nearest_liquid_strike(expiry, "PE", entry_day, Kp * (1 - WING_PCT), max_strike=Kp)
            if Kc_w is None or Kp_w is None:
                n_dropped["wing"] += 1
                continue
            cew_path = price_path(expiry, "CE", Kc_w, entry_day)
            pew_path = price_path(expiry, "PE", Kp_w, entry_day)
            if cew_path is None or pew_path is None:
                n_dropped["wing"] += 1
                continue
            cew_entry_px = float(by_strike.loc[(expiry, "CE", Kc_w, entry_day), "CLOSE"])
            pew_entry_px = float(by_strike.loc[(expiry, "PE", Kp_w, entry_day), "CLOSE"])
            cbase = dict(base)
            cbase.update(Kc_w=Kc_w, Kp_w=Kp_w, cew_entry_px=cew_entry_px, pew_entry_px=pew_entry_px,
                         cew_path=cew_path, pew_path=pew_path)
            raw_trades.setdefault((tenor, target_delta, "condor"), []).append(cbase)

log(f"    dropped: {n_dropped}")
for k, v in raw_trades.items():
    log(f"    {k}: {len(v)} trades")

# ---------------------------------------------------------------- 8. cost helpers
def leg_cost_rs(n_legs, lot=LOT):
    """Rs cost for n_legs executed at once (brokerage + slippage, per side)."""
    return n_legs * (BROKERAGE_RS + SLIP_PT * lot)

def apply_management(mark_series, credit, mgmt):
    if mgmt == "hold" or mark_series is None or mark_series.empty:
        return None
    if mgmt == "buyback50":
        trig = mark_series[mark_series <= 0.5 * credit]
    elif mgmt == "stop2x":
        trig = mark_series[mark_series >= 2.0 * credit]
    else:
        return None
    if trig.empty:
        return None
    return trig.index[0], float(trig.iloc[0])

# ---------------------------------------------------------------- 9. simulate one (tenor,delta,structure,mgmt)
def simulate(tenor, delta, structure, mgmt):
    trades = raw_trades.get((tenor, delta, structure), [])
    out_rows = []
    for tr in trades:
        entry_day, expiry = tr["entry_day"], tr["expiry"]
        if structure == "naked":
            credit_pt = tr["ce_entry_px"] + tr["pe_entry_px"]
            mark = (tr["ce_path"]["close_ffill"] + tr["pe_path"]["close_ffill"]).dropna()
            n_legs_entry, n_legs_exit = 2, 2
            margin_rs = MARGIN_NAKED_PCT * tr["spot_entry"] * LOT
        else:
            credit_pt = (tr["ce_entry_px"] - tr["cew_entry_px"]) + (tr["pe_entry_px"] - tr["pew_entry_px"])
            ce_net = (tr["ce_path"]["close_ffill"] - tr["cew_path"]["close_ffill"])
            pe_net = (tr["pe_path"]["close_ffill"] - tr["pew_path"]["close_ffill"])
            mark = (ce_net + pe_net).dropna()
            n_legs_entry, n_legs_exit = 4, 4
            margin_rs = MARGIN_HEDGED_PCT * tr["spot_entry"] * LOT

        trig = apply_management(mark, credit_pt, mgmt)
        entry_cost_rs = leg_cost_rs(n_legs_entry)

        if trig is not None:
            exit_day, exit_mark_pt = trig
            pl_pt = credit_pt - exit_mark_pt
            pl_rs_gross = pl_pt * LOT
            exit_cost_rs = leg_cost_rs(n_legs_exit)
            pl_rs_net = pl_rs_gross - entry_cost_rs - exit_cost_rs
            exit_reason = mgmt
        else:
            exit_day = expiry
            Sx = tr["spot_expiry"]
            if structure == "naked":
                intr_c, intr_p = max(Sx - tr["Kc"], 0.0), max(tr["Kp"] - Sx, 0.0)
                pl_pt = credit_pt - (intr_c + intr_p)
                pl_rs_gross = pl_pt * LOT
                exit_cost_rs = leg_cost_rs(2)  # settlement handling, both short legs
                stt_rs = 0.0  # writer side, no exercise STT (see note above)
            else:
                intr_cs, intr_ps = max(Sx - tr["Kc"], 0.0), max(tr["Kp"] - Sx, 0.0)
                intr_cw, intr_pw = max(Sx - tr["Kc_w"], 0.0), max(tr["Kp_w"] - Sx, 0.0)
                pl_pt = credit_pt - ((intr_cs - intr_cw) + (intr_ps - intr_pw))
                pl_rs_gross = pl_pt * LOT
                exit_cost_rs = leg_cost_rs(4)
                # exercise STT: only on LONG wing legs finishing ITM (we are the buyer there)
                stt_rs = STT_EXERCISE_PCT * (intr_cw + intr_pw) * LOT
            pl_rs_net = pl_rs_gross - entry_cost_rs - exit_cost_rs - stt_rs
            exit_reason = "expiry_itm" if (pl_pt < credit_pt) else "expiry_otm"

        margin_ret = pl_rs_net / margin_rs if margin_rs > 0 else np.nan
        out_rows.append(dict(tenor=tenor, delta=delta, structure=structure, mgmt=mgmt,
                              entry_day=entry_day, exit_day=exit_day, expiry=expiry,
                              credit_pt=credit_pt, pl_rs_gross=pl_rs_gross, pl_rs_net=pl_rs_net,
                              margin_rs=margin_rs, margin_ret=margin_ret, exit_reason=exit_reason,
                              spot_entry=tr["spot_entry"], spot_expiry=tr["spot_expiry"]))
    return pd.DataFrame(out_rows)

log("[7] running 54 base configs (3 tenor x 3 delta x 2 structure x 3 mgmt) ...")
all_results = {}
for tenor in TENORS:
    for delta in DELTAS:
        for structure in STRUCTURES:
            for mgmt in MGMTS:
                df = simulate(tenor, delta, structure, mgmt)
                all_results[(tenor, delta, structure, mgmt)] = df
log(f"    done, {len(all_results)} configs, elapsed {time.time()-t_start:.0f}s")

# ---------------------------------------------------------------- 10. metrics
def newey_west_t(x, lag=None):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 5:
        return np.nan, n
    if lag is None:
        lag = max(1, int(4 * (n / 100) ** (2 / 9)))
    mean = x.mean()
    resid = x - mean
    gamma0 = np.sum(resid ** 2) / n
    lrv = gamma0
    for l in range(1, min(lag, n - 1) + 1):
        gamma_l = np.sum(resid[l:] * resid[:-l]) / n
        lrv += 2 * (1 - l / (lag + 1)) * gamma_l
    lrv = max(lrv, 1e-12)
    se = np.sqrt(lrv / n)
    return mean / se if se > 0 else np.nan, n

def perf_metrics(df, ret_col="margin_ret", pl_col="pl_rs_net", label=""):
    if df.empty:
        return dict(label=label, n=0)
    df = df.sort_values("exit_day")
    rets = df[ret_col].values
    nav = np.cumprod(1 + np.nan_to_num(rets, nan=0.0))
    span_days = max((df["exit_day"].max() - df["entry_day"].min()).days, 1)
    years = span_days / 365.25
    cagr = nav[-1] ** (1 / years) - 1 if years > 0 and nav[-1] > 0 else np.nan
    run_max = np.maximum.accumulate(nav)
    dd = nav / run_max - 1
    maxdd = dd.min() if len(dd) else np.nan
    calmar = cagr / abs(maxdd) if maxdd and maxdd < 0 else np.nan
    trades_per_year = len(df) / years if years > 0 else np.nan
    sharpe = (np.nanmean(rets) / np.nanstd(rets)) * np.sqrt(trades_per_year) if np.nanstd(rets) > 0 else np.nan
    wins = df[df.pl_rs_net > 0]["pl_rs_net"].sum() if pl_col in df else np.nan
    losses = -df[df.pl_rs_net < 0]["pl_rs_net"].sum() if pl_col in df else np.nan
    pf = wins / losses if losses and losses > 0 else np.nan
    t_stat, n_t = newey_west_t(df[pl_col].values)
    monthly = df.set_index("exit_day")[pl_col].resample("ME").sum()
    win_rate_m = (monthly > 0).mean() if len(monthly) else np.nan
    worst_day_rs = df[pl_col].min()
    worst_day_pct_margin = (df[pl_col] / df["margin_rs"]).min()
    worst_month = monthly.min() if len(monthly) else np.nan
    worst_month_pct = (monthly / df.set_index("exit_day")["margin_rs"].resample("ME").mean()).min() if len(monthly) else np.nan
    return dict(label=label, n=len(df), cagr=cagr, maxdd=maxdd, calmar=calmar, sharpe=sharpe,
                pf=pf, nw_t=t_stat, win_rate_monthly=win_rate_m, worst_day_rs=worst_day_rs,
                worst_day_pct_margin=worst_day_pct_margin, worst_month_rs=worst_month,
                worst_month_pct_margin=worst_month_pct, trades_per_year=trades_per_year,
                span_start=str(df.entry_day.min().date()), span_end=str(df.exit_day.max().date()))

# ---------------------------------------------------------------- 11. build/held-out split + summary table
log("[8] computing build/held-out metrics for all 54 configs ...")
summary_rows = []
for key, df in all_results.items():
    tenor, delta, structure, mgmt = key
    build = df[df.exit_day <= BUILD_END]
    held = df[df.entry_day >= HELDOUT_START]
    gross_m = perf_metrics(build, ret_col="margin_ret", pl_col="pl_rs_gross", label="build_gross")
    net_m = perf_metrics(build, ret_col="margin_ret", pl_col="pl_rs_net", label="build_net")
    held_net_m = perf_metrics(held, ret_col="margin_ret", pl_col="pl_rs_net", label="held_net")
    held_gross_m = perf_metrics(held, ret_col="margin_ret", pl_col="pl_rs_gross", label="held_gross")
    summary_rows.append(dict(tenor=tenor, delta=delta, structure=structure, mgmt=mgmt,
                              **{f"build_net_{k}": v for k, v in net_m.items() if k != "label"},
                              **{f"build_gross_cagr": gross_m.get("cagr"), "build_gross_pf": gross_m.get("pf"),
                                 "build_gross_winrate_m": gross_m.get("win_rate_monthly")},
                              **{f"held_net_{k}": v for k, v in held_net_m.items() if k != "label"},
                              **{f"held_gross_cagr": held_gross_m.get("cagr"), "held_gross_pf": held_gross_m.get("pf"),
                                 "held_gross_winrate_m": held_gross_m.get("win_rate_monthly")}))
summary = pd.DataFrame(summary_rows)
summary.to_csv(OUT / "config_grid_summary.csv", index=False)
log(f"    wrote config_grid_summary.csv ({len(summary)} rows)")

# best config by BUILD-window net Sharpe (tie-break Calmar), pre-registered rule
valid = summary[summary.build_net_n >= 20].copy()
valid = valid.sort_values(["build_net_sharpe", "build_net_calmar"], ascending=False)
best = valid.iloc[0] if len(valid) else summary.sort_values("build_net_n", ascending=False).iloc[0]
best_key = (best.tenor, best.delta, best.structure, best.mgmt)
log(f"    BEST base config by build-window net Sharpe: {best_key} "
    f"(sharpe={best.get('build_net_sharpe')}, calmar={best.get('build_net_calmar')})")

# ---------------------------------------------------------------- 12. overlays on best config (+3 trials)
log("[9] overlay tests on best config: IV-gate, RV-skip, both stacked ...")
best_df = all_results[best_key].copy()
best_df["iv_pct_entry"] = best_df["entry_day"].map(IV_PCT)
best_df["rv_pct_entry"] = best_df["entry_day"].map(RV_PCT)

iv_window = best_df[(best_df.entry_day >= IV_WIN_START) & (best_df.entry_day <= IV_WIN_END)]
overlay_rows = []
overlay_rows.append(dict(overlay="baseline_in_iv_window",
                          **perf_metrics(iv_window, pl_col="pl_rs_net", label="baseline_in_iv_window")))
iv_gated = iv_window[iv_window.iv_pct_entry >= 90]
overlay_rows.append(dict(overlay="iv_gate_top_decile",
                          **perf_metrics(iv_gated, pl_col="pl_rs_net", label="iv_gate_top_decile")))
rv_skipped = best_df[(best_df.rv_pct_entry < 90) | best_df.rv_pct_entry.isna()]
overlay_rows.append(dict(overlay="rv_regime_skip_full_period",
                          **perf_metrics(rv_skipped, pl_col="pl_rs_net", label="rv_regime_skip_full_period")))
both = iv_window[(iv_window.iv_pct_entry >= 90) & ((iv_window.rv_pct_entry < 90) | iv_window.rv_pct_entry.isna())]
overlay_rows.append(dict(overlay="iv_gate_AND_rv_skip",
                          **perf_metrics(both, pl_col="pl_rs_net", label="iv_gate_AND_rv_skip")))
overlay_df = pd.DataFrame(overlay_rows)
overlay_df.to_csv(OUT / "overlay_tests.csv", index=False)
log(f"    wrote overlay_tests.csv\n{overlay_df.to_string()}")

# ---------------------------------------------------------------- 13. tail / era slices on best config
log("[10] tail and era-slice reporting on best config (descriptive, not selected on) ...")
era_windows = {
    "2015-16": ("2015-01-01", "2016-12-31"),
    "2018": ("2018-01-01", "2018-12-31"),
    "2020_covid": ("2020-01-01", "2020-12-31"),
    "2024-09": ("2024-08-15", "2024-10-31"),
}
era_rows = []
for name, (s, e) in era_windows.items():
    sub = best_df[(best_df.exit_day >= s) & (best_df.exit_day <= e)]
    era_rows.append(dict(era=name, n=len(sub), gross_rs=sub.pl_rs_gross.sum() if len(sub) else np.nan,
                          net_rs=sub.pl_rs_net.sum() if len(sub) else np.nan,
                          worst_trade_rs=sub.pl_rs_net.min() if len(sub) else np.nan,
                          worst_trade_pct_margin=(sub.pl_rs_net / sub.margin_rs).min() if len(sub) else np.nan))
era_df = pd.DataFrame(era_rows)
era_df.to_csv(OUT / "era_slices_best_config.csv", index=False)
log(f"    wrote era_slices_best_config.csv\n{era_df.to_string()}")

best_df.to_csv(OUT / "best_config_trades.csv", index=False)
for key, df in all_results.items():
    pass  # full per-config trade dumps skipped to keep output lean; summary.csv has the metrics

# save ALL raw trades for the full grid too, compactly (for later audit / DSR-PBO)
all_trades_rows = []
for key, df in all_results.items():
    if df.empty:
        continue
    d = df.copy()
    d["tenor"], d["delta"], d["structure"], d["mgmt"] = key
    all_trades_rows.append(d)
if all_trades_rows:
    pd.concat(all_trades_rows, ignore_index=True).to_csv(OUT / "all_trades_full_grid.csv", index=False)
    log("    wrote all_trades_full_grid.csv")

# ---------------------------------------------------------------- 14. trials ledger entries
trials = []
for key in all_results:
    trials.append(dict(family="longdated_selling_20260730", config=str(key), n_trials_component=1))
for row in overlay_rows:
    trials.append(dict(family="longdated_selling_20260730", config=f"overlay:{row['overlay']}", n_trials_component=1))
trials_df = pd.DataFrame(trials)
trials_df.to_csv(OUT / "trials_this_arm.csv", index=False)
log(f"    TOTAL TRIALS THIS ARM: {len(trials_df)} (pre-registered as 57 in PREREG.md)")

meta = dict(elapsed_seconds=round(time.time() - t_start, 1), n_configs=len(all_results),
            best_config=str(best_key), trading_days=len(TRADING_DAYS),
            expiries=len(EXPIRIES), dropped=n_dropped)
(OUT / "run_meta.json").write_text(json.dumps(meta, indent=2, default=str), encoding="utf-8")
log(f"[DONE] {json.dumps(meta, default=str)}")
