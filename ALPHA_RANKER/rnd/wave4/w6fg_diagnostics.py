"""
W6FG STEP 3: diagnostics beyond the harness's single-factor KILL/PROMOTE gate --
NOTE: across the ENTIRE firm's rnd/cards/ library (558 evaluated factors with a
PBO number), median PBO = 0.98 and essentially 0% pass PBO<=0.5 (verified this
session). The harness's single-factor CSCV/PBO adaptation is documented in its
own docstring as "not the literal multi-strategy paper procedure" and in
practice near-universally triggers KILL. So a harness "KILL" verdict here is
NOT on its own evidence this factor is worse than the validated 7-leg (which
would ALSO fail this same PBO gate) -- the diagnostic weight has to sit on
IC_IR + Newey-West t-stat + monotonicity + hit-rate + sign-stability, which
DO discriminate (see accel_alone: NW-t -3.2, clearly real and clearly bad;
theme_alone: NW-t -0.48, indistinguishable from noise).

This step:
  A. earnings_confirm dummy as its OWN standalone factor (does op-profit-growth
     carry information on its own, independent of the composite injection)
  B. informal (non-harness) split: Spearman IC of composite_raw computed
     SEPARATELY within earnings_confirm==1 vs ==0 subsets, to see whether
     conditioning (not blunt penalty-injection) reveals a cleaner story
  C. Fama-MacBeth: fwd_ret ~ value7leg_score + composite_raw per date,
     average coefficient + NW t-stat on the growth term = does forward-growth
     add anything BEYOND the value/quality legs
  D. GARP 2x2 quadrant (value7leg_score x composite_raw, median split/date):
     mean forward return per quadrant + the earnings_confirm split WITHIN the
     "expensive+growing" cell (multibagger-vs-trap separation test)
  E. INFY / KPIGREEN case pull for ex-ante adjudication
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

fog = pd.read_parquet(OUT_DIR / "_w6fg_scored.parquet")
panel = pd.read_parquet(ALPHA_DIR / "rnd" / "panel" / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])
fog["date"] = pd.to_datetime(fog["date"])

results = {}

# ---------------------------------------------------------------------------
# A. earnings_confirm dummy alone, through the harness
# ---------------------------------------------------------------------------
print("="*70, "\nA. earnings_confirm dummy alone (op-profit-growth>0)\n" + "="*70)
fseries = fog.dropna(subset=["earnings_confirm"])[["date", "symbol", "earnings_confirm"]].rename(
    columns={"earnings_confirm": "factor"}).set_index(["date", "symbol"])["factor"]
for hz in ("1Y", "5Y"):
    c = H.evaluate(fseries, horizon=hz, return_basis="excess", factor_id=f"W6FG_EARNCONFIRM_ALONE_{hz}",
                   family="W6FG", panel=panel, panel_source="real", cards_dir=CARDS_DIR)
    results[f"EARNCONFIRM_ALONE_{hz}"] = c
    print(f"{hz}: IC_IR={c['ic']['ic_ir']:.3f} NW_t={c['ic']['newey_west_t']:.2f} "
          f"mono={c['deciles']['monotonicity']:.2f} hit_rate={c['long_short']['hit_rate']:.2f} "
          f"-> {c['verdict']}")

# ---------------------------------------------------------------------------
# B. within-group IC (composite_raw), conditioned NOT gated
# ---------------------------------------------------------------------------
print("\n" + "="*70 + "\nB. composite_raw IC conditioned on earnings_confirm (informal, non-harness)\n" + "="*70)

def _cond_ic(df, hz):
    col = f"fwd_ret_{hz}_excess"
    m = df.merge(panel[["date","symbol",col]], on=["date","symbol"], how="inner").dropna(subset=["composite_raw", col])
    out = {}
    for flag, label in [(1.0, "confirmed"), (0.0, "unconfirmed")]:
        sub = m[m["earnings_confirm"] == flag]
        ics = sub.groupby("date").apply(
            lambda g: stats.spearmanr(g["composite_raw"], g[col])[0] if len(g) >= 15 else np.nan,
            include_groups=False).dropna()
        nw = H.newey_west_tstat(ics, H.HORIZON_PERIODS[hz])
        out[label] = {"ic_mean": float(ics.mean()) if len(ics) else np.nan,
                      "ic_ir": float(ics.mean()/ics.std(ddof=1)) if len(ics) > 1 and ics.std(ddof=1) else np.nan,
                      "nw_t": nw["t_stat"], "n_dates": int(len(ics)), "n_obs": int(len(sub))}
    return out

for hz in ("1Y", "5Y"):
    r = _cond_ic(fog, hz)
    results[f"COND_IC_{hz}"] = r
    print(f"{hz}: confirmed -> IC_mean={r['confirmed']['ic_mean']:.4f} IC_IR={r['confirmed']['ic_ir']:.3f} "
          f"NW_t={r['confirmed']['nw_t']:.2f} n_obs={r['confirmed']['n_obs']}")
    print(f"     unconfirmed -> IC_mean={r['unconfirmed']['ic_mean']:.4f} IC_IR={r['unconfirmed']['ic_ir']:.3f} "
          f"NW_t={r['unconfirmed']['nw_t']:.2f} n_obs={r['unconfirmed']['n_obs']}")

# ---------------------------------------------------------------------------
# C. Fama-MacBeth: fwd_ret ~ value7leg + composite_raw, per date, avg + NW-t
# ---------------------------------------------------------------------------
print("\n" + "="*70 + "\nC. Fama-MacBeth: does forward-growth add beyond value/quality (7-leg)?\n" + "="*70)

def _fmb(df, hz, growth_col="composite_raw"):
    col = f"fwd_ret_{hz}_excess"
    m = df.merge(panel[["date","symbol",col]], on=["date","symbol"], how="inner").dropna(
        subset=["value7leg_score", growth_col, col])
    betas = []
    for d, g in m.groupby("date"):
        if len(g) < 25:
            continue
        X = np.column_stack([np.ones(len(g)),
                              stats.zscore(g["value7leg_score"].values),
                              stats.zscore(g[growth_col].values)])
        y = g[col].values
        try:
            b, *_ = np.linalg.lstsq(X, y, rcond=None)
        except Exception:
            continue
        betas.append({"date": d, "const": b[0], "value": b[1], "growth": b[2], "n": len(g)})
    bdf = pd.DataFrame(betas)
    out = {}
    for coef in ("value", "growth"):
        s = bdf[coef].dropna()
        nw = H.newey_west_tstat(s, H.HORIZON_PERIODS[hz])
        out[coef] = {"mean": float(s.mean()), "nw_t": nw["t_stat"], "n_dates": int(len(s))}
    return out, bdf

for hz in ("1Y", "5Y"):
    out, bdf = _fmb(fog, hz, "composite_raw")
    results[f"FMB_{hz}"] = out
    print(f"{hz} (n_dates={out['value']['n_dates']}): "
          f"value_coef={out['value']['mean']:.4f} (NW_t={out['value']['nw_t']:.2f})  "
          f"growth_coef={out['growth']['mean']:.4f} (NW_t={out['growth']['nw_t']:.2f})")

# ---------------------------------------------------------------------------
# D. GARP quadrant (median split value7leg_score x composite_raw, per date)
# ---------------------------------------------------------------------------
print("\n" + "="*70 + "\nD. GARP 2x2 quadrant\n" + "="*70)

def _quadrant(df, hz):
    col = f"fwd_ret_{hz}_raw"
    m = df.merge(panel[["date","symbol",col]], on=["date","symbol"], how="inner").dropna(
        subset=["value7leg_score", "composite_raw", col])
    def _tag(g):
        vmed = g["value7leg_score"].median()
        gmed = g["composite_raw"].median()
        cheap = g["value7leg_score"] >= vmed
        grow = g["composite_raw"] >= gmed
        g = g.copy()
        g["quad"] = np.select(
            [cheap.values & grow.values, (~cheap).values & grow.values,
             cheap.values & (~grow).values, (~cheap).values & (~grow).values],
            ["Q1_cheap_growing_GARP", "Q2_expensive_growing_STORY", "Q3_cheap_notgrowing_VALUETRAP", "Q4_expensive_notgrowing_AVOID"],
            default="NA")
        g["earnings_confirm"] = df.loc[g.index, "earnings_confirm"] if "earnings_confirm" in df.columns else np.nan
        return g
    m = m.groupby("date", group_keys=False).apply(_tag, include_groups=False)
    summ = m.groupby("quad")[col].agg(["mean", "std", "count"])
    summ["ann_1yr_equiv"] = summ["mean"] / H.HORIZON_YEARS[hz]
    # t-stat per quadrant vs 0
    summ["t_stat"] = summ["mean"] / (summ["std"] / np.sqrt(summ["count"]))
    return summ, m

for hz in ("1Y", "5Y"):
    summ, m = _quadrant(fog, hz)
    results[f"QUADRANT_{hz}"] = summ.to_dict()
    print(f"\n-- horizon {hz} --")
    print(summ)
    # within Q2 (expensive+growing STORY), split by earnings_confirm
    q2 = m[m["quad"] == "Q2_expensive_growing_STORY"]
    if "earnings_confirm" in q2.columns:
        sub = q2.dropna(subset=["earnings_confirm"])
        col = f"fwd_ret_{hz}_raw"
        gg = sub.groupby("earnings_confirm")[col].agg(["mean", "std", "count"])
        print(f"  Q2 split by earnings_confirm ({hz}):")
        print(gg)
        results[f"QUADRANT_Q2_SPLIT_{hz}"] = gg.to_dict()

# ---------------------------------------------------------------------------
# E. INFY / KPIGREEN case pull
# ---------------------------------------------------------------------------
print("\n" + "="*70 + "\nE. INFY / KPIGREEN ex-ante case files\n" + "="*70)
for sym in ["INFY", "KPIGREEN"]:
    print(f"\n--- {sym} ---")
    sub = fog[fog.symbol == sym].sort_values("date").tail(8)
    cols = ["date","rev_growth_t","rev_accel","op_growth_t","margin_inflection","cwip_growth_t",
            "cwip_intensity","earnings_confirm","theme_dummy","composite_raw","composite_confirmed","value7leg_score"]
    print(sub[cols].to_string(index=False))
    # realized forward returns where available
    real = panel[panel.symbol == sym][["date","fwd_ret_1Y_raw","fwd_ret_5Y_raw"]].sort_values("date").tail(8)
    print(" realized fwd returns (tail):")
    print(real.to_string(index=False))

with open(OUT_DIR / "_w6fg_diagnostics_summary.json", "w", encoding="utf-8") as fh:
    json.dump(results, fh, indent=2, default=str)
print("\nSTEP 3 done ->", OUT_DIR / "_w6fg_diagnostics_summary.json")
