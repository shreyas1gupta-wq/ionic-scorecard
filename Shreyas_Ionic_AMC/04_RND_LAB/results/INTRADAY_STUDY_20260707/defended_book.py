"""Defended book — three tests, defined-risk + portfolio combination.
Test 1: PE-sell 0DTE 12:00 as BULL-PUT SPREAD (SELL ATM PE + BUY PE-100).
Test 2: Portfolio = defined-risk PE-sell + Wider-BEAR skew-fade (uncorrelated by signal).
Test 3: Standing weekly tail hedge (BUY 5%-OTM PE) on top of Test 2.
Rs.1cr capital. Real costs.
"""
import sys, time
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INTRADAY_STUDY_20260707")
LOT = 65
CAP0 = 10_000_000  # Rs.1cr

def leg_cost(entry, exit, is_sell):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 20
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    stt = 0.001 * (entry if is_sell else exit) * LOT
    stamp = 3e-5 * (exit if is_sell else entry) * LOT
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
daily_close = s.groupby("d").agg(close=("close","last"))
expiries = list(dl.expiries())
expiry_days = [e for e in expiries if e in set(days_all)]

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
# TEST 1: Bull-put SPREAD version of 0DTE PE-sell 12:00
# Only fires when CE > 1.1x PE at 12:00 (bullish skew)
# SELL ATM PE + BUY ATM-100 PE, hold to 15:20
# ==========================================================
def test1_spread(hedge_gap=100):
    trades = []
    for d in expiry_days:
        arr = by_day.get(d)
        if arr is None or len(arr) < 300: continue
        ch = get_chain(d, d)
        if ch is None: continue
        sp0 = spot_at(d, 720)   # 12:00
        if sp0 is None: continue
        atm = int(round(sp0 / 50) * 50)
        ce0 = opt_px(ch, 720, atm, "CE")
        pe0 = opt_px(ch, 720, atm, "PE")
        if ce0 is None or pe0 is None or ce0 < 1 or pe0 < 1: continue
        ratio = ce0 / pe0
        if ratio < 1.10: continue
        # Only bullish skew: CE > 1.1x PE. Cheap side = PE. Sell PE ATM + Buy PE-gap.
        short_K = atm
        long_K = atm - hedge_gap
        short_e = pe0
        long_e = opt_px(ch, 720, long_K, "PE")
        if long_e is None or long_e < 0.5: continue
        short_x = opt_px(ch, 920, short_K, "PE")
        long_x = opt_px(ch, 920, long_K, "PE")
        if short_x is None or long_x is None: continue
        p_short = leg_pnl("S", short_e, short_x)
        p_long = leg_pnl("B", long_e, long_x)
        if p_short is None or p_long is None: continue
        credit = (short_e - long_e) * LOT
        max_loss = (hedge_gap * LOT) - credit
        pnl = p_short + p_long
        trades.append(dict(d=str(d), atm=atm, ratio=round(ratio,3),
                           short_K=short_K, long_K=long_K,
                           short_e=short_e, long_e=long_e,
                           short_x=short_x, long_x=long_x,
                           credit=round(credit,0), max_loss=round(max_loss,0),
                           pnl=round(pnl,0)))
    return pd.DataFrame(trades)

# ==========================================================
# TEST 2: Load skew-fade wider data + combine with Test 1
# Wider-BEAR fires on r < 0.7 (bearish skew) at 09:30
# Uses SHORT FUT + SHORT PE (already backtested)
# ==========================================================
def load_wider_bear():
    df = pd.read_csv(OUT / "skew_synth_wider.csv")
    df = df[(df["fut_dir"] == "S") & (df["opt_cp"] == "PE")].copy()
    df["date"] = pd.to_datetime(df["d"])
    df["src"] = "BEAR_fade"
    return df[["date","total_pnl","src"]].rename(columns={"total_pnl":"pnl"})

# ==========================================================
# TEST 3: Weekly tail hedge — BUY far-OTM PE, hold to expiry
# Simulate: at Monday 09:30, buy 1 lot PE 5% OTM, exit at expiry via intrinsic
# ==========================================================
def test3_tail_hedge():
    trades = []
    for d in daily_close.index:
        if not isinstance(d, date): d = pd.Timestamp(d).date()
        if d.weekday() != 0: continue  # Monday only
        # find next weekly expiry >= d + 2
        later = [e for e in expiries if (e - d).days in range(2, 10)]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, 570)
        if sp is None: continue
        K = int(round(sp * 0.95 / 50) * 50)  # 5% OTM
        ch = get_chain(d, ex)
        if ch is None: continue
        px_e = opt_px(ch, 570, K, "PE")
        if px_e is None or px_e < 1 or px_e > 200: continue  # skip if too expensive or thin
        settle = expiry_settle(ex)
        if settle is None: continue
        px_x = max(0.0, K - settle)
        pnl = leg_pnl("B", px_e, px_x)
        if pnl is None: continue
        trades.append(dict(d=str(d), K=K, entry=px_e, exit=px_x, expiry=str(ex), pnl=round(pnl,0)))
    return pd.DataFrame(trades)

# ==========================================================
def stats(df, name, pnl_col="pnl"):
    if len(df) == 0: return dict(name=name, n=0)
    df = df.copy()
    if "date" not in df.columns:
        df["date"] = pd.to_datetime(df["d"])
    df = df.sort_values("date").reset_index(drop=True)
    p = df[pnl_col].values.astype(float)
    yrs = max((df["date"].max() - df["date"].min()).days / 365.25, 0.5)
    eq = np.concatenate(([CAP0], CAP0 + p.cumsum()))
    peak = np.maximum.accumulate(eq); dd = eq - peak; ddp = dd / peak
    ret = np.diff(eq) / eq[:-1]
    n_yr = len(p) / yrs
    return dict(name=name, n=len(p),
                trades_per_yr=round(n_yr, 1),
                win_pct=round((p>0).mean()*100, 1),
                avg_win=round(p[p>0].mean(), 0) if (p>0).any() else 0,
                avg_loss=round(p[p<0].mean(), 0) if (p<0).any() else 0,
                expect=round(p.mean(), 0),
                total_pnl=round(p.sum(), 0),
                final=round(eq[-1], 0),
                cagr=round(((eq[-1]/CAP0)**(1/yrs) - 1) * 100, 2),
                maxdd_pct=round(ddp.min()*100, 1),
                sharpe=round(ret.mean()/max(1e-9, ret.std()) * np.sqrt(n_yr), 2),
                pf=round(p[p>0].sum()/max(1, abs(p[p<0].sum())), 2),
                worst=round(p.min(), 0), best=round(p.max(), 0)), eq, df

t0 = time.time()

# --- Run tests ---
print("=== TEST 1: Bull-put SPREAD version (SELL ATM PE + BUY PE-100) ===")
t1_100 = test1_spread(hedge_gap=100)
t1_100_stats, t1_100_eq, t1_100_df = stats(t1_100, "T1a · Spread hedge -100")
print(f"  {t1_100_stats}")
t1_100.to_csv(OUT / "defended_t1_hedge100.csv", index=False)

t1_150 = test1_spread(hedge_gap=150)
t1_150_stats, t1_150_eq, t1_150_df = stats(t1_150, "T1b · Spread hedge -150")
print(f"  {t1_150_stats}")

# --- naked baseline for comparison ---
naked = pd.read_csv(OUT / "rev_A_sell_cheap_hold.csv")
naked = naked[naked["side"] == "PE"].copy()
naked["date"] = pd.to_datetime(naked["d"])
naked_stats, naked_eq, naked_df = stats(naked, "Baseline · Naked PE sell")
print(f"  {naked_stats}")

# --- TEST 2 combined ---
print("\n=== TEST 2: Portfolio (Spread PE-sell + Wider-BEAR skew fade) ===")
bear = load_wider_bear()
bear_stats, bear_eq, bear_df = stats(bear, "BEAR fade only")
print(f"  BEAR alone: {bear_stats}")

# Combine on date - both fire independently, sum P&L
t1_use = t1_100_df[["date","pnl"]].copy(); t1_use["src"] = "PE_spread"
bear_use = bear_df[["date","pnl"]].copy(); bear_use["src"] = "BEAR_fade"
port = pd.concat([t1_use, bear_use]).sort_values("date").reset_index(drop=True)
port_stats, port_eq, _ = stats(port, "T2 · PE-spread + BEAR-fade")
print(f"  Combined: {port_stats}")

# --- TEST 3 hedge ---
print("\n=== TEST 3: Weekly tail hedge (BUY 5% OTM PE Monday->expiry) ===")
hedge = test3_tail_hedge()
if len(hedge):
    hedge_stats, hedge_eq, hedge_df = stats(hedge, "T3 · Weekly tail hedge only")
    print(f"  Hedge alone: {hedge_stats}")
    hedge.to_csv(OUT / "defended_t3_tailhedge.csv", index=False)
    # Portfolio + hedge
    port_h = pd.concat([port, hedge_df[["date","pnl"]].assign(src="HEDGE")]).sort_values("date")
    porth_stats, porth_eq, _ = stats(port_h, "T2+T3 · Portfolio + hedge overlay")
    print(f"  Combined + hedge: {porth_stats}")

# --- Yearly comparison ---
print("\n=== Yearly: Baseline naked vs T1a spread ===")
for tag, d in [("naked", naked_df), ("spread100", t1_100_df)]:
    d = d.copy()
    d["year"] = pd.to_datetime(d.get("date", d.get("d"))).dt.year
    yr = d.groupby("year").agg(n=("pnl","size"), pnl=("pnl","sum"),
                                win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0)
    print(f"\n{tag}:"); print(yr)

# --- Summary table ---
all_results = [naked_stats, t1_100_stats, t1_150_stats, bear_stats, port_stats]
if len(hedge):
    all_results += [hedge_stats, porth_stats]
sdf = pd.DataFrame(all_results).set_index("name")
sdf.to_csv(OUT / "defended_book_summary.csv")
print("\n=== SUMMARY ===")
print(sdf[["n","trades_per_yr","win_pct","expect","total_pnl","cagr","maxdd_pct","sharpe","pf","worst","best"]].to_string())

# --- Chart ---
fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(13, 11), gridspec_kw={"height_ratios":[3,1,1]})
sizings = [
    ("Baseline naked PE-sell", naked_eq, "#787b86"),
    ("T1a Spread PE-sell (-100 hedge)", t1_100_eq, "#4dd0e1"),
    ("T1b Spread PE-sell (-150 hedge)", t1_150_eq, "#26a69a"),
    ("BEAR-fade alone", bear_eq, "#ff8f8f"),
    ("T2 Portfolio (Spread + BEAR)", port_eq, "#ffd54f"),
]
if len(hedge):
    sizings += [
        ("T3 Tail-hedge alone (cost)", hedge_eq, "#ba68c8"),
        ("T2+T3 Portfolio + hedge", porth_eq, "#2962ff"),
    ]
for name, eq, col in sizings:
    st = next(r for r in all_results if r["name"].startswith(name.split(" ")[0]) or name.split()[0] in r["name"])
    ax1.plot(eq, label=f'{name}: final Rs.{eq[-1]/1e7:.2f}cr, CAGR {round(((eq[-1]/CAP0)**(1/max((len(eq))/50, 0.5))-1)*100, 1)}%', color=col, lw=1.4)
ax1.axhline(CAP0, color='#787b86', ls='--', alpha=0.5, label='Rs.1cr baseline')
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(fontsize=9, loc='best'); ax1.grid(alpha=0.3)
ax1.set_title('Defended Book on Rs.1cr - naked vs spread hedge vs portfolio vs +tail hedge (1 lot per trade, real costs)')

for name, eq, col in sizings:
    peak = np.maximum.accumulate(eq); dd = (eq-peak)/peak*100
    ax2.fill_between(range(len(dd)), dd, 0, color=col, alpha=0.25)
ax2.set_ylabel('Drawdown %'); ax2.grid(alpha=0.3)

# Bar chart: worst trade comparison
labels = [r["name"].split("·")[-1].strip()[:24] for r in all_results]
worst = [r["worst"] for r in all_results]
ax3.barh(labels, worst, color=['#787b86','#4dd0e1','#26a69a','#ff8f8f','#ffd54f','#ba68c8','#2962ff'][:len(labels)])
ax3.set_xlabel('Worst single trade P&L (Rs.)'); ax3.grid(alpha=0.3, axis='x')
plt.tight_layout()
plt.savefig(OUT / "defended_book.png", dpi=110)
print(f"\nchart -> defended_book.png")
print(f"runtime: {time.time()-t0:.0f}s")
