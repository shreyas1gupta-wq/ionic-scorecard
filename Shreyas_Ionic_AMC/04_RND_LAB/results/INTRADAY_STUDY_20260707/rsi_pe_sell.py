"""Strategy: SELL 200-OTM PE when NIFTY>20DMA, book/skip when RSI14>80 AND RSI5>90.
Two variants: weekly (front) vs biweekly (next weekly).
1 lot / trade, real costs (brokerage+STT+txn+GST+stamp+slippage), sequential.
Causal: daily indicators computed at D's close -> action at D+1 09:30.
"""
import sys, time
from pathlib import Path
from datetime import date, timedelta
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
OPEN_HM = 555     # 09:15
ENTRY_HM = 570    # 09:30 (round-trip entry/exit)
EOD_HM = 924      # 15:24
SETTLE_START = 900  # 15:00 for 30-min avg

def rsi(close, period):
    d = close.diff()
    u = d.clip(lower=0); dn = -d.clip(upper=0)
    au = u.ewm(alpha=1/period, adjust=False).mean()
    ad = dn.ewm(alpha=1/period, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return 100 - 100/(1+rs)

def real_cost(entry, exit):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40
    turnover = (entry + exit) * LOT
    ex_txn = 0.0003503 * turnover
    ipft = 0.000005 * turnover
    sebi = 0.000001 * turnover
    stt  = 0.001 * entry * LOT
    stamp = 0.00003 * exit * LOT
    gst  = 0.18 * (brok + ex_txn + ipft + sebi)
    hs_e = max(0.10, 0.001 * entry)
    hs_x = max(0.10, 0.001 * exit)
    slip = (hs_e + hs_x) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + slip

def sell_pnl(entry, exit):
    if entry is None or exit is None: return None
    c = real_cost(entry, exit)
    if c is None: return None
    return (entry - exit) * LOT - c

# ---- load spot + daily ----
s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(close=("close","last")).reset_index()
daily["sma20"] = daily["close"].rolling(20).mean()
daily["rsi14"] = rsi(daily["close"], 14)
daily["rsi5"]  = rsi(daily["close"], 5)
daily["above_20dma"] = daily["close"] > daily["sma20"]
daily["ob"] = (daily["rsi14"] > 80) & (daily["rsi5"] > 90)  # overbought trigger
daily = daily.dropna(subset=["sma20","rsi14","rsi5"]).reset_index(drop=True)
d_idx = {d: i for i, d in enumerate(daily["d"])}

expiries = list(dl.expiries())
def target_expiry(d, kind):
    """kind: 'w'=next weekly (dte>=1), 'b'=one after that."""
    later = [e for e in expiries if (e - d).days >= 1]
    if kind == "w":
        return later[0] if later else None
    else:
        return later[1] if len(later) > 1 else None

opt_cache = {}
def get_chain(d, ex):
    k = (d, ex)
    if k not in opt_cache:
        try: opt_cache[k] = dl.load_option_day(ex, d)
        except Exception: opt_cache[k] = None
    return opt_cache[k]

def opt_price(chain, hm, K, cp, back=15, fwd=15):
    if chain is None: return None
    for b in range(back+1):
        row = chain["minute_index"].get(hm - b, {}).get((int(K), cp))
        if row: return row["c"]
    for f in range(1, fwd+1):
        row = chain["minute_index"].get(hm + f, {}).get((int(K), cp))
        if row: return row["c"]
    return None

def spot_at(d, hm, back=10, fwd=10):
    arr = by_day.get(d)
    if arr is None or len(arr) == 0: return None
    idx = np.searchsorted(arr[:,0], hm)
    if 0 <= idx < len(arr) and abs(int(arr[idx,0]) - hm) <= back:
        return float(arr[idx, 4])
    if idx > 0 and abs(int(arr[idx-1,0]) - hm) <= back:
        return float(arr[idx-1, 4])
    return None

def expiry_settle(exp):
    """30-min-avg spot close on expiry day, 15:00-15:29."""
    arr = by_day.get(exp)
    if arr is None or len(arr) == 0: return None
    tail = arr[(arr[:,0] >= SETTLE_START) & (arr[:,0] <= EOD_HM+5)]
    if len(tail) < 5: return None
    return float(tail[:,4].mean())

def run_backtest(kind):
    """kind: 'w' or 'b'. Returns trades list + equity array."""
    trades = []
    eq = [CAP]
    pos = None  # dict(K, expiry, entry_day, entry_hm, entry_px)
    for i in range(1, len(daily)):
        # signal date = i-1 (yesterday's close); action date = i today at 09:30
        d = daily.iloc[i]["d"]
        yd = daily.iloc[i-1]
        # ---- EXIT LOGIC (before entry) ----
        if pos is not None:
            close_reason = None; exit_px = None
            # A) expiry day today -> settle
            if d == pos["expiry"]:
                settle = expiry_settle(d)
                if settle is not None:
                    exit_px = max(0.0, pos["K"] - settle)
                    close_reason = "EXPIRY"
            # B) RSI trigger fired at close of previous day -> close at today's 09:30
            elif bool(yd["ob"]):
                ch = get_chain(d, pos["expiry"])
                exit_px = opt_price(ch, ENTRY_HM, pos["K"], "PE")
                if exit_px is not None:
                    close_reason = "RSI_BOOK"
            # C) safety: expiry passed while position held (shouldn't happen with weekly overlap)
            elif d > pos["expiry"]:
                settle = expiry_settle(pos["expiry"])
                if settle is not None:
                    exit_px = max(0.0, pos["K"] - settle)
                    close_reason = "EXPIRY_LATE"
            if close_reason:
                pnl = sell_pnl(pos["entry_px"], exit_px)
                trades.append(dict(
                    entry_d=str(pos["entry_day"]), exit_d=str(d),
                    K=pos["K"], expiry=str(pos["expiry"]),
                    entry_px=round(pos["entry_px"], 2),
                    exit_px=round(exit_px, 2) if exit_px is not None else None,
                    days_held=(d - pos["entry_day"]).days,
                    reason=close_reason, pnl=round(pnl, 0) if pnl is not None else None,
                ))
                if pnl is not None: eq.append(eq[-1] + pnl)
                pos = None
        # ---- ENTRY LOGIC ----
        if pos is None:
            if bool(yd["above_20dma"]) and not bool(yd["ob"]):
                ex = target_expiry(d, kind)
                if ex is None: continue
                dte = (ex - d).days
                if dte < 1 or dte > 15: continue
                ch = get_chain(d, ex)
                sp = spot_at(d, ENTRY_HM)
                if ch is None or sp is None: continue
                K = int(round((sp - 200) / 50) * 50)
                px = opt_price(ch, ENTRY_HM, K, "PE")
                if px is None or px < 1: continue
                pos = dict(K=K, expiry=ex, entry_day=d, entry_hm=ENTRY_HM, entry_px=px)
    return trades, np.array(eq)

t0 = time.time()
print("running WEEKLY..."); w_tr, w_eq = run_backtest("w")
print(f"  weekly: {len(w_tr)} trades in {time.time()-t0:.0f}s")
print("running BIWEEKLY..."); b_tr, b_eq = run_backtest("b")
print(f"  biweekly: {len(b_tr)} trades in {time.time()-t0:.0f}s")

def stats(trades, eq, name):
    if not trades: return dict(name=name, n=0)
    df = pd.DataFrame(trades)
    df = df.dropna(subset=["pnl"])
    p = df["pnl"].values
    df["exit_d"] = pd.to_datetime(df["exit_d"])
    df["entry_d"] = pd.to_datetime(df["entry_d"])
    span_days = (df["exit_d"].max() - df["entry_d"].min()).days
    years = max(span_days/365.25, 0.5)
    peak = np.maximum.accumulate(eq)
    dd = eq - peak; ddp = dd / peak
    by_day = df.groupby(df["exit_d"].dt.date)["pnl"].sum()
    daily_ret = by_day / CAP
    final = eq[-1]
    return dict(
        name=name, n=len(p),
        trades_per_yr=round(len(p) / years, 1),
        avg_dte=round(df["days_held"].mean(), 1),
        win_pct=round((p>0).mean()*100, 1),
        avg_win=round(p[p>0].mean(), 0) if (p>0).any() else 0,
        avg_loss=round(p[p<0].mean(), 0) if (p<0).any() else 0,
        expectancy_rs=round(p.mean(), 0),
        total_pnl_rs=round(p.sum(), 0),
        final_equity_rs=round(final, 0),
        total_ret_pct=round((final-CAP)/CAP*100, 1),
        cagr_pct=round(((final/CAP)**(1/years) - 1)*100, 1),
        max_dd_rs=round(dd.min(), 0),
        max_dd_pct=round(ddp.min()*100, 1),
        sharpe=round(daily_ret.mean()/max(1e-9, daily_ret.std())*np.sqrt(252), 2),
        pf=round(p[p>0].sum()/max(1, abs(p[p<0].sum())), 2),
        worst_trade=round(p.min(), 0),
        best_trade=round(p.max(), 0),
    )

w_s = stats(w_tr, w_eq, "Weekly (front expiry)")
b_s = stats(b_tr, b_eq, "Biweekly (next expiry)")
print("\n" + pd.DataFrame([w_s, b_s]).set_index("name").T.to_string())

# yearly
def yearly(tr, name):
    if not tr: return pd.DataFrame()
    df = pd.DataFrame(tr).dropna(subset=["pnl"])
    df["year"] = pd.to_datetime(df["exit_d"]).dt.year
    return df.groupby("year").agg(n=("pnl","size"),
                                  pnl=("pnl","sum"),
                                  win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0)
print("\nWEEKLY yearly:"); print(yearly(w_tr, "w"))
print("\nBIWEEKLY yearly:"); print(yearly(b_tr, "b"))

# exit-reason breakdown
def reasons(tr, name):
    if not tr: return
    df = pd.DataFrame(tr).dropna(subset=["pnl"])
    print(f"\n{name} exit reasons:")
    print(df.groupby("reason").agg(n=("pnl","size"),
                                    pnl_sum=("pnl","sum"),
                                    pnl_mean=("pnl","mean"),
                                    win_pct=("pnl", lambda x: (x>0).mean()*100)).round(1).to_string())
reasons(w_tr, "WEEKLY"); reasons(b_tr, "BIWEEKLY")

# save CSVs
pd.DataFrame(w_tr).to_csv(OUT / "rsi_pe_weekly.csv", index=False)
pd.DataFrame(b_tr).to_csv(OUT / "rsi_pe_biweekly.csv", index=False)

# plot equity
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={"height_ratios":[3,1]})
ax1.plot(w_eq, label=f'Weekly · final ₹{w_s.get("final_equity_rs",CAP)/1e5:.2f}L · CAGR {w_s.get("cagr_pct",0)}% · Sharpe {w_s.get("sharpe",0)} · maxDD {w_s.get("max_dd_pct",0)}%', color='#2962ff', lw=1.4)
ax1.plot(b_eq, label=f'Biweekly · final ₹{b_s.get("final_equity_rs",CAP)/1e5:.2f}L · CAGR {b_s.get("cagr_pct",0)}% · Sharpe {b_s.get("sharpe",0)} · maxDD {b_s.get("max_dd_pct",0)}%', color='#26a69a', lw=1.4)
ax1.axhline(CAP, color='#787b86', ls='--', alpha=0.5, label='₹10L baseline')
ax1.set_ylabel('Equity (₹)'); ax1.legend(loc='upper left', fontsize=9); ax1.grid(alpha=0.3)
ax1.set_title('SELL 200-OTM PE when NIFTY>20DMA, book on RSI14>80 & RSI5>90 — 1 lot, real costs, 2021-2026')
w_pk = np.maximum.accumulate(w_eq); w_dd = (w_eq - w_pk)/w_pk*100
b_pk = np.maximum.accumulate(b_eq); b_dd = (b_eq - b_pk)/b_pk*100
ax2.fill_between(range(len(w_dd)), w_dd, 0, color='#2962ff', alpha=0.4, label='Weekly DD%')
ax2.fill_between(range(len(b_dd)), b_dd, 0, color='#26a69a', alpha=0.4, label='Biweekly DD%')
ax2.set_ylabel('Drawdown %'); ax2.set_xlabel('Trade #'); ax2.legend(fontsize=9); ax2.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "rsi_pe_equity.png", dpi=110)
print(f"\nchart → {OUT}/rsi_pe_equity.png")
print(f"total runtime: {time.time()-t0:.0f}s")
