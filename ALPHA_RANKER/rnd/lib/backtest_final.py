"""
CAPSTONE PORTFOLIO BACKTEST -- Arjun Rao (Quant Head), 2026-07-17.

Builds the actual TRADEABLE portfolio equity curve of the FINAL 1Y ALPHA_RANKER
composite (rnd/FINAL_MODEL.md S2): value_EY + PLAIN 12-1 residual momentum +
trend_ma65_slope + quality_QMJ + bs_issuance(net-issuance, -) + bs_asset_growth(-)
+ quality_cfo_pat, SIMPLE RANK-AVERAGE, monthly rebalance with 10pct rank-band
hysteresis, breadth+VIX exposure-scalar sizing (long portfolio only), net of
Shreyas_Ionic_AMC/06_TRADING_DESK/COST_STANDARDS.md (APPROVED per D-021, but the
harness's bps-per-tier blend is itself an [INFERENCE] arithmetic combination --
flagged in FND_harness.md, not re-litigated here).

No new lookahead surface: every leg is REUSED from the already-PIT-audited
capstone_legs.parquet cache (built by lib/run_capstone.py off panel_long.parquet
builders) EXCEPT the PLAIN 12-1 residual momentum, which was NOT cached (only
its peer-relative sibling was) -- rebuilt here via the SAME, already-audited
run_long_confirm.build_mom_resid_12_1(), unmodified.

DISCLOSED CORRECTION vs run_capstone.py's exposure overlay: that script's
breadth scalar used `breadth_m.rank(pct=True)` -- a FULL-SAMPLE percentile rank,
which uses the ENTIRE 21-year distribution (including future dates) to rank a
value in e.g. 2008. That is lookahead. This script replaces it with an
EXPANDING (causal, in-sample-to-date-only) percentile rank. The India-VIX leg
of the exposure scalar is a NEW addition (FINAL_MODEL.md S3 mentions it
qualitatively but run_capstone.py's validated overlay used breadth ONLY) --
flagged [INFERENCE], not independently validated the way the breadth-only
overlay was.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent                      # ALPHA_RANKER/rnd
ALPHA_RANKER_DIR = RND_DIR.parent                   # ALPHA_RANKER
REPO_ROOT = ALPHA_RANKER_DIR.parent                 # NIFTY 500 root
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))
sys.path.insert(0, str(REPO_ROOT / "Shreyas_Ionic_AMC" / "04_RND_LAB" / "lib"))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402
import guards as G  # noqa: E402  (mandatory landmine-guard import, D-028/CLAUDE.md)

PANEL_LONG = RND_DIR / "panel" / "panel_long.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
CUBE_BENCH_LONG = RND_DIR / "panel" / "cube_bench_long.parquet"
CAPSTONE_LEGS = RND_DIR / "panel" / "capstone_legs.parquet"
MARKET_STATE = RND_DIR / "panel" / "market_state.parquet"
MACRO_STATE = RND_DIR / "panel" / "macro_state.parquet"
RESULTS_DIR = RND_DIR / "results"
REPORTS_DIR = RND_DIR / "reports"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Parameters (all disclosed here; kept <=5 "free" choices per RESEARCH_SOP cap;
# rank-band + quintile + min-legs-present are DATA-HYGIENE gates already used
# elsewhere in this codebase, not newly fitted on this backtest's own output).
# ---------------------------------------------------------------------------
FINAL_1Y_LEGS = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
                 "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
MIN_LEGS_PRESENT = 4        # majority of 7 -- names scored off <4 legs are dropped that month
RANK_BAND = 0.10            # hysteresis band (reused from run_long_confirm.apply_rank_band)
QUINTILE = 0.20             # top/bottom 20%
MIN_NAMES_PER_DATE = 20     # matches harness.evaluate's min_names_per_date default
EXPOSURE_FLOOR = 0.5        # matches run_capstone.py's validated breadth-scalar floor
VIX_PANIC_PCTL = 0.80       # India-VIX expanding percentile above which we stop de-risking further
VIX_PANIC_FLOOR = 0.70      # NEW, unvalidated addition -- disclosed in FINAL_BACKTEST.md caveats


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Causal expanding percentile rank (fixes the full-sample-rank lookahead bug)
# ---------------------------------------------------------------------------
def expanding_pct_rank(s: pd.Series, min_hist: int = 12) -> pd.Series:
    vals = s.values.astype(float)
    out = np.full(len(vals), np.nan)
    for i in range(len(vals)):
        if np.isnan(vals[i]):
            continue
        window = vals[: i + 1]
        window = window[~np.isnan(window)]
        if len(window) < min_hist:
            continue
        out[i] = float((window <= vals[i]).mean())
    return pd.Series(out, index=s.index)


# ---------------------------------------------------------------------------
# Leg assembly
# ---------------------------------------------------------------------------
def load_legs(panel: pd.DataFrame):
    dates = LC._panel_dates(panel)
    close = pd.read_parquet(CUBE_CLOSE_LONG)
    close.index = pd.to_datetime(close.index)
    bench = pd.read_parquet(CUBE_BENCH_LONG)["NIFTY500"]
    bench.index = pd.to_datetime(bench.index)

    log("Building PLAIN 12-1 residual momentum (mom_resid_plain) -- not cached; "
        "the cached mom_resid_peer wraps this in sector_analytics.peer_relative, "
        "which FINAL_MODEL.md S1 says REVERSES on the full 21yr (bull-panel artifact).")
    mom_plain = LC.build_mom_resid_12_1(close, bench, dates)

    cached = pd.read_parquet(CAPSTONE_LEGS)
    cached["date"] = pd.to_datetime(cached["date"])
    legs = {}
    for name in ["value_EY", "trend_ma65_slope", "quality_QMJ", "bs_issuance",
                 "bs_asset_growth", "quality_cfo_pat"]:
        sub = cached[cached["leg"] == name].set_index(["date", "symbol"])["value"]
        legs[name] = sub
    legs["mom_resid_plain"] = mom_plain
    for name in FINAL_1Y_LEGS:
        log(f"  leg {name}: n={len(legs[name])}, "
            f"dates=({legs[name].index.get_level_values('date').min()},"
            f"{legs[name].index.get_level_values('date').max()})")
    return legs, close, bench


def build_composite(legs: dict) -> pd.Series:
    frames = []
    for name in FINAL_1Y_LEGS:
        r = legs[name].rename("v").reset_index()
        r.columns = ["date", "symbol", "v"]
        r["v"] = r.groupby("date")["v"].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])["v"].rename(name))
    wide = pd.concat(frames, axis=1)
    n_present = wide.notna().sum(axis=1)
    combo = wide.mean(axis=1, skipna=True).where(n_present >= MIN_LEGS_PRESENT)
    combo = combo.dropna().rename("composite")
    log(f"Composite built: n_present>= {MIN_LEGS_PRESENT} of 7 legs, "
        f"{len(combo)} (date,symbol) obs, {combo.index.get_level_values('date').nunique()} dates")
    return combo


def apply_hysteresis(composite: pd.Series, band: float = RANK_BAND) -> pd.Series:
    """Re-rank within date, then only let a name's EFFECTIVE percentile move if
    it shifts more than `band` from its last effective value (limits turnover).
    Same mechanics as run_long_confirm.apply_rank_band, applied to the final
    composite instead of a single factor."""
    f = composite.reset_index()
    f.columns = ["date", "symbol", "composite"]
    dates = sorted(f["date"].unique())
    last_pct = {}
    rows = []
    for d in dates:
        g = f.loc[f["date"] == d].set_index("symbol")["composite"]
        pct = g.rank(pct=True)
        eff = {}
        for sym, p in pct.items():
            prev = last_pct.get(sym)
            eff[sym] = p if (prev is None or abs(p - prev) > band) else prev
        last_pct.update(eff)
        for sym, val in eff.items():
            rows.append((d, sym, val))
    out = pd.DataFrame(rows, columns=["date", "symbol", "eff_pct"])
    return out.set_index(["date", "symbol"])["eff_pct"]


# ---------------------------------------------------------------------------
# Exposure scalar (breadth, causal-expanding-rank fixed + India-VIX panic floor)
# ---------------------------------------------------------------------------
def build_exposure(panel_dates: pd.DatetimeIndex) -> pd.DataFrame:
    ms = pd.read_parquet(MARKET_STATE)
    ms["date"] = pd.to_datetime(ms["date"])
    ms = ms.sort_values("date").set_index("date")
    breadth = ms["breadth_pct_above_200dma"].reindex(panel_dates)
    breadth_causal_pctl = expanding_pct_rank(breadth, min_hist=12)
    exposure_breadth = (0.5 + 0.5 * breadth_causal_pctl).clip(EXPOSURE_FLOOR, 1.0)
    # pre-warmup (no breadth signal yet): default to full exposure (neutral, disclosed)
    exposure_breadth = exposure_breadth.fillna(1.0)

    macro = pd.read_parquet(MACRO_STATE)
    macro["date"] = pd.to_datetime(macro["date"])
    macro = macro.sort_values("date")
    vix_pctl_own = expanding_pct_rank(macro.set_index("date")["india_vix"], min_hist=12)
    left_dates = pd.DataFrame({"date": pd.DatetimeIndex(panel_dates).astype("datetime64[ns]")})
    right = vix_pctl_own.rename("vix_pctl").reset_index()
    right["date"] = pd.to_datetime(right["date"]).astype("datetime64[ns]")
    vix_aligned = pd.merge_asof(
        left_dates.sort_values("date"), right.sort_values("date"),
        on="date", direction="backward", tolerance=pd.Timedelta(days=45),
    ).set_index("date")["vix_pctl"]

    exposure = exposure_breadth.copy()
    panic = vix_aligned > VIX_PANIC_PCTL
    exposure = exposure.where(~panic.fillna(False), other=np.maximum(exposure, VIX_PANIC_FLOOR))
    exposure = exposure.clip(EXPOSURE_FLOOR, 1.0)

    out = pd.DataFrame({
        "breadth_raw": breadth, "breadth_causal_pctl": breadth_causal_pctl,
        "vix_causal_pctl": vix_aligned, "exposure": exposure,
    })
    return out


# ---------------------------------------------------------------------------
# Portfolio realization
# ---------------------------------------------------------------------------
def realize_portfolios(eff_pct: pd.Series, panel: pd.DataFrame):
    p = panel[["date", "symbol", "fwd_ret_1M_raw", "disc_event_in_window_1M", "mktcap_log"]].copy()
    p["date"] = pd.to_datetime(p["date"])
    eff = eff_pct.rename("eff_pct").reset_index()
    m = eff.merge(p, on=["date", "symbol"], how="inner")
    # data-quality exclusion (NOT an alpha filter): drop rows whose forward
    # return window contains a flagged discontinuity (corporate-action / data
    # error contamination guard, per PANEL_SCHEMA.md + run_long_confirm.py precedent)
    n_before = len(m)
    m = m[m["disc_event_in_window_1M"].fillna(0) <= 0]
    n_excluded = n_before - len(m)
    m = m.dropna(subset=["fwd_ret_1M_raw"])

    tier_bps = harness._read_cost_standards_bps()
    cost_source = tier_bps["source"]
    tier_bps_rt = tier_bps["tier_bps_rt"]

    rows = []
    prev_top, prev_bot = set(), set()
    dates = sorted(m["date"].unique())
    for d in dates:
        g = m[m["date"] == d]
        if len(g) < MIN_NAMES_PER_DATE:
            continue
        top = set(g.loc[g["eff_pct"] >= (1 - QUINTILE), "symbol"])
        bot = set(g.loc[g["eff_pct"] <= QUINTILE, "symbol"])
        if not top or not bot:
            continue
        top_df = g[g["symbol"].isin(top)]
        bot_df = g[g["symbol"].isin(bot)]
        top_ret = float(top_df["fwd_ret_1M_raw"].mean())
        bot_ret = float(bot_df["fwd_ret_1M_raw"].mean())

        added_top = top - prev_top
        turn_top = len(added_top) / len(top) if top else 0.0
        added_bot = bot - prev_bot
        turn_bot = len(added_bot) / len(bot) if bot else 0.0

        tiers = harness._mktcap_tier(top_df.set_index("symbol")["mktcap_log"])
        tier_counts = tiers.value_counts(normalize=True).to_dict()
        blended_bps_top = sum(tier_counts.get(t, 0) * tier_bps_rt.get(t, 25) for t in
                               ["large", "mid", "small", "micro"])
        tiers_b = harness._mktcap_tier(bot_df.set_index("symbol")["mktcap_log"])
        tier_counts_b = tiers_b.value_counts(normalize=True).to_dict()
        blended_bps_bot = sum(tier_counts_b.get(t, 0) * tier_bps_rt.get(t, 25) for t in
                               ["large", "mid", "small", "micro"])

        cost_top = turn_top * (blended_bps_top / 10000.0)
        cost_bot = turn_bot * (blended_bps_bot / 10000.0)

        rows.append({
            "date": d, "n_top": len(top), "n_bot": len(bot), "n_universe": len(g),
            "top_ret_gross": top_ret, "bot_ret_gross": bot_ret,
            "turn_top": turn_top, "turn_bot": turn_bot,
            "cost_top_bps_rt": blended_bps_top, "cost_bot_bps_rt": blended_bps_bot,
            "top_ret_net": top_ret - cost_top, "bot_ret_net": bot_ret - cost_bot,
            "top_ret_net_2x": top_ret - 2 * cost_top, "bot_ret_net_2x": bot_ret - 2 * cost_bot,
        })
        prev_top, prev_bot = top, bot

    out = pd.DataFrame(rows).set_index("date")
    return out, n_excluded, cost_source


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------
def compute_stats(ret: pd.Series) -> dict:
    r = ret.dropna()
    if len(r) < 6:
        return {}
    ann_ret = float((1 + r).prod() ** (12 / len(r)) - 1)
    ann_vol = float(r.std(ddof=1) * np.sqrt(12))
    sharpe = float(r.mean() / r.std(ddof=1) * np.sqrt(12)) if r.std(ddof=1) > 0 else np.nan
    downside = r[r < 0]
    sortino = float(r.mean() / downside.std(ddof=1) * np.sqrt(12)) if len(downside) > 1 and downside.std(ddof=1) > 0 else np.nan
    eq = (1 + r).cumprod()
    peak = eq.cummax()
    dd = eq / peak - 1.0
    max_dd = float(dd.min())
    return {"CAGR": ann_ret, "ann_vol": ann_vol, "Sharpe": sharpe, "Sortino": sortino,
            "maxDD": max_dd, "n_months": int(len(r))}


def calendar_year_returns(ret: pd.Series) -> pd.Series:
    r = ret.dropna()
    yr = r.groupby(r.index.year).apply(lambda x: float((1 + x).prod() - 1))
    return yr


def degenerate_check(ret: pd.Series, label: str) -> list:
    """Monthly-frequency adaptation of guards.degenerate_flags (that helper
    assumes DAILY returns / sqrt(252); disclosed deviation, same thresholds)."""
    flags = []
    r = ret.dropna()
    if len(r) < 12:
        return flags
    sharpe = r.mean() / (r.std(ddof=1) + 1e-12) * np.sqrt(12)
    eq = (1 + r).cumprod()
    x = np.arange(len(eq))
    r2 = np.corrcoef(x, eq.values)[0, 1] ** 2
    if sharpe > 4:
        flags.append(f"[{label}] Sharpe {sharpe:.1f} > 4")
    if r2 > 0.98:
        flags.append(f"[{label}] equity R^2 {r2:.3f} > 0.98 (too smooth)")
    win = (r > 0).mean()
    if win > 0.85:
        flags.append(f"[{label}] monthly win rate {win:.0%} suspiciously high")
    return flags


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    log("Loading panel_long.parquet ...")
    panel = pd.read_parquet(PANEL_LONG)
    panel["date"] = pd.to_datetime(panel["date"])
    log(f"panel_long: {panel.shape}, dates={panel['date'].nunique()} "
        f"({panel['date'].min()} -> {panel['date'].max()}), symbols={panel['symbol'].nunique()}")

    legs, close, bench = load_legs(panel)
    composite = build_composite(legs)
    eff_pct = apply_hysteresis(composite)

    log("Realizing monthly portfolio returns (top/bottom quintile, cost-adjusted) ...")
    port, n_excluded, cost_source = realize_portfolios(eff_pct, panel)
    log(f"Portfolio dates: {len(port)}, disc-event rows excluded: {n_excluded}, cost source: {cost_source}")

    log("Building exposure scalar (breadth causal-expanding-rank + India-VIX panic floor) ...")
    exposure_df = build_exposure(pd.DatetimeIndex(port.index))
    port = port.join(exposure_df)

    port["ls_ret_net"] = port["top_ret_net"] - port["bot_ret_net"]
    port["top_ret_scaled"] = port["top_ret_net"] * port["exposure"]
    port["top_ret_2x_scaled"] = port["top_ret_net_2x"] * port["exposure"]

    # NIFTY500 benchmark over the SAME monthly windows (panel-date to panel-date)
    bench_at_dates = bench.reindex(port.index, method="ffill")
    bench_ret = bench_at_dates.pct_change()
    port["nifty500_ret"] = bench_ret

    port.to_parquet(RESULTS_DIR / "final_equity_curve.parquet")
    log(f"Saved {RESULTS_DIR / 'final_equity_curve.parquet'} ({port.shape})")

    # ---- stats ----
    stats_scaled = compute_stats(port["top_ret_scaled"])
    stats_unscaled = compute_stats(port["top_ret_net"])
    stats_ls = compute_stats(port["ls_ret_net"])
    stats_nifty = compute_stats(port["nifty500_ret"])
    stats_2x = compute_stats(port["top_ret_2x_scaled"])

    yr_scaled = calendar_year_returns(port["top_ret_scaled"])
    yr_unscaled = calendar_year_returns(port["top_ret_net"])
    yr_nifty = calendar_year_returns(port["nifty500_ret"])
    yr_ls = calendar_year_returns(port["ls_ret_net"])

    flags = (degenerate_check(port["top_ret_scaled"], "LONG scaled")
             + degenerate_check(port["top_ret_net"], "LONG unscaled")
             + degenerate_check(port["ls_ret_net"], "LONG-SHORT"))

    avg_turn = float(port["turn_top"].mean())

    # ---- RELIABLE-WINDOW check (disclosed data-thinness finding, 2026-07-17):
    # composite universe count explodes 49 -> 470 names between 2012-04-30 and
    # 2012-05-31 (value_EY coverage cliff in the underlying fundamentals source;
    # quality_cfo_pat stays <20 names until ~2015-16). Dates before this are
    # NOT a representative cross-section -- MIN_NAMES_PER_DATE=20 already drops
    # the worst of it (portfolio starts 2011-11), but 2011-11->2012-04 (n=22-49)
    # is still a thin/marginal stub. Report a RELIABLE sub-window (n_universe>=400)
    # alongside the full series so nobody mistakes 2011-2012 for real coverage.
    reliable = port[port["n_universe"] >= 400]
    reliable_stats = {
        "with_exposure_scalar": compute_stats(reliable["top_ret_scaled"]),
        "without_exposure_scalar": compute_stats(reliable["top_ret_net"]),
        "long_short_top_minus_bottom": compute_stats(reliable["ls_ret_net"]),
        "nifty500_benchmark": compute_stats(reliable["nifty500_ret"]),
        "window": [str(reliable.index.min()), str(reliable.index.max())],
        "calendar_years": {
            "with_scalar": calendar_year_returns(reliable["top_ret_scaled"]).to_dict(),
            "without_scalar": calendar_year_returns(reliable["top_ret_net"]).to_dict(),
            "long_short": calendar_year_returns(reliable["ls_ret_net"]).to_dict(),
            "nifty500": calendar_year_returns(reliable["nifty500_ret"]).to_dict(),
        },
    }
    log(f"RELIABLE window (n_universe>=400): {reliable.index.min()} -> {reliable.index.max()}, "
        f"{len(reliable)} months. With-scalar CAGR={reliable_stats['with_exposure_scalar'].get('CAGR')}")

    summary = {
        "reliable_window_n_universe_gte_400": reliable_stats,
        "with_exposure_scalar": stats_scaled,
        "without_exposure_scalar": stats_unscaled,
        "long_short_top_minus_bottom": stats_ls,
        "nifty500_benchmark": stats_nifty,
        "with_scalar_2x_cost_stress": stats_2x,
        "avg_monthly_turnover_top_quintile": avg_turn,
        "n_disc_event_rows_excluded": int(n_excluded),
        "cost_source": cost_source,
        "degenerate_flags": flags,
        "calendar_years": {
            "with_scalar": yr_scaled.to_dict(),
            "without_scalar": yr_unscaled.to_dict(),
            "long_short": yr_ls.to_dict(),
            "nifty500": yr_nifty.to_dict(),
        },
    }
    (REPORTS_DIR / "FINAL_BACKTEST_stats.json").write_text(
        json.dumps(summary, indent=2, default=str), encoding="utf-8")
    log(f"Wrote {REPORTS_DIR / 'FINAL_BACKTEST_stats.json'}")
    log(f"WITH scalar: {stats_scaled}")
    log(f"WITHOUT scalar: {stats_unscaled}")
    log(f"LONG-SHORT: {stats_ls}")
    log(f"NIFTY500: {stats_nifty}")
    log(f"Degenerate flags: {flags}")
    log("DONE.")


if __name__ == "__main__":
    main()
