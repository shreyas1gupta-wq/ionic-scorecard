"""Reverse the losing strategies:
  R-A) Credit spread at 13:30: SELL ATM + BUY ATM+50 (bear-call for CE, bull-put for PE) - hold to 15:20
  R-B) SELL 0DTE skew side at 12:00, 4 variants:
         [SELL rich (was FOLLOW-buy), SELL cheap (was REVERSE-buy)] x [25%SL/50%TP, hold-to-15:20]
     For SELL: 25% SL = price rises 25% (loss capped). 50% TP = price falls 50% (profit).
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
EXIT_HM = 920      # 15:20

def leg_cost(entry, exit, is_sell):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    if is_sell:
        stt = 0.001 * entry * LOT
        stamp = 3e-5 * exit * LOT
    else:
        stt = 0.001 * exit * LOT
        stamp = 3e-5 * entry * LOT
    gst = 0.18*(brok + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + hs

def sell_pnl(entry, exit):
    if entry is None or exit is None or entry <= 0.05: return None
    c = leg_cost(entry, exit, True)
    if c is None: return None
    return (entry - exit) * LOT - c

def buy_pnl(entry, exit):
    if entry is None or exit is None or entry <= 0.05: return None
    c = leg_cost(entry, exit, False)
    if c is None: return None
    return (exit - entry) * LOT - c

def spread_credit_pnl(short_e, short_x, long_e, long_x):
    """SELL near + BUY far = credit spread."""
    if any(x is None for x in (short_e, short_x, long_e, long_x)): return None
    sp = sell_pnl(short_e, short_x)
    bp = buy_pnl(long_e, long_x)
    if sp is None or bp is None: return None
    return sp + bp

s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
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

def check_sl_tp_sell(chain, K, cp, entry_hm, entry_px, sl_pct=0.25, tp_pct=0.50, max_hm=EXIT_HM):
    """For a SHORT option: SL = price rises to entry*(1+sl_pct), TP = price falls to entry*(1-tp_pct)."""
    sl_level = entry_px * (1 + sl_pct)   # short loses on price up
    tp_level = entry_px * (1 - tp_pct)   # short profits on price down
    for hm in range(entry_hm + 1, max_hm + 1):
        row = chain["minute_index"].get(hm, {}).get((int(K), cp))
        if not row: continue
        if row["l"] <= tp_level:   # price fell -> hit TP first (favorable side)
            return hm, tp_level, "TP"
        if row["h"] >= sl_level:   # price rose -> hit SL
            return hm, sl_level, "SL"
    for hm in range(max_hm, entry_hm, -1):
        row = chain["minute_index"].get(hm, {}).get((int(K), cp))
        if row: return hm, row["c"], "EOD"
    return None, None, None

# ==========================================================
# R-A: CREDIT SPREADS at 13:30, hold to 15:20
# ==========================================================
def credit_spread_backtest(spread, entry_hm=810):
    trades = []
    for d in expiry_days:
        arr = by_day.get(d)
        if arr is None or len(arr) < 300: continue
        ch = get_chain(d, d)
        if ch is None: continue
        sp0 = spot_at(d, entry_hm)
        if sp0 is None: continue
        atm = int(round(sp0 / 50) * 50)
        short_K = atm
        long_K = atm + 50 if spread == "CE" else atm - 50
        short_e = opt_px(ch, entry_hm, short_K, spread)
        long_e = opt_px(ch, entry_hm, long_K, spread)
        if short_e is None or long_e is None or short_e < 1: continue
        short_x = opt_px(ch, EXIT_HM, short_K, spread)
        long_x = opt_px(ch, EXIT_HM, long_K, spread)
        if short_x is None or long_x is None: continue
        pnl = spread_credit_pnl(short_e, short_x, long_e, long_x)
        if pnl is None: continue
        credit = (short_e - long_e) * LOT
        trades.append(dict(d=str(d), atm=atm, spread=spread,
                           short_K=short_K, long_K=long_K,
                           short_e=short_e, long_e=long_e,
                           short_x=short_x, long_x=long_x,
                           credit=round(credit,0),
                           pnl=round(pnl,0)))
    return trades

# ==========================================================
# R-B: 0DTE at 12:00, SELL expensive/cheap side
# ==========================================================
def sell_skew_backtest():
    variants = {
        "sell_rich_sltp":  {"sell_rich": True,  "sltp": True},
        "sell_rich_hold":  {"sell_rich": True,  "sltp": False},
        "sell_cheap_sltp": {"sell_rich": False, "sltp": True},
        "sell_cheap_hold": {"sell_rich": False, "sltp": False},
    }
    out = {k: [] for k in variants}
    for d in expiry_days:
        arr = by_day.get(d)
        if arr is None or len(arr) < 300: continue
        ch = get_chain(d, d)
        if ch is None: continue
        sp0 = spot_at(d, 720)
        if sp0 is None: continue
        atm = int(round(sp0/50)*50)
        ce = opt_px(ch, 720, atm, "CE")
        pe = opt_px(ch, 720, atm, "PE")
        if ce is None or pe is None or ce < 1 or pe < 1: continue
        rich, cheap = ("CE", "PE") if ce > pe else ("PE", "CE")
        rich_px, cheap_px = (ce, pe) if ce > pe else (pe, ce)
        ratio = max(ce, pe) / min(ce, pe)
        if ratio < 1.10: continue
        for name, v in variants.items():
            side = rich if v["sell_rich"] else cheap
            side_px = rich_px if v["sell_rich"] else cheap_px
            if side_px < 1: continue
            if v["sltp"]:
                exit_hm, exit_px, reason = check_sl_tp_sell(ch, atm, side, 720, side_px)
            else:
                exit_px = opt_px(ch, EXIT_HM, atm, side)
                exit_hm = EXIT_HM
                reason = "HOLD_15:20"
            if exit_px is None: continue
            pnl = sell_pnl(side_px, exit_px)
            if pnl is None: continue
            out[name].append(dict(d=str(d), atm=atm, ratio=round(ratio,3),
                                  side=side, entry_px=side_px, exit_px=exit_px,
                                  exit_hm=exit_hm, reason=reason, pnl=round(pnl, 0)))
    return out

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
all_res = []; all_eqs = {}

print("=== R-A: CREDIT SPREADS at 13:30 ===")
for spread, tag in [("CE", "bear-call"), ("PE", "bull-put")]:
    tr = credit_spread_backtest(spread, entry_hm=810)
    st, eq = stats(tr, f"R-A · {spread} credit ({tag}) 13:30")
    all_res.append(st); all_eqs[st['name']] = eq
    print(f"  {st['name']}: n={st['n']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, DD={st['maxdd_pct']}%")
    pd.DataFrame(tr).to_csv(OUT / f"rev_credit_{spread.lower()}_810.csv", index=False)

print("\n=== R-B: SELL 0DTE 12:00 skew side ===")
b_out = sell_skew_backtest()
for name, tr in b_out.items():
    st, eq = stats(tr, f"R-B · {name}")
    all_res.append(st); all_eqs[st['name']] = eq
    print(f"  {st['name']}: n={st['n']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, DD={st['maxdd_pct']}%")
    pd.DataFrame(tr).to_csv(OUT / f"rev_A_{name}.csv", index=False)
    # reason breakdown for sltp variants
    if "sltp" in name and tr:
        df = pd.DataFrame(tr)
        print(f"    exit reasons:")
        r = df.groupby("reason").agg(n=("pnl","size"),pnl_sum=("pnl","sum"),
                                      pnl_mean=("pnl","mean"),win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0)
        print(r.to_string().replace("\n","\n    "))

# yearly breakdowns for the best sell-rich-hold
print("\n=== Yearly for R-B sell_rich_hold ===")
if "sell_rich_hold" in b_out:
    df = pd.DataFrame(b_out["sell_rich_hold"])
    if len(df):
        df["date"] = pd.to_datetime(df["d"]); df["year"] = df["date"].dt.year
        # split by side
        print("  By year:")
        print(df.groupby("year").agg(n=("pnl","size"),pnl=("pnl","sum"),
                                      win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0))
        print("\n  By side sold:")
        print(df.groupby("side").agg(n=("pnl","size"),pnl=("pnl","sum"),
                                      win_pct=("pnl", lambda x: round((x>0).mean()*100,1))).round(0))

pd.DataFrame(all_res).to_csv(OUT / "reverse_tests_summary.csv", index=False)
print("\n=== SUMMARY ===")
print(pd.DataFrame(all_res).set_index("name").T.to_string())

# equity chart
fig, ax = plt.subplots(figsize=(13, 7))
colors = ['#2962ff','#26a69a','#ba68c8','#ff9800','#4dd0e1','#ef5350']
for i, (name, eq) in enumerate(all_eqs.items()):
    st = next(r for r in all_res if r["name"] == name)
    ax.plot(eq, label=f'{name}: n={st["n"]}, Sharpe {st["sharpe"]}, CAGR {st["cagr"]}%', color=colors[i%len(colors)], lw=1.3)
ax.axhline(CAP, color='#787b86', ls='--', alpha=0.5, label='Rs.10L baseline')
ax.set_ylabel('Equity (Rs.)'); ax.set_xlabel('Trade #')
ax.legend(fontsize=8, loc='best'); ax.grid(alpha=0.3)
ax.set_title('Reverse of losing setups - credit spreads @ 13:30 + SELL 0DTE skew side @ 12:00 (1 lot, real costs)')
plt.tight_layout(); plt.savefig(OUT / "reverse_tests.png", dpi=110)
print(f"\nchart -> {OUT}/reverse_tests.png")
print(f"total runtime: {time.time()-t0:.0f}s")
