"""Medium-hold strategies: 12-16 DTE biweekly, entry Monday 09:30, hold to expiry (10-15 day median hold).

Strategies:
  A) SELL 3% OTM PE biweekly (Nifty > 20DMA filter) — winner scaled to longer DTE
  B) SELL 3% OTM PE + BUY 5% OTM PE biweekly (bull put spread, Nifty > 20DMA)
  C) SELL 3% OTM strangle biweekly (SELL 3% OTM CE + SELL 3% OTM PE, no direction filter)
  D) SELL iron condor biweekly (SELL 3% OTM both + BUY 5% OTM both — defined risk)

Real costs. Rs.1cr / 1 lot per unit. Weekly Monday entries.
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
DTE_MIN, DTE_MAX = 8, 18  # medium hold ~10-15 day sweet spot

def leg_cost(entry, exit, is_sell):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 20
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    stt = 0.001*(entry if is_sell else exit)*LOT
    stamp = 3e-5*(exit if is_sell else entry)*LOT
    gst = 0.18*(brok*2 + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok*2 + stt + ex_txn + ipft + sebi + stamp + gst + hs

def leg_pnl(side, entry, exit):
    c = leg_cost(entry, exit, side == "S")
    if c is None: return None
    gross = (exit - entry) * LOT if side == "B" else (entry - exit) * LOT
    return gross - c

s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(close=("close","last")).reset_index()
daily["sma20"] = daily["close"].rolling(20).mean()
daily["above_20dma"] = daily["close"] > daily["sma20"]
daily = daily.dropna(subset=["sma20"]).reset_index(drop=True)

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

# ==========================================================
def biweekly_pe_sell(bull_only=True, hedge_pct=None):
    """SELL 3% OTM PE biweekly. If hedge_pct set, BUY PE hedge_pct further OTM (bull put spread)."""
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue
        if bull_only and not bool(daily.iloc[i-1]["above_20dma"]): continue
        later = [e for e in expiries if DTE_MIN <= (e - d).days <= DTE_MAX]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        K_short = int(round(sp * 0.97 / 50) * 50)  # 3% OTM PE
        ch = get_chain(d, ex)
        short_e = opt_px(ch, ENTRY_HM, K_short, "PE")
        if short_e is None or short_e < 1: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        short_x = max(0.0, K_short - settle)
        p_short = leg_pnl("S", short_e, short_x)
        if p_short is None: continue
        if hedge_pct:
            K_long = int(round(sp * (1 - hedge_pct) / 50) * 50)
            long_e = opt_px(ch, ENTRY_HM, K_long, "PE")
            long_x = max(0.0, K_long - settle)
            if long_e is None or long_e < 0.3: continue
            p_long = leg_pnl("B", long_e, long_x)
            if p_long is None: continue
            pnl = p_short + p_long
            trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                               K_short=K_short, K_long=K_long,
                               short_e=short_e, long_e=long_e,
                               short_x=round(short_x,2), long_x=round(long_x,2),
                               credit=round((short_e-long_e)*LOT, 0),
                               pnl=round(pnl, 0)))
        else:
            trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                               K=K_short, entry_px=short_e, exit_px=round(short_x,2),
                               credit=round(short_e*LOT, 0),
                               pnl=round(p_short, 0)))
    return pd.DataFrame(trades)

def biweekly_strangle_sell(bull_only=False, hedge_pct=None):
    """SELL 3% OTM strangle biweekly. If hedge_pct set, BUY hedge_pct OTM both sides (iron condor)."""
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue
        if bull_only and not bool(daily.iloc[i-1]["above_20dma"]): continue
        later = [e for e in expiries if DTE_MIN <= (e - d).days <= DTE_MAX]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        K_short_pe = int(round(sp * 0.97 / 50) * 50)
        K_short_ce = int(round(sp * 1.03 / 50) * 50)
        ch = get_chain(d, ex)
        pe_e = opt_px(ch, ENTRY_HM, K_short_pe, "PE")
        ce_e = opt_px(ch, ENTRY_HM, K_short_ce, "CE")
        if pe_e is None or ce_e is None or pe_e < 1 or ce_e < 1: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        pe_x = max(0.0, K_short_pe - settle)
        ce_x = max(0.0, settle - K_short_ce)
        p_pe = leg_pnl("S", pe_e, pe_x)
        p_ce = leg_pnl("S", ce_e, ce_x)
        if p_pe is None or p_ce is None: continue
        row = dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                   K_pe=K_short_pe, K_ce=K_short_ce,
                   pe_e=pe_e, ce_e=ce_e, pe_x=round(pe_x,2), ce_x=round(ce_x,2),
                   settle=round(settle,1),
                   pnl_naked=round(p_pe + p_ce, 0))
        if hedge_pct:
            K_long_pe = int(round(sp * (1 - hedge_pct) / 50) * 50)
            K_long_ce = int(round(sp * (1 + hedge_pct) / 50) * 50)
            long_pe_e = opt_px(ch, ENTRY_HM, K_long_pe, "PE")
            long_ce_e = opt_px(ch, ENTRY_HM, K_long_ce, "CE")
            if long_pe_e is None or long_ce_e is None or long_pe_e < 0.3 or long_ce_e < 0.3: continue
            long_pe_x = max(0.0, K_long_pe - settle)
            long_ce_x = max(0.0, settle - K_long_ce)
            p_long_pe = leg_pnl("B", long_pe_e, long_pe_x)
            p_long_ce = leg_pnl("B", long_ce_e, long_ce_x)
            if p_long_pe is None or p_long_ce is None: continue
            row["K_long_pe"] = K_long_pe; row["K_long_ce"] = K_long_ce
            row["credit"] = round((pe_e + ce_e - long_pe_e - long_ce_e)*LOT, 0)
            row["pnl"] = round(p_pe + p_ce + p_long_pe + p_long_ce, 0)
        else:
            row["credit"] = round((pe_e + ce_e)*LOT, 0)
            row["pnl"] = row["pnl_naked"]
        trades.append(row)
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
                avg_hold=round(df.get("dte", pd.Series([0])).mean(), 1),
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

variants = [
    ("A · Biweekly 3pct-OTM PE (Nifty>20DMA)",       lambda: biweekly_pe_sell(bull_only=True)),
    ("A' · Biweekly 3pct-OTM PE (no filter)",         lambda: biweekly_pe_sell(bull_only=False)),
    ("B · Biweekly bull-put spread (3pct SELL + 5pct BUY, Nifty>20DMA)", lambda: biweekly_pe_sell(bull_only=True, hedge_pct=0.05)),
    ("C · Biweekly 3pct strangle sell (no filter)",   lambda: biweekly_strangle_sell(bull_only=False)),
    ("C' · Biweekly 3pct strangle sell (Nifty>20DMA)",lambda: biweekly_strangle_sell(bull_only=True)),
    ("D · Biweekly iron condor (3pct short + 5pct long)", lambda: biweekly_strangle_sell(bull_only=False, hedge_pct=0.05)),
    ("D' · Biweekly IC + Nifty>20DMA filter",         lambda: biweekly_strangle_sell(bull_only=True, hedge_pct=0.05)),
]

res = []; eqs = {}
for name, fn in variants:
    print(f"\n{name} ...")
    df = fn()
    if len(df) == 0:
        print("  no trades"); continue
    st, eq = stats(df, name)
    res.append(st); eqs[name] = eq
    print(f"  n={st['n']}, avg_hold={st['avg_hold']}d, tpy={st['tpy']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, total=Rs.{st['total']}, Sharpe={st['sharpe']}, PF={st['pf']}, worst=Rs.{st['worst']}, best=Rs.{st['best']}")
    tag = name.split("·")[0].strip().replace(" ", "_").replace("'","p")
    df.to_csv(OUT / f"mh_{tag}.csv", index=False)

sdf = pd.DataFrame(res).set_index("name")
sdf.to_csv(OUT / "medium_hold_summary.csv")
print("\n=== SUMMARY ===")
print(sdf[["n","tpy","avg_hold","win_pct","expect","total","cagr","maxdd_pct","sharpe","pf","worst","best"]].to_string())

# yearly for best variant
best = max(res, key=lambda r: r["sharpe"]) if res else None
if best:
    print(f"\n=== YEARLY for BEST: {best['name']} ===")
    # find the df for this variant
    fn = dict(variants)[best["name"]]
    df_best = fn()
    df_best["year"] = pd.to_datetime(df_best["entry_d"]).dt.year
    print(df_best.groupby("year").agg(n=("pnl","size"), pnl=("pnl","sum"),
                                       win=("pnl", lambda x: round((x>0).mean()*100,1)),
                                       best=("pnl","max"), worst=("pnl","min")).round(0).to_string())

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios":[3,1]})
colors = ['#26a69a','#4dd0e1','#ffd54f','#ff9800','#ba68c8','#2962ff','#ef5350']
for i, (name, eq) in enumerate(eqs.items()):
    st = next(r for r in res if r["name"] == name)
    ax1.plot(eq, label=f'{name}: n={st["n"]}, Sharpe {st["sharpe"]}, PF {st["pf"]}, total Rs.{st["total"]:,}',
             color=colors[i%len(colors)], lw=1.3)
    peak = np.maximum.accumulate(eq); dd = (eq-peak)/peak*100
    ax2.fill_between(range(len(dd)), dd, 0, color=colors[i%len(colors)], alpha=0.25)
ax1.axhline(CAP0, color='#787b86', ls='--', alpha=0.5)
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(fontsize=8, loc='best'); ax1.grid(alpha=0.3)
ax1.set_title('Biweekly medium-hold (12-16 DTE, ~10-14 day hold) - 4 structures compared, real costs')
ax2.set_ylabel('DD %'); ax2.set_xlabel('Trade #'); ax2.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "medium_hold_book.png", dpi=110)
print(f"\nchart -> medium_hold_book.png")
print(f"runtime: {time.time()-t0:.0f}s")
