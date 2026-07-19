"""Runner: IDG-G-03/04/05 investment-issuance anomalies vs panel_long, 1Y & 5Y,
basis=resid. Writes rnd/cards/IDG_G0{3,4,5}_*_{1Y,5Y}.json via the shared
harness, plus an era-split (pre-2015 vs post-2015) advisory diagnostic per
DATA-TRUST directive (AUTONOMOUS_PLAN.md). Hard gates = lag+placebo (harness
verdict already enforces lag_test_delta/placebo_ic/ic_ir/dsr thresholds);
PBO/DSR are advisory only for this pass per the WAVE brief.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

RND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RND_DIR / "lib"))
import harness
from builders_w2_issuance import BUILDERS

PANEL_LONG_PATH = RND_DIR / "panel" / "panel_long.parquet"


def era_split_ic(factor: pd.Series, panel: pd.DataFrame, horizon: str, basis: str = "resid",
                  cutoff_year: int = 2015, min_names: int = 20) -> dict:
    """Advisory-only signed cross-sectional IC split by calendar year of the
    rebalance date, NOT part of the hard-gate harness (disclosed separately)."""
    target_col = f"fwd_ret_{horizon}_{basis}"
    f = factor.rename("factor").reset_index()
    f["date"] = pd.to_datetime(f["date"])
    p = panel[["date", "symbol", target_col]].copy()
    p["date"] = pd.to_datetime(p["date"])
    m = f.merge(p, on=["date", "symbol"], how="inner").dropna(subset=["factor", target_col])
    m["year"] = m["date"].dt.year

    def _ic_by_era(sub):
        def _ic(g):
            if len(g) < min_names:
                return np.nan
            rho, _ = stats.spearmanr(g["factor"], g[target_col])
            return rho
        s = sub.groupby("date").apply(_ic, include_groups=False).dropna()
        if len(s) < 3:
            return {"ic_mean": None, "ic_ir": None, "n_dates": int(len(s))}
        ic_mean = float(s.mean())
        ic_std = float(s.std(ddof=1))
        ic_ir = float(ic_mean / ic_std) if ic_std else None
        return {"ic_mean": ic_mean, "ic_ir": ic_ir, "n_dates": int(len(s))}

    pre = m[m["year"] < cutoff_year]
    post = m[m["year"] >= cutoff_year]
    return {"pre_2015": _ic_by_era(pre), "post_2015": _ic_by_era(post)}


def main():
    panel = pd.read_parquet(PANEL_LONG_PATH)
    panel["date"] = pd.to_datetime(panel["date"])
    print(f"panel_long: rows={len(panel)} dates={panel['date'].nunique()} symbols={panel['symbol'].nunique()}")

    results = {}
    for name, builder_fn in BUILDERS.items():
        factor = builder_fn(panel)
        print(f"{name}: n_obs={len(factor)} n_dates={factor.index.get_level_values('date').nunique()}")
        for horizon in ("1Y", "5Y"):
            factor_id = f"{name}_{horizon}"
            card = harness.evaluate(factor, horizon=horizon, return_basis="resid",
                                     factor_id=factor_id, panel=panel, panel_source="real_long",
                                     family="IDG_G0345")
            era = era_split_ic(factor, panel, horizon)
            card["era_split_advisory"] = era
            # rewrite card with era split appended
            (RND_DIR / "cards" / f"{factor_id}.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
            results[factor_id] = card
            ic_ir = card.get("ic", {}).get("ic_ir")
            lag_d = card.get("lag_test", {}).get("lag_test_delta")
            mono = card.get("deciles", {}).get("monotonicity")
            print(f"  {factor_id}: ic_ir={ic_ir} mono={mono} lag_delta={lag_d} verdict={card.get('verdict')}")
            print(f"    era_split: pre2015={era['pre_2015']} post2015={era['post_2015']}")

    summary_path = RND_DIR / "reports" / "IDG_G0345_summary.json"
    summary_path.write_text(json.dumps(
        {k: {"ic_ir": v.get("ic", {}).get("ic_ir"),
             "mono": v.get("deciles", {}).get("monotonicity"),
             "lag_delta": v.get("lag_test", {}).get("lag_test_delta"),
             "placebo_ic": v.get("placebo", {}).get("placebo_ic"),
             "pbo": v.get("pbo", {}).get("pbo"),
             "dsr": v.get("dsr", {}).get("dsr"),
             "verdict": v.get("verdict"),
             "era_split": v.get("era_split_advisory")}
            for k, v in results.items()}, indent=2), encoding="utf-8")
    print(f"\nsummary written: {summary_path}")


if __name__ == "__main__":
    main()
