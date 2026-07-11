# -*- coding: utf-8 -*-
"""RED-TEAM 2 (Nikhil Bose): lag-decay + year-exclusion for MIDSMALL Var-B (frozen engine)."""
import sys, json, pickle
import numpy as np, pandas as pd
OUT=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707"
LIB=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/lib"
sys.path.insert(0, OUT); sys.path.insert(0, LIB)
import midsmall_mom_rotation as M

def stats(ret):
    r=ret.dropna(); eq=(1+r).cumprod(); yrs=len(r)/252.0
    return dict(cagr=float(eq.iloc[-1]**(1/yrs)-1), sharpe=float(r.mean()/(r.std()+1e-12)*np.sqrt(252)),
                maxdd=float((eq/eq.cummax()-1).min()), finalV=float((1+r).prod()))

# ---- LAG DECAY (enter 0/1/2/3/5 trading days late) ----
print("=== LAG-DECAY (Var-B) — a fast signal degrades; slow drift/regime does NOT ===")
lag=[]
base=None
for L in [0,1,2,3,5]:
    dd,_,_,_=M.run_backtest("B",L,M.CASH_RATE,1.0,False,"lag%d"%L)
    s=stats(dd["ret"]);
    if L==0: base=s
    s["lag"]=L; s["cagr_ret"]=s["cagr"]/base["cagr"]; s["sharpe_ret"]=s["sharpe"]/base["sharpe"]
    lag.append(s)
    print("  lag %d: CAGR %.4f (%.0f%% of base) Sharpe %.3f (%.0f%%) MaxDD %.3f"
          %(L,s["cagr"],s["cagr_ret"]*100,s["sharpe"],s["sharpe_ret"]*100,s["maxdd"]))

# ---- YEAR-EXCLUSION (drop each CY from the daily-return chain) ----
with open(OUT+"/_raw_results.pkl","rb") as f: R=pickle.load(f)
r=R["B_1x"][0]["ret"].dropna()
full=stats(r)
print("\n=== YEAR-EXCLUSION (Var-B) full CAGR %.4f finalV %.3f ==="%(full["cagr"],full["finalV"]))
yr=[]
for y in sorted(set(r.index.year)):
    sub=r[r.index.year!=y]; s=stats(sub)
    cy=(1+r[r.index.year==y]).prod()-1
    yr.append(dict(drop_year=int(y),cy_ret=float(cy),cagr_ex=s["cagr"],sharpe_ex=s["sharpe"],finalV_ex=s["finalV"]))
    print("  drop %d (CY %+6.1f%%): CAGR ex=%.4f  Sharpe ex=%.3f  finalV ex=%.3f"%(y,cy*100,s["cagr"],s["sharpe"],s["finalV"]))
# drop the two monster years together
sub=r[~r.index.year.isin([2021,2023])]; s2=stats(sub)
print("  drop 2021+2023 together: CAGR ex=%.4f  Sharpe ex=%.3f  finalV ex=%.3f"%(s2["cagr"],s2["sharpe"],s2["finalV"]))

json.dump(dict(lag=lag,year_excl=yr,drop_2021_2023=s2,full=full),
          open(OUT+"/varb_rt_2_robust.json","w"),indent=2)
print("\nWROTE varb_rt_2_robust.json  DONE")
