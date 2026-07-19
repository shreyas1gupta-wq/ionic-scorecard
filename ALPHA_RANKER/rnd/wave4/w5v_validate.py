"""
Dr. Sameer Bhat (E-027, Overfit/Sensitivity) -- W5 careful-method validation.

Purpose: the run_w5_convex.py "base7_reconstructed" (ic_ir=1.3374, hypotheses_w5.json)
does NOT reproduce the OFFICIAL/registered CANONICAL_7LEG_1Y ic_ir=1.3450288630259197
(rnd/cards/CANONICAL_7LEG_1Y.json), despite matching n_obs (86838) and n_ic_dates (145)
EXACTLY. Root cause (found by inspection): run_w5_convex.py's SEVEN_LEGS uses
"mom_resid_peer" (pulled from capstone_legs.parquet cache) where the OFFICIAL
CANONICAL_7LEG_1Y construction (per its own construction.legs field) uses
"mom_resid_plain" -- a DIFFERENT, freshly-built momentum construction (built via
run_long_confirm.build_mom_resid_12_1, exactly as rnd/wave4/reconcile_returns.py
does it). capstone_legs.parquet does not even contain a "mom_resid_plain" row
(verified: leg.unique() = [mom_resid_peer, trend_ma65_slope, value_EY, ...] --
12 legs, none named mom_resid_plain). So every "incremental 8-leg IC_IR" number
in hypotheses_w5.json / W5_RESULTS.json was computed against a base-7 that is
NOT the frozen/registered composite. This script rebuilds the TRUE official
base-7, sanity-checks it against 1.345, then redoes the incremental-IR test
and both parties' drop-one requirements from scratch.
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
WAVE4_DIR = _THIS.parent
RND_DIR = WAVE4_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))

import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402
import builders_w5 as BW  # noqa: E402

CARDS_DIR = RND_DIR / "cards"
OUT_MD = WAVE4_DIR / "W5_VALIDATION.md"

HORIZON = "1Y"
MIN_NAMES = 20
OFFICIAL_IC_IR = 1.3450288630259197  # CANONICAL_7LEG_1Y.json, registered/official
OFFICIAL_IC_MEAN = 0.1889984545699352
OFFICIAL_N_OBS = 86838
OFFICIAL_N_IC_DATES = 145

SEVEN_LEGS_OFFICIAL = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
                       "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ==========================================================================
# quick, lightweight IC scorer (mirrors harness.evaluate's IC block exactly:
# spearman per date, min_names gate, ic_std ddof=1) -- used for all the
# drop-one/era/incremental recomputations so we don't pay full evaluate()
# (DSR/PBO/turnover) cost hundreds of times.
# ==========================================================================
def quick_ic(factor: pd.Series, panel: pd.DataFrame, horizon: str = HORIZON,
             min_names: int = MIN_NAMES, only_dates=None, disc_guard=True) -> dict:
    lbl = harness._label_cols(horizon)
    target_col = lbl["resid"]
    disc_col = f"disc_event_in_window_{horizon}"
    p = panel[["date", "symbol", target_col] + ([disc_col] if disc_guard and disc_col in panel.columns else [])].copy()
    p["date"] = pd.to_datetime(p["date"])
    p = p.rename(columns={target_col: "target_eval"})
    if disc_guard and disc_col in p.columns:
        mask = p[disc_col].fillna(0) > 0
        p.loc[mask, "target_eval"] = np.nan
        p = p.drop(columns=[disc_col])
    f = harness._normalize_factor(factor)
    if only_dates is not None:
        dates_set = set(pd.to_datetime(only_dates))
        p = p[p["date"].isin(dates_set)]
        f = f[f["date"].isin(dates_set)]
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    ic_series = harness._cross_sectional_ic(merged, min_names=min_names, target_col="target_eval").dropna()
    ic_mean = float(ic_series.mean()) if len(ic_series) else float("nan")
    ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else float("nan")
    ic_ir = float(ic_mean / ic_std) if ic_std and ic_std == ic_std and ic_std > 0 else float("nan")
    return {"ic_mean": ic_mean, "ic_ir": ic_ir, "n_ic_dates": int(len(ic_series)), "n_obs": int(len(merged))}


def rank_avg(legs_dict: dict, names: list, min_legs: int) -> pd.Series:
    frames = []
    for n in names:
        r = legs_dict[n].rename("factor").reset_index()
        r.columns = ["date", "symbol", n]
        r[n] = r.groupby("date")[n].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])[n])
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


def main():
    log("Loading panel_long + close/bench (run_long_confirm.load_all)...")
    panel, close, bench = LC.load_all()
    panel["date"] = pd.to_datetime(panel["date"])
    log(f"panel_long: {panel.shape}, {panel['date'].nunique()} dates, {panel['symbol'].nunique()} symbols")

    log("Building mom_resid_plain fresh (SAME builder the official CANONICAL_7LEG_1Y card used)...")
    dates = LC._panel_dates(panel)
    mom_plain = LC.build_mom_resid_12_1(close, bench, dates)  # Series indexed (date,symbol)

    log("Loading capstone_legs.parquet cache for the other 6 legs...")
    legs_df = pd.read_parquet(RND_DIR / "panel" / "capstone_legs.parquet")
    legs_df["date"] = pd.to_datetime(legs_df["date"])
    legs = {name: g.set_index(["date", "symbol"])["value"].rename("factor") for name, g in legs_df.groupby("leg")}
    legs["mom_resid_plain"] = mom_plain.rename("factor") if isinstance(mom_plain, pd.Series) else mom_plain

    missing = [l for l in SEVEN_LEGS_OFFICIAL if l not in legs]
    if missing:
        raise RuntimeError(f"missing legs for official base-7: {missing}")

    # ---- SANITY CHECK: rebuild TRUE official base-7, must reproduce IC_IR=1.345 ----
    log("Rebuilding TRUE official base-7 (mom_resid_plain, min_legs=5)...")
    base7 = rank_avg(legs, SEVEN_LEGS_OFFICIAL, min_legs=5)
    base7_full = quick_ic(base7, panel, HORIZON, min_names=MIN_NAMES)
    log(f"  base7 (corrected) ic_mean={base7_full['ic_mean']:.10f} ic_ir={base7_full['ic_ir']:.10f} "
        f"n_ic_dates={base7_full['n_ic_dates']} n_obs={base7_full['n_obs']}")
    sanity_pass = (abs(base7_full["ic_ir"] - OFFICIAL_IC_IR) < 1e-6
                   and base7_full["n_obs"] == OFFICIAL_N_OBS
                   and base7_full["n_ic_dates"] == OFFICIAL_N_IC_DATES)
    log(f"  SANITY CHECK vs official CANONICAL_7LEG_1Y (ic_ir={OFFICIAL_IC_IR}): "
        f"{'PASS' if sanity_pass else 'FAIL'}")

    # also record what the (buggy) mom_resid_peer reconstruction gives, for the record
    legs_peer_ver = dict(legs)
    peer7 = rank_avg(legs_peer_ver, ["value_EY", "mom_resid_peer", "trend_ma65_slope", "quality_QMJ",
                                     "bs_issuance", "bs_asset_growth", "quality_cfo_pat"], min_legs=5)
    peer7_full = quick_ic(peer7, panel, HORIZON, min_names=MIN_NAMES)
    log(f"  (for the record) mom_resid_peer-substituted base7: ic_ir={peer7_full['ic_ir']:.10f} "
        f"-- this is what run_w5_convex.py actually used as 'base7_reconstructed'")

    sanity_card = {
        "official_ic_ir": OFFICIAL_IC_IR, "official_ic_mean": OFFICIAL_IC_MEAN,
        "official_n_obs": OFFICIAL_N_OBS, "official_n_ic_dates": OFFICIAL_N_IC_DATES,
        "rebuilt_correct_base7": base7_full,
        "sanity_check_pass": bool(sanity_pass),
        "buggy_base7_reconstructed_actually_used_in_W5_pipeline": peer7_full,
        "root_cause": ("run_w5_convex.py SEVEN_LEGS used 'mom_resid_peer' (capstone_legs.parquet cache) "
                       "instead of the official 'mom_resid_plain' (freshly built via "
                       "run_long_confirm.build_mom_resid_12_1) that CANONICAL_7LEG_1Y.json's own "
                       "construction.legs field specifies. capstone_legs.parquet has NO mom_resid_plain "
                       "row at all -- the substitution was silent, not a deliberate choice."),
    }
    (CARDS_DIR / "W5V_base7_sanity.json").write_text(json.dumps(sanity_card, indent=2, default=str), encoding="utf-8")

    if not sanity_pass:
        log("!!! SANITY CHECK FAILED -- proceeding anyway with the CORRECTED base7 (closest reproduction), "
            "flagging discrepancy in the report.")

    # ---- Build W5-01 / W5-02 factors (base construction only, per trial discipline) ----
    log("Building W5-01 (cost-elasticity base) and W5-02 (implied-borrow-cost base) factors...")
    t0 = time.time()
    w501 = BW.build_w501_base(panel)
    w502 = BW.build_w502_base(panel)
    log(f"  done in {time.time()-t0:.1f}s. w501 n_obs={len(w501)}, w502 n_obs={len(w502)}")

    years_all = sorted(panel["date"].dt.year.unique())

    def incremental_test(cand_name: str, cand_factor: pd.Series) -> dict:
        r = cand_factor.rename("factor").reset_index()
        r.columns = ["date", "symbol", cand_name]
        r[cand_name] = r.groupby("date")[cand_name].rank(pct=True)
        cand_ranked = r.set_index(["date", "symbol"])[cand_name]

        combo8_frames = []
        for n in SEVEN_LEGS_OFFICIAL:
            rr = legs[n].rename("factor").reset_index()
            rr.columns = ["date", "symbol", n]
            rr[n] = rr.groupby("date")[n].rank(pct=True)
            combo8_frames.append(rr.set_index(["date", "symbol"])[n])
        combo8_frames.append(cand_ranked.rename("factor").to_frame(cand_name)[cand_name])
        wide8 = pd.concat(combo8_frames, axis=1)
        combo8 = wide8.mean(axis=1, skipna=True)
        n_present8 = wide8.notna().sum(axis=1)
        combo8 = combo8.where(n_present8 >= 6).dropna().rename("factor")

        # restrict comparison window to dates where the CANDIDATE itself has
        # coverage (W4DO2 precedent: window_restricted_to_candidate_dates)
        cand_dates = sorted(harness._normalize_factor(cand_factor)["date"].unique())
        n_candidate_dates = len(cand_dates)

        full_base7 = quick_ic(base7, panel, HORIZON, only_dates=cand_dates)
        full_with8 = quick_ic(combo8, panel, HORIZON, only_dates=cand_dates)
        delta_full = (full_with8["ic_ir"] - full_base7["ic_ir"]
                      if np.isfinite(full_with8["ic_ir"]) and np.isfinite(full_base7["ic_ir"]) else float("nan"))

        # ---- drop-one-year ----
        dropone_year = {}
        for yr in years_all:
            keep_dates = [d for d in cand_dates if pd.Timestamp(d).year != yr]
            if len(keep_dates) < 10:
                continue
            b7 = quick_ic(base7, panel, HORIZON, only_dates=keep_dates)
            w8 = quick_ic(combo8, panel, HORIZON, only_dates=keep_dates)
            if not (np.isfinite(b7["ic_ir"]) and np.isfinite(w8["ic_ir"])):
                continue
            dropone_year[int(yr)] = {
                "base7_ic_ir": b7["ic_ir"], "with8_ic_ir": w8["ic_ir"],
                "delta_ic_ir": w8["ic_ir"] - b7["ic_ir"], "n_ic_dates": w8["n_ic_dates"],
            }
        distinct_deltas = len(set(round(v["delta_ic_ir"], 8) for v in dropone_year.values()))
        worst_key, worst_val = (None, None)
        if dropone_year:
            worst_key = min(dropone_year, key=lambda k: dropone_year[k]["delta_ic_ir"])
            worst_val = dropone_year[worst_key]["delta_ic_ir"]
        n_negative = sum(1 for v in dropone_year.values() if v["delta_ic_ir"] <= 0)
        survives_drop_one = bool(dropone_year) and n_negative == 0

        # ---- era split (halves) ----
        mid = cand_dates[len(cand_dates) // 2]
        pre_dates = [d for d in cand_dates if d < mid]
        post_dates = [d for d in cand_dates if d >= mid]
        era = {}
        for label, dts in [("first_half", pre_dates), ("second_half", post_dates)]:
            b7 = quick_ic(base7, panel, HORIZON, only_dates=dts)
            w8 = quick_ic(combo8, panel, HORIZON, only_dates=dts)
            era[label] = {"base7_ic_ir": b7["ic_ir"], "with8_ic_ir": w8["ic_ir"],
                          "delta_ic_ir": (w8["ic_ir"] - b7["ic_ir"]) if np.isfinite(w8["ic_ir"]) and np.isfinite(b7["ic_ir"]) else float("nan"),
                          "n_ic_dates": w8["n_ic_dates"]}
        era_survives = all(np.isfinite(v["delta_ic_ir"]) and v["delta_ic_ir"] > 0 for v in era.values())

        return {
            "candidate": cand_name, "n_candidate_dates": n_candidate_dates,
            "full_base7": full_base7, "full_with8": full_with8, "delta_ic_ir_full": delta_full,
            "dropone_year": dropone_year, "distinct_deltas_across_years": distinct_deltas,
            "n_years_tested": len(dropone_year),
            "worst_drop": {"key": f"year_{worst_key}", "delta_ic_ir": worst_val} if worst_key is not None else None,
            "n_years_delta_negative": n_negative,
            "survives_drop_one": survives_drop_one,
            "era_split": era, "survives_era_split": bool(era_survives),
        }

    log("Running incremental-IR test (corrected base7) for W5-01...")
    res_w501 = incremental_test("W5_01_cost_elasticity_base", w501)
    log(f"  delta_ic_ir_full(corrected)={res_w501['delta_ic_ir_full']:.4f}  survives_drop_one={res_w501['survives_drop_one']}  "
        f"survives_era_split={res_w501['survives_era_split']}")

    log("Running incremental-IR test (corrected base7) for W5-02...")
    res_w502 = incremental_test("W5_02_implied_borrow_cost_base", w502)
    log(f"  delta_ic_ir_full(corrected)={res_w502['delta_ic_ir_full']:.4f}  survives_drop_one={res_w502['survives_drop_one']}  "
        f"survives_era_split={res_w502['survives_era_split']}")

    (CARDS_DIR / "W5V_W5_01_incremental.json").write_text(json.dumps(res_w501, indent=2, default=str), encoding="utf-8")
    (CARDS_DIR / "W5V_W5_02_incremental.json").write_text(json.dumps(res_w502, indent=2, default=str), encoding="utf-8")

    # ==========================================================================
    # W5-02 CONVEX-HEDGE validation (hedge-axis, not IC): drop-one-crash-episode,
    # era-split of the RAW factor's own conditional payoff, month-level detail.
    # ==========================================================================
    log("W5-02 convex-hedge validation: monthly LS payoff, per-episode detail...")
    panel_ret = panel[["date", "symbol", "fwd_ret_1M_raw", "disc_event_in_window_1M"]].copy()
    mask1m = panel_ret["disc_event_in_window_1M"].fillna(0) > 0
    panel_ret.loc[mask1m, "fwd_ret_1M_raw"] = np.nan
    panel_ret = panel_ret[["date", "symbol", "fwd_ret_1M_raw"]]

    f = w502.rename("factor").reset_index()
    f.columns = ["date", "symbol", "factor"]
    sub = f.merge(panel_ret, on=["date", "symbol"], how="inner").dropna(subset=["factor", "fwd_ret_1M_raw"])
    ls_rows = {}
    for d, g in sub.groupby("date"):
        if len(g) < 15:
            continue
        try:
            g = g.copy()
            g["qtile"] = pd.qcut(g["factor"], 5, labels=False, duplicates="drop")
        except ValueError:
            continue
        qmax = g["qtile"].max()
        top = g.loc[g["qtile"] == qmax, "fwd_ret_1M_raw"].mean()
        bot = g.loc[g["qtile"] == 0, "fwd_ret_1M_raw"].mean()
        ls_rows[d] = top - bot
    ls = pd.Series(ls_rows).sort_index()

    EPISODES = {
        "GFC_2008-09": (pd.Timestamp("2008-08-01"), pd.Timestamp("2009-03-01")),
        "COVID_2020-02_03": (pd.Timestamp("2020-01-15"), pd.Timestamp("2020-03-31")),
        "SELLOFF_2022": (pd.Timestamp("2021-12-15"), pd.Timestamp("2022-06-30")),
    }
    ep_months = {}
    for name, (start, end) in EPISODES.items():
        dd = [d for d in ls.index if start <= d <= end]
        ep_months[name] = {str(d.date()): float(ls[d]) for d in dd}
        log(f"  {name}: n_months={len(dd)} values={[round(ls[d]*100,2) for d in dd]}")

    # panel date coverage check -- why does GFC show 0 months?
    panel_dates_all = sorted(panel["date"].unique())
    gfc_panel_dates = [d for d in panel_dates_all if EPISODES["GFC_2008-09"][0] <= pd.Timestamp(d) <= EPISODES["GFC_2008-09"][1]]
    w502_dates = sorted(harness._normalize_factor(w502)["date"].unique())
    gfc_w502_dates = [d for d in w502_dates if EPISODES["GFC_2008-09"][0] <= pd.Timestamp(d) <= EPISODES["GFC_2008-09"][1]]
    log(f"  GFC window: {len(gfc_panel_dates)} panel dates exist, {len(gfc_w502_dates)} have w502 factor coverage")

    # drop-one-crash-episode: with only COVID vs only 2022 (GFC has no data -- disclosed)
    covid_vals = list(ep_months["COVID_2020-02_03"].values())
    selloff_vals = list(ep_months["SELLOFF_2022"].values())
    dropone_episode = {
        "only_COVID_2020": {"n": len(covid_vals), "mean": float(np.mean(covid_vals)) if covid_vals else None,
                             "min": float(np.min(covid_vals)) if covid_vals else None,
                             "all_positive": bool(all(v > 0 for v in covid_vals)) if covid_vals else None},
        "only_SELLOFF_2022": {"n": len(selloff_vals), "mean": float(np.mean(selloff_vals)) if selloff_vals else None,
                               "min": float(np.min(selloff_vals)) if selloff_vals else None,
                               "all_positive": bool(all(v > 0 for v in selloff_vals)) if selloff_vals else None},
        "GFC_2008-09": {"n": 0, "note": "NO DATA -- panel/factor has 0 dates in this window (checked directly), "
                                        "cannot assess 2008 crisis at all"},
    }
    both_episodes_positive_mean = (dropone_episode["only_COVID_2020"]["mean"] is not None
                                    and dropone_episode["only_COVID_2020"]["mean"] > 0
                                    and dropone_episode["only_SELLOFF_2022"]["mean"] is not None
                                    and dropone_episode["only_SELLOFF_2022"]["mean"] > 0)
    one_episode_carries_all = False
    if covid_vals and selloff_vals:
        # "carried by one episode" heuristic: episode with n_months<=3 contributing
        # >3x the per-month magnitude of the other episode
        covid_permonth = abs(np.mean(covid_vals))
        selloff_permonth = abs(np.mean(selloff_vals))
        one_episode_carries_all = (covid_permonth > 3 * selloff_permonth) or (selloff_permonth > 3 * covid_permonth)

    # era-split of the raw factor's OWN unconditional IC (not incremental) --
    # "genuinely positive... without one episode carrying it" also needs an
    # unconditional-era check, since 2020 has only 3 months of crash data.
    w502_dates_sorted = w502_dates
    mid = w502_dates_sorted[len(w502_dates_sorted) // 2]
    era_ic = {}
    for label, dts in [("first_half", [d for d in w502_dates_sorted if d < mid]),
                       ("second_half", [d for d in w502_dates_sorted if d >= mid])]:
        era_ic[label] = quick_ic(w502, panel, HORIZON, only_dates=dts)
    log(f"  W5-02 unconditional era-split IC_mean: first_half={era_ic['first_half']['ic_mean']:.4f} "
        f"second_half={era_ic['second_half']['ic_mean']:.4f}")

    convex_card = {
        "candidate": "W5_02_implied_borrow_cost_base",
        "worst_decile_market_month_conditional": None,  # see W5_RESULTS.json existing figure, unaffected by base7 bug
        "episode_months_detail": ep_months,
        "dropone_crash_episode": dropone_episode,
        "both_episodes_positive_mean": bool(both_episodes_positive_mean),
        "one_episode_carries_all_magnitude": bool(one_episode_carries_all),
        "unconditional_era_split_ic": era_ic,
        "unconditional_era_both_positive": bool(era_ic["first_half"]["ic_mean"] > 0 and era_ic["second_half"]["ic_mean"] > 0)
                                            if np.isfinite(era_ic["first_half"]["ic_mean"]) and np.isfinite(era_ic["second_half"]["ic_mean"]) else None,
        "n_crash_episodes_with_data": sum(1 for v in [covid_vals, selloff_vals] if v),
        "gfc_data_status": f"{len(gfc_panel_dates)} panel dates in window, {len(gfc_w502_dates)} with w502 coverage -- NO DATA",
    }
    (CARDS_DIR / "W5V_W5_02_convex_hedge.json").write_text(json.dumps(convex_card, indent=2, default=str), encoding="utf-8")

    # ==========================================================================
    # write W5_VALIDATION.md
    # ==========================================================================
    lines = []
    lines.append(f"# W5 Validation -- Dr. Sameer Bhat (E-027), {time.strftime('%Y-%m-%d')}\n\n")
    lines.append("## 0. Base-7 sanity check (MANDATORY precondition)\n\n")
    lines.append(f"Official registered IC_IR (CANONICAL_7LEG_1Y.json): **{OFFICIAL_IC_IR:.6f}** "
                 f"(ic_mean={OFFICIAL_IC_MEAN:.6f}, n_obs={OFFICIAL_N_OBS}, n_ic_dates={OFFICIAL_N_IC_DATES}).\n\n")
    lines.append(f"Rebuilt base-7 using the OFFICIAL legs (mom_resid_plain, freshly built): "
                 f"ic_ir={base7_full['ic_ir']:.6f}, ic_mean={base7_full['ic_mean']:.6f}, "
                 f"n_obs={base7_full['n_obs']}, n_ic_dates={base7_full['n_ic_dates']}. "
                 f"**Sanity check: {'PASS' if sanity_pass else 'FAIL'}**.\n\n")
    lines.append(f"For contrast, the base-7 actually used by rnd/wave4/run_w5_convex.py "
                 f"('base7_reconstructed' in hypotheses_w5.json, ic_ir={peer7_full['ic_ir']:.6f}) "
                 f"substituted the leg 'mom_resid_peer' (capstone_legs.parquet cache) for the official "
                 f"'mom_resid_plain' -- a leg that doesn't even exist in that cache. This is a SILENT "
                 f"construction bug: every incremental-8-leg number in the W5 batch used the WRONG base-7.\n\n")
    lines.append("## 1. W5-01 cost-elasticity: incremental IR after sanity-checked rebuild\n\n")
    lines.append(f"Originally reported (buggy base): delta_ic_ir = +0.3959 ('+0.396 incremental IR as 8th leg').\n\n")
    lines.append(f"Recomputed against the CORRECTED, sanity-checked base-7 "
                 f"(restricted to W5-01's {res_w501['n_candidate_dates']} candidate dates): "
                 f"base7_ic_ir={res_w501['full_base7']['ic_ir']:.4f}, "
                 f"with8_ic_ir={res_w501['full_with8']['ic_ir']:.4f}, "
                 f"**delta_ic_ir = {res_w501['delta_ic_ir_full']:.4f}**.\n\n")
    lines.append(f"Drop-one-year ({res_w501['n_years_tested']} years tested, "
                 f"{res_w501['distinct_deltas_across_years']} distinct delta values -- confirms the "
                 f"drop-one loop is actually varying, not a no-op): worst year "
                 f"{res_w501['worst_drop']}. n_years with delta<=0: {res_w501['n_years_delta_negative']}. "
                 f"**survives_drop_one = {res_w501['survives_drop_one']}**.\n\n")
    lines.append(f"Era split (halves): {res_w501['era_split']}. "
                 f"**survives_era_split = {res_w501['survives_era_split']}**.\n\n")
    lines.append("## 2. W5-02 implied-borrow-cost: convex-hedge validation (hedge-axis, not IC)\n\n")
    lines.append(f"Per-episode monthly LS values: {json.dumps(ep_months, indent=2)}\n\n")
    lines.append(f"Drop-one-crash-episode: {json.dumps(dropone_episode, indent=2)}\n\n")
    lines.append(f"both_episodes_positive_mean = {both_episodes_positive_mean}; "
                 f"one_episode_carries_all_magnitude = {one_episode_carries_all}.\n\n")
    lines.append(f"Unconditional era-split IC (own factor, not incremental): "
                 f"first_half={era_ic['first_half']['ic_mean']:.4f}, second_half={era_ic['second_half']['ic_mean']:.4f}.\n\n")
    lines.append(f"For completeness, the corrected incremental-IR test for W5-02 (this hypothesis is a "
                 f"HEDGE candidate, not an IC play, so this is secondary): delta_ic_ir_full="
                 f"{res_w502['delta_ic_ir_full']:.4f}, survives_drop_one={res_w502['survives_drop_one']}, "
                 f"survives_era_split={res_w502['survives_era_split']}.\n\n")
    OUT_MD.write_text("".join(lines), encoding="utf-8")
    log(f"Wrote {OUT_MD}")

    print("\n" + "=" * 100)
    print("SUMMARY")
    print(f"Base7 sanity check: {'PASS' if sanity_pass else 'FAIL'} (rebuilt ic_ir={base7_full['ic_ir']:.6f} vs official {OFFICIAL_IC_IR:.6f})")
    print(f"W5-01 corrected delta_ic_ir_full = {res_w501['delta_ic_ir_full']:.4f}  survives_drop_one={res_w501['survives_drop_one']}  survives_era_split={res_w501['survives_era_split']}")
    print(f"W5-02 episode means: COVID={dropone_episode['only_COVID_2020']['mean']}  SELLOFF_2022={dropone_episode['only_SELLOFF_2022']['mean']}  GFC=NO DATA")
    print(f"W5-02 both_episodes_positive_mean={both_episodes_positive_mean}  one_episode_carries_all_magnitude={one_episode_carries_all}")
    print("=" * 100)


if __name__ == "__main__":
    main()
