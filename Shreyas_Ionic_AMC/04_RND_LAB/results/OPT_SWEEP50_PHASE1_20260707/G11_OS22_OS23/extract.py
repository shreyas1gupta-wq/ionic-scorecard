import pandas as pd, numpy as np, glob, os, gc
import pyarrow.parquet as pq
root="intraday_options_strategy/datasets/raw/hf_index_options_1m/options/NIFTY"
OUT="C:/Users/SHREYA~1.1GU/AppData/Local/Temp/claude/c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500/0c22b4db-aef8-438e-81af-b9cb0af5930c/scratchpad"
sp=pd.read_parquet(f"{root}/../../index/NIFTY.parquet",columns=['timestamp','open','close','trading_day'])
sp=sp[(sp['timestamp'].dt.hour*60+sp['timestamp'].dt.minute)>=555]
g=sp.groupby('trading_day')
spot_close=g['close'].last(); spot_open=g['open'].first()
spot_close.index=pd.to_datetime(spot_close.index); spot_open.index=pd.to_datetime(spot_open.index)
sdates=spot_close.index.sort_values(); del sp,g; gc.collect()
def next_td(d):
    nx=sdates[sdates>d]; return nx[0] if len(nx) else None
files=sorted(glob.glob(f"{root}/*.parquet"))
exp=pd.to_datetime([os.path.basename(f)[:-8] for f in files])
edf=pd.DataFrame({'expiry':exp}); edf['ym']=edf['expiry'].dt.to_period('M')
monthly=sorted(edf.groupby('ym')['expiry'].max())
def quote(sub,otype,spot_ent,pct,lo,hi):
    d=sub[(sub['option_type']==otype)&(sub['volume']>0)]
    if d.empty: return (np.nan,np.nan)
    tgt=spot_ent*pct
    band=[s for s in d['strike'].unique() if lo*spot_ent<=s<=hi*spot_ent]
    if not band: return (np.nan,np.nan)
    K=min(band,key=lambda s:abs(s-tgt))
    dk=d[d['strike']==K].sort_values('timestamp')
    return (float(K),float(dk['close'].iloc[0]))
rows=[]; log=open(f"{OUT}/extract_progress.txt","w")
for i in range(1,len(monthly)):
    E=monthly[i]; ed=next_td(monthly[i-1])
    rec=dict(expiry=E.date(),entry=None,spot_ent=np.nan,spot_exp=np.nan,Kc=np.nan,Pc=np.nan,Kp=np.nan,Pp=np.nan,dte=np.nan,
             n_ce=0,ce_maxpct=np.nan,n_pe=0,pe_minpct=np.nan)
    if ed is not None and ed in spot_close.index and E in spot_close.index:
        spot_ent=float(spot_open.get(ed,np.nan)); spot_exp=float(spot_close[E])
        rec.update(entry=ed.date(),spot_ent=spot_ent,spot_exp=spot_exp,dte=(E-ed).days)
        f=f"{root}/{E.date()}.parquet"
        if os.path.exists(f) and not np.isnan(spot_ent):
            t=pq.read_table(f,columns=['timestamp','close','volume','strike','option_type'],
                            filters=[('trading_day','==',str(ed.date()))])
            sub=t.to_pandas(); del t
            if not sub.empty:
                sub=sub[(sub['timestamp'].dt.hour*60+sub['timestamp'].dt.minute)>=555]
                ce=sub[(sub['option_type']=='CE')&(sub['volume']>0)]['strike']
                pe=sub[(sub['option_type']=='PE')&(sub['volume']>0)]['strike']
                if len(ce): rec['n_ce']=ce.nunique(); rec['ce_maxpct']=100*ce.max()/spot_ent
                if len(pe): rec['n_pe']=pe.nunique(); rec['pe_minpct']=100*pe.min()/spot_ent
                Kc,Pc=quote(sub,'CE',spot_ent,1.05,1.03,1.08)
                Kp,Pp=quote(sub,'PE',spot_ent,0.95,0.92,0.97)
                rec.update(Kc=Kc,Pc=Pc,Kp=Kp,Pp=Pp)
            del sub; gc.collect()
    rows.append(rec)
    log.write(f"{i}/{len(monthly)-1} {E.date()} ent={rec['entry']} dte={rec['dte']} nCE={rec['n_ce']} ceMax%={rec['ce_maxpct']} Kc={rec['Kc']} Pc={rec['Pc']} nPE={rec['n_pe']} peMin%={rec['pe_minpct']} Kp={rec['Kp']} Pp={rec['Pp']}\n"); log.flush()
pd.DataFrame(rows).to_csv(f"{OUT}/cycles.csv",index=False); log.write("DONE\n"); log.close(); print("DONE")
