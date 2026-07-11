"""BUY 1-sigma PE when Nifty < 20DMA AND < 50DMA (bearish trend regime).

1-sigma derived from actual ATM straddle: sigma = (ATM_CE + ATM_PE) * 1.25
1-sigma strike = round((spot - sigma) / 50) * 50

Grid:
  - sigma multiplier: 0.5, 1.0, 1.5
  - hold: to expiry (default) & early exit at Wed EOD (for weeklies)
  - filter: < 20DMA AND < 50DMA
Real costs. 1 lot per trade. Weekly entry (Monday 09:30, front expiry 4-7 DTE).
"""
import sys, time
from pathlib import Path
from datetime import date
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INTRADAY_STUDY_20260707")
LOT = 65; CAP0 = 10_000_000
ENTRY_HM = 570

def buy_cost(entry, exit):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    stt = 0.001 * exit * LOT   # STT on sell = exit; if ITM at expiry, ~0.125% of intrinsic
    stamp = 3e-5 * entry * LOT
    gst = 0.18*(brok + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + hs

def buy_pnl(e, x):
    c = buy_cost(e, x)
    if c is None: return None
    return (x - e) * LOT - c

s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(close=("close","last")).reset_index()
daily["sma20"] = daily["close"].rolling(20).mean()
daily["sma50"] = daily["close"].rolling(50).mean()
daily["bear"] = (daily["close"] < daily["sma20"]) & (daily["close"] < daily["sma50"])
daily = daily.dropna(subset=["sma50"]).reset_index(drop=True)

expiries = list(dl.expiries())
opt_cache = {}
def get_chain(d, ex):
    k = (d, ex)
    if k not in opt_cache:
        if len(opt_cache) > 60:
            for _k in list(opt_cache.keys())[:20]: del opt_cache[_k]
        try: opt_cache[k] = dl.load_option_day(ex, d)
        except Exception: opt_cache[k] = None
    return opt_cache[k]

def opt_px(ch, hm, K, cp):
    if ch is None: return None
    for b in range(16):
        r = ch["minute_index"].get(hm - b, {}).get((int(K), cp))
        if r: return r["c"]
    for f in range(1, 6):
        r = ch["minute_index"].get(hm + f, {}).get((int(K), cp))
        if r: return r["c"]
    return None

def spot_at(d, hm):
    arr = by_day.get(d)
    if arr is None or len(arr) == 0: return None
    idx = np.searchsorted(arr[:,0], hm)
    if 0 <= idx < len(arr): return float(arr[idx, 4])
    return float(arr[-1, 4])

def expiry_settle(exp):
    arr = by_day.get(exp)
    if arr is None: return None
    tail = arr[(arr[:,0] >= 900) & (arr[:,0] <= 929)]
    return float(tail[:,4].mean()) if len(tail) >= 5 else None

# ==========================================================
def run(sigma_mult=1.0, early_exit_wed=False):
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue      # Monday entry
        if not bool(daily.iloc[i-1]["bear"]): continue  # need bearish regime (< 20DMA AND < 50DMA)
        later = [e for e in expiries if (e - d).days in range(4, 10)]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        atm = int(round(sp / 50) * 50)
        ch = get_chain(d, ex)
        # sigma from ATM straddle
        ce_atm = opt_px(ch, ENTRY_HM, atm, "CE")
        pe_atm = opt_px(ch, ENTRY_HM, atm, "PE")
        if ce_atm is None or pe_atm is None: continue
        sigma_pts = (ce_atm + pe_atm) * 1.25   # BS approx: ATM straddle / 0.8 ~ 1sigma move
        K = int(round((sp - sigma_mult * sigma_pts) / 50) * 50)
        if K <= 0: continue
        px_e = opt_px(ch, ENTRY_HM, K, "PE")
        if px_e is None or px_e < 0.5: continue
        # exit
        if early_exit_wed:
            # find Wednesday of same week
            wed_d = d + pd.Timedelta(days=2)  # Wed = Mon+2
            wed_arr = by_day.get(wed_d.date() if hasattr(wed_d, "date") else wed_d)
            if wed_arr is None: continue
            wed_ch = get_chain(wed_d.date() if hasattr(wed_d, "date") else wed_d, ex)
            if wed_ch is None: continue
            px_x = opt_px(wed_ch, 920, K, "PE")   # 15:20 close on Wed
            if px_x is None: continue
            exit_type = "WED_EOD"
        else:
            settle = expiry_settle(ex)
            if settle is None: continue
            px_x = max(0.0, K - settle)
            exit_type = "EXPIRY"
        pnl = buy_pnl(px_e, px_x)
        if pnl is None: continue
        trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                           K=K, spot_entry=sp,
                           sigma_pts=round(sigma_pts,1),
                           entry_px=px_e, exit_px=round(px_x,2),
                           exit_type=exit_type, pnl=round(pnl,0)))
    return pd.DataFrame(trades)

def stats(df, name):
    if len(df) == 0: return dict(name=name, n=0)
    df = df.copy(); df["date"] = pd.to_datetime(df["entry_d"])
    df = df.sort_values("date").reset_index(drop=True)
    p = df["pnl"].values.astype(float)
    yrs = max((df["date"].max()-df["date"].min()).days/365.25, 0.5)
    eq = np.concatenate(([CAP0], CAP0 + p.cumsum()))
    peak = np.maximum.accumulate(eq); dd = (eq-peak)/peak
    ret = np.diff(eq) / eq[:-1]
    n_yr = len(p) / yrs
    return dict(name=name, n=len(p), tpy=round(n_yr,1),
                win_pct=round((p>0).mean()*100,1),
                avg_win=round(p[p>0].mean(),0) if (p>0).any() else 0,
                avg_loss=round(p[p<0].mean(),0) if (p<0).any() else 0,
                expect=round(p.mean(),0),
                total=round(p.sum(),0),
                final=round(eq[-1],0),
                cagr=round(((eq[-1]/CAP0)**(1/yrs)-1)*100,2),
                maxdd_pct=round(dd.min()*100,1),
                sharpe=round(ret.mean()/max(1e-9,ret.std())*np.sqrt(n_yr),2),
                pf=round(p[p>0].sum()/max(1,abs(p[p<0].sum())),2),
                worst=round(p.min(),0), best=round(p.max(),0)), eq

t0 = time.time()
n_bear_days = int(daily["bear"].sum())
print(f"Bearish regime days (close < 20DMA AND < 50DMA): {n_bear_days}/{len(daily)} ({n_bear_days/len(daily)*100:.1f}%)")

variants = [
    ("1.0 sigma · hold to expiry", 1.0, False),
    ("0.5 sigma · hold to expiry", 0.5, False),
    ("1.5 sigma · hold to expiry", 1.5, False),
    ("1.0 sigma · early exit Wed", 1.0, True),
]

res = []; eqs = {}
for name, sm, ee in variants:
    df = run(sm, ee)
    if len(df) == 0:
        print(f"{name}: no trades")
        continue
    st, eq = stats(df, name)
    res.append(st); eqs[name] = eq
    print(f"\n{name}: n={st['n']}, tpy={st['tpy']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, total=Rs.{st['total']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, worst=Rs.{st['worst']}, best=Rs.{st['best']}")
    df.to_csv(OUT / f"downtrend_put_{name.split()[0]}_{'wed' if ee else 'exp'}.csv", index=False)

# yearly for base variant
if variants and len(res) > 0:
    df_base = run(1.0, False); df_base["year"] = pd.to_datetime(df_base["entry_d"]).dt.year
    print("\n=== 1.0-sigma hold-to-expiry YEARLY ===")
    print(df_base.groupby("year").agg(n=("pnl","size"), pnl=("pnl","sum"),
                                       win=("pnl", lambda x: round((x>0).mean()*100,1)),
                                       best=("pnl","max"), worst=("pnl","min")).round(0).to_string())

sdf = pd.DataFrame(res).set_index("name")
sdf.to_csv(OUT / "downtrend_put_buy_summary.csv")
print("\n=== SUMMARY ===")
print(sdf[["n","tpy","win_pct","expect","total","cagr","maxdd_pct","sharpe","pf","worst","best"]].to_string())

fig, ax = plt.subplots(figsize=(13,7))
colors = ['#26a69a','#4dd0e1','#ffd54f','#ba68c8']
for i, (name, eq) in enumerate(eqs.items()):
    st = next(r for r in res if r["name"] == name)
    ax.plot(eq, label=f'{name}: n={st["n"]}, Sharpe {st["sharpe"]}, total Rs.{st["total"]:,}, best Rs.{st["best"]:,}',
            color=colors[i], lw=1.4)
ax.axhline(CAP0, color='#787b86', ls='--', alpha=0.5)
ax.set_ylabel('Equity (Rs.)'); ax.set_xlabel('Trade #')
ax.legend(fontsize=9, loc='best'); ax.grid(alpha=0.3)
ax.set_title('BUY 1-sigma PE when Nifty < 20DMA AND < 50DMA (bear regime) - weekly Mon->expiry, real costs')
plt.tight_layout(); plt.savefig(OUT / "downtrend_put_buy.png", dpi=110)
print(f"\nchart -> downtrend_put_buy.png")
print(f"runtime: {time.time()-t0:.0f}s")
