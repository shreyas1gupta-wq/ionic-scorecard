"""Supplementary pass: sector-drop perturbation (fixed column name) + 2005-10 coverage sanity check."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))
import harness  # noqa: E402
import run_long_confirm as LC  # noqa: E402

REPORTS_DIR = RND_DIR / "reports"
LEGS_CACHE = RND_DIR / "panel" / "capstone_legs.parquet"
UNIVERSE_PATH = RND_DIR.parent / "data" / "universe" / "nifty_total_market_750.csv"


def load_cached_legs():
    d = pd.read_parquet(LEGS_CACHE)
    d["date"] = pd.to_datetime(d["date"])
    out = {}
    for leg, g in d.groupby("leg"):
        out[leg] = g.set_index(["date", "symbol"])["value"].rename("factor")
    return out


def rank_avg(legs_dict, names, min_legs=5):
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


def quick_ic(factor, panel, min_names=20, drop_symbols=None):
    lbl = harness._label_cols("1Y")
    p = panel[["date", "symbol", lbl["resid"]]].copy().rename(columns={lbl["resid"]: "target_eval"})
    p["date"] = pd.to_datetime(p["date"])
    if drop_symbols:
        p = p[~p["symbol"].isin(drop_symbols)]
    f = harness._normalize_factor(factor)
    if drop_symbols:
        f = f[~f["symbol"].isin(drop_symbols)]
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    ic_series = harness._cross_sectional_ic(merged, min_names=min_names)
    ic_mean = float(ic_series.mean()) if len(ic_series) else np.nan
    ic_std = float(ic_series.std(ddof=1)) if len(ic_series) > 1 else np.nan
    ic_ir = ic_mean / ic_std if ic_std and ic_std > 0 else np.nan
    return {"ic_mean": ic_mean, "ic_ir": ic_ir, "n_dates_scored": int(ic_series.notna().sum()),
            "n_dates_total": int(len(ic_series)), "n_obs": int(len(merged))}


def main():
    panel, close, bench = LC.load_all()
    dates = LC._panel_dates(panel)
    legs = load_cached_legs()
    mom_plain = LC.build_mom_resid_12_1(close, bench, dates)
    legs["mom_resid_plain"] = mom_plain
    TRUE7 = ["value_EY", "mom_resid_plain", "trend_ma65_slope", "quality_QMJ",
             "bs_issuance", "bs_asset_growth", "quality_cfo_pat"]
    factor_true7 = rank_avg(legs, TRUE7)

    # 2005-10 coverage sanity check
    lbl = harness._label_cols("1Y")
    p = panel[["date", "symbol", lbl["resid"]]].copy().rename(columns={lbl["resid"]: "target_eval"})
    p["date"] = pd.to_datetime(p["date"])
    f = harness._normalize_factor(factor_true7)
    merged = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", "target_eval"])
    sub = merged[(merged["date"] >= "2005-01-01") & (merged["date"] < "2010-01-01")]
    per_date_n = sub.groupby("date").size()
    print("2005-10 window: n_dates_with_any_obs =", len(per_date_n),
          "| max names on best date =", int(per_date_n.max()) if len(per_date_n) else 0,
          "| dates with >=20 names =", int((per_date_n >= 20).sum()))
    print(per_date_n.describe())

    # sector-drop (fixed column: "Industry")
    uni = pd.read_csv(UNIVERSE_PATH)
    sec_col = "Industry"
    sym_col = "Symbol"
    sector_results = {}
    for sec, g in uni.groupby(sec_col):
        dropped = set(g[sym_col].astype(str))
        r = quick_ic(factor_true7, panel, drop_symbols=dropped)
        sector_results[str(sec)] = r
    out = json.loads((REPORTS_DIR / "PREIC_AUDIT_results.json").read_text(encoding="utf-8"))
    out["perturb_drop_each_sector"] = sector_results
    out["era_2005_10_coverage_check"] = {
        "n_dates_with_any_obs": int(len(per_date_n)),
        "max_names_any_date": int(per_date_n.max()) if len(per_date_n) else 0,
        "dates_with_ge20_names": int((per_date_n >= 20).sum()),
    }
    (REPORTS_DIR / "PREIC_AUDIT_results.json").write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    print("Sector-drop IC_IR range:",
          min(v["ic_ir"] for v in sector_results.values() if v["ic_ir"] == v["ic_ir"]),
          "to", max(v["ic_ir"] for v in sector_results.values() if v["ic_ir"] == v["ic_ir"]))
    for k, v in sorted(sector_results.items(), key=lambda kv: kv[1]["ic_ir"] if kv[1]["ic_ir"] == kv[1]["ic_ir"] else 999):
        print(f"  {k}: ic_ir={v['ic_ir']:.3f} ic_mean={v['ic_mean']:.4f}")


if __name__ == "__main__":
    main()
