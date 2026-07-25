"""
FACTOR REPLICATION CHECK — NIFTY 100 Low Vol 30 (approximation). SECONDARY, lighter-touch.
Owner: Arjun Rao. Date: 2026-07-24.

score  = 1 / trailing-1yr daily-return vol ; select 30 lowest vol ; weight ~ 1/vol capped 5% ;
rebalance QUARTERLY. Universe = historical Nifty-100 = Nifty50 UNION NiftyNext50 (Yes flags,
monthly 2008-01..2025-10) from 'Historical stock composition of Nifty 50 and Nifty Next 50.xlsx'
(rows are TICKERS matching our panel; genuine PIT membership, not a top-100 proxy).
Membership snapshot = most-recent monthly column at-or-before each rebalance. Same PIT/cost/panel-cap
handling as the Momentum 50 script. Costs on realized turnover only, 1x + 2x stress.
"""
import os, json
os.environ["PYTHONIOENCODING"] = "utf-8"; os.environ["PYTHONUNBUFFERED"] = "1"
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT  = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "results", "FACTOR_REPLICATION_CHECK_20260724")
NAV_F   = os.path.join(ROOT, "datasets", "index_daily", "factor_navs_principal.parquet")
PANEL_F = os.path.join(ROOT, "datasets", "derived", "pit_union_panel_v1", "close_panel_return_v11.parquet")
COMP_F  = os.path.join(ROOT, "Historical stock composition of Nifty 50 and Nifty Next 50.xlsx")
MCAP_F  = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results", "full750_scored.csv")

SERIES="NIFTY 100 Low Vol 30"; PANEL_CAP=pd.Timestamp("2026-01-22"); TOPN=30; WCAP=0.05; LB=252; MIN_HIST=252
SLIP={"Large":0.0010,"Mid":0.0020,"Small":0.0035}
def oneway_cost(t):
    return SLIP.get(t,0.0035)+0.0010+0.0000297+0.000075+0.000001+0.18*(0.0000297+0.000001)
def cap_weights(w,cap):
    w=w/w.sum()
    for _ in range(100):
        over=w>cap
        if not over.any(): break
        ex=(w[over]-cap).sum(); w[over]=cap; room=~over
        if not room.any(): break
        w[room]+=ex*(w[room]/w[room].sum())
    return w/w.sum()

print("Loading official NAV ...",flush=True)
nav=pd.read_parquet(NAV_F); off=nav[nav["series"]==SERIES][["date","nav"]].copy()
off["date"]=pd.to_datetime(off["date"]); off=off.sort_values("date").reset_index(drop=True)
print(f"  {SERIES}: {len(off)} rows {off['date'].min().date()}->{off['date'].max().date()}",flush=True)

print("Loading Nifty-100 membership (union of two sheets) ...",flush=True)
d50=pd.read_excel(COMP_F,sheet_name="Nifty 50").rename(columns={"Unnamed: 0":"tkr"}).set_index("tkr")
dN =pd.read_excel(COMP_F,sheet_name="Nifty Next 50").rename(columns={"Unnamed: 0":"tkr"}).set_index("tkr")
mcols=sorted([c for c in d50.columns if isinstance(c,(pd.Timestamp,)) or hasattr(c,"year")])
def memb_at(rb):
    cands=[c for c in mcols if pd.Timestamp(c)<=rb]
    if not cands: return set()
    c=max(cands, key=lambda x: pd.Timestamp(x))
    s50=set(d50.index[d50[c]=="Yes"]); sN=set(dN.index[dN[c]=="Yes"])
    return {str(x).strip() for x in (s50|sN)}
uni=set()
for c in mcols:
    uni|= set(d50.index[d50[c]=="Yes"])|set(dN.index[dN[c]=="Yes"])
uni={str(x).strip() for x in uni}
print(f"  monthly cols {pd.Timestamp(mcols[0]).date()}->{pd.Timestamp(mcols[-1]).date()}; union tickers {len(uni)}",flush=True)

sc=pd.read_csv(MCAP_F); TIER={r.symbol:str(r.mcap_tercile) for r in sc.itertuples()}

print("Loading price panel ...",flush=True)
pan=pd.read_parquet(PANEL_F,columns=["date","symbol","close"]); pan["date"]=pd.to_datetime(pan["date"])
pan=pan[(pan["symbol"].isin(uni))&(pan["date"]<=PANEL_CAP)]
px=pan.pivot_table(index="date",columns="symbol",values="close",aggfunc="last").sort_index()
px=px[px.index>=pd.Timestamp("2006-06-01")]; rets=px.pct_change()
print(f"  wide px {px.shape[0]}x{px.shape[1]} {px.index.min().date()}->{px.index.max().date()}",flush=True)

# quarterly rebalances from 2009-03 (need 1yr vol after 2008 membership start)
rebals=[]
for y in range(2009,2027):
    for m in (3,6,9,12):
        d=pd.Timestamp(y,m,1)+pd.offsets.MonthEnd(0)
        if off["date"].min()<=d<=px.index.max():
            av=px.index[px.index<=d]
            if len(av): rebals.append(av[-1])
rebals=sorted(set(rebals)); print(f"{len(rebals)} quarterly rebalances {rebals[0].date()}->{rebals[-1].date()}",flush=True)

excl_rows={}; wh={}
for rb in rebals:
    members=memb_at(rb); hist=px.loc[:rb]; elig=[]
    for s in members:
        if s not in px.columns: continue
        col=hist[s].dropna()
        if len(col)<MIN_HIST: continue
        if rb not in px.index or pd.isna(px.loc[rb,s]): continue
        elig.append(s)
    excl_rows[rb]=dict(rebal=rb,n_members=len(members),n_eligible=len(elig))
    if len(elig)<TOPN: wh[rb]=pd.Series(dtype=float); continue
    rows=[]
    for s in elig:
        dr=hist[s].dropna().pct_change().dropna().iloc[-LB:]
        v=dr.std()*np.sqrt(252)
        if v>0 and np.isfinite(v): rows.append((s,v))
    dfm=pd.DataFrame(rows,columns=["symbol","vol"]).sort_values("vol").head(TOPN).copy()
    w=cap_weights((1.0/dfm["vol"]).values,WCAP)
    wh[rb]=pd.Series(w,index=dfm["symbol"].values)

excl=pd.DataFrame(excl_rows.values()); excl["excl_rate"]=1-excl["n_eligible"]/excl["n_members"]
excl["year"]=excl["rebal"].dt.year
print("\nExclusion (Nifty-100 large caps -> expect low):",flush=True)
print(excl.groupby("year").agg(n_members=("n_members","mean"),n_eligible=("n_eligible","mean"),excl_rate=("excl_rate","mean")).round(3).to_string(),flush=True)

def simulate(cm):
    dates=px.index[px.index>=rebals[0]]; nav_v=100.0; out=[(rebals[0],nav_v)]
    cur=wh[rebals[0]].copy()
    nav_v*=(1-sum(abs(cur[s])*oneway_cost(TIER.get(s,"Small")) for s in cur.index)*cm)
    ri=0
    for d in dates[1:]:
        r=rets.loc[d,cur.index].fillna(0.0); nav_v*=(1+float((cur*r).sum()))
        cur=cur*(1+r); cur=cur/cur.sum()
        if ri+1<len(rebals) and d>=rebals[ri+1]:
            ri+=1; nw=wh[rebals[ri]]
            if len(nw)>=TOPN:
                alls=cur.index.union(nw.index); a=cur.reindex(alls).fillna(0); b=nw.reindex(alls).fillna(0)
                dt=(b-a).abs(); nav_v*=(1-sum(dt[s]*oneway_cost(TIER.get(s,"Small")) for s in alls)*cm); cur=nw.copy()
        out.append((d,nav_v))
    s=pd.Series(dict(out)); s.index=pd.to_datetime(s.index); return s.sort_index()
rep1=simulate(1.0); rep2=simulate(2.0)

def metrics(rep,offd,label):
    m=pd.merge(rep.rename("rep").reset_index().rename(columns={"index":"date"}),
               offd.rename(columns={"nav":"off"}),on="date",how="inner").sort_values("date")
    if len(m)<30: return None,None
    m["rep_i"]=m["rep"]/m["rep"].iloc[0]*100; m["off_i"]=m["off"]/m["off"].iloc[0]*100
    mm=m.set_index("date").resample("ME").last().dropna()
    mm["rr"]=mm["rep_i"].pct_change(); mm["ro"]=mm["off_i"].pct_change(); mm=mm.dropna()
    yrs=(m["date"].iloc[-1]-m["date"].iloc[0]).days/365.25
    return dict(label=label,start=str(m["date"].iloc[0].date()),end=str(m["date"].iloc[-1].date()),n_months=len(mm),
        monthly_corr=round(float(mm["rr"].corr(mm["ro"])),4),
        ann_tracking_error=round(float((mm["rr"]-mm["ro"]).std()*np.sqrt(12)),4),
        cagr_rep=round(float((m["rep_i"].iloc[-1]/100)**(1/yrs)-1),4),
        cagr_off=round(float((m["off_i"].iloc[-1]/100)**(1/yrs)-1),4),
        cagr_delta=round(float((m["rep_i"].iloc[-1]/100)**(1/yrs)-(m["off_i"].iloc[-1]/100)**(1/yrs)),4),
        total_ret_rep=round(float(m["rep_i"].iloc[-1]/100-1),4),total_ret_off=round(float(m["off_i"].iloc[-1]/100-1),4),
        total_ret_delta=round(float(m["rep_i"].iloc[-1]/100-m["off_i"].iloc[-1]/100),4)),m
res={}; r1,mfull=metrics(rep1,off,"full_1x"); res["full_1x"]=r1; res["full_2x"],_=metrics(rep2,off,"full_2x")
print("\n===== LOW VOL 30 METRICS =====",flush=True)
for k,v in res.items():
    if v: print(k,"->",{kk:v[kk] for kk in ("start","end","monthly_corr","ann_tracking_error","cagr_rep","cagr_off","cagr_delta","total_ret_delta")},flush=True)

fig,ax=plt.subplots(figsize=(12,6))
ax.plot(mfull["date"],mfull["off_i"],label="Official NIFTY 100 Low Vol 30",lw=1.6,color="#1a1a2e")
ax.plot(mfull["date"],mfull["rep_i"],label="Our replication (approx)",lw=1.4,color="#0b6e4f",alpha=0.85)
ax.set_yscale("log"); ax.legend(loc="upper left"); ax.grid(alpha=0.3,which="both"); ax.set_ylabel("Rebased NAV (log)")
ax.set_title(f"NIFTY 100 Low Vol 30 — replication vs official (rebased 100 @ {res['full_1x']['start']}, log)\n"
    f"monthly corr={res['full_1x']['monthly_corr']}  ann.TE={res['full_1x']['ann_tracking_error']:.1%}  "
    f"CAGR {res['full_1x']['cagr_rep']:.1%} vs {res['full_1x']['cagr_off']:.1%} (Δ{res['full_1x']['cagr_delta']:+.1%})")
plt.tight_layout(); png=os.path.join(OUT,"lowvol30_replication.png"); plt.savefig(png,dpi=110); plt.close()
print("saved",png,flush=True)
with open(os.path.join(OUT,"lowvol30_summary.json"),"w") as f:
    json.dump(dict(series=SERIES,generated="2026-07-24",owner="Arjun Rao",panel_cap=str(PANEL_CAP.date()),
        official_range=[str(off['date'].min().date()),str(off['date'].max().date())],
        methodology="approx: score=1/1yr-vol; top30 lowest; w~1/vol cap5%; quarterly; universe=Nifty50UNIONNext50 PIT",
        metrics=res,exclusion_by_year=excl.groupby("year")["excl_rate"].mean().round(3).to_dict(),
        n_rebalances=len(rebals)),f,indent=2,default=str)
print("saved lowvol30_summary.json",flush=True)
