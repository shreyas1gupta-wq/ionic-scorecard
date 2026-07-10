"""Principal spec 2026-07-10: 0DTE strangle +-50 (sell CE@ATM+50, PE@ATM-50) 35% per-leg SL,
with DEFENSE on SL-hit in the breached direction:
  V0 no defense (baseline strangle 35% SL)
  V1 defense = BUY 50pt-ITM + SELL 50pt-OTM (100pt debit spread, momentum direction), no SL, to settle
  V2 defense = BUY 50pt-ITM only, 25% SL on long premium
  V3 defense = BUY 50pt-ITM only, 50% SL on long premium
PRE-REGISTERED bars per variant: PASS = net>0 @BASE costs AND day-t>=2 AND PF>=1.2 AND
  max-day<30% of profits. Entry 09:20 1-min close; ATM=round50(spot). SL evaluated on 1-min
  closes, fills at NEXT close after breach; defense entered at that same fill bar using spot
  round50 at that minute (ITM=round50-50 / OTM=round50+50 for CE side; mirrored for PE).
  Each leg defends independently (whipsaw can open both defenses). Settle 15:25 last print.
  Costs 1pt/leg one-way (2x pre-09:30). NO COVID in sample. Ledger +4.
SIZING for CAGR: margin ~Rs 1.1L per strangle set (defense debit ignored, labeled approx),
  lot 75, capital Rs 10L start: (a) 0.2-Kelly fraction (computed per variant), (b) 75%-of-equity
  margin deployment. Compounded daily, CAGR over sample span, maxDD%.
"""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/defense_strangle"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
sd = pd.Series(spot.index.date, index=spot.index)
mapping, exps = chain.build_expiry_index()
SL_SHORT = 0.35
END = dt.time(15, 25)

def lc(ts): return 2.0 if ts.time() < dt.time(9, 30) else 1.0

rows = []
for exp in exps:
    day = exp
    s1d = spot[sd == day]
    if len(s1d) < 100:
        continue
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "close", "trading_day"]).to_pandas()
    except Exception:
        continue
    df = df[df["trading_day"] == str(day)]
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)
    cache = {}
    def leg(k, cp):
        key = (float(k), cp)
        if key not in cache:
            s = df[(df.strike == float(k)) & (df.option_type == cp)].set_index("ts")["close"].sort_index()
            cache[key] = s[~s.index.duplicated(keep="last")]
        return cache[key]
    cand = s1d[s1d.index.time >= dt.time(9, 20)]
    if not len(cand):
        continue
    t0 = cand.index[0]
    atm = round(s1d["close"].loc[t0] / 50) * 50
    LS = {"CE": leg(atm + 50, "CE"), "PE": leg(atm - 50, "PE")}
    if any(t0 not in LS[c].index for c in LS):
        continue
    day_pnl = {v: 0.0 for v in ("V0", "V1", "V2", "V3")}
    valid = True
    for cp in ("CE", "PE"):
        s = LS[cp]
        e = s.loc[t0]
        win = s[(s.index > t0) & (s.index.time <= END)]
        if not len(win):
            valid = False; break
        br = win[win >= e * (1 + SL_SHORT)]
        if not len(br):
            pnl = (e - win.iloc[-1]) - lc(t0) - 1.0
            for v in day_pnl: day_pnl[v] += pnl
            continue
        after = win[win.index > br.index[0]]
        xt, xp = (after.index[0], after.iloc[0]) if len(after) else (br.index[0], br.iloc[0])
        short_pnl = (e - xp) - lc(t0) - lc(xt)
        for v in day_pnl: day_pnl[v] += short_pnl
        # defense at xt
        try:
            spx = s1d["close"].asof(xt)
        except Exception:
            spx = None
        if spx is None or pd.isna(spx):
            continue
        k0 = round(spx / 50) * 50
        sign = 1 if cp == "CE" else -1          # CE breach -> bullish defense
        k_itm, k_otm = k0 - sign * 50, k0 + sign * 50
        li, lo_ = leg(k_itm, cp), leg(k_otm, cp)
        if xt not in li.index:
            continue
        ei = li.loc[xt]
        wi = li[(li.index > xt) & (li.index.time <= END)]
        settle_i = wi.iloc[-1] if len(wi) else ei
        # V1 spread (needs OTM leg print)
        if xt in lo_.index:
            eo = lo_.loc[xt]
            wo = lo_[(lo_.index > xt) & (lo_.index.time <= END)]
            settle_o = wo.iloc[-1] if len(wo) else eo
            day_pnl["V1"] += (settle_i - ei) - (settle_o - eo) - 2 * (lc(xt) + 1.0)
        # V2/V3 long-only with SL on long premium
        for v, slL in (("V2", 0.25), ("V3", 0.50)):
            if len(wi):
                brl = wi[wi <= ei * (1 - slL)]
                if len(brl):
                    a2 = wi[wi.index > brl.index[0]]
                    xpl = a2.iloc[0] if len(a2) else brl.iloc[0]
                else:
                    xpl = wi.iloc[-1]
            else:
                xpl = ei
            day_pnl[v] += (xpl - ei) - lc(xt) - 1.0
    if valid:
        for v, pnl in day_pnl.items():
            rows.append(dict(variant=v, day=str(day), net=pnl))

df = pd.DataFrame(rows)
df.to_csv(OUT / "defense_trades.csv", index=False)

MARGIN, LOT, CAP0 = 110000.0, 75, 1_000_000.0
lines = ["# Defense-strangle variants (0DTE +-50 strangle, 35% SL; defense on breach). Frozen bars in docstring.",
         "Reference: S1 ATM straddle 30%SL = +8.02 t=2.94 PF1.56"]
for v, g in df.groupby("variant"):
    g = g.sort_values("day")
    daily = g.set_index("day")["net"]
    t = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily)))
    w, l = g[g.net > 0], g[g.net <= 0]
    pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
    cum = daily.cumsum(); dd = (cum - cum.cummax()).min()
    conc = daily.max() / daily[daily > 0].sum() * 100 if daily.sum() > 0 else np.nan
    era = {e2: gg.net.mean() for e2, gg in g.groupby(g.day < "2024-01-01")}
    verdict = ("PASS" if (g.net.mean() > 0 and t >= 2 and pf >= 1.2 and conc < 30) else "KILL") if len(g) >= 60 else "INSUFF"
    # sizing
    r = daily * LOT / MARGIN
    f02 = max(0.2 * (r.mean() / r.var(ddof=1)), 0.0) if r.var(ddof=1) > 0 else 0.0
    out_sz = []
    for tag, frac in (("0.2K", f02), ("75%", 0.75)):
        eq = CAP0; peak = CAP0; mdd = 0.0
        for pnl in daily:
            lots = int(min(frac, 4.0) * eq / MARGIN)  # cap leverage at 4x margin-fraction sanity
            eq += pnl * LOT * lots
            peak = max(peak, eq); mdd = min(mdd, (eq - peak) / peak)
        yrs = 4.9
        cagr = ((eq / CAP0) ** (1 / yrs) - 1) * 100 if eq > 0 else -100.0
        out_sz.append(f"{tag}(frac={min(frac,4.0):.2f}): final={eq/1e5:.1f}L CAGR={cagr:.1f}% maxDD={mdd*100:.1f}%")
    lines.append(f"{v}: n={len(g)} net={g.net.mean():+.2f} pts | t={t:.2f} PF={pf:.2f} win={len(w)/len(g)*100:.0f}% "
                 f"| maxDD={dd:.0f}pts conc={conc:.0f}% | era21-23={era.get(True, np.nan):+.2f} era24-26={era.get(False, np.nan):+.2f} "
                 f"| worst5={daily.nsmallest(5).round(1).to_dict()} | **{verdict}**\n   sizing: {' | '.join(out_sz)}")
txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")
print("saved ->", OUT)
