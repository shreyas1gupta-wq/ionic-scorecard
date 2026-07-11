"""Deep-OTM PE BUY as portfolio tail insurance.
Grid:
  - target delta: 0.1, 0.2 (moneyness proxy since delta not stored)
  - target DTE: 30, 60, 90 days
  - roll: at expiry, or at 10-DTE remaining
Rolling means: at close/roll trigger, close current PE, buy new PE on next-expiry at same target delta.
Real costs. 1 lot per position.

Moneyness proxy for target delta (using rough BS with IV=15pct):
  30-DTE: 0.1 delta -> K/S=0.92; 0.2 delta -> K/S=0.95
  60-DTE: 0.1 delta -> K/S=0.89; 0.2 delta -> K/S=0.93
  90-DTE: 0.1 delta -> K/S=0.86; 0.2 delta -> K/S=0.91
"""
import sys, time
from pathlib import Path
from datetime import date, timedelta
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INTRADAY_STUDY_20260707")
LOT = 65; CAP0 = 10_000_000
ENTRY_HM = 570

DELTA_MONEYNESS = {
    (30, 0.10): 0.92, (30, 0.20): 0.95,
    (60, 0.10): 0.89, (60, 0.20): 0.93,
    (90, 0.10): 0.86, (90, 0.20): 0.91,
}

def buy_cost(entry, exit):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    stt = 0.001 * exit * LOT
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
expiries = list(dl.expiries())
day_set = set(days_all)

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

def find_expiry_at_dte(d, target_dte, tol=7):
    candidates = [e for e in expiries if abs((e - d).days - target_dte) <= tol]
    if not candidates: return None
    return min(candidates, key=lambda e: abs((e-d).days - target_dte))

# ==========================================================
def run(target_delta, target_dte, roll_at_10dte=True):
    """Roll positions monthly. Each 'trade' = entry to close/roll."""
    trades = []
    d = days_all[0]
    end = days_all[-1]
    idx = 0
    while d <= end:
        # get target expiry
        ex = find_expiry_at_dte(d, target_dte)
        if ex is None:
            idx += 5;
            if idx >= len(days_all): break
            d = days_all[idx]; continue
        sp = spot_at(d, ENTRY_HM)
        if sp is None:
            idx += 1
            if idx >= len(days_all): break
            d = days_all[idx]; continue
        moneyness = DELTA_MONEYNESS.get((target_dte, target_delta))
        if moneyness is None:
            idx += 1
            if idx >= len(days_all): break
            d = days_all[idx]; continue
        K = int(round(sp * moneyness / 50) * 50)
        ch = get_chain(d, ex)
        px_e = opt_px(ch, ENTRY_HM, K, "PE")
        if px_e is None or px_e < 0.3:
            # try 50-pt shifts around target strike
            for shift in [50, -50, 100, -100]:
                K_try = K + shift
                px_try = opt_px(ch, ENTRY_HM, K_try, "PE")
                if px_try is not None and px_try >= 0.3:
                    K = K_try; px_e = px_try; break
        if px_e is None or px_e < 0.3:
            # Skip and try next month
            idx += 21
            if idx >= len(days_all): break
            d = days_all[idx]; continue
        # Roll trigger
        if roll_at_10dte:
            roll_target_dte = 10
            roll_day = None
            for cd in days_all:
                if cd <= d: continue
                if (ex - cd).days <= roll_target_dte:
                    roll_day = cd; break
            if roll_day is None: break
            # exit at roll_day 09:30
            roll_ch = get_chain(roll_day, ex)
            px_x = opt_px(roll_ch, ENTRY_HM, K, "PE")
            exit_reason = "ROLL_10DTE"
            next_d = roll_day
        else:
            settle = expiry_settle(ex)
            if settle is None:
                idx += 21
                if idx >= len(days_all): break
                d = days_all[idx]; continue
            px_x = max(0.0, K - settle)
            exit_reason = "EXPIRY"
            next_d = ex + timedelta(days=1)
            while next_d not in day_set and next_d < end:
                next_d = next_d + timedelta(days=1)
        if px_x is None:
            idx += 21
            if idx >= len(days_all): break
            d = days_all[idx]; continue
        pnl = buy_pnl(px_e, px_x)
        if pnl is None:
            idx += 21
            if idx >= len(days_all): break
            d = days_all[idx]; continue
        trades.append(dict(entry_d=str(d), exit_d=str(next_d), expiry=str(ex),
                           dte_entry=(ex-d).days, K=K, spot_entry=sp,
                           moneyness=round(K/sp,3),
                           entry_px=px_e, exit_px=round(px_x,2),
                           exit_reason=exit_reason,
                           pnl=round(pnl, 0)))
        # Advance to next_d
        if next_d not in day_set:
            # find next available day
            for cd in days_all:
                if cd > next_d - timedelta(days=1):
                    next_d = cd; break
        if next_d >= end: break
        idx = days_all.index(next_d) if next_d in day_set else idx + 1
        d = next_d
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
                avg_entry_prem=round(df["entry_px"].mean(),1),
                win_pct=round((p>0).mean()*100,1),
                expect=round(p.mean(),0),
                total=round(p.sum(),0),
                final=round(eq[-1],0),
                cagr=round(((eq[-1]/CAP0)**(1/yrs)-1)*100,2),
                maxdd_pct=round(dd.min()*100,1),
                sharpe=round(ret.mean()/max(1e-9,ret.std())*np.sqrt(n_yr),2),
                pf=round(p[p>0].sum()/max(1,abs(p[p<0].sum())),2),
                best=round(p.max(),0), worst=round(p.min(),0)), eq

t0 = time.time()
grid = [
    ("0.10-delta 30DTE roll@10", 0.10, 30, True),
    ("0.20-delta 30DTE roll@10", 0.20, 30, True),
    ("0.10-delta 60DTE roll@10", 0.10, 60, True),
    ("0.20-delta 60DTE roll@10", 0.20, 60, True),
    ("0.10-delta 90DTE roll@10", 0.10, 90, True),
    ("0.10-delta 30DTE hold-to-expiry", 0.10, 30, False),
    ("0.20-delta 30DTE hold-to-expiry", 0.20, 30, False),
]

res = []; eqs = {}
for name, delta, dte, roll in grid:
    print(f"\n{name} ...")
    df = run(delta, dte, roll)
    if len(df) == 0:
        print(f"  no trades"); continue
    st, eq = stats(df, name)
    res.append(st); eqs[name] = eq
    print(f"  n={st['n']}, tpy={st['tpy']}, avg_prem=Rs.{st['avg_entry_prem']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, total=Rs.{st['total']}, Sharpe={st['sharpe']}, best=Rs.{st['best']}, worst=Rs.{st['worst']}")
    tag = name.replace(" ", "_").replace(".","p")
    df.to_csv(OUT / f"tail_{tag}.csv", index=False)

# yearly for one variant
if res:
    print("\n=== 0.10-delta 30DTE roll@10 yearly ===")
    df1 = run(0.10, 30, True)
    if len(df1):
        df1["year"] = pd.to_datetime(df1["entry_d"]).dt.year
        yr = df1.groupby("year").agg(n=("pnl","size"), pnl=("pnl","sum"),
                                     win=("pnl", lambda x: round((x>0).mean()*100,1)),
                                     best=("pnl","max"), worst=("pnl","min")).round(0)
        print(yr.to_string())

sdf = pd.DataFrame(res).set_index("name")
sdf.to_csv(OUT / "tail_put_buy_summary.csv")
print("\n=== SUMMARY ===")
print(sdf[["n","tpy","avg_entry_prem","win_pct","expect","total","cagr","maxdd_pct","sharpe","pf","worst","best"]].to_string())

fig, ax = plt.subplots(figsize=(13,7))
colors = ['#26a69a','#4dd0e1','#ffd54f','#ff9800','#ba68c8','#787b86','#607d8b']
for i, (name, eq) in enumerate(eqs.items()):
    st = next(r for r in res if r["name"] == name)
    ax.plot(eq, label=f'{name}: n={st["n"]}, Sharpe {st["sharpe"]}, total Rs.{st["total"]:,}', color=colors[i], lw=1.3)
ax.axhline(CAP0, color='#787b86', ls='--', alpha=0.5)
ax.set_ylabel('Equity (Rs.)'); ax.set_xlabel('Trade #')
ax.legend(fontsize=8, loc='best'); ax.grid(alpha=0.3)
ax.set_title('Deep-OTM PE BUY (0.1 / 0.2 delta, 30-90 DTE) - portfolio tail insurance test')
plt.tight_layout(); plt.savefig(OUT / "tail_put_buy.png", dpi=110)
print(f"\nchart -> tail_put_buy.png")
print(f"runtime: {time.time()-t0:.0f}s")
