"""Velocity-triggered 100-OTM option sell.
Signal: |spot_return_over_Y_minutes| > X pct.
Two directions per event:
  FADE     - sell 100-OTM in the direction of the move (up-move -> sell CE, down-move -> sell PE).
  FOLLOW   - sell 100-OTM opposite direction (up-move -> sell PE, down-move -> sell CE).
Hold 60 min or to 15:20, whichever first. Real costs. 60-min overlap-skip.
Grid: velocity thresholds x lookback windows.
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

OUT = Path(r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\INTRADAY_STUDY_20260707")
LOT = 65
CAP0 = 10_000_000
OPEN_HM = 555
LAST_ENTRY = 870   # 14:30
EOD_HM = 924       # 15:24

def leg_cost(entry, exit, is_sell):
    if entry is None or exit is None or entry <= 0.05 or exit < 0: return None
    brok = 40
    turn = (entry + exit) * LOT
    ex_txn = 0.0003503*turn; ipft = 5e-6*turn; sebi = 1e-6*turn
    stt = 0.001 * (entry if is_sell else exit) * LOT
    stamp = 3e-5 * (exit if is_sell else entry) * LOT
    gst = 0.18*(brok + ex_txn + ipft + sebi)
    hs = (max(0.10, 0.001*entry) + max(0.10, 0.001*exit)) * LOT
    return brok + stt + ex_txn + ipft + sebi + stamp + gst + hs

def sell_pnl(entry, exit):
    c = leg_cost(entry, exit, True)
    if c is None: return None
    return (entry - exit) * LOT - c

s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
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

def front_expiry(d):
    later = [e for e in expiries if e >= d]
    return later[0] if later else None

# ==========================================================
# Main scan: iterate 1-min bars, detect velocity events
# ==========================================================
def run(velocity_pct, lookback_min, direction, max_dte=7):
    trades = []
    for d in days_all:
        arr = by_day[d]
        if len(arr) < 360: continue
        ex = front_expiry(d)
        if ex is None: continue
        dte = (ex - d).days
        if dte > max_dte: continue
        # sample every 5 mins to keep compute bounded
        hm_arr = arr[:, 0]
        close_arr = arr[:, 4]
        last_exit_hm = -1
        for i in range(lookback_min, len(arr), 5):
            hm = int(hm_arr[i])
            if hm < OPEN_HM + lookback_min or hm > LAST_ENTRY: continue
            if hm < last_exit_hm: continue  # no overlap
            # need bar approximately lookback_min ago
            j = i - lookback_min
            if j < 0: continue
            if int(hm_arr[j]) != hm - lookback_min: continue
            ret = (close_arr[i] - close_arr[j]) / close_arr[j]
            if abs(ret) < velocity_pct: continue
            spot = float(close_arr[i])
            sign = 1 if ret > 0 else -1
            atm = int(round(spot / 50) * 50)
            if direction == "fade":
                # up move -> sell CE (fade); down move -> sell PE
                cp = "CE" if sign > 0 else "PE"
                K = atm + 100 if sign > 0 else atm - 100
            else:  # follow
                cp = "PE" if sign > 0 else "CE"
                K = atm - 100 if sign > 0 else atm + 100
            ch = get_chain(d, ex)
            entry_px = opt_px(ch, hm, K, cp)
            if entry_px is None or entry_px < 1: continue
            # exit 60 min later or EOD
            exit_hm_target = min(hm + 60, EOD_HM)
            exit_px = opt_px(ch, exit_hm_target, K, cp)
            if exit_px is None: continue
            pnl = sell_pnl(entry_px, exit_px)
            if pnl is None: continue
            last_exit_hm = exit_hm_target
            trades.append(dict(d=str(d), hm=hm, dte=dte, sign=sign,
                               ret_pct=round(ret*100, 3), K=K, cp=cp,
                               entry_px=entry_px, exit_px=exit_px,
                               pnl=round(pnl, 0)))
    return pd.DataFrame(trades)

def stats(df, name):
    if len(df) == 0: return dict(name=name, n=0)
    df = df.copy()
    df["date"] = pd.to_datetime(df["d"])
    df = df.sort_values(["date","hm"]).reset_index(drop=True)
    p = df["pnl"].values.astype(float)
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
                worst=round(p.min(), 0), best=round(p.max(), 0)), eq

t0 = time.time()
grid = [
    (0.003, 15, "fade"),   (0.003, 15, "follow"),
    (0.004, 15, "fade"),   (0.004, 15, "follow"),
    (0.005, 15, "fade"),   (0.005, 15, "follow"),
    (0.003,  5, "fade"),   (0.005,  5, "fade"),
    (0.005, 30, "fade"),
]

results = []; all_eqs = {}
for vp, lb, dir_ in grid:
    name = f"vel={vp*100:.1f}%/{lb}min · {dir_}"
    print(f"\n{name}...")
    df = run(vp, lb, dir_)
    if len(df) < 20:
        print(f"  n={len(df)}, skipping"); continue
    st, eq = stats(df, name)
    print(f"  n={st['n']}, tpy={st['trades_per_yr']}, win={st['win_pct']}%, expect=Rs.{st['expect']}, Sharpe={st['sharpe']}, CAGR={st['cagr']}%, DD={st['maxdd_pct']}%, worst=Rs.{st['worst']}")
    results.append(st); all_eqs[name] = eq
    df.to_csv(OUT / f"vel_{vp*100:.1f}pct_{lb}m_{dir_}.csv", index=False)

# ---- direction split analysis for best cells ----
print("\n=== Direction split for FADE variants (BEAR = down-spike fade -> sell PE) ===")
for vp, lb, dir_ in [(0.003, 15, "fade"), (0.004, 15, "fade"), (0.005, 15, "fade")]:
    fn = OUT / f"vel_{vp*100:.1f}pct_{lb}m_fade.csv"
    if not fn.exists(): continue
    df = pd.read_csv(fn)
    if len(df) == 0: continue
    print(f"\n  {vp*100:.1f}%/{lb}min fade:")
    by_sign = df.groupby("sign").agg(n=("pnl","size"), pnl=("pnl","sum"),
                                      expect=("pnl","mean"),
                                      win=("pnl", lambda x: round((x>0).mean()*100,1)),
                                      cp=("cp","first")).round(0)
    print(by_sign.to_string())

sdf = pd.DataFrame(results).set_index("name")
sdf.to_csv(OUT / "velocity_100otm_summary.csv")
print("\n=== SUMMARY (grid) ===")
print(sdf[["n","trades_per_yr","win_pct","expect","cagr","maxdd_pct","sharpe","pf","worst","best"]].to_string())

# ---- chart top 6 by Sharpe ----
top = sorted(results, key=lambda r: r["sharpe"], reverse=True)[:6]
fig, ax = plt.subplots(figsize=(13,7))
colors = ['#26a69a','#4dd0e1','#ffd54f','#2962ff','#ba68c8','#ff8f8f']
for i, st in enumerate(top):
    eq = all_eqs[st["name"]]
    ax.plot(eq, label=f'{st["name"]}: n={st["n"]}, Sharpe {st["sharpe"]}, CAGR {st["cagr"]}%', color=colors[i], lw=1.3)
ax.axhline(CAP0, color='#787b86', ls='--', alpha=0.5)
ax.set_ylabel('Equity (Rs.)'); ax.set_xlabel('Trade #')
ax.legend(fontsize=8, loc='best'); ax.grid(alpha=0.3)
ax.set_title('Velocity-triggered 100-OTM SELL - top 6 variants by Sharpe (Rs.1cr, 1 lot, real costs)')
plt.tight_layout(); plt.savefig(OUT / "velocity_100otm.png", dpi=110)
print(f"\nchart -> velocity_100otm.png")
print(f"runtime: {time.time()-t0:.0f}s")
