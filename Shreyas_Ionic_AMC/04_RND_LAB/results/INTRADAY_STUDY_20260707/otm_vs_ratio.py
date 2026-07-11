"""Compare two 20DMA-filtered PE strategies (Nifty > 20DMA required):
  A) SELL 3% OTM PE (naked, safer strike) weekly, hold to expiry
  B) SELL ATM PE + BUY 2 x far-OTM PE (broken-wing ratio hedge) weekly, hold to expiry

Ratio hedge properties:
  entry credit = P_short_ATM - 2 * P_long_far
  Below far strike: NET LONG puts (2 longs - 1 short) -> gains as market falls (TAIL PROTECTION)
  Between strikes: NET SHORT (loses on drops)
  Above ATM: all expire OTM -> keep net credit (or eat net debit if negative)

Cross entered every Monday if Nifty > 20DMA at prev close. Front weekly expiry.
1 unit sizing on Rs.1cr. Real costs.

Also compare vs prior "baseline PE-sell" from the defended book.
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
LOT = 65
CAP0 = 10_000_000
ENTRY_HM = 570  # 09:30
SETTLE_START = 900

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
d_idx = {d: i for i, d in enumerate(daily["d"])}

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
    tail = arr[(arr[:,0] >= SETTLE_START) & (arr[:,0] <= 929)]
    return float(tail[:,4].mean()) if len(tail) >= 5 else None

# ==========================================================
# Strategy A: SELL 3% OTM PE, hold to expiry
# ==========================================================
def strat_A():
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue  # Monday
        if not bool(daily.iloc[i-1]["above_20dma"]): continue  # need uptrend regime
        later = [e for e in expiries if (e - d).days in range(4, 10)]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        K = int(round(sp * 0.97 / 50) * 50)  # 3% OTM PE
        ch = get_chain(d, ex)
        px_e = opt_px(ch, ENTRY_HM, K, "PE")
        if px_e is None or px_e < 1: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        px_x = max(0.0, K - settle)
        pnl = leg_pnl("S", px_e, px_x)
        if pnl is None: continue
        trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days, K=K,
                           spot_entry=sp, entry_px=px_e, exit_px=round(px_x,2),
                           spot_settle=round(settle,1),
                           credit=round(px_e * LOT, 0),
                           pnl=round(pnl, 0)))
    return pd.DataFrame(trades)

# ==========================================================
# Strategy B: SELL 1x ATM PE + BUY 2x far-OTM PE
# Test with far_otm_pct in {3%, 5%}
# ==========================================================
def strat_B(far_otm_pct=0.03):
    trades = []
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]
        if d.weekday() != 0: continue
        if not bool(daily.iloc[i-1]["above_20dma"]): continue
        later = [e for e in expiries if (e - d).days in range(4, 10)]
        if not later: continue
        ex = later[0]
        sp = spot_at(d, ENTRY_HM)
        if sp is None: continue
        K_short = int(round(sp / 50) * 50)  # ATM
        K_long = int(round(sp * (1 - far_otm_pct) / 50) * 50)  # far OTM
        ch = get_chain(d, ex)
        px_short_e = opt_px(ch, ENTRY_HM, K_short, "PE")
        px_long_e = opt_px(ch, ENTRY_HM, K_long, "PE")
        if px_short_e is None or px_long_e is None or px_short_e < 1 or px_long_e < 0.3: continue
        settle = expiry_settle(ex)
        if settle is None: continue
        px_short_x = max(0.0, K_short - settle)
        px_long_x = max(0.0, K_long - settle)
        # 1 short + 2 long
        p_short = leg_pnl("S", px_short_e, px_short_x)
        p_long_each = leg_pnl("B", px_long_e, px_long_x)
        if p_short is None or p_long_each is None: continue
        pnl_total = p_short + 2 * p_long_each
        net_entry = px_short_e - 2 * px_long_e  # per lot pair
        # Below where 2 longs pay off: S* = 2*K_long - K_short (linear payoff below this)
        breakeven_below = 2 * K_long - K_short
        trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                           K_short=K_short, K_long=K_long,
                           spot_entry=sp, spot_settle=round(settle,1),
                           px_short_e=px_short_e, px_long_e=px_long_e,
                           px_short_x=round(px_short_x,2), px_long_x=round(px_long_x,2),
                           net_credit=round(net_entry * LOT, 0),
                           be_below=breakeven_below,
                           pnl_short=round(p_short,0),
                           pnl_long_each=round(p_long_each,0),
                           pnl=round(pnl_total, 0),
                           regime=("BIG_DROP" if settle < K_long else "MID" if settle < K_short else "OTM_expire")))
    return pd.DataFrame(trades)

# ==========================================================
def stats(df, name):
    if len(df) == 0: return dict(name=name, n=0)
    df = df.copy(); df["date"] = pd.to_datetime(df["entry_d"])
    df = df.sort_values("date").reset_index(drop=True)
    p = df["pnl"].values.astype(float)
    yrs = max((df["date"].max() - df["date"].min()).days / 365.25, 0.5)
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

print("=== A: SELL 3% OTM PE ===")
a_df = strat_A()
a_stats, a_eq = stats(a_df, "A · SELL 3pct-OTM PE")
print(f"  {a_stats}")
a_df.to_csv(OUT / "otm_A_3pct_naked.csv", index=False)

print("\n=== B: SELL ATM PE + BUY 2 x 3% OTM PE (broken-wing hedge) ===")
b3_df = strat_B(0.03)
b3_stats, b3_eq = stats(b3_df, "B · Ratio ATM + 2x 3pct-OTM")
print(f"  {b3_stats}")
b3_df.to_csv(OUT / "otm_B_ratio_3pct.csv", index=False)

print("\n=== B': SELL ATM PE + BUY 2 x 5% OTM PE (wider hedge) ===")
b5_df = strat_B(0.05)
b5_stats, b5_eq = stats(b5_df, "B' · Ratio ATM + 2x 5pct-OTM")
print(f"  {b5_stats}")
b5_df.to_csv(OUT / "otm_B_ratio_5pct.csv", index=False)

# ---- Additional variant: 2% and 4% for reference ----
b2_df = strat_B(0.02)
b2_stats, b2_eq = stats(b2_df, "B · Ratio ATM + 2x 2pct-OTM")
print(f"  {b2_stats}")

b4_df = strat_B(0.04)
b4_stats, b4_eq = stats(b4_df, "B · Ratio ATM + 2x 4pct-OTM")
print(f"  {b4_stats}")

# ---- Analysis: yearly + by regime for strat B 3% ----
if len(b3_df):
    b3_df["date"] = pd.to_datetime(b3_df["entry_d"]); b3_df["year"] = b3_df["date"].dt.year
    print("\n=== B (ratio 3%) YEARLY ===")
    print(b3_df.groupby("year").agg(n=("pnl","size"), pnl=("pnl","sum"),
                                     win=("pnl", lambda x: round((x>0).mean()*100,1))).round(0).to_string())
    print("\n=== B (ratio 3%) BY REGIME (where did spot settle vs strikes) ===")
    print(b3_df.groupby("regime").agg(n=("pnl","size"), pnl_sum=("pnl","sum"),
                                       pnl_mean=("pnl","mean"),
                                       win=("pnl", lambda x: round((x>0).mean()*100,1))).round(0).to_string())

# ---- Combined chart ----
all_stats = [a_stats, b2_stats, b3_stats, b4_stats, b5_stats]
all_eqs = {a_stats["name"]: a_eq, b2_stats["name"]: b2_eq, b3_stats["name"]: b3_eq,
           b4_stats["name"]: b4_eq, b5_stats["name"]: b5_eq}
sdf = pd.DataFrame(all_stats).set_index("name")
sdf.to_csv(OUT / "otm_vs_ratio_summary.csv")
print("\n=== SUMMARY ===")
print(sdf[["n","tpy","win_pct","expect","total","cagr","maxdd_pct","sharpe","pf","worst","best"]].to_string())

fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 8), gridspec_kw={"height_ratios":[3,1]})
colors = ['#4dd0e1', '#ffd54f', '#26a69a', '#ff9800', '#ba68c8']
for i, (name, eq) in enumerate(all_eqs.items()):
    st = next(r for r in all_stats if r["name"] == name)
    ax1.plot(eq, label=f'{name}: final Rs.{eq[-1]/1e5:.1f}L, Sharpe {st["sharpe"]}, DD {st["maxdd_pct"]}%, worst Rs.{st["worst"]:,}',
             color=colors[i], lw=1.3)
    peak = np.maximum.accumulate(eq); dd = (eq-peak)/peak*100
    ax2.fill_between(range(len(dd)), dd, 0, color=colors[i], alpha=0.25)
ax1.axhline(CAP0, color='#787b86', ls='--', alpha=0.5, label='Rs.1cr baseline')
ax1.set_ylabel('Equity (Rs.)'); ax1.legend(fontsize=8, loc='best'); ax1.grid(alpha=0.3)
ax1.set_title('Nifty > 20DMA regime: Naked 3% OTM PE-sell vs Broken-wing ratio hedge (1x ATM sell + 2x far-OTM buy)')
ax2.set_ylabel('DD %'); ax2.set_xlabel('Trade #'); ax2.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(OUT / "otm_vs_ratio.png", dpi=110)
print(f"\nchart -> otm_vs_ratio.png")
print(f"runtime: {time.time()-t0:.0f}s")
