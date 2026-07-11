"""MEANREV_RSI_CAMPAIGN — Test A (Arjun Rao / quant desk, 2026-07-07).

30-min z-score mean reversion, far-OTM SELL. Two variants: EMA100 & EMA200.
On 30-min NIFTY spot bars compute EMA(span=L) and rolling std(L); z=(close-EMA)/std.
  z >= +2 (extended UP)   -> SELL CALL 100pts OTM (K=round(spot+100)) : fade the rally
  z <= -2 (extended DOWN) -> SELL PUT  100pts OTM (K=round(spot-100)) : fade the selloff

EXIT ASSUMPTION (Principal left open; STATED for challenge):
  exit when z reverts inside +/-0.5 (reversion complete), checked at each later 30-min
  bar close; else MAX HOLD 5 trading days; else EXPIRY settle. Whichever first.

Causal: signal at 30-min bar CLOSE (t); entry strictly AFTER (next 1-min bar = next
30-min bar open). One position at a time. Costs = COST_STANDARDS (APPROVED D-021),
100-OTM index slippage 0.5% one-way. Headline = denominator-free RUPEE POINTS + %spot.
"""
import sys, time
from pathlib import Path
from functools import lru_cache
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, ROOT + r"\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server")
import data_loader as dl

OUT = Path(__file__).parent
LOT = 75
SLIP_FRAC = 0.005            # 100-OTM index one-way slippage 0.5%
Z_ENTRY = 2.0
Z_EXIT  = 0.5
MAXHOLD_TD = 5
EXP_DTE_MIN, EXP_DTE_MAX = 2, 10
SETTLE_START, SETTLE_END = 900, 929
SESS_OPEN = 555

def cost_rt(entry, exit):
    brok = 40.0
    turnover = (entry+exit)*LOT
    ex_txn = 0.00035*turnover; ipft=0.000005*turnover; sebi=0.000001*turnover
    stt = 0.001*entry*LOT            # sell-side STT on entry premium
    stamp = 0.00003*exit*LOT         # buy-side stamp on exit premium
    gst = 0.18*(brok+ex_txn+ipft+sebi)
    slip = (max(0.05,SLIP_FRAC*entry)+max(0.05,SLIP_FRAC*exit))*LOT
    return brok+stt+ex_txn+ipft+sebi+stamp+gst+slip

s = dl._spot()
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
days_list = list(dl.trading_days())
day_pos = {d:i for i,d in enumerate(days_list)}
DATA_MAX = days_list[-1]

# ---- build 30-min bars (global ordered series) ----
def bucket(hm): return min(12, int((hm-SESS_OPEN)//30))
rows = []
for d in days_list:
    arr = by_day[d]
    if len(arr) < 100: continue
    bk = np.array([bucket(h) for h in arr[:,0]])
    for b in range(13):
        m = bk==b
        if not m.any(): continue
        sub = arr[m]
        rows.append((d, int(sub[0,0]), int(sub[-1,0]), float(sub[-1,4])))  # d, start_hm, end_hm, close
bars = pd.DataFrame(rows, columns=["d","start_hm","end_hm","close"]).reset_index(drop=True)

expiries = list(dl.expiries())
def pick_expiry(entry_day):
    c = [e for e in expiries if EXP_DTE_MIN <= (e-entry_day).days <= EXP_DTE_MAX]
    return c[0] if c else None

# fast chain access: read each expiry parquet ONCE (LRU), slice per day, cache small chains
@lru_cache(maxsize=6)
def _expiry_df(ex):
    cols=["timestamp","strike","option_type","close"]
    df=pq.read_table(dl.expiry_path(ex), columns=cols).to_pandas()
    ts=pd.to_datetime(df["timestamp"])
    ts=ts.dt.tz_convert("Asia/Kolkata") if ts.dt.tz is not None else ts.dt.tz_localize("Asia/Kolkata")
    hm=ts.dt.hour*60+ts.dt.minute
    m=(hm>=SESS_OPEN)&(hm<=930)&(df["close"]>0)
    out=df.loc[m, ["strike","option_type","close"]].copy()
    out["hm"]=hm[m].astype(int); out["d"]=ts[m].dt.date
    return out

mi_cache={}
def get_chain(d, ex):
    k=(d,ex)
    if k in mi_cache: return mi_cache[k]
    try: df=_expiry_df(ex)
    except Exception: mi_cache[k]=None; return None
    g=df[df["d"]==d]
    if g.empty: mi_cache[k]=None; return None
    mi={}
    for hm,K,cp,c in zip(g["hm"].to_numpy(),g["strike"].to_numpy(),
                          g["option_type"].to_numpy(),g["close"].to_numpy()):
        mi.setdefault(int(hm),{})[(int(K),str(cp))]=float(c)
    ch={"minute_index":mi}; mi_cache[k]=ch
    return ch

def opt_price(chain, hm, K, cp, back=20, fwd=20):
    if chain is None: return None
    mi=chain["minute_index"]
    key=(int(K),cp)
    for b in range(back+1):
        r=mi.get(hm-b,{}).get(key)
        if r is not None and r>0: return r
    for f in range(1,fwd+1):
        r=mi.get(hm+f,{}).get(key)
        if r is not None and r>0: return r
    return None

def spot_at(d, hm, tol=20):
    arr=by_day.get(d)
    if arr is None or len(arr)==0: return None
    idx=np.searchsorted(arr[:,0], hm)
    if 0<=idx<len(arr) and abs(int(arr[idx,0])-hm)<=tol: return float(arr[idx,4])
    if idx>0 and abs(int(arr[idx-1,0])-hm)<=tol: return float(arr[idx-1,4])
    return None

def expiry_settle(exp):
    arr=by_day.get(exp)
    if arr is None or len(arr)==0: return None
    tail=arr[(arr[:,0]>=SETTLE_START)&(arr[:,0]<=SETTLE_END)]
    if len(tail)<3: return None
    return float(tail[:,4].mean())

def run(L):
    b = bars.copy()
    b["ema"]=b["close"].ewm(span=L, adjust=False).mean()
    b["std"]=b["close"].rolling(L).std()
    b["z"]=(b["close"]-b["ema"])/b["std"]
    b=b.reset_index(drop=True)
    n=len(b)
    trades=[]; nofill=0
    i=L
    while i < n-1:
        z=b["z"].iloc[i]
        if pd.isna(z) or abs(z) < Z_ENTRY:
            i+=1; continue
        sig_d=b["d"].iloc[i]; sig_end=int(b["end_hm"].iloc[i]); side_up = z>=Z_ENTRY
        # ---- entry: next 1-min bar (== next 30-min bar open), strictly after signal close ----
        if i+1 < n and b["d"].iloc[i+1]==sig_d:
            entry_d=sig_d; entry_hm=int(b["start_hm"].iloc[i+1])
        else:
            # signal was last bar of day -> next trading day open
            dp=day_pos[sig_d]
            if dp+1>=len(days_list): break
            entry_d=days_list[dp+1]; entry_hm=SESS_OPEN
        entry_spot=spot_at(entry_d, entry_hm)
        if entry_spot is None: i+=1; continue
        if side_up:
            cp="CE"; K=int(round((entry_spot+100)/50)*50)
        else:
            cp="PE"; K=int(round((entry_spot-100)/50)*50)
        ex=pick_expiry(entry_d)
        if ex is None: i+=1; continue
        ch=get_chain(entry_d, ex)
        entry_px=opt_price(ch, entry_hm, K, cp)
        if entry_px is None or entry_px<0.5: nofill+=1; i+=1; continue
        # ---- walk forward 30-min bars for exit ----
        entry_dp=day_pos[entry_d]
        exit_px=None; exit_d=None; reason=None; exit_bar=i
        j=i+1
        while j<n:
            dj=b["d"].iloc[j]; djp=day_pos[dj]
            held_td=djp-entry_dp
            # expiry reached?
            if dj>=ex:
                st=expiry_settle(ex)
                if st is not None:
                    exit_px=max(0.0,(st-K) if cp=="CE" else (K-st))
                    exit_d=ex; reason="EXPIRY"; exit_bar=j
                break
            # max hold?
            if held_td>=MAXHOLD_TD:
                hm_x=int(b["end_hm"].iloc[j])
                px=opt_price(get_chain(dj,ex), hm_x, K, cp)
                if px is not None:
                    exit_px=px; exit_d=dj; reason="MAXHOLD"; exit_bar=j
                break
            # z reversion?
            zj=b["z"].iloc[j]
            if not pd.isna(zj) and abs(zj)<=Z_EXIT:
                hm_x=int(b["end_hm"].iloc[j])
                px=opt_price(get_chain(dj,ex), hm_x, K, cp)
                if px is not None:
                    exit_px=px; exit_d=dj; reason="ZREVERT"; exit_bar=j
                    break
            j+=1
        if exit_px is None or exit_d is None:
            nofill+=1; i+=1; continue
        if pd.Timestamp(exit_d)>pd.Timestamp(DATA_MAX): i=exit_bar+1; continue
        gross=(entry_px-exit_px)            # SELL
        c=cost_rt(entry_px,exit_px)
        net=gross-c/LOT
        trades.append(dict(
            sig_d=str(sig_d), entry_d=str(entry_d), exit_d=str(exit_d),
            z=round(float(z),2), cp=cp, K=K, entry_spot=round(entry_spot,1),
            entry_px=round(entry_px,2), exit_px=round(exit_px,2),
            hold_td=day_pos[exit_d]-entry_dp, reason=reason,
            gross_pts=round(gross,2), cost_pts=round(c/LOT,2),
            net_pts=round(net,2), pct_spot=round(net/entry_spot*100,4),
        ))
        i=exit_bar+1     # one position at a time: resume after exit bar
    return trades, nofill

def stats(trades, name, nofill):
    if not trades: return dict(variant=name, n=0, nofill=nofill)
    df=pd.DataFrame(trades); p=df["net_pts"].values
    df["exit_d"]=pd.to_datetime(df["exit_d"]); df["entry_d"]=pd.to_datetime(df["entry_d"])
    years=max((df["exit_d"].max()-df["entry_d"].min()).days/365.25,0.5)
    tpy=len(p)/years
    pt_sharpe=p.mean()/(p.std()+1e-9); ann=pt_sharpe*np.sqrt(max(tpy,1e-9))
    p2=df["gross_pts"].values-2*df["cost_pts"].values
    return dict(variant=name, n=len(p), nofill=nofill, trades_per_yr=round(tpy,1),
        avg_hold_td=round(df["hold_td"].mean(),1),
        win_pct=round((p>0).mean()*100,1),
        mean_net_pts=round(p.mean(),2), med_net_pts=round(np.median(p),2),
        mean_pct_spot=round(df["pct_spot"].mean(),4), mean_cost_pts=round(df["cost_pts"].mean(),2),
        avg_win_pts=round(p[p>0].mean(),1) if (p>0).any() else 0,
        avg_loss_pts=round(p[p<0].mean(),1) if (p<0).any() else 0,
        worst_pts=round(p.min(),1), best_pts=round(p.max(),1),
        pt_sharpe=round(pt_sharpe,3), ann_sharpe=round(ann,2),
        total_pts=round(p.sum(),1), total_rs_1lot=round(p.sum()*LOT,0),
        mean_net_pts_2x=round(p2.mean(),2),
        ann_sharpe_2x=round(p2.mean()/(p2.std()+1e-9)*np.sqrt(max(tpy,1e-9)),2),
        pct_zrevert=round((df["reason"]=="ZREVERT").mean()*100,1),
        pct_maxhold=round((df["reason"]=="MAXHOLD").mean()*100,1),
        pct_expiry=round((df["reason"]=="EXPIRY").mean()*100,1))

if __name__=="__main__":
    t0=time.time()
    print(f"30-min bars built: {len(bars)}  ({bars['d'].iloc[0]} .. {bars['d'].iloc[-1]})")
    all_stats=[]
    for L in (100,200):
        name=f"TestA_EMA{L}"
        tr,nf=run(L)
        pd.DataFrame(tr).to_csv(OUT/f"trades_{name}.csv", index=False)
        st=stats(tr,name,nf); all_stats.append(st)
        print(f"{name}: n={st['n']} nofill={nf} win={st.get('win_pct')}% "
              f"mean_net={st.get('mean_net_pts')}pts ann_sharpe={st.get('ann_sharpe')} "
              f"({time.time()-t0:.0f}s)")
    pd.DataFrame(all_stats).to_csv(OUT/"stats_A.csv", index=False)
    print("\n"+pd.DataFrame(all_stats).set_index("variant").T.to_string())
    print(f"\nruntime {time.time()-t0:.0f}s")
