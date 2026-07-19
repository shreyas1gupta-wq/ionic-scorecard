"""
oversight_cascade.py -- scaffold for 03_OVERSIGHT_CASCADE.md.

Layered tailwind/headwind ADJUSTMENT (score-points, NOT a gate) applied
top-down: GLOBAL -> NATIONAL -> SECTOR -> STOCK(passthrough to 02's
bottom-up composite, not yet built).

Every layer that substitutes a proxy for the true design input (03's spec:
US10Y/DXY/Fed/VIX/crude/PMI at Global; RBI/credit/FII-DII/CPI/IIP at
National; true sector indices/full-constituent baskets at Sector) is
explicitly tagged [INFERENCE/approx] with the substitution reason, per
EPISTEMIC_CONDUCT. Nothing here is fabricated -- untagged numbers are direct
reads off factor_navs or data/prices; tagged numbers are approximations
built from those same real series.

Adjustment scale: +-15 points per layer (per 03's spec). net_adj = simple
sum of the three active layers (stock layer is a 0-point placeholder until
02_SCORING_ENGINE exists to be shifted).
"""
from __future__ import annotations
import csv
import sys
from pathlib import Path

import pandas as pd

THIS = Path(__file__).resolve()
SRC = THIS.parents[1]         # ALPHA_RANKER/src
PROJECT = THIS.parents[2]     # ALPHA_RANKER
ROOT = THIS.parents[3]        # NIFTY 500 repo root

sys.path.insert(0, str(SRC / "lib"))
import factor_bench as fb  # noqa: E402

PRICES_DIR = PROJECT / "data" / "prices"
SECTOR_CSV = ROOT / "datasets" / "india_stock_metadata" / "india.csv"

ADJ_CAP = 15.0  # points, +-15 per layer per 03_OVERSIGHT_CASCADE.md

PILOT = ["HDFCBANK", "ASIANPAINT", "NESTLEIND", "TATASTEEL", "HINDALCO",
         "MARUTI", "TCS", "INFY", "GRAVITA", "SHAKTIPUMP"]


def _clip(x: float, lo: float = -ADJ_CAP, hi: float = ADJ_CAP) -> float:
    return max(lo, min(hi, x))


def load_sector_map(tickers=None) -> dict:
    """ticker -> sector, from datasets/india_stock_metadata/india.csv.
    [DATA] direct read, first match kept if a ticker appears more than once."""
    wanted = set(tickers or PILOT)
    out = {}
    with open(SECTOR_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            t = row["ticker"].strip()
            if t in wanted and t not in out:
                out[t] = row["sector"].strip()
    for m in wanted - out.keys():
        out[m] = "UNKNOWN"
    return out


def load_pilot_prices() -> dict:
    """ticker -> OHLC DataFrame from ALPHA_RANKER/data/prices/<ticker>.parquet
    (yfinance pull, ~2y history; see PROGRESS.md). [DATA] direct read."""
    out = {}
    for t in PILOT:
        p = PRICES_DIR / f"{t}.parquet"
        if p.exists():
            out[t] = pd.read_parquet(p)
    return out


def _stock_returns(prices: dict, ticker: str) -> pd.Series:
    df = prices.get(ticker)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    return df[col].pct_change().dropna()


# ---------------------------------------------------------------- GLOBAL --
def global_layer(asof, lookback_days: int = 63) -> dict:
    """
    Spec inputs (US10Y/DXY/Fed stance/VIX/crude/gold-silver ratio/PMI/
    shipping/geopolitics) are NOT yet pulled into 05_DATA_OFFICE -- see
    09_DATA_LAYER.md Macro + PROGRESS.md 'BLOCKED - need Principal'.
    [INFERENCE/approx]: we approximate the risk-appetite backdrop from the
    two macro-risk proxies that DO exist inside factor_navs:
      1. GOLDBEES trailing return -- flight-to-gold is a real risk-off tell,
         but it is only one leg of the spec's global-risk axis.
      2. High-Beta-50 vs Low-Vol-30 relative strength -- a domestic-market
         risk-on/off proxy, not the true global cross-asset read (no
         US10Y/DXY/VIX access from this panel).
    Replace with true global inputs once macro pulls (D-033-eligible:
    FRED/Stooq) land in 05_DATA_OFFICE.
    """
    gold_ret = fb.trailing_return("GOLD", asof, lookback_days)
    beta_vs_lowvol = fb.relative_strength("HIGHBETA50", "LOWVOL30", asof, lookback_days)

    adj = 0.0
    reasons = []
    if not pd.isna(gold_ret):
        gold_component = _clip(-gold_ret * 100 * 0.6)  # ~10% gold rally -> -6pt headwind
        adj += gold_component
        reasons.append(f"GOLDBEES {lookback_days}d trailing {gold_ret:+.1%} "
                        f"-> {gold_component:+.1f}pt (flight-to-gold proxy)")
    if not pd.isna(beta_vs_lowvol):
        beta_component = _clip(beta_vs_lowvol * 100 * 0.5)
        adj += beta_component
        reasons.append(f"HighBeta50 vs LowVol30 RS {beta_vs_lowvol:+.1%} "
                        f"-> {beta_component:+.1f}pt (domestic risk-on/off proxy)")
    adj = _clip(adj)
    if not reasons:
        reasons.append("insufficient history for global proxies -> neutral 0")
    return {"adj": round(adj, 1), "rationale": " | ".join(reasons),
            "tag": "[INFERENCE/approx]"}


# -------------------------------------------------------------- NATIONAL --
def national_layer(asof, fast: int = 50, slow: int = 200,
                    breadth_lookback: int = 63) -> dict:
    """
    Spec inputs (RBI repo/stance, credit growth, 10Y G-sec, INR, CPI/WPI/IIP,
    FII/DII flows, fiscal/GST, PMI) are NOT yet pulled -- same blocker as
    global. [INFERENCE/approx]: approximate the National regime read from
      1. NIFTY 500's own trend state (price vs SMA50/SMA200) -- a DIRECT
         read, not a proxy, but only the price-trend half of the spec's
         'regime tuple' (no credit/rate axis).
      2. A breadth surrogate = fraction of the panel's cap/style indices
         with a positive trailing return over the window, standing in for
         true market-breadth (advance/decline) which needs constituent-level
         data we don't have. [INFERENCE/approx] on breadth only.
    """
    trend = fb.trend_state("NIFTY500", asof, fast, slow)
    trend_component = {"uptrend": 10.0, "downtrend": -10.0, "mixed": 0.0,
                        "insufficient_history": 0.0}[trend["state"]]

    breadth_universe = ["NIFTY100", "NIFTY500", "MIDCAP150", "SMALLCAP100",
                         "SMALLCAP250", "LOWVOL30", "QUALITY30", "VALUE30",
                         "MOMENTUM30", "ALPHA30", "HIGHBETA50"]
    above, counted = 0, 0
    for nm in breadth_universe:
        r = fb.trailing_return(nm, asof, breadth_lookback)
        if not pd.isna(r):
            counted += 1
            above += r > 0
    breadth_frac = (above / counted) if counted else float("nan")
    breadth_component = _clip((breadth_frac - 0.5) * 2 * 10) if not pd.isna(breadth_frac) else 0.0

    adj = _clip(trend_component * 0.6 + breadth_component * 0.4)
    rationale = (f"NIFTY500 trend={trend['state']} (px {trend['level']:.0f} vs "
                 f"SMA{fast}={trend['sma_fast']:.0f}/SMA{slow}={trend['sma_slow']:.0f}) "
                 f"-> {trend_component:+.1f}pt [DATA]; breadth {above}/{counted} indices "
                 f"positive over {breadth_lookback}d -> {breadth_component:+.1f}pt "
                 f"[INFERENCE/approx]")
    return {"adj": round(adj, 1), "rationale": rationale,
            "tag": "[DATA]+[INFERENCE/approx-breadth]"}


# ---------------------------------------------------------------- SECTOR --
def sector_layer(ticker: str, sector_map: dict, prices: dict, asof,
                  lookback_days: int = 63) -> dict:
    """
    Spec input is a true sector index or full-constituent sector basket.
    Neither exists in factor_navs (which has cap/style factor indices, not
    GICS-like sectors) nor in 05_DATA_OFFICE yet. [INFERENCE/approx]: build
    an equal-weight sector composite from ONLY the pilot's own constituents
    sharing this stock's india.csv sector (n_peers as low as 1 for singleton
    sectors in this 10-name pilot -- e.g. Finance has just HDFCBANK), then
    take that composite's relative strength vs NIFTY 500. This is a
    small-N/self-referential proxy (a stock can end up compared against
    itself when n_peers==1, RS==0 by construction) -- NOT a real sector
    read. Replace once full NIFTY-500 sector baskets are built.
    """
    sector = sector_map.get(ticker, "UNKNOWN")
    peers = [t for t, s in sector_map.items() if s == sector and t in prices]
    if not peers:
        return {"adj": 0.0, "sector": sector, "n_peers": 0,
                "rationale": f"sector={sector}: no priced peers in pilot -> neutral 0",
                "tag": "[INFERENCE/approx]"}

    ret_frames = [_stock_returns(prices, p).rename(p) for p in peers]
    ret_frames = [r for r in ret_frames if len(r)]
    if not ret_frames:
        return {"adj": 0.0, "sector": sector, "n_peers": len(peers),
                "rationale": f"sector={sector}: peers found but no return history -> neutral 0",
                "tag": "[INFERENCE/approx]"}

    panel = pd.concat(ret_frames, axis=1)
    composite_ret = panel.mean(axis=1)  # equal-weight, pilot-only sector composite
    asof_ts = pd.Timestamp(asof)
    hist = composite_ret[composite_ret.index <= asof_ts]

    bench_trailing = fb.trailing_return("NIFTY500", asof, lookback_days)
    if len(hist) < lookback_days or pd.isna(bench_trailing):
        return {"adj": 0.0, "sector": sector, "n_peers": len(peers),
                "rationale": f"sector={sector} (n_peers={len(peers)}): insufficient "
                             f"history for {lookback_days}d window -> neutral 0",
                "tag": "[INFERENCE/approx]"}

    sector_trailing = float((1 + hist.tail(lookback_days)).prod() - 1)
    rs = sector_trailing - bench_trailing
    adj = _clip(rs * 100 * 1.0)  # 1pt per 1% relative outperformance, capped +-15
    singleton_note = (" (singleton sector: RS partly self-referential)"
                       if len(peers) == 1 and ticker in peers else "")
    rationale = (f"sector={sector} (n_peers={len(peers)}: {','.join(peers)}){singleton_note}; "
                 f"composite {lookback_days}d trailing {sector_trailing:+.1%} vs NIFTY500 "
                 f"{bench_trailing:+.1%} -> RS {rs:+.1%} -> {adj:+.1f}pt")
    return {"adj": round(adj, 1), "sector": sector, "n_peers": len(peers),
            "rationale": rationale, "tag": "[INFERENCE/approx]"}


# ----------------------------------------------------------------- STOCK --
def stock_layer(ticker: str) -> dict:
    """
    Handoff to the bottom-up factor/theme composite (02_SCORING_ENGINE.md),
    which is NOT built yet in this task. 0-point placeholder so the
    net-adjustment arithmetic is well-formed; this is where the cascade's
    output (cascade_shift) would be ADDED to the real composite score once
    02 exists. [PLACEHOLDER] -- not a computed result.
    """
    return {"adj": 0.0,
            "rationale": "passthrough -- bottom-up composite score (02_SCORING_ENGINE) not yet built",
            "tag": "[PLACEHOLDER]"}


# ------------------------------------------------------------------- run --
def run_cascade(asof=None, tickers=None) -> pd.DataFrame:
    tickers = tickers or PILOT
    navs = fb.load_navs()
    asof = pd.Timestamp(asof) if asof else navs.index.max()

    sector_map = load_sector_map(tickers)
    prices = load_pilot_prices()

    g = global_layer(asof)
    n = national_layer(asof)

    rows = []
    for t in tickers:
        s = sector_layer(t, sector_map, prices, asof)
        st = stock_layer(t)
        net = g["adj"] + n["adj"] + s["adj"] + st["adj"]
        rows.append({
            "ticker": t,
            "asof": asof.date().isoformat(),
            "sector": s["sector"],
            "n_sector_peers": s["n_peers"],
            "global_adj": g["adj"],
            "national_adj": n["adj"],
            "sector_adj": s["adj"],
            "stock_adj": st["adj"],
            "net_adj": round(net, 1),
            "global_rationale": f"{g['tag']} {g['rationale']}",
            "national_rationale": f"{n['tag']} {n['rationale']}",
            "sector_rationale": f"{s['tag']} {s['rationale']}",
            "stock_rationale": f"{st['tag']} {st['rationale']}",
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run_cascade()
    out = PROJECT / "results" / "pilot_cascade_adjustments.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print("wrote", out, df.shape)
    print(df[["ticker", "sector", "n_sector_peers", "global_adj",
               "national_adj", "sector_adj", "net_adj"]].to_string(index=False))
