"""Multi-strategy sweep — 5 setups + shared cost model + equity curves.
Complements rsi_pe_sell.py (running in parallel).
Setups:
  Z1: 30-min z-score |z|>=2 vs 100-EMA -> sell 100-OTM opposite intraday
  R2: Daily RSI(5)<10 or >90 + 1-day delay -> sell ATM opposite max 5 days
  R3: same trigger -> buy 200-OTM same-as-reversion max 5 days
  S4: Weekly ATM straddle sell Monday->expiry
  P5: Weekly 200-OTM PE sell Monday->expiry (no RSI, baseline for the RSI-gated variant)
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
OPEN_HM = 555; ENTRY_HM = 570; EOD_HM = 924; SETTLE_START = 900

# ---- cost model (real, from backtest_fade.py) ----
def real_cost(entry, exit, is_sell):
    if entry is None or exit is None: return None
    if entry <= 0.05: return None
    brok = 40
    turnover = (entry + exit) * LOT
    ex_txn = 0.0003503 * turnover
    ipft = 0.000005 * turnover
    sebi = 0.000001 * turnover
    stt = 0.001 * (entry if is_sell else exit) * LOT   # STT on sell-leg premium (either open or close)
    stamp = 0.00003 * (exit if is_sell else entry) * LOT
    gst = 0.18 * (brok + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + hs

def leg_pnl(side, entry, exit):
    """side: 'B' buy or 'S' sell. Returns net Rs on 1 lot."""
    if entry is None or exit is None or entry <= 0.05: return None
    c = real_cost(entry, exit, side == "S")
    if c is None: return None
    gross = (exit - entry) * LOT if side == "B" else (entry - exit) * LOT
    return gross - c

# ---- data ----
def rsi(close, period):
    d = close.diff()
    u = d.clip(lower=0); dn = -d.clip(upper=0)
    au = u.ewm(alpha=1/period, adjust=False).mean()
    ad = dn.ewm(alpha=1/period, adjust=False).mean()
    return 100 - 100 / (1 + au/ad.replace(0, np.nan))

t0 = time.time()
print("loading spot...")
s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(close=("close","last")).reset_index()
daily["sma20"] = daily["close"].rolling(20).mean()
daily["rsi5"] = rsi(daily["close"], 5)
daily["rsi14"] = rsi(daily["close"], 14)
daily["above_20dma"] = daily["close"] > daily["sma20"]
daily["overbought_5"] = daily["rsi5"] > 90
daily["oversold_5"] = daily["rsi5"] < 10
daily["neutral_rsi"] = daily["rsi5"].between(30, 70)
daily = daily.dropna(subset=["sma20","rsi5"]).reset_index(drop=True)
d_map = {d: i for i, d in enumerate(daily["d"])}

expiries = list(dl.expiries())
def next_weekly(d, min_dte=1, max_dte=8):
    for e in expiries:
        if min_dte <= (e - d).days <= max_dte: return e
    return None
def next_biweekly(d):
    w = [e for e in expiries if (e - d).days >= 8]
    return w[0] if w and (w[0] - d).days <= 15 else None

opt_cache = {}
def get_chain(d, ex):
    k = (d, ex)
    if k not in opt_cache:
        if len(opt_cache) > 40:
            for _k in list(opt_cache.keys())[:20]: del opt_cache[_k]
        try: opt_cache[k] = dl.load_option_day(ex, d)
        except Exception: opt_cache[k] = None
    return opt_cache[k]

def opt_price(chain, hm, K, cp):
    if chain is None: return None
    for b in range(16):
        r = chain["minute_index"].get(hm - b, {}).get((int(K), cp))
        if r: return r["c"]
    for f in range(1, 6):
        r = chain["minute_index"].get(hm + f, {}).get((int(K), cp))
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
    tail = arr[(arr[:,0] >= SETTLE_START) & (arr[:,0] <= EOD_HM+5)]
    return float(tail[:,4].mean()) if len(tail) >= 5 else None

# ---- BACKTEST HARNESS ----
def build_equity(trades):
    eq = [CAP]
    for t in trades:
        pnl = t.get("pnl")
        if pnl is None or pd.isna(pnl): continue
        eq.append(eq[-1] + pnl)
    return np.array(eq)

def stats(trades, eq, name):
    if not trades: return dict(name=name, n=0)
    df = pd.DataFrame([t for t in trades if t.get("pnl") is not None])
    if len(df) == 0: return dict(name=name, n=0)
    p = df["pnl"].values
    df["date_exit"] = pd.to_datetime(df.get("exit_d", df.get("entry_d")))
    df["date_entry"] = pd.to_datetime(df.get("entry_d", df.get("d")))
    span = (df["date_exit"].max() - df["date_entry"].min()).days
    years = max(span/365.25, 0.5)
    by_day = df.groupby(df["date_exit"].dt.date)["pnl"].sum()
    d_ret = by_day / CAP
    peak = np.maximum.accumulate(eq); dd = eq - peak; ddp = dd / peak
    return dict(
        name=name, n=int(len(p)), tpy=round(len(p)/years, 1),
        win_pct=round((p>0).mean()*100, 1),
        expectancy=round(p.mean(), 0),
        total_pnl=round(p.sum(), 0),
        final=round(eq[-1], 0),
        ret_pct=round((eq[-1]-CAP)/CAP*100, 1),
        cagr=round(((eq[-1]/CAP)**(1/years) - 1)*100, 1),
        maxdd_pct=round(ddp.min()*100, 1),
        sharpe=round(d_ret.mean()/max(1e-9, d_ret.std())*np.sqrt(252), 2),
        pf=round(p[p>0].sum()/max(1, abs(p[p<0].sum())), 2),
        worst=round(p.min(), 0), best=round(p.max(), 0),
    )

# =========================================================
# Z1: 30-min z-score MR — SELL 100-OTM opposite when |z|>=2
# =========================================================
def strat_z_score(z_thresh=2.0, period=100):
    # Build concatenated 30-min series
    bars = []
    for d in days_all:
        arr = by_day[d]
        if len(arr) < 100: continue
        idx = ((arr[:,0] - OPEN_HM) // 30).astype(int)
        for j in np.unique(idx):
            m = idx == j
            if not m.any(): continue
            end_hm = OPEN_HM + (int(j)+1) * 30
            bars.append((d, end_hm, arr[m,4][-1]))  # (day, bar end HM, close)
    bars = pd.DataFrame(bars, columns=["d","hm","close"])
    bars["ema"] = bars["close"].ewm(span=period, adjust=False).mean()
    bars["std"] = bars["close"].rolling(period).std()
    bars["z"] = (bars["close"] - bars["ema"]) / bars["std"]
    bars["dte"] = bars["d"].apply(lambda x: (next_weekly(x, 0, 8) - x).days if next_weekly(x, 0, 8) else -1)
    trades = []
    open_pos = None  # dict(cp, K, entry_d, entry_hm, entry_px, expiry)
    for i, r in bars.iterrows():
        d = r["d"]; hm = int(r["hm"]); z = r["z"]
        if pd.isna(z): continue
        # exit first
        if open_pos is not None:
            close_now = False
            # exit if z reverts inside 1σ, or day changed (no overnight for MR)
            same_day = (d == open_pos["entry_d"])
            if not same_day or abs(z) < 1.0 or hm >= EOD_HM:
                close_now = True
            if close_now:
                ex = open_pos["expiry"]
                use_d = d if same_day else open_pos["entry_d"]
                use_hm = hm if same_day else EOD_HM
                ch = get_chain(use_d, ex)
                exit_px = opt_price(ch, use_hm, open_pos["K"], open_pos["cp"])
                if exit_px is None:
                    # try previous minute
                    exit_px = opt_price(ch, use_hm - 5, open_pos["K"], open_pos["cp"])
                if exit_px is not None:
                    pnl = leg_pnl("S", open_pos["entry_px"], exit_px)
                    trades.append(dict(
                        entry_d=str(open_pos["entry_d"]), exit_d=str(use_d),
                        K=open_pos["K"], cp=open_pos["cp"], entry_px=open_pos["entry_px"],
                        exit_px=exit_px, pnl=pnl, z_entry=open_pos["z_entry"], z_exit=z,
                    ))
                open_pos = None
        # entry
        if open_pos is None and abs(z) >= z_thresh and hm < EOD_HM - 30:
            ex = next_weekly(d, 1, 8)
            if ex is None: continue
            sp = spot_at(d, hm)
            if sp is None: continue
            # z > 2 (price high) -> mean reversion DOWN -> sell 100-OTM CE (bet price stays / falls)
            # z < -2 (price low) -> mean reversion UP -> sell 100-OTM PE
            if z > 0:
                K = int(round((sp + 100) / 50) * 50); cp = "CE"
            else:
                K = int(round((sp - 100) / 50) * 50); cp = "PE"
            ch = get_chain(d, ex)
            px = opt_price(ch, hm, K, cp)
            if px is None or px < 2: continue
            open_pos = dict(cp=cp, K=K, entry_d=d, entry_hm=hm, entry_px=px, expiry=ex, z_entry=z)
    return trades

# =========================================================
# R2: RSI(5) extreme daily + 1-day delay -> SELL ATM opposite, max 5 days
# =========================================================
def strat_rsi5_sell_atm(max_hold=5):
    trades = []; open_pos = None
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]; yd = daily.iloc[i-1]
        # exit
        if open_pos is not None:
            hold_days = (d - open_pos["entry_d"]).days
            close = False; reason = ""
            if d == open_pos["expiry"]: close = True; reason = "EXPIRY"
            elif hold_days >= max_hold: close = True; reason = "TIMEOUT"
            elif bool(yd["neutral_rsi"]): close = True; reason = "RSI_NEUTRAL"
            if close:
                if reason == "EXPIRY":
                    settle = expiry_settle(d)
                    exit_px = max(0.0, (settle - open_pos["K"]) if open_pos["cp"] == "CE" else (open_pos["K"] - settle)) if settle else None
                else:
                    ch = get_chain(d, open_pos["expiry"])
                    exit_px = opt_price(ch, ENTRY_HM, open_pos["K"], open_pos["cp"])
                if exit_px is not None:
                    pnl = leg_pnl("S", open_pos["entry_px"], exit_px)
                    trades.append(dict(
                        entry_d=str(open_pos["entry_d"]), exit_d=str(d),
                        cp=open_pos["cp"], K=open_pos["K"],
                        entry_px=open_pos["entry_px"], exit_px=exit_px,
                        days_held=hold_days, reason=reason, pnl=pnl,
                    ))
                open_pos = None
        # entry
        if open_pos is None and (bool(yd["overbought_5"]) or bool(yd["oversold_5"])):
            ex = next_weekly(d, 2, 8)
            if ex is None: continue
            sp = spot_at(d, ENTRY_HM)
            if sp is None: continue
            atm = int(round(sp / 50) * 50)
            cp = "CE" if bool(yd["overbought_5"]) else "PE"
            ch = get_chain(d, ex)
            px = opt_price(ch, ENTRY_HM, atm, cp)
            if px is None or px < 2: continue
            open_pos = dict(cp=cp, K=atm, entry_d=d, entry_hm=ENTRY_HM, entry_px=px, expiry=ex)
    return trades

# =========================================================
# R3: RSI(5) extreme + 1-day delay -> BUY 200-OTM (mean reversion direction), max 5 days
# =========================================================
def strat_rsi5_buy_otm(max_hold=5):
    trades = []; open_pos = None
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]; yd = daily.iloc[i-1]
        # exit
        if open_pos is not None:
            hold_days = (d - open_pos["entry_d"]).days
            close = False; reason = ""
            if d == open_pos["expiry"]: close = True; reason = "EXPIRY"
            elif hold_days >= max_hold: close = True; reason = "TIMEOUT"
            elif bool(yd["neutral_rsi"]): close = True; reason = "RSI_NEUTRAL"
            if close:
                if reason == "EXPIRY":
                    settle = expiry_settle(d)
                    exit_px = max(0.0, (settle - open_pos["K"]) if open_pos["cp"] == "CE" else (open_pos["K"] - settle)) if settle else None
                else:
                    ch = get_chain(d, open_pos["expiry"])
                    exit_px = opt_price(ch, ENTRY_HM, open_pos["K"], open_pos["cp"])
                if exit_px is not None:
                    pnl = leg_pnl("B", open_pos["entry_px"], exit_px)
                    trades.append(dict(
                        entry_d=str(open_pos["entry_d"]), exit_d=str(d),
                        cp=open_pos["cp"], K=open_pos["K"],
                        entry_px=open_pos["entry_px"], exit_px=exit_px,
                        days_held=hold_days, reason=reason, pnl=pnl,
                    ))
                open_pos = None
        # entry: RSI5<10 -> expect UP reversal -> buy 200-OTM CE; RSI5>90 -> buy 200-OTM PE
        if open_pos is None and (bool(yd["overbought_5"]) or bool(yd["oversold_5"])):
            ex = next_weekly(d, 2, 8)
            if ex is None: continue
            sp = spot_at(d, ENTRY_HM)
            if sp is None: continue
            if bool(yd["oversold_5"]):
                cp = "CE"; K = int(round((sp + 200) / 50) * 50)
            else:
                cp = "PE"; K = int(round((sp - 200) / 50) * 50)
            ch = get_chain(d, ex)
            px = opt_price(ch, ENTRY_HM, K, cp)
            if px is None or px < 1: continue
            open_pos = dict(cp=cp, K=K, entry_d=d, entry_hm=ENTRY_HM, entry_px=px, expiry=ex)
    return trades

# =========================================================
# S4: Weekly ATM straddle SELL Monday -> expiry
# =========================================================
def strat_atm_straddle_sell():
    trades = []
    # trade on Mondays where 20DMA above (calm regime bias)
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue  # Monday only
        ex = next_weekly(d, 2, 8)
        if ex is None: continue
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        atm = int(round(sp / 50) * 50)
        ch = get_chain(d, ex)
        pce = opt_price(ch, ENTRY_HM, atm, "CE")
        ppe = opt_price(ch, ENTRY_HM, atm, "PE")
        if pce is None or ppe is None or pce < 2 or ppe < 2: continue
        # exit at expiry: intrinsic
        settle = expiry_settle(ex)
        if settle is None: continue
        xce = max(0.0, settle - atm)
        xpe = max(0.0, atm - settle)
        p_ce = leg_pnl("S", pce, xce)
        p_pe = leg_pnl("S", ppe, xpe)
        if p_ce is None or p_pe is None: continue
        trades.append(dict(entry_d=str(d), exit_d=str(ex), K=atm,
                           entry_px=pce+ppe, exit_px=xce+xpe,
                           days_held=(ex-d).days, pnl=p_ce + p_pe))
    return trades

# =========================================================
# P5: Weekly 200-OTM PE SELL Monday -> expiry (no filter — baseline)
# =========================================================
def strat_friday_pe_weekly():
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue
        ex = next_weekly(d, 2, 8)
        if ex is None: continue
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        K = int(round((sp - 200) / 50) * 50)
        ch = get_chain(d, ex)
        px = opt_price(ch, ENTRY_HM, K, "PE")
        if px is None or px < 1: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        xpx = max(0.0, K - settle)
        pnl = leg_pnl("S", px, xpx)
        if pnl is None: continue
        trades.append(dict(entry_d=str(d), exit_d=str(ex), K=K,
                           entry_px=px, exit_px=xpx,
                           days_held=(ex-d).days, pnl=pnl))
    return trades

# =========================================================
# RUN ALL
# =========================================================
suite = [
    ("Z1 · 30m z-score MR (sell 100OTM)", strat_z_score),
    ("R2 · RSI5-ext delayed sell ATM (5d)", strat_rsi5_sell_atm),
    ("R3 · RSI5-ext delayed buy 200OTM (5d)", strat_rsi5_buy_otm),
    ("S4 · Weekly ATM straddle sell", strat_atm_straddle_sell),
    ("P5 · Weekly 200-OTM PE sell (Mon)", strat_friday_pe_weekly),
]

summary = []
all_trades = {}
for name, fn in suite:
    print(f"\n--- {name} ---"); t1 = time.time()
    try:
        trades = fn()
        eq = build_equity(trades)
        st = stats(trades, eq, name)
        summary.append(st); all_trades[name] = (trades, eq)
        print(f"  {st}")
    except Exception as e:
        import traceback; traceback.print_exc()
        summary.append(dict(name=name, n=0, error=str(e)))
    print(f"  runtime: {time.time()-t1:.0f}s")

sdf = pd.DataFrame(summary).set_index("name")
print("\n=== SUMMARY ===")
print(sdf.to_string())
sdf.to_csv(OUT / "sweep_summary.csv")

# save each strategy trades
for name, (trades, _) in all_trades.items():
    if trades:
        safe = name.split("·")[0].strip().replace(" ", "_")
        pd.DataFrame(trades).to_csv(OUT / f"trades_{safe}.csv", index=False)

# equity chart
fig, ax = plt.subplots(figsize=(13, 7))
colors = ['#2962ff', '#26a69a', '#ef5350', '#ff9800', '#ba68c8']
for i, (name, (_, eq)) in enumerate(all_trades.items()):
    if len(eq) < 2: continue
    st = [s for s in summary if s["name"] == name][0]
    lbl = f'{name}: final ₹{st.get("final",CAP)/1e5:.2f}L, CAGR {st.get("cagr",0)}%, Sharpe {st.get("sharpe",0)}, maxDD {st.get("maxdd_pct",0)}%'
    ax.plot(eq, label=lbl, color=colors[i], lw=1.3, alpha=0.85)
ax.axhline(CAP, color='#787b86', ls='--', alpha=0.5, label='₹10L baseline')
ax.set_ylabel('Equity (₹)'); ax.set_xlabel('Trade #')
ax.legend(fontsize=8, loc='best'); ax.grid(alpha=0.3)
ax.set_title('5-Strategy Sweep — 1 lot, real costs, 2021–2026')
plt.tight_layout(); plt.savefig(OUT / "sweep_equity.png", dpi=110)
print(f"\nchart -> {OUT}/sweep_equity.png")
print(f"total runtime: {time.time()-t0:.0f}s")
