"""Improve the 3% OTM PE-sell winner: dynamic strikes, IV/VIX filters, conservative sizing.
Baseline: SELL 3% OTM PE weekly Monday when Nifty > 20DMA, hold to expiry.
Variants:
  V1: baseline (fixed 3% OTM, no VIX filter)
  V2: + VIX > 12 (skip ultra-low-vol days)
  V3: + VIX > 14
  V4: DYNAMIC 1-sigma OTM (strike = round((spot - straddle*1.25)/50)*50)
  V5: DYNAMIC 1.5-sigma OTM (safer)
  V6: DYNAMIC 1-sigma + VIX > 13
  V7: DYNAMIC 1-sigma + IV-scaled sizing (lots down when IV high)
Sizing baseline: 1 lot (comparable). V7 uses 1 lot at IV=15%, scales inversely with IV.
"""
import sys, time
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INTRADAY_STUDY_20260707")
LOT = 65; CAP0 = 10_000_000
ENTRY_HM = 570

def sell_cost(entry, exit):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    stt = 0.001 * entry * LOT
    stamp = 3e-5 * exit * LOT
    gst = 0.18*(brok + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + hs

def sell_pnl(e, x, lots=1):
    c = sell_cost(e, x)
    if c is None: return None
    return ((e - x) * LOT - c) * lots

s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(close=("close","last")).reset_index()
daily["sma20"] = daily["close"].rolling(20).mean()
daily["above_20dma"] = daily["close"] > daily["sma20"]
daily = daily.dropna(subset=["sma20"]).reset_index(drop=True)

# Load VIX daily
try:
    vix = pd.read_parquet(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\processed\vix_1min.parquet").reset_index()
    vix["d"] = pd.to_datetime(vix["dt"]).dt.date
    vix_daily = vix.groupby("d")["vix"].first()   # open-of-day VIX
    print(f"VIX loaded: {len(vix_daily)} days")
except Exception as e:
    print("VIX load failed:", e); vix_daily = {}

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
    if arr is None: return None
    idx = np.searchsorted(arr[:,0], hm)
    if 0 <= idx < len(arr): return float(arr[idx, 4])
    return float(arr[-1, 4])

def expiry_settle(exp):
    arr = by_day.get(exp)
    if arr is None: return None
    tail = arr[(arr[:,0] >= 900) & (arr[:,0] <= 929)]
    return float(tail[:,4].mean()) if len(tail) >= 5 else None

# ---- Generic runner ----
def run(strike_mode="fixed_3pct", sigma_mult=1.0, vix_min=None, size_mode="fixed"):
    """strike_mode: 'fixed_3pct' | 'sigma'; size_mode: 'fixed' | 'iv_scaled'"""
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue
        if not bool(daily.iloc[i-1]["above_20dma"]): continue
        # VIX filter (previous close)
        v = None
        try: v = float(vix_daily.get(d, np.nan))
        except: v = None
        if vix_min is not None and (v is None or np.isnan(v) or v < vix_min): continue
        later = [e for e in expiries if (e - d).days in range(4, 10)]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        atm = int(round(sp / 50) * 50)
        ch = get_chain(d, ex)
        # compute sigma from ATM straddle for dynamic
        ce_atm = opt_px(ch, ENTRY_HM, atm, "CE")
        pe_atm = opt_px(ch, ENTRY_HM, atm, "PE")
        if ce_atm is None or pe_atm is None: continue
        sigma_pts = (ce_atm + pe_atm) * 1.25  # BS approx
        iv_pct = sigma_pts / sp * 100          # rough per-week IV proxy in pct
        # target strike
        if strike_mode == "fixed_3pct":
            K = int(round(sp * 0.97 / 50) * 50)
        elif strike_mode == "sigma":
            K = int(round((sp - sigma_mult * sigma_pts) / 50) * 50)
        else:
            continue
        if K <= 0: continue
        px_e = opt_px(ch, ENTRY_HM, K, "PE")
        if px_e is None or px_e < 0.5: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        px_x = max(0.0, K - settle)
        # sizing
        if size_mode == "fixed":
            lots = 1
        elif size_mode == "iv_scaled":
            # target: 1 lot at IV=1.5%/week (typical), lots = 1.5/iv_pct
            lots = max(0.25, min(2.0, 1.5 / max(iv_pct, 0.5)))
        pnl = sell_pnl(px_e, px_x, lots=lots)
        if pnl is None: continue
        trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                           K=K, K_offset_pct=round((sp-K)/sp*100, 2),
                           spot_entry=sp, sigma_pts=round(sigma_pts,1),
                           iv_wk_pct=round(iv_pct,2), vix=v,
                           entry_px=px_e, exit_px=round(px_x,2),
                           lots=round(lots,2),
                           credit=round(px_e * LOT * lots, 0),
                           pnl=round(pnl, 0)))
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
                expect=round(p.mean(),0),
                total=round(p.sum(),0),
                final=round(eq[-1],0),
                cagr=round(((eq[-1]/CAP0)**(1/yrs)-1)*100,2),
                maxdd_pct=round(dd.min()*100,1),
                sharpe=round(ret.mean()/max(1e-9,ret.std())*np.sqrt(n_yr),2),
                pf=round(p[p>0].sum()/max(1,abs(p[p<0].sum())),2),
                avg_offset=round(df["K_offset_pct"].mean(),2),
                avg_iv=round(df["iv_wk_pct"].mean(),2),
                worst=round(p.min(),0), best=round(p.max(),0)), eq

t0 = time.time()

variants = [
    ("V1 · fixed 3pct OTM (baseline)", dict(strike_mode="fixed_3pct")),
    ("V2 · fixed 3pct OTM + VIX>12",   dict(strike_mode="fixed_3pct", vix_min=12)),
    ("V3 · fixed 3pct OTM + VIX>14",   dict(strike_mode="fixed_3pct", vix_min=14)),
    ("V4 · dynamic 1.0-sigma OTM",     dict(strike_mode="sigma", sigma_mult=1.0)),
    ("V5 · dynamic 1.5-sigma OTM",     dict(strike_mode="sigma", sigma_mult=1.5)),
    ("V6 · dynamic 1.0-sigma + VIX>13",dict(strike_mode="sigma", sigma_mult=1.0, vix_min=13)),
    ("V7 · dyn 1.0-sigma + IV-scaled sizing", dict(strike_mode="sigma", sigma_mult=1.0, size_mode="iv_scaled")),
]

res = []; eqs = {}
for name, kw in variants:
    df = run(**kw)
    if len(df) == 0:
        print(f"{name}: no trades"); continue
    st, eq = stats(df, name)
    res.append(st); eqs[name] = eq
    print(f"\n{name}: n={st['n']}, tpy={st['tpy']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, total=Rs.{st['total']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, DD={st['maxdd_pct']}%, worst=Rs.{st['worst']}, avg_offset={st['avg_offset']}%, avg_iv={st['avg_iv']}%")
    tag = name.split("·")[0].strip().replace(" ", "_")
    df.to_csv(OUT / f"filt_{tag}.csv", index=False)

sdf = pd.DataFrame(res).set_index("name")
sdf.to_csv(OUT / "filter_search_summary.csv")
print("\n=== SUMMARY ===")
print(sdf[["n","tpy","win_pct","expect","total","cagr","maxdd_pct","sharpe","pf","avg_offset","avg_iv","worst","best"]].to_string())

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios":[3,1]})
colors = ['#787b86','#4dd0e1','#26a69a','#ffd54f','#ff9800','#ba68c8','#2962ff']
for i, (name, eq) in enumerate(eqs.items()):
    st = next(r for r in res if r["name"] == name)
    ax1.plot(eq, label=f'{name}: n={st["n"]}, Sharpe {st["sharpe"]}, PF {st["pf"]}, total Rs.{st["total"]:,}', color=colors[i], lw=1.4)
    peak = np.maximum.accumulate(eq); dd = (eq-peak)/peak*100
    ax2.fill_between(range(len(dd)), dd, 0, color=colors[i], alpha=0.25)
ax1.axhline(CAP0, color='#787b86', ls='--', alpha=0.5)
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(fontsize=8, loc='best'); ax1.grid(alpha=0.3)
ax1.set_title('SELL far-OTM PE (Nifty > 20DMA) - filter/sizing search')
ax2.set_ylabel('DD %'); ax2.set_xlabel('Trade #'); ax2.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "filter_search.png", dpi=110)
print(f"\nchart -> filter_search.png")
print(f"runtime: {time.time()-t0:.0f}s")
