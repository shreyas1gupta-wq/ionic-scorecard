"""
WAVE-2 runner: IDG-G-01 (op profitability), IDG-G-15 (profitability improvement),
IDG-G-02 (QMJ composite), IDG-G-12 (Buffett's-alpha composite).
Evaluated via the shared harness against panel_long.parquet (21yr, 249 monthly
dates, 2005-2025) at basis='resid', horizons 1Y AND 5Y, with per-regime
(regime_trend, regime_vol) IC breakdown -- the money-first, cross-regime test
this pass is chartered to run (quality/profitability expected regime-gold: a
bear-defensive leg like the confirmed earnings-yield card, per CONSOLIDATION.md
REGIME MAP). disc_event_in_window_<h> rows excluded per PANEL_SCHEMA.md guard
(same convention as rnd/run_long_confirm.py).

Also builds H014 earnings-yield on the SAME long panel (re-derived, not
imported, matching run_long_confirm.py's self-contained-per-worker convention)
purely as a DIAGNOSTIC correlation check for IDG-G-01's pre-registered kill
condition ("park if |corr| to H014 >0.6 -- then it is value in disguise").
"""
from __future__ import annotations
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
LIB_DIR = _THIS.parent
RND_DIR = LIB_DIR.parent
sys.path.insert(0, str(LIB_DIR))
import harness  # noqa: E402
import builders_w2_profq as bpq  # noqa: E402

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
FUND_PATH = RND_DIR.parent / "data" / "fundamentals" / "MASTER_fundamentals_pit.parquet"
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def load_all():
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    close = pd.read_parquet(CUBE_CLOSE_LONG)
    close.index = pd.to_datetime(close.index)
    return panel, close


def build_earnings_yield_diagnostic(panel: pd.DataFrame, close: pd.DataFrame) -> pd.Series:
    """H014 re-derivation (diagnostic only, for the IDG-G-01 corr-vs-value kill
    check) -- identical construction to rnd/run_long_confirm.py build_earnings_yield."""
    ds = panel[["date", "symbol"]].drop_duplicates()
    fund = pd.read_parquet(FUND_PATH)
    fund = fund[fund["nse_symbol"].notna()].copy()
    fund["available_date"] = pd.to_datetime(fund["available_date"])
    eps = fund[fund["metric_norm"] == "eps in rs"].dropna(subset=["value", "available_date"]).copy()
    eps = eps.sort_values(["nse_symbol", "fiscal_year", "is_fresh", "available_date"])
    eps = eps.drop_duplicates(["nse_symbol", "fiscal_year"], keep="last")
    eps = eps[["nse_symbol", "value", "available_date"]].rename(
        columns={"nse_symbol": "symbol", "value": "eps_ttm", "available_date": "date"}).sort_values("date")

    left = ds.sort_values("date").copy()
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


def main():
    panel, close = load_all()
    log(f"panel_long: {panel.shape}, {panel['date'].nunique()} dates, {panel['symbol'].nunique()} symbols")

    log("Building factors...")
    factors = {
        "IDGG01": bpq.build_op_profitability_factor(panel),
        "IDGG15": bpq.build_profitability_change_factor(panel),
        "IDGG02": bpq.build_qmj_composite(panel),
        "IDGG12": bpq.build_buffett_alpha_composite(panel),
    }
    log("  IDG-G-01/02/12/15 built")
    ey = build_earnings_yield_diagnostic(panel, close)
    log("  H014 EY diagnostic built")

    fresh_cov = {
        "IDGG01": bpq.freshness_coverage(panel, "op_at"),
        "IDGG15": bpq.freshness_coverage(panel, "op_at_delta"),
    }
    log(f"  DATA-TRUST freshness coverage (frac is_fresh>=0.5): {fresh_cov}")

    # diagnostic: IDG-G-01 vs H014 correlation (pre-registered kill check)
    aligned = pd.concat([factors["IDGG01"].rename("g01"), ey.rename("ey")], axis=1).dropna()
    corr_g01_ey = float(aligned["g01"].corr(aligned["ey"])) if len(aligned) > 30 else float("nan")
    log(f"  corr(IDG-G-01, H014-EY) on {len(aligned)} overlapping obs = {corr_g01_ey:.3f}")

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

            factor_id = f"{fid}_{horizon}"
            log(f"Evaluating {factor_id} (excluding {n_excluded} disc-flagged rows)...")
            card = harness.evaluate(
                factor, horizon, return_basis="resid", factor_id=factor_id,
                panel=p2, panel_source="real_long_panel_long_history",
                family=fid, write_card=True, cards_dir=CARDS_DIR,
            )
            if fid == "IDGG01":
                card["diagnostic_corr_vs_H014_EY"] = corr_g01_ey
            card["data_trust_fresh_coverage"] = fresh_cov.get(fid)
            (CARDS_DIR / f"{factor_id}.json").write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")

            ic = card.get("ic", {})
            dec = card.get("deciles", {})
            pbo = card.get("pbo", {})
            dsr = card.get("dsr", {})
            costs = card.get("costs", {})
            reg_trend = card.get("regime_breakdown", {}).get("regime_trend", {})
            reg_vol = card.get("regime_breakdown", {}).get("regime_vol", {})
            summary.append({
                "factor": fid, "horizon": horizon,
                "ic_mean": ic.get("ic_mean"), "ic_ir": ic.get("ic_ir"),
                "mono": dec.get("monotonicity"), "pbo": pbo.get("pbo"), "dsr": dsr.get("dsr"),
                "net_cost_ann": costs.get("net_of_cost_ann_return"),
                "lag_delta": card.get("lag_test", {}).get("lag_test_delta"),
                "placebo_ic": card.get("placebo", {}).get("placebo_ic"),
                "bull_ic": reg_trend.get("bull"), "sideways_ic": reg_trend.get("sideways"),
                "bear_ic": reg_trend.get("bear"),
                "lowvol_ic": reg_vol.get("low"), "normalvol_ic": reg_vol.get("normal"),
                "hivol_ic": reg_vol.get("high"),
                "n_dates": card.get("n_dates"), "n_obs": card.get("n_obs"),
                "n_excluded_disc": n_excluded,
                "verdict": card.get("verdict"),
            })
            log(f"  -> IC_IR={ic.get('ic_ir')}  mono={dec.get('monotonicity')}  "
                f"bear_IC={reg_trend.get('bear')}  hivol_IC={reg_vol.get('high')}  "
                f"verdict={card.get('verdict')}")

    summ_df = pd.DataFrame(summary)
    out_csv = REPORTS_DIR / "W2_profq_summary.csv"
    summ_df.to_csv(out_csv, index=False)
    (CARDS_DIR / "_W2_profq_summary.json").write_text(
        json.dumps({"corr_IDGG01_vs_H014EY": corr_g01_ey, "fresh_coverage": fresh_cov,
                    "rows": summary}, indent=2, default=str), encoding="utf-8")
    log(f"Saved summary: {out_csv}")
    print(summ_df.to_string())


if __name__ == "__main__":
    main()
