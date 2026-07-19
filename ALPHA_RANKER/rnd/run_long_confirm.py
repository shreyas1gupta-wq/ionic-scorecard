"""
WAVE-2 worker task (2026-07-17): confirm current top factors across REAL bear
regimes (2008/2011/2020) using the 21-year panel_long.parquet (969 symbols,
249 monthly rebalances, 2005-04 -> 2025-12).

Factors confirmed at 1Y AND 5Y (basis='resid'):
  - 65DMA stack & slope (vs 50DMA) -- builders_ma.py logic, replicated on the
    LONG close cube (cube_close_long.parquet) instead of the short cube.
  - vol-scaled-momentum-12m (H004) + rankband_b10 refinement (builders_w2_volmom.py)
  - 12-1 residual momentum (H003) -- daily-beta-residual construction (builders_mom.py)
  - earnings-yield (H014) -- MASTER_fundamentals_pit.parquet, PIT via available_date
  - Weinstein stage-2 (H009) -- builders_oneil.py logic, on the long cube

Every factor goes through the SAME harness.evaluate() as the short-panel work
(no redefinition of IC/DSR/PBO/lag/placebo math). Rows with a disc_event_in_window_<h>
flag (>0) for the relevant horizon are EXCLUDED before scoring (corporate-action /
data-error contamination guard, per PANEL_SCHEMA.md addendum instruction).

Cards written to rnd/cards/LONG_<id>_<horizon>.json. Additionally computes a
bear-year (2008/2011/2020) vs other-years IC split directly (not just the
harness's regime_trend-label breakdown) since that is the specific ask.
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent
sys.path.insert(0, str(RND_DIR / "lib"))
import harness  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
CUBE_BENCH_LONG = RND_DIR / "panel" / "cube_bench_long.parquet"
FUND_PATH = RND_DIR.parent / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"
CARDS_DIR = RND_DIR / "cards"
BEAR_YEARS = {2008, 2011, 2020}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 0. load panel + cubes
# ---------------------------------------------------------------------------
def load_all():
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    close = pd.read_parquet(CUBE_CLOSE_LONG)
    close.index = pd.to_datetime(close.index)
    bench = pd.read_parquet(CUBE_BENCH_LONG)["NIFTY500"]
    bench.index = pd.to_datetime(bench.index)
    return panel, close, bench


def _panel_dates(panel: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(panel["date"].unique()))


def _to_long_factor(wide: pd.DataFrame, dates: pd.DatetimeIndex) -> pd.Series:
    sub = wide.reindex(dates)
    f = sub.stack()
    f.index.names = ["date", "symbol"]
    return f.rename("factor")


def _rank_combine(components: list, dates: pd.DatetimeIndex) -> pd.Series:
    ranked = []
    for comp in components:
        sel = comp.reindex(dates)
        r = sel.rank(axis=1, pct=True, na_option="keep")
        ranked.append(r)
    stacked = [c.stack() for c in ranked]
    combo = pd.concat(stacked, axis=1).mean(axis=1, skipna=True)
    combo.index.names = ["date", "symbol"]
    return combo.rename("factor")


def apply_rank_band(factor: pd.Series, band: float = 0.10) -> pd.Series:
    f = factor.rename("factor").reset_index()
    f["date"] = pd.to_datetime(f["date"])
    dates = sorted(f["date"].unique())
    last_pct = {}
    rows = []
    for d in dates:
        g = f.loc[f["date"] == d].set_index("symbol")["factor"]
        pct = g.rank(pct=True)
        eff = {}
        for sym, p in pct.items():
            prev = last_pct.get(sym)
            eff[sym] = p if (prev is None or abs(p - prev) > band) else prev
        last_pct.update(eff)
        for sym, val in eff.items():
            rows.append((d, sym, val))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


# ---------------------------------------------------------------------------
# 1. factor builders (long-cube versions of builders_ma / builders_mom /
#    builders_oneil / builders_w2_volmom / builders_value logic)
# ---------------------------------------------------------------------------
def build_dma_stack(close, dates, fast_n, mid_n=150, slow_n=200):
    ma_fast = close.rolling(fast_n, min_periods=fast_n).mean()
    ma_mid = close.rolling(mid_n, min_periods=mid_n).mean()
    ma_slow = close.rolling(slow_n, min_periods=slow_n).mean()
    score = (close > ma_fast).astype(int) + (ma_fast > ma_mid).astype(int) + (ma_mid > ma_slow).astype(int)
    score = score.where(ma_fast.notna() & ma_mid.notna() & ma_slow.notna())
    return _to_long_factor(score, dates)


def build_dma_slope(close, dates, n, lookback=21):
    ma = close.rolling(n, min_periods=n).mean()
    slope = ma / ma.shift(lookback) - 1.0
    return _to_long_factor(slope, dates)


def build_vol_scaled_mom(panel, close, dates, window_days, vol_col):
    vol_lookup = panel.set_index(["date", "symbol"])[vol_col]
    rows = []
    idx = close.index
    for d in dates:
        if d not in idx:
            continue
        loc = idx.get_loc(d)
        if loc < window_days:
            continue
        p_t = close.iloc[loc]
        p_t0 = close.iloc[loc - window_days]
        ret = (p_t / p_t0 - 1.0).dropna()
        for sym, val in ret.items():
            vol = vol_lookup.get((d, sym), np.nan)
            if pd.isna(vol) or vol <= 0:
                continue
            rows.append((d, sym, val / vol))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


def build_mom_resid_12_1(close, bench, dates):
    daily_ret = close.pct_change()
    bench_ret = bench.pct_change()
    cov = daily_ret.rolling(252, min_periods=126).cov(bench_ret)
    var = bench_ret.rolling(252, min_periods=126).var()
    beta = cov.div(var, axis=0)
    resid = daily_ret.sub(beta.mul(bench_ret, axis=0))
    idx = resid.index
    rows = []
    for d in dates:
        if d not in idx:
            continue
        loc = idx.get_loc(d)
        if loc < 273:
            continue
        window = resid.iloc[loc - 251: loc - 20]
        cov_ok = window.notna().mean() >= 0.80
        cum = (1.0 + window.fillna(0.0)).prod() - 1.0
        cum = cum.where(cov_ok)
        for sym, val in cum.dropna().items():
            rows.append((d, sym, val))
    out = pd.DataFrame(rows, columns=["date", "symbol", "factor"])
    return out.set_index(["date", "symbol"])["factor"]


def build_stage2(close, bench, dates):
    ma150 = close.rolling(150, min_periods=150).mean()
    above_ma = close / ma150 - 1.0
    ma_slope = ma150 / ma150.shift(21) - 1.0
    stock_126 = close / close.shift(126) - 1.0
    bench_126 = bench / bench.shift(126) - 1.0
    rs = stock_126.sub(bench_126, axis=0)
    gate = (above_ma > 0) & (ma_slope > 0) & (rs > 0)
    return _rank_combine([above_ma.where(gate), ma_slope.where(gate), rs.where(gate)], dates)


def build_earnings_yield(panel, close, dates):
    ds = panel[["date", "symbol"]].drop_duplicates()
    fund = pd.read_parquet(FUND_PATH)
    fund = fund[fund["nse_symbol"].notna()].copy()
    fund["available_date"] = pd.to_datetime(fund["available_date"])
    eps = fund[fund["metric_norm"] == "eps in rs"].dropna(subset=["value", "available_date"]).copy()
    eps = eps.sort_values(["nse_symbol", "fiscal_year", "is_fresh", "available_date"])
    eps = eps.drop_duplicates(["nse_symbol", "fiscal_year"], keep="last")
    eps = eps[["nse_symbol", "value", "available_date"]].rename(
        columns={"nse_symbol": "symbol", "value": "eps_ttm", "available_date": "date"}).sort_values("date")

    left = ds.rename(columns={"symbol": "symbol"}).sort_values("date").copy()
    left["symbol"] = left["symbol"].astype(str)
    right = eps.copy()
    right["symbol"] = right["symbol"].astype(str)
    m = pd.merge_asof(left, right, on="date", by="symbol", direction="backward")

    idx_name = close.index.name or "index"
    price_long = close.reset_index().melt(id_vars=idx_name, var_name="symbol", value_name="price")
    price_long = price_long.rename(columns={idx_name: "date"})
    price_long["date"] = pd.to_datetime(price_long["date"])
    price_long = price_long.dropna(subset=["price"])

    mm = m.merge(price_long, on=["date", "symbol"], how="inner")
    mm = mm[(mm["price"] > 0) & mm["eps_ttm"].notna()]
    mm["factor"] = mm["eps_ttm"] / mm["price"]
    return mm.set_index(["date", "symbol"])["factor"].replace([np.inf, -np.inf], np.nan).dropna()


# ---------------------------------------------------------------------------
# 2. bear-year vs other-year IC (direct, not the harness regime_trend label)
# ---------------------------------------------------------------------------
def bear_vs_other_ic(factor: pd.Series, panel: pd.DataFrame, target_col: str, min_names: int = 20):
    f = factor.rename("factor").reset_index()
    f["date"] = pd.to_datetime(f["date"])
    p = panel[["date", "symbol", target_col]].rename(columns={target_col: "target"})
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target"])
    ic_rows = []
    for d, g in merged.groupby("date"):
        if len(g) < min_names:
            continue
        rho, _ = stats.spearmanr(g["factor"], g["target"])
        ic_rows.append({"date": d, "ic": rho})
    ic_df = pd.DataFrame(ic_rows)
    if ic_df.empty:
        return {"bear_ic_2008_11_20": None, "other_ic": None, "n_bear_dates": 0, "n_other_dates": 0}
    ic_df["year"] = ic_df["date"].dt.year
    bear = ic_df[ic_df["year"].isin(BEAR_YEARS)]
    other = ic_df[~ic_df["year"].isin(BEAR_YEARS)]
    return {
        "bear_ic_2008_11_20": float(bear["ic"].mean()) if len(bear) else None,
        "other_ic": float(other["ic"].mean()) if len(other) else None,
        "n_bear_dates": int(len(bear)), "n_other_dates": int(len(other)),
        "bear_ic_by_year": {int(y): float(g["ic"].mean()) for y, g in bear.groupby("year")},
    }


# ---------------------------------------------------------------------------
# 3. main
# ---------------------------------------------------------------------------
def main():
    panel, close, bench = load_all()
    dates = _panel_dates(panel)
    log(f"panel_long: {panel.shape}, {panel['date'].nunique()} dates, {panel['symbol'].nunique()} symbols")
    log(f"cube_close_long: {close.shape}")

    log("Building factors...")
    factors = {}
    factors["H001_stack65"] = build_dma_stack(close, dates, fast_n=65)
    factors["H001_stack50"] = build_dma_stack(close, dates, fast_n=50)
    factors["H001_slope65"] = build_dma_slope(close, dates, n=65)
    factors["H001_slope50"] = build_dma_slope(close, dates, n=50)
    log("  MA stack/slope done")
    factors["H004_mom_sharpe12m"] = build_vol_scaled_mom(panel, close, dates, 252, "vol_252")
    factors["H004_rankband_b10"] = apply_rank_band(factors["H004_mom_sharpe12m"], band=0.10)
    log("  vol-scaled mom + rankband done")
    factors["H003_mom121_resid"] = build_mom_resid_12_1(close, bench, dates)
    log("  12-1 resid mom done")
    factors["H009_stage2"] = build_stage2(close, bench, dates)
    log("  stage2 done")
    factors["H014_earnings_yield"] = build_earnings_yield(panel, close, dates)
    log("  earnings yield done")

    family_map = {
        "H001_stack65": "H001", "H001_stack50": "H001", "H001_slope65": "H001", "H001_slope50": "H001",
        "H004_mom_sharpe12m": "H004", "H004_rankband_b10": "H004",
        "H003_mom121_resid": "H003", "H009_stage2": "H009", "H014_earnings_yield": "H014",
    }

    summary = []
    for fid, factor in factors.items():
        for horizon in ("1Y", "5Y"):
            lbl_raw = f"fwd_ret_{horizon}_raw"
            lbl_resid = f"fwd_ret_{horizon}_resid"
            disc_col = f"disc_event_in_window_{horizon}"
            p2 = panel.copy()
            mask = p2[disc_col].fillna(0) > 0
            n_excluded = int(mask.sum())
            p2.loc[mask, [lbl_raw, lbl_resid]] = np.nan

            factor_id = f"LONG_{fid}_{horizon}"
            log(f"Evaluating {factor_id} (excluding {n_excluded} disc-flagged rows)...")
            card = harness.evaluate(
                factor, horizon, return_basis="resid", factor_id=factor_id,
                panel=p2, panel_source="real_long_panel_long_history",
                family=family_map[fid], write_card=True, cards_dir=CARDS_DIR,
            )
            bear_split = bear_vs_other_ic(factor, p2, lbl_resid)
            card["bear_split_2008_11_20"] = bear_split
            (CARDS_DIR / f"{factor_id}.json").write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")

            ic = card.get("ic", {})
            dec = card.get("deciles", {})
            pbo = card.get("pbo", {})
            reg = card.get("regime_breakdown", {}).get("regime_trend", {})
            summary.append({
                "factor": fid, "horizon": horizon,
                "IC_IR_long": ic.get("ic_ir"), "IC_mean": ic.get("ic_mean"),
                "mono": dec.get("monotonicity"), "PBO_long": pbo.get("pbo"),
                "n_dates": card.get("n_dates"), "n_obs": card.get("n_obs"),
                "n_excluded_disc": n_excluded,
                "bull_IC_regimetrend": reg.get("bull"), "bear_IC_regimetrend": reg.get("bear"),
                "bear_ic_2008_11_20": bear_split.get("bear_ic_2008_11_20"),
                "other_ic": bear_split.get("other_ic"),
                "n_bear_dates": bear_split.get("n_bear_dates"),
                "verdict": card.get("verdict"),
            })
            log(f"  -> IC_IR={ic.get('ic_ir'):.3f}  mono={dec.get('monotonicity')}  "
                f"PBO={pbo.get('pbo')}  bear_2008_11_20_IC={bear_split.get('bear_ic_2008_11_20')}  "
                f"verdict={card.get('verdict')}")

    summ_df = pd.DataFrame(summary)
    out_csv = RND_DIR / "reports" / "WAVE2_LONG_confirm_summary.csv"
    summ_df.to_csv(out_csv, index=False)
    log(f"Saved summary: {out_csv}")
    print(summ_df.to_string())


if __name__ == "__main__":
    main()
