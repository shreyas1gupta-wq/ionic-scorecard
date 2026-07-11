"""MEANREV_RSI_CAMPAIGN — Tests B & C (Arjun Rao / quant desk, 2026-07-07).

Test B: daily NIFTY RSI(5) extreme -> ATM option SELL, max hold 5 trading days.
  RSI(5) crosses <10 (oversold/bounce bet) -> SELL ATM PUT
  RSI(5) crosses >90 (overbought/pullback bet) -> SELL ATM CALL
Test C: same triggers -> BUY 200-OTM option in the reversion direction.
  oversold -> BUY 200-OTM CALL ; overbought -> BUY 200-OTM PUT

Two entry-style variants each:
  (i)  DELAY : signal at T close, enter T+1 at open (09:15 bar).
  (ii) LIMIT : on T+1, limit at T's close (C_T). Fill only if spot touches C_T
               (bull bet: low<=C_T ; bear bet: high>=C_T). Else DROP (D-031 no-fill=drop).

Causal: signal computed at T close, action never before T+1. One position at a time.
Costs: COST_STANDARDS (APPROVED D-021). P&L booked at EXIT (firm doctrine).
Headline metric: denominator-free RUPEE POINTS (premium points) + %spot.
"""
import sys, time, json
from pathlib import Path
from datetime import date
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, ROOT + r"\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server")
sys.path.insert(0, ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
import data_loader as dl

OUT = Path(__file__).parent
LOT = 75                 # current NIFTY lot; points metric is ~lot-independent
ENTRY_HM = 555           # 09:15 open bar (variant i)
EXIT_HM  = 900           # 15:00 for non-expiry exits
SETTLE_START, SETTLE_END = 900, 929   # 30-min settle window
MAXHOLD_TD = 5           # max hold in trading days
EXP_DTE_MIN, EXP_DTE_MAX = 3, 12      # weekly expiry pick window (calendar days from entry)

def rsi(close, period):
    d = close.diff()
    u = d.clip(lower=0); dn = -d.clip(upper=0)
    au = u.ewm(alpha=1/period, adjust=False).mean()
    ad = dn.ewm(alpha=1/period, adjust=False).mean()
    rs = au / ad.replace(0, np.nan)
    return 100 - 100/(1+rs)

# ---- costs (COST_STANDARDS APPROVED) : returns rupee cost round-trip ----
def cost_rt(entry, exit, side, slip_frac):
    """side 'sell' or 'buy'. slip_frac = one-way slippage as frac of premium."""
    brok = 40.0
    turnover = (entry + exit) * LOT
    ex_txn = 0.00035 * turnover
    ipft   = 0.000005 * turnover
    sebi   = 0.000001 * turnover
    if side == "sell":
        stt   = 0.001 * entry * LOT          # STT 0.1% on sell-side premium (entry=sell)
        stamp = 0.00003 * exit  * LOT        # stamp 0.003% on buy-side premium (exit=buy)
    else:
        stt   = 0.001 * exit  * LOT          # exit=sell
        stamp = 0.00003 * entry * LOT        # entry=buy
    gst  = 0.18 * (brok + ex_txn + ipft + sebi)
    slip = (max(0.05, slip_frac*entry) + max(0.05, slip_frac*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + slip

# ---- load spot + daily ----
s = dl._spot()
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
daily = s.groupby("d").agg(close=("close","last")).reset_index()
daily["rsi5"] = rsi(daily["close"], 5)
daily = daily.dropna(subset=["rsi5"]).reset_index(drop=True)
days_list = list(daily["d"])
DATA_MAX = max(days_list)

expiries = list(dl.expiries())
def pick_expiry(entry_day):
    cands = [e for e in expiries if EXP_DTE_MIN <= (e - entry_day).days <= EXP_DTE_MAX]
    return cands[0] if cands else None

opt_cache = {}
def get_chain(d, ex):
    k = (d, ex)
    if k not in opt_cache:
        try: opt_cache[k] = dl.load_option_day(ex, d)
        except Exception: opt_cache[k] = None
    return opt_cache[k]

def opt_price(chain, hm, K, cp, back=15, fwd=15):
    if chain is None: return None
    mi = chain["minute_index"]
    for b in range(back+1):
        row = mi.get(hm - b, {}).get((int(K), cp))
        if row and row["c"] > 0: return row["c"]
    for f in range(1, fwd+1):
        row = mi.get(hm + f, {}).get((int(K), cp))
        if row and row["c"] > 0: return row["c"]
    return None

def spot_open(d):
    arr = by_day.get(d)
    if arr is None or len(arr) == 0: return None
    return float(arr[0, 1])   # open of first bar (09:15)

def expiry_settle(exp):
    arr = by_day.get(exp)
    if arr is None or len(arr) == 0: return None
    tail = arr[(arr[:,0] >= SETTLE_START) & (arr[:,0] <= SETTLE_END)]
    if len(tail) < 3: return None
    return float(tail[:,4].mean())

def limit_fill(entry_day, level, direction):
    """direction 'bull' (bounce) fills if low<=level; 'bear' fills if high>=level.
    Returns (fill_hm, fill_spot) or None. Gap-through fills at open (price improvement)."""
    arr = by_day.get(entry_day)
    if arr is None or len(arr) == 0: return None
    op = float(arr[0,1])
    if direction == "bull":
        if op <= level: return int(arr[0,0]), op           # gaps through -> fill at open
        hit = arr[arr[:,3] <= level]                        # low <= level
        if len(hit): return int(hit[0,0]), level
    else:
        if op >= level: return int(arr[0,0]), op
        hit = arr[arr[:,2] >= level]                        # high >= level
        if len(hit): return int(hit[0,0]), level
    return None

def run(test, variant, slip_frac, otm):
    """test 'B'(sell ATM) or 'C'(buy 200-OTM); variant 'delay'/'limit'.
    otm = strike offset (0 ATM, 200 for C). Returns trades list."""
    side = "sell" if test == "B" else "buy"
    trades = []; nofill = 0
    in_pos_until = None   # trading-day index guard for one-position-at-a-time
    for i in range(1, len(daily)-1):
        r5, r5p = daily["rsi5"].iloc[i], daily["rsi5"].iloc[i-1]
        os_cross = (r5 < 10) and (r5p >= 10)     # oversold cross -> bull bet
        ob_cross = (r5 > 90) and (r5p <= 90)     # overbought cross -> bear bet
        if not (os_cross or ob_cross): continue
        if in_pos_until is not None and i <= in_pos_until: continue
        T = days_list[i]; C_T = float(daily["close"].iloc[i])
        eidx = i + 1
        if eidx >= len(days_list): break
        entry_day = days_list[eidx]
        direction = "bull" if os_cross else "bear"
        # instrument + strike direction
        if test == "B":
            cp = "PE" if os_cross else "CE"   # sell put on bounce bet, sell call on pullback
        else:
            cp = "CE" if os_cross else "PE"   # buy call on bounce bet, buy put on pullback
        # ---- entry ----
        if variant == "delay":
            entry_spot = spot_open(entry_day)
            entry_hm = ENTRY_HM
        else:
            lf = limit_fill(entry_day, C_T, direction)
            if lf is None:
                nofill += 1; continue
            entry_hm, entry_spot = lf
        if entry_spot is None: continue
        if os_cross:
            K = int(round((entry_spot - otm)/50)*50) if test=="C" else int(round(entry_spot/50)*50)
        else:
            K = int(round((entry_spot + otm)/50)*50) if test=="C" else int(round(entry_spot/50)*50)
        ex = pick_expiry(entry_day)
        if ex is None: continue
        ch = get_chain(entry_day, ex)
        entry_px = opt_price(ch, entry_hm, K, cp)
        if entry_px is None or entry_px < 0.5:
            nofill += 1; continue
        # ---- exit: min(entry+5 trading days, expiry) ----
        exit_cap_idx = min(eidx + MAXHOLD_TD, len(days_list)-1)
        exit_day = None; exit_px = None; reason = None
        for j in range(eidx+1, exit_cap_idx+1):
            dj = days_list[j]
            if dj >= ex:
                settle = expiry_settle(ex)
                if settle is None: break
                if cp == "PE": exit_px = max(0.0, K - settle)
                else:          exit_px = max(0.0, settle - K)
                exit_day = ex if dj == ex else dj; reason = "EXPIRY"; break
            if j == exit_cap_idx:
                chx = get_chain(dj, ex)
                px = opt_price(chx, EXIT_HM, K, cp)
                if px is None: px = opt_price(get_chain(dj, ex), EXIT_HM, K, cp, back=30, fwd=0)
                if px is None: break
                exit_px = px; exit_day = dj; reason = "MAXHOLD"; break
        if exit_px is None or exit_day is None:
            nofill += 1; continue
        if pd.Timestamp(exit_day) > pd.Timestamp(DATA_MAX):
            continue
        gross_pts = (entry_px - exit_px) if side=="sell" else (exit_px - entry_px)
        c = cost_rt(entry_px, exit_px, side, slip_frac)
        net_pts = gross_pts - c/LOT
        trades.append(dict(
            signal_d=str(T), entry_d=str(entry_day), exit_d=str(exit_day),
            dir=direction, cp=cp, K=K, entry_spot=round(entry_spot,1),
            entry_px=round(entry_px,2), exit_px=round(exit_px,2),
            hold_td=j-eidx, reason=reason,
            gross_pts=round(gross_pts,2), cost_pts=round(c/LOT,2),
            net_pts=round(net_pts,2), pct_spot=round(net_pts/entry_spot*100,4),
            net_rs_1lot=round(net_pts*LOT,0),
        ))
        in_pos_until = j   # flat only after exit trading-day index
    return trades, nofill

def stats(trades, name, nofill):
    if not trades:
        return dict(variant=name, n=0, nofill=nofill)
    df = pd.DataFrame(trades)
    p = df["net_pts"].values
    df["exit_d"] = pd.to_datetime(df["exit_d"]); df["entry_d"] = pd.to_datetime(df["entry_d"])
    years = max((df["exit_d"].max() - df["entry_d"].min()).days/365.25, 0.5)
    tpy = len(p)/years
    pt_sharpe = p.mean()/ (p.std()+1e-9)
    ann_sharpe = pt_sharpe * np.sqrt(max(tpy,1e-9))
    # 2x-cost stress
    p2 = df["gross_pts"].values - 2*df["cost_pts"].values
    return dict(
        variant=name, n=len(p), nofill=nofill, trades_per_yr=round(tpy,1),
        avg_hold_td=round(df["hold_td"].mean(),1),
        win_pct=round((p>0).mean()*100,1),
        mean_net_pts=round(p.mean(),2), med_net_pts=round(np.median(p),2),
        mean_pct_spot=round(df["pct_spot"].mean(),4),
        mean_cost_pts=round(df["cost_pts"].mean(),2),
        avg_win_pts=round(p[p>0].mean(),1) if (p>0).any() else 0,
        avg_loss_pts=round(p[p<0].mean(),1) if (p<0).any() else 0,
        worst_pts=round(p.min(),1), best_pts=round(p.max(),1),
        pt_sharpe=round(pt_sharpe,3), ann_sharpe=round(ann_sharpe,2),
        total_pts=round(p.sum(),1), total_rs_1lot=round(p.sum()*LOT,0),
        mean_net_pts_2x=round(p2.mean(),2), ann_sharpe_2x=round(p2.mean()/(p2.std()+1e-9)*np.sqrt(max(tpy,1e-9)),2),
    )

if __name__ == "__main__":
    t0 = time.time()
    configs = [
        ("B", "delay", 0.0025, 0),    # sell ATM, 0.25% slip
        ("B", "limit", 0.0025, 0),
        ("C", "delay", 0.01,  200),   # buy 200-OTM, 1.0% slip
        ("C", "limit", 0.01,  200),
    ]
    all_stats = []
    for test, variant, slip, otm in configs:
        name = f"Test{test}_{variant}"
        tr, nf = run(test, variant, slip, otm)
        pd.DataFrame(tr).to_csv(OUT / f"trades_{name}.csv", index=False)
        st = stats(tr, name, nf)
        all_stats.append(st)
        print(f"{name}: n={st['n']} nofill={nf} "
              f"win={st.get('win_pct')}% mean_net={st.get('mean_net_pts')}pts "
              f"ann_sharpe={st.get('ann_sharpe')} ({time.time()-t0:.0f}s)")
    pd.DataFrame(all_stats).to_csv(OUT / "stats_BC.csv", index=False)
    print("\n" + pd.DataFrame(all_stats).set_index("variant").T.to_string())
    print(f"\nruntime {time.time()-t0:.0f}s")
