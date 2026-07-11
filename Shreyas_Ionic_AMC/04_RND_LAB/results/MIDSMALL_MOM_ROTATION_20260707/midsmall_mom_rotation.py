# -*- coding: utf-8 -*-
"""FROZEN backtest: MidSmall Momentum + Smallcap100/200EMA regime + gold/cash rotation.
Owner: Arjun Rao (Head of Quant). Date 2026-07-07. Firm Shreyas_Ionic_AMC."""
from __future__ import annotations
import sys, os, json
import numpy as np, pandas as pd

BASE = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
LIB  = BASE + "/Shreyas_Ionic_AMC/04_RND_LAB/lib"
OUT  = BASE + "/Shreyas_Ionic_AMC/04_RND_LAB/results/MIDSMALL_MOM_ROTATION_20260707"
sys.path.insert(0, LIB)
import guards as G
import execution_realism as X

N_TOP=15; W3,W6=0.4,0.6; L3,L6=63,126; VOLW=126; ADTVW=126
REBAL=10; REGIME=5; EMA_SPAN=200; REENTRY=3; CASH_RATE=0.0625
START=pd.Timestamp("2017-01-01"); MID_ADTV_RANK=150
SLIP_MID,SLIP_SMALL=20.0,35.0; BOOK0=1.0e7; CLIP=0.60

mem500=pd.read_excel(BASE+"/NIFTY500_TICKER_2005_2025_Final.xlsx")
mem200=pd.read_excel(BASE+"/NIFTY200_TICKER_2005_2025.xlsx")
univ_tickers=set(mem500["Ticker"].unique())|set(mem200["Ticker"].unique())

pp=pd.read_parquet(BASE+"/datasets/derived/pit_union_panel_v1/close_panel_price.parquet",columns=["date","symbol","close"])
pp["date"]=pd.to_datetime(pp["date"])
pp=pp[(pp["date"]>=pd.Timestamp("2015-06-01"))&(pp["symbol"].isin(univ_tickers))]
close=pp.pivot_table(index="date",columns="symbol",values="close").sort_index()
cal=close.index; CALN=len(cal); END=cal.max()
print("close panel:",cal.min().date(),"->",END.date(),"| symbols",close.shape[1])

hf=pd.read_parquet(BASE+"/swing_momentum/data/hf_stock_minute/day/train-00000.parquet",columns=["symbol","timestamp","open","high","low","close","volume"])
hf=G.fix_ist_dates(hf); hf["date"]=pd.to_datetime(hf["date"])
hf=hf[(hf["date"]>=pd.Timestamp("2015-06-01"))&(hf["symbol"].isin(univ_tickers))]
def wide(col): return hf.pivot_table(index="date",columns="symbol",values=col).reindex(cal)
h_open,h_high,h_low,h_close,h_vol=wide("open"),wide("high"),wide("low"),wide("close"),wide("volume")
h_prevclose=h_close.shift(1); h_medvol20=h_vol.rolling(20,min_periods=10).median()

ret3=close/close.shift(L3)-1.0
ret6=close/close.shift(L6)-1.0
dret=close.pct_change().clip(-CLIP,CLIP)
n_clipped=int((close.pct_change().abs()>CLIP).sum().sum())
vol6=close.pct_change().rolling(VOLW,min_periods=90).std()
score=(W3*ret3+W6*ret6)/vol6
adtv=(close*h_vol).rolling(ADTVW,min_periods=60).mean()

idxall=pd.read_parquet(BASE+"/datasets/index_daily/nse_official_all_indices.parquet")
idxall["date"]=pd.to_datetime(idxall["date"]).dt.tz_localize(None)
def idx_series(name_lower):
    s=idxall[idxall["index_name"].str.lower()==name_lower].sort_values("date")
    return s.set_index("date")["close"]
sc100=idx_series("nifty smallcap 100")
sc100=sc100[~sc100.index.duplicated(keep="last")].reindex(cal).ffill()
ema200=sc100.ewm(span=EMA_SPAN,min_periods=120).mean()
mss400=idx_series("nifty midsmallcap 400").reindex(cal).ffill()

def parquet_close_ist(path):
    d=pd.read_parquet(BASE+path)
    ts=pd.to_datetime(d["timestamp"],utc=True).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    return pd.Series(d["close"].values,index=ts)
n500idx=parquet_close_ist("/datasets/index_daily/nifty500.parquet").reindex(cal).ffill()
gold=parquet_close_ist("/datasets/etf_gold_silver/goldbees_daily.parquet")
gold=gold[~gold.index.duplicated(keep="last")].reindex(cal)
gold3m=gold/gold.shift(L3)-1.0
goldret=gold.pct_change().clip(-CLIP,CLIP)
print("SC100:",sc100.dropna().index.min().date(),"->",sc100.dropna().index.max().date(),"| EMA from ~",ema200.dropna().index.min().date())
print("GOLDBEES from",gold.dropna().index.min().date())

def snap_map(mem):
    mem=mem.copy(); mem["snap"]=pd.to_datetime(mem["Month-Year"],format="%b%Y")
    d={s:set(g["Ticker"]) for s,g in mem.groupby("snap")}
    return d,np.array(sorted(d.keys()))
m500,s500=snap_map(mem500); m200,s200=snap_map(mem200)
def members_asof(d,mmap,snaps):
    idx=np.searchsorted(snaps,np.datetime64(d),side="right")-1
    return set() if idx<0 else mmap[snaps[idx]]

def cost_oneway(notional,slip_bps,side,cost_mult=1.0):
    notional=abs(float(notional))
    if notional<=0: return 0.0
    brok=20.0; exch=notional*0.0000297; sebi=notional*0.000001
    stt=notional*0.001; stamp=notional*0.00015 if side=="buy" else 0.0
    slip=notional*(slip_bps/10000.0); gst=0.18*(brok+exch+sebi)
    return cost_mult*(brok+exch+sebi+stt+stamp+slip+gst)

def eq_fill(sym,i,tier):
    base=SLIP_MID if tier=="mid" else SLIP_SMALL
    try:
        ci=h_open.columns.get_loc(sym)
        o=h_open.iat[i,ci]; h=h_high.iat[i,ci]; l=h_low.iat[i,ci]; c=h_close.iat[i,ci]
        pc=h_prevclose.iat[i,ci]; v=h_vol.iat[i,ci]; mv=h_medvol20.iat[i,ci]
    except KeyError:
        return False,float("inf"),"not_in_HF"
    return X.fill_check(o,h,l,c,pc,v,mv,base)

def run_backtest(universe_mode="A",extra_lag=0,cash_rate=CASH_RATE,cost_mult=1.0,reverse=False,tag=""):
    i0=int(np.searchsorted(cal.values,np.datetime64(START),side="left"))
    while i0<CALN and pd.isna(ema200.iloc[i0-1]): i0+=1
    cols=list(close.columns)
    score_np=score.values; ret6_np=ret6.values; adtv_np=adtv.values; dret_np=dret.values; close_np=close.values
    col_ix={c:k for k,c in enumerate(cols)}
    sc=sc100.values; em=ema200.values; g3=gold3m.values; gr=goldret.values

    def pick_basket(i_dec):
        d=cal[i_dec]; u=members_asof(d,m500,s500)
        if universe_mode=="A": u=u-members_asof(d,m200,s200)
        srow=score_np[i_dec]; r6row=ret6_np[i_dec]; arow=adtv_np[i_dec]
        cand=[]
        for s in u:
            k=col_ix.get(s)
            if k is None: continue
            sv=srow[k]
            if not np.isfinite(sv) or not np.isfinite(r6row[k]): continue
            cand.append((s,sv,arow[k] if np.isfinite(arow[k]) else -1.0))
        if not cand: return [],{}
        cand_adtv=sorted(cand,key=lambda t:t[2],reverse=True)
        tier={}
        for rank,(s,_,_) in enumerate(cand_adtv): tier[s]="mid" if rank<MID_ADTV_RANK else "small"
        cand.sort(key=lambda t:t[1],reverse=not reverse)
        return [s for s,_,_ in cand[:N_TOP]],tier

    eq_pos={}; entry={}; gold_val=0.0; cash_val=BOOK0
    state="INIT"; substate=None; consec=0
    daily=[]; trades=[]; rebal_bounds=[]
    turnover_notional=0.0; fills_attempted=0; fills_ok=0
    cashd=(1.0+cash_rate)**(1/252)-1.0; tier_now={}
    def cclose(sym,i): return close_np[i,col_ix[sym]]

    def close_all_equity(i,why):
        nonlocal cash_val,turnover_notional
        for s in list(eq_pos.keys()):
            v=eq_pos[s]; t=tier_now.get(s,"small")
            ok,slip,reason=eq_fill(s,i,t)
            if not ok: continue
            cash_val+=v; cash_val-=cost_oneway(v,slip,"sell",cost_mult); turnover_notional+=v
            ec=cclose(s,i); e0d,e0i=entry.get(s,(cal[i],i))
            ep=cclose(s,e0i) if np.isfinite(cclose(s,e0i)) else ec
            trades.append(dict(sym=s,universe=universe_mode,entry_date=str(e0d.date()),exit_date=str(cal[i].date()),entry_close=float(ep),exit_close=float(ec),ret=float(ec/ep-1.0) if ep>0 else 0.0,tier=t,reason=why,still_open=0))
            del eq_pos[s]; entry.pop(s,None)

    def deploy_equity(i,picks,tiers):
        nonlocal cash_val,turnover_notional,fills_attempted,fills_ok
        sleeve=sum(eq_pos.values())+max(cash_val,0.0); tgt_each=sleeve/N_TOP; pickset=set(picks)
        for s in list(eq_pos.keys()):
            if s in pickset: continue
            v=eq_pos[s]; t=tier_now.get(s,"small")
            ok,slip,reason=eq_fill(s,i,t)
            if not ok: continue
            cash_val+=v; cash_val-=cost_oneway(v,slip,"sell",cost_mult); turnover_notional+=v
            ec=cclose(s,i); e0d,e0i=entry.get(s,(cal[i],i))
            ep=cclose(s,e0i) if np.isfinite(cclose(s,e0i)) else ec
            trades.append(dict(sym=s,universe=universe_mode,entry_date=str(e0d.date()),exit_date=str(cal[i].date()),entry_close=float(ep),exit_close=float(ec),ret=float(ec/ep-1.0) if ep>0 else 0.0,tier=t,reason="rebal_out",still_open=0))
            del eq_pos[s]; entry.pop(s,None)
        for s in picks:
            t=tiers.get(s,"small"); tier_now[s]=t
            cur=eq_pos.get(s,0.0); diff=tgt_each-cur
            if abs(diff)<1.0: eq_pos[s]=cur; continue
            fills_attempted+=1
            ok,slip,reason=eq_fill(s,i,t)
            if not ok: eq_pos[s]=cur; continue
            fills_ok+=1
            if diff>0:
                if not np.isfinite(cclose(s,i)): eq_pos[s]=cur; continue
                cash_val-=diff; cash_val-=cost_oneway(diff,slip,"buy",cost_mult); turnover_notional+=diff; eq_pos[s]=tgt_each
                if cur==0.0: entry[s]=(cal[i],i)
            else:
                cash_val+=(-diff); cash_val-=cost_oneway(-diff,slip,"sell",cost_mult); turnover_notional+=(-diff); eq_pos[s]=tgt_each

    dec0=max(i0-1-extra_lag,0)
    above0=np.isfinite(sc[i0-1]) and np.isfinite(em[i0-1]) and sc[i0-1]>em[i0-1]
    if above0:
        state="EQUITY"; picks,tiers=pick_basket(dec0); deploy_equity(i0,picks,tiers)
    else:
        state="OUT"
        if np.isfinite(g3[i0-1]) and g3[i0-1]>0 and np.isfinite(gold.iloc[i0]):
            substate="GOLD"; gold_val=cash_val; cash_val=0.0; gold_val-=cost_oneway(gold_val,10.0,"buy",cost_mult)
        else: substate="CASH"
    Vprev=sum(eq_pos.values())+gold_val+cash_val
    daily.append((cal[i0],Vprev,0.0,state if state=="EQUITY" else substate))
    rebal_bounds.append((cal[i0],Vprev))

    for i in range(i0+1,CALN):
        if state=="EQUITY":
            for s in list(eq_pos.keys()):
                r=dret_np[i,col_ix[s]]; eq_pos[s]*=(1.0+(r if np.isfinite(r) else 0.0))
        if gold_val>0:
            r=gr[i]; gold_val*=(1.0+(r if np.isfinite(r) else 0.0))
        if cash_val!=0: cash_val*=(1.0+cashd)
        V=sum(eq_pos.values())+gold_val+cash_val
        rec_state=("EQUITY" if state=="EQUITY" else substate)
        daily.append((cal[i],V,V/Vprev-1.0 if Vprev>0 else 0.0,rec_state)); Vprev=V
        ab=np.isfinite(sc[i-1]) and np.isfinite(em[i-1]) and sc[i-1]>em[i-1]
        consec=consec+1 if ab else 0
        dec=max(i-1-extra_lag,0)
        if state=="EQUITY":
            if (i-i0)%REGIME==0 and not ab:
                close_all_equity(i,"regime_exit"); state="OUT"; consec=0
                if np.isfinite(g3[i-1]) and g3[i-1]>0 and np.isfinite(gold.iloc[i]):
                    substate="GOLD"; gold_val=cash_val; cash_val=0.0; gold_val-=cost_oneway(gold_val,10.0,"buy",cost_mult); turnover_notional+=gold_val
                else: substate="CASH"
            elif (i-i0)%REBAL==0:
                picks,tiers=pick_basket(dec)
                if picks: deploy_equity(i,picks,tiers)
        else:
            if consec>=REENTRY:
                if substate=="GOLD" and gold_val>0:
                    cash_val+=gold_val; cash_val-=cost_oneway(gold_val,10.0,"sell",cost_mult); turnover_notional+=gold_val; gold_val=0.0
                substate=None; state="EQUITY"; picks,tiers=pick_basket(dec); deploy_equity(i,picks,tiers); consec=0
            elif (i-i0)%REGIME==0:
                want_gold=np.isfinite(g3[i-1]) and g3[i-1]>0 and np.isfinite(gold.iloc[i])
                if want_gold and substate=="CASH":
                    gold_val=cash_val; cash_val=0.0; gold_val-=cost_oneway(gold_val,10.0,"buy",cost_mult); turnover_notional+=gold_val; substate="GOLD"
                elif (not want_gold) and substate=="GOLD" and gold_val>0:
                    cash_val+=gold_val; cash_val-=cost_oneway(gold_val,10.0,"sell",cost_mult); turnover_notional+=gold_val; gold_val=0.0; substate="CASH"
        if (i-i0)%REBAL==0: rebal_bounds.append((cal[i],V))

    for s in list(eq_pos.keys()):
        ec=cclose(s,CALN-1); e0d,e0i=entry.get(s,(END,CALN-1))
        ep=cclose(s,e0i) if np.isfinite(cclose(s,e0i)) else ec
        trades.append(dict(sym=s,universe=universe_mode,entry_date=str(e0d.date()),exit_date=str(END.date()),entry_close=float(ep),exit_close=float(ec),ret=float(ec/ep-1.0) if ep>0 else 0.0,tier=tier_now.get(s,"small"),reason="open_at_end",still_open=1))

    dd=pd.DataFrame(daily,columns=["date","V","ret","state"]).set_index("date")
    td=pd.DataFrame(trades); rb=pd.DataFrame(rebal_bounds,columns=["date","V"]).set_index("date")
    avgV=dd["V"].mean(); years=(dd.index[-1]-dd.index[0]).days/365.25
    meta=dict(universe=universe_mode,extra_lag=extra_lag,cash_rate=cash_rate,cost_mult=cost_mult,reverse=reverse,i0=int(i0),first_date=str(cal[i0].date()),last_date=str(END.date()),turnover_ann=float(turnover_notional/max(avgV,1)/max(years,1e-9)),fills_attempted=int(fills_attempted),fills_ok=int(fills_ok),n_clipped_cells=n_clipped,tag=tag)
    return dd,td,rb,meta

if __name__=="__main__":
    import pickle
    results={}
    combos=[("A",0,CASH_RATE,1.0,False,"A_1x"),("A",1,CASH_RATE,1.0,False,"A_lag1"),("A",0,CASH_RATE,2.0,False,"A_2x"),("A",0,0.0,1.0,False,"A_nocarry"),("B",0,CASH_RATE,1.0,False,"B_1x"),("B",0,CASH_RATE,2.0,False,"B_2x")]
    for um,lag,cr,cm,rev,tag in combos:
        dd,td,rb,meta=run_backtest(um,lag,cr,cm,rev,tag); results[tag]=(dd,td,rb,meta)
        print(f"[{tag}] {meta['first_date']}->{meta['last_date']} days={len(dd)} finalV={dd['V'].iloc[-1]:.0f} turn={meta['turnover_ann']:.2f} fills={meta['fills_ok']}/{meta['fills_attempted']}")
    with open(OUT+"/_raw_results.pkl","wb") as f: pickle.dump(results,f)
    pd.DataFrame({"n500":n500idx,"mss400":mss400,"sc100":sc100,"ema200":ema200,"gold":gold}).to_parquet(OUT+"/_market_series.parquet")
    print("clipped cells:",n_clipped); print("DONE")
