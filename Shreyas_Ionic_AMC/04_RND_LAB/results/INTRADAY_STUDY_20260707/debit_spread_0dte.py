"""0DTE debit spread — BUY ATM + SELL ATM+50 (bull call spread for CE, bear put spread for PE).
Two entry times (09:30 and 13:30) x two spreads (CE, PE) = 4 variants.
Hold to 15:20 close via option prices. Real costs on all 4 executions per round-trip.
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(__file__).parent
LOT = 65; CAP = 1_000_000
EXIT_HM = 920  # 15:20

def leg_cost(entry, exit, is_sell):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 20  # per leg, so ONE round-trip = 40; here we return per side
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503 * turn; ipft = 5e-6 * turn; sebi = 1e-6 * turn
    stt = 0.001 * (entry if is_sell else exit) * LOT
    stamp = 3e-5 * (exit if is_sell else entry) * LOT
    gst = 0.18 * (brok*2 + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok*2 + stt + ex_txn + ipft + sebi + stamp + gst + hs

def leg_pnl(side, entry, exit):
    if entry is None or exit is None: return None
    c = leg_cost(entry, exit, side == "S")
    if c is None: return None
    gross = (exit - entry) * LOT if side == "B" else (entry - exit) * LOT
    return gross - c

s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
expiries = list(dl.expiries())
expiry_days = [e for e in expiries if e in set(days_all)]

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

def backtest(spread, entry_hm):
    """spread: 'CE' (bull call spread) or 'PE' (bear put spread)."""
    trades = []
    for d in expiry_days:
        arr = by_day.get(d)
        if arr is None or len(arr) < 300: continue
        ch = get_chain(d, d)
        if ch is None: continue
        sp0 = spot_at(d, entry_hm)
        if sp0 is None: continue
        atm = int(round(sp0 / 50) * 50)
        # long leg = ATM, short leg = ATM+50 (CE) or ATM-50 (PE)
        long_K = atm
        short_K = atm + 50 if spread == "CE" else atm - 50
        long_e = opt_px(ch, entry_hm, long_K, spread)
        short_e = opt_px(ch, entry_hm, short_K, spread)
        if long_e is None or short_e is None or long_e < 1 or short_e < 0.5: continue
        long_x = opt_px(ch, EXIT_HM, long_K, spread)
        short_x = opt_px(ch, EXIT_HM, short_K, spread)
        if long_x is None or short_x is None: continue
        p_long = leg_pnl("B", long_e, long_x)
        p_short = leg_pnl("S", short_e, short_x)
        if p_long is None or p_short is None: continue
        debit = (long_e - short_e) * LOT   # net premium paid per lot pair
        trades.append(dict(
            d=str(d), atm=atm, spread=spread, entry_hm=entry_hm,
            long_e=long_e, short_e=short_e, long_x=long_x, short_x=short_x,
            spot_entry=round(sp0,2),
            debit=round(debit, 0),
            long_pnl=round(p_long,0), short_pnl=round(p_short,0),
            total_pnl=round(p_long + p_short, 0),
            max_win=round(50*LOT - debit, 0),
            max_loss=round(-debit, 0),
        ))
    return trades

def stats(trades, name):
    if not trades: return dict(name=name, n=0)
    df = pd.DataFrame(trades); df["date"] = pd.to_datetime(df["d"])
    df = df.sort_values("date").reset_index(drop=True)
    p = df["total_pnl"].values.astype(float)
    span = (df["date"].max() - df["date"].min()).days
    yrs = max(span/365.25, 0.5)
    eq = np.concatenate(([CAP], CAP + p.cumsum()))
    peak = np.maximum.accumulate(eq); dd = eq - peak; ddp = dd/peak
    dret = pd.Series(p/CAP)
    return dict(name=name, n=len(p), tpy=round(len(p)/yrs, 1),
                debit_med=round(df["debit"].median(), 0),
                win_pct=round((p>0).mean()*100, 1),
                avg_win=round(p[p>0].mean(),0) if (p>0).any() else 0,
                avg_loss=round(p[p<0].mean(),0) if (p<0).any() else 0,
                expect=round(p.mean(), 0),
                total_pnl=round(p.sum(), 0),
                final=round(eq[-1], 0),
                cagr=round(((eq[-1]/CAP)**(1/yrs) - 1)*100, 1),
                maxdd_pct=round(ddp.min()*100, 1),
                sharpe=round(dret.mean()/max(1e-9, dret.std())*np.sqrt(252), 2),
                pf=round(p[p>0].sum()/max(1, abs(p[p<0].sum())), 2),
                best=round(p.max(),0), worst=round(p.min(),0),
               ), df, eq

t0 = time.time()
variants = [
    ("CE spread 09:30 (bull call)", "CE", 570),
    ("CE spread 13:30 (bull call)", "CE", 810),
    ("PE spread 09:30 (bear put)", "PE", 570),
    ("PE spread 13:30 (bear put)", "PE", 810),
]
results = []; eqs = {}
for name, spread, hm in variants:
    print(f"\n--- {name} ---")
    tr = backtest(spread, hm)
    if not tr: print("  no trades"); continue
    st, df, eq = stats(tr, name)
    results.append(st); eqs[name] = eq
    print(f"  n={st['n']} · debit_med=Rs.{st['debit_med']} · win={st['win_pct']}% · expect=Rs.{st['expect']} · Sharpe={st['sharpe']} · CAGR={st['cagr']}% · maxDD={st['maxdd_pct']}% · PF={st['pf']}")
    df.to_csv(OUT / f"debit_{spread.lower()}_{hm}.csv", index=False)

sdf = pd.DataFrame(results).set_index("name")
print("\n=== SUMMARY ===")
print(sdf.T.to_string())
sdf.to_csv(OUT / "debit_spread_summary.csv")

# yearly for the best variant by Sharpe
best_name = sdf["sharpe"].idxmax() if len(sdf) else None
if best_name:
    spread = "CE" if "CE" in best_name else "PE"
    hm = 570 if "09:30" in best_name else 810
    df = pd.read_csv(OUT / f"debit_{spread.lower()}_{hm}.csv")
    df["date"] = pd.to_datetime(df["d"]); df["year"] = df["date"].dt.year
    print(f"\nBEST ({best_name}) yearly:")
    print(df.groupby("year").agg(n=("total_pnl","size"), pnl=("total_pnl","sum"),
                                  win_pct=("total_pnl", lambda x: round((x>0).mean()*100,1))).round(0))

# equity chart
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), gridspec_kw={"height_ratios":[3,1]})
colors = ['#26a69a','#4dd0e1','#ef5350','#ff8f8f']
for i, (name, eq) in enumerate(eqs.items()):
    st = next(r for r in results if r["name"] == name)
    ax1.plot(eq, label=f'{name}: n={st["n"]}, win {st["win_pct"]}%, Sharpe {st["sharpe"]}, CAGR {st["cagr"]}%', color=colors[i], lw=1.3)
    peak = np.maximum.accumulate(eq); dd = (eq-peak)/peak*100
    ax2.fill_between(range(len(dd)), dd, 0, color=colors[i], alpha=0.3)
ax1.axhline(CAP, color='#787b86', ls='--', alpha=0.5, label='Rs.10L baseline')
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(fontsize=8, loc='best'); ax1.grid(alpha=0.3)
ax1.set_title('0DTE debit spread - BUY ATM + SELL +/-50 - 2 entry times x CE (bull) & PE (bear)')
ax2.set_ylabel('DD %'); ax2.set_xlabel('Trade #'); ax2.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "debit_spread_equity.png", dpi=110)
print(f"\nchart -> {OUT}/debit_spread_equity.png")
print(f"runtime: {time.time()-t0:.0f}s")
