# -*- coding: utf-8 -*-
"""RED-TEAM 3 (Nikhil Bose): beta/alpha (with t-stat) + corr-horizon for MIDSMALL Var-B."""
import sys, json, pickle
import numpy as np, pandas as pd
OUT=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707"
LIB=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/lib"
BOOK=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/STACKED_BOOK_20260711/book_daily_pnl.csv"
sys.path.insert(0, OUT); sys.path.insert(0, LIB)
import midsmall_mom_rotation as M

with open(OUT+"/_raw_results.pkl","rb") as f: R=pickle.load(f)
dd=R["B_1x"][0]
y_all=dd["ret"].rename("varb")
state=dd["state"]
mss=M.mss400.pct_change().rename("mss")
n500=M.n500idx.pct_change().rename("n500")

def ols(y,x):
    d=pd.concat([y,x],axis=1).dropna(); n=len(d)
    yy=d.iloc[:,0].values; xx=d.iloc[:,1].values
    b,a=np.polyfit(xx,yy,1)  # slope,intercept
    e=yy-(a+b*xx); s2=(e@e)/(n-2); Sxx=((xx-xx.mean())**2).sum()
    se_a=np.sqrt(s2*(1/n+xx.mean()**2/Sxx)); t_a=a/se_a
    corr=np.corrcoef(xx,yy)[0,1]
    return dict(n=int(n),beta=float(b),alpha_daily=float(a),alpha_ann=float(a*252),t_alpha=float(t_a),
                corr=float(corr),r2=float(corr**2))

print("=== BETA / ALPHA (Var-B daily returns) ===")
res={}
for lbl,x in [("vs_MSS400",mss),("vs_N500",n500)]:
    res[lbl+"_full"]=ols(y_all,x)
    inv=y_all[state=="EQUITY"]
    res[lbl+"_invested"]=ols(inv,x)
    for scope in ["full","invested"]:
        rr=res[lbl+"_"+scope]
        print("  %-12s %-9s beta=%.3f  alpha_ann=%+.1f%%  t(alpha)=%.2f  corr=%.3f (R2=%.2f)  n=%d"
              %(lbl,scope,rr["beta"],rr["alpha_ann"]*100,rr["t_alpha"],rr["corr"],rr["r2"],rr["n"]))

# ---- CORR-HORIZON vs other book sleeves (2022-2025 book window) ----
bk=pd.read_csv(BOOK,index_col=0,parse_dates=True)
sleeves=["midsmall","breakout","s1f","b1b"]
def ch(dfp,label):
    c=dfp[sleeves].corr()
    print("  %-9s midsmall vs: breakout %.2f  s1f %.2f  b1b %.2f  | max(non-self) %.2f"
          %(label,c.loc["midsmall","breakout"],c.loc["midsmall","s1f"],c.loc["midsmall","b1b"],
            c.loc["midsmall",["breakout","s1f","b1b"]].max()))
    return {k:float(c.loc["midsmall",k]) for k in sleeves}
print("\n=== CORR-HORIZON (book_daily_pnl 2022-2025) — midsmall vs sleeves ===")
corr_h={}
corr_h["daily"]=ch(bk,"daily")
corr_h["monthly"]=ch(bk.resample("ME").sum(),"monthly")
corr_h["quarterly"]=ch(bk.resample("QE").sum(),"quarterly")

json.dump(dict(beta=res,corr_horizon=corr_h),open(OUT+"/varb_rt_3_beta_corr.json","w"),indent=2)
print("\nWROTE varb_rt_3_beta_corr.json  DONE")
