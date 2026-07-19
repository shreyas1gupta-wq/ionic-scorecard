"""
exit_trigger_leg4_hardgate_battery.py
========================================
Overfit & Sensitivity desk discipline (Dr. Sameer Bhat's methodology, `exit_trigger_
hardgate_battery.py`, replicated here) applied to LEG 4 (Minervini/Weinstein technical
stop/trim), the leg `build_exit_trigger_leg4.py` just added to `exit_trigger_flags.parquet`.

Same hard gates B2 ran on Leg 2 (`EXIT_TRIGGER_HARDGATE_REPORT.md`), same discipline
(spec `EXIT_TRIGGER_SPEC.md` Section 7):
  1. Lag-test        : shift firing date forward one period, delta<0.25 vs reference = PASS.
  2. Placebo-shuffle  : 5 draws, seed=42, per-date stratified symbol reassignment.
  3. Alt-entry-date   : top-DECILE entry (rel_score>=80) and +3-month execution-lag entry --
                        THE EXACT test that just broke Leg 2 (EXIT_TRIGGER_HARDGATE_REPORT.md);
                        leg 4 is held to the identical bar, per task instruction, precisely
                        because it would be easy to let it "just work" as the last leg tested.

Run on ALL FOUR leg4 outputs (leg4a_hardstop, leg4b_trim, leg4c_stagebreak, leg4_escalated) --
not just the one that looks best -- because the spec assigns them different conviction levels
(4a/4b = ADVISORY-only, 4c = TRIM, escalated = EXIT_NOW) and a PM needs an honest per-leg read,
not one blended verdict hiding which sub-trigger is actually doing the work.

Determinism: rerun twice, byte-identical console output + report file (placebo uses a single
np.random.default_rng(42) advanced across the 5 draws, same as B2).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[2]  # ALPHA_RANKER/
PANEL_DIR = ROOT / "rnd" / "panel"
SCORECARD_DIR = ROOT / "rnd" / "scorecard"

FLAGS_PATH = SCORECARD_DIR / "exit_trigger_flags.parquet"
WEIGHTS_PATH = SCORECARD_DIR / "exit_weights_v1.json"
CUBE_CLOSE_PATH = PANEL_DIR / "cube_close_long.parquet"
CUBE_VOLUME_PATH = PANEL_DIR / "cube_volume.parquet"
REPORT_PATH = SCORECARD_DIR / "EXIT_TRIGGER_LEG4_REPORT.md"

OUT = []


def log(msg=""):
    print(msg)
    OUT.append(str(msg))


def to_dt(s):
    return pd.to_datetime(s).astype("datetime64[ns]")


def load_weights():
    with open(WEIGHTS_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Rebuild the daily leg4 RAW signal table (entry-independent part) -- same
# construction as build_exit_trigger_leg4.py's compute_daily_signals(), kept
# self-contained here (same reasoning as B2: what's being stress-tested is the
# entry-date convention, so the entry-independent daily signals are computed
# once and reused across all entry-convention variants).
# ---------------------------------------------------------------------------
def compute_daily_signals(L4):
    cc = pd.read_parquet(CUBE_CLOSE_PATH)
    cc.index.name = "date"
    long_close = cc.reset_index().melt(id_vars="date", var_name="symbol", value_name="close")
    long_close = long_close.dropna(subset=["close"])
    long_close["date"] = to_dt(long_close["date"])

    cv = pd.read_parquet(CUBE_VOLUME_PATH)
    cv.index.name = "date"
    long_vol = cv.reset_index().melt(id_vars="date", var_name="symbol", value_name="volume")
    long_vol["date"] = to_dt(long_vol["date"])

    daily = long_close.merge(long_vol, on=["date", "symbol"], how="left")
    daily = daily.sort_values(["symbol", "date"]).reset_index(drop=True)

    disc_thr = L4["discontinuity_guard_1day_return_abs"]
    ma_s, ma_l = L4["ma_short_window"], L4["ma_long_window"]
    vol_win = L4["avg_volume_window_days"]
    dist_win, dist_min = L4["distribution_day_window"], L4["distribution_day_count_min"]
    recent_cross_win = L4["recent_cross_window_days"]
    climax_win, climax_min = L4["climax_run_window_days"], L4["climax_run_return_min"]
    blowoff_ret_min, blowoff_vol_ratio = L4["blowoff_return_proxy_min"], L4["blowoff_volume_ratio_min"]

    parts = []
    for sym, g in daily.groupby("symbol", sort=False):
        g = g.sort_values("date").reset_index(drop=True)
        close = g["close"]
        vol = g["volume"]

        ret1d = close.pct_change()
        is_disc = ret1d.abs().gt(disc_thr).fillna(False)

        ma50 = close.rolling(ma_s, min_periods=ma_s).mean()
        ma150 = close.rolling(ma_l, min_periods=ma_l).mean()
        avg_vol20 = vol.rolling(vol_win, min_periods=max(5, vol_win // 2)).mean()
        ret_climax = close / close.shift(climax_win) - 1

        down_day = close < close.shift(1)
        vol_up = vol >= vol.shift(1)
        dist_day = (down_day & vol_up & vol.notna()).fillna(False)
        dist_count = dist_day.rolling(dist_win, min_periods=1).sum()

        ma_below = (ma50 < ma150)
        crossed_below = ma_below & (~ma_below.shift(1).fillna(False))
        recently_crossed = crossed_below.rolling(recent_cross_win, min_periods=1).max().fillna(0).astype(bool)
        close_below_ma50 = (close < ma50).fillna(False)
        above_avg_vol = (vol >= avg_vol20).fillna(False)

        leg4c_daily_raw = (
            recently_crossed & close_below_ma50 & above_avg_vol & (dist_count >= dist_min) & ~is_disc
        )
        climax_run = (ret_climax >= climax_min).fillna(False)
        blowoff = ((ret1d >= blowoff_ret_min) & (vol >= blowoff_vol_ratio * avg_vol20)).fillna(False)
        leg4b_daily_raw = (climax_run | blowoff) & ~is_disc

        parts.append(pd.DataFrame({
            "symbol": sym, "date": g["date"].values, "close": close.values,
            "is_discontinuity": is_disc.values,
            "leg4b_daily_raw": leg4b_daily_raw.values,
            "leg4c_daily_raw": leg4c_daily_raw.values,
        }))
    daily_signals = pd.concat(parts, ignore_index=True).sort_values("date").reset_index(drop=True)
    return daily_signals


# ---------------------------------------------------------------------------
# Base panel (fwd returns + rel_score for entry-date variants), same sources
# as exit_trigger_hardgate_battery.py's load_base()
# ---------------------------------------------------------------------------
def load_base():
    panel = pd.read_parquet(
        PANEL_DIR / "panel_pit.parquet",
        columns=["date", "symbol", "sector", "fwd_ret_1M_raw", "fwd_ret_1Y_raw"],
    )
    panel["date"] = to_dt(panel["date"])
    rel1y = pd.read_parquet(SCORECARD_DIR / "rel_score_1Y.parquet", columns=["date", "symbol", "rel_score_1Y"])
    rel1y["date"] = to_dt(rel1y["date"])
    rel5y = pd.read_parquet(SCORECARD_DIR / "rel_score_5Y.parquet", columns=["date", "symbol", "rel_score_5Y"])
    rel5y["date"] = to_dt(rel5y["date"])
    base_rows = len(panel)
    df = panel.merge(rel1y, on=["date", "symbol"], how="left")
    df = df.merge(rel5y, on=["date", "symbol"], how="left")
    assert len(df) == base_rows, "merge changed row count"
    return df.sort_values(["symbol", "date"]).reset_index(drop=True)


def build_next_date_map(df):
    nd = {}
    for sym, g in df.groupby("symbol", sort=False):
        dates = g["date"].sort_values().unique()
        for i, d in enumerate(dates):
            nd[(sym, pd.Timestamp(d))] = pd.Timestamp(dates[i + 1]) if i + 1 < len(dates) else pd.NaT
    return nd


def advance_date(sym, d, next_date_map, steps):
    cur = d
    for _ in range(steps):
        if pd.isna(cur):
            return pd.NaT
        cur = next_date_map.get((sym, cur), pd.NaT)
    return cur


# ---------------------------------------------------------------------------
# Recompute leg4a/b/c under a given entry-date convention
# ---------------------------------------------------------------------------
def compute_leg4_for_entry(df, daily_signals, L4, next_date_map, entry_threshold=60.0, entry_lag_steps=0):
    e1 = df.loc[df["rel_score_1Y"] >= entry_threshold].groupby("symbol")["date"].min().rename("entry_1Y")
    e5 = df.loc[df["rel_score_5Y"] >= entry_threshold].groupby("symbol")["date"].min().rename("entry_5Y")
    entry = pd.concat([e1, e5], axis=1)
    entry["entry_date_raw"] = entry[["entry_1Y", "entry_5Y"]].min(axis=1)
    if entry_lag_steps > 0:
        entry["entry_date"] = [
            advance_date(sym, d, next_date_map, entry_lag_steps) if pd.notna(d) else pd.NaT
            for sym, d in zip(entry.index, entry["entry_date_raw"])
        ]
    else:
        entry["entry_date"] = entry["entry_date_raw"]

    d2 = df.merge(entry[["entry_date"]], on="symbol", how="left")
    assert len(d2) == len(df)
    held = d2["entry_date"].notna() & (d2["date"] >= d2["entry_date"])

    entry_lookup = entry.reset_index().rename(columns={"index": "symbol"})[["symbol", "entry_date"]].dropna()
    entry_lookup = entry_lookup.sort_values("entry_date").rename(columns={"entry_date": "date"})
    close_only = daily_signals[["symbol", "date", "close"]].sort_values("date")
    entry_price_df = pd.merge_asof(
        entry_lookup, close_only, on="date", by="symbol", direction="backward"
    ).rename(columns={"close": "entry_price", "date": "entry_date"})

    d2 = d2.merge(entry_price_df[["symbol", "entry_price"]], on="symbol", how="left")
    assert len(d2) == len(df)

    d2 = d2.sort_values("date")
    asof_cols = ["close", "is_discontinuity", "leg4b_daily_raw", "leg4c_daily_raw"]
    joined = pd.merge_asof(d2, daily_signals[["symbol", "date"] + asof_cols], on="date", by="symbol", direction="backward")
    assert len(joined) == len(df)

    hard_stop_pct = L4["hard_stop_pct"]
    leg4a = (
        held.values
        & joined["close"].notna().values & joined["entry_price"].notna().values
        & (joined["close"] <= joined["entry_price"] * (1 - hard_stop_pct)).values
        & ~joined["is_discontinuity"].fillna(False).values
    )
    leg4b = held.values & joined["leg4b_daily_raw"].fillna(False).values
    leg4c = held.values & joined["leg4c_daily_raw"].fillna(False).values

    out = joined[["symbol", "date", "fwd_ret_1M_raw", "fwd_ret_1Y_raw"]].copy()
    out["held"] = held.values
    out["leg4a_hardstop"] = leg4a
    out["leg4b_trim"] = leg4b
    out["leg4c_stagebreak"] = leg4c
    return out.sort_values(["symbol", "date"]).reset_index(drop=True)


def effect_stats(flagged_ret, baseline_ret):
    flagged_ret = flagged_ret.dropna()
    baseline_ret = baseline_ret.dropna()
    n_f, n_b = len(flagged_ret), len(baseline_ret)
    if n_f < 2 or n_b < 2:
        return dict(mean_flagged=np.nan, mean_baseline=np.nan, diff_pp=np.nan, t=np.nan, p=np.nan, n_flagged=n_f, n_baseline=n_b)
    t, p = stats.ttest_ind(flagged_ret, baseline_ret, equal_var=False)
    diff = (flagged_ret.mean() - baseline_ret.mean()) * 100.0
    return dict(mean_flagged=flagged_ret.mean() * 100.0, mean_baseline=baseline_ret.mean() * 100.0,
                diff_pp=diff, t=t, p=p, n_flagged=n_f, n_baseline=n_b)


def run_battery_for_leg(leg_col, prod_flags, df, daily_signals, L4, next_date_map, horizon_col,
                         ref_all_legs_baseline, skip_alt_entry=False):
    """Full hard-gate battery for one leg4 sub-trigger column, against the production
    (original top-quintile entry) frozen flags, for one forward-return horizon.
    skip_alt_entry=True for leg4_escalated: its alt-entry re-derivation would require
    recomputing leg1_valuation_ceiling/leg2_fundamental_deterioration (legs 1-3's own
    logic, owned by quant-head-arjun-rao) under the alternative entry conventions too --
    out of scope for this pass. Reference + lag-test + placebo are still run; alt-entry
    is reported NOT_TESTED with the reason, not silently skipped."""
    log(f"\n### Leg column: `{leg_col}`, horizon: `{horizon_col}`\n")

    prod_m = df.merge(
        prod_flags[["date", "symbol", "entry_date", leg_col, "any_leg_fired"]],
        on=["date", "symbol"], how="left",
    )
    prod_m["held"] = prod_m["entry_date"].notna() & (prod_m["date"] >= prod_m["entry_date"])
    prod_held = prod_m[prod_m["held"]]
    clean_baseline = prod_held[~prod_held["any_leg_fired"].fillna(False)]
    leg_fired = prod_held[prod_held[leg_col].fillna(False)]
    ref = effect_stats(leg_fired[horizon_col], clean_baseline[horizon_col])
    log(f"Reference (original top-quintile entry, clean any-leg-fired==False baseline): "
        f"flagged={ref['mean_flagged']:.2f}%, baseline={ref['mean_baseline']:.2f}%, "
        f"diff={ref['diff_pp']:.2f}pp, t={ref['t']:.2f}, p={ref['p']:.4f}, n={ref['n_flagged']}")

    if ref["n_flagged"] < 20 or np.isnan(ref["diff_pp"]):
        log(f"n={ref['n_flagged']} too thin for a meaningful battery -- SKIPPING lag/placebo/alt-entry, "
            f"reporting reference only.")
        return dict(leg=leg_col, horizon=horizon_col, ref=ref, skipped=True)

    REF_DIFF = ref["diff_pp"]
    next_date_map_local = next_date_map

    # ---- lag-test ----
    fired_rows = leg_fired[["symbol", "date"]].copy()
    fired_rows["date_lag1"] = [advance_date(s, d, next_date_map_local, 1) for s, d in zip(fired_rows["symbol"], fired_rows["date"])]
    n_no_next = fired_rows["date_lag1"].isna().sum()
    fired_lag = fired_rows.dropna(subset=["date_lag1"]).merge(
        df[["symbol", "date", horizon_col]].rename(columns={"date": "date_lag1"}), on=["symbol", "date_lag1"], how="left")
    lag_effect = effect_stats(fired_lag[horizon_col], clean_baseline[horizon_col])
    lag_delta = abs(lag_effect["diff_pp"] - REF_DIFF) / abs(REF_DIFF) if REF_DIFF else np.nan
    lag_same_sign = np.sign(lag_effect["diff_pp"]) == np.sign(REF_DIFF) if not np.isnan(lag_effect["diff_pp"]) else False
    lag_pass = bool(lag_same_sign and (lag_delta < 0.25)) if not np.isnan(lag_delta) else False
    log(f"Lag-test: dropped {n_no_next} (no next period), diff={lag_effect['diff_pp']:.2f}pp, "
        f"t={lag_effect['t']:.2f}, p={lag_effect['p']:.4f}, n={lag_effect['n_flagged']}, "
        f"delta={lag_delta:.3f} (gate<0.25) -> {'PASS' if lag_pass else 'FAIL'}")

    # ---- placebo-shuffle, 5 draws, seed=42, stratified by date ----
    held_pop = prod_held[["date", "symbol", horizon_col, leg_col]].copy()
    held_pop[leg_col] = held_pop[leg_col].fillna(False)
    rng = np.random.default_rng(42)
    placebo_diffs = []
    for draw in range(5):
        placebo_flag = np.zeros(len(held_pop), dtype=bool)
        for date, idx in held_pop.groupby("date").indices.items():
            n_fire_this_date = int(held_pop.loc[held_pop.index[idx], leg_col].sum())
            if n_fire_this_date == 0 or len(idx) == 0:
                continue
            chosen = rng.choice(idx, size=min(n_fire_this_date, len(idx)), replace=False)
            placebo_flag[chosen] = True
        st = effect_stats(held_pop.loc[placebo_flag, horizon_col], held_pop.loc[~placebo_flag, horizon_col])
        placebo_diffs.append(st["diff_pp"])
    placebo_diffs = np.array(placebo_diffs)
    real_outside = (REF_DIFF < placebo_diffs.min()) or (REF_DIFF > placebo_diffs.max())
    same_dir_extreme = (REF_DIFF < placebo_diffs.min()) if REF_DIFF < 0 else (REF_DIFF > placebo_diffs.max())
    pstd = placebo_diffs.std(ddof=1)
    z = (REF_DIFF - placebo_diffs.mean()) / pstd if pstd > 0 else np.nan
    placebo_pass = bool(same_dir_extreme and (abs(z) > 2 if not np.isnan(z) else False))
    log(f"Placebo (5 draws seed=42): diffs={np.round(placebo_diffs, 2).tolist()}pp, "
        f"mean={placebo_diffs.mean():.2f}pp std={pstd:.2f}pp, real={REF_DIFF:.2f}pp, "
        f"z={z:.2f} -> {'PASS' if placebo_pass else 'FAIL'}")

    if skip_alt_entry:
        log(f"Alt-entry (top-decile / +3mo lag): NOT_TESTED for `{leg_col}` -- would require "
            f"recomputing leg1_valuation_ceiling/leg2_fundamental_deterioration under the "
            f"alternative entry conventions too (legs 1-3's own logic), out of scope for this "
            f"pass. Reported as an open gap, not silently passed.")
        dec_effect = dict(diff_pp=np.nan, t=np.nan, p=np.nan, n_flagged=0)
        lag3_effect = dict(diff_pp=np.nan, t=np.nan, p=np.nan, n_flagged=0)
        dec_pass, lag3_pass, entry_robust = None, None, None
    else:
        # ---- alt-entry: top-decile ----
        dec_out = compute_leg4_for_entry(df, daily_signals, L4, next_date_map_local, entry_threshold=80.0, entry_lag_steps=0)
        dec_held = dec_out[dec_out["held"]]
        dec_fired = dec_held[dec_held[leg_col]]
        dec_base = dec_held[~dec_held[leg_col]]
        dec_effect = effect_stats(dec_fired[horizon_col], dec_base[horizon_col])
        dec_same_sign = np.sign(dec_effect["diff_pp"]) == np.sign(REF_DIFF) if not np.isnan(dec_effect["diff_pp"]) else False
        dec_pass = bool(dec_same_sign and dec_effect["p"] < 0.10 and dec_effect["n_flagged"] >= 20) if not np.isnan(dec_effect["p"]) else False
        log(f"Alt-entry (top-decile, rel_score>=80): diff={dec_effect['diff_pp']:.2f}pp, "
            f"t={dec_effect['t']:.2f}, p={dec_effect['p']:.4f}, n={dec_effect['n_flagged']} "
            f"-> {'PASS' if dec_pass else 'FAIL'}")

        # ---- alt-entry: +3mo lag ----
        lag3_out = compute_leg4_for_entry(df, daily_signals, L4, next_date_map_local, entry_threshold=60.0, entry_lag_steps=3)
        lag3_held = lag3_out[lag3_out["held"]]
        lag3_fired = lag3_held[lag3_held[leg_col]]
        lag3_base = lag3_held[~lag3_held[leg_col]]
        lag3_effect = effect_stats(lag3_fired[horizon_col], lag3_base[horizon_col])
        lag3_same_sign = np.sign(lag3_effect["diff_pp"]) == np.sign(REF_DIFF) if not np.isnan(lag3_effect["diff_pp"]) else False
        lag3_pass = bool(lag3_same_sign and lag3_effect["p"] < 0.10 and lag3_effect["n_flagged"] >= 20) if not np.isnan(lag3_effect["p"]) else False
        log(f"Alt-entry (+3mo exec lag): diff={lag3_effect['diff_pp']:.2f}pp, t={lag3_effect['t']:.2f}, "
            f"p={lag3_effect['p']:.4f}, n={lag3_effect['n_flagged']} -> {'PASS' if lag3_pass else 'FAIL'}")
        entry_robust = dec_pass and lag3_pass

    if skip_alt_entry:
        verdict = ("REAL-ON-LAG/PLACEBO-ONLY (entry-date robustness NOT_TESTED)" if (lag_pass and placebo_pass)
                    else "FRAGILE-TO-FAKE -- fails a hard lookahead/noise gate")
    elif lag_pass and placebo_pass and entry_robust:
        verdict = "REAL (conditionally)"
    elif lag_pass and placebo_pass and not entry_robust:
        verdict = "FRAGILE -- sensitive to entry-date convention"
    else:
        verdict = "FRAGILE-TO-FAKE -- fails a hard lookahead/noise gate"
    log(f"VERDICT ({leg_col}, {horizon_col}): {verdict}")

    return dict(leg=leg_col, horizon=horizon_col, ref=ref, lag_effect=lag_effect, lag_pass=lag_pass, lag_delta=lag_delta,
                placebo_diffs=placebo_diffs, placebo_pass=placebo_pass, dec_effect=dec_effect, dec_pass=dec_pass,
                lag3_effect=lag3_effect, lag3_pass=lag3_pass, verdict=verdict, skipped=False)


def main():
    log("# EXIT-TRIGGER LEG-4 (TECHNICAL STOP/TRIM) -- HARD-GATE BATTERY -- run log\n")
    W = load_weights()
    L4 = W["leg4_technical_stop_trim"]
    prod_flags = pd.read_parquet(FLAGS_PATH)
    prod_flags["date"] = to_dt(prod_flags["date"])
    prod_flags["entry_date"] = to_dt(prod_flags["entry_date"])

    df = load_base()
    log(f"[DATA] base panel rows={len(df)}, symbols={df['symbol'].nunique()}, dates={df['date'].nunique()}")
    next_date_map = build_next_date_map(df)
    daily_signals = compute_daily_signals(L4)
    log(f"[DATA] daily leg4 raw signals recomputed: {len(daily_signals)} rows\n")

    results = []
    for leg_col in ["leg4a_hardstop", "leg4b_trim", "leg4c_stagebreak"]:
        for horizon_col in ["fwd_ret_1M_raw", "fwd_ret_1Y_raw"]:
            results.append(run_battery_for_leg(leg_col, prod_flags, df, daily_signals, L4, next_date_map, horizon_col, None))

    # leg4_escalated (leg4c AND (leg1 OR leg2)) -- the EXIT_NOW escalation column
    for horizon_col in ["fwd_ret_1M_raw", "fwd_ret_1Y_raw"]:
        results.append(run_battery_for_leg("leg4_escalated", prod_flags, df, daily_signals, L4, next_date_map,
                                            horizon_col, None, skip_alt_entry=True))

    return results, prod_flags


if __name__ == "__main__":
    results, prod_flags = main()
    with open(SCORECARD_DIR / "_exit_trigger_leg4_hardgate_log.txt", "w") as f:
        f.write("\n".join(OUT))
    print(f"\n[DONE] log written to _exit_trigger_leg4_hardgate_log.txt")
