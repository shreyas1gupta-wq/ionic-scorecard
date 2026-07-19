"""
TICK worker (2026-07-17): W2SEC-C1 / C2 / C3 -- sector-child backlog items from
backlog_scout.json, tested on the 21-year `panel_long.parquet` (969 symbols,
249 monthly rebalances, 2005-04 -> 2025-12) instead of the short 61-month
`panel.parquet` the parent W2SEC-S1/S2/S3 cheap-tests ran on.

  C1: does sub-sector peer-relative residual momentum's cheap-test edge
      (IC_IR 0.92 vs plain 0.72 @1Y, 61 monthly obs) SURVIVE across real
      bears (2008/2011/2020) on the full 21yr sample?
  C2: does own-sector RS sharpen at sub_sector (62-bucket) granularity vs
      macro_sector (21-bucket), confirmed fresh on the long panel (no long
      macro-level baseline existed before this pass)?
  C3: sector-aware quality-momentum composite -- peer-relative (sub_sector)
      residual momentum (from C1) rank-combined with PLAIN (non-peer)
      earnings yield, since the WAVE-2 short-panel finding was asymmetric:
      peer-relative helps momentum but hurts value monotonicity (plain EY
      1.52 > peer EY 1.26 @1Y on the short panel).

Money-first (CONSOLIDATION.md / pragmatic_score_v2.py): hard gates are
lag_test_delta<=0.25 and |placebo_ic|<=0.02 only; PBO/DSR are reported but
advisory (single-factor CSCV PBO is structurally near-saturated at this
trial count per FND_harness.md disclosure, and DSR's global trial count is
punitive to a single family -- both flagged, neither used to KILL here).

Reuses vetted long-panel plumbing rather than re-deriving it:
  - `sector_analytics.load_sector_map` / `peer_relative` (generic, cube-
    agnostic: only needs sector_map.parquet + any (date,symbol) factor).
  - `run_long_confirm.build_mom_resid_12_1` / `build_earnings_yield` /
    `bear_vs_other_ic` / `BEAR_YEARS` (already-verified long-cube factor
    builders + the bear-vs-other-year IC split used for the sibling
    LONG_H00x confirm pass).
The plain-momentum and plain-EY single-factor BASELINES are NOT re-run
through the harness here (that would double-count H003/H014 family trials
in trials_counter.json for no new information) -- their numbers are read
directly off the existing `rnd/cards/LONG_H003_mom121_resid_1Y.json` and
`rnd/cards/LONG_H014_earnings_yield_1Y.json`. Only the NEW constructs (peer
transform, sub_sector sector-RS, the composite) are scored fresh, under
family ids `W2SEC_C1` / `W2SEC_C2` / `W2SEC_C3`.
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
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
from sector_analytics import load_sector_map, peer_relative  # noqa: E402
from run_long_confirm import (  # noqa: E402
    build_mom_resid_12_1, build_earnings_yield, bear_vs_other_ic, BEAR_YEARS,
)

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"
CUBE_CLOSE_LONG = RND_DIR / "panel" / "cube_close_long.parquet"
CUBE_BENCH_LONG = RND_DIR / "panel" / "cube_bench_long.parquet"
CARDS_DIR = RND_DIR / "cards"
REPORTS_DIR = RND_DIR / "reports"

_CACHE: dict = {}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# 0. load panel_long + long cubes (cached)
# ---------------------------------------------------------------------------
def load_long_all():
    if "long_all" not in _CACHE:
        panel = pd.read_parquet(PANEL_LONG_PATH)
        panel["date"] = pd.to_datetime(panel["date"])
        close = pd.read_parquet(CUBE_CLOSE_LONG)
        close.index = pd.to_datetime(close.index)
        bench = pd.read_parquet(CUBE_BENCH_LONG)["NIFTY500"]
        bench.index = pd.to_datetime(bench.index)
        _CACHE["long_all"] = (panel, close, bench)
    return _CACHE["long_all"]


def panel_dates(panel: pd.DataFrame) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(sorted(panel["date"].unique()))


# ---------------------------------------------------------------------------
# 1. long-cube sector composites + sector RS (mirrors sector_analytics.py's
#    build_sector_composites / sector_rs_vs_market / own_sector_rs_factor,
#    but off cube_close_long/cube_bench_long instead of the short cube --
#    those functions are hardcoded to the short-panel paths, see their
#    module docstring, so a parallel long-cube version is needed rather
#    than a param).
# ---------------------------------------------------------------------------
def build_sector_composites_long(level: str = "macro_sector", min_names: int = 3) -> pd.DataFrame:
    assert level in ("macro_sector", "sub_sector")
    key = f"composites_long_{level}_{min_names}"
    if key in _CACHE:
        return _CACHE[key]
    _, close, _ = load_long_all()
    smap = load_sector_map().set_index("symbol")[level]
    ret = close.pct_change()
    sectors = smap.reindex(ret.columns)
    out = {}
    for sec, syms in sectors.dropna().groupby(sectors.dropna()).groups.items():
        cols = [c for c in syms if c in ret.columns]
        if len(cols) < min_names:
            continue
        sub = ret[cols]
        n_valid = sub.notna().sum(axis=1)
        mean_ret = sub.mean(axis=1, skipna=True).where(n_valid >= min_names)
        out[sec] = mean_ret
    ret_df = pd.DataFrame(out).sort_index()
    idx = (1.0 + ret_df.fillna(0.0)).cumprod() * 100.0
    first_valid = ret_df.notna().cummax()
    idx = idx.where(first_valid)
    _CACHE[key] = idx
    return idx


def sector_rs_vs_market_long(composites: pd.DataFrame, lookback: int = 252, skip: int = 21) -> pd.DataFrame:
    _, _, bench = load_long_all()
    bench_mom = bench.shift(skip) / bench.shift(lookback) - 1.0
    shifted = composites.shift(skip)
    base = composites.shift(lookback)
    sec_mom = shifted / base - 1.0
    return sec_mom.sub(bench_mom, axis=0)


def own_sector_rs_factor_long(panel: pd.DataFrame, level: str = "macro_sector",
                               lookback: int = 252, skip: int = 21, min_names: int = 3) -> pd.Series:
    composites = build_sector_composites_long(level=level, min_names=min_names)
    rs = sector_rs_vs_market_long(composites, lookback=lookback, skip=skip)
    smap = load_sector_map().set_index("symbol")[level]

    ds = panel[["date", "symbol"]].drop_duplicates().copy()
    ds["date"] = pd.to_datetime(ds["date"])
    ds["sec"] = ds["symbol"].map(smap)
    ds = ds.dropna(subset=["sec"])

    idx_name = rs.index.name or "date"
    rs_long = rs.reset_index().melt(id_vars=idx_name, var_name="sec", value_name="factor")
    rs_long = rs_long.rename(columns={idx_name: "date"})
    rs_long["date"] = pd.to_datetime(rs_long["date"])

    m = ds.merge(rs_long, on=["date", "sec"], how="left").dropna(subset=["factor"])
    return m.set_index(["date", "symbol"])["factor"]


# ---------------------------------------------------------------------------
# 2. rank-average composite combiner (C3) -- lookahead-free: purely
#    cross-sectional percentile rank of each component at each date, no
#    time-series element added by the combine step itself.
# ---------------------------------------------------------------------------
def rank_average_composite(components: list[pd.Series]) -> pd.Series:
    frames = []
    for comp in components:
        d = comp.rename("factor").reset_index()
        d["date"] = pd.to_datetime(d["date"])
        d["pct"] = d.groupby("date")["factor"].rank(pct=True)
        frames.append(d.set_index(["date", "symbol"])["pct"])
    combo = pd.concat(frames, axis=1).mean(axis=1, skipna=True)
    combo.name = "factor"
    return combo.dropna()


# ---------------------------------------------------------------------------
# 3. read an existing card's key stats (for the plain-factor baselines,
#    without re-running them through the harness / re-incrementing trials).
# ---------------------------------------------------------------------------
def read_card_stats(card_path: Path) -> dict:
    d = json.loads(card_path.read_text(encoding="utf-8"))
    return {
        "ic_ir": d.get("ic", {}).get("ic_ir"),
        "ic_mean": d.get("ic", {}).get("ic_mean"),
        "mono": d.get("deciles", {}).get("monotonicity"),
        "lag_test_delta": d.get("lag_test", {}).get("lag_test_delta"),
        "placebo_ic": d.get("placebo", {}).get("placebo_ic"),
        "pbo": d.get("pbo", {}).get("pbo"),
        "bear_split": d.get("bear_split_2008_11_20"),
        "net_of_cost_ann_return": d.get("costs", {}).get("net_of_cost_ann_return"),
    }


def excl_disc(panel: pd.DataFrame, horizon: str) -> tuple[pd.DataFrame, int]:
    lbl_raw, lbl_resid = f"fwd_ret_{horizon}_raw", f"fwd_ret_{horizon}_resid"
    disc_col = f"disc_event_in_window_{horizon}"
    p2 = panel.copy()
    mask = p2[disc_col].fillna(0) > 0
    p2.loc[mask, [lbl_raw, lbl_resid]] = np.nan
    return p2, int(mask.sum())


def eval_and_bearsplit(factor: pd.Series, panel_excl: pd.DataFrame, horizon: str,
                        factor_id: str, family: str) -> dict:
    card = harness.evaluate(
        factor, horizon, return_basis="resid", factor_id=factor_id,
        panel=panel_excl, panel_source="real_long_panel_long_history",
        family=family, write_card=True, cards_dir=CARDS_DIR,
    )
    bear_split = bear_vs_other_ic(factor, panel_excl, f"fwd_ret_{horizon}_resid")
    card["bear_split_2008_11_20"] = bear_split
    (CARDS_DIR / f"{factor_id}.json").write_text(json.dumps(card, indent=2, default=str), encoding="utf-8")
    return card


# ---------------------------------------------------------------------------
# 4. main -- C1 / C2 / C3, horizon=1Y, basis=resid (per task spec)
# ---------------------------------------------------------------------------
def main():
    panel, close, bench = load_long_all()
    dates = panel_dates(panel)
    log(f"panel_long: {panel.shape}, {panel['date'].nunique()} dates, {panel['symbol'].nunique()} symbols")
    panel_1y, n_excl_1y = excl_disc(panel, "1Y")
    log(f"1Y disc-event exclusions: {n_excl_1y} rows")

    summary = []

    # ---- C1: sub-sector peer-relative residual momentum, full 21yr -------
    log("C1: building plain resid-mom + peer-relative(sub_sector) transform...")
    plain_mom = build_mom_resid_12_1(close, bench, dates)
    peer_mom = peer_relative(plain_mom, level="sub_sector", method="z")
    log(f"  plain n_obs={len(plain_mom)}  peer n_obs={len(peer_mom)}")

    c1_card = eval_and_bearsplit(peer_mom, panel_1y, "1Y", "W2SEC_C1_peer_residmom_subsector_1Y", "W2SEC_C1")
    baseline_h003 = read_card_stats(CARDS_DIR / "LONG_H003_mom121_resid_1Y.json")
    summary.append({
        "id": "W2SEC-C1", "leg": "peer_subsector", "horizon": "1Y",
        "ic_ir": c1_card["ic"]["ic_ir"], "mono": c1_card["deciles"]["monotonicity"],
        "lag_delta": c1_card["lag_test"]["lag_test_delta"], "placebo_ic": c1_card["placebo"]["placebo_ic"],
        "pbo": c1_card["pbo"]["pbo"], "bear_ic_2008_11_20": c1_card["bear_split_2008_11_20"]["bear_ic_2008_11_20"],
        "other_ic": c1_card["bear_split_2008_11_20"]["other_ic"],
        "verdict": c1_card.get("verdict"),
    })
    summary.append({
        "id": "W2SEC-C1", "leg": "plain_baseline(LONG_H003, cached)", "horizon": "1Y",
        "ic_ir": baseline_h003["ic_ir"], "mono": baseline_h003["mono"],
        "lag_delta": baseline_h003["lag_test_delta"], "placebo_ic": baseline_h003["placebo_ic"],
        "pbo": baseline_h003["pbo"],
        "bear_ic_2008_11_20": baseline_h003["bear_split"]["bear_ic_2008_11_20"] if baseline_h003["bear_split"] else None,
        "other_ic": baseline_h003["bear_split"]["other_ic"] if baseline_h003["bear_split"] else None,
        "verdict": None,
    })
    log(f"  C1 peer IC_IR={c1_card['ic']['ic_ir']:.3f} (baseline plain IC_IR={baseline_h003['ic_ir']:.3f}) "
        f"verdict={c1_card.get('verdict')}")

    # ---- C2: sub_sector-level sector-momentum tilt vs macro_sector -------
    log("C2: building own-sector RS at macro_sector (fresh long baseline) and sub_sector...")
    rs_macro = own_sector_rs_factor_long(panel, level="macro_sector")
    rs_sub = own_sector_rs_factor_long(panel, level="sub_sector")
    log(f"  macro n_obs={len(rs_macro)}  sub_sector n_obs={len(rs_sub)}")

    c2_macro_card = eval_and_bearsplit(rs_macro, panel_1y, "1Y", "W2SEC_C2_secRS_macro_1Y", "W2SEC_C2")
    c2_sub_card = eval_and_bearsplit(rs_sub, panel_1y, "1Y", "W2SEC_C2_secRS_subsector_1Y", "W2SEC_C2")
    for leg, card in (("macro_sector(long baseline)", c2_macro_card), ("sub_sector(test)", c2_sub_card)):
        summary.append({
            "id": "W2SEC-C2", "leg": leg, "horizon": "1Y",
            "ic_ir": card["ic"]["ic_ir"], "mono": card["deciles"]["monotonicity"],
            "lag_delta": card["lag_test"]["lag_test_delta"], "placebo_ic": card["placebo"]["placebo_ic"],
            "pbo": card["pbo"]["pbo"],
            "bear_ic_2008_11_20": card["bear_split_2008_11_20"]["bear_ic_2008_11_20"],
            "other_ic": card["bear_split_2008_11_20"]["other_ic"],
            "verdict": card.get("verdict"),
        })
    log(f"  C2 macro IC_IR={c2_macro_card['ic']['ic_ir']:.3f}  sub_sector IC_IR={c2_sub_card['ic']['ic_ir']:.3f}")

    # ---- C3: sector-aware quality-momentum composite ----------------------
    log("C3: building plain EY + composite(peer_mom_subsector, plain EY)...")
    plain_ey = build_earnings_yield(panel, close, dates)
    composite = rank_average_composite([peer_mom, plain_ey])
    log(f"  plain_ey n_obs={len(plain_ey)}  composite n_obs={len(composite)}")

    c3_card = eval_and_bearsplit(composite, panel_1y, "1Y", "W2SEC_C3_sectoraware_composite_1Y", "W2SEC_C3")
    baseline_h014 = read_card_stats(CARDS_DIR / "LONG_H014_earnings_yield_1Y.json")
    summary.append({
        "id": "W2SEC-C3", "leg": "composite(peer_mom+plain_ey)", "horizon": "1Y",
        "ic_ir": c3_card["ic"]["ic_ir"], "mono": c3_card["deciles"]["monotonicity"],
        "lag_delta": c3_card["lag_test"]["lag_test_delta"], "placebo_ic": c3_card["placebo"]["placebo_ic"],
        "pbo": c3_card["pbo"]["pbo"],
        "bear_ic_2008_11_20": c3_card["bear_split_2008_11_20"]["bear_ic_2008_11_20"],
        "other_ic": c3_card["bear_split_2008_11_20"]["other_ic"],
        "verdict": c3_card.get("verdict"),
    })
    summary.append({
        "id": "W2SEC-C3", "leg": "parent1_peer_mom(=C1 above)", "horizon": "1Y",
        "ic_ir": c1_card["ic"]["ic_ir"], "mono": c1_card["deciles"]["monotonicity"],
        "lag_delta": c1_card["lag_test"]["lag_test_delta"], "placebo_ic": c1_card["placebo"]["placebo_ic"],
        "pbo": c1_card["pbo"]["pbo"], "bear_ic_2008_11_20": None, "other_ic": None, "verdict": None,
    })
    summary.append({
        "id": "W2SEC-C3", "leg": "parent2_plain_ey_baseline(LONG_H014, cached)", "horizon": "1Y",
        "ic_ir": baseline_h014["ic_ir"], "mono": baseline_h014["mono"],
        "lag_delta": baseline_h014["lag_test_delta"], "placebo_ic": baseline_h014["placebo_ic"],
        "pbo": baseline_h014["pbo"], "bear_ic_2008_11_20": None, "other_ic": None, "verdict": None,
    })
    log(f"  C3 composite IC_IR={c3_card['ic']['ic_ir']:.3f} vs parents peer_mom={c1_card['ic']['ic_ir']:.3f} / "
        f"plain_ey={baseline_h014['ic_ir']:.3f}  verdict={c3_card.get('verdict')}")

    summ_df = pd.DataFrame(summary)
    out_csv = REPORTS_DIR / "W2SEC_children_long_summary.csv"
    summ_df.to_csv(out_csv, index=False)
    log(f"Saved summary: {out_csv}")
    print(summ_df.to_string())


if __name__ == "__main__":
    main()
