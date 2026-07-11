"""
V3 (Principal directives 2026-07-08):
 1. MOMENTUM SUB-REGIMES within each valuation regime:
      CHEAP_FALL  = cheap & 12m return < 0  (falling knife)
      CHEAP_RECOV = cheap & (6m or 12m return > 0)  (fall is over, turning up)
      FAIR
      RICH_CALM   = rich, not extended
      RICH_EXT    = rich & (6m return in top decile  OR  monthly RSI14 >= 70)  (extended/overbought)
 2. NET-HEDGE-POSITIVE CONSTRAINT (hard): a hedge/play is NEVER net-short protection.
      allowed iff net_put_qty >= 0  (hedges: short call ok = covered by long index;
      plays: also require net_call_qty >= 0 -> no naked short anything). Bans sell-2-fund-1 ratios.
 3. PE checks retained (regime signals = CAPE / PE / median-PE / smallcap-PE).
Owner: Kabir Anand (E-028). Reuses engine.py BS/backtester/MC.
"""
import os, json, math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import engine as E
from engine_v2 import idx_monthly, regime_stats_w
BASE=E.BASE; RES=E.RES; DATA=E.DATA

# ---- net-hedge-positive structure filter ----
def net_qty(legs):
    npq=sum(q for r,q,m in legs if r=="put"); ncq=sum(q for r,q,m in legs if r=="call"); return npq,ncq
ALLOWED={}
for name,(frame,lt,legs) in E.STRUCTURES.items():
    npq,ncq=net_qty(legs)
    if frame=="hedge" and npq>=0:               # short call covered by long index
        ALLOWED[name]=(frame,lt,legs)
    elif frame=="play" and npq>=0 and ncq>=0:   # no naked short anything
        ALLOWED[name]=(frame,lt,legs)
BANNED=[n for n in E.STRUCTURES if n not in ALLOWED]

# ---- momentum helpers ----
def rsi(series,n=14):
    d=series.diff(); up=d.clip(lower=0); dn=-d.clip(upper=0)
    ru=up.ewm(alpha=1/n,adjust=False).mean(); rd=dn.ewm(alpha=1/n,adjust=False).mean()
    return 100-100/(1+ru/(rd+1e-12))

def sub_regime(m,valreg,price_col):
    p=m[price_col]
    r3=np.log(p/p.shift(3)); r6=np.log(p/p.shift(6)); r12=np.log(p/p.shift(12))
    rs=rsi(p,14)
    ext_thr=r6.quantile(0.90)
    out=[]
    for dt in m.index:
        vr=valreg.loc[dt]; i=m.index.get_loc(dt)
        r6v=r6.iloc[i]; r12v=r12.iloc[i]; rsv=rs.iloc[i]
        if vr=="CHEAP":
            lab="CHEAP_FALL" if (pd.notna(r12v) and r12v<0) else "CHEAP_RECOV"
        elif vr=="RICH":
            extended = (pd.notna(r6v) and r6v>=ext_thr) or (pd.notna(rsv) and rsv>=70)
            lab="RICH_EXT" if extended else "RICH_CALM"
        else:
            lab="FAIR"
        out.append(lab)
    return pd.Series(out,index=m.index)

SUBS=["CHEAP_FALL","CHEAP_RECOV","FAIR","RICH_CALM","RICH_EXT"]

def run_seg(m,valreg,price_col,skew,seg,ivmult=1.10):
    sub=sub_regime(m,valreg,price_col)
    # descriptive per sub-regime (winsorized), reuse regime_stats_w with sub as the 'regime'
    ds=regime_stats_w(m,sub,price_col)
    # regime_stats_w iterates its own fixed labels; instead compute inline for SUBS:
    rows=[]; p=m[price_col]
    for rg in SUBS+["ALL"]:
        s=m if rg=="ALL" else m[sub==rg]
        rr=s["ret"].dropna().values
        if len(rr)<3: continue
        fwd=[]
        for dt in s.index:
            i=m.index.get_loc(dt)
            if i+12<len(m): fwd.append(np.log(p.iloc[i+12]/p.iloc[i]))
        fwd=np.array(fwd)
        def wz(a,lo=.025,hi=.975):
            a=a[np.isfinite(a)];
            return np.clip(a,np.quantile(a,lo),np.quantile(a,hi)) if len(a)>=4 else a
        rw=wz(rr); fw=wz(fwd) if len(fwd) else fwd
        rows.append(dict(subregime=rg,n=len(rr),median_ann_ret=np.median(rr)*12,
            ann_vol_w=rw.std()*math.sqrt(12),fwd12m_mean_w=(fw.mean() if len(fw) else np.nan),
            fwd12m_worst_w=(fw.min() if len(fw) else np.nan),pct_neg=(rr<0).mean()))
    pd.DataFrame(rows).assign(market=seg).to_csv(os.path.join(RES,f"subregime_stats_{seg}.csv"),index=False)
    # grids over ALLOWED structures x tenors x sub-regimes
    hist=[]
    for s in ALLOWED:
        for tlab,tm in E.TENORS.items():
            for rf in SUBS:
                hb=E.hist_backtest(m,sub,price_col,s,tm,rf,ivmult,skew)
                if hb:
                    res,df=hb; res["market"]=seg; res["tenor"]=tlab
                    res["worst_w"]=float(np.quantile(df["combined"],0.025))
                    res["cvar_improve"]=res["cvar5"]-res["unhedged_cvar5"]
                    res["dd_improve"]=res["maxdd"]-res["unhedged_maxdd"]
                    res["ret_sacrificed"]=res["unhedged_ann"]-res["ann_ret"]
                    hist.append(res)
    H=pd.DataFrame(hist); H.to_csv(os.path.join(RES,f"hist_grid_v3_{seg}.csv"),index=False)
    # current sub-regime
    cur=sub.iloc[-1]
    return H,cur,sub

def recommend(H,seg):
    """Best HEDGE per sub-regime: among cells that don't worsen the tail (dd_improve>=0),
       maximise CVaR improvement per unit cost; tie-break higher Sortino; require n>=6."""
    h=H[(H.frame=="hedge")&(H.n>=6)&(H.dd_improve>=-1e-9)].copy()
    h["eff"]=h["cvar_improve"]/(h["avg_cost"].abs()+1e-4)
    recs=[]
    for rg in SUBS:
        s=h[h.regime_filter==rg]
        if s.empty: continue
        best=s.sort_values(["cvar_improve","sortino"],ascending=False).iloc[0]
        recs.append(dict(subregime=rg,best_hedge=best["struct"],tenor=best["tenor"],n=int(best["n"]),
            ann_ret=round(best["ann_ret"],3),maxdd=round(best["maxdd"],3),unhedged_maxdd=round(best["unhedged_maxdd"],3),
            cvar5=round(best["cvar5"],3),cvar_improve=round(best["cvar_improve"],3),
            cost=round(best["avg_cost"],4),sortino=round(best["sortino"],1)))
    # best long-convex PLAY per sub-regime (for RICH_EXT especially)
    pl=H[(H.frame=="play")&(H.n>=6)].copy()
    prc=[]
    for rg in SUBS:
        s=pl[pl.regime_filter==rg]
        if s.empty: continue
        b=s.sort_values("mean_pnl",ascending=False).iloc[0]
        prc.append(dict(subregime=rg,best_play=b["struct"],tenor=b["tenor"],n=int(b["n"]),
            mean_pnl=round(b["mean_pnl"],4),winrate=round(b["winrate"],2),worst_w=round(b["worst_w"],3)))
    pd.DataFrame(recs).assign(market=seg).to_csv(os.path.join(RES,f"subregime_hedge_recs_{seg}.csv"),index=False)
    pd.DataFrame(prc).assign(market=seg).to_csv(os.path.join(RES,f"subregime_play_recs_{seg}.csv"),index=False)
    return pd.DataFrame(recs),pd.DataFrame(prc)

if __name__=="__main__":
    E.log("V3: momentum sub-regimes + net-hedge-positive constraint (owner Kabir E-028)")
    E.log(f"ALLOWED structures ({len(ALLOWED)}): {list(ALLOWED)}")
    E.log(f"BANNED by net-hedge-positive rule ({len(BANNED)}): {BANNED}")
    # load segments
    us=E.load_us(); us_vr,_,_=E.classify(us,"cape")
    ind,_=E.load_india(); ind_vr,_,_=E.classify(ind,"pb")
    vix=pd.read_parquet(os.path.join(BASE,"datasets/index_daily/india_vix.parquet"))
    vix["date"]=pd.to_datetime(vix["timestamp"]).dt.tz_localize(None)
    vixm=vix.set_index("date")["close"].resample("ME").mean(); vixm.index=vixm.index.to_period("M").to_timestamp()
    medpe=pd.read_parquet(os.path.join(DATA,"india_market_median_pe.parquet")); medpe.index=pd.to_datetime(medpe.index).to_period("M").to_timestamp()
    broad=idx_monthly("Nifty 500",vixm); broad["medpe"]=medpe["median_pe"].reindex(broad.index)
    broad=broad.dropna(subset=["medpe","price"]); broad["ret"]=np.log(broad["price"]).diff(); broad_vr,_,_=E.classify(broad,"medpe")
    sc=idx_monthly("Nifty Smallcap 250",vixm*1.4); sc=sc.dropna(subset=["price","pe"]); sc["ret"]=np.log(sc["price"]).diff(); sc_vr,_,_=E.classify(sc,"pe")

    segs={"US":(us,us_vr,"sp500",0.90),"INDIA_LARGE":(ind,ind_vr,"nifty",0.50),
          "INDIA_BROAD":(broad,broad_vr,"price",0.60),"INDIA_SMALLCAP":(sc,sc_vr,"price",0.70)}
    cur_all={}
    for seg,(m,vr,pc,sk) in segs.items():
        H,cur,sub=run_seg(m,vr,pc,sk,seg)
        rh,rp=recommend(H,seg)
        cur_all[seg]=cur
        E.log(f"[{seg}] current sub-regime = {cur}; hedge recs:\n"+rh.to_string(index=False))
    json.dump(cur_all,open(os.path.join(RES,"current_subregime.json"),"w"),indent=2)
    E.log("current sub-regimes: "+json.dumps(cur_all))
    E.log("V3 DONE")
