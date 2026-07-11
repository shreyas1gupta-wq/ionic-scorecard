"""
HEDGING & DOWNSIDE-PLAY REGIME STUDY  —  Shreyas_Ionic_AMC / 04_RND_LAB
US (S&P 500, real Shiller CAPE, real VIX 1990+) and India (NIFTY 50, PB/PE, India VIX 2016+).
Valuation regimes 25-50-25. Options Black-Scholes-modeled off VIX/India-VIX + skew (no real chains).
Historical rollover backtest + regime-conditional Monte Carlo. Hedging overlays + downside plays.

METHOD NOTES (honesty):
 - No real option prices exist for this span -> every option is BS-priced at entry using implied vol
   (VIX / India VIX at entry, or realized*mult pre-1990 US) with a put skew term; settled at realized
   intrinsic at expiry. The entry-IV -> realized-intrinsic gap IS the volatility risk premium / hedge cost.
 - US valuation = real Shiller CAPE (10y smoothed E). India has no Shiller PE; primary metric = PRICE/BOOK
   (CAPE-analog: stable through the 2020-21 earnings collapse that corrupts trailing PE); trailing PE shown too.
 - Costs are DRAFT (not user-approved COST_STANDARDS): per-leg = spread_bps of notional + fixed. Gross & net both reported.
"""
import os, json, math, warnings
import numpy as np, pandas as pd
from datetime import datetime
warnings.filterwarnings("ignore")
np.random.seed(20260708)

BASE = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT  = os.path.join(BASE, r"Shreyas_Ionic_AMC\04_RND_LAB\results\HEDGING_ANALYSIS_20260708")
DATA = os.path.join(OUT, "data")
RES  = os.path.join(OUT, "results"); os.makedirs(RES, exist_ok=True)

def log(msg):
    line=f"[{datetime.now():%H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(os.path.join(OUT,"PROGRESS.md"),"a",encoding="utf-8") as f: f.write(line+"\n")

# ------------------------------------------------------------------ Black-Scholes
SQRT2=math.sqrt(2.0)
def _ncdf(x): return 0.5*(1.0+math.erf(x/SQRT2))
def bs_price(S,K,T,r,q,sigma,right):
    if T<=0 or sigma<=0:
        intr = max(S-K,0.0) if right=="call" else max(K-S,0.0)
        return intr
    d1=(math.log(S/K)+(r-q+0.5*sigma*sigma)*T)/(sigma*math.sqrt(T))
    d2=d1-sigma*math.sqrt(T)
    if right=="call": return S*math.exp(-q*T)*_ncdf(d1)-K*math.exp(-r*T)*_ncdf(d2)
    else:             return K*math.exp(-r*T)*_ncdf(-d2)-S*math.exp(-q*T)*_ncdf(-d1)

def iv_for_strike(atm_iv, moneyness, right, skew):
    """moneyness=K/S. Puts below spot get IV bump (equity skew); calls slight."""
    if right=="put":
        return atm_iv + skew*max(0.0, 1.0-moneyness)
    else:  # calls: mild upside skew reduction, floor
        return max(0.05, atm_iv - 0.25*skew*max(0.0, moneyness-1.0))

# ------------------------------------------------------------------ Structures
# leg = (right, qty_signed, moneyness).  frame: 'hedge' (added to +1 long index) or 'play' (standalone)
STRUCTURES = {
 # ---- HEDGING OVERLAYS (frame hedge) ----
 "H_put_ATM":            ("hedge","long_only",[("put",+1,1.00)]),
 "H_put_95":             ("hedge","long_only",[("put",+1,0.95)]),
 "H_put_90":             ("hedge","long_only",[("put",+1,0.90)]),
 "H_putspread_95_85":    ("hedge","long_short",[("put",+1,0.95),("put",-1,0.85)]),
 "H_putspread_90_80":    ("hedge","long_short",[("put",+1,0.90),("put",-1,0.80)]),
 "H_collar_95_105":      ("hedge","long_short",[("put",+1,0.95),("call",-1,1.05)]),
 "H_collar_90_110":      ("hedge","long_short",[("put",+1,0.90),("call",-1,1.10)]),
 "H_collar_95_110":      ("hedge","long_short",[("put",+1,0.95),("call",-1,1.10)]),
 "H_putratio_1x2_95_85": ("hedge","long_short",[("put",+1,0.95),("put",-2,0.85)]),   # buy1 sell2 (cheap, tail risk)
 "H_backspread_1x2_100_90":("hedge","long_short",[("put",-1,1.00),("put",+2,0.90)]), # sell1 buy2 (convex)
 "H_pspread_collar_95_85_105":("hedge","long_short",[("put",+1,0.95),("put",-1,0.85),("call",-1,1.05)]),
 # ---- DOWNSIDE PLAYS (frame play, standalone) ----
 "P_longput_97":         ("play","long_only",[("put",+1,0.97)]),
 "P_longput_95":         ("play","long_only",[("put",+1,0.95)]),
 "P_longput_90":         ("play","long_only",[("put",+1,0.90)]),
 "P_bearspread_97_90":   ("play","long_short",[("put",+1,0.97),("put",-1,0.90)]),
 "P_bearspread_95_85":   ("play","long_short",[("put",+1,0.95),("put",-1,0.85)]),
 "P_backspread_1x2_97_90":("play","long_short",[("put",-1,0.97),("put",+2,0.90)]),   # sell1 buy2 convex, cheap
 "P_backspread_1x3_97_90":("play","long_short",[("put",-1,0.97),("put",+3,0.90)]),   # 1:3
 "P_ratio_2x1_95_85":    ("play","long_short",[("put",+1,0.95),("put",-2,0.85)]),    # buy1 sell2 credit ratio
 "P_ratio_3x1_92_82":    ("play","long_short",[("put",+3,0.92),("put",-1,0.82)]),    # 3:1
 "P_ratio_3x2_95_85":    ("play","long_short",[("put",+3,0.95),("put",-2,0.85)]),    # 3:2
 "P_ratio_3x3_95_85":    ("play","long_short",[("put",+3,0.95),("put",-3,0.85)]),    # 3:3
 "P_riskrev_95_105":     ("play","long_short",[("put",+1,0.95),("call",-1,1.05)]),   # bearish risk reversal
 "P_shortcall_102":      ("play","long_short",[("call",-1,1.02)]),                    # naked short call (undefined risk)
}

TENORS = {"monthly":1,"quarterly":3,"semiannual":6,"annual":12}  # in months
COST_BPS = 8.0      # per-leg spread cost, bps of notional (DRAFT)
COST_FIX = 0.0002   # per-leg fixed, fraction of notional (DRAFT)

def structure_entry_cost(legs, S, T, r, q, atm_iv, skew):
    """Net debit(+)/credit(-) per 1.0 notional (S), plus transaction cost (always a drag)."""
    net=0.0; tc=0.0
    for right,qty,mny in legs:
        K=mny*S
        iv=iv_for_strike(atm_iv,mny,right,skew)
        px=bs_price(S,K,T,r,q,iv,right)
        net += qty*px                       # long qty>0 pays, short qty<0 receives
        tc  += abs(qty)*(COST_BPS/1e4*S + COST_FIX*S)
    return net/S, tc/S                       # as fraction of notional

def structure_expiry_payoff(legs, S_entry, S_exit):
    """Intrinsic payoff per 1.0 notional (fraction of S_entry)."""
    pay=0.0
    for right,qty,mny in legs:
        K=mny*S_entry
        intr = max(S_exit-K,0.0) if right=="call" else max(K-S_exit,0.0)
        pay += qty*intr
    return pay/S_entry

# ------------------------------------------------------------------ Data loaders
def load_us():
    def g(n): return pd.read_parquet(os.path.join(DATA,f"{n}.parquet"))
    cape=g("us_cape"); spx=g("us_sp500"); dy=g("us_divyield"); r10=g("us_10y")
    vix=g("us_vix")[["date","close"]].rename(columns={"close":"vix"})
    # monthly panel keyed to month period
    def mk(df,col):
        d=df.copy(); d["ym"]=d["date"].dt.to_period("M"); return d.groupby("ym")[col].last()
    m=pd.DataFrame({"sp500":mk(spx,"sp500"),"cape":mk(cape,"cape"),
                    "div_yield":mk(dy,"div_yield"),"r10y":mk(r10,"r10y")})
    vixm=vix.copy(); vixm["ym"]=vixm["date"].dt.to_period("M")
    m["vix"]=vixm.groupby("ym")["vix"].mean()
    m=m.dropna(subset=["sp500","cape"]).copy()
    m["r"]=m["r10y"]/100.0; m["q"]=m["div_yield"]/100.0
    m["ret"]=np.log(m["sp500"]).diff()
    m.index=m.index.to_timestamp()
    return m

def load_india():
    allidx=pd.read_parquet(os.path.join(BASE,"datasets/index_daily/nse_official_all_indices.parquet"))
    n=allidx[allidx.index_name=="Nifty 50"].copy()
    n["date"]=pd.to_datetime(n["date"]); n=n.sort_values("date")
    vix=pd.read_parquet(os.path.join(BASE,"datasets/index_daily/india_vix.parquet"))
    vix["date"]=pd.to_datetime(vix["timestamp"]).dt.tz_localize(None)
    vix=vix.sort_values("date")[["date","close"]].rename(columns={"close":"ivix"})
    # daily frame for case studies
    daily=n[["date","close","pe","pb","div_yield"]].merge(vix,on="date",how="left")
    daily["ivix"]=daily["ivix"].ffill()
    # monthly panel
    d=daily.copy(); d["ym"]=d["date"].dt.to_period("M")
    m=d.groupby("ym").agg(nifty=("close","last"),pe=("pe","last"),pb=("pb","last"),
                          div_yield=("div_yield","last"),ivix=("ivix","mean"))
    m=m.dropna(subset=["nifty","pb"]).copy()
    m["r"]=0.065; m["q"]=m["div_yield"]/100.0
    m["vix"]=m["ivix"]; m["ret"]=np.log(m["nifty"]).diff()
    m.index=m.index.to_timestamp()
    return m, daily

# ------------------------------------------------------------------ Regime classification
def classify(m, valcol):
    v=m[valcol]
    q25,q75=v.quantile(0.25),v.quantile(0.75)
    reg=pd.Series(np.where(v<=q25,"CHEAP",np.where(v>=q75,"RICH","FAIR")),index=m.index)
    return reg,q25,q75

# ------------------------------------------------------------------ Descriptive per-regime stats
def regime_stats(m, reg, price_col, ppy=12):
    out=[]
    for rg in ["CHEAP","FAIR","RICH","ALL"]:
        sub = m if rg=="ALL" else m[reg==rg]
        rets=sub["ret"].dropna()
        if len(rets)<3: continue
        # forward horizon stats: 12m fwd log return from months in regime
        fwd12=[]
        p=m[price_col]
        for dt in sub.index:
            i=m.index.get_loc(dt)
            if i+12 < len(m): fwd12.append(np.log(p.iloc[i+12]/p.iloc[i]))
        fwd12=np.array(fwd12)
        out.append(dict(regime=rg,n_months=len(rets),
            mean_ann_ret=rets.mean()*ppy, median_ann_ret=rets.median()*ppy,
            ann_vol=rets.std()*math.sqrt(ppy),
            fwd12m_mean=np.nan if len(fwd12)==0 else fwd12.mean(),
            fwd12m_median=np.nan if len(fwd12)==0 else np.median(fwd12),
            fwd12m_p10=np.nan if len(fwd12)==0 else np.percentile(fwd12,10),
            fwd12m_worst=np.nan if len(fwd12)==0 else fwd12.min(),
            pct_neg_month=(rets<0).mean()))
    return pd.DataFrame(out)

# ------------------------------------------------------------------ Historical rollover backtest
def hist_backtest(m, reg, price_col, struct_name, tenor_m, regime_filter, iv_mult, skew):
    frame,legtype,legs=STRUCTURES[struct_name]
    T=tenor_m/12.0
    idx=list(range(0,len(m)-tenor_m, tenor_m))   # non-overlapping rolls at tenor spacing
    rows=[]
    p=m[price_col].values
    for i in idx:
        dt=m.index[i]
        if regime_filter!="ALL" and reg.iloc[i]!=regime_filter: continue
        S=p[i]; S_exit=p[i+tenor_m]
        atm_iv=(m["vix"].iloc[i]/100.0)
        if not np.isfinite(atm_iv) or atm_iv<=0:
            atm_iv=m["ret"].iloc[max(0,i-12):i].std()*math.sqrt(12)*iv_mult
        atm_iv=max(atm_iv,0.05)
        r=m["r"].iloc[i]; q=m["q"].iloc[i] if np.isfinite(m["q"].iloc[i]) else 0.0
        debit,tc=structure_entry_cost(legs,S,T,r,q,atm_iv,skew)
        payoff=structure_expiry_payoff(legs,S,S_exit)
        idx_ret=(S_exit-S)/S + q*T                # long index total return over period
        opt_pnl=payoff-debit-tc                   # structure P&L (frac of notional)
        combined=(idx_ret+opt_pnl) if frame=="hedge" else opt_pnl
        rows.append(dict(dt=dt,regime=reg.iloc[i],idx_ret=idx_ret,opt_pnl=opt_pnl,
                         entry_cost=debit+tc,payoff=payoff,combined=combined,unhedged=idx_ret))
    if not rows: return None
    df=pd.DataFrame(rows)
    per_year=12/tenor_m
    def ann(series): return series.mean()*per_year
    def curve_maxdd(series):
        eq=(1+series).cumprod(); peak=eq.cummax(); return (eq/peak-1).min()
    c=df["combined"]; u=df["unhedged"]
    res=dict(market=None,struct=struct_name,frame=frame,legtype=legtype,tenor_m=tenor_m,
        regime_filter=regime_filter,n=len(df),
        ann_ret=ann(c), vol=c.std()*math.sqrt(per_year),
        sharpe=(ann(c))/(c.std()*math.sqrt(per_year)+1e-9),
        sortino=(ann(c))/((c[c<0].std()*math.sqrt(per_year))+1e-9),
        maxdd=curve_maxdd(c), worst=c.min(), best=c.max(),
        cvar5=c[c<=c.quantile(0.05)].mean() if len(c)>=20 else c.min(),
        winrate=(c>0).mean(), avg_cost=df["entry_cost"].mean(),
        unhedged_ann=ann(u), unhedged_maxdd=curve_maxdd(u),
        unhedged_vol=u.std()*math.sqrt(per_year), unhedged_cvar5=u[u<=u.quantile(0.05)].mean() if len(u)>=20 else u.min(),
        mean_pnl=c.mean(), median_pnl=c.median())
    return res, df

# ------------------------------------------------------------------ Monte Carlo (regime-conditional bootstrap)
def mc_backtest(m, reg, struct_name, tenor_m, regime_filter, skew, npaths=8000):
    frame,legtype,legs=STRUCTURES[struct_name]
    T=tenor_m/12.0
    pool_mask = (reg==regime_filter) if regime_filter!="ALL" else pd.Series(True,index=m.index)
    monthly_rets=m.loc[pool_mask,"ret"].dropna().values
    if len(monthly_rets)<6: return None
    atm_iv=np.nanmean(m.loc[pool_mask,"vix"].values)/100.0
    if not np.isfinite(atm_iv) or atm_iv<=0: atm_iv=monthly_rets.std()*math.sqrt(12)*1.1
    atm_iv=max(atm_iv,0.05)
    r=np.nanmean(m["r"].values); q=np.nanmean(m["q"].values); q=q if np.isfinite(q) else 0.0
    S=100.0
    debit,tc=structure_entry_cost(legs,S,T,r,q,atm_iv,skew)
    # simulate terminal via block bootstrap of tenor_m consecutive monthly rets from the regime pool
    combos=[]
    for _ in range(npaths):
        draw=np.random.choice(monthly_rets,size=tenor_m,replace=True)
        S_exit=S*math.exp(draw.sum())
        payoff=structure_expiry_payoff(legs,S,S_exit)
        idx_ret=(S_exit-S)/S + q*T
        opt_pnl=payoff-debit-tc
        combined=(idx_ret+opt_pnl) if frame=="hedge" else opt_pnl
        combos.append((combined,idx_ret,opt_pnl))
    a=np.array(combos); c=a[:,0]; u=a[:,1]
    return dict(struct=struct_name,frame=frame,tenor_m=tenor_m,regime_filter=regime_filter,
        mc_mean=c.mean(),mc_median=np.median(c),mc_vol=c.std(),
        mc_p05=np.percentile(c,5),mc_p95=np.percentile(c,95),mc_worst=c.min(),
        mc_winrate=(c>0).mean(),mc_cvar5=c[c<=np.percentile(c,5)].mean(),
        mc_entry_cost=debit+tc, mc_unhedged_mean=u.mean(), mc_unhedged_p05=np.percentile(u,5),
        mc_atm_iv=atm_iv)

# ------------------------------------------------------------------ MAIN
def run_market(name, m, reg, price_col, skew, valcol, ivmult=1.1):
    log(f"=== {name}: {len(m)} months {m.index.min():%Y-%m}->{m.index.max():%Y-%m}; skew={skew} val={valcol}")
    # descriptive
    rs=regime_stats(m,reg,price_col); rs.insert(0,"market",name)
    rs.to_csv(os.path.join(RES,f"regime_stats_{name}.csv"),index=False)
    log(f"{name} regime stats:\n"+rs.to_string(index=False))
    # backtest grid
    hist_rows=[]; mc_rows=[]; detail={}
    for sname in STRUCTURES:
        for tlab,tm in TENORS.items():
            for rf in ["ALL","CHEAP","FAIR","RICH"]:
                hb=hist_backtest(m,reg,price_col,sname,tm,rf,ivmult,skew)
                if hb:
                    res,df=hb; res["market"]=name; res["tenor"]=tlab; hist_rows.append(res)
                mc=mc_backtest(m,reg,sname,tm,rf,skew)
                if mc: mc["market"]=name; mc["tenor"]=tlab; mc_rows.append(mc)
        log(f"  done {sname}")
    H=pd.DataFrame(hist_rows); M=pd.DataFrame(mc_rows)
    H.to_csv(os.path.join(RES,f"hist_grid_{name}.csv"),index=False)
    M.to_csv(os.path.join(RES,f"mc_grid_{name}.csv"),index=False)
    log(f"{name}: hist rows={len(H)} mc rows={len(M)} saved.")
    return rs,H,M

if __name__=="__main__":
    open(os.path.join(OUT,"PROGRESS.md"),"w",encoding="utf-8").write(f"# HEDGING ANALYSIS PROGRESS\nstarted {datetime.now():%Y-%m-%d %H:%M}\n\n")
    log("loading data")
    us=load_us()
    ind,ind_daily=load_india()
    ind_daily.to_parquet(os.path.join(RES,"india_daily.parquet"))
    us.to_parquet(os.path.join(RES,"us_monthly.parquet"))
    ind.to_parquet(os.path.join(RES,"india_monthly.parquet"))
    # regimes
    us_reg,us25,us75=classify(us,"cape")
    ind_reg_pb,i25,i75=classify(ind,"pb")          # PRIMARY India = PB (CAPE-analog)
    ind_reg_pe,ie25,ie75=classify(ind,"pe")        # secondary
    reg_info=dict(us_cape_q25=us25,us_cape_q75=us75,us_cape_now=float(us["cape"].iloc[-1]),
                  us_regime_now=us_reg.iloc[-1],
                  india_pb_q25=i25,india_pb_q75=i75,india_pb_now=float(ind["pb"].iloc[-1]),
                  india_regime_now=ind_reg_pb.iloc[-1],
                  india_pe_q25=ie25,india_pe_q75=ie75,india_pe_now=float(ind["pe"].iloc[-1]),
                  india_pe_regime_now=ind_reg_pe.iloc[-1])
    json.dump({k:(float(v) if isinstance(v,(int,float,np.floating)) else v) for k,v in reg_info.items()},
              open(os.path.join(RES,"regime_info.json"),"w"),indent=2)
    log("regime_info: "+json.dumps({k:(round(v,2) if isinstance(v,(int,float,np.floating)) else v) for k,v in reg_info.items()}))
    # run grids
    run_market("US", us, us_reg, "sp500", skew=0.90, valcol="cape", ivmult=1.10)
    run_market("INDIA", ind, ind_reg_pb, "nifty", skew=0.50, valcol="pb", ivmult=1.10)
    # also India PE-based regime stats (secondary, for the note on PE artifact)
    rs_pe=regime_stats(ind,ind_reg_pe,"nifty"); rs_pe.insert(0,"market","INDIA_PE")
    rs_pe.to_csv(os.path.join(RES,"regime_stats_INDIA_PE.csv"),index=False)
    log("ALL GRIDS DONE")
