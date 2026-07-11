"""Rankings + case studies (current / last-2y / COVID) from the engine grids."""
import os, json, math
import numpy as np, pandas as pd
import engine as E

RES=E.RES
def rd(n): return pd.read_csv(os.path.join(RES,n))
H_us=rd("hist_grid_US.csv"); M_us=rd("mc_grid_US.csv")
H_in=rd("hist_grid_INDIA.csv"); M_in=rd("mc_grid_INDIA.csv")
us=pd.read_parquet(os.path.join(RES,"us_monthly.parquet"))
ind=pd.read_parquet(os.path.join(RES,"india_monthly.parquet"))
ind_daily=pd.read_parquet(os.path.join(RES,"india_daily.parquet"))

# ---------- merge MC into hist for a combined view ----------
def enrich(H,M):
    m=M[["struct","tenor","regime_filter","mc_mean","mc_median","mc_p05","mc_winrate","mc_cvar5","mc_entry_cost","mc_atm_iv"]]
    return H.merge(m,on=["struct","tenor","regime_filter"],how="left")
Gus=enrich(H_us,M_us); Gin=enrich(H_in,M_in)

# ---------- HEDGING rankings (frame hedge) ----------
def rank_hedge(G,market):
    h=G[G.frame=="hedge"].copy()
    h["dd_improve"]=h["maxdd"]-h["unhedged_maxdd"]          # + = shallower drawdown
    h["cvar_improve"]=h["cvar5"]-h["unhedged_cvar5"]        # + = better tail
    h["ret_sacrificed"]=h["unhedged_ann"]-h["ann_ret"]      # + = gave up return
    h["tail_eff"]=h["cvar_improve"]/h["avg_cost"].replace(0,np.nan)
    cols=["market","struct","legtype","tenor","regime_filter","ann_ret","vol","sharpe","sortino",
          "maxdd","cvar5","winrate","avg_cost","unhedged_ann","unhedged_maxdd","unhedged_cvar5",
          "dd_improve","cvar_improve","ret_sacrificed","tail_eff","mc_mean","mc_p05"]
    h=h[cols].sort_values(["regime_filter","sortino"],ascending=[True,False])
    h.to_csv(os.path.join(RES,f"ranking_hedge_{market}.csv"),index=False)
    return h

# ---------- DOWNSIDE PLAY rankings (frame play) ----------
def rank_play(G,market):
    p=G[G.frame=="play"].copy()
    cols=["market","struct","legtype","tenor","regime_filter","mean_pnl","median_pnl","ann_ret","vol",
          "sharpe","winrate","worst","best","cvar5","avg_cost","mc_mean","mc_median","mc_p05","mc_winrate","mc_cvar5"]
    p=p[cols].sort_values(["regime_filter","mean_pnl"],ascending=[True,False])
    p.to_csv(os.path.join(RES,f"ranking_play_{market}.csv"),index=False)
    return p

Hh_us=rank_hedge(Gus,"US"); Hh_in=rank_hedge(Gin,"INDIA")
Pp_us=rank_play(Gus,"US");  Pp_in=rank_play(Gin,"INDIA")

def show(df,cols,n=6):
    return df[cols].head(n).round(4).to_string(index=False)

report=[]
def w(s): report.append(s); print(s)

w("="*90)
w("HEDGING — best overlays by Sortino (on a long-index position)")
for mk,h in [("US",Hh_us),("INDIA",Hh_in)]:
    for rg in ["ALL","RICH","FAIR","CHEAP"]:
        sub=h[h.regime_filter==rg]
        w(f"\n[{mk}] regime={rg}  (unhedged ann={sub.unhedged_ann.iloc[0]:.3f} maxdd={sub.unhedged_maxdd.iloc[0]:.3f} cvar5={sub.unhedged_cvar5.iloc[0]:.3f})")
        w(show(sub,["struct","tenor","ann_ret","maxdd","cvar5","sortino","ret_sacrificed","dd_improve","avg_cost"],4))

w("\n"+"="*90)
w("DOWNSIDE PLAYS — best expectancy in RICH (overvalued) regime")
for mk,p in [("US",Pp_us),("INDIA",Pp_in)]:
    sub=p[p.regime_filter=="RICH"]
    w(f"\n[{mk}] RICH regime downside plays (mean_pnl = frac of notional per period):")
    w(show(sub,["struct","tenor","mean_pnl","median_pnl","winrate","worst","best","mc_mean","mc_p05"],8))

# ================= CASE STUDIES =================
def price_struct_on_path(legs,S_entry,S_exit,T,r,q,atm_iv,skew):
    debit,tc=E.structure_entry_cost(legs,S_entry,T,r,q,atm_iv,skew)
    payoff=E.structure_expiry_payoff(legs,S_entry,S_exit)
    return debit,tc,payoff

CASE={}

# ---- COVID: India daily (real depth) ----
d=ind_daily.copy(); d["date"]=pd.to_datetime(d["date"])
entry=d[d.date<="2020-02-19"].iloc[-1]     # pre-crash peak area
trough=d[(d.date>="2020-03-20")&(d.date<="2020-03-26")].sort_values("close").iloc[0]
exp1m=d[d.date<="2020-03-19"].iloc[-1]     # ~1m later (monthly expiry window)
exp3m=d[d.date<="2020-05-19"].iloc[-1]
covid_in=[]
S0=entry.close; ivix0=entry.ivix/100.0
for sname,(frame,lt,legs) in E.STRUCTURES.items():
    for tlab,tm,Sx in [("1m@trough",1,trough.close),("1m@expiry",1,exp1m.close),("3m@expiry",3,exp3m.close)]:
        T=tm/12.0
        deb,tc,pay=price_struct_on_path(legs,S0,Sx,T,0.065,0.012,ivix0,0.50)
        idx_ret=(Sx-S0)/S0
        opt=pay-deb-tc
        covid_in.append(dict(struct=sname,frame=frame,leg=lt,scenario=tlab,S0=round(S0),Sx=round(Sx),
            idx_ret=round(idx_ret,3),entry_cost=round(deb+tc,4),opt_pnl=round(opt,4),
            combined=round(idx_ret+opt,4) if frame=="hedge" else round(opt,4)))
covid_in=pd.DataFrame(covid_in); covid_in.to_csv(os.path.join(RES,"case_covid_INDIA.csv"),index=False)
CASE["covid_india_entry"]=dict(date=str(entry.date.date()),nifty=float(S0),ivix=float(entry.ivix),
    trough_date=str(trough.date.date()),trough=float(trough.close),trough_dd=round((trough.close-S0)/S0,3))

# ---- COVID: US monthly ----
u=us.copy()
ein=u[u.index<="2020-02-28"].iloc[-1]; e1=u[u.index<="2020-03-31"].iloc[-1]; e3=u[u.index<="2020-05-31"].iloc[-1]
S0u=ein["sp500"]; iv0=ein["vix"]/100.0
covid_us=[]
for sname,(frame,lt,legs) in E.STRUCTURES.items():
    for tlab,Sx in [("1m@Mar",e1["sp500"]),("3m@May",e3["sp500"])]:
        T=(1 if "1m" in tlab else 3)/12.0
        deb,tc,pay=price_struct_on_path(legs,S0u,Sx,T,ein["r"],ein["q"],iv0,0.90)
        idx_ret=(Sx-S0u)/S0u; opt=pay-deb-tc
        covid_us.append(dict(struct=sname,frame=frame,scenario=tlab,S0=round(S0u),Sx=round(Sx),
            idx_ret=round(idx_ret,3),entry_cost=round(deb+tc,4),opt_pnl=round(opt,4),
            combined=round(idx_ret+opt,4) if frame=="hedge" else round(opt,4)))
covid_us=pd.DataFrame(covid_us); covid_us.to_csv(os.path.join(RES,"case_covid_US.csv"),index=False)
CASE["covid_us_entry"]=dict(date=str(ein.name.date()),sp500=float(S0u),vix=float(ein["vix"]),
    mar_sp500=float(e1["sp500"]),mar_dd=round((e1["sp500"]-S0u)/S0u,3))

# ---- LAST 2Y rollover (2024-07 -> 2026-07): apply monthly & quarterly on selected structures ----
def rollover_realized(m,price_col,legs,frame,tenor_m,start,end,skew):
    p=m[price_col]; sub=m[(m.index>=start)&(m.index<=end)]
    idxs=[m.index.get_loc(dt) for dt in sub.index]
    i=idxs[0]; rows=[]
    while i+tenor_m < len(m) and m.index[i]<=pd.Timestamp(end):
        S=p.iloc[i]; Sx=p.iloc[i+tenor_m]; T=tenor_m/12.0
        iv=m["vix"].iloc[i]/100.0
        if not np.isfinite(iv) or iv<=0: iv=m["ret"].iloc[max(0,i-12):i].std()*math.sqrt(12)*1.1
        r=m["r"].iloc[i]; q=m["q"].iloc[i] if np.isfinite(m["q"].iloc[i]) else 0.0
        deb,tc=E.structure_entry_cost(legs,S,T,r,q,max(iv,0.05),skew)
        pay=E.structure_expiry_payoff(legs,S,Sx)
        idx_ret=(Sx-S)/S+q*T; opt=pay-deb-tc
        rows.append(dict(dt=str(m.index[i].date()),idx_ret=idx_ret,opt=opt,
                         combined=idx_ret+opt if frame=="hedge" else opt))
        i+=tenor_m
    df=pd.DataFrame(rows)
    return df

last2y={}
picks_hedge={"collar":E.STRUCTURES["H_collar_95_110"][2],"putspread":E.STRUCTURES["H_putspread_95_85"][2],
             "protput95":E.STRUCTURES["H_put_95"][2]}
picks_play={"bearspread":E.STRUCTURES["P_bearspread_95_85"][2],"backspread1x2":E.STRUCTURES["P_backspread_1x2_97_90"][2],
            "longput95":E.STRUCTURES["P_longput_95"][2]}
for mk,m,pc,skew in [("US",us,"sp500",0.90),("INDIA",ind,"nifty",0.50)]:
    rec={}
    for nm,legs in picks_hedge.items():
        df=rollover_realized(m,pc,legs,"hedge",1,"2024-07-01","2026-07-01",skew)
        rec[f"hedge_{nm}_1m"]=dict(cum_combined=float((1+df["combined"]).prod()-1),
            cum_unhedged=float((1+df["idx_ret"]).prod()-1),n=len(df),
            worst_period=float(df["combined"].min()))
    for nm,legs in picks_play.items():
        df=rollover_realized(m,pc,legs,"play",1,"2024-07-01","2026-07-01",skew)
        rec[f"play_{nm}_1m"]=dict(cum_pnl=float(df["combined"].sum()),n=len(df),
            worst=float(df["combined"].min()),best=float(df["combined"].max()))
    last2y[mk]=rec
CASE["last2y"]=last2y

json.dump(CASE,open(os.path.join(RES,"case_studies.json"),"w"),indent=2,default=float)

w("\n"+"="*90); w("CASE STUDIES")
w("\nCOVID India entry: "+json.dumps(CASE["covid_india_entry"]))
w("COVID India — hedges & plays (combined = total incl long-index for hedges; standalone for plays):")
w(covid_in[covid_in.scenario=="1m@trough"][["struct","frame","idx_ret","entry_cost","opt_pnl","combined"]].round(3).to_string(index=False))
w("\nCOVID US entry: "+json.dumps(CASE["covid_us_entry"]))
w(covid_us[covid_us.scenario=="1m@Mar"][["struct","frame","idx_ret","entry_cost","opt_pnl","combined"]].round(3).to_string(index=False))
w("\nLAST 2Y (2024-07..2026-07):")
w(json.dumps(last2y,indent=2,default=lambda x:round(float(x),4)))

open(os.path.join(RES,"SUMMARY.txt"),"w",encoding="utf-8").write("\n".join(report))
print("\nSAVED rankings + case studies to",RES)
