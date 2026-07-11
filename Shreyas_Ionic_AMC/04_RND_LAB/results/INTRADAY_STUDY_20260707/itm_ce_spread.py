"""BUY 1% ITM CE + SELL ATM CE (bull call spread, deeper long leg).
Filter: Nifty > 20DMA (V1) or Nifty > 50DMA (V2) — bullish trend regime.
Entry: Monday 09:30. Weekly expiry (4-7 DTE). Hold to expiry.
Width = ~1% of spot = ~250 pts = ~Rs.16,250/lot max.

Also compare vs:
  V3: naked BUY ATM CE (baseline directional bet)
  V4: naked BUY 1% OTM CE (further OTM)
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
ENTRY_HM = 570; SETTLE_START = 900

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
daily["sma50"] = daily["close"].rolling(50).mean()
daily["above_20dma"] = daily["close"] > daily["sma20"]
daily["above_50dma"] = daily["close"] > daily["sma50"]
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
    if arr is None: return None
    idx = np.searchsorted(arr[:,0], hm)
    if 0 <= idx < len(arr): return float(arr[idx, 4])
    return float(arr[-1, 4])

def expiry_settle(exp):
    arr = by_day.get(exp)
    if arr is None: return None
    tail = arr[(arr[:,0] >= SETTLE_START) & (arr[:,0] <= 929)]
    return float(tail[:,4].mean()) if len(tail) >= 5 else None

# ==========================================================
# Strategies
# ==========================================================
def bull_call_spread(filter_col="above_20dma", itm_pct=0.01):
    """BUY (1-itm_pct)*spot CE + SELL ATM CE. Hold to expiry."""
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue
        if not bool(daily.iloc[i-1][filter_col]): continue
        later = [e for e in expiries if (e - d).days in range(4, 10)]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        K_long = int(round(sp * (1 - itm_pct) / 50) * 50)   # ITM
        K_short = int(round(sp / 50) * 50)                   # ATM
        if K_long >= K_short: continue  # ensure spread structure
        ch = get_chain(d, ex)
        long_e = opt_px(ch, ENTRY_HM, K_long, "CE")
        short_e = opt_px(ch, ENTRY_HM, K_short, "CE")
        if long_e is None or short_e is None or long_e < 1: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        long_x = max(0.0, settle - K_long)
        short_x = max(0.0, settle - K_short)
        p_long = leg_pnl("B", long_e, long_x)
        p_short = leg_pnl("S", short_e, short_x)
        if p_long is None or p_short is None: continue
        debit = (long_e - short_e) * LOT
        width = (K_short - K_long) * LOT
        max_gain = width - debit
        pnl = p_long + p_short
        trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                           K_long=K_long, K_short=K_short, spot_entry=sp,
                           settle=round(settle,1),
                           long_e=long_e, short_e=short_e,
                           long_x=round(long_x,2), short_x=round(short_x,2),
                           debit=round(debit,0), width=round(width,0),
                           max_gain=round(max_gain,0),
                           pnl=round(pnl, 0)))
    return pd.DataFrame(trades)

def naked_ce_buy(filter_col="above_20dma", moneyness=1.00):
    """BUY CE at moneyness*spot strike. Hold to expiry."""
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue
        if not bool(daily.iloc[i-1][filter_col]): continue
        later = [e for e in expiries if (e - d).days in range(4, 10)]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        K = int(round(sp * moneyness / 50) * 50)
        ch = get_chain(d, ex)
        px_e = opt_px(ch, ENTRY_HM, K, "CE")
        if px_e is None or px_e < 1: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        px_x = max(0.0, settle - K)
        pnl = leg_pnl("B", px_e, px_x)
        if pnl is None: continue
        trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                           K=K, spot_entry=sp, settle=round(settle,1),
                           entry_px=px_e, exit_px=round(px_x,2),
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
    ("V1 · 1pct-ITM CE + ATM CE (bull spread) · Nifty>20DMA", "spread", "above_20dma", 0.01),
    ("V2 · 1pct-ITM CE + ATM CE (bull spread) · Nifty>50DMA", "spread", "above_50dma", 0.01),
    ("V3 · Naked BUY ATM CE · Nifty>20DMA (baseline)",         "naked",  "above_20dma", 1.00),
    ("V4 · Naked BUY 1pct-OTM CE · Nifty>20DMA",                "naked",  "above_20dma", 1.01),
    ("V5 · Naked BUY 1pct-ITM CE · Nifty>20DMA",                "naked",  "above_20dma", 0.99),
    ("V6 · 2pct-ITM + ATM (wider spread) · Nifty>20DMA",        "spread", "above_20dma", 0.02),
]

res = []; eqs = {}
for name, kind, fcol, param in variants:
    print(f"\n{name} ...")
    if kind == "spread":
        df = bull_call_spread(filter_col=fcol, itm_pct=param)
    else:
        df = naked_ce_buy(filter_col=fcol, moneyness=param)
    if len(df) == 0:
        print(f"  no trades"); continue
    st, eq = stats(df, name)
    res.append(st); eqs[name] = eq
    print(f"  n={st['n']}, tpy={st['tpy']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, total=Rs.{st['total']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, worst=Rs.{st['worst']}, best=Rs.{st['best']}")
    tag = name.split("·")[0].strip().replace(" ", "_")
    df.to_csv(OUT / f"itm_ce_{tag}.csv", index=False)

sdf = pd.DataFrame(res).set_index("name")
sdf.to_csv(OUT / "itm_ce_spread_summary.csv")
print("\n=== SUMMARY ===")
print(sdf[["n","tpy","win_pct","expect","total","cagr","maxdd_pct","sharpe","pf","worst","best"]].to_string())

# yearly for the best spread variant
best = max(res, key=lambda r: r["sharpe"]) if res else None
if best:
    print(f"\n=== YEARLY for BEST: {best['name']} ===")
    df_best = bull_call_spread(filter_col="above_20dma", itm_pct=0.01) if "20DMA" in best['name'] and "V1" in best['name'] else None
    if df_best is not None:
        df_best["date"] = pd.to_datetime(df_best["entry_d"]); df_best["year"] = df_best["date"].dt.year
        print(df_best.groupby("year").agg(n=("pnl","size"), pnl=("pnl","sum"), win=("pnl", lambda x: round((x>0).mean()*100,1))).round(0).to_string())

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), gridspec_kw={"height_ratios":[3,1]})
colors = ['#26a69a','#4dd0e1','#787b86','#ff8f8f','#ba68c8','#ffd54f']
for i, (name, eq) in enumerate(eqs.items()):
    st = next(r for r in res if r["name"] == name)
    ax1.plot(eq, label=f'{name}: n={st["n"]}, Sharpe {st["sharpe"]}, CAGR {st["cagr"]}%, total Rs.{st["total"]:,}',
             color=colors[i%len(colors)], lw=1.3)
    peak = np.maximum.accumulate(eq); dd = (eq-peak)/peak*100
    ax2.fill_between(range(len(dd)), dd, 0, color=colors[i%len(colors)], alpha=0.2)
ax1.axhline(CAP0, color='#787b86', ls='--', alpha=0.5)
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(fontsize=8, loc='best'); ax1.grid(alpha=0.3)
ax1.set_title('BUY ITM CE + SELL ATM CE (bull call spread) vs naked CE buys - weekly Monday, real costs')
ax2.set_ylabel('DD %'); ax2.set_xlabel('Trade #'); ax2.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "itm_ce_spread.png", dpi=110)
print(f"\nchart -> itm_ce_spread.png")
print(f"runtime: {time.time()-t0:.0f}s")
