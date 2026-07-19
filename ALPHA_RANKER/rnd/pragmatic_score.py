"""Money-first scoreboard. Reads rnd/cards/*.json and ranks factors by PRACTICAL edge.
HARD gates (only these can veto — they catch self-deception): lookahead (lag_test_delta>0.25)
and placebo leak (|placebo_ic|>0.02). Everything else (net-of-cost LS return, IC_IR, monotonicity,
hit-rate) is a RANKING. PBO/DSR are shown as ADVISORY flags, not kills (they're structurally
near-1 on our small monthly sample — see momentum/vol worker findings)."""
import json, glob, os
import numpy as np, pandas as pd

C = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER\rnd"
def g(d, *path, default=np.nan):
    for p in path:
        if isinstance(d, dict) and p in d: d = d[p]
        else: return default
    return d

rows = []
for f in glob.glob(os.path.join(C, "cards", "*.json")):
    d = json.load(open(f))
    if g(d, "status", default="OK") not in ("OK", None):
        # deferred/parked cards
        rows.append({"id": g(d,"factor_id"), "horizon": g(d,"horizon"), "status": g(d,"status")}); continue
    turn = g(d, "turnover", "avg_top_decile_turnover", default=np.nan)
    cost = g(d, "costs", "blended_cost_bps_roundtrip", default=80)
    gross = g(d, "long_short", "ann_return_LS", default=np.nan)
    net = gross - (turn * (cost/10000.0) * 12) if np.isfinite(gross) and np.isfinite(turn) else gross
    lag = g(d, "lag_test", "lag_test_delta", default=np.nan)
    plac = abs(g(d, "placebo", "placebo_ic", default=0) or 0)
    rows.append({
        "id": g(d,"factor_id"), "family": g(d,"family"), "horizon": g(d,"horizon"), "basis": g(d,"return_basis"),
        "ic_ir": g(d,"ic","ic_ir"), "ic_mean": g(d,"ic","ic_mean"), "mono": g(d,"deciles","monotonicity"),
        "hit": g(d,"long_short","hit_rate"), "gross_LS": gross, "net_LS": net, "turnover": turn,
        "pbo": g(d,"pbo","pbo"), "dsr": g(d,"dsr","dsr"), "lag": lag, "placebo": plac,
        "ic_bull": g(d,"regime_breakdown","regime_trend","bull"),
        "ic_bear": g(d,"regime_breakdown","regime_trend","bear"),
        "ic_side": g(d,"regime_breakdown","regime_trend","sideways"),
        "ic_lovol": g(d,"regime_breakdown","regime_vol","low"),
        "ic_hivol": g(d,"regime_breakdown","regime_vol","high"),
        "status": "OK"})
df = pd.DataFrame(rows)
ok = df[df["status"]=="OK"].copy()

# HARD gates (self-deception only)
ok["gate_fail"] = ((ok["lag"] > 0.25) | (ok["placebo"] > 0.02)).map({True:"LOOKAHEAD/PLACEBO", False:""})

def z(s):
    s = pd.to_numeric(s, errors="coerce");
    return (s - s.mean())/s.std(ddof=0) if s.std(ddof=0) else s*0
# rank within horizon
ok["net_cap"] = pd.to_numeric(ok["net_LS"], errors="coerce").clip(-3, 3)   # cap runaway small-sample LS
parts = []
for h, grp in ok.groupby("horizon"):
    grp = grp.copy()
    grp["edge_score"] = (0.35*z(grp["ic_ir"].abs()*np.sign(grp["ic_ir"]))
                         + 0.25*z(grp["mono"]) + 0.25*z(grp["net_cap"]) + 0.15*z(grp["hit"])
                         - 0.10*z(grp["turnover"]))
    parts.append(grp)
ok = pd.concat(parts)
def verdict(r):
    if r["gate_fail"]: return "FAIL_GATE"
    if (r["ic_ir"]>0.3) and (r["mono"]>0.5) and (r["net_LS"]>0) and (r["hit"]>=0.55): return "PROMOTE*"
    if (r["ic_ir"]>0.2) and (r["mono"]>0.3) and (r["net_LS"]>0): return "CANDIDATE"
    return "WEAK"
ok["verdict_v2"] = ok.apply(verdict, axis=1)
# REGIME-GOLD (Principal): weak pooled but STRONG in a causally-identifiable regime = valuable (regime label at t is lookahead-free)
regcols = ["ic_bull","ic_bear","ic_side","ic_lovol","ic_hivol"]
def best_regime(r):
    vals = {c[3:]: r[c] for c in regcols if pd.notna(r.get(c, np.nan))}
    if not vals: return None, np.nan
    k = max(vals, key=lambda c: abs(vals[c])); return k, vals[k]
br = ok.apply(lambda r: pd.Series(best_regime(r), index=["best_regime","best_regime_ic"]), axis=1)
ok = pd.concat([ok, br], axis=1)
ok["regime_gold"] = ((ok["gate_fail"]=="") & (ok["verdict_v2"].isin(["WEAK","CANDIDATE"]))
                     & (ok["best_regime_ic"].abs() >= 0.06)
                     & (ok["best_regime_ic"].abs() >= 1.5*ok["ic_mean"].abs()))   # regime IC clearly beats pooled
ok = ok.sort_values(["horizon","edge_score"], ascending=[True,False])
ok.to_csv(os.path.join(C, "scoreboard.csv"), index=False)

pd.set_option("display.width", 230); pd.set_option("display.max_rows", 60)
show = ["id","family","horizon","basis","ic_ir","mono","hit","net_LS","turnover","pbo","lag","verdict_v2"]
print("SCOREBOARD (money-first; PBO advisory). cards:", len(df), "OK:", len(ok),
      "| PROMOTE*:", int((ok.verdict_v2=='PROMOTE*').sum()),
      "CANDIDATE:", int((ok.verdict_v2=='CANDIDATE').sum()),
      "FAIL_GATE:", int((ok.verdict_v2=='FAIL_GATE').sum()))
print("\n=== TOP 20 by practical edge ===")
print(ok.head(20)[show].round(3).to_string(index=False))
print("\n=== PROMOTE* + CANDIDATE ===")
print(ok[ok.verdict_v2.isin(["PROMOTE*","CANDIDATE"])][show].round(3).to_string(index=False))
print("\n=== REGIME-GOLD (weak pooled, STRONG in a lookahead-free identifiable regime) ===")
gshow = ["id","family","horizon","ic_mean","ic_bull","ic_bear","ic_side","ic_lovol","ic_hivol","best_regime","best_regime_ic"]
gold = ok[ok["regime_gold"]]
print(f"count: {len(gold)}")
print(gold[[c for c in gshow if c in ok.columns]].round(3).to_string(index=False) if len(gold) else "(none yet)")
