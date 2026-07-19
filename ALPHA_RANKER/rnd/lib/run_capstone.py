"""
CAPSTONE synthesis (ALPHA_RANKER) -- Arjun Rao (Quant Head), 2026-07-17.

Builds every CONFIRMED survivor leg (per rnd/CONSOLIDATION.md + rnd/SURVIVORS.md)
on the real 21yr panel_long.parquet, computes the cross-sectional orthogonality
matrix among them, drops redundant legs (|corr|>0.6, keep higher IC_IR x lower
turnover), assembles the per-horizon FINAL COMPOSITE as a SIMPLE RANK-AVERAGE of
the surviving legs, evaluates it via the shared harness (hard gates = lag+
placebo; PBO/DSR advisory per CONSOLIDATION harness-fix #1), and applies the
%>200DMA breadth exposure-scalar as a portfolio overlay.

No new lookahead surface: every leg is REUSED from an existing, already-
PIT-audited builder (builders_*.py) or from run_long_confirm.py's long-cube
reimplementations (same modules that already produced the LONG_/W2_* survivor
cards this synthesis is built on). This script does not redefine any factor.
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
RND_DIR = _THIS.parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
from harness import run_experiment, _decile_stats, _normalize_factor  # noqa: E402
import run_long_confirm as LC  # noqa: E402  (long-cube MA/mom/EY builders; guarded __main__)
import sector_analytics as SA  # noqa: E402  (peer_relative)
import builders_w2_dcf as bdcf  # noqa: E402
import builders_w2_profq as bprofq  # noqa: E402
import builders_w2_indiaqv as bindiaqv  # noqa: E402
import builders_w2_issuance as bissu  # noqa: E402
import builders_w2_lowrisk as blowrisk  # noqa: E402
import builders_w2_seas as bseas  # noqa: E402
import market_state as MS  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
STOCK_VAL_PATH = RND_DIR / "panel" / "stock_valuation_pit.parquet"
MARKET_STATE_PATH = RND_DIR / "panel" / "market_state.parquet"
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 0. load panel + build every leg (each a (date,symbol)-indexed pd.Series)
# ---------------------------------------------------------------------------
def build_all_legs(panel: pd.DataFrame, close, bench) -> dict:
    dates = LC._panel_dates(panel)
    legs = {}

    def _try(name, fn):
        t0 = time.time()
        try:
            s = fn()
            s = s.rename("factor") if isinstance(s, pd.Series) else s
            legs[name] = s
            log(f"  {name}: n={len(s)} dt={time.time()-t0:.1f}s")
        except Exception as e:
            log(f"  {name}: FAILED ({e!r})")

    _try("mom_resid_peer", lambda: SA.peer_relative(
        LC.build_mom_resid_12_1(close, bench, dates), level="sub_sector", method="z"))
    _try("trend_ma65_slope", lambda: LC.build_dma_slope(close, dates, n=65))
    _try("value_EY", lambda: LC.build_earnings_yield(panel, close, dates))
    _try("value_dcf_revgap", lambda: bdcf.make_revgap_builder(0.13, 0.05)(panel))
    _try("value_marketstate_M3", lambda: _build_m3(panel))
    _try("value_smallcap_M2", lambda: _build_m2())
    _try("quality_QMJ", lambda: bprofq.build_qmj_composite(panel))
    _try("quality_cfo_pat", lambda: bindiaqv.build_cum_cfo_pat_factor(panel))
    _try("bs_issuance", lambda: bissu.build_issuance_factor(panel))
    _try("bs_asset_growth", lambda: bissu.build_asset_growth_factor(panel))
    _try("defensive_BAB", lambda: (-panel.set_index(["date", "symbol"])["beta_252"]).dropna().rename("factor"))
    _try("seasonality", lambda: bseas.build_seasonality(panel))

    return legs


def _build_m3(panel):
    stock_val = pd.read_parquet(STOCK_VAL_PATH)
    market = pd.read_parquet(MARKET_STATE_PATH)
    sys.path.insert(0, str(RND_DIR / "lib"))
    import test_market_state as TMS
    return TMS.build_m3_factor(stock_val, market, metric="EY")


def _build_m2():
    stock_val = pd.read_parquet(STOCK_VAL_PATH)
    small = stock_val[stock_val["cap_tier"] == "small"][["date", "symbol", "EY"]].dropna()
    small["date"] = pd.to_datetime(small["date"])
    return small.set_index(["date", "symbol"])["EY"].rename("factor")


# ---------------------------------------------------------------------------
# 1. orthogonality matrix -- pairwise avg per-date Spearman corr
# ---------------------------------------------------------------------------
def pairwise_corr(legs: dict, min_names: int = 20) -> pd.DataFrame:
    names = list(legs.keys())
    mat = pd.DataFrame(np.nan, index=names, columns=names)
    n_obs = pd.DataFrame(0, index=names, columns=names)
    for i, a in enumerate(names):
        sa = legs[a].rename("a").reset_index()
        sa.columns = ["date", "symbol", "a"]
        for b in names[i:]:
            if a == b:
                mat.loc[a, b] = 1.0
                continue
            sb = legs[b].rename("b").reset_index()
            sb.columns = ["date", "symbol", "b"]
            m = sa.merge(sb, on=["date", "symbol"], how="inner")
            corrs = []
            for _, g in m.groupby("date"):
                if len(g) < min_names:
                    continue
                rho, _ = stats.spearmanr(g["a"], g["b"])
                if rho == rho:
                    corrs.append(rho)
            avg = float(np.mean(corrs)) if corrs else np.nan
            mat.loc[a, b] = avg
            mat.loc[b, a] = avg
            n_obs.loc[a, b] = len(corrs)
            n_obs.loc[b, a] = len(corrs)
    return mat, n_obs


# ---------------------------------------------------------------------------
# 2. per-leg harness eval (fresh, resume-safe) at given horizons
# ---------------------------------------------------------------------------
def eval_leg(fid, factor, horizon, panel, family):
    existing = CARDS_DIR / f"{fid}.json"
    if existing.exists():
        c = json.loads(existing.read_text(encoding="utf-8"))
        if c.get("status") == "OK":
            return c
    return run_experiment(fid, lambda p: factor, horizon, basis="resid", panel=panel,
                           panel_source="real_panel_long_capstone", family=family)


HORIZON_YEARS = {"1M": 1.0 / 12.0, "1Y": 1.0, "5Y": 5.0}


def v2_annualization(card: dict) -> dict:
    ann_old = card.get("long_short", {}).get("ann_return_LS", np.nan)
    cost_drag = card.get("costs", {}).get("ann_cost_drag", 0.0)
    horizon = card.get("horizon")
    if ann_old is None or not np.isfinite(ann_old):
        return {"gross_v2": np.nan, "net_v2": np.nan}
    mean_ls_period = ann_old / 12.0
    hy = HORIZON_YEARS.get(horizon, 1.0)
    gross_v2 = mean_ls_period / hy
    net_v2 = gross_v2 - (cost_drag if cost_drag is not None and np.isfinite(cost_drag) else 0.0)
    return {"gross_v2": gross_v2, "net_v2": net_v2}


def summarize_card(fid, card):
    ic = card.get("ic", {})
    dec = card.get("deciles", {})
    turn = card.get("turnover", {})
    ann = v2_annualization(card)
    return {
        "factor_id": fid, "horizon": card.get("horizon"), "status": card.get("status"),
        "ic_ir": ic.get("ic_ir"), "ic_mean": ic.get("ic_mean"), "mono": dec.get("monotonicity"),
        "turnover": turn.get("avg_top_decile_turnover"),
        "gross_LS_v2": ann.get("gross_v2"), "net_LS_v2": ann.get("net_v2"),
        "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
        "verdict_v1": card.get("verdict"),
    }


# ---------------------------------------------------------------------------
# 3. main
# ---------------------------------------------------------------------------
def main():
    log("Loading panel_long + long cubes...")
    panel, close, bench = LC.load_all()
    log(f"panel_long: {panel.shape}, dates={panel['date'].nunique()}, symbols={panel['symbol'].nunique()}, "
        f"range=({panel['date'].min()},{panel['date'].max()})")

    log("Building all survivor legs...")
    legs = build_all_legs(panel, close, bench)
    log(f"Built {len(legs)}/12 legs OK: {list(legs.keys())}")

    # cache to disk (long format) so a restart doesn't rebuild
    rows = []
    for name, s in legs.items():
        d = s.reset_index()
        d.columns = ["date", "symbol", "value"]
        d["leg"] = name
        rows.append(d)
    pd.concat(rows, ignore_index=True).to_parquet(LEGS_CACHE, index=False)
    log(f"Cached legs -> {LEGS_CACHE}")

    log("Computing orthogonality matrix (pairwise avg per-date Spearman)...")
    mat, nobs = pairwise_corr(legs)
    mat.to_csv(REPORTS_DIR / "orthogonality_matrix.csv")
    nobs.to_csv(REPORTS_DIR / "orthogonality_matrix_nobs.csv")
    log("Wrote orthogonality_matrix.csv")
    print(mat.round(3).to_string())

    # -------------------------------------------------------------------
    # per-leg fresh harness cards (1Y for all short-horizon-relevant legs,
    # 5Y for value/quality/bs legs) -- resume-safe
    # -------------------------------------------------------------------
    LEG_HORIZONS = {
        "mom_resid_peer": ["1Y", "5Y"],
        "trend_ma65_slope": ["1Y", "5Y"],
        "value_EY": ["1Y", "5Y"],
        "value_dcf_revgap": ["1Y", "5Y"],
        "value_marketstate_M3": ["5Y"],
        "value_smallcap_M2": ["1Y", "5Y"],
        "quality_QMJ": ["1Y", "5Y"],
        "quality_cfo_pat": ["1Y", "5Y"],
        "bs_issuance": ["1Y"],
        "bs_asset_growth": ["5Y"],
        "defensive_BAB": ["1Y"],
        "seasonality": ["1Y"],
    }
    FAMILY = {n: f"CAPSTONE_{n}" for n in legs}

    single_summaries = {}
    for name, hlist in LEG_HORIZONS.items():
        if name not in legs:
            continue
        for h in hlist:
            fid = f"CAPSTONE_{name}_{h}"
            log(f"Evaluating leg card {fid} ...")
            card = eval_leg(fid, legs[name], h, panel, FAMILY[name])
            single_summaries[fid] = summarize_card(fid, card)
            s = single_summaries[fid]
            log(f"  -> ic_ir={s['ic_ir']} mono={s['mono']} turn={s['turnover']} "
                f"net_LS_v2={s['net_LS_v2']} lag={s['lag_delta']} placebo={s['placebo_ic']}")

    (REPORTS_DIR / "CAPSTONE_leg_cards.json").write_text(
        json.dumps(single_summaries, indent=2, default=str), encoding="utf-8")
    log("Wrote CAPSTONE_leg_cards.json")

    # -------------------------------------------------------------------
    # composites per horizon (rank-average of surviving legs; MODEL_SPEC
    # horizon buckets, drops decided by orthogonality below in FINAL_MODEL.md)
    # -------------------------------------------------------------------
    def rank_avg(names, dates_index=None):
        frames = []
        for n in names:
            r = legs[n].rename("factor").reset_index()
            r.columns = ["date", "symbol", n]
            r[n] = r.groupby("date")[n].rank(pct=True)
            frames.append(r.set_index(["date", "symbol"])[n])
        wide = pd.concat(frames, axis=1)
        combo = wide.mean(axis=1, skipna=True)
        # require at least 2 of N legs present so a name isn't scored off 1 leg alone
        n_present = wide.notna().sum(axis=1)
        combo = combo.where(n_present >= min(2, len(names)))
        return combo.dropna().rename("factor")

    COMPOSITES = {
        "COMPO_1Y_final": ["mom_resid_peer", "trend_ma65_slope", "value_EY", "value_smallcap_M2"],
        "COMPO_1Y_all_equal": list(legs.keys()),
        "COMPO_5Y_final": ["value_EY", "value_dcf_revgap", "value_marketstate_M3",
                            "quality_QMJ", "quality_cfo_pat", "bs_asset_growth"],
        "COMPO_5Y_all_equal": list(legs.keys()),
    }

    compo_summaries = {}
    for cname, members in COMPOSITES.items():
        members = [m for m in members if m in legs]
        horizon = "1Y" if "1Y" in cname else "5Y"
        factor = rank_avg(members)
        fid = f"CAPSTONE_{cname}"
        log(f"Evaluating composite {fid} (members={members}) ...")
        existing = CARDS_DIR / f"{fid}.json"
        if existing.exists() and json.loads(existing.read_text(encoding="utf-8")).get("status") == "OK":
            card = json.loads(existing.read_text(encoding="utf-8"))
        else:
            card = harness.evaluate(factor, horizon, return_basis="resid", factor_id=fid,
                                     panel=panel, panel_source="real_panel_long_capstone",
                                     family="CAPSTONE_COMPO", write_card=True, cards_dir=CARDS_DIR)
        compo_summaries[fid] = summarize_card(fid, card)
        s = compo_summaries[fid]
        log(f"  -> ic_ir={s['ic_ir']} mono={s['mono']} turn={s['turnover']} "
            f"net_LS_v2={s['net_LS_v2']} lag={s['lag_delta']} placebo={s['placebo_ic']}")
        # stash the factor itself for the exposure-overlay step (1Y final only)
        if cname == "COMPO_1Y_final":
            COMPOSITES["_1Y_final_factor"] = factor
        if cname == "COMPO_5Y_final":
            COMPOSITES["_5Y_final_factor"] = factor

    (REPORTS_DIR / "CAPSTONE_composite_cards.json").write_text(
        json.dumps(compo_summaries, indent=2, default=str), encoding="utf-8")
    log("Wrote CAPSTONE_composite_cards.json")

    # -------------------------------------------------------------------
    # breadth exposure-scalar overlay on the 1Y final composite's LS series
    # -------------------------------------------------------------------
    log("Computing breadth (%>200DMA) off cube_close_long + overlay effect...")
    dma200 = close.rolling(200, min_periods=150).mean()
    above = (close > dma200)
    valid = close.notna() & dma200.notna()
    breadth = (above & valid).sum(axis=1) / valid.sum(axis=1).replace(0, np.nan)
    breadth = breadth.rename("breadth").to_frame()
    breadth.index = pd.to_datetime(breadth.index)
    monthly_dates = LC._panel_dates(panel)
    breadth_m = breadth.reindex(monthly_dates, method="ffill")["breadth"]
    breadth_pct = breadth_m.rank(pct=True)
    exposure = (0.5 + 0.5 * breadth_pct).clip(0.5, 1.0)

    factor_1y = COMPOSITES.get("_1Y_final_factor")
    lbl = harness._label_cols("1Y")
    base_cols = ["date", "symbol", "regime_trend", "regime_vol", "mktcap_log"]
    p = panel[base_cols + [lbl["resid"], lbl["raw"]]].copy().rename(
        columns={lbl["resid"]: "target_eval", lbl["raw"]: "target_raw"})
    p["date"] = pd.to_datetime(p["date"])
    f = _normalize_factor(factor_1y)
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    ls_ret_raw, _, _ = _decile_stats(merged, min_names=20)
    ls_ret_raw.index = pd.to_datetime(ls_ret_raw.index)

    exp_aligned = exposure.reindex(ls_ret_raw.index).fillna(method="ffill").fillna(1.0)
    ls_scaled = ls_ret_raw * exp_aligned

    def sharpe(r):
        return float(r.mean() / r.std(ddof=1) * np.sqrt(12)) if r.std(ddof=1) > 0 else np.nan

    def max_dd(r):
        eq = (1 + r.fillna(0)).cumprod()
        peak = eq.cummax()
        dd = eq / peak - 1.0
        return float(dd.min())

    overlay_result = {
        "n_periods": int(len(ls_ret_raw)),
        "base_sharpe": sharpe(ls_ret_raw), "base_maxDD": max_dd(ls_ret_raw),
        "base_ann_ret": float(ls_ret_raw.mean() * 12),
        "overlay_sharpe": sharpe(ls_scaled), "overlay_maxDD": max_dd(ls_scaled),
        "overlay_ann_ret": float(ls_scaled.mean() * 12),
        "exposure_rule": "exposure = clip(0.5 + 0.5*breadth_pct_rank, 0.5, 1.0); breadth = %names>200DMA off cube_close_long",
    }
    (REPORTS_DIR / "CAPSTONE_exposure_overlay.json").write_text(
        json.dumps(overlay_result, indent=2), encoding="utf-8")
    log(f"Exposure overlay result: {overlay_result}")

    log("DONE.")


if __name__ == "__main__":
    main()
