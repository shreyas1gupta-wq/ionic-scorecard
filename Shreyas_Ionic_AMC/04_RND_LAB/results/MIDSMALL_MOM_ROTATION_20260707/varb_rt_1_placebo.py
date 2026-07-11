# -*- coding: utf-8 -*-
"""RED-TEAM 1 (Nikhil Bose): random-selection placebo for MIDSMALL Var-B.
Feeds RANDOMIZED cross-sectional scores into the FROZEN engine (midsmall_mom_rotation.run_backtest),
keeping the NaN/eligibility mask byte-identical so regime overlay + gold/cash + fills are unchanged.
Only the cross-sectional STOCK PICK is randomized => isolates SELECTION from regime-timing/beta.
D-029 cap-matched: random 15 drawn from the SAME N500-as-of eligible pool (same cap universe).

CONFOUND CONTROL: run each seed at BOTH cost_mult=1 (NET, contaminated by turnover asymmetry -
random churns fully each rebalance, momentum names persist) AND cost_mult=0 (GROSS = clean
selection test). Also capture turnover to quantify the persistence/cost asymmetry."""
import sys, json
import numpy as np, pandas as pd
OUT=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707"
LIB=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/lib"
sys.path.insert(0, OUT); sys.path.insert(0, LIB)
import midsmall_mom_rotation as M

def stats(ret):
    r=ret.dropna()
    if len(r)<30: return {}
    eq=(1+r).cumprod(); yrs=len(r)/252.0
    return dict(cagr=float(eq.iloc[-1]**(1/yrs)-1), sharpe=float(r.mean()/(r.std()+1e-12)*np.sqrt(252)),
                maxdd=float((eq/eq.cummax()-1).min()), vol=float(r.std()*np.sqrt(252)), finalV=float((1+r).prod()))

orig_score=M.score.copy()
finite=np.isfinite(orig_score.values)
idx=orig_score.index; cols=orig_score.columns
N=int(sys.argv[1]) if len(sys.argv)>1 else 200

def run(score_df, cm, tag):
    M.score=score_df
    dd,td,rb,meta=M.run_backtest("B",0,M.CASH_RATE,cm,False,tag)
    s=stats(dd["ret"]); s["turnover"]=float(meta["turnover_ann"]); return s

# ---- baseline momentum, NET (reproduce banked) and GROSS ----
mom_net=run(orig_score,1.0,"mom_net")
mom_gross=run(orig_score,0.0,"mom_gross")
print("MOMENTUM Var-B NET  : CAGR %.4f Sharpe %.4f MaxDD %.4f finalV %.4f turn %.1f"%(mom_net['cagr'],mom_net['sharpe'],mom_net['maxdd'],mom_net['finalV'],mom_net['turnover']))
print("  (banked B_1x: CAGR 0.2277 Sharpe 1.142 MaxDD -0.2462 finalV 6.2327 turn 22.1)")
print("MOMENTUM Var-B GROSS: CAGR %.4f Sharpe %.4f MaxDD %.4f finalV %.4f turn %.1f"%(mom_gross['cagr'],mom_gross['sharpe'],mom_gross['maxdd'],mom_gross['finalV'],mom_gross['turnover']))

# ---- random-selection placebo x N, NET and GROSS ----
rows=[]
for seed in range(N):
    rng=np.random.default_rng(seed)
    vals=rng.standard_normal(orig_score.shape); vals[~finite]=np.nan
    sdf=pd.DataFrame(vals,index=idx,columns=cols)
    sn=run(sdf,1.0,"rn%d"%seed);  sn={**sn,"seed":seed,"cost":"net"}
    sg=run(sdf,0.0,"rg%d"%seed);  sg={**sg,"seed":seed,"cost":"gross"}
    rows.append(sn); rows.append(sg)
    if (seed+1)%25==0:
        a=pd.DataFrame(rows); an=a[a.cost=="net"]; ag=a[a.cost=="gross"]
        print("  seed %d/%d NET rand CAGR med=%.3f p90=%.3f (mom %.3f) | GROSS rand med=%.3f p90=%.3f (mom %.3f)"
              %(seed+1,N,an['cagr'].median(),an['cagr'].quantile(.9),mom_net['cagr'],
                ag['cagr'].median(),ag['cagr'].quantile(.9),mom_gross['cagr']))
M.score=orig_score

df=pd.DataFrame(rows); df.to_csv(OUT+"/varb_rt_1_placebo_dist.csv",index=False)
def summ(sub,mom):
    out={}
    for k in ["cagr","sharpe","maxdd","finalV","turnover"]:
        out[k]=dict(mom=mom[k], rand_med=float(sub[k].median()), rand_p90=float(sub[k].quantile(.9)),
                    rand_p95=float(sub[k].quantile(.95)), rand_max=float(sub[k].max()),
                    mom_pct=float((sub[k]<mom[k]).mean()))
    return out
res=dict(net=summ(df[df.cost=="net"],mom_net), gross=summ(df[df.cost=="gross"],mom_gross))
print("\n=== RANDOM-SELECTION PLACEBO (N=%d) ==="%N)
for cost,mom in [("net",mom_net),("gross",mom_gross)]:
    print("--- %s ---"%cost.upper())
    for k in ["cagr","sharpe","maxdd","turnover"]:
        r=res[cost][k]
        print("  %-8s mom=%.3f | rand med=%.3f p90=%.3f p95=%.3f max=%.3f | mom @ %.0fth pct"
              %(k,r['mom'],r['rand_med'],r['rand_p90'],r['rand_p95'],r['rand_max'],r['mom_pct']*100))
json.dump(res, open(OUT+"/varb_rt_1_placebo_summary.json","w"), indent=2)
print("\nGROSS selection CAGR gap (mom-rand_med) = %.3f  | mom percentile(gross) = %.0f"
      %(mom_gross['cagr']-res['gross']['cagr']['rand_med'], res['gross']['cagr']['mom_pct']*100))
print("WROTE varb_rt_1_placebo_dist.csv + varb_rt_1_placebo_summary.json  DONE")
