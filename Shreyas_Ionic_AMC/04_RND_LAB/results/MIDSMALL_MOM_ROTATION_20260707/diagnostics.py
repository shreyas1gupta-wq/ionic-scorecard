# -*- coding: utf-8 -*-
import sys, pickle, numpy as np, pandas as pd
OUT=r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500/Shreyas_Ionic_AMC/04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707"
sys.path.insert(0,OUT)
import midsmall_mom_rotation as M
with open(OUT+"/_raw_results.pkl","rb") as f: R=pickle.load(f)
first=R["A_1x"][0].index[0]; last=R["A_1x"][0].index[-1]
mss=M.mss400[(M.mss400.index>=first)&(M.mss400.index<=last)].pct_change()
n500=M.n500idx[(M.n500idx.index>=first)&(M.n500idx.index<=last)].pct_change()

for tag in ["A_1x","B_1x"]:
    dd,td,rb,meta=R[tag]
    r=dd["ret"]
    # regime transitions
    st=dd["state"]; trans=int((st!=st.shift()).sum()-1)
    exits=int(((st.shift()=="EQUITY")&(st!="EQUITY")).sum())
    reentries=int(((st.shift()!="EQUITY")&(st=="EQUITY")&(st.shift().notna())).sum())
    # beta/alpha vs MSS400 and N500 (full-period OLS on daily)
    def ab(bench):
        x=pd.concat([r.rename("s"),bench.rename("b")],axis=1).dropna()
        b=np.polyfit(x["b"],x["s"],1); beta=b[0]; alpha_d=b[1]
        return beta, (1+alpha_d)**252-1
    bm,am=ab(mss); bn,an=ab(n500)
    # equity-days-only return vs MSS400 same days (selection when invested)
    inq=st=="EQUITY"
    eq_r=r[inq]; mss_same=mss.reindex(r.index)[inq]
    sel_ann=(1+eq_r).prod()**(252/len(eq_r))-1
    mss_when_in=(1+mss_same.fillna(0)).prod()**(252/len(eq_r))-1
    # P&L concentration (round-trip trades, rupee-weighted by entry notional*ret proxy=ret)
    tv=td[td["still_open"]==0].copy()
    tv["pnl_proxy"]=tv["ret"]  # per-trade return; equal-weight proxy for concentration
    bysym=tv.groupby("sym")["pnl_proxy"].sum()
    top1=bysym.abs().max()/ (bysym.abs().sum()+1e-9)
    top5=tv["ret"].nlargest(5).sum(); tot=tv["ret"].sum()
    # max DD date
    eq=(1+r).cumprod(); ddser=eq/eq.cummax()-1; dd_date=ddser.idxmin()
    print(f"\n===== {tag} =====")
    print(f"regime: transitions={trans} equity_exits={exits} reentries={reentries} | time_eq={ (st=='EQUITY').mean()*100:.0f}%")
    print(f"beta vs MSS400={bm:.2f} ann_alpha={am*100:.1f}%   | beta vs N500={bn:.2f} ann_alpha={an*100:.1f}%")
    print(f"when-invested strat CAGR={sel_ann*100:.1f}% vs MSS400-same-days CAGR={mss_when_in*100:.1f}% (selection gap={ (sel_ann-mss_when_in)*100:.1f}pp)")
    print(f"round-trip trades={len(tv)} open_at_end={int(td['still_open'].sum())} | top1-name |P&L| share={top1*100:.1f}% | sum_ret={tot:.2f} top5_ret={top5:.2f} (top5/tot={top5/ (tot+1e-9)*100:.0f}%)")
    print(f"maxDD={ddser.min()*100:.1f}% on {dd_date.date()} | avg trade ret={tv['ret'].mean()*100:.2f}% win={ (tv['ret']>0).mean()*100:.0f}% n_names={tv['sym'].nunique()}")
    print(f"best trade={tv['ret'].max()*100:.0f}% ({tv.loc[tv['ret'].idxmax(),'sym']}) worst={tv['ret'].min()*100:.0f}% ({tv.loc[tv['ret'].idxmin(),'sym']})")
