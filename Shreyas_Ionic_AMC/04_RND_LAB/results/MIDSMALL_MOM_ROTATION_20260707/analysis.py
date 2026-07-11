# -*- coding: utf-8 -*-
"""Analysis / deliverables for MIDSMALL_MOM_ROTATION. Imports the frozen engine (reuses data)."""
import sys, os, json, pickle
import numpy as np, pandas as pd
OUT=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707"
sys.path.insert(0, OUT)
sys.path.insert(0, r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/lib")
import guards as G
import midsmall_mom_rotation as M   # reuses close,dret,cal,members_asof,mss400,n500idx,sc100,ema200,gold

with open(OUT+"/_raw_results.pkl","rb") as f: R=pickle.load(f)

def stats(ret):
    r=ret.dropna(); 
    if len(r)<30: return {}
    eq=(1+r).cumprod(); yrs=len(r)/252.0
    return dict(cagr=float(eq.iloc[-1]**(1/yrs)-1), sharpe=float(r.mean()/(r.std()+1e-12)*np.sqrt(252)),
                maxdd=float((eq/eq.cummax()-1).min()), vol=float(r.std()*np.sqrt(252)), ndays=int(len(r)),
                finalV=float((1+r).prod()))
def cy(ret): 
    g=(1+ret).groupby(ret.index.year).prod()-1; return {int(k):float(v) for k,v in g.items()}
def nav_from_ret(ret, v0=1.0):
    return v0*(1+ret.fillna(0)).cumprod()
def trailing_cagr(nav, yrs):
    end=nav.index[-1]; start=end-pd.DateOffset(years=yrs)
    sub=nav[nav.index>=start]
    if len(sub)<20 or (sub.index[0]-start)>pd.Timedelta(days=25): return None
    y=(sub.index[-1]-sub.index[0]).days/365.25
    return float((sub.iloc[-1]/sub.iloc[0])**(1/y)-1)

# ---- benchmark series aligned to strategy window ----
first=R["A_1x"][0].index[0]; last=R["A_1x"][0].index[-1]
n500=M.n500idx[(M.n500idx.index>=first)&(M.n500idx.index<=last)]
n500ret=n500.pct_change(); n500nav=n500/n500.iloc[0]
mss=M.mss400[(M.mss400.index>=first)&(M.mss400.index<=last)]; mssret=mss.pct_change()
print("window",first.date(),"->",last.date())

# ---- per-variant metrics ----
summary={}
for tag,(dd,td,rb,meta) in R.items():
    s=stats(dd["ret"])
    st=dd["state"].value_counts(normalize=True).to_dict()
    rbret=rb["V"].pct_change().dropna()
    win=float((rbret>0).mean()); 
    tv=td[td["still_open"]==0] if len(td) else td
    flags=G.degenerate_flags(dd["ret"], td.rename(columns={}), ret_col="ret", sym_col="sym") if len(td)>10 else []
    summary[tag]=dict(meta=meta, stats=s,
        time_in=dict(EQUITY=float(st.get("EQUITY",0)),GOLD=float(st.get("GOLD",0)),CASH=float(st.get("CASH",0))),
        rebal_win_pct=win, n_rebal_periods=int(len(rbret)), n_trades=int(len(td)),
        n_open_at_end=int(td["still_open"].sum()) if len(td) else 0, degenerate_flags=flags)
    print(f"{tag}: CAGR {s['cagr']*100:5.1f}% Sharpe {s['sharpe']:.2f} MaxDD {s['maxdd']*100:6.1f}% "
          f"vol {s['vol']*100:.1f}% | eq {summary[tag]['time_in']['EQUITY']*100:.0f}% gold {summary[tag]['time_in']['GOLD']*100:.0f}% "
          f"cash {summary[tag]['time_in']['CASH']*100:.0f}% | win {win*100:.0f}% turn {meta['turnover_ann']:.1f} flags={flags}")

# ---- benchmark stats ----
bench={"NIFTY500":dict(stats=stats(n500ret), cy=cy(n500ret)),
       "MSS400_idx":dict(stats=stats(mssret), cy=cy(mssret))}
print("\nNIFTY500 buy-hold:", {k:round(v,3) for k,v in bench["NIFTY500"]["stats"].items()})
print("MSS400 index    :", {k:round(v,3) for k,v in bench["MSS400_idx"]["stats"].items()})

# ---- CY table (strategy A/B 1x + n500 + mss + BSE) ----
years=sorted(set(list(cy(R["A_1x"][0]["ret"]).keys())+list(bench["NIFTY500"]["cy"].keys())))
BSE_CY={2025:-0.0247}   # only real annual figure available (=1Y as of 31-Dec-2025)
cyA=cy(R["A_1x"][0]["ret"]); cyB=cy(R["B_1x"][0]["ret"]); cyN=bench["NIFTY500"]["cy"]; cyM=bench["MSS400_idx"]["cy"]
print("\n=== CALENDAR-YEAR RETURNS (%) ===")
print(f"{'Year':>6} {'VarA':>8} {'VarB':>8} {'N500':>8} {'MSS400':>8} {'BSEMom30':>9}")
cy_rows=[]
for y in years:
    row=dict(year=y, VarA=cyA.get(y), VarB=cyB.get(y), N500=cyN.get(y), MSS400=cyM.get(y), BSEMom30=BSE_CY.get(y))
    cy_rows.append(row)
    def f(x): return f"{x*100:7.1f}" if x is not None else "     -- "
    print(f"{y:>6} {f(row['VarA'])} {f(row['VarB'])} {f(row['N500'])} {f(row['MSS400'])} {f(row['BSEMom30'])[:9]:>9}")

# ---- trailing CAGR ----
navA=nav_from_ret(R["A_1x"][0]["ret"]); navB=nav_from_ret(R["B_1x"][0]["ret"])
BSE_TRAIL={"1Y":-0.0247,"3Y":0.3511,"5Y":0.3662,"10Y":0.2721}
print("\n=== TRAILING CAGR (%) as of", last.date(), "(BSE as of 2025-12-31, backtested pre-2026-01-12 launch) ===")
print(f"{'Horizon':>8} {'VarA':>8} {'VarB':>8} {'N500':>8} {'BSEMom30':>9}")
trail={}
for h in [1,3,5,10]:
    a=trailing_cagr(navA,h); b=trailing_cagr(navB,h); n=trailing_cagr(n500nav,h); s=BSE_TRAIL.get(f"{h}Y")
    trail[f"{h}Y"]=dict(VarA=a,VarB=b,N500=n,BSEMom30=s)
    def f(x): return f"{x*100:7.1f}" if x is not None else "     -- "
    print(f"{h:>6}Y  {f(a)} {f(b)} {f(n)} {f(s)[:9]:>9}")

# ---- one-day-lag lookahead test ----
sA=stats(R["A_1x"][0]["ret"])["sharpe"]; sAl=stats(R["A_lag1"][0]["ret"])["sharpe"]
cA=stats(R["A_1x"][0]["ret"])["cagr"]; cAl=stats(R["A_lag1"][0]["ret"])["cagr"]
lag_test=dict(sharpe_base=sA,sharpe_lag1=sAl,sharpe_retained=float(sAl/sA) if sA else None,
              cagr_base=cA,cagr_lag1=cAl,cagr_retained=float(cAl/cA) if cA else None)
print("\n=== ONE-DAY-LAG TEST (Var A) ===",{k:round(v,3) if v is not None else None for k,v in lag_test.items()})

# ---- proxy universe (N500 minus N200) vs real MSS400 index: daily-return correlation ----
months=pd.date_range(first,last,freq="MS")
proxy_ret=pd.Series(index=M.cal,dtype=float)
dret=M.dret; colix={c:k for k,c in enumerate(M.close.columns)}
for mi,ms in enumerate(months):
    d=ms; U=M.members_asof(d,M.m500,M.s500)-M.members_asof(d,M.m200,M.s200)
    cols=[colix[s] for s in U if s in colix]
    end=months[mi+1] if mi+1<len(months) else last+pd.Timedelta(days=40)
    mask=(M.cal>=ms)&(M.cal<end)
    if cols and mask.any():
        proxy_ret.loc[M.cal[mask]]=np.nanmean(dret.values[np.ix_(np.where(mask)[0],cols)],axis=1)
pr=proxy_ret[(proxy_ret.index>=first)&(proxy_ret.index<=last)]
both=pd.concat([pr.rename("proxy"),mssret.rename("mss")],axis=1).dropna()
corr=float(both["proxy"].corr(both["mss"]))
print(f"\nProxy(N500-N200 EW) vs real MSS400 index daily-return corr = {corr:.3f}  (n={len(both)})")

# ---- write CSV/JSON deliverables ----
R["A_1x"][1].to_csv(OUT+"/trades_variantA.csv",index=False)
R["B_1x"][1].to_csv(OUT+"/trades_variantB.csv",index=False)
R["A_1x"][0][["state"]].to_csv(OUT+"/regime_timeline_variantA.csv")
R["B_1x"][0][["state"]].to_csv(OUT+"/regime_timeline_variantB.csv")
# growth of 1cr, weekly
def wk(nav): return (nav*1e7).resample("W-FRI").last()
gdf=pd.DataFrame({"VariantA_midsmall":wk(navA),"VariantB_fullN500":wk(navB),
                  "Nifty500_buyhold":wk(n500nav)}).dropna(how="all")
gdf.index.name="date"; gdf.to_csv(OUT+"/growth_of_1cr.csv")
out=dict(window=[str(first.date()),str(last.date())],variants=summary,benchmarks=bench,
         cy_table=cy_rows,trailing_cagr=trail,lag_test=lag_test,
         proxy_vs_mss400_corr=corr,proxy_corr_n=len(both),
         BSE_note="BSE Midcap150 Momentum30: launched 2026-01-12; all pre-launch figures backtested/hypothetical (BSE disclaimer). Figures as of 2025-12-31 TR.")
with open(OUT+"/summary_stats.json","w") as f: json.dump(out,f,indent=2,default=str)
print("\nWROTE: trades_variantA/B.csv, regime_timeline_variantA/B.csv, growth_of_1cr.csv, summary_stats.json")
print("DONE")
