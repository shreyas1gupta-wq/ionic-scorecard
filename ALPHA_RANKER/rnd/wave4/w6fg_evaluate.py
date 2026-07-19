"""
W6FG STEP 2: score the factors and run them through the harness.
Devika Menon, 2026-07-17.

Factors built:
  W6FG_THEME_ALONE      = theme_dummy only (static sector tag, no earnings gate)
  W6FG_ACCEL_ALONE      = revenue growth acceleration only (raw growth, no gate) --
                           this is the direct analog of the ALREADY-KILLED H024-H027
                           raw-growth family (see rnd/cards/_growth_run_summary.json);
                           re-run here on the SAME symbols/dates as the new composite
                           so the "killed as growth-trap" contrast is apples-to-apples.
  W6FG_COMPOSITE_RAW    = z(rev_accel) + z(margin_inflection) + theme_dummy, NO
                           earnings gate (story-chasing candidate)
  W6FG_COMPOSITE_CONFIRMED = same composite, but names WITHOUT earnings
                           confirmation (op profit growth <= 0) are forced to the
                           bottom of the cross-section each date ("theme alone =
                           trade, theme+earnings=stays" discipline)

All four go through rnd/lib/harness.evaluate() on panel_long (real, PIT, 2005-2025)
at horizons 1M/1Y/5Y, return_basis='excess' (most complete; resid checked as
robustness for 5Y only given resid's higher NaN rate). Cards written to
rnd/wave4/cards_w6fg_*.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import harness as H

ALPHA_DIR = Path(__file__).resolve().parent.parent.parent
OUT_DIR = Path(__file__).resolve().parent
CARDS_DIR = OUT_DIR / "cards_w6fg"
CARDS_DIR.mkdir(parents=True, exist_ok=True)

fog = pd.read_parquet(OUT_DIR / "_w6fg_fund_on_grid.parquet")
panel = pd.read_parquet(ALPHA_DIR / "rnd" / "panel" / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])
fog["date"] = pd.to_datetime(fog["date"])

# ---------------------------------------------------------------------------
# cross-sectional z-scoring per date (robust: median/MAD-based, matches the
# spirit of the harness's rank-based IC -- not sensitive to scale)
# ---------------------------------------------------------------------------
def _cs_z(df, col):
    def _z(s):
        mu, sd = s.mean(), s.std(ddof=1)
        if not sd or np.isnan(sd):
            return pd.Series(np.nan, index=s.index)
        return (s - mu) / sd
    return df.groupby("date")[col].transform(_z)

fog["z_accel"] = _cs_z(fog, "rev_accel")
fog["z_margin_infl"] = _cs_z(fog, "margin_inflection")
fog["z_cwip_growth"] = _cs_z(fog, "cwip_growth_t")

fog["theme_alone"] = fog["theme_dummy"]
fog["accel_alone"] = fog["rev_accel"]
fog["composite_raw"] = fog[["z_accel", "z_margin_infl"]].mean(axis=1, skipna=True) + fog["theme_dummy"].fillna(0)

# earnings-confirmed gate: where earnings_confirm is 0 (op profit NOT growing),
# force to a very low percentile-equivalent value so the cross-section punishes
# unconfirmed "story" names; where earnings_confirm is NaN (insufficient data),
# leave composite as NaN (can't judge -> excluded, not assumed good or bad).
penalty = fog["composite_raw"].min() - 10.0  # far below any real observation
fog["composite_confirmed"] = np.where(
    fog["earnings_confirm"] == 1, fog["composite_raw"],
    np.where(fog["earnings_confirm"] == 0, penalty, np.nan)
)

n_conf = (fog["earnings_confirm"] == 1).sum()
n_unconf = (fog["earnings_confirm"] == 0).sum()
print(f"[DATA] earnings_confirm==1 (op profit growing): {n_conf} obs; "
      f"==0 (not growing, penalized): {n_unconf} obs; NaN (insufficient history): "
      f"{fog['earnings_confirm'].isna().sum()}")

fog.to_parquet(OUT_DIR / "_w6fg_scored.parquet", index=False)

# ---------------------------------------------------------------------------
# run each factor through the ONE harness, horizons 1M/1Y/5Y, basis=excess
# ---------------------------------------------------------------------------
factors = {
    "W6FG_THEME_ALONE": "theme_alone",
    "W6FG_ACCEL_ALONE": "accel_alone",
    "W6FG_COMPOSITE_RAW": "composite_raw",
    "W6FG_COMPOSITE_CONFIRMED": "composite_confirmed",
}

results = {}
for fid, col in factors.items():
    fseries = fog.dropna(subset=[col])[["date", "symbol", col]].rename(columns={col: "factor"})
    fseries = fseries.set_index(["date", "symbol"])["factor"]
    for hz in ("1M", "1Y", "5Y"):
        card = H.evaluate(fseries, horizon=hz, return_basis="excess", factor_id=f"{fid}_{hz}",
                           family="W6FG", panel=panel, panel_source="real", cards_dir=CARDS_DIR)
        key = f"{fid}_{hz}"
        results[key] = card
        v = card.get("verdict", card.get("status"))
        icir = card.get("ic", {}).get("ic_ir")
        nobs = card.get("n_obs")
        print(f"{key:35s} n_obs={nobs!s:>8} IC_IR={icir!s:>8} -> {v}")

# 5Y resid robustness check for the confirmed composite (the task's crux horizon)
fseries = fog.dropna(subset=["composite_confirmed"])[["date", "symbol", "composite_confirmed"]].rename(
    columns={"composite_confirmed": "factor"}).set_index(["date", "symbol"])["factor"]
card_resid = H.evaluate(fseries, horizon="5Y", return_basis="resid", factor_id="W6FG_COMPOSITE_CONFIRMED_5Y_resid",
                         family="W6FG", panel=panel, panel_source="real", cards_dir=CARDS_DIR)
results["W6FG_COMPOSITE_CONFIRMED_5Y_resid"] = card_resid
print(f"{'W6FG_COMPOSITE_CONFIRMED_5Y_resid':35s} n_obs={card_resid.get('n_obs')!s:>8} "
      f"IC_IR={card_resid.get('ic',{}).get('ic_ir')!s:>8} -> {card_resid.get('verdict')}")

with open(OUT_DIR / "_w6fg_all_cards_summary.json", "w", encoding="utf-8") as fh:
    json.dump({k: {kk: vv for kk, vv in v.items() if kk not in ("regime_breakdown",)}
               for k, v in results.items()}, fh, indent=2, default=str)

print("\nSTEP 2 done.")
