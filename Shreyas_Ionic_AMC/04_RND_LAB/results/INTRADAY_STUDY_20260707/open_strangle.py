"""Open-strangle test: BUY 100-OTM CE + BUY 100-OTM PE at 09:15, exit at fixed times.
Also grids 50/100/150-OTM x exit-time 09:20/25/30/45 for context.
"""
import sys, time
from pathlib import Path
import numpy as np
import pandas as pd

GAME = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\fno_game\server"
sys.path.insert(0, GAME)
import data_loader as dl

OUT = Path(__file__).parent
LOT = 65
COST_BUY_BPS = 5.0    # one-way on premium — round trip = 10 bps of turnover
OPEN_HM = 555         # 09:15
EXITS = [560, 565, 570, 585]  # 09:20, 09:25, 09:30, 09:45
OFFSETS = [50, 100, 150]

t0 = time.time()

s = dl._spot()
days_all = sorted(s["d"].unique())
by_day = {d: g[["hm","open","high","low","close"]].to_numpy() for d, g in s.groupby("d")}
expiries = list(dl.expiries())
def expiry_of(d):
    nxt = [e for e in expiries if e >= d]
    return nxt[0] if nxt else None
def dte_of(d):
    e = expiry_of(d)
    return (e - d).days if e else -1

opt_cache = {}
def get_chain(d, ex):
    k = (d, ex)
    if k not in opt_cache:
        try: opt_cache[k] = dl.load_option_day(ex, d)
        except Exception: opt_cache[k] = None
    return opt_cache[k]

def opt_price(chain, hm, strike, cp, back=5):
    if chain is None: return None
    for b in range(back+1):
        row = chain["minute_index"].get(hm - b, {}).get((int(strike), cp))
        if row is not None: return row["c"]
    # if entry, also look forward a couple of minutes (some strikes print first at 09:16)
    for f in range(1, 4):
        row = chain["minute_index"].get(hm + f, {}).get((int(strike), cp))
        if row is not None: return row["c"]
    return None

def buy_pnl(entry, exit):
    if entry is None or exit is None or entry <= 0.1: return None
    gross = (exit - entry) * LOT
    return gross - abs(entry * LOT * 2 * COST_BUY_BPS/1e4)  # entry + exit costs

events = []
for d in days_all:
    arr = by_day[d]
    if len(arr) < 360: continue
    dte = dte_of(d)
    if dte < 0 or dte > 7: continue
    ex = expiry_of(d)
    ch = get_chain(d, ex)
    if ch is None: continue
    # spot at 09:15 close
    if int(arr[0,0]) != OPEN_HM: continue
    spot_915 = arr[0,4]
    atm = int(round(spot_915 / 50) * 50)
    row = dict(d=str(d), dte=dte, spot=spot_915, atm=atm)
    for off in OFFSETS:
        ce_K = atm + off; pe_K = atm - off
        pce = opt_price(ch, OPEN_HM, ce_K, "CE")
        ppe = opt_price(ch, OPEN_HM, pe_K, "PE")
        if pce is None or ppe is None or pce < 0.5 or ppe < 0.5: continue
        row[f"ce{off}_e"] = pce
        row[f"pe{off}_e"] = ppe
        for xh in EXITS:
            # find bar at or before xh
            idx = np.searchsorted(arr[:,0], xh)
            idx = min(idx, len(arr)-1)
            hm_x = int(arr[idx,0])
            xce = opt_price(ch, hm_x, ce_K, "CE")
            xpe = opt_price(ch, hm_x, pe_K, "PE")
            ce_pnl = buy_pnl(pce, xce)
            pe_pnl = buy_pnl(ppe, xpe)
            if ce_pnl is None or pe_pnl is None: continue
            row[f"pnl_{off}_{xh}"] = ce_pnl + pe_pnl
    events.append(row)

df = pd.DataFrame(events)
print(f"events: {len(df)}   runtime so far: {time.time()-t0:.0f}s")
df.to_csv(OUT / "open_strangle.csv", index=False)

lines = ["# OPEN-STRANGLE: BUY 100-OTM CE + 100-OTM PE at 09:15",
         f"n = {len(df)} days · costs approx (5bps entry + 5bps exit each leg)",
         "P&L per pair-of-lots (1 CE + 1 PE, LOT=65). Multiply by lot pairs actually traded.",
         ""]

# Primary answer: 100-OTM at 09:20 and 09:30
def cell_stats(col):
    if col not in df: return None
    s = df[col].dropna()
    if len(s) < 20: return None
    return dict(n=len(s), win=round((s>0).mean()*100,1),
                mean=round(s.mean(),0), med=round(s.median(),0),
                p10=round(s.quantile(0.10),0), p90=round(s.quantile(0.90),0),
                std=round(s.std(),0),
                sharpe=round(s.mean()/max(1,s.std()),2))

lines += ["## Direct answer (100-OTM, exits at 09:20 / 09:30)"]
for xh, name in [(560,"09:20"),(565,"09:25"),(570,"09:30"),(585,"09:45")]:
    c = cell_stats(f"pnl_100_{xh}")
    if c: lines.append(f"  exit {name} → n={c['n']}, win={c['win']}%, "
                      f"mean=Rs.{c['mean']}, median=Rs.{c['med']}, "
                      f"p10=Rs.{c['p10']}, p90=Rs.{c['p90']}, std=Rs.{c['std']}, sharpe={c['sharpe']}")

lines += ["", "## Full grid: strike offset × exit time"]
lines += ["  row=offset from ATM (both legs), col=exit time. Cells: 'win% / mean Rs. / median Rs.'"]
rows = []
for off in OFFSETS:
    r = {"off": f"±{off}"}
    for xh, nm in [(560,"09:20"),(565,"09:25"),(570,"09:30"),(585,"09:45")]:
        c = cell_stats(f"pnl_{off}_{xh}")
        r[nm] = f"{c['win']}% / {c['mean']} / {c['med']}" if c else "—"
    rows.append(r)
lines.append(pd.DataFrame(rows).to_string(index=False))

lines += ["", "## Best cell breakdown by DTE"]
best_col = "pnl_100_585"  # will refine after seeing results
if best_col in df:
    sub = df.dropna(subset=[best_col]).copy()
    sub["dte_b"] = pd.cut(sub["dte"], bins=[-1,0,1,3,7], labels=["0DTE","1DTE","2-3DTE","4-7DTE"])
    def st(g):
        s = g[best_col]
        return pd.Series(dict(n=len(g),
                              win=round((s>0).mean()*100,1),
                              mean=round(s.mean(),0),
                              med=round(s.median(),0),
                              sharpe=round(s.mean()/max(1,s.std()),2)))
    lines += ["  100-OTM strangle, exit 09:45, by DTE:",
              sub.groupby("dte_b", observed=False).apply(st, include_groups=False).to_string()]

# Year stability
lines += ["", "## Year stability (100-OTM strangle, exit 09:30)"]
if "pnl_100_570" in df:
    df["year"] = df["d"].str[:4]
    yr = df.dropna(subset=["pnl_100_570"]).groupby("year").agg(
        n=("pnl_100_570","size"),
        win_pct=("pnl_100_570", lambda x: round((x>0).mean()*100,1)),
        mean=("pnl_100_570", lambda x: round(x.mean(),0)),
        med=("pnl_100_570", lambda x: round(x.median(),0)),
    )
    lines.append(yr.to_string())

# Aggregate stats — what does the WHOLE 5-year P&L look like?
lines += ["", "## Aggregate P&L if you did this EVERY DAY"]
for xh, nm in [(560,"09:20"),(570,"09:30"),(585,"09:45")]:
    for off in OFFSETS:
        col = f"pnl_{off}_{xh}"
        if col in df:
            s = df[col].dropna()
            if len(s) >= 50:
                lines.append(f"  ±{off} OTM · exit {nm}: n={len(s)}, sum P&L = Rs.{s.sum():,.0f}, avg Rs.{s.mean():.0f}/day")

lines.append(f"\n---\nruntime: {time.time()-t0:.0f}s")
(OUT / "OPEN_STRANGLE.md").write_text("\n".join(lines), encoding="utf-8")
print("DONE →", OUT / "OPEN_STRANGLE.md")
