"""G09 Phase-1 triage: OS-29 jade lizard + OS-15 regime-gated 0DTE IC.
Arjun Rao / Head of Quant. FAST/CHEAP pass. Edge in RUPEE POINTS + %-of-SPOT.
Honest-causal only: strike selection & flags use entry-time info exclusively.
FAST rewrite: row-filtered parquet reads + vectorized per-day snapshots.
"""
import os, math, glob, bisect
import numpy as np, pandas as pd
from math import erf, sqrt, log
from datetime import time as dtime

BASE = "intraday_options_strategy/datasets/raw/hf_index_options_1m/"
OPTDIR = BASE + "options/NIFTY/"
SPOTF  = BASE + "index/NIFTY.parquet"
VIXF   = "datasets/index_daily/india_vix.parquet"
OUT    = "Shreyas_Ionic_AMC/04_RND_LAB/results/OPT_SWEEP50_PHASE1_20260707/G09_OS15_OS29/"
LOT=75
REGIME_BREAK=pd.Timestamp("2025-09-01").date()
OCOLS=["timestamp","close","volume","trading_day","strike","option_type"]

def Nd(x): return 0.5*(1+erf(x/sqrt(2)))
def bs_delta(S,K,T,sig,typ):
    if T<=0 or sig<=0:
        if typ=='CE': return 1.0 if S>K else 0.0
        return -1.0 if S<K else 0.0
    d1=(log(S/K)+0.5*sig*sig*T)/(sig*sqrt(T))
    return Nd(d1) if typ=='CE' else Nd(d1)-1.0

print("loading spot/vix...",flush=True)
spot=pd.read_parquet(SPOTF,columns=["timestamp","open","high","low","close","trading_day"])
spot["trading_day"]=spot["trading_day"].astype(str)
spot["t"]=spot["timestamp"].dt.time
spot=spot[spot["t"]>=dtime(9,15)].copy()
sm={u:pd.Timestamp(u).date() for u in spot["trading_day"].unique()}
spot["td"]=spot["trading_day"].map(sm)
daily=spot.groupby("td").agg(o=("open","first"),c=("close","last"),h=("high","max"),l=("low","min")).reset_index().sort_values("td").reset_index(drop=True)
daily["prevc"]=daily["c"].shift(1)
cal=daily["td"].tolist(); cal_idx={d:i for i,d in enumerate(cal)}
prevc_map=dict(zip(daily["td"],daily["prevc"]))
sclose=dict(zip(daily["td"],daily["c"]))
spot_by_day={d:g for d,g in spot.groupby("td")}

vix=pd.read_parquet(VIXF)
vix["td"]=pd.to_datetime(vix["timestamp"]).dt.date
vix=vix.sort_values("td").reset_index(drop=True)
vix["med20"]=vix["close"].rolling(20).median()
vc=dict(zip(vix["td"],vix["close"])); vm=dict(zip(vix["td"],vix["med20"])); vdays=vix["td"].tolist()
def prior_vix(d):
    i=bisect.bisect_left(vdays,d)
    if i==0: return None,None
    p=vdays[i-1]; return vc.get(p),vm.get(p)

def spot_at(td,hhmm):
    g=spot_by_day.get(td)
    if g is None: return None
    x=g[g["t"]>=hhmm]
    return float(x.iloc[0]["close"]) if len(x) else None

def read_days(fp,days):
    try:
        df=pd.read_parquet(fp,columns=OCOLS,filters=[("trading_day","in",days)])
    except Exception:
        df=pd.read_parquet(fp,columns=OCOLS); df["trading_day"]=df["trading_day"].astype(str); df=df[df["trading_day"].isin(days)]
    if df.empty: return df
    df["trading_day"]=df["trading_day"].astype(str)
    df["option_type"]=df["option_type"].astype(str)
    df["t"]=df["timestamp"].dt.time
    df=df[df["t"]>=dtime(9,15)]
    return df

def snap(df_day,after,before=None):
    d=df_day[(df_day["t"]>=after)&(df_day["volume"]>0)]
    if before is not None: d=d[d["t"]<=before]
    if d.empty: return {}
    d=d.sort_values("timestamp")
    g=d.groupby(["option_type","strike"],as_index=False).first()
    return {(r.option_type,int(r.strike)):float(r.close) for r in g.itertuples()}

def atm_sig(sp,S,T):
    ce={k for (t,k) in sp if t=='CE'}; pe={k for (t,k) in sp if t=='PE'}
    common=ce&pe
    if not common: return None
    a=min(common,key=lambda k:abs(k-S))
    st=sp[('CE',a)]+sp[('PE',a)]
    return max(0.03,min(2.0,st/(S*sqrt(max(T,1e-6))*0.7979)))

def pick(sp,typ,S,T,sig,target,exclude=None):
    best=None
    for (t,k) in sp:
        if t!=typ: continue
        if exclude and k in exclude: continue
        d=abs(bs_delta(S,k,T,sig,typ)); sc=abs(d-target)
        if best is None or sc<best[0]: best=(sc,k,sp[(typ,k)],d)
    return best

def run_os29():
    rows=[]; drop_upside=0; tried=0
    for fp in sorted(glob.glob(OPTDIR+"*.parquet")):
        exp=os.path.basename(fp)[:-8]
        try: expd=pd.Timestamp(exp).date()
        except: continue
        if expd not in cal_idx: continue
        ei=cal_idx[expd]
        if ei<4: continue
        entry_td=cal[ei-4]; after=dtime(9,20)
        S=spot_at(entry_td,after)
        if S is None: continue
        T=max((expd-entry_td).days,1)/365.0
        df=read_days(fp,[str(entry_td)])
        if df.empty: continue
        dd=df[df["trading_day"]==str(entry_td)]
        sp=snap(dd,after)
        if not sp: continue
        sig=atm_sig(sp,S,T)
        if sig is None: continue
        tried+=1
        bpe=pick(sp,'PE',S,T,sig,0.20); bce=pick(sp,'CE',S,T,sig,0.20)
        if not bpe or not bce: continue
        _,Kpe,pPe,dpe=bpe; _,Kces,pCes,dces=bce
        best=None
        for (t,k) in sp:
            if t!='CE' or k<=Kces: continue
            pCel=sp[('CE',k)]; w=k-Kces; cr=pPe+pCes-pCel
            if cr>=w and w>0:
                sc=abs(abs(bs_delta(S,k,T,sig,'CE'))-0.10)
                if best is None or sc<best[0]: best=(sc,k,pCel,w,cr)
        if best is None:
            drop_upside+=1; continue
        _,Kcel,pCel,width,credit=best
        Sx=sclose.get(expd)
        if Sx is None: continue
        liab=max(0,Kpe-Sx)+max(0,Sx-Kces)-max(0,Sx-Kcel)
        gross=credit-liab
        ev=[max(0,Kpe-Sx),max(0,Sx-Kces),max(0,Sx-Kcel)]; itm=[v for v in ev if v>0]
        broker=(20*3*2)/LOT
        slip=sum(max(0.05,0.0025*p) for p in [pPe,pCes,pCel])+sum(max(0.05,0.0025*p) for p in ev if p>0)
        stt=0.001*(pPe+pCes)+0.00125*sum(itm)
        exch=0.00035*(pPe+pCes+pCel+sum(v for v in ev if v>0))
        gst=0.18*(20*3*2+exch*LOT)/LOT
        c=broker+slip+stt+exch+gst; net=gross-c
        rows.append(dict(exp=exp,entry=str(entry_td),S=round(S,1),Sx=round(Sx,1),sig=round(sig,3),
            Kpe=Kpe,Kces=Kces,Kcel=Kcel,width=width,credit=round(credit,2),
            gross=round(gross,2),cost=round(c,2),net=round(net,2),net_pctspot=round(100*net/S,4),
            regime=("post" if entry_td>=REGIME_BREAK else "pre")))
    print(f"OS29: tried={tried} built={len(rows)} dropped_upside={drop_upside}",flush=True)
    return pd.DataFrame(rows)

def run_os15():
    rows=[]; ea=dtime(9,20); xa=dtime(15,10); T=(5.9/6.25)/252.0
    for fp in sorted(glob.glob(OPTDIR+"*.parquet")):
        exp=os.path.basename(fp)[:-8]
        try: expd=pd.Timestamp(exp).date()
        except: continue
        if expd not in cal_idx: continue
        S=spot_at(expd,ea)
        if S is None: continue
        prevc=prevc_map.get(expd)
        if prevc is None or prevc!=prevc: continue
        g=spot_by_day.get(expd)
        m=g[(g["t"]>=dtime(9,15))&(g["t"]<=dtime(9,30))]
        if m.empty: continue
        or_range=(m["high"].max()-m["low"].min())/S
        open_gap=abs(float(m.iloc[0]["open"])-prevc)/prevc
        pv,pm=prior_vix(expd)
        if pv is None: continue
        crush=(pv<15.0) and (open_gap<0.003) and (or_range<0.002)
        df=read_days(fp,[str(expd)])
        if df.empty: continue
        dd=df[df["trading_day"]==str(expd)]
        sp=snap(dd,ea)
        if not sp: continue
        sig=atm_sig(sp,S,T)
        if sig is None: continue
        bce=pick(sp,'CE',S,T,sig,0.20); bpe=pick(sp,'PE',S,T,sig,0.20)
        if not bce or not bpe: continue
        _,Kces,pCes,_=bce; _,Kpes,pPes,_=bpe
        bcw=pick(sp,'CE',S,T,sig,0.10,exclude={Kces}); bpw=pick(sp,'PE',S,T,sig,0.10,exclude={Kpes})
        if not bcw or not bpw: continue
        _,Kcew,pCew,_=bcw; _,Kpew,pPew,_=bpw
        if not(Kcew>Kces and Kpew<Kpes): continue
        credit=pCes+pPes-pCew-pPew
        if credit<=0: continue
        Sx=sclose.get(expd)
        spx=snap(dd,xa)
        def xp(typ,K):
            v=spx.get((typ,K))
            if v is not None: return v
            return max(0,(Sx-K) if typ=='CE' else (K-Sx))
        buyback=xp('CE',Kces)+xp('PE',Kpes)-xp('CE',Kcew)-xp('PE',Kpew)
        gross=credit-buyback
        ev=[xp('CE',Kces),xp('PE',Kpes),xp('CE',Kcew),xp('PE',Kpew)]
        itm=[v for v in [max(0,Sx-Kces),max(0,Kpes-Sx)] if v>0]
        broker=(20*4*2)/LOT
        slip=sum(max(0.05,0.0025*p) for p in [pCes,pPes,pCew,pPew])+sum(max(0.05,0.0025*p) for p in ev if p>0)
        stt=0.001*(pCes+pPes)+0.00125*sum(itm)
        exch=0.00035*(pCes+pPes+pCew+pPew+sum(v for v in ev if v>0))
        gst=0.18*(20*4*2+exch*LOT)/LOT
        c=broker+slip+stt+exch+gst; net=gross-c
        rows.append(dict(exp=exp,S=round(S,1),Sx=round(Sx,1),pvix=round(pv,2),
            open_gap=round(open_gap*100,3),or_range=round(or_range*100,3),crush=bool(crush),
            credit=round(credit,2),gross=round(gross,2),cost=round(c,2),net=round(net,2),
            net_pctspot=round(100*net/S,4),regime=("post" if expd>=REGIME_BREAK else "pre")))
    print(f"OS15: built={len(rows)} crush_true={sum(r['crush'] for r in rows)}",flush=True)
    return pd.DataFrame(rows)

def summ(df,label):
    if df is None or len(df)==0: return f"{label}: NO TRADES"
    n=len(df); mean=df["net"].mean(); sd=df["net"].std(); med=df["net"].median()
    pt=mean/sd if sd>0 else float('nan')
    ann=pt*math.sqrt(52) if pt==pt else float('nan')
    win=(df["net"]>0).mean()*100
    return (f"{label}: N={n} mean={mean:.2f}pt ({100*mean/df['S'].mean():.4f}%spot) med={med:.2f} "
            f"sd={sd:.2f} ptSharpe={pt:.3f} annSharpe~{ann:.2f} win={win:.1f}% tot={df['net'].sum():.0f}pt minTrade={df['net'].min():.1f}")

if __name__=="__main__":
    print("=== OS-29 jade lizard ===",flush=True)
    d29=run_os29(); d29.to_csv(OUT+"os29_trades.csv",index=False)
    print(summ(d29,"OS29 ALL"))
    if len(d29):
        print(summ(d29[d29.regime=="pre"],"OS29 PRE"))
        print(summ(d29[d29.regime=="post"],"OS29 POST"))
    print("\n=== OS-15 0DTE IC gated ===",flush=True)
    d15=run_os15(); d15.to_csv(OUT+"os15_trades.csv",index=False)
    print(summ(d15,"OS15 ALL(ungated=K005)"))
    if len(d15):
        print(summ(d15[d15.crush],"OS15 CRUSH=TRUE(gated)"))
        print(summ(d15[~d15.crush],"OS15 CRUSH=FALSE"))
        print(summ(d15[d15.regime=='pre'],"OS15 PRE all"))
        print(summ(d15[d15.regime=='post'],"OS15 POST all"))
    print("DONE",flush=True)
