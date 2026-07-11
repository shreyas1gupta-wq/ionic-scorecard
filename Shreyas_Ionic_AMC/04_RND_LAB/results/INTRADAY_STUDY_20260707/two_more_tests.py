"""Two more setups:
  A) 0DTE at 12:00 - if ATM ratio (higher/lower) > 1.1x, buy expensive side (follow) OR cheap side (reverse).
     4 sub-variants: [follow, reverse] x [25%SL/50%TP, buy-and-hold-to-15:20].
  B) 5-7DTE spread with 20DMA filter: Nifty > 20DMA -> BUY ATM CE + SELL 2 or 3 strikes OTM CE
     Nifty < 20DMA -> BUY ATM PE + SELL 2 or 3 strikes OTM PE. Hold to expiry.
     2 variants (2-strike vs 3-strike wing).
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
ENTRY_A_HM = 720   # 12:00 for setup A
ENTRY_B_HM = 570   # 09:30 for setup B
EXIT_HM = 920      # 15:20
SETTLE_START = 900

def leg_cost(entry, exit, is_sell):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40 if is_sell is None else 20  # legs charge 20 each; naked buys use 40 R/T
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    stt = 0.001*(entry if is_sell else exit)*LOT if is_sell is not None else 0.001*exit*LOT  # buy: STT on sell (exit)
    stamp = 3e-5*(exit if is_sell else entry)*LOT if is_sell is not None else 3e-5*entry*LOT # buy: stamp on entry
    gst = 0.18*(brok + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + hs

def buy_pnl(entry, exit):
    if entry is None or exit is None or entry <= 0.05: return None
    c = leg_cost(entry, exit, None)  # naked buy
    if c is None: return None
    return (exit - entry) * LOT - c

def spread_pnl(long_e, long_x, short_e, short_x):
    if any(x is None for x in (long_e, long_x, short_e, short_x)): return None
    # long leg cost
    lc = leg_cost(long_e, long_x, False)
    sc = leg_cost(short_e, short_x, True)
    if lc is None or sc is None: return None
    gross_l = (long_x - long_e) * LOT
    gross_s = (short_e - short_x) * LOT
    # subtract half brokerage per leg to avoid double count (leg_cost has 20 each in single-leg version)
    return gross_l + gross_s - lc - sc

# ---- data ----
s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}

# Daily close + 20DMA
daily = s.groupby("d").agg(close=("close","last")).reset_index()
daily["sma20"] = daily["close"].rolling(20).mean()
daily["above_20dma"] = daily["close"] > daily["sma20"]
daily = daily.dropna(subset=["sma20"]).reset_index(drop=True)
d_idx = {d: i for i, d in enumerate(daily["d"])}

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
    tail = arr[(arr[:,0] >= SETTLE_START) & (arr[:,0] <= EXIT_HM+5)]
    return float(tail[:,4].mean()) if len(tail) >= 5 else None

def check_sl_tp(chain, K, cp, entry_hm, entry_px, sl_pct=0.25, tp_pct=0.50, max_hm=EXIT_HM):
    """For a LONG option, find first bar where price crosses SL (down X%) or TP (up Y%)."""
    sl_level = entry_px * (1 - sl_pct)
    tp_level = entry_px * (1 + tp_pct)
    for hm in range(entry_hm + 1, max_hm + 1):
        row = chain["minute_index"].get(hm, {}).get((int(K), cp))
        if not row: continue
        if row["h"] >= tp_level:
            return hm, tp_level, "TP"
        if row["l"] <= sl_level:
            return hm, sl_level, "SL"
    # EOD: exit at last available bar
    for hm in range(max_hm, entry_hm, -1):
        row = chain["minute_index"].get(hm, {}).get((int(K), cp))
        if row: return hm, row["c"], "EOD"
    return None, None, None

# ==========================================================
# SETUP A: 0DTE at 12:00, skew >1.1x, buy expensive/cheap
# ==========================================================
def setup_a():
    variants = {
        "follow_sltp":  {"follow": True,  "sltp": True},
        "follow_hold":  {"follow": True,  "sltp": False},
        "reverse_sltp": {"follow": False, "sltp": True},
        "reverse_hold": {"follow": False, "sltp": False},
    }
    out = {k: [] for k in variants}
    for d in expiry_days:
        arr = by_day.get(d)
        if arr is None or len(arr) < 300: continue
        ch = get_chain(d, d)
        if ch is None: continue
        sp0 = spot_at(d, ENTRY_A_HM)
        if sp0 is None: continue
        atm = int(round(sp0 / 50) * 50)
        ce = opt_px(ch, ENTRY_A_HM, atm, "CE")
        pe = opt_px(ch, ENTRY_A_HM, atm, "PE")
        if ce is None or pe is None or ce < 1 or pe < 1: continue
        rich, cheap = ("CE", "PE") if ce > pe else ("PE", "CE")
        rich_px, cheap_px = (ce, pe) if ce > pe else (pe, ce)
        ratio = max(ce, pe) / min(ce, pe)
        if ratio < 1.10: continue
        for name, v in variants.items():
            side = rich if v["follow"] else cheap
            side_px = rich_px if v["follow"] else cheap_px
            if side_px < 1: continue
            if v["sltp"]:
                exit_hm, exit_px, reason = check_sl_tp(ch, atm, side, ENTRY_A_HM, side_px)
            else:
                exit_px = opt_px(ch, EXIT_HM, atm, side)
                exit_hm = EXIT_HM
                reason = "HOLD_15:20"
            if exit_px is None: continue
            pnl = buy_pnl(side_px, exit_px)
            if pnl is None: continue
            out[name].append(dict(d=str(d), atm=atm, ratio=round(ratio,3),
                                  side=side, entry_px=side_px, exit_px=exit_px,
                                  exit_hm=exit_hm, reason=reason, pnl=round(pnl, 0)))
    return out

# ==========================================================
# SETUP B: 5-7 DTE spread with 20DMA filter
# Enter at DTE=6 (or nearest 5-7). Direction by yesterday's close vs 20DMA.
# ==========================================================
def setup_b(wing_strikes=2):
    """wing_strikes: number of strikes OTM to sell (2 = ATM+100, 3 = ATM+150 for CE)."""
    trades = []
    used_expiries = set()
    for i in range(1, len(daily)):
        d = daily.iloc[i]["d"]; yd = daily.iloc[i-1]  # yesterday's daily close/DMA (causal)
        # find expiry with DTE in [5, 7]
        later = [e for e in expiries if 5 <= (e - d).days <= 7]
        if not later: continue
        ex = later[0]
        if ex in used_expiries: continue  # avoid duplicate weekly entries
        used_expiries.add(ex)
        arr = by_day.get(d)
        if arr is None: continue
        sp = spot_at(d, ENTRY_B_HM)
        if sp is None: continue
        atm = int(round(sp / 50) * 50)
        above = bool(yd["above_20dma"])
        cp = "CE" if above else "PE"
        short_K = atm + wing_strikes * 50 if above else atm - wing_strikes * 50
        ch = get_chain(d, ex)
        if ch is None: continue
        long_e = opt_px(ch, ENTRY_B_HM, atm, cp)
        short_e = opt_px(ch, ENTRY_B_HM, short_K, cp)
        if long_e is None or short_e is None or long_e < 1 or short_e < 0.3: continue
        # exit at expiry
        settle = expiry_settle(ex)
        if settle is None: continue
        if cp == "CE":
            long_x = max(0.0, settle - atm)
            short_x = max(0.0, settle - short_K)
        else:
            long_x = max(0.0, atm - settle)
            short_x = max(0.0, short_K - settle)
        pnl = spread_pnl(long_e, long_x, short_e, short_x)
        if pnl is None: continue
        trades.append(dict(entry_d=str(d), expiry=str(ex), dte=(ex-d).days,
                           atm=atm, cp=cp, above_20dma=above,
                           long_e=long_e, short_e=short_e,
                           long_x=round(long_x,2), short_x=round(short_x,2),
                           debit=round((long_e-short_e)*LOT,0),
                           pnl=round(pnl,0)))
    return trades

# ==========================================================
# STATS + RUN
# ==========================================================
def stats(trades, name):
    if not trades: return dict(name=name, n=0)
    df = pd.DataFrame(trades)
    date_col = "entry_d" if "entry_d" in df.columns else "d"
    df["date"] = pd.to_datetime(df[date_col])
    df = df.sort_values("date").reset_index(drop=True)
    p = df["pnl"].values.astype(float)
    span = (df["date"].max() - df["date"].min()).days
    yrs = max(span/365.25, 0.5)
    eq = np.concatenate(([CAP], CAP + p.cumsum()))
    peak = np.maximum.accumulate(eq); dd = eq - peak; ddp = dd/peak
    dret = pd.Series(p/CAP)
    return dict(name=name, n=len(p), tpy=round(len(p)/yrs, 1),
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
                best=round(p.max(),0), worst=round(p.min(),0)), eq

t0 = time.time()
print("=== SETUP A: 0DTE 12:00 skew-follow/reverse ===")
a_out = setup_a()
a_res = []; a_eqs = {}
for name, trades in a_out.items():
    st, eq = stats(trades, f"A · {name}")
    a_res.append(st); a_eqs[st['name']] = eq
    print(f"  {st['name']}: n={st['n']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, DD={st['maxdd_pct']}%")
    pd.DataFrame(trades).to_csv(OUT / f"tmt_A_{name}.csv", index=False)

# reason breakdown for the sltp variants
for name, trades in a_out.items():
    if not trades or "sltp" not in name: continue
    df = pd.DataFrame(trades)
    print(f"\n  {name} exit reasons:")
    r = df.groupby("reason").agg(n=("pnl","size"),pnl_sum=("pnl","sum"),
                                  pnl_mean=("pnl","mean"),win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0)
    print(r.to_string())

print("\n=== SETUP B: 5-7 DTE spread with 20DMA filter ===")
b_res = []; b_eqs = {}
for wing in [2, 3]:
    trades = setup_b(wing_strikes=wing)
    st, eq = stats(trades, f"B · {wing}-strike wing")
    b_res.append(st); b_eqs[st['name']] = eq
    print(f"  {st['name']}: n={st['n']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, DD={st['maxdd_pct']}%")
    pd.DataFrame(trades).to_csv(OUT / f"tmt_B_wing{wing}.csv", index=False)
    # yearly + above/below split
    if trades:
        df = pd.DataFrame(trades); df["date"] = pd.to_datetime(df["entry_d"])
        df["year"] = df["date"].dt.year
        print(f"\n  Wing={wing} yearly:")
        print(df.groupby("year").agg(n=("pnl","size"),pnl=("pnl","sum"),
                                      win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0).to_string())
        print(f"\n  Wing={wing} above vs below 20DMA:")
        print(df.groupby("above_20dma").agg(n=("pnl","size"),pnl=("pnl","sum"),
                                            win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0).to_string())

# summary
all_res = a_res + b_res
pd.DataFrame(all_res).to_csv(OUT / "two_more_tests_summary.csv", index=False)
print("\n=== SUMMARY ===")
print(pd.DataFrame(all_res).set_index("name").T.to_string())

# equity chart
fig, ax = plt.subplots(figsize=(13, 7))
colors = ['#26a69a','#4dd0e1','#ef5350','#ff8f8f','#2962ff','#ba68c8']
all_eqs = {**a_eqs, **b_eqs}
for i, (name, eq) in enumerate(all_eqs.items()):
    st = next(r for r in all_res if r["name"] == name)
    ax.plot(eq, label=f'{name}: n={st["n"]}, Sharpe {st["sharpe"]}, CAGR {st["cagr"]}%', color=colors[i%len(colors)], lw=1.3)
ax.axhline(CAP, color='#787b86', ls='--', alpha=0.5, label='Rs.10L baseline')
ax.set_ylabel('Equity (Rs.)'); ax.set_xlabel('Trade #')
ax.legend(fontsize=8, loc='best'); ax.grid(alpha=0.3)
ax.set_title('Setup A (0DTE 12:00 skew follow/reverse) + Setup B (5-7DTE 20DMA spread) - 1 lot, real costs')
plt.tight_layout(); plt.savefig(OUT / "two_more_tests.png", dpi=110)
print(f"\nchart -> {OUT}/two_more_tests.png")
print(f"total runtime: {time.time()-t0:.0f}s")
