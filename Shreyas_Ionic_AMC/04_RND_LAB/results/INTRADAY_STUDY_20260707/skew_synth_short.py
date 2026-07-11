"""Expiry-day skew-fade: when ATM CE/PE ratio is skewed, take FUT + short-option in the
richer side's direction (put-call parity synthetic-short).

Rule:
  On 0DTE at ENTRY_HM (09:30 by default):
    r = CE_ATM / PE_ATM
    r < 0.80  -> PE overpriced (bearish skew) -> SHORT FUT + SHORT ATM PE
    r > 1.20  -> CE overpriced (bullish skew) -> LONG FUT + SHORT ATM CE
  Hold to 15:20 (close via market). Fut is proxied by SPOT (basis on 0DTE ~ Rs.5-15).

Real costs on option leg (STT/exch/GST/stamp/slippage half-spread).
Fut leg: brokerage Rs.40 R/T + STT 0.02% sell + exch 0.002% both + GST + stamp.

Sensitivity variants: also try thresholds (0.70/1.30) and (0.90/1.10).
"""
import sys, time
from pathlib import Path
from datetime import date
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(__file__).parent
LOT = 65
CAP = 1_000_000
OPEN_HM = 555; ENTRY_HM = 570; EXIT_HM = 920  # 15:20

def opt_cost(entry, exit):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503 * turn
    ipft = 5e-6 * turn; sebi = 1e-6 * turn
    stt  = 0.001 * entry * LOT  # sell open
    stamp = 3e-5 * exit * LOT   # buy close
    gst  = 0.18 * (brok + ex_txn + ipft + sebi)
    hs   = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + hs

def fut_cost(entry, exit):
    if entry is None or exit is None: return None
    brok = 40
    turn = (entry + exit) * LOT
    ex_txn = 0.00002 * turn      # fut lower
    ipft = 5e-6 * turn; sebi = 1e-6 * turn
    stt  = 0.0002 * entry * LOT  # sell side only, fut STT 0.02%
    stamp = 2e-5 * entry * LOT   # 0.002% on buy — approximation
    gst  = 0.18 * (brok + ex_txn + ipft + sebi)
    # slippage — NIFTY fut liquid, ~0.25 pt each side
    slip = 0.5 * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + slip

def opt_sell_pnl(entry, exit):
    if entry is None or exit is None or entry <= 0.05: return None
    c = opt_cost(entry, exit)
    if c is None: return None
    return (entry - exit) * LOT - c

def fut_pnl(entry, exit, direction):
    """direction: 'S' short (profit if exit<entry) or 'B' long."""
    if entry is None or exit is None: return None
    c = fut_cost(entry, exit)
    gross = (entry - exit) * LOT if direction == "S" else (exit - entry) * LOT
    return gross - c

# ---- load spot ----
s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}

expiries = list(dl.expiries())

opt_cache = {}
def get_chain(d, ex):
    k = (d, ex)
    if k not in opt_cache:
        if len(opt_cache) > 50:
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

# Expiry days = days that ARE an expiry
expiry_days = [e for e in expiries if e in set(days_all)]
print(f"expiry days in data: {len(expiry_days)}")

def backtest(lo=0.80, hi=1.20, entry_hm=ENTRY_HM, exit_hm=EXIT_HM):
    trades = []
    for d in expiry_days:
        arr = by_day.get(d)
        if arr is None or len(arr) < 300: continue
        ch = get_chain(d, d)   # expiry file for the expiry day = same date
        if ch is None: continue
        sp0 = spot_at(d, entry_hm)
        sp1 = spot_at(d, exit_hm)
        if sp0 is None or sp1 is None: continue
        atm = int(round(sp0 / 50) * 50)
        ce0 = opt_px(ch, entry_hm, atm, "CE")
        pe0 = opt_px(ch, entry_hm, atm, "PE")
        if ce0 is None or pe0 is None or ce0 < 1 or pe0 < 1: continue
        r = ce0 / pe0
        # skip near neutral
        if lo <= r <= hi: continue
        if r < lo:
            # PE overpriced -> bearish -> short fut + short PE
            fut_dir = "S"; opt_cp = "PE"; opt_e = pe0
        else:
            # CE overpriced -> bullish -> long fut + short CE
            fut_dir = "B"; opt_cp = "CE"; opt_e = ce0
        opt_x = opt_px(ch, exit_hm, atm, opt_cp)
        if opt_x is None: continue
        fp = fut_pnl(sp0, sp1, fut_dir)
        op = opt_sell_pnl(opt_e, opt_x)
        if fp is None or op is None: continue
        trades.append(dict(
            d=str(d), atm=atm, ratio=round(r, 3),
            spot_entry=round(sp0,2), spot_exit=round(sp1,2),
            fut_dir=fut_dir, opt_cp=opt_cp,
            opt_entry=opt_e, opt_exit=opt_x,
            fut_pnl=round(fp,0), opt_pnl=round(op,0),
            total_pnl=round(fp + op, 0),
        ))
    return trades

def stats(trades, name):
    if not trades: return dict(name=name, n=0)
    df = pd.DataFrame(trades)
    df["date"] = pd.to_datetime(df["d"])
    df = df.sort_values("date").reset_index(drop=True)
    p = df["total_pnl"].values
    span = (df["date"].max() - df["date"].min()).days
    yrs = max(span / 365.25, 0.5)
    eq = np.concatenate(([CAP], CAP + p.cumsum()))
    peak = np.maximum.accumulate(eq); dd = eq - peak; ddp = dd / peak
    dret = pd.Series(p / CAP, index=df["date"])
    return dict(
        name=name, n=len(p), tpy=round(len(p)/yrs, 1),
        win_pct=round((p>0).mean()*100, 1),
        avg_win=round(p[p>0].mean(), 0) if (p>0).any() else 0,
        avg_loss=round(p[p<0].mean(), 0) if (p<0).any() else 0,
        expect=round(p.mean(), 0),
        total_pnl=round(p.sum(), 0),
        final=round(eq[-1], 0),
        ret_pct=round((eq[-1]-CAP)/CAP*100, 1),
        cagr=round(((eq[-1]/CAP)**(1/yrs) - 1)*100, 1),
        maxdd_pct=round(ddp.min()*100, 1),
        sharpe=round(dret.mean()/max(1e-9, dret.std())*np.sqrt(252), 2),
        pf=round(p[p>0].sum()/max(1, abs(p[p<0].sum())), 2),
        best=round(p.max(), 0), worst=round(p.min(), 0),
    ), df, eq

t0 = time.time()
# main variants
variants = [
    ("Base (0.80/1.20)", 0.80, 1.20),
    ("Tighter (0.90/1.10)", 0.90, 1.10),
    ("Wider (0.70/1.30)", 0.70, 1.30),
]
results = []
allrun = {}
for name, lo, hi in variants:
    print(f"\n--- {name} ---")
    tr = backtest(lo=lo, hi=hi)
    if not tr:
        print(f"  no trades"); continue
    st, df, eq = stats(tr, name)
    print(f"  n={st['n']} · win={st['win_pct']}% · expect=Rs.{st['expect']} · Sharpe={st['sharpe']} · CAGR={st['cagr']}% · maxDD={st['maxdd_pct']}% · PF={st['pf']}")
    results.append(st); allrun[name] = (df, eq)
    df.to_csv(OUT / f"skew_synth_{name.split()[0].lower()}.csv", index=False)

print("\n=== SUMMARY ===")
print(pd.DataFrame(results).set_index("name").T.to_string())
pd.DataFrame(results).to_csv(OUT / "skew_synth_summary.csv", index=False)

# Base variant deep dive
if "Base (0.80/1.20)" in allrun:
    df, _ = allrun["Base (0.80/1.20)"]
    print("\nBASE: split by direction taken")
    def by_dir(g):
        p = g["total_pnl"]
        return pd.Series(dict(n=len(g), win=round((p>0).mean()*100,1),
                              expect=round(p.mean(),0), total=round(p.sum(),0),
                              fut=round(g["fut_pnl"].mean(),0), opt=round(g["opt_pnl"].mean(),0)))
    print(df.groupby(["fut_dir","opt_cp"]).apply(by_dir, include_groups=False).to_string())
    print("\nBASE: yearly")
    df["year"] = df["date"].dt.year
    yr = df.groupby("year").agg(n=("total_pnl","size"),
                                 pnl=("total_pnl","sum"),
                                 win_pct=("total_pnl", lambda x: round((x>0).mean()*100,1))).round(0)
    print(yr.to_string())

# Chart the three variants
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios":[3,1]})
colors = ['#2962ff', '#26a69a', '#ff9800']
for i, (name, (_, eq)) in enumerate(allrun.items()):
    st = next(r for r in results if r["name"] == name)
    ax1.plot(eq, label=f'{name}: n={st["n"]}, final Rs.{st["final"]/1e5:.2f}L, Sharpe {st["sharpe"]}, maxDD {st["maxdd_pct"]}%',
             color=colors[i], lw=1.4)
    peak = np.maximum.accumulate(eq); dd = (eq - peak)/peak*100
    ax2.fill_between(range(len(dd)), dd, 0, color=colors[i], alpha=0.3, label=f'{name} DD%')
ax1.axhline(CAP, color='#787b86', ls='--', alpha=0.5, label='Rs.10L baseline')
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(loc='upper left', fontsize=9); ax1.grid(alpha=0.3)
ax1.set_title('Expiry-day skew-fade: SHORT FUT + SHORT PE (bearish skew) or LONG FUT + SHORT CE (bullish skew) - hold 09:30->15:20')
ax2.set_ylabel('Drawdown %'); ax2.set_xlabel('Trade #'); ax2.legend(fontsize=9); ax2.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(OUT / "skew_synth_equity.png", dpi=110)
print(f"\nchart -> {OUT}/skew_synth_equity.png")
print(f"runtime: {time.time()-t0:.0f}s")
