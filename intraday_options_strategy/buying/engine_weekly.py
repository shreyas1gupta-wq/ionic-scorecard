"""Weekly short-STRANGLE engine with multi-filter regime logic (user's design).

Sell CE + PE at target delta (default 0.2, dynamic 0.1-0.5), enter ~3-4 DTE, hold to
weekly expiry (manage@target / total-stop / expiry settle). Filters (toggleable):
  - DMA stack 20/50/100/200/350 (regime)
  - RULE: avoid NAKED PE when spot < 50DMA  (skip_pe | defined_risk | skip_trade | none)
  - IV-rank (sell only rich vol), RSI, MACD (avoid selling into extremes/strong trends)
  - support/resistance: require short strikes to sit beyond recent swing hi/lo
  - structure: naked strangle | iron_condor (defined-risk wings for low capital)
  - total-position STOP (cut when cost-to-close >= stop_mult x credit) — key MDD lever
Fixed 1 lot, real prices, retail costs. Build 2021-2025 / forward 2026 H1.
Runs a config GRID -> results CSV + best-config trades for downstream verification.
"""
from __future__ import annotations

import datetime as dt
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from options.bs_pricing import bs_greeks, implied_vol  # noqa: E402

import chain  # noqa: E402
from engine import (BROKERAGE_PER_ORDER, STT_SELL_PCT, EXCH_TXN_PCT, GST_PCT,
                    SEBI_PER_CRORE, STAMP_BUY_PCT, STEP)  # noqa: E402

R, Q, LOT, SLIP = 0.065, 0.012, 75, 0.0075
CAP = 3_00_000.0
OUTDIR = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup"
              r"\NIFTY 500\intraday_options_strategy\buying")


@dataclass
class WCfg:
    ce_delta: float = 0.20
    pe_delta: float = 0.20
    wing_delta: float = 0.08
    target_dte: int = 3
    min_dte: int = 2
    max_dte: int = 5
    structure: str = "strangle"          # strangle | iron_condor
    pe_below_50dma: str = "skip_pe"      # skip_pe | defined_risk | skip_trade | none
    iv_rank_min: float = 0.0             # 0=off; else require straddle% rank >=
    rsi_band: float = 0.0                # 0=off; else skip if RSI in extreme (see code)
    use_macd: bool = False               # skip PE if MACD bearish, CE if bullish
    use_sr: bool = False                 # require short strikes beyond 20d swing hi/lo
    target_frac: float = 0.50            # buy back at 50% credit
    stop_mult: float = 2.0               # total-position stop (0=off)
    entry_hhmm: str = "09:20"
    exit_hhmm: str = "15:15"


# ---------- daily features ----------
def _rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1/n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1/n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def daily_features(spot):
    g = spot.groupby(spot.index.date)
    d = pd.DataFrame({"close": g["close"].last(), "high": g["high"].max(),
                      "low": g["low"].min()})
    d.index = [pd.Timestamp(x).date() for x in d.index]
    for n in (20, 50, 100, 200, 350):
        d[f"ma{n}"] = d["close"].rolling(n).mean()
    d["rsi14"] = _rsi(d["close"], 14)
    ema12 = d["close"].ewm(span=12, adjust=False).mean()
    ema26 = d["close"].ewm(span=26, adjust=False).mean()
    d["macd"] = ema12 - ema26
    d["macd_sig"] = d["macd"].ewm(span=9, adjust=False).mean()
    d["swing_hi20"] = d["high"].rolling(20).max()
    d["swing_lo20"] = d["low"].rolling(20).min()
    return d.shift(1)   # prior-day values -> known at entry (no lookahead)


# ---------- helpers ----------
def pick_delta(df, s0, T, iv, target, otype, avail):
    """Vectorised: one BS call over all strikes, pick closest |delta| to target."""
    is_call = otype == "CE"
    ks = np.asarray(avail, dtype=float)
    d = np.abs(np.asarray(bs_greeks(s0, ks, T, iv, R, Q, is_call)["delta"]))
    return avail[int(np.argmin(np.abs(d - target)))]


def yte(t0, exp):
    ex = pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)
    return max((ex - t0).total_seconds() / (365.25 * 24 * 3600), 1e-5)


def _leg(df, k, o):
    return df[(df["strike"] == k) & (df["option_type"] == o)].set_index("t")["close"].sort_index()


def _leg_open(df, k, o, t0):
    s = df[(df["strike"] == k) & (df["option_type"] == o)].set_index("t").sort_index()
    a = s[s.index >= t0]
    return a["open"].iloc[0] if not a.empty else np.nan


def costs_multi(sell_prem, buy_prem, close_prem, n_legs):
    qty = LOT
    brok = BROKERAGE_PER_ORDER * n_legs * 2
    turnover = (sell_prem + buy_prem + close_prem) * qty
    exch = EXCH_TXN_PCT * turnover
    stt = STT_SELL_PCT * (sell_prem * qty)
    gst = GST_PCT * (brok + exch)
    sebi = SEBI_PER_CRORE * turnover / 1e7
    stamp = STAMP_BUY_PCT * (buy_prem * qty)
    return brok + exch + stt + gst + sebi + stamp


# ---------- straddle%% precompute for IV rank ----------
def straddle_pct_by_expiry(spot, exps, cfg):
    out = {}
    for exp in exps:
        df = chain.load_expiry(exp)
        tdays = sorted(df["trading_day"].unique())
        ed = None
        for td in tdays:
            d = dt.date.fromisoformat(td)
            if cfg.min_dte <= (exp - d).days <= cfg.max_dte:
                ed = d
                if (exp - d).days <= cfg.target_dte:
                    break
        if ed is None:
            continue
        et = pd.Timestamp(ed) + pd.Timedelta(hours=9, minutes=20)
        sp = spot[(spot.index.date == ed) & (spot.index <= et)]
        if sp.empty:
            continue
        s0 = sp["close"].iloc[-1]
        avail = sorted(df["strike"].unique())
        atmk = min(avail, key=lambda x: abs(x - round(s0 / STEP) * STEP))
        ce = _leg(df[df["t"] <= et], atmk, "CE")
        pe = _leg(df[df["t"] <= et], atmk, "PE")
        if ce.empty or pe.empty:
            continue
        out[exp] = (ce.iloc[-1] + pe.iloc[-1]) / s0
    s = pd.Series(out).sort_index()
    rank = s.rolling(40, min_periods=10).apply(lambda w: (w.iloc[-1] >= w).mean(), raw=False)
    return s, rank


# ---------- one trade ----------
def simulate(spot, exp, cfg, dfeat, ivrank):
    df = chain.load_expiry(exp)
    tdays = sorted(df["trading_day"].unique())
    ed = None
    for td in tdays:
        d = dt.date.fromisoformat(td)
        if cfg.min_dte <= (exp - d).days <= cfg.max_dte:
            ed = d
            if (exp - d).days <= cfg.target_dte:
                break
    if ed is None:
        return None
    if ed not in dfeat.index:
        return None
    feat = dfeat.loc[ed]
    et = pd.Timestamp(ed) + pd.Timedelta(hours=9, minutes=20)
    sp = spot[(spot.index.date == ed) & (spot.index <= et)]
    if sp.empty:
        return None
    s0 = sp["close"].iloc[-1]
    avail = sorted(df["strike"].unique())
    if len(avail) < 8:
        return None

    # ---- filters ----
    if cfg.iv_rank_min > 0:
        r = ivrank.get(exp, np.nan)
        if not (np.isfinite(r) and r >= cfg.iv_rank_min):
            return {"skip": True}
    below_50 = np.isfinite(feat["ma50"]) and s0 < feat["ma50"]
    sell_pe = True
    pe_defined = (cfg.structure == "iron_condor")
    if below_50:
        if cfg.pe_below_50dma == "skip_trade":
            return {"skip": True}
        elif cfg.pe_below_50dma == "skip_pe":
            sell_pe = False
        elif cfg.pe_below_50dma == "defined_risk":
            pe_defined = True
    if cfg.rsi_band > 0 and np.isfinite(feat["rsi14"]):
        # avoid selling PE when oversold (bounce-down risk already; actually skip both extremes)
        if feat["rsi14"] < (50 - cfg.rsi_band):
            sell_pe = False       # oversold -> downside risk -> don't sell naked PE
    if cfg.use_macd and np.isfinite(feat["macd"]):
        if feat["macd"] < feat["macd_sig"]:
            sell_pe = False       # MACD bearish -> skip PE

    T = yte(et, exp)
    atmk = min(avail, key=lambda x: abs(x - round(s0 / STEP) * STEP))
    ce_atm = _leg(df[df["t"] <= et], atmk, "CE")
    if ce_atm.empty:
        return None
    iv = implied_vol(ce_atm.iloc[-1], s0, atmk, T, R, Q, True)
    if not (np.isfinite(iv) and 0.03 < iv < 1.5):
        return None

    legs = []  # (strike, otype, side)
    ksc = pick_delta(df, s0, T, iv, cfg.ce_delta, "CE", avail)
    legs.append((ksc, "CE", +1))
    if cfg.structure == "iron_condor":
        kbc = pick_delta(df, s0, T, iv, cfg.wing_delta, "CE", avail)
        legs.append((max(kbc, ksc + STEP), "CE", -1))
    if sell_pe:
        ksp = pick_delta(df, s0, T, iv, cfg.pe_delta, "PE", avail)
        legs.append((ksp, "PE", +1))
        if pe_defined:
            kbp = pick_delta(df, s0, T, iv, cfg.wing_delta, "PE", avail)
            legs.append((min(kbp, ksp - STEP), "PE", -1))

    # support/resistance: short strikes must be beyond swing hi/lo
    if cfg.use_sr and np.isfinite(feat["swing_hi20"]):
        if ksc < feat["swing_hi20"]:
            return {"skip": True}
        if sell_pe:
            ksp = [l[0] for l in legs if l[1] == "PE" and l[2] == +1]
            if ksp and ksp[0] > feat["swing_lo20"]:
                return {"skip": True}

    entry_px = {}
    for k, o, side in legs:
        px = _leg_open(df, k, o, et)
        if not np.isfinite(px):
            return None
        entry_px[(k, o)] = px
    sell_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == +1)
    buy_prem = sum(entry_px[(k, o)] for k, o, s in legs if s == -1)
    credit = (sum(entry_px[(k, o)] * (1 - SLIP) for k, o, s in legs if s == +1)
              - sum(entry_px[(k, o)] * (1 + SLIP) for k, o, s in legs if s == -1))
    if credit <= 0:
        return None

    series = {(k, o, side): _leg(df, k, o) for k, o, side in legs}
    idx = series[legs[0][:3] if len(legs[0]) == 3 else legs[0]].index if False else \
        series[(legs[0][0], legs[0][1], legs[0][2])].index
    idx = idx[idx >= et][::15]   # 15-min sampling for exit checks

    def val_at(t):
        v = 0.0
        for k, o, side in legs:
            px = series[(k, o, side)].asof(t)   # binary search, last value <= t
            if not np.isfinite(px):
                return np.nan
            v += side * px
        return v

    tgt = credit * (1 - cfg.target_frac)
    stop_v = credit * cfg.stop_mult if cfg.stop_mult > 0 else 1e18
    exit_v = reason = None
    for t in idx:
        if t <= et:
            continue
        d_ = t.date()
        eod = pd.Timestamp(d_) + pd.Timedelta(hours=15, minutes=15)
        if d_ >= exp and t >= eod:
            es = spot[spot.index.date == exp]
            s1 = es["close"].iloc[-1] if not es.empty else s0
            v = 0.0
            for k, o, side in legs:
                v += side * max(0.0, (k - s1) if o == "PE" else (s1 - k))
            exit_v, reason = max(v, 0.0), "expiry"; break
        v = val_at(t)
        if not np.isfinite(v):
            continue
        if v <= tgt:
            exit_v, reason = v, "target"; break
        if v >= stop_v:
            exit_v, reason = v, "stop"; break
    if exit_v is None:
        exit_v, reason = val_at(idx[-1]) if len(idx) else 0.0, "eod"
        if not np.isfinite(exit_v):
            exit_v = 0.0

    close_prem = max(exit_v, 0.0)
    fill_close = close_prem * (1 + SLIP)
    gross = (credit - fill_close) * LOT
    costs = costs_multi(sell_prem, buy_prem, close_prem, len(legs))
    net = gross - costs
    return {"enter_day": ed, "exp": exp, "regime_below50": bool(below_50),
            "sold_pe": sell_pe, "n_legs": len(legs), "credit": credit,
            "reason": reason, "net_pnl": net, "win": net > 0}


def run_cfg(spot, exps, cfg, dfeat, ivrank, start, end):
    rows = []
    for exp in exps:
        if not (start <= exp <= end):
            continue
        try:
            tr = simulate(spot, exp, cfg, dfeat, ivrank)
        except Exception:
            continue
        if tr is None or tr.get("skip"):
            continue
        rows.append(tr)
    return pd.DataFrame(rows)


def metrics(df):
    if df.empty or len(df) < 3:
        return {"n": len(df)}
    df = df.sort_values("exp")
    net = df["net_pnl"].sum()
    eq = CAP + df["net_pnl"].cumsum().values
    dd = float(((eq - np.maximum.accumulate(eq)) / np.maximum.accumulate(eq)).min())
    r = df["net_pnl"] / CAP
    yrs = (df["exp"].iloc[-1] - df["exp"].iloc[0]).days / 365.25 + 1e-9
    tpy = len(df) / yrs
    sharpe = float(r.mean() / r.std() * np.sqrt(tpy)) if r.std() > 0 else 0.0
    w = df[df["net_pnl"] > 0]["net_pnl"]; l = df[df["net_pnl"] <= 0]["net_pnl"]
    pf = float(w.sum() / abs(l.sum())) if l.sum() != 0 else 99.0
    return {"n": len(df), "wr": float(df["win"].mean()), "pf": pf,
            "net": float(net), "tot_ret": float(net / CAP), "maxdd": dd,
            "sharpe": sharpe, "worst": float(df["net_pnl"].min())}


GRID = []
for structure in ("strangle", "iron_condor"):
    for delta in (0.20, 0.30):
        for pe_mode in ("none", "skip_pe", "defined_risk"):
            for stop in (0.0, 2.0):
                for ivf in (0.0, 0.4):
                    GRID.append(WCfg(structure=structure, ce_delta=delta, pe_delta=delta,
                                     pe_below_50dma=pe_mode, stop_mult=stop, iv_rank_min=ivf))


if __name__ == "__main__":
    spot = chain.load_index()
    dfeat = daily_features(spot)
    _, exps = chain.build_expiry_index()
    _, ivrank = straddle_pct_by_expiry(spot, exps, WCfg())
    ivrank = ivrank.to_dict()
    print(f"[weekly] grid of {len(GRID)} configs over {len(exps)} expiries")
    res = []
    for i, cfg in enumerate(GRID):
        b = run_cfg(spot, exps, cfg, dfeat, ivrank, dt.date(2021, 1, 1), dt.date(2025, 12, 31))
        f = run_cfg(spot, exps, cfg, dfeat, ivrank, dt.date(2026, 1, 1), dt.date(2026, 6, 2))
        mb, mf = metrics(b), metrics(f)
        row = {**{k: v for k, v in asdict(cfg).items()
                  if k in ("structure", "ce_delta", "pe_below_50dma", "stop_mult", "iv_rank_min")},
               **{f"b_{k}": v for k, v in mb.items()},
               **{f"f_{k}": v for k, v in mf.items()}}
        res.append(row)
        if i % 8 == 0:
            print(f"  ...{i}/{len(GRID)}")
    R_ = pd.DataFrame(res)
    R_.to_csv(OUTDIR / "weekly_grid.csv", index=False)
    pd.set_option("display.width", 240, "display.max_columns", None)
    cols = ["structure", "ce_delta", "pe_below_50dma", "stop_mult", "iv_rank_min",
            "b_n", "b_wr", "b_pf", "b_sharpe", "b_maxdd", "b_tot_ret",
            "f_n", "f_pf", "f_sharpe", "f_tot_ret"]
    top = R_.sort_values("b_sharpe", ascending=False)
    print("\nTOP 12 by BUILD Sharpe:")
    print(top[cols].head(12).to_string(index=False))
    print(f"\nsaved -> {OUTDIR / 'weekly_grid.csv'}")
