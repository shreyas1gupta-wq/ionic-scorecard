"""V2 study — spreads, overnight holds, PCR/20DMA, holding-period, biweekly options.
Principal question dump 2026-07-07 follow-up. Exploratory (D-028: not a backtest).
"""
import sys, time, json
from pathlib import Path
from datetime import date
import numpy as np
import pandas as pd

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(__file__).parent
LOT = 65
COST_BUY_BPS = 5.0   # one-way
COST_SELL_BPS = 15.0
OPEN = 555
EOD = 924
LAST_ENTRY = 870

t0 = time.time()
def log(m): print(f"[{time.time()-t0:.0f}s] {m}", flush=True)

lines = ["# INTRADAY STUDY V2 — spreads / overnight / PCR / holding-period / biweekly",
         "generated 2026-07-07 · exploratory (D-028)", ""]

# ============================================================
# Setup
# ============================================================
s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(o=("open","first"), h=("high","max"), l=("low","min"), c=("close","last"))
expiries = list(dl.expiries())
def dte_of(d, k=0):
    nxt = [e for e in expiries if e >= d]
    return (nxt[k] - d).days if len(nxt) > k else -1
def expiry_of(d, k=0):
    nxt = [e for e in expiries if e >= d]
    return nxt[k] if len(nxt) > k else None

opt_cache = {}
def get_chain(d, ex):
    k = (d, ex)
    if k not in opt_cache:
        try: opt_cache[k] = dl.load_option_day(ex, d)
        except Exception: opt_cache[k] = None
    return opt_cache[k]

def opt_price(chain, hm, strike, cp, back=10):
    if chain is None: return None
    for b in range(back+1):
        row = chain["minute_index"].get(hm - b, {}).get((int(strike), cp))
        if row is not None: return row["c"]
    return None

def buy_pnl(entry, exit):
    if entry is None or exit is None: return None
    return (exit - entry) * LOT - abs(entry * LOT * 2 * COST_BUY_BPS/1e4)
def sell_pnl(entry, exit):
    if entry is None or exit is None: return None
    return (entry - exit) * LOT - abs(entry * LOT * COST_SELL_BPS/1e4)

# ============================================================
# F. SPREADS on the 100-pt race (vs naked sell)
# For each race event: SELL ATM same-side vs SELL ATM same-side + BUY 200-OTM same-side (defined-risk)
#                     SELL 200-OTM same-side vs SELL 200-OTM same-side + BUY 400-OTM same-side
# ============================================================
log("F. SPREADS on the 100-pt race")
events_f = []
for d in days_all:
    arr = by_day[d]
    if len(arr) < 360: continue
    dte = dte_of(d)
    if dte < 0 or dte > 7: continue
    ex = expiry_of(d)
    for i in range(0, len(arr)-15):
        hm0 = int(arr[i,0])
        if hm0 < OPEN or hm0 > LAST_ENTRY-15: continue
        j = i + 15
        if j >= len(arr): break
        if int(arr[j,0]) - hm0 > 20: continue
        move = arr[j,4] - arr[i,1]
        if abs(move) < 100: continue
        e_hm = int(arr[j,0]); e_spot = arr[j,4]
        sgn = 1 if move > 0 else -1
        atm = int(round(e_spot / 50) * 50)
        cp = "CE" if sgn > 0 else "PE"
        # exit
        exit_hm = min(e_hm+60, EOD)
        idx_ex = min(np.searchsorted(arr[:,0], exit_hm), len(arr)-1)
        x_hm = int(arr[idx_ex,0])
        ch = get_chain(d, ex)
        # naked ATM sell same-side + hedge = SELL ATM CE / BUY ATM+200 CE
        atm_sell_e = opt_price(ch, e_hm, atm, cp); atm_sell_x = opt_price(ch, x_hm, atm, cp)
        hedge_atm_e = opt_price(ch, e_hm, atm + (200 if sgn>0 else -200), cp)
        hedge_atm_x = opt_price(ch, x_hm, atm + (200 if sgn>0 else -200), cp)
        # naked 200-OTM sell + hedge = SELL 200-OTM + BUY 400-OTM
        far_sell_e = opt_price(ch, e_hm, atm + (200 if sgn>0 else -200), cp)
        far_sell_x = opt_price(ch, x_hm, atm + (200 if sgn>0 else -200), cp)
        hedge_far_e = opt_price(ch, e_hm, atm + (400 if sgn>0 else -400), cp)
        hedge_far_x = opt_price(ch, x_hm, atm + (400 if sgn>0 else -400), cp)
        # spreads: net = sell_pnl(near) + buy_pnl(far)
        naked_atm = sell_pnl(atm_sell_e, atm_sell_x)
        naked_far = sell_pnl(far_sell_e, far_sell_x)
        spread_atm = None
        if all(x is not None for x in (atm_sell_e, atm_sell_x, hedge_atm_e, hedge_atm_x)):
            spread_atm = sell_pnl(atm_sell_e, atm_sell_x) + buy_pnl(hedge_atm_e, hedge_atm_x)
        spread_far = None
        if all(x is not None for x in (far_sell_e, far_sell_x, hedge_far_e, hedge_far_x)):
            spread_far = sell_pnl(far_sell_e, far_sell_x) + buy_pnl(hedge_far_e, hedge_far_x)
        if naked_atm is None or naked_far is None: continue
        events_f.append(dict(d=str(d), dte=dte, sign=sgn,
                             naked_atm=naked_atm, spread_atm=spread_atm,
                             naked_far=naked_far, spread_far=spread_far))
log(f"F events: {len(events_f)}")
ef = pd.DataFrame(events_f)
if len(ef):
    def stats(g, col):
        s = g[col].dropna()
        if len(s) < 20: return dict(n=len(s), win=None, mean=None, med=None, std=None)
        return dict(n=len(s),
                    win=round((s>0).mean()*100,1),
                    mean=round(s.mean(),0),
                    med=round(s.median(),0),
                    std=round(s.std(),0),
                    sharpe=round(s.mean()/max(1,s.std()),2))
    ef["dte_b"] = pd.cut(ef["dte"], bins=[-1,0,1,3,7], labels=["0DTE","1DTE","2-3DTE","4-7DTE"])
    def compare_naked_vs_spread(g):
        return pd.Series({
            "n": len(g),
            "naked_atm_win": round((g["naked_atm"]>0).mean()*100, 1),
            "naked_atm_mean": round(g["naked_atm"].mean(), 0),
            "naked_atm_sharpe": round(g["naked_atm"].mean()/max(1,g["naked_atm"].std()), 2),
            "spread_atm_win": round((g["spread_atm"].dropna()>0).mean()*100, 1),
            "spread_atm_mean": round(g["spread_atm"].mean(), 0),
            "spread_atm_sharpe": round(g["spread_atm"].mean()/max(1,g["spread_atm"].std()), 2),
            "naked_far_win": round((g["naked_far"]>0).mean()*100, 1),
            "naked_far_mean": round(g["naked_far"].mean(), 0),
            "naked_far_sharpe": round(g["naked_far"].mean()/max(1,g["naked_far"].std()), 2),
            "spread_far_win": round((g["spread_far"].dropna()>0).mean()*100, 1),
            "spread_far_mean": round(g["spread_far"].mean(), 0),
            "spread_far_sharpe": round(g["spread_far"].mean()/max(1,g["spread_far"].std()), 2),
        })
    lines += ["## F. NAKED SELL vs DEFINED-RISK SPREAD (100-pt race, 60m hold)",
              "  ATM-spread = SELL ATM + BUY 200-OTM same-side (bear-call / bull-put)",
              "  FAR-spread = SELL 200-OTM + BUY 400-OTM same-side (further-OTM spread)",
              "  Sharpe = mean/std of per-event P&L (risk-adjusted)", ""]
    lines.append(compare_naked_vs_spread(ef).to_frame("all").T.to_string())
    lines += ["", "### By DTE"]
    lines.append(ef.groupby("dte_b", observed=False).apply(compare_naked_vs_spread, include_groups=False).to_string())
    lines += [""]
    ef.to_csv(OUT / "spreads.csv", index=False)

# ============================================================
# G. HOLDING PERIOD: intraday vs overnight vs 2-3d vs to-expiry
# For a fixed setup (sell 200-OTM PE on RSI<30 or after 100-pt down move at DTE 2-3),
# hold to 15:24 sim day vs 15:24 next day vs 3 trading days vs expiry.
# ============================================================
log("G. HOLDING PERIOD")
# Simpler: for every eligible (d, dte 2-3) day sample, at 09:30 sell ATM+200 PE, exit at:
#   T0=EOD-sim, T1=EOD+1, T2=EOD+2, T3=EOD+3, Texp=expiry-day EOD or day before expiry EOD
events_g = []
for d in days_all[::2]:  # every 2nd eligible day
    arr = by_day[d]
    if len(arr) < 360: continue
    dte = dte_of(d)
    if not (2 <= dte <= 3): continue
    ex = expiry_of(d)
    ch = get_chain(d, ex)
    if ch is None: continue
    idx_e = np.searchsorted(arr[:,0], 570)  # 09:30
    if idx_e >= len(arr): continue
    e_spot = arr[idx_e, 4]
    atm = int(round(e_spot / 50) * 50)
    K = atm - 200  # sell OTM PE
    p_e = opt_price(ch, 570, K, "PE")
    if p_e is None or p_e < 3: continue
    # exits: same-day EOD, next-day EOD, day-after EOD
    idx_x0 = min(np.searchsorted(arr[:,0], EOD), len(arr)-1)
    p_x0 = opt_price(ch, int(arr[idx_x0,0]), K, "PE")
    # next-day within same expiry (if not yet expired)
    di = days_all.index(d)
    p_x1 = None; p_x2 = None
    if di+1 < len(days_all) and days_all[di+1] <= ex:
        d1 = days_all[di+1]
        ch1 = get_chain(d1, ex)
        if ch1:
            arr1 = by_day[d1]
            idx = min(np.searchsorted(arr1[:,0], EOD), len(arr1)-1)
            p_x1 = opt_price(ch1, int(arr1[idx,0]), K, "PE")
    if di+2 < len(days_all) and days_all[di+2] <= ex:
        d2 = days_all[di+2]
        ch2 = get_chain(d2, ex)
        if ch2:
            arr2 = by_day[d2]
            idx = min(np.searchsorted(arr2[:,0], EOD), len(arr2)-1)
            p_x2 = opt_price(ch2, int(arr2[idx,0]), K, "PE")
    # to-expiry: settle = max(0, K - close_of_expiry); we approximate close_of_expiry
    ce_i = days_all.index(ex) if ex in days_all else None
    p_xexp = None
    if ce_i is not None:
        arr_e = by_day[ex]
        # last-30-min settle
        tail = arr_e[(arr_e[:,0]>=900)]
        if len(tail) > 5:
            settle = tail[:,4].mean()
            p_xexp = max(0.0, K - settle)
    events_g.append(dict(d=str(d), dte=dte, K=K, entry=p_e, x0=p_x0, x1=p_x1, x2=p_x2, xexp=p_xexp))
log(f"G events: {len(events_g)}")
eg = pd.DataFrame(events_g)
if len(eg):
    for col in ("x0","x1","x2","xexp"):
        eg[f"pnl_{col}"] = eg.apply(lambda r: sell_pnl(r["entry"], r[col]) if pd.notna(r[col]) else None, axis=1)
    def hp_stats(col):
        s = eg[f"pnl_{col}"].dropna()
        return dict(n=len(s), win=round((s>0).mean()*100,1),
                    mean=round(s.mean(),0), med=round(s.median(),0),
                    std=round(s.std(),0),
                    sharpe=round(s.mean()/max(1,s.std()),2))
    lines += ["## G. HOLDING PERIOD (sell 200-OTM PE at 09:30 on DTE 2-3 days)"]
    t = pd.DataFrame({k: hp_stats(k) for k in ("x0","x1","x2","xexp")}).T
    t.index = ["intraday (EOD)", "overnight (+1 EOD)", "+2 days", "to expiry"]
    lines.append(t.to_string())
    lines += [""]
    eg.to_csv(OUT / "holding_period.csv", index=False)

# ============================================================
# H. WEEKLY vs BIWEEKLY — same 09:30 entry, DTE-matched exit
# ============================================================
log("H. WEEKLY vs BIWEEKLY")
events_h = []
for d in days_all[::2]:
    arr = by_day[d]
    if len(arr) < 360: continue
    dte1 = dte_of(d, 0); dte2 = dte_of(d, 1)
    if dte1 < 0 or dte2 < 0: continue
    ex1 = expiry_of(d, 0); ex2 = expiry_of(d, 1)
    ch1 = get_chain(d, ex1); ch2 = get_chain(d, ex2)
    if ch1 is None or ch2 is None: continue
    idx_e = np.searchsorted(arr[:,0], 570)
    if idx_e >= len(arr): continue
    e_spot = arr[idx_e, 4]
    atm = int(round(e_spot / 50) * 50)
    K = atm - 200  # OTM PE (repeat the winning cell)
    # entry and same-day EOD exit for both weekly and biweekly
    for tag, ex, ch in (("w1", ex1, ch1), ("w2", ex2, ch2)):
        p_e = opt_price(ch, 570, K, "PE")
        if p_e is None or p_e < 2: continue
        idx_x = min(np.searchsorted(arr[:,0], EOD), len(arr)-1)
        p_x = opt_price(ch, int(arr[idx_x,0]), K, "PE")
        if p_x is None: continue
        events_h.append(dict(d=str(d), tag=tag, dte=(ex-d).days,
                             entry=p_e, exit=p_x,
                             pnl=sell_pnl(p_e, p_x)))
log(f"H events: {len(events_h)}")
eh = pd.DataFrame(events_h)
if len(eh):
    def w_stats(g):
        return pd.Series(dict(n=len(g), avg_dte=round(g["dte"].mean(),1),
                              avg_entry_prem=round(g["entry"].mean(),1),
                              win=round((g["pnl"]>0).mean()*100,1),
                              mean=round(g["pnl"].mean(),0),
                              med=round(g["pnl"].median(),0),
                              sharpe=round(g["pnl"].mean()/max(1,g["pnl"].std()),2)))
    lines += ["## H. WEEKLY (front) vs BIWEEKLY (next weekly) — sell 200-OTM PE, intraday",
              eh.groupby("tag").apply(w_stats, include_groups=False).to_string(), ""]
    eh.to_csv(OUT / "weekly_biweekly.csv", index=False)

# ============================================================
# I. PCR / 20DMA — daily signals for next-day directional bias
# ============================================================
log("I. PCR / 20DMA")
# 20DMA
daily["sma20"] = daily["c"].rolling(20).mean()
daily["above_20dma"] = (daily["c"] > daily["sma20"]).astype(int)
daily["next_ret"] = daily["c"].pct_change().shift(-1) * 1e4  # bps
daily["next_5d_ret"] = (daily["c"].shift(-5) / daily["c"] - 1) * 1e4
# PCR from OI: sum PE OI / sum CE OI on front expiry as of day D
# We'll compute for a sample only (expiry file loads are expensive) — reuse cache
log("  computing PCR on sample days")
sample = days_all[::5]  # every 5th day (~250 days)
pcrs = {}
for d in sample:
    ex = expiry_of(d)
    if ex is None: continue
    ch = get_chain(d, ex)
    if ch is None: continue
    # OI at 15:20 (or last available)
    ce_oi = pe_oi = 0
    for k, b in ch["minute_index"].get(920, {}).items():
        strike, cp = k
        (ce_oi := ce_oi + b["oi"]) if cp == "CE" else (pe_oi := pe_oi + b["oi"])
    if ce_oi > 0: pcrs[d] = pe_oi / ce_oi
log(f"  {len(pcrs)} PCR values")
daily["pcr"] = daily.index.map(pcrs)
# report
def sig_stats(sub, ret_col):
    s = sub[ret_col].dropna()
    return dict(n=len(s), mean_bps=round(s.mean(),1),
                up_pct=round((s>0).mean()*100,1))
lines += ["## I. PCR / 20DMA daily signal"]
lines += ["### 20DMA state → next-day return"]
for state, name in [(1, "close > 20DMA"), (0, "close <= 20DMA")]:
    r = sig_stats(daily[daily["above_20dma"]==state], "next_ret")
    lines.append(f"  {name}: n={r['n']}, next-day mean={r['mean_bps']}bps, up%={r['up_pct']}%")
lines += ["", "### 20DMA state → next-5d return"]
for state, name in [(1, "close > 20DMA"), (0, "close <= 20DMA")]:
    r = sig_stats(daily[daily["above_20dma"]==state], "next_5d_ret")
    lines.append(f"  {name}: n={r['n']}, next-5d mean={r['mean_bps']}bps, up%={r['up_pct']}%")
# PCR bins
dpcr = daily.dropna(subset=["pcr","next_ret"])
lines += ["", f"### PCR (sum PE-OI / CE-OI on front expiry, 15:20) → next-day return (n={len(dpcr)})"]
if len(dpcr) >= 40:
    dpcr["pcr_q"] = pd.qcut(dpcr["pcr"], 5, duplicates="drop")
    tbl = dpcr.groupby("pcr_q", observed=False).agg(n=("next_ret","size"),
                                       mean_next=("next_ret","mean"),
                                       up_pct=("next_ret", lambda x: (x>0).mean()*100))
    tbl = tbl.round(1)
    lines.append(tbl.to_string())
lines += [""]
daily.to_csv(OUT / "daily_signals.csv")

lines += [f"\n---\nruntime: {time.time()-t0:.0f}s"]
(OUT / "REPORT_V2.md").write_text("\n".join(lines), encoding="utf-8")
log("DONE → REPORT_V2.md")
