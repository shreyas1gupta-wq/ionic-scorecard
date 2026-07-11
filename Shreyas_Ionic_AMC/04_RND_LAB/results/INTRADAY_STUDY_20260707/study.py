"""Intraday microstructure study — Principal question dump 2026-07-07.

Sections:
  A. Time-of-day: big moves, direction persistence, shakeouts
  B. Day-of-week & DTE effects
  C. The 100-pt / 15-min race: 200OTM-opp-BUY vs ATM-same-SELL vs 200OTM-same-SELL
  D. Strike-moneyness x DTE for buying and selling (ATM/±50/±100/±150/±200)
  E. Indicator lift: 9/21 EMA (5m,15m), VWAP, PDH/PDL, PWH/PWL, VIX band

Exploratory (D-028: not a backtest, no Gate-4 claim). Costs approximated per COST_STANDARDS
draft: option BUY = -1 tick + 0.05% one-way; SELL = same + 0.1% STT on premium.
"""
import sys, time
from pathlib import Path
from datetime import date, timedelta
import numpy as np
import pandas as pd

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(__file__).parent
LOT = 65
TICK = 0.05
COST_BUY_BPS = 5.0   # entry+exit brokerage/txn/GST/stamp on premium, one-way ~= 5bps
COST_SELL_BPS = 15.0 # +STT 0.1% sell side; round-trip on premium
LAST_ENTRY = 870     # 14:30
EOD = 924            # 15:24
OPEN = 555           # 09:15

def hm_str(hm): return f"{hm//60:02d}:{hm%60:02d}"

t0 = time.time()
lines = [f"# INTRADAY STUDY — NIFTY 2021-06 → 2026-06 (D-028 exploratory)",
         f"generated 2026-07-07 · win-race = ±20bps first-touch (60m) · costs approx",
         ""]

# ============================================================
# Load spot + build per-day arrays once
# ============================================================
s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(o=("open","first"), h=("high","max"), l=("low","min"), c=("close","last"))
daily["ret_pct"] = (daily["c"]/daily["o"] - 1) * 100
daily["rng_pct"] = (daily["h"]-daily["l"]) / daily["o"] * 100
daily["pdh"] = daily["h"].shift(1); daily["pdl"] = daily["l"].shift(1)
daily["pwh"] = daily["h"].rolling(5).max().shift(1); daily["pwl"] = daily["l"].rolling(5).min().shift(1)
daily["dow"] = pd.to_datetime(daily.index).dayofweek

# expiry calendar for DTE
expiries = list(dl.expiries())
def dte_of(d):
    nxt = [e for e in expiries if e >= d]
    return (nxt[0] - d).days if nxt else -1
daily["dte"] = [dte_of(d) for d in daily.index]

# ============================================================
# A. Time-of-day: big moves, persistence, shakeouts
# ============================================================
lines += ["## A. TIME-OF-DAY WINDOWS (15-min buckets, IST)"]
buckets = list(range(OPEN, 930, 15))  # 09:15 .. 15:15
window_stats = []
for b in buckets:
    ranges = []; ret15 = []; ret_rest = []
    for d in days_all:
        arr = by_day[d]
        m = (arr[:,0] >= b) & (arr[:,0] < b+15)
        w = arr[m]
        if len(w) < 10: continue
        rng = (w[:,2].max() - w[:,3].min()) / w[0,1] * 1e4
        r = (w[-1,4] - w[0,1]) / w[0,1] * 1e4
        # remainder of day return from bucket close to EOD
        end_idx = np.searchsorted(arr[:,0], EOD, side="right") - 1
        rem = (arr[end_idx,4] - w[-1,4]) / w[-1,4] * 1e4
        ranges.append(rng); ret15.append(r); ret_rest.append(rem)
    if not ranges: continue
    ranges = np.array(ranges); ret15 = np.array(ret15); ret_rest = np.array(ret_rest)
    # persistence: correlation of window direction with rest-of-day direction (SAMESIGN%)
    same_sign = ((np.sign(ret15) == np.sign(ret_rest)) & (np.abs(ret15) > 5)).mean() * 100
    # shakeout%: window makes a new session extreme then closes back inside range so far
    shk = 0; nshk = 0
    for d in days_all:
        arr = by_day[d]
        m_day = arr[:,0] < b; m_win = (arr[:,0] >= b) & (arr[:,0] < b+15)
        pre = arr[m_day]; win = arr[m_win]
        if len(pre) < 5 or len(win) < 10: continue
        nshk += 1
        pre_h, pre_l = pre[:,2].max(), pre[:,3].min()
        win_h, win_l = win[:,2].max(), win[:,3].min()
        wc = win[-1,4]
        if (win_h > pre_h and wc < pre_h) or (win_l < pre_l and wc > pre_l):
            shk += 1
    window_stats.append(dict(
        window=f"{hm_str(b)}-{hm_str(b+15)}",
        n=len(ranges),
        med_range_bps=round(np.median(ranges), 1),
        p90_range_bps=round(np.percentile(ranges, 90), 1),
        mean_abs_ret_bps=round(np.mean(np.abs(ret15)), 1),
        persist_pct=round(same_sign, 1),
        shakeout_pct=round(shk/nshk*100 if nshk else 0, 1),
    ))
df_a = pd.DataFrame(window_stats)
lines += ["### Median range, |return|, persistence into EOD, and shakeout% per 15-min window",
          df_a.to_string(index=False), ""]

# ============================================================
# B. Day-of-week × DTE effects on daily behaviour
# ============================================================
lines += ["## B. DAY-OF-WEEK × DTE"]
dow_lbl = {0:"Mon",1:"Tue",2:"Wed",3:"Thu",4:"Fri"}
# note: expiry weekday changed Thu->Tue in Sep-2025; DTE captures both eras uniformly
def daily_stats(g):
    return pd.Series(dict(
        n=len(g),
        range_bps=round(g["rng_pct"].mean()*100, 1),
        abs_ret_bps=round(g["ret_pct"].abs().mean()*100, 1),
        up_pct=round((g["ret_pct"]>0).mean()*100, 1),
    ))
b1 = daily.groupby("dow").apply(daily_stats, include_groups=False).reset_index()
b1["dow"] = b1["dow"].map(dow_lbl).fillna(b1["dow"].astype(str))
lines += ["### By calendar day-of-week (all days)", b1.to_string(index=False), ""]
b2 = daily[daily["dte"].between(0,7)].groupby("dte").apply(daily_stats, include_groups=False).reset_index()
lines += ["### By DTE (front weekly, 0=expiry day)", b2.to_string(index=False), ""]

# ============================================================
# C. The 100-pt / 15-min race: three responses
# ============================================================
lines += ["## C. THE 100-POINT / 15-MIN RACE"]
lines += ["Find every 15-min window with |Δ| ≥ 100 pts (~40-50bps @ NIFTY 20-25k).",
          "Entry = end of window; hold 60 min or EOD, whichever first.",
          "Fair compare: **premium P&L per lot of net delta risk** (option prices from 1-min chain).",
          ""]

# Cache option-day loads across events on the same day+expiry
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

# scan events
events_c = []
for d in days_all:
    arr = by_day[d]
    if len(arr) < 360: continue
    dte = dte_of(d)
    if dte < 0 or dte > 7: continue
    ex = [e for e in expiries if e >= d][0]
    # sliding 15-min windows
    for i in range(0, len(arr)-15):
        hm0 = int(arr[i,0])
        if hm0 < OPEN or hm0 > LAST_ENTRY-15: continue
        # need bar exactly 15m later on/before
        j = i + 15
        if j >= len(arr): break
        if int(arr[j,0]) - hm0 > 20: continue  # gap in data
        move = arr[j,4] - arr[i,1]
        if abs(move) < 100: continue
        # entry at j
        e_hm = int(arr[j,0]); e_spot = arr[j,4]
        sign = 1 if move > 0 else -1
        # ATM to nearest 50
        atm = int(round(e_spot / 50) * 50)
        same_cp = "CE" if sign > 0 else "PE"    # 'same direction' side = the leg that WOULD profit if it continues
        opp_cp = "PE" if sign > 0 else "CE"
        # 200 OTM opposite (BUY)
        opp_strike = atm - 200 if sign > 0 else atm + 200
        # 200 OTM same (SELL far)
        same_far = atm + 200 if sign > 0 else atm - 200
        ch = get_chain(d, ex)
        p_opp = opt_price(ch, e_hm, opp_strike, opp_cp)
        p_same_atm = opt_price(ch, e_hm, atm, same_cp)
        p_same_far = opt_price(ch, e_hm, same_far, same_cp)
        # forward: exit at min(e_hm+60, EOD)
        exit_hm = min(e_hm+60, EOD)
        k = i + 60 if i+60 < len(arr) else len(arr)-1
        # find bar closest to exit_hm
        idx_ex = np.searchsorted(arr[:,0], exit_hm)
        if idx_ex >= len(arr): idx_ex = len(arr)-1
        x_hm = int(arr[idx_ex,0])
        x_opp = opt_price(ch, x_hm, opp_strike, opp_cp)
        x_same_atm = opt_price(ch, x_hm, atm, same_cp)
        x_same_far = opt_price(ch, x_hm, same_far, same_cp)
        if None in (p_opp, p_same_atm, p_same_far, x_opp, x_same_atm, x_same_far):
            continue
        # per-lot P&L in Rs, then in ROI% on premium debited (buy) / margin (approx)
        def buy_pnl_bps(entry, exit):
            gross = (exit - entry) * LOT
            cost_pct = COST_BUY_BPS * 2 / 1e4
            return gross - abs(entry * LOT * cost_pct)   # rupee net; premium debit = entry*LOT
        def sell_pnl_bps(entry, exit):
            gross = (entry - exit) * LOT
            cost_pct = COST_SELL_BPS / 1e4              # STT+txn+GST — one-way (sell open + buy close mostly)
            return gross - abs(entry * LOT * cost_pct)
        events_c.append(dict(
            d=str(d), dte=dte, e_hm=e_hm, move=int(move), sign=sign,
            opp_buy_pnl=buy_pnl_bps(p_opp, x_opp),          # BUY 200 OTM opposite (fade)
            atm_sell_pnl=sell_pnl_bps(p_same_atm, x_same_atm),  # SELL ATM same-side (fade w/ premium)
            far_sell_pnl=sell_pnl_bps(p_same_far, x_same_far),  # SELL 200 OTM same-side (safer fade)
            opp_prem=p_opp, atm_prem=p_same_atm, far_prem=p_same_far,
        ))

ec = pd.DataFrame(events_c)
if len(ec) == 0:
    lines += ["**NO EVENTS FOUND** — check option-price lookup", ""]
else:
    lines += [f"### Events found: {len(ec)} (across {ec['d'].nunique()} days)"]
    def race_stats(g):
        return pd.Series(dict(
            n=len(g),
            opp_buy_win=round((g["opp_buy_pnl"]>0).mean()*100,1),
            opp_buy_mean=round(g["opp_buy_pnl"].mean(),0),
            opp_buy_med=round(g["opp_buy_pnl"].median(),0),
            atm_sell_win=round((g["atm_sell_pnl"]>0).mean()*100,1),
            atm_sell_mean=round(g["atm_sell_pnl"].mean(),0),
            atm_sell_med=round(g["atm_sell_pnl"].median(),0),
            far_sell_win=round((g["far_sell_pnl"]>0).mean()*100,1),
            far_sell_mean=round(g["far_sell_pnl"].mean(),0),
            far_sell_med=round(g["far_sell_pnl"].median(),0),
        ))
    lines += ["### All events (per-lot Rs P&L on 60m hold)", race_stats(ec).to_frame("all").T.to_string(), ""]
    lines += ["### By DTE bucket"]
    ec["dte_b"] = pd.cut(ec["dte"], bins=[-1,0,1,3,7], labels=["0DTE","1DTE","2-3DTE","4-7DTE"])
    lines.append(ec.groupby("dte_b", observed=False).apply(race_stats, include_groups=False).to_string())
    lines += ["", "### By move direction (sign +1=up spike, -1=down spike)"]
    lines.append(ec.groupby("sign").apply(race_stats, include_groups=False).to_string())
    lines += ["", "### By hour of entry"]
    ec["hour"] = ec["e_hm"] // 60
    lines.append(ec.groupby("hour").apply(race_stats, include_groups=False).to_string())
    lines += [""]

# ============================================================
# D. Strike moneyness × DTE — buying vs selling, EOD hold
# ============================================================
lines += ["## D. STRIKE × DTE — BUY vs SELL (09:30 entry, EOD exit)"]
strike_moneyness = [-200,-100,-50,0,50,100,200]   # 0 = ATM (rounded to 50); +ve = OTM for CE / ITM for PE
rows_d = []
# sample days — use every 3rd eligible day to keep runtime bounded
sample_days = days_all[::3]
for d in sample_days:
    arr = by_day[d]
    if len(arr) < 360: continue
    dte = dte_of(d)
    if dte < 0 or dte > 7: continue
    ex = [e for e in expiries if e >= d][0]
    ch = get_chain(d, ex)
    if ch is None: continue
    e_hm = 570  # 09:30
    x_hm = EOD
    idx_e = np.searchsorted(arr[:,0], e_hm)
    if idx_e >= len(arr): continue
    e_spot = arr[idx_e, 4]
    atm = int(round(e_spot / 50) * 50)
    for off in strike_moneyness:
        for cp in ("CE","PE"):
            K = atm + off
            pe = opt_price(ch, e_hm, K, cp)
            px = opt_price(ch, x_hm, K, cp)
            if pe is None or px is None or pe <= 0.5: continue
            buy = (px - pe) * LOT - abs(pe * LOT * 2 * COST_BUY_BPS/1e4)
            sell = (pe - px) * LOT - abs(pe * LOT * COST_SELL_BPS/1e4)
            rows_d.append(dict(dte=dte, off=off, cp=cp, entry=pe, exit=px, buy=buy, sell=sell))
sd = pd.DataFrame(rows_d)
if len(sd):
    sd["dte_b"] = pd.cut(sd["dte"], bins=[-1,0,1,3,7], labels=["0DTE","1DTE","2-3DTE","4-7DTE"])
    def strike_stats(g):
        return pd.Series(dict(n=len(g),
            entry_prem_med=round(g["entry"].median(),1),
            buy_mean=round(g["buy"].mean(),0),
            buy_med=round(g["buy"].median(),0),
            buy_win=round((g["buy"]>0).mean()*100,1),
            sell_mean=round(g["sell"].mean(),0),
            sell_med=round(g["sell"].median(),0),
            sell_win=round((g["sell"]>0).mean()*100,1),
        ))
    for dte_b in sd["dte_b"].dropna().unique():
        sub = sd[sd["dte_b"] == dte_b]
        t = sub.groupby(["cp","off"]).apply(strike_stats, include_groups=False).reset_index()
        lines += [f"### {dte_b} — 09:30 entry, EOD exit, per lot Rs (offset from ATM; -50 = ATM-50 = ITM CE / OTM PE)",
                  t.to_string(index=False), ""]
else:
    lines += ["**strike table empty**", ""]

# ============================================================
# E. Indicator lift over baseline
# ============================================================
lines += ["## E. INDICATOR LIFT (spot, forward-15m and forward-60m returns)"]
# baseline forward return distribution per bar (5m folded)
def fold(arr, tf):
    hm, o, h, l, c = arr.T
    idx = ((hm - OPEN) // tf).astype(int)
    keep = idx >= 0
    hm, o, h, l, c, idx = hm[keep], o[keep], h[keep], l[keep], c[keep], idx[keep]
    j_arr = np.unique(idx)
    out = []
    for j in j_arr:
        m = idx == j
        out.append((OPEN + (int(j)+1)*tf, o[m][0], h[m].max(), l[m].min(), c[m][-1]))
    return np.array(out)

def ema(arr, n):
    a = 2/(n+1); out = np.zeros_like(arr, dtype=float); out[0] = arr[0]
    for i in range(1, len(arr)): out[i] = a*arr[i] + (1-a)*out[i-1]
    return out

def collect_indicator_rows():
    rows = []
    vix_1m = None
    try:
        # daily VIX open-of-day for band
        vixp = pd.read_parquet(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\intraday_options_strategy\datasets\processed\vix_1min.parquet")
        vixp = vixp.reset_index()
        vixp["d"] = pd.to_datetime(vixp["dt"]).dt.date
        vix_1m = vixp.groupby("d")["vix"].first()
    except Exception: pass
    for d in days_all:
        arr = by_day[d]
        if len(arr) < 360: continue
        f5 = fold(arr, 5); f15 = fold(arr, 15)
        if len(f5) < 30 or len(f15) < 15: continue
        e9 = ema(f5[:,4], 9); e21 = ema(f5[:,4], 21)
        e9_15 = ema(f15[:,4], 9); e21_15 = ema(f15[:,4], 21)
        # RSI(14) 15m
        diff = np.diff(f15[:,4], prepend=f15[0,4])
        up = np.where(diff>0, diff, 0); dn = np.where(diff<0, -diff, 0)
        au = pd.Series(up).ewm(alpha=1/14, adjust=False).mean().values
        ad = pd.Series(dn).ewm(alpha=1/14, adjust=False).mean().values
        rsi = 100 - 100/(1 + au/np.maximum(ad, 1e-9))
        # VWAP (typical, on 1m — index has no volume so equal-weight = SMA of typical)
        tp = (arr[:,2] + arr[:,3] + arr[:,4]) / 3
        vwap = np.cumsum(tp) / np.arange(1, len(tp)+1)
        # PDH/PDL/PWH/PWL for this day
        di = days_all.index(d)
        if di < 6: continue
        pdh, pdl = daily.iloc[di]["pdh"], daily.iloc[di]["pdl"]
        pwh, pwl = daily.iloc[di]["pwh"], daily.iloc[di]["pwl"]
        vix_open = float(vix_1m.get(d, np.nan)) if vix_1m is not None else np.nan
        # iterate 5m bars, entry at bar close, forward 15m + 60m in bps
        hm5 = f5[:,0]; c5 = f5[:,4]
        for j in range(6, len(f5)):
            if hm5[j] > LAST_ENTRY: break
            # forward returns from 1m
            idx_now = np.searchsorted(arr[:,0], hm5[j])
            if idx_now >= len(arr): continue
            spot = arr[idx_now, 4]
            i15 = min(idx_now + 15, len(arr)-1)
            i60 = min(idx_now + 60, len(arr)-1)
            r15 = (arr[i15,4] - spot)/spot * 1e4
            r60 = (arr[i60,4] - spot)/spot * 1e4
            # indicators at bar j
            ema9 = e9[j]; ema21 = e21[j]
            j15 = min(hm5[j] // 15, len(f15)-1)
            j15 = int((hm5[j] - OPEN) // 15)
            if j15 >= len(f15): continue
            ema9_15 = e9_15[j15]; ema21_15 = e21_15[j15]
            rsi_val = rsi[j15]
            vw = vwap[idx_now]
            near_pdh = 1 if abs(spot - pdh) < 0.001*pdh else 0
            near_pdl = 1 if abs(spot - pdl) < 0.001*pdl else 0
            near_pwh = 1 if abs(spot - pwh) < 0.001*pwh else 0
            near_pwl = 1 if abs(spot - pwl) < 0.001*pwl else 0
            rows.append(dict(
                r15=r15, r60=r60, spot=spot,
                ema5_bull = 1 if ema9 > ema21 else -1,
                ema15_bull = 1 if ema9_15 > ema21_15 else -1,
                rsi=rsi_val, vwap_side = 1 if spot > vw else -1,
                near_pdh=near_pdh, near_pdl=near_pdl, near_pwh=near_pwh, near_pwl=near_pwl,
                vix=vix_open,
            ))
    return pd.DataFrame(rows)

ind = collect_indicator_rows()
lines += [f"### {len(ind):,} bar-observations · baseline mean r15 = {ind['r15'].mean():.2f}bps / r60 = {ind['r60'].mean():.2f}bps",
          f"   baseline P(r60 > 0) = {(ind['r60']>0).mean()*100:.1f}%"]

def signal_lift(df, cond, label):
    sub = df[cond]
    if len(sub) < 200: return None
    return dict(signal=label, n=len(sub),
                r15_mean=round(sub["r15"].mean(),2), r60_mean=round(sub["r60"].mean(),2),
                up_pct_r60=round((sub["r60"]>0).mean()*100,1),
                dir_edge_bps = round(sub["r60"].mean() - df["r60"].mean(), 2))

sigs = []
for lbl, cond in [
    ("EMA9>21 5m",  ind["ema5_bull"]==1),
    ("EMA9<21 5m",  ind["ema5_bull"]==-1),
    ("EMA9>21 15m", ind["ema15_bull"]==1),
    ("EMA9<21 15m", ind["ema15_bull"]==-1),
    ("Above VWAP",  ind["vwap_side"]==1),
    ("Below VWAP",  ind["vwap_side"]==-1),
    ("5m bull + Above VWAP", (ind["ema5_bull"]==1)&(ind["vwap_side"]==1)),
    ("5m bear + Below VWAP", (ind["ema5_bull"]==-1)&(ind["vwap_side"]==-1)),
    ("RSI<30 15m", ind["rsi"]<30),
    ("RSI>70 15m", ind["rsi"]>70),
    ("Near PDH", ind["near_pdh"]==1),
    ("Near PDL", ind["near_pdl"]==1),
    ("Near PWH", ind["near_pwh"]==1),
    ("Near PWL", ind["near_pwl"]==1),
    ("VIX <13",  ind["vix"]<13),
    ("VIX 13-17",(ind["vix"]>=13)&(ind["vix"]<17)),
    ("VIX 17-25",(ind["vix"]>=17)&(ind["vix"]<25)),
    ("VIX >25",  ind["vix"]>=25),
]:
    r = signal_lift(ind, cond, lbl)
    if r: sigs.append(r)
df_e = pd.DataFrame(sigs)
lines += ["### Signal → forward return lift over baseline",
          df_e.to_string(index=False),
          "",
          "**Interpretation:** `dir_edge_bps` > 3 = meaningfully directional (bull signals should be +; bear signals should be -).",
          ""]

# ============================================================
# Write output
# ============================================================
lines += [f"\n---\nruntime: {time.time()-t0:.0f}s · full CSVs saved alongside"]
(OUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
if len(ec): ec.to_csv(OUT / "race_events.csv", index=False)
if len(sd): sd.to_csv(OUT / "strike_dte.csv", index=False)
ind.to_csv(OUT / "indicators.csv", index=False)
print(f"DONE in {time.time()-t0:.0f}s → REPORT.md ({len(lines)} lines)")
