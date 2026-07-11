# OS-50: BUY swing CE/PE on NIFTY momentum (Donchian) breakout, multi-day hold.
# Phase-1 fast/cheap triage. Directional option BUYING (K-001-adjacent, fights VRP).
import sys, datetime as dt
sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\buying")
import pandas as pd, numpy as np
import pyarrow.parquet as pq, pyarrow.compute as pc
import chain as C

H = 5          # hold horizon (trading days)
MIN_DTE = 3
LOT = 75

mapping, exps = C.build_expiry_index()          # {date: Path}
exp_arr = sorted(exps)

# ---- lazy coverage test via predicate-pushdown (memory-frugal) ----
def covers(exp, day_iso):
    filt = pc.field('trading_day')==day_iso
    t = pq.read_table(mapping[exp], columns=['strike'], filters=filt)
    return t.num_rows>0

# ---- filtered option read (only needed rows) ----
def opt_rows(exp, day_iso, strike, otype):
    filt = (pc.field('trading_day')==day_iso) & (pc.field('strike')==strike) & (pc.field('option_type')==otype)
    t = pq.read_table(mapping[exp], columns=['timestamp','close','volume','strike','option_type','trading_day'], filters=filt)
    if t.num_rows==0: return None
    df = t.to_pandas()
    df = df[df['volume']>0]
    if df.empty: return None
    df['tt'] = pd.to_datetime(df['timestamp']).dt.tz_localize(None)
    return df.sort_values('tt')

def liq_px(exp, day_iso, strike, otype, side):
    df = opt_rows(exp, day_iso, strike, otype)
    if df is None: return None
    if side=='entry':
        df = df[df['tt'].dt.time >= dt.time(9,20)]
    else:
        df = df[df['tt'].dt.time <= dt.time(15,20)]
    if df.empty: return None
    row = df.iloc[0] if side=='entry' else df.iloc[-1]
    v = float(row['close'])
    return v if v>0 else None

def opt_close_on(exp, day_iso, strike, otype):
    df = opt_rows(exp, day_iso, strike, otype)
    if df is None: return None
    df = df[df['tt'].dt.time <= dt.time(15,20)]
    if df.empty: return None
    v=float(df.iloc[-1]['close']); return v if v>0 else None

# ---- spot -> daily OHLC ----
idx = C.load_index()
idx = idx[idx.index.time >= dt.time(9,15)]
g = idx.groupby(idx.index.normalize())
daily = pd.DataFrame({'open':g['open'].first(),'high':g['high'].max(),
                      'low':g['low'].min(),'close':g['close'].last()}).sort_index()
tdays = list(daily.index)
def next_tday(d):
    for t in tdays:
        if t>d: return t
    return None

def pick_expiry(entry_day):
    ed = pd.Timestamp(entry_day); ed_iso = ed.date().isoformat()
    cands = sorted([e for e in exp_arr if MIN_DTE <= (pd.Timestamp(e)-ed).days <= 14])
    for e in reversed(cands):                 # most time first
        if covers(e, ed_iso):
            return e
    return None

def roundtrip_cost_pts(entry_px, exit_px):
    slip = 0.0025*entry_px + 0.0025*exit_px
    brok = 40.0/LOT
    stt  = 0.001*exit_px
    exch = 0.00035*(entry_px+exit_px)
    stamp= 0.00003*entry_px
    gst  = 0.18*(brok+exch)
    return slip+brok+stt+exch+stamp+gst

def run(N):
    ph = daily['high'].shift(1).rolling(N).max()
    pl = daily['low'].shift(1).rolling(N).min()
    c  = daily['close']
    up   = (c>ph) & (c.shift(1)<=ph.shift(1))
    down = (c<pl) & (c.shift(1)>=pl.shift(1))
    trades=[]; busy_until=None
    for d in tdays:
        if busy_until is not None and d < busy_until: continue
        sig = 'CE' if up.get(d,False) else ('PE' if down.get(d,False) else None)
        if sig is None: continue
        ed = next_tday(d)
        if ed is None: continue
        exp = pick_expiry(ed)
        if exp is None: continue
        exp_iso = pd.Timestamp(exp).date().isoformat(); ed_iso=ed.date().isoformat()
        spot_e = float(daily['close'].get(d)); strike=int(round(spot_e/50)*50)
        entry_px = liq_px(exp, ed_iso, strike, sig, 'entry')
        if entry_px is None:                       # circuit/zero-vol => DROP
            continue
        entry_px_close = opt_close_on(exp, d.date().isoformat(), strike, sig)
        j = tdays.index(ed)
        exit_target = tdays[min(j+H, len(tdays)-1)]
        last_exp_day = max([t for t in tdays if t <= pd.Timestamp(exp)], default=exit_target)
        exit_day = min(exit_target, last_exp_day)
        exit_px=None
        for t in reversed([t for t in tdays if ed <= t <= exit_day]):
            exit_px = liq_px(exp, t.date().isoformat(), strike, sig, 'exit')
            if exit_px is not None: exit_day=t; break
        if exit_px is None: continue
        gross = exit_px-entry_px; cost=roundtrip_cost_pts(entry_px,exit_px); net=gross-cost
        gross_opt = (exit_px-entry_px_close) if entry_px_close else np.nan
        trades.append(dict(sig=sig,sig_day=d.date(),entry_day=ed.date(),exit_day=exit_day.date(),
            exp=exp_iso,strike=strike,spot_e=spot_e,entry_px=entry_px,exit_px=exit_px,
            gross=gross,cost=cost,net=net,gross_opt=gross_opt,
            pct_spot_gross=100*gross/spot_e,pct_spot_net=100*net/spot_e))
        busy_until = next_tday(exit_day)
    return pd.DataFrame(trades)

def summ(tr,label):
    if tr is None or tr.empty:
        print(f"\n[{label}] NO TRADES"); return
    n=len(tr)
    print(f"\n===== {label}  (N={n}) =====")
    print(f"  entry premium pts: mean {tr['entry_px'].mean():.1f} median {tr['entry_px'].median():.1f}")
    print(f"  GROSS pts/trade mean {tr['gross'].mean():+.2f} median {tr['gross'].median():+.2f} sum {tr['gross'].sum():+.0f}")
    print(f"  NET1x pts/trade mean {tr['net'].mean():+.2f} median {tr['net'].median():+.2f} sum {tr['net'].sum():+.0f}")
    print(f"  %-spot GROSS mean {tr['pct_spot_gross'].mean():+.4f}%  NET mean {tr['pct_spot_net'].mean():+.4f}%")
    print(f"  win-rate(net) {(tr['net']>0).mean():.0%}  avg cost {tr['cost'].mean():.2f} pts")
    go=tr['gross_opt'].dropna()
    if len(go): print(f"  OPTIMISTIC same-day-close entry GROSS mean {go.mean():+.2f} (n={len(go)})")
    r=tr['pct_spot_net']; print(f"  per-trade net %-spot std {r.std():.4f} t-stat {r.mean()/(r.std()/np.sqrt(n)+1e-12):.2f}")
    by=tr.assign(yr=pd.to_datetime(tr['entry_day']).dt.year).groupby('yr')['net'].agg(['count','mean','sum'])
    print("  by year (net pts):\n"+by.round(1).to_string())

for N in (20,10):
    tr=run(N)
    summ(tr,f"OS-50 Donchian({N}) ATM, hold {H}d, D+1 next-liquid, 1x cost")
    if N==20 and tr is not None and not tr.empty:
        out=r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\0c22b4db-aef8-438e-81af-b9cb0af5930c\scratchpad\os50_trades_N20.csv"
        tr.to_csv(out,index=False)
        cut=pd.Timestamp('2025-09-01')
        summ(tr[pd.to_datetime(tr['entry_day'])<cut],"OS-50 N20 PRE Sept-2025")
        summ(tr[pd.to_datetime(tr['entry_day'])>=cut],"OS-50 N20 POST Sept-2025")
        summ(tr[tr['sig']=='CE'],"OS-50 N20 CE only")
        summ(tr[tr['sig']=='PE'],"OS-50 N20 PE only")
