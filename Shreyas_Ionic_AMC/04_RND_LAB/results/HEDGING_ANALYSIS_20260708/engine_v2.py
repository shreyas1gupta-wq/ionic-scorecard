"""
V2 additions (bias controls the Principal asked for):
 1. WINSORIZE returns before descriptive stats so single extreme obs (Depression -66% window, COVID)
    don't bias mean/median/vol/min/max. Clip at [2.5, 97.5] pct. Raw tail kept via CVaR (the hedge rationale).
 2. COMPLETE-MARKET analysis on a MEDIAN-PE regime signal (true cross-sectional median trailing PE across
    ~1,100 stocks, PIT), studied on the broad Nifty Total Market index — removes the large-cap/cap-weight bias.
 3. SMALL-CAP-only analysis (Nifty Smallcap 250) — the segment the large-cap indices miss.
Reuses engine.py (BS, structures, backtester, MC). Supersedes v1 for tail/descriptive metrics.
"""
import os, json, math, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
import engine as E
BASE=E.BASE; RES=E.RES; DATA=E.DATA
NSE=os.path.join(BASE,"datasets/index_daily/nse_official_all_indices.parquet")

def winsor(a,lo=0.025,hi=0.975):
    a=np.asarray(a,float); a=a[np.isfinite(a)]
    if len(a)<4: return a
    l,h=np.quantile(a,lo),np.quantile(a,hi)
    return np.clip(a,l,h)

def regime_stats_w(m,reg,price_col,ppy=12):
    out=[]; p=m[price_col]
    for rg in ["CHEAP","FAIR","RICH","ALL"]:
        sub = m if rg=="ALL" else m[reg==rg]
        rets=sub["ret"].dropna().values
        if len(rets)<3: continue
        fwd=[]
        for dt in sub.index:
            i=m.index.get_loc(dt)
            if i+12<len(m): fwd.append(np.log(p.iloc[i+12]/p.iloc[i]))
        fwd=np.array(fwd); rw=winsor(rets); fw=winsor(fwd) if len(fwd) else fwd
        out.append(dict(regime=rg,n_months=len(rets),
            mean_ann_ret_w=rw.mean()*ppy, median_ann_ret=np.median(rets)*ppy,
            ann_vol_w=rw.std()*math.sqrt(ppy),
            fwd12m_mean_w=(fw.mean() if len(fw) else np.nan),
            fwd12m_median=(np.median(fwd) if len(fwd) else np.nan),
            fwd12m_worst_w=(fw.min() if len(fw) else np.nan),   # winsorized worst (=2.5pct clip)
            fwd12m_worst_raw=(fwd.min() if len(fwd) else np.nan),
            fwd12m_best_w=(fw.max() if len(fw) else np.nan),
            pct_neg_month=(rets<0).mean()))
    return pd.DataFrame(out)

def run_grid(m,reg,price_col,skew,seg,ivmult=1.10):
    hist=[]; mc=[]
    for s in E.STRUCTURES:
        for tlab,tm in E.TENORS.items():
            for rf in ["ALL","CHEAP","FAIR","RICH"]:
                hb=E.hist_backtest(m,reg,price_col,s,tm,rf,ivmult,skew)
                if hb:
                    res,df=hb
                    res["market"]=seg; res["tenor"]=tlab
                    res["worst_w"]=float(np.quantile(df["combined"],0.025))
                    res["best_w"]=float(np.quantile(df["combined"],0.975))
                    hist.append(res)
                m2=E.mc_backtest(m,reg,s,tm,rf,skew)
                if m2: m2["market"]=seg; m2["tenor"]=tlab; mc.append(m2)
    H=pd.DataFrame(hist); M=pd.DataFrame(mc)
    H.to_csv(os.path.join(RES,f"hist_grid_{seg}.csv"),index=False)
    M.to_csv(os.path.join(RES,f"mc_grid_{seg}.csv"),index=False)
    # rankings
    h=H[H.frame=="hedge"].copy()
    h["dd_improve"]=h["maxdd"]-h["unhedged_maxdd"]; h["ret_sacrificed"]=h["unhedged_ann"]-h["ann_ret"]
    h.sort_values(["regime_filter","sortino"],ascending=[True,False]).to_csv(os.path.join(RES,f"ranking_hedge_{seg}.csv"),index=False)
    p=H[H.frame=="play"].copy()
    p.sort_values(["regime_filter","mean_pnl"],ascending=[True,False]).to_csv(os.path.join(RES,f"ranking_play_{seg}.csv"),index=False)
    return H,M

def idx_monthly(name,vix_series,rf=0.065,skewnote=""):
    a=pd.read_parquet(NSE); d=a[a.index_name==name].copy()
    d["date"]=pd.to_datetime(d["date"]); d=d.sort_values("date")
    d["ym"]=d["date"].dt.to_period("M")
    m=d.groupby("ym").agg(price=("close","last"),pe=("pe","last"),pb=("pb","last"),
                          div_yield=("div_yield","last")).dropna(subset=["price"])
    m["ym_ts"]=m.index.to_timestamp(); m=m.set_index("ym_ts")
    m["vix"]=vix_series.reindex(m.index).ffill()
    m["r"]=rf; m["q"]=(m["div_yield"]/100.0).fillna(0.0); m["ret"]=np.log(m["price"]).diff()
    return m

if __name__=="__main__":
    E.log("V2: winsorize + complete-market-median-PE + small-cap")
    # India VIX monthly (large-cap implied vol)
    vix=pd.read_parquet(os.path.join(BASE,"datasets/index_daily/india_vix.parquet"))
    vix["date"]=pd.to_datetime(vix["timestamp"]).dt.tz_localize(None)
    vixm=vix.set_index("date")["close"].resample("ME").mean()
    vixm.index=vixm.index.to_period("M").to_timestamp()

    # ---- winsorized regime stats for the v1 segments ----
    us=E.load_us(); us_reg,_,_=E.classify(us,"cape")
    ind,_=E.load_india(); ind_reg,_,_=E.classify(ind,"pb")
    regime_stats_w(us,us_reg,"sp500").assign(market="US").to_csv(os.path.join(RES,"regime_stats_wins_US.csv"),index=False)
    regime_stats_w(ind,ind_reg,"nifty").assign(market="INDIA_LARGE").to_csv(os.path.join(RES,"regime_stats_wins_INDIA.csv"),index=False)

    # ---- COMPLETE-MARKET (median-PE regime, broad Nifty Total Market) ----
    medpe=pd.read_parquet(os.path.join(DATA,"india_market_median_pe.parquet"))
    medpe.index=pd.to_datetime(medpe.index).to_period("M").to_timestamp()
    broad=idx_monthly("Nifty 500",vixm)   # broadest FULL-history index (Total Market only launched ~2021)
    broad["medpe"]=medpe["median_pe"].reindex(broad.index)
    broad=broad.dropna(subset=["medpe","price"]).copy()
    broad["ret"]=np.log(broad["price"]).diff()
    b_reg,b25,b75=E.classify(broad,"medpe")
    E.log(f"BROAD median-PE q25={b25:.1f} q75={b75:.1f} now={broad['medpe'].iloc[-1]:.1f} regime_now={b_reg.iloc[-1]} n={len(broad)}")
    regime_stats_w(broad,b_reg,"price").assign(market="INDIA_BROAD_MEDIANPE").to_csv(os.path.join(RES,"regime_stats_wins_INDIA_BROAD.csv"),index=False)
    run_grid(broad,b_reg,"price",skew=0.60,seg="INDIA_BROAD")

    # ---- SMALL-CAP only (Nifty Smallcap 250) ----
    # small-cap implied vol proxy: India VIX * 1.4 (small-caps realise ~1.4x large-cap vol); steeper skew
    sc=idx_monthly("Nifty Smallcap 250",vixm*1.4)
    sc=sc.dropna(subset=["price","pe"]).copy(); sc["ret"]=np.log(sc["price"]).diff()
    sc_reg,s25,s75=E.classify(sc,"pe")
    E.log(f"SMALLCAP PE q25={s25:.1f} q75={s75:.1f} now={sc['pe'].iloc[-1]:.1f} regime_now={sc_reg.iloc[-1]} n={len(sc)}")
    regime_stats_w(sc,sc_reg,"price").assign(market="INDIA_SMALLCAP").to_csv(os.path.join(RES,"regime_stats_wins_INDIA_SMALLCAP.csv"),index=False)
    run_grid(sc,sc_reg,"price",skew=0.70,seg="INDIA_SMALLCAP")

    # ---- large-cap-bias comparison table ----
    def idxpe(nm):
        a=pd.read_parquet(NSE); d=a[a.index_name==nm].copy(); d["date"]=pd.to_datetime(d["date"])
        s=d.set_index("date")["pe"].resample("ME").last(); s.index=s.index.to_period("M").to_timestamp(); return s
    cmp=pd.DataFrame({"median_stocklevel":medpe["median_pe"],
        "nifty50_capwt":idxpe("Nifty 50"),"nifty500_capwt":idxpe("Nifty 500"),
        "totalmkt_capwt":idxpe("Nifty Total Market"),"smallcap250":idxpe("Nifty Smallcap 250"),
        "microcap250":idxpe("Nifty Microcap 250")})
    cmp.to_csv(os.path.join(RES,"valuation_breadth_compare.csv"))
    info={"broad_medpe_q25":float(b25),"broad_medpe_q75":float(b75),"broad_medpe_now":float(broad['medpe'].iloc[-1]),
          "broad_regime_now":b_reg.iloc[-1],"smallcap_pe_q25":float(s25),"smallcap_pe_q75":float(s75),
          "smallcap_pe_now":float(sc['pe'].iloc[-1]),"smallcap_regime_now":sc_reg.iloc[-1],
          "median_pe_latest":float(medpe['median_pe'].iloc[-1]),"median_pe_date":str(medpe.index[-1].date())}
    json.dump(info,open(os.path.join(RES,"regime_info_v2.json"),"w"),indent=2)
    E.log("V2 info: "+json.dumps(info))
    E.log("V2 DONE")
