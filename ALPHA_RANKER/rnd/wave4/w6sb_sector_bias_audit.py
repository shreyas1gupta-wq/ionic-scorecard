"""
W6SB -- SECTOR-BIAS AUDIT on the 7-leg capstone factors.
Arjun Rao (Head of Quant), 2026-07-17.

Principal's concern: earnings-yield (EY) is structurally biased -- financials
have low PE by business-model (leverage), cyclicals show high EY (cheap P/E)
at PEAK trailing earnings just before mean-reversion. Part of the "value
edge" may be a hidden SECTOR BET (long financials/utilities/cyclical-peak,
short IT/consumer), not true cross-stock alpha.

TASKS (see prompt): (1) sector composition of raw EY top/bottom decile,
(2) sector-relative EY IC vs raw EY IC, (3) per-leg (all 7 + composite) raw
vs sector-neutral IC delta, (4) cyclical-peak value-trap check, (5) recommend
which legs need sector-relativizing + decompose composite edge into
sector-timing vs stock-selection.

METHOD:
- Target: fwd_ret_1Y_resid (return_basis="resid", matches CANONICAL_7LEG_1Y
  construction) for IC; fwd_ret_1Y_raw for long-short / Brinson decomposition.
- Corporate-action guard: disc_event_in_window_1Y>0 rows dropped from target
  (same guard as CANONICAL_7LEG_1Y card).
- Sector grain: panel_long.sector (macro_sector, 22 buckets, same source
  n750 Industry that build_panel.py joins -- same column the composite's own
  regime/attribution code already uses). Static classification (documented
  caveat in sector_map.py), applied to full history.
- momentum leg: canonical composite (composite_pit.py TRUE7) uses
  "mom_resid_plain" (residual vs NIFTY500 benchmark only, no sector step),
  built FRESH here via the same run_long_confirm.build_mom_resid_12_1() the
  canonical script calls -- NOT the cached "mom_resid_peer" leg in
  capstone_legs.parquet (that one is ALREADY sub_sector peer_relative-z'd,
  i.e. it is itself a candidate sector-neutral variant, kept as a
  cross-check but not treated as "raw").
- Sector-neutral transform: per-(date,sector) percentile rank of the SAME
  raw factor value (centered -0.5..+0.5), min_peers=5 (sector-date buckets
  smaller than 5 dropped, not fabricated). This is a genuine re-ranking
  (not a monotonic transform of the cross-sectional rank) so its Spearman
  IC is an independent number, not algebraically forced to match raw IC.
- min_names_per_date pooled IC = 20 (matches harness.evaluate default).
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

import harness as H  # noqa: E402
import run_long_confirm as LC  # noqa: E402

PANEL_DIR = RND_DIR / "panel"
CARDS_DIR = RND_DIR / "wave4" / "cards_w6sb"
CARDS_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = RND_DIR / "wave4" / "SECTOR_BIAS_AUDIT.md"

MIN_NAMES = 20
MIN_SECTOR_PEERS = 5
HORIZON = "1Y"

CYCLICAL_SECTORS = [
    "Metals & Mining", "Capital Goods", "Automobile and Auto Components",
    "Oil Gas & Consumable Fuels", "Construction", "Construction Materials",
    "Power", "Realty",
]
TRUE7_CANON = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
               "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
LEG_LABELS = {
    "value_EY": "EY", "mom_resid_plain": "mom-resid", "trend_ma65_slope": "MA65",
    "quality_QMJ": "QMJ", "bs_issuance": "issuance", "bs_asset_growth": "asset-growth",
    "quality_cfo_pat": "cfo-pat",
}


def log(msg):
    print(f"[w6sb {time.strftime('%H:%M:%S')}] {msg}", flush=True)


def to_native(o):
    if isinstance(o, dict):
        return {k: to_native(v) for k, v in o.items()}
    if isinstance(o, list):
        return [to_native(v) for v in o]
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (pd.Timestamp,)):
        return str(o.date())
    return o


def write_card(name, obj):
    p = CARDS_DIR / f"{name}.json"
    p.write_text(json.dumps(to_native(obj), indent=2), encoding="utf-8")
    log(f"wrote {p}")


# ==========================================================================
# 0. load
# ==========================================================================
log("loading panel_long, capstone_legs...")
panel = pd.read_parquet(PANEL_DIR / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])
legs_raw = pd.read_parquet(PANEL_DIR / "capstone_legs.parquet")
legs_raw["date"] = pd.to_datetime(legs_raw["date"])

tgt = panel[["date", "symbol", "sector", "fwd_ret_1Y_raw", "fwd_ret_1Y_resid",
             "disc_event_in_window_1Y"]].copy()
n_before = len(tgt)
tgt = tgt[tgt["disc_event_in_window_1Y"].fillna(0) <= 0]
n_guard_dropped = n_before - len(tgt)
tgt = tgt.dropna(subset=["fwd_ret_1Y_resid", "fwd_ret_1Y_raw"])
tgt = tgt.rename(columns={"fwd_ret_1Y_resid": "target_eval", "fwd_ret_1Y_raw": "target_raw"})
log(f"panel rows={n_before}, corp-action guard dropped {n_guard_dropped}, "
    f"after target dropna={len(tgt)}")

sym_sector = panel.dropna(subset=["sector"]).groupby("symbol")["sector"] \
    .agg(lambda s: s.mode().iat[0])

legs = {}
for leg, g in legs_raw.groupby("leg"):
    legs[leg] = g.set_index(["date", "symbol"])["value"]

log("building mom_resid_plain fresh (matches canonical CANONICAL_7LEG_PIT_1Y construction)...")
_, close, bench = LC.load_all()
dates = LC._panel_dates(panel)
legs["mom_resid_plain"] = LC.build_mom_resid_12_1(close, bench, dates)
log(f"mom_resid_plain: {len(legs['mom_resid_plain'])} obs")

for n in TRUE7_CANON:
    assert n in legs, f"missing leg {n}"


def merge_leg(name):
    f = legs[name].rename("factor").reset_index()
    f["date"] = pd.to_datetime(f["date"])
    m = f.merge(tgt, on=["date", "symbol"], how="inner")
    return m


def compute_ic(m, factor_col="factor", min_names=MIN_NAMES):
    ic_rows = []
    for d, g in m.groupby("date"):
        gg = g.dropna(subset=[factor_col, "target_eval"])
        if len(gg) < min_names:
            continue
        rho, _ = stats.spearmanr(gg[factor_col], gg["target_eval"])
        if not np.isnan(rho):
            ic_rows.append((d, rho))
    s = pd.Series(dict(ic_rows)).dropna().sort_index()
    if len(s) < 3:
        return {"ic_mean": float("nan"), "ic_std": float("nan"), "ic_ir": float("nan"),
                "n_ic_dates": int(len(s)), "nw_t": float("nan")}, s
    ic_mean, ic_std = float(s.mean()), float(s.std(ddof=1))
    ic_ir = ic_mean / ic_std if ic_std else float("nan")
    nw = H.newey_west_tstat(s, H.HORIZON_PERIODS[HORIZON])
    return {"ic_mean": ic_mean, "ic_std": ic_std, "ic_ir": ic_ir,
            "n_ic_dates": int(len(s)), "nw_t": nw["t_stat"]}, s


def decile_ls_ann(m, factor_col="factor", min_names=MIN_NAMES):
    rows = []
    for d, g in m.groupby("date"):
        gg = g.dropna(subset=[factor_col, "target_raw"])
        if len(gg) < min_names:
            continue
        try:
            dec = pd.qcut(gg[factor_col].rank(method="first"), 10, labels=False, duplicates="drop")
        except ValueError:
            continue
        if dec.nunique() < 3:
            continue
        gg = gg.assign(decile=dec)
        top_d, bot_d = gg["decile"].max(), gg["decile"].min()
        top = gg.loc[gg["decile"] == top_d, "target_raw"].mean()
        bot = gg.loc[gg["decile"] == bot_d, "target_raw"].mean()
        rows.append((d, top - bot))
    s = pd.Series(dict(rows)).dropna()
    if not len(s):
        return float("nan"), 0
    return float(s.mean() * 12), int(len(s))


def sector_neutral_rank(m, min_peers=MIN_SECTOR_PEERS):
    g = m.copy()
    cnt = g.groupby(["date", "sector"])["factor"].transform("count")
    g = g[cnt >= min_peers].copy()
    g["sec_rank"] = g.groupby(["date", "sector"])["factor"].rank(pct=True) - 0.5
    return g


# ==========================================================================
# TASK 1 -- sector composition of raw EY top / bottom decile
# ==========================================================================
log("TASK 1: sector composition of raw EY deciles...")
ey_m = merge_leg("value_EY")


def decile_sector_composition(m, min_names=MIN_NAMES):
    rows_top, rows_bot, rows_univ = [], [], []
    for d, g in m.groupby("date"):
        if len(g) < min_names:
            continue
        try:
            dec = pd.qcut(g["factor"].rank(method="first"), 10, labels=False, duplicates="drop")
        except ValueError:
            continue
        if dec.nunique() < 3:
            continue
        gg = g.assign(decile=dec)
        top_d, bot_d = gg["decile"].max(), gg["decile"].min()
        top = gg[gg["decile"] == top_d]
        bot = gg[gg["decile"] == bot_d]
        rows_top.append(top["sector"].value_counts(normalize=True))
        rows_bot.append(bot["sector"].value_counts(normalize=True))
        rows_univ.append(gg["sector"].value_counts(normalize=True))
    top_avg = pd.concat(rows_top, axis=1).fillna(0.0).mean(axis=1).sort_values(ascending=False)
    bot_avg = pd.concat(rows_bot, axis=1).fillna(0.0).mean(axis=1).sort_values(ascending=False)
    univ_avg = pd.concat(rows_univ, axis=1).fillna(0.0).mean(axis=1).sort_values(ascending=False)
    return top_avg, bot_avg, univ_avg, len(rows_top)


ey_top_comp, ey_bot_comp, ey_univ_comp, n_dates_comp = decile_sector_composition(ey_m)
hhi_top = float((ey_top_comp ** 2).sum())
hhi_bot = float((ey_bot_comp ** 2).sum())
hhi_univ = float((ey_univ_comp ** 2).sum())
overweight_top = (ey_top_comp / ey_univ_comp.reindex(ey_top_comp.index)).sort_values(ascending=False)
overweight_bot = (ey_bot_comp / ey_univ_comp.reindex(ey_bot_comp.index)).sort_values(ascending=False)

task1 = {
    "n_dates": n_dates_comp,
    "hhi_top_decile": hhi_top, "hhi_bottom_decile": hhi_bot, "hhi_universe": hhi_univ,
    "top_decile_sector_share": ey_top_comp.head(8).to_dict(),
    "bottom_decile_sector_share": ey_bot_comp.head(8).to_dict(),
    "universe_sector_share": ey_univ_comp.to_dict(),
    "top_decile_overweight_vs_universe": overweight_top.head(8).to_dict(),
    "bottom_decile_overweight_vs_universe": overweight_bot.head(8).to_dict(),
}
write_card("W6SB_TASK1_EY_sector_composition", task1)
log(f"EY top decile top sectors: {ey_top_comp.head(5).to_dict()}")
log(f"EY bottom decile top sectors: {ey_bot_comp.head(5).to_dict()}")

# ==========================================================================
# TASK 2 -- sector-relative EY vs raw EY: IC comparison
# ==========================================================================
log("TASK 2: sector-relative EY vs raw EY IC...")
ic_ey_raw, s_ey_raw = compute_ic(ey_m)
ey_neutral = sector_neutral_rank(ey_m)
ic_ey_neutral, s_ey_neutral = compute_ic(ey_neutral, factor_col="sec_rank")
ls_ey_raw, n_ls_raw = decile_ls_ann(ey_m)
ls_ey_neutral, n_ls_neutral = decile_ls_ann(ey_neutral, factor_col="sec_rank")

task2 = {
    "raw_EY": {**ic_ey_raw, "ann_LS_return": ls_ey_raw, "n_ls_dates": n_ls_raw},
    "sector_neutral_EY": {**ic_ey_neutral, "ann_LS_return": ls_ey_neutral, "n_ls_dates": n_ls_neutral},
    "ic_delta_neutral_minus_raw": ic_ey_neutral["ic_mean"] - ic_ey_raw["ic_mean"],
    "ic_retention_pct": (ic_ey_neutral["ic_mean"] / ic_ey_raw["ic_mean"] * 100.0
                         if ic_ey_raw["ic_mean"] else float("nan")),
}
write_card("W6SB_TASK2_EY_sector_relative_vs_raw", task2)
log(f"EY raw IC={ic_ey_raw['ic_mean']:.4f} (IR={ic_ey_raw['ic_ir']:.2f}) vs "
    f"sector-neutral IC={ic_ey_neutral['ic_mean']:.4f} (IR={ic_ey_neutral['ic_ir']:.2f})")

# ==========================================================================
# TASK 3 -- per-leg raw vs sector-neutral IC (all 7 legs + composite)
# ==========================================================================
log("TASK 3: per-leg raw vs sector-neutral IC...")
per_leg_results = {}
for name in TRUE7_CANON:
    m = merge_leg(name)
    ic_raw, _ = compute_ic(m)
    m_n = sector_neutral_rank(m)
    ic_neutral, _ = compute_ic(m_n, factor_col="sec_rank")
    per_leg_results[name] = {
        "label": LEG_LABELS[name],
        "raw_ic_mean": ic_raw["ic_mean"], "raw_ic_ir": ic_raw["ic_ir"], "raw_n_dates": ic_raw["n_ic_dates"],
        "neutral_ic_mean": ic_neutral["ic_mean"], "neutral_ic_ir": ic_neutral["ic_ir"],
        "neutral_n_dates": ic_neutral["n_ic_dates"],
        "delta_ic_mean": ic_neutral["ic_mean"] - ic_raw["ic_mean"],
        "ic_retention_pct": (ic_neutral["ic_mean"] / ic_raw["ic_mean"] * 100.0
                             if ic_raw["ic_mean"] else float("nan")),
    }
    log(f"  {LEG_LABELS[name]}: raw IC={ic_raw['ic_mean']:.4f} -> neutral IC={ic_neutral['ic_mean']:.4f} "
        f"(delta={per_leg_results[name]['delta_ic_mean']:+.4f})")

# cross-check: cached mom_resid_peer (already sub_sector peer_relative-z'd upstream)
if "mom_resid_peer" in legs:
    m_peer = merge_leg("mom_resid_peer")
    ic_peer, _ = compute_ic(m_peer)
    per_leg_results["mom_resid_peer_cached_crosscheck"] = {
        "label": "mom-resid (cached sub_sector peer_relative-z, upstream build)",
        "raw_ic_mean": ic_peer["ic_mean"], "raw_ic_ir": ic_peer["ic_ir"], "raw_n_dates": ic_peer["n_ic_dates"],
    }
    log(f"  cross-check cached mom_resid_peer IC={ic_peer['ic_mean']:.4f}")


# composite (raw = full-universe rank-average, min_legs=5; sector-neutral = per-sector rank-average)
def build_raw_composite(names, min_legs=5):
    frames = []
    for n in names:
        r = legs[n].rename("factor").reset_index()
        r["date"] = pd.to_datetime(r["date"])
        r["rank"] = r.groupby("date")["factor"].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])["rank"].rename(n))
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


def build_sector_neutral_composite(names, min_legs=5, min_peers=MIN_SECTOR_PEERS):
    frames = []
    for n in names:
        r = legs[n].rename("factor").reset_index()
        r["date"] = pd.to_datetime(r["date"])
        r["sector"] = r["symbol"].map(sym_sector)
        r = r.dropna(subset=["sector"])
        cnt = r.groupby(["date", "sector"])["factor"].transform("count")
        r = r[cnt >= min_peers].copy()
        r["rank"] = r.groupby(["date", "sector"])["factor"].rank(pct=True)
        frames.append(r.set_index(["date", "symbol"])["rank"].rename(n))
    wide = pd.concat(frames, axis=1)
    combo = wide.mean(axis=1, skipna=True)
    n_present = wide.notna().sum(axis=1)
    combo = combo.where(n_present >= min_legs)
    return combo.dropna().rename("factor")


log("building raw + sector-neutral composites...")
raw_combo = build_raw_composite(TRUE7_CANON)
neutral_combo = build_sector_neutral_composite(TRUE7_CANON)

raw_combo_m = raw_combo.reset_index().merge(tgt, on=["date", "symbol"], how="inner")
neutral_combo_m = neutral_combo.reset_index().merge(tgt, on=["date", "symbol"], how="inner")

ic_combo_raw, _ = compute_ic(raw_combo_m)
ic_combo_neutral, _ = compute_ic(neutral_combo_m)
ls_combo_raw, n_ls_combo_raw = decile_ls_ann(raw_combo_m)
ls_combo_neutral, n_ls_combo_neutral = decile_ls_ann(neutral_combo_m)

per_leg_results["COMPOSITE_7LEG"] = {
    "label": "composite (equal-weight rank-avg, min_legs=5)",
    "raw_ic_mean": ic_combo_raw["ic_mean"], "raw_ic_ir": ic_combo_raw["ic_ir"],
    "raw_n_dates": ic_combo_raw["n_ic_dates"], "raw_ann_LS": ls_combo_raw,
    "neutral_ic_mean": ic_combo_neutral["ic_mean"], "neutral_ic_ir": ic_combo_neutral["ic_ir"],
    "neutral_n_dates": ic_combo_neutral["n_ic_dates"], "neutral_ann_LS": ls_combo_neutral,
    "delta_ic_mean": ic_combo_neutral["ic_mean"] - ic_combo_raw["ic_mean"],
    "ic_retention_pct": (ic_combo_neutral["ic_mean"] / ic_combo_raw["ic_mean"] * 100.0
                         if ic_combo_raw["ic_mean"] else float("nan")),
    "ls_retention_pct": (ls_combo_neutral / ls_combo_raw * 100.0 if ls_combo_raw else float("nan")),
}
log(f"  COMPOSITE: raw IC={ic_combo_raw['ic_mean']:.4f} (annLS={ls_combo_raw:.3f}) -> "
    f"neutral IC={ic_combo_neutral['ic_mean']:.4f} (annLS={ls_combo_neutral:.3f})")

write_card("W6SB_TASK3_per_leg_raw_vs_neutral_IC", per_leg_results)

# ==========================================================================
# TASK 4 -- cyclical value-trap check
# ==========================================================================
log("TASK 4: cyclical peak-earnings value-trap check...")
cyc_m = ey_m[ey_m["sector"].isin(CYCLICAL_SECTORS)]
noncyc_m = ey_m[~ey_m["sector"].isin(CYCLICAL_SECTORS)]
ic_cyc, _ = compute_ic(cyc_m, min_names=15)
ic_noncyc, _ = compute_ic(noncyc_m, min_names=MIN_NAMES)

# expanding (PIT-safe), own-history percentile of sector-mean EY per cyclical sector
sec_ey = ey_m.groupby(["date", "sector"])["factor"].mean().rename("sector_ey").reset_index()
sec_ey = sec_ey[sec_ey["sector"].isin(CYCLICAL_SECTORS)].sort_values(["sector", "date"]).reset_index(drop=True)


def expanding_pct_rank(s):
    vals = s.values
    out = np.empty(len(vals))
    for i in range(len(vals)):
        out[i] = (vals[: i + 1] <= vals[i]).mean()
    return pd.Series(out, index=s.index)


sec_ey["peak_pctile"] = sec_ey.groupby("sector")["sector_ey"].transform(expanding_pct_rank)
sec_ey["hist_len"] = sec_ey.groupby("sector").cumcount()
sec_ey_ok = sec_ey[sec_ey["hist_len"] >= 24].copy()
sec_ey_ok["is_peak"] = sec_ey_ok["peak_pctile"] >= 0.75

peak_flag = sec_ey_ok[["date", "sector", "is_peak"]]
cyc2 = cyc_m.merge(peak_flag, on=["date", "sector"], how="inner")

# "cheap-looking" cyclical names = top quintile of raw EY that date (pooled cyclical universe)
top_thresh = cyc2.groupby("date")["factor"].transform(lambda s: s.quantile(0.8))
cheap = cyc2[cyc2["factor"] >= top_thresh]
ret_peak = cheap.loc[cheap["is_peak"], "target_raw"]
ret_nonpeak = cheap.loc[~cheap["is_peak"], "target_raw"]

task4 = {
    "raw_EY_IC_within_cyclical_sectors": ic_cyc,
    "raw_EY_IC_within_noncyclical_sectors": ic_noncyc,
    "cyclical_sectors_used": CYCLICAL_SECTORS,
    "peak_earnings_test": {
        "method": "expanding (PIT-safe) own-history percentile of sector-mean raw EY per cyclical "
                  "sector; is_peak = current sector-EY in its own top quartile-to-date (>=24mo "
                  "history required); 'cheap' = stock in top quintile of pooled-cyclical raw EY "
                  "that date",
        "n_cheap_peak_obs": int(len(ret_peak)), "n_cheap_nonpeak_obs": int(len(ret_nonpeak)),
        "fwd_ret_1Y_raw_mean_cheap_at_peak": float(ret_peak.mean()) if len(ret_peak) else float("nan"),
        "fwd_ret_1Y_raw_mean_cheap_not_at_peak": float(ret_nonpeak.mean()) if len(ret_nonpeak) else float("nan"),
        "delta_peak_minus_nonpeak": (float(ret_peak.mean() - ret_nonpeak.mean())
                                      if len(ret_peak) and len(ret_nonpeak) else float("nan")),
    },
}
write_card("W6SB_TASK4_cyclical_value_trap", task4)
log(f"EY IC cyclical-only={ic_cyc['ic_mean']:.4f} (n={ic_cyc['n_ic_dates']}) vs "
    f"non-cyclical={ic_noncyc['ic_mean']:.4f} (n={ic_noncyc['n_ic_dates']})")
log(f"peak-earnings test: cheap@peak fwd ret={task4['peak_earnings_test']['fwd_ret_1Y_raw_mean_cheap_at_peak']}"
    f" vs cheap@non-peak={task4['peak_earnings_test']['fwd_ret_1Y_raw_mean_cheap_not_at_peak']} "
    f"(n_peak={len(ret_peak)}, n_nonpeak={len(ret_nonpeak)})")

# ==========================================================================
# TASK 5 -- Brinson sector-timing vs stock-selection decomposition (raw composite)
# ==========================================================================
log("TASK 5: Brinson decomposition of raw composite long-short return...")


def brinson_decompose(m, factor_col="factor", min_names=MIN_NAMES):
    rows = []
    for d, g in m.groupby("date"):
        gg = g.dropna(subset=[factor_col, "target_raw", "sector"])
        if len(gg) < min_names:
            continue
        try:
            dec = pd.qcut(gg[factor_col].rank(method="first"), 10, labels=False, duplicates="drop")
        except ValueError:
            continue
        if dec.nunique() < 3:
            continue
        gg = gg.assign(decile=dec)
        top_d, bot_d = gg["decile"].max(), gg["decile"].min()
        top = gg[gg["decile"] == top_d]
        bot = gg[gg["decile"] == bot_d]
        long_ret = top["target_raw"].mean()
        short_ret = bot["target_raw"].mean()
        total_ls = long_ret - short_ret
        sec_avg_ret = gg.groupby("sector")["target_raw"].mean()
        long_w = top["sector"].value_counts(normalize=True)
        short_w = bot["sector"].value_counts(normalize=True)
        all_secs = sorted(set(long_w.index) | set(short_w.index))
        timing = sum((long_w.get(s, 0.0) - short_w.get(s, 0.0)) * sec_avg_ret.get(s, 0.0) for s in all_secs)
        selection = total_ls - timing
        rows.append({"date": d, "total_ls": total_ls, "sector_timing": timing, "stock_selection": selection})
    return pd.DataFrame(rows).set_index("date")


brinson_ey = brinson_decompose(ey_m)
brinson_combo = brinson_decompose(raw_combo_m)

task5_ey = {
    "n_dates": len(brinson_ey),
    "ann_total_LS": float(brinson_ey["total_ls"].mean() * 12),
    "ann_sector_timing": float(brinson_ey["sector_timing"].mean() * 12),
    "ann_stock_selection": float(brinson_ey["stock_selection"].mean() * 12),
    "pct_from_sector_timing": float(brinson_ey["sector_timing"].mean() / brinson_ey["total_ls"].mean() * 100.0)
    if brinson_ey["total_ls"].mean() else float("nan"),
}
task5_combo = {
    "n_dates": len(brinson_combo),
    "ann_total_LS": float(brinson_combo["total_ls"].mean() * 12),
    "ann_sector_timing": float(brinson_combo["sector_timing"].mean() * 12),
    "ann_stock_selection": float(brinson_combo["stock_selection"].mean() * 12),
    "pct_from_sector_timing": float(brinson_combo["sector_timing"].mean() / brinson_combo["total_ls"].mean() * 100.0)
    if brinson_combo["total_ls"].mean() else float("nan"),
    "cross_check_sector_neutral_composite_ann_LS": ls_combo_neutral,
    "cross_check_note": "sector_neutral composite's OWN decile-LS should roughly track the "
                         "stock_selection component here (independent construction, same target) "
                         "-- reported for triangulation, not identical by construction",
}
write_card("W6SB_TASK5_brinson_decomposition", {"value_EY": task5_ey, "COMPOSITE_7LEG": task5_combo})
log(f"EY Brinson: total={task5_ey['ann_total_LS']:.3f} timing={task5_ey['ann_sector_timing']:.3f} "
    f"selection={task5_ey['ann_stock_selection']:.3f} ({task5_ey['pct_from_sector_timing']:.1f}% timing)")
log(f"COMPOSITE Brinson: total={task5_combo['ann_total_LS']:.3f} timing={task5_combo['ann_sector_timing']:.3f} "
    f"selection={task5_combo['ann_stock_selection']:.3f} ({task5_combo['pct_from_sector_timing']:.1f}% timing)")

log("DONE. All cards written to " + str(CARDS_DIR))
