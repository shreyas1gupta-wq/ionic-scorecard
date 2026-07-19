"""
ALPHA_RANKER -- Universe-scale Oversight Cascade (NIFTY-750).

Scales src/cascade/oversight_cascade.py (10-stock pilot) to the FULL universe.

KEY IMPROVEMENT over the pilot: sector now comes from the real `Industry`
column in data/universe/nifty_total_market_750.csv (22 GICS-like industries
across 751 names), and each sector's equal-weight RS composite is built from
ALL of that industry's priced constituents in data/prices/ -- not just the
pilot's own 10 tickers. This directly fixes the pilot's documented
singleton-sector artifact (e.g. "Finance has just HDFCBANK" -> RS
self-referential by construction when n_peers==1 and the stock IS its own
sector composite). At universe scale, sector composites range from 1 (a few
"Diversified"/"Forest Materials" outliers) to 100+ (Financial Services,
Capital Goods) priced constituents -- self-reference is now the rare
exception, not the pilot's rule, and is still flagged explicitly per-name
when n_peers==1 so it's never silently treated as a real read.

GLOBAL / NATIONAL layers are UNCHANGED from the pilot (they don't depend on
the pilot ticker list at all -- both already read only from factor_navs).
SECTOR is rebuilt as described above. STOCK remains a 0-point PLACEHOLDER --
the bottom-up composite (02_SCORING_ENGINE) is out of scope for this task.

Adjustment scale: +-15 points per layer (per 03's spec). net_adj = sum of
the four layers (stock=0 today).
"""
from __future__ import annotations
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THIS = Path(__file__).resolve()
SRC = THIS.parents[1]         # ALPHA_RANKER/src
PROJECT = THIS.parents[2]     # ALPHA_RANKER
ROOT = THIS.parents[3]        # NIFTY 500 repo root

sys.path.insert(0, str(SRC / "lib"))
import factor_bench as fb  # noqa: E402

PRICES_DIR = PROJECT / "data" / "prices"
UNIVERSE_CSV = PROJECT / "data" / "universe" / "nifty_total_market_750.csv"
RESULTS = PROJECT / "results"
RESULTS.mkdir(exist_ok=True, parents=True)

ADJ_CAP = 15.0  # points, +-15 per layer per 03_OVERSIGHT_CASCADE.md


def _clip(x: float, lo: float = -ADJ_CAP, hi: float = ADJ_CAP) -> float:
    return max(lo, min(hi, x))


def load_sector_map() -> dict:
    """symbol -> Industry, from data/universe/nifty_total_market_750.csv
    (the real universe file, replacing the pilot's datasets/india_stock_metadata/
    india.csv external lookup). [DATA] direct read, all 751 symbols."""
    uni = pd.read_csv(UNIVERSE_CSV)
    return dict(zip(uni["Symbol"], uni["Industry"]))


def load_universe_prices(symbols) -> dict:
    """symbol -> OHLC DataFrame from ALPHA_RANKER/data/prices/<symbol>.parquet,
    for whichever of the universe's symbols have landed so far (696/751 at
    time of writing; code re-reads the directory on every run so later runs
    just pick up more coverage). [DATA] direct read."""
    out = {}
    for t in symbols:
        p = PRICES_DIR / f"{t}.parquet"
        if p.exists():
            try:
                out[t] = pd.read_parquet(p)
            except Exception as e:
                print(f"  [WARN] failed to read {p.name}: {e}")
    return out


def _stock_returns(prices: dict, ticker: str) -> pd.Series:
    df = prices.get(ticker)
    if df is None or df.empty:
        return pd.Series(dtype=float)
    col = "Adj Close" if "Adj Close" in df.columns else "Close"
    return df[col].pct_change().dropna()


# ---------------------------------------------------------------- GLOBAL --
def global_layer(asof, lookback_days: int = 63) -> dict:
    """Unchanged from the pilot -- global-risk proxies live in factor_navs,
    not tied to any stock list. True spec inputs (US10Y/DXY/Fed/VIX/crude/
    PMI) still not pulled into 05_DATA_OFFICE; approximated from GOLDBEES
    trailing return (flight-to-gold) and HighBeta50-vs-LowVol30 RS (domestic
    risk-on/off proxy). [INFERENCE/approx], same as pilot."""
    gold_ret = fb.trailing_return("GOLD", asof, lookback_days)
    beta_vs_lowvol = fb.relative_strength("HIGHBETA50", "LOWVOL30", asof, lookback_days)

    adj = 0.0
    reasons = []
    if not pd.isna(gold_ret):
        gold_component = _clip(-gold_ret * 100 * 0.6)
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
    return {"adj": round(adj, 1), "rationale": " | ".join(reasons), "tag": "[INFERENCE/approx]"}


# -------------------------------------------------------------- NATIONAL --
def national_layer(asof, fast: int = 50, slow: int = 200,
                    breadth_lookback: int = 63) -> dict:
    """Unchanged from the pilot -- NIFTY500 trend [DATA] + cap/style-index
    breadth surrogate [INFERENCE/approx], same blocker on RBI/credit/FII-DII/
    CPI/IIP/PMI as the pilot (not yet in 05_DATA_OFFICE)."""
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
    return {"adj": round(adj, 1), "rationale": rationale, "tag": "[DATA]+[INFERENCE/approx-breadth]"}


# ---------------------------------------------------------------- SECTOR --
def build_sector_composites(sector_map: dict, prices: dict, asof,
                             lookback_days: int = 63) -> dict:
    """
    Build ONE equal-weight sector composite per Industry from ALL priced
    constituents of that industry (not per-stock -- computed once, looked up
    per symbol below). This is the fix for the pilot's singleton-sector
    self-reference artifact: with the full universe, sector peer counts are
    typically dozens (Financial Services=121 names in the universe csv,
    Capital Goods=112, ...), so a stock's own return is a small fraction of
    its sector composite rather than the whole of it.

    Returns dict[industry] -> {"adj", "rationale", "n_peers", "peers", "tag"}.
    Sectors with 0 priced peers, or peers with a full return history but the
    stock itself unavailable, are neutral 0 with an explicit reason -- never
    fabricated.
    """
    bench_trailing = fb.trailing_return("NIFTY500", asof, lookback_days)
    asof_ts = pd.Timestamp(asof)

    # group symbols by industry, keep only those with price data
    by_industry: dict[str, list[str]] = {}
    for sym, ind in sector_map.items():
        if sym in prices:
            by_industry.setdefault(ind, []).append(sym)

    out = {}
    all_industries = sorted(set(sector_map.values()))
    for industry in all_industries:
        peers = by_industry.get(industry, [])
        if not peers:
            out[industry] = {"adj": 0.0, "n_peers": 0, "peers": [],
                              "rationale": f"sector={industry}: no priced constituents in universe -> neutral 0",
                              "tag": "[INFERENCE/approx]"}
            continue

        ret_frames = [_stock_returns(prices, p).rename(p) for p in peers]
        ret_frames = [r for r in ret_frames if len(r)]
        if not ret_frames:
            out[industry] = {"adj": 0.0, "n_peers": len(peers), "peers": peers,
                              "rationale": f"sector={industry}: {len(peers)} priced peers but no "
                                           "return history -> neutral 0",
                              "tag": "[INFERENCE/approx]"}
            continue

        panel = pd.concat(ret_frames, axis=1, sort=True)
        composite_ret = panel.mean(axis=1)  # equal-weight, full-universe sector composite
        hist = composite_ret[composite_ret.index <= asof_ts]

        if len(hist) < lookback_days or pd.isna(bench_trailing):
            out[industry] = {"adj": 0.0, "n_peers": len(peers), "peers": peers,
                              "rationale": f"sector={industry} (n_peers={len(peers)}): insufficient "
                                           f"history for {lookback_days}d window -> neutral 0",
                              "tag": "[INFERENCE/approx]"}
            continue

        sector_trailing = float((1 + hist.tail(lookback_days)).prod() - 1)
        rs = sector_trailing - bench_trailing
        adj = _clip(rs * 100 * 1.0)  # 1pt per 1% relative outperformance, capped +-15
        singleton_note = (" (singleton sector: RS self-referential when this stock IS the "
                           "composite)" if len(peers) == 1 else "")
        rationale = (f"sector={industry} (n_peers={len(peers)}){singleton_note}; composite "
                     f"{lookback_days}d trailing {sector_trailing:+.1%} vs NIFTY500 "
                     f"{bench_trailing:+.1%} -> RS {rs:+.1%} -> {adj:+.1f}pt")
        out[industry] = {"adj": round(adj, 1), "n_peers": len(peers), "peers": peers,
                          "rationale": rationale, "tag": "[INFERENCE/approx]"}
    return out


# ----------------------------------------------------------------- STOCK --
def stock_layer(ticker: str) -> dict:
    """0-point PLACEHOLDER -- the bottom-up factor/theme composite
    (02_SCORING_ENGINE) is out of scope for this task; this is where
    cascade_shift would be ADDED to that composite once it exists."""
    return {"adj": 0.0,
            "rationale": "passthrough -- bottom-up composite score (02_SCORING_ENGINE) not built here",
            "tag": "[PLACEHOLDER]"}


# ------------------------------------------------------------------- run --
def run_cascade(asof=None) -> pd.DataFrame:
    navs = fb.load_navs()
    asof = pd.Timestamp(asof) if asof else navs.index.max()

    print("Loading universe sector map (Industry column)...")
    sector_map = load_sector_map()
    symbols = list(sector_map.keys())
    print(f"  {len(symbols)} symbols, {len(set(sector_map.values()))} industries")

    print("Loading universe prices...")
    prices = load_universe_prices(symbols)
    print(f"  {len(prices)}/{len(symbols)} symbols priced")

    print("Computing GLOBAL / NATIONAL layers (once)...")
    g = global_layer(asof)
    n = national_layer(asof)

    print("Building sector composites (once per industry)...")
    sector_adj = build_sector_composites(sector_map, prices, asof)

    rows = []
    for t in symbols:
        industry = sector_map.get(t, "UNKNOWN")
        s = sector_adj.get(industry, {"adj": 0.0, "n_peers": 0,
                                       "rationale": f"sector={industry}: not found -> neutral 0",
                                       "tag": "[INFERENCE/approx]"})
        st = stock_layer(t)
        net = g["adj"] + n["adj"] + s["adj"] + st["adj"]
        rows.append({
            "symbol": t,
            "asof": asof.date().isoformat(),
            "sector": industry,
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
            "has_price_data": t in prices,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = run_cascade()
    out = RESULTS / "universe_cascade_adjustments.parquet"
    df.to_parquet(out, index=False)
    print("wrote", out, df.shape)
    print(f"\nSector sizes (priced peers):")
    print(df.drop_duplicates("sector")[["sector", "n_sector_peers"]]
          .sort_values("n_sector_peers", ascending=False).to_string(index=False))
    print(f"\nSingleton sectors (n_peers<=1): "
          f"{sorted(df[df.n_sector_peers <= 1]['sector'].unique().tolist())}")
    print(df[["symbol", "sector", "n_sector_peers", "global_adj",
              "national_adj", "sector_adj", "net_adj"]].head(10).to_string(index=False))
