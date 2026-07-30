"""VOL-SELLING BENCHMARK, trend/signal-filtered — pre-registered in PRE_REGISTRATION.md.

Weekly NIFTY short strangle (naked) / iron condor (defined-risk), delta-based strikes,
buy-back-at-50%-credit / 2x-credit-stop management, real 1-min option prices, cash-settled
at intrinsic on expiry (no LANDMINE #9). 16 configs (2 structures x 8 filters) x
{BUILD 2021-05..2025-12, HELD-OUT FWD 2026 H1}.

Costs: Rs25/lot/side brokerage + 0.4% per-leg slippage (SHARED_CONTEXT mandate).
Margin (Principal ruling 2026-07-29 22:56): naked strangle 10% of notional, hedged condor
5% of notional, both DYNAMIC (spot-scaled), applied once per whole position (not per leg).

Reuses verbatim: chain.py (data access), options/bs_pricing.py (BS greeks/IV), and the
sweep/round-number signal functions from EMA_INTRADAY_BUYING_20260729/signal_budget/
measure_signal_budget.py (same trigger definitions the session already validated).
"""
from __future__ import annotations

import datetime as dt
import gc
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
BUY = ROOT / "intraday_options_strategy" / "buying"
sys.path.insert(0, str(BUY))
sys.path.insert(0, str(BUY.parent))
from options.bs_pricing import bs_greeks, implied_vol  # noqa: E402
import chain  # noqa: E402
from engine import STEP  # noqa: E402  (=50)

SIGDIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/EMA_INTRADAY_BUYING_20260729/signal_budget"
STAGE1DIR = SIGDIR.parent
sys.path.insert(0, str(SIGDIR))
sys.path.insert(0, str(STAGE1DIR))
from measure_signal_budget import sweep_signals, round_number_levels  # noqa: E402
from stage1_signal_test import nw_tstat  # noqa: E402

OUT = Path(__file__).parent

# ---------------------------------------------------------------------------
# constants (pre-registered, not tuned after seeing results)
# ---------------------------------------------------------------------------
LOT = 75
R_, Q_ = 0.065, 0.012
BROK_PER_LOT_SIDE = 25.0          # Rs, mandate cost model
SLIP_FRAC = 0.004                 # per-leg slippage, frac of that leg's own premium
TARGET_DTE, MIN_DTE, MAX_DTE = 3, 2, 5
SHORT_DELTA, WING_DELTA = 0.18, 0.08
TARGET_FRAC, STOP_MULT = 0.50, 2.0
ENTRY_HH, ENTRY_MM = 9, 20
EXIT_HH, EXIT_MM = 15, 15
BUILD_START, BUILD_END = dt.date(2021, 5, 24), dt.date(2025, 12, 31)
FWD_START, FWD_END = dt.date(2026, 1, 1), dt.date(2026, 6, 30)
CAP0, DEPLOY = 1_000_000.0, 0.75
MARGIN_RATE = {"short_strangle": 0.10, "iron_condor": 0.05}
S1F_BENCH = dict(CAGR=12.57, maxDD=-4.44, Calmar=2.83, Sharpe=2.15, PF=2.21, n=204, win=74.0)

STEP_MIN = 5  # position-value check granularity (minutes) for target/stop scanning


NEEDED_COLS = ["timestamp", "open", "close", "strike", "option_type", "trading_day"]


def load_expiry_light(path):
    """Memory-frugal replacement for chain.load_expiry() for this single-pass loop:
    column-projected read (drops symbol/expiry/high/low/volume/open_interest, none of
    which this engine uses), no lru_cache (each file is touched exactly once here, so
    caching only holds memory that will never be reused again)."""
    tbl = pq.read_table(path, columns=NEEDED_COLS)
    df = tbl.to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df.drop(columns=["timestamp"], inplace=True)
    df["option_type"] = df["option_type"].astype("category")
    df["trading_day"] = df["trading_day"].astype(str)
    df = df.drop_duplicates(["t", "strike", "option_type"])
    return df


def brok_pts_per_leg():
    return BROK_PER_LOT_SIDE / LOT


def yte(t0, exp):
    ex = pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)
    return max((ex - t0).total_seconds() / (365.25 * 24 * 3600), 1e-5)


def pick_delta(s0, T, iv, target, otype, avail):
    is_call = otype == "CE"
    best, bd = None, 9e9
    for k in avail:
        d = abs(float(bs_greeks(s0, k, T, iv, R_, Q_, is_call)["delta"]))
        if abs(d - target) < bd:
            bd, best = abs(d - target), k
    return best


def _leg(df, k, o):
    s = df[(df["strike"] == k) & (df["option_type"] == o)]
    return s.set_index("t")["close"].sort_index()


def _leg_open_at(df, k, o, t0):
    s = df[(df["strike"] == k) & (df["option_type"] == o)].set_index("t").sort_index()
    a = s[s.index >= t0]
    return a["open"].iloc[0] if not a.empty else np.nan


# ---------------------------------------------------------------------------
# 1. day-level filter flags (all D-1, PIT-safe)
# ---------------------------------------------------------------------------
def build_day_flags(spot):
    print("[flags] building 15-min bars + signal flags ...", flush=True)
    o = spot["open"].resample("15min").first()
    h = spot["high"].resample("15min").max()
    l = spot["low"].resample("15min").min()
    c = spot["close"].resample("15min").last()
    bars15 = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()
    bars15 = bars15[(bars15.index.time >= dt.time(9, 15)) & (bars15.index.time <= dt.time(15, 30))]

    sweeps = sweep_signals(bars15)
    _, rn_rej = round_number_levels(bars15)

    def day_set(df):
        return set(pd.to_datetime(df["t"]).dt.date) if (df is not None and not df.empty) else set()

    reclaim_days = day_set(sweeps.get("intraday_reclaim"))
    pd_continue_days = day_set(sweeps.get("priorday_continue"))
    round_reject_days = day_set(rn_rej)

    # trend veto: S1-F F1/F2 style, computed off the SAME spot source (HF 1-min), stated assumption
    dcl = spot["close"].groupby(spot.index.date).last()
    dcl.index = pd.to_datetime(dcl.index)
    d = dcl.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 5, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 5, adjust=False).mean()
    rsi5 = (100 - 100 / (1 + up / dn))
    pret = dcl.pct_change() * 100
    trend_veto_by_day = ((rsi5 >= 80) | (rsi5 <= 20) | (pret.abs() > 1.5)).to_dict()  # keyed by D's OWN day

    trading_days = sorted(dcl.index.date)
    prev_day = {trading_days[i]: trading_days[i - 1] for i in range(1, len(trading_days))}

    flags = {}
    for d_ in trading_days:
        p = prev_day.get(d_)
        if p is None:
            continue
        flags[d_] = {
            "reclaim": p in reclaim_days,
            "round_reject": p in round_reject_days,
            "pd_continue": p in pd_continue_days,
            "trend_veto": bool(trend_veto_by_day.get(pd.Timestamp(p), False)),
        }
    n_days = len(flags)
    print(f"[flags] {n_days} entry-days flagged. reclaim={sum(f['reclaim'] for f in flags.values())} "
          f"({sum(f['reclaim'] for f in flags.values())/n_days:.1%}), "
          f"round_reject={sum(f['round_reject'] for f in flags.values())} "
          f"({sum(f['round_reject'] for f in flags.values())/n_days:.1%}), "
          f"pd_continue={sum(f['pd_continue'] for f in flags.values())} "
          f"({sum(f['pd_continue'] for f in flags.values())/n_days:.1%}), "
          f"trend_veto={sum(f['trend_veto'] for f in flags.values())} "
          f"({sum(f['trend_veto'] for f in flags.values())/n_days:.1%})", flush=True)
    return flags


# ---------------------------------------------------------------------------
# 2. per-expiry base trade (both structures), cost/gross/net all computed here
# ---------------------------------------------------------------------------
def build_structure_trade(df, exp, entry_day, et, s0, T, iv, avail, structure):
    if structure == "short_strangle":
        ksp = pick_delta(s0, T, iv, SHORT_DELTA, "PE", avail)
        ksc = pick_delta(s0, T, iv, SHORT_DELTA, "CE", avail)
        legs = [(ksp, "PE", +1), (ksc, "CE", +1)]
    else:  # iron_condor
        ksp = pick_delta(s0, T, iv, SHORT_DELTA, "PE", avail)
        ksc = pick_delta(s0, T, iv, SHORT_DELTA, "CE", avail)
        kbp = pick_delta(s0, T, iv, WING_DELTA, "PE", avail)
        kbc = pick_delta(s0, T, iv, WING_DELTA, "CE", avail)
        kbp = min(kbp, ksp - STEP)
        kbc = max(kbc, ksc + STEP)
        legs = [(ksp, "PE", +1), (ksc, "CE", +1), (kbp, "PE", -1), (kbc, "CE", -1)]

    entry_px = {}
    for k, o, s in legs:
        px = _leg_open_at(df, k, o, et)
        if not np.isfinite(px):
            return None
        entry_px[(k, o)] = px
    sell_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == 1)
    buy_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == -1)
    credit = sell_prem - buy_prem
    if credit <= 0:
        return None

    fill_credit, entry_brok_pts = 0.0, 0.0
    for k, o, s in legs:
        px = entry_px[(k, o)]
        slip = SLIP_FRAC * px
        fill_px = (px - slip) if s == 1 else (px + slip)
        fill_credit += s * fill_px
        entry_brok_pts += brok_pts_per_leg()
    if fill_credit <= 0:
        return None

    series = {(k, o, side): _leg(df, k, o) for k, o, side in legs}
    idx = series[legs[0]].index
    idx = idx[idx >= et]
    if len(idx) < 2:
        return None

    def val_at(t):
        v = 0.0
        for k, o, side in legs:
            s = series[(k, o, side)]
            sub = s[s.index <= t]
            if sub.empty:
                return np.nan
            v += side * sub.iloc[-1]
        return v

    if structure == "short_strangle":
        max_loss_per_lot = np.nan
    else:
        put_w = abs(legs[0][0] - legs[2][0])
        call_w = abs(legs[1][0] - legs[3][0])
        max_loss_per_lot = (max(put_w, call_w) - fill_credit) * LOT

    tgt = fill_credit * (1 - TARGET_FRAC)
    stop_v = fill_credit * STOP_MULT
    exit_t = exit_v = reason = None
    pts = list(idx)[::STEP_MIN]
    for t in pts:
        if t <= et:
            continue
        d_ = t.date()
        eod = pd.Timestamp(d_) + pd.Timedelta(hours=EXIT_HH, minutes=EXIT_MM)
        v = val_at(t)
        if not np.isfinite(v):
            continue
        if d_ >= exp and t >= eod:
            exit_t, reason = t, "expiry"     # value re-derived from intrinsic below
            break
        if v <= tgt:
            exit_t, exit_v, reason = t, v, "target"
            break
        if v >= stop_v:
            exit_t, exit_v, reason = t, v, "stop"
            break
    if exit_t is None:
        # exhausted the series without reaching the expiry-day flat cutoff (data ran out early)
        exit_t, exit_v, reason = idx[-1], val_at(idx[-1]), "eod"

    if reason == "expiry":
        s1 = spot_close_on(exp)
        if s1 is None:
            return None
        v = 0.0
        for k, o, side in legs:
            intr = max(0.0, (k - s1) if o == "PE" else (s1 - k))
            v += side * intr
        exit_v = max(v, 0.0)
        exit_brok_pts = 0.0  # worthless/intrinsic settle -> no closing order placed
        fill_close = exit_v  # cash settlement at exact intrinsic, no slippage
    else:
        exit_v = max(exit_v, 0.0)
        n_legs = len(legs)
        exit_brok_pts = brok_pts_per_leg() * n_legs
        fill_close = exit_v * (1 + SLIP_FRAC) if exit_v > 0 else 0.0

    close_prem = exit_v
    gross_pnl = (credit - close_prem) * LOT                      # zero-cost, raw mid prices
    cost_rs = (entry_brok_pts + exit_brok_pts) * LOT
    net_pnl = (fill_credit - fill_close) * LOT - cost_rs

    return {
        "credit": credit, "fill_credit": fill_credit, "close_prem": close_prem,
        "fill_close": fill_close, "reason": reason, "gross_pnl": gross_pnl,
        "cost_rs": cost_rs, "net_pnl": net_pnl, "max_loss_per_lot": max_loss_per_lot,
        "hold_days": (exit_t.date() - entry_day).days, "n_legs": len(legs), "spot0": s0,
    }


_SPOT_DAILY_CLOSE = {}


def spot_close_on(day):
    return _SPOT_DAILY_CLOSE.get(day)


def build_base_trades(spot, day_flags):
    global _SPOT_DAILY_CLOSE
    dcl = spot["close"].groupby(spot.index.date).last()
    _SPOT_DAILY_CLOSE = dcl.to_dict()

    mapping, exps = chain.build_expiry_index()
    rows = []
    n_ok = n_skip_data = 0
    for i, exp in enumerate(exps):
        if i % 20 == 0:
            print(f"[trades] expiry {i}/{len(exps)} ({exp}) ...", flush=True)
            gc.collect()
        try:
            df = load_expiry_light(mapping[exp])
        except Exception as e:
            print(f"  [skip] {exp}: load error {type(e).__name__}: {e}", flush=True)
            n_skip_data += 1
            continue
        tdays = sorted(df["trading_day"].unique())
        entry_day = None
        for td in tdays:
            d_ = dt.date.fromisoformat(td)
            if MIN_DTE <= (exp - d_).days <= MAX_DTE:
                entry_day = d_
                if (exp - d_).days <= TARGET_DTE:
                    break
        if entry_day is None:
            n_skip_data += 1
            continue
        et = pd.Timestamp(entry_day) + pd.Timedelta(hours=ENTRY_HH, minutes=ENTRY_MM)
        sp = spot[(spot.index.date == entry_day) & (spot.index <= et)]
        if sp.empty:
            n_skip_data += 1
            continue
        s0 = sp["close"].iloc[-1]
        avail = sorted(df["strike"].unique())
        if len(avail) < 6:
            n_skip_data += 1
            continue
        atmk = min(avail, key=lambda x: abs(x - round(s0 / STEP) * STEP))
        T = yte(et, exp)
        dfe = df[df["t"] <= et]
        ce0 = _leg(dfe, atmk, "CE")
        pe0 = _leg(dfe, atmk, "PE")
        if ce0.empty or pe0.empty:
            n_skip_data += 1
            continue
        straddle = ce0.iloc[-1] + pe0.iloc[-1]
        iv = implied_vol(ce0.iloc[-1], s0, atmk, T, R_, Q_, True)
        if not (np.isfinite(iv) and 0.03 < iv < 1.5):
            iv = straddle / s0 / (0.8 * np.sqrt(T))

        fl = day_flags.get(entry_day, {})
        for structure in ("short_strangle", "iron_condor"):
            try:
                tr = build_structure_trade(df, exp, entry_day, et, s0, T, iv, avail, structure)
            except Exception as e:
                continue
            if tr is None:
                continue
            tr.update({
                "entry_day": entry_day, "exp": exp, "structure": structure,
                "flag_reclaim": bool(fl.get("reclaim", False)),
                "flag_round_reject": bool(fl.get("round_reject", False)),
                "flag_pd_continue": bool(fl.get("pd_continue", False)),
                "flag_trend_veto": bool(fl.get("trend_veto", False)),
            })
            rows.append(tr)
            n_ok += 1
    print(f"[trades] built {n_ok} structure-trades from {len(exps)} expiries "
          f"({n_skip_data} expiry-level skips: corrupt/stub/no-data/thin-chain).", flush=True)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 3. filters (post-hoc masks on the base-trade table) + portfolio sizing
# ---------------------------------------------------------------------------
FILTERS = {
    "unconditional": lambda d: pd.Series(True, index=d.index),
    "enter_if_reclaim": lambda d: d["flag_reclaim"],
    "skip_if_reclaim": lambda d: ~d["flag_reclaim"],
    "enter_if_round_reject": lambda d: d["flag_round_reject"],
    "enter_if_pd_continue": lambda d: d["flag_pd_continue"],
    "skip_if_pd_continue": lambda d: ~d["flag_pd_continue"],
    "trend_veto": lambda d: ~d["flag_trend_veto"],
    "reclaim_and_trend": lambda d: d["flag_reclaim"] & (~d["flag_trend_veto"]),
}


def portfolio(trades, margin_rate, cap0=CAP0, deploy=DEPLOY):
    t = trades.sort_values("exp").reset_index(drop=True)
    eq_net = cap0
    path = []
    for _, r in t.iterrows():
        margin = r["spot0"] * LOT * margin_rate
        lots = int(deploy * eq_net / margin) if margin > 0 else 0
        lots = max(lots, 0)
        net_rs = r["net_pnl"] * lots
        gross_rs = r["gross_pnl"] * lots
        eq_net += net_rs
        path.append({"exp": r["exp"], "entry_day": r["entry_day"], "lots": lots,
                     "net_pnl_rs": net_rs, "gross_pnl_rs": gross_rs,
                     "net_pnl_per_lot": r["net_pnl"], "gross_pnl_per_lot": r["gross_pnl"],
                     "reason": r["reason"], "eq_net": eq_net})
    return pd.DataFrame(path)


def metrics(pf, cap0=CAP0):
    if pf.empty or pf["lots"].sum() == 0:
        return {"n": 0}
    traded = pf[pf["lots"] > 0].copy()
    idx = pd.to_datetime(traded["entry_day"])
    yrs = max((idx.max() - idx.min()).days / 365.25, 0.1)
    eq = pf["eq_net"].values
    dd = (eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)
    cagr = ((eq[-1] / cap0) ** (1 / yrs) - 1) * 100
    tpy = len(traded) / yrs
    prior_eq = pf["eq_net"].shift(1).fillna(cap0)
    r = (pf["net_pnl_rs"] / prior_eq).loc[traded.index].values   # pct return on compounding equity, S1F convention
    sd = r.std(ddof=1) if len(r) > 1 else np.nan
    sharpe = (r.mean() / sd * np.sqrt(tpy)) if sd and sd > 0 else np.nan
    wins = traded[traded["net_pnl_rs"] > 0]["net_pnl_rs"]
    losses = traded[traded["net_pnl_rs"] <= 0]["net_pnl_rs"]
    pf_ratio = (wins.sum() / abs(losses.sum())) if losses.sum() != 0 else np.nan
    t_nw = nw_tstat(r, lags=4)
    # monthly win rate, gross vs net
    m = traded.copy()
    m["ym"] = pd.to_datetime(m["entry_day"]).dt.to_period("M")
    mo_net = m.groupby("ym")["net_pnl_rs"].sum()
    mo_gross = m.groupby("ym")["gross_pnl_rs"].sum()
    win_mo_net = (mo_net > 0).mean() * 100 if len(mo_net) else np.nan
    win_mo_gross = (mo_gross > 0).mean() * 100 if len(mo_gross) else np.nan
    worst_day_rs = traded["net_pnl_rs"].min()
    worst_day_pct_cap = worst_day_rs / cap0 * 100
    worst_month_rs = mo_net.min() if len(mo_net) else np.nan
    worst_month_pct_cap = worst_month_rs / cap0 * 100 if len(mo_net) else np.nan
    largest_share = traded["net_pnl_rs"].abs().max() / abs(traded["net_pnl_rs"].sum()) if traded["net_pnl_rs"].sum() else np.nan
    return {
        "n": int(len(traded)), "yrs": round(yrs, 2), "CAGR_%": round(cagr, 2),
        "maxDD_%": round(dd.min() * 100, 2), "Calmar": round(cagr / abs(dd.min() * 100), 2) if dd.min() != 0 else np.nan,
        "Sharpe": round(sharpe, 2) if sharpe == sharpe else np.nan, "PF": round(pf_ratio, 2) if pf_ratio == pf_ratio else np.nan,
        "NW_t": round(t_nw, 2) if t_nw == t_nw else np.nan,
        "win_mo_net_%": round(win_mo_net, 1) if win_mo_net == win_mo_net else np.nan,
        "win_mo_gross_%": round(win_mo_gross, 1) if win_mo_gross == win_mo_gross else np.nan,
        "worst_day_rs": round(worst_day_rs), "worst_day_%cap": round(worst_day_pct_cap, 2),
        "worst_month_rs": round(worst_month_rs) if worst_month_rs == worst_month_rs else np.nan,
        "worst_month_%cap": round(worst_month_pct_cap, 2) if worst_month_pct_cap == worst_month_pct_cap else np.nan,
        "largest_trade_share": round(largest_share, 3) if largest_share == largest_share else np.nan,
        "gross_total_rs": round(traded["gross_pnl_rs"].sum()), "net_total_rs": round(traded["net_pnl_rs"].sum()),
        "final_equity": round(eq[-1]), "avg_lots": round(traded["lots"].mean(), 2),
        "max_lots": int(traded["lots"].max()),
    }


def main():
    spot = chain.load_index()
    spot = spot[(spot.index.time >= dt.time(9, 15))]
    day_flags = build_day_flags(spot)
    base = build_base_trades(spot, day_flags)
    base.to_parquet(OUT / "base_trades.parquet")
    print(f"[base] {len(base)} rows saved -> base_trades.parquet", flush=True)

    trials = []
    detail_rows = []
    for structure in ("short_strangle", "iron_condor"):
        srate = MARGIN_RATE[structure]
        sdf_all = base[base["structure"] == structure]
        for fname, fmask in FILTERS.items():
            for label, s0, s1 in (("BUILD", BUILD_START, BUILD_END), ("FWD_2026H1", FWD_START, FWD_END)):
                win = sdf_all[(sdf_all["entry_day"] >= s0) & (sdf_all["entry_day"] <= s1)]
                win = win[fmask(win)]
                pf_ = portfolio(win, srate)
                m = metrics(pf_)
                m.update({"structure": structure, "filter": fname, "window": label, "margin_rate": srate})
                trials.append(m)
                if label == "BUILD":
                    pf_.to_parquet(OUT / f"portfolio_{structure}_{fname}_BUILD.parquet")
                print(f"  {structure:14s} {fname:22s} {label:10s} n={m.get('n',0):4d} "
                      f"CAGR={m.get('CAGR_%','-'):>7} maxDD={m.get('maxDD_%','-'):>7} "
                      f"Sharpe={m.get('Sharpe','-'):>6} Calmar={m.get('Calmar','-'):>6} "
                      f"PF={m.get('PF','-'):>5} NWt={m.get('NW_t','-'):>5}", flush=True)

    tdf = pd.DataFrame(trials)
    tdf.to_csv(OUT / "TRIALS_LOG.csv", index=False)
    print(f"\n[done] {len(tdf)} trials logged -> TRIALS_LOG.csv", flush=True)


if __name__ == "__main__":
    main()
