"""
TURNOVER / ADV-CAPACITY / REALISTIC-FILL AUDIT — Tara Singh (Execution & TCA)
Targets: the Tier-A momentum rescues flagged by COMPLETENESS_CRITIC.md #4:
  H002_slope200_1M (MA-slope sweep winner), H004_mom_sharpe12m_1M (vol-scaled
  momentum), H043_beta_adj_mom (beta-adjusted 12-1 momentum, 1Y horizon).

Reuses the EXACT factor-builder code (rnd/lib/builders_ma.py,
rnd/lib/builders_mom.py) and the EXACT decile-assignment / one-way-turnover
convention already in rnd/lib/harness.py (_decile_stats / _turnover), so the
turnover number here is directly reconcilable to the one already printed in
the cards -- this audit goes one level deeper: real symbol-level ADV
participation + volume-conditional fill/slippage from
Shreyas_Ionic_AMC/04_RND_LAB/lib/execution_realism.py (Principal-order,
binding), applied to the ACTUAL entering names on ACTUAL rebalance dates.

Known, stated limitation: cube_volume.parquet only starts 2021-07-16. ADV
participation / realistic-fill numbers below are RECENT-REGIME ONLY
(2021-07 onward, ~last 4-4.5 years of the ~20-year backtest window). No
volume-based capacity claim is made for the pre-2021 sample; it cannot be
measured from this dataset.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RND = Path(r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/ALPHA_RANKER/rnd")
FIRM_LIB = Path(r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/lib")
sys.path.insert(0, str(RND / "lib"))
sys.path.insert(0, str(FIRM_LIB))

import builders_ma            # noqa: E402
import builders_mom            # noqa: E402
import harness                 # noqa: E402
import execution_realism as er  # noqa: E402

OUT_DIR = RND / "wave4"
CARDS_DIR = OUT_DIR / "cards_exec"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

VOL_START = pd.Timestamp("2021-07-16")  # cube_volume.parquet first date (verified)
MIN_NAMES = 20

# COST_STANDARDS.md slippage floors (one-way, bps of traded value) + fixed
# round-trip charges — same constants harness._read_cost_standards_bps() uses,
# duplicated here (read-only reuse, not a redefinition) so this script has no
# import-time dependency surprise if harness's cache changes.
TIER_FLOOR_1W_BPS = {"large": 10, "mid": 20, "small": 35, "micro": 50}
FIXED_RT_BPS = 20.0 + 3.0  # STT delivery round-trip (20) + exch/GST/stamp blended (3)


def load_fno_universe() -> set:
    p = OUT_DIR / "_fno_universe_list.txt"
    return set(x.strip() for x in p.read_text().splitlines() if x.strip())


def get_decile_sets(factor_series: pd.Series, min_names=MIN_NAMES) -> dict:
    """Mirrors harness._decile_stats' decile assignment exactly (qcut rank
    method='first', 10 bins, duplicates='drop'). Returns {date: (top_set, bot_set)}."""
    df = factor_series.rename("factor").reset_index()
    df.columns = ["date", "symbol", "factor"] if list(df.columns) != ["date", "symbol", "factor"] else df.columns
    out = {}
    for d, g in df.groupby("date"):
        if len(g) < min_names:
            continue
        try:
            g = g.assign(decile=pd.qcut(g["factor"].rank(method="first"), 10, labels=False, duplicates="drop"))
        except ValueError:
            continue
        if g["decile"].nunique() < 3:
            continue
        top_d, bot_d = g["decile"].max(), g["decile"].min()
        top = set(g.loc[g["decile"] == top_d, "symbol"])
        bot = set(g.loc[g["decile"] == bot_d, "symbol"])
        out[pd.Timestamp(d)] = (top, bot)
    return out


def oneway_turnover_leg(sets_by_date: dict, leg_idx: int) -> tuple[float, dict]:
    """Same convention as harness._turnover: new_names / current_size, averaged
    over consecutive rebalance dates. Returns (avg, {date: turnover_that_date})."""
    dates = sorted(sets_by_date.keys())
    fracs, per_date = [], {}
    for i in range(1, len(dates)):
        cur = sets_by_date[dates[i]][leg_idx]
        prev = sets_by_date[dates[i - 1]][leg_idx]
        if not cur:
            continue
        new_names = cur - prev
        t = len(new_names) / len(cur)
        fracs.append(t)
        per_date[dates[i]] = t
    return (float(np.mean(fracs)) if fracs else float("nan")), per_date


def entering_names_by_date(sets_by_date: dict, leg_idx: int) -> dict:
    dates = sorted(sets_by_date.keys())
    out = {}
    for i in range(1, len(dates)):
        cur = sets_by_date[dates[i]][leg_idx]
        prev = sets_by_date[dates[i - 1]][leg_idx]
        out[dates[i]] = cur - prev
    return out


def nearest_prior_index(idx: pd.DatetimeIndex, d: pd.Timestamp):
    sub = idx[idx <= d]
    return sub[-1] if len(sub) else None


def main():
    print("Loading panel + cubes...", flush=True)
    panel = pd.read_parquet(RND / "panel" / "panel_long.parquet")
    cube_close = pd.read_parquet(RND / "panel" / "cube_close_long.parquet")
    cube_close.index = pd.to_datetime(cube_close.index)
    cube_close = cube_close.sort_index()
    cube_vol = pd.read_parquet(RND / "panel" / "cube_volume.parquet")
    cube_vol.index = pd.to_datetime(cube_vol.index)
    cube_vol = cube_vol.sort_index()
    vol_med20 = cube_vol.rolling(20, min_periods=10).median()

    fno_universe = load_fno_universe()
    print(f"FNO universe loaded: {len(fno_universe)} names", flush=True)

    # symbol -> tier, computed exactly like harness._mktcap_tier (per-symbol
    # mean mktcap_log across the whole sample, then cross-sectional quantile
    # cut) so tiers here reconcile to the cards' blended_cost_bps.
    sym_mktcap = panel.groupby("symbol")["mktcap_log"].mean()
    sym_tier = harness._mktcap_tier(sym_mktcap)  # noqa: SLF001 (intentional reuse)

    print("Building H002_slope200_1M factor...", flush=True)
    h002_factor = builders_ma.dma_slope_factor(200, 21)(panel)
    print("Building H004_mom_sharpe12m_1M factor...", flush=True)
    h004_factor = builders_mom.build_mom_sharpe_12m(panel)
    print("Building H043_beta_adj_mom factor (1Y horizon)...", flush=True)
    h043_factor = builders_mom.build_beta_adjusted_mom(panel)

    SIGNALS = {
        "H002_slope200_1M": {"family": "H002", "horizon": "1M", "factor": h002_factor,
                              "card_gross_ann": 0.20019739876962642, "card_turnover": 0.2438305313532688,
                              "card_net_flat": 0.1768074133949987},
        "H004_mom_sharpe12m_1M": {"family": "H004", "horizon": "1M", "factor": h004_factor,
                                   "card_gross_ann": 0.17107818521106616, "card_turnover": 0.2718842990145561,
                                   "card_net_flat": 0.1449945131374466},
        "H043_beta_adj_mom": {"family": "H043", "horizon": "1Y", "factor": h043_factor,
                               "card_gross_ann": 2.5644024258326215, "card_turnover": 0.2500967966095334,
                               "card_net_flat": 2.5403999028954583},
    }

    results = {}
    AUM_LIST = [("10cr", 10e7), ("100cr", 100e7)]

    for fid, info in SIGNALS.items():
        print(f"\n=== {fid} ===", flush=True)
        sets_by_date = get_decile_sets(info["factor"])
        n_dates = len(sets_by_date)
        top_to, top_per = oneway_turnover_leg(sets_by_date, 0)
        bot_to, bot_per = oneway_turnover_leg(sets_by_date, 1)
        ls_book_turnover = float(np.nanmean([top_to, bot_to]))

        avg_top_n = float(np.mean([len(v[0]) for v in sets_by_date.values()]))
        avg_bot_n = float(np.mean([len(v[1]) for v in sets_by_date.values()]))

        # avg holding period proxy (months) = 1/one-way turnover
        hold_months_top = 1.0 / top_to if top_to > 0 else float("nan")
        hold_months_bot = 1.0 / bot_to if bot_to > 0 else float("nan")

        # --- ADV / capacity: recent-regime only (dates >= VOL_START) ---
        cap_rows = []
        recent_dates = [d for d in sets_by_date if d >= VOL_START]
        for d in recent_dates:
            dd = nearest_prior_index(cube_close.index, d)
            if dd is None:
                continue
            top, bot = sets_by_date[d]
            for leg, names in (("long", top), ("short", bot)):
                n = len(names)
                if n == 0:
                    continue
                for sym in names:
                    if sym not in cube_close.columns or sym not in vol_med20.columns:
                        continue
                    price = cube_close.at[dd, sym] if dd in cube_close.index else np.nan
                    vmed = vol_med20.at[dd, sym] if dd in vol_med20.index else np.nan
                    if pd.isna(price) or pd.isna(vmed) or vmed <= 0 or price <= 0:
                        continue
                    adv_rs = price * vmed
                    tier = sym_tier.get(sym, "mid")
                    for aum_label, aum in AUM_LIST:
                        pos_rs = aum / n
                        part_pct = pos_rs / adv_rs * 100.0
                        cap_rows.append({"date": d, "leg": leg, "symbol": sym, "tier": tier,
                                          "aum": aum_label, "participation_pct": part_pct,
                                          "is_fno": sym in fno_universe})
        cap_df = pd.DataFrame(cap_rows)

        # --- FNO / shortability of the short leg (recent-regime sample) ---
        short_fno_share = float("nan")
        if not cap_df.empty:
            short_names = cap_df.loc[cap_df["leg"] == "short", ["date", "symbol", "is_fno"]].drop_duplicates()
            if len(short_names):
                short_fno_share = float(short_names["is_fno"].mean())
        long_names_all = cap_df.loc[cap_df["leg"] == "long", ["date", "symbol", "is_fno"]].drop_duplicates() if not cap_df.empty else pd.DataFrame()
        long_fno_share = float(long_names_all["is_fno"].mean()) if len(long_names_all) else float("nan")

        cap_summary = {}
        for aum_label, _ in AUM_LIST:
            for leg in ("long", "short"):
                sub = cap_df[(cap_df["aum"] == aum_label) & (cap_df["leg"] == leg)] if not cap_df.empty else pd.DataFrame()
                if sub.empty:
                    cap_summary[f"{leg}_{aum_label}"] = None
                    continue
                cap_summary[f"{leg}_{aum_label}"] = {
                    "median_pct": float(sub["participation_pct"].median()),
                    "p90_pct": float(sub["participation_pct"].quantile(0.90)),
                    "max_pct": float(sub["participation_pct"].max()),
                    "frac_over_10pct": float((sub["participation_pct"] > 10.0).mean()),
                    "frac_over_5pct_micro": float(((sub["tier"] == "micro") & (sub["participation_pct"] > 5.0)).sum() / max((sub["tier"] == "micro").sum(), 1)),
                    "n_leg_days": int(len(sub)),
                }

        # --- realistic fill / slippage on ACTUAL entering names, recent-regime only ---
        entrants_top = entering_names_by_date(sets_by_date, 0)
        entrants_bot = entering_names_by_date(sets_by_date, 1)
        fill_rows = []
        for leg, entrants in (("long", entrants_top), ("short", entrants_bot)):
            for d, names in entrants.items():
                if d < VOL_START or not names:
                    continue
                dd = nearest_prior_index(cube_vol.index, d)
                if dd is None:
                    continue
                for sym in names:
                    if sym not in cube_vol.columns or sym not in vol_med20.columns:
                        continue
                    day_vol = cube_vol.at[dd, sym] if dd in cube_vol.index else np.nan
                    med_vol = vol_med20.at[dd, sym] if dd in vol_med20.index else np.nan
                    tier = sym_tier.get(sym, "mid")
                    floor_bps = TIER_FLOOR_1W_BPS.get(tier, 20)
                    mult = er.slippage_multiplier(day_vol, med_vol)
                    fillable = np.isfinite(mult)
                    eff_bps_1w = floor_bps * mult if fillable else float("nan")
                    fill_rows.append({"date": d, "leg": leg, "symbol": sym, "tier": tier,
                                       "fillable": fillable, "eff_slip_bps_1w": eff_bps_1w,
                                       "mult": mult if fillable else np.nan})
        fill_df = pd.DataFrame(fill_rows)

        no_fill_rate = float((~fill_df["fillable"]).mean()) if len(fill_df) else float("nan")
        avg_eff_slip_1w = float(fill_df.loc[fill_df["fillable"], "eff_slip_bps_1w"].mean()) if fill_df["fillable"].any() else float("nan")
        realistic_bps_rt = 2.0 * avg_eff_slip_1w + FIXED_RT_BPS if not np.isnan(avg_eff_slip_1w) else float("nan")
        flat_bps_rt = 2.0 * float(np.mean([TIER_FLOOR_1W_BPS[t] for t in sym_tier.reindex(fill_df["symbol"]).fillna("mid")])) + FIXED_RT_BPS if len(fill_df) else float("nan")

        mult_dist = fill_df.loc[fill_df["fillable"], "mult"].value_counts(normalize=True).to_dict() if len(fill_df) else {}

        # --- recompute net-of-cost on the RECENT-REGIME subsample for apples-to-apples ---
        # gross LS return recent-regime: recompute IC-consistent ls_ret using
        # harness's own per-date decile spread machinery restricted to recent dates.
        lbl = harness._label_cols(info["horizon"])
        target_col = lbl["resid"]
        raw_col = lbl["raw"]
        base_cols = ["date", "symbol", "mktcap_log"]
        pcols = panel[base_cols + [target_col, raw_col]].copy()
        pcols = pcols.rename(columns={target_col: "target_eval", raw_col: "target_raw"})
        pcols["date"] = pd.to_datetime(pcols["date"])
        f_norm = harness._normalize_factor(info["factor"])
        merged = f_norm.merge(pcols, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
        merged_recent = merged[merged["date"] >= VOL_START]
        ls_recent, _, _ = harness._decile_stats(merged_recent, min_names=MIN_NAMES)
        ls_full, _, _ = harness._decile_stats(merged, min_names=MIN_NAMES)
        periods_per_year = 12
        gross_ann_recent = float(ls_recent.mean() * periods_per_year) if len(ls_recent) else float("nan")
        gross_ann_full = float(ls_full.mean() * periods_per_year) if len(ls_full) else float("nan")
        # 1Y-horizon label already annual -> harness's annualize_ls_return handles that
        gross_ann_recent_ha = harness.annualize_ls_return(float(ls_recent.mean()), info["horizon"]) if len(ls_recent) else float("nan")
        gross_ann_full_ha = harness.annualize_ls_return(float(ls_full.mean()), info["horizon"]) if len(ls_full) else float("nan")

        turnover_recent = ls_book_turnover  # book turnover computed on full sample; recent-only recompute below
        top_to_recent, _ = oneway_turnover_leg({d: v for d, v in sets_by_date.items() if d >= VOL_START}, 0)
        bot_to_recent, _ = oneway_turnover_leg({d: v for d, v in sets_by_date.items() if d >= VOL_START}, 1)
        turnover_recent = float(np.nanmean([top_to_recent, bot_to_recent]))

        net_recent_flat = (gross_ann_recent_ha - turnover_recent * (flat_bps_rt / 10000.0) * periods_per_year
                           if not np.isnan(gross_ann_recent_ha) and not np.isnan(flat_bps_rt) else float("nan"))
        net_recent_realistic = (gross_ann_recent_ha - turnover_recent * (realistic_bps_rt / 10000.0) * periods_per_year
                                if not np.isnan(gross_ann_recent_ha) and not np.isnan(realistic_bps_rt) else float("nan"))

        result = {
            "factor_id": fid, "family": info["family"], "horizon": info["horizon"],
            "n_rebal_dates_total": n_dates,
            "n_rebal_dates_recent_2021_07plus": len(recent_dates),
            "turnover_oneway_book_fullsample": ls_book_turnover,
            "turnover_oneway_long_leg": top_to, "turnover_oneway_short_leg": bot_to,
            "avg_top_decile_n": avg_top_n, "avg_bottom_decile_n": avg_bot_n,
            "implied_avg_holding_months_long": hold_months_top,
            "implied_avg_holding_months_short": hold_months_bot,
            "turnover_oneway_book_recent_regime": turnover_recent,
            "capacity_recent_regime": cap_summary,
            "short_leg_fno_eligible_share_recent": short_fno_share,
            "long_leg_fno_eligible_share_recent": long_fno_share,
            "fill_recent_regime": {
                "n_entry_events": int(len(fill_df)),
                "no_fill_rate": no_fill_rate,
                "avg_effective_slippage_bps_oneway": avg_eff_slip_1w,
                "slippage_multiplier_distribution": mult_dist,
                "realistic_bps_roundtrip": realistic_bps_rt,
                "flat_costmodel_bps_roundtrip_recent_mix": flat_bps_rt,
            },
            "gross_ann_return": {
                "full_sample_horizon_aware": gross_ann_full_ha,
                "recent_regime_horizon_aware": gross_ann_recent_ha,
                "card_reported_full_sample": info["card_gross_ann"],
            },
            "net_of_cost_recent_regime": {
                "flat_costmodel": net_recent_flat,
                "realistic_volcond_fill": net_recent_realistic,
            },
            "card_reported": {"gross_ann": info["card_gross_ann"], "turnover": info["card_turnover"],
                               "net_flat_full_sample": info["card_net_flat"]},
        }
        results[fid] = result
        (CARDS_DIR / f"W4TF_exec_{fid}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
        print(json.dumps({k: v for k, v in result.items() if k not in ("capacity_recent_regime",)}, indent=2, default=str))

    (OUT_DIR / "_turnover_fill_audit_raw.json").write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print("\nDONE. Cards written to", CARDS_DIR)


if __name__ == "__main__":
    main()
