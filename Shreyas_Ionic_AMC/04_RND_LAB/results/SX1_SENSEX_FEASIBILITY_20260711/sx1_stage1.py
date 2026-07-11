"""SX1-CARD Stage 1: SENSEX 0DTE raw seller economics on BSE daily bhavcopy (frozen @ 26e1684).
SELL ATM straddle at OPEN of expiry day, settle at intrinsic from futures close (spot proxy =
near/expiring SENSEX futures — declared; no SENSEX index series in dataset). Tradeable legs only.
BAR: mean gross > 0 with t>=2 AND premium %-of-spot within 0.8-1.5x NIFTY's -> Stage 2 shadow.
NIFTY comparator: same construction from 1-min chain (open-bar straddle vs 15:25 intrinsic).
"""
import datetime as dt
import json, sys
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SX1_SENSEX_FEASIBILITY_20260711"
OUT.mkdir(parents=True, exist_ok=True)
BSE = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/bse_fo_bhavcopy"

fo = pd.concat([pd.read_parquet(p) for p in sorted(BSE.glob("bse_fo_*.parquet"))], ignore_index=True)
fo = fo[fo.TckrSymb == "SENSEX"].copy()
fo["d"] = pd.to_datetime(fo.TradDt).dt.date
fo["exp"] = pd.to_datetime(fo.XpryDt).dt.date
for c in ["StrkPric", "OpnPric", "ClsPric", "SttlmPric", "TtlTradgVol"]:
    fo[c] = pd.to_numeric(fo[c], errors="coerce")

opt = fo[fo.FinInstrmTp == "IDO"]
fut = fo[fo.FinInstrmTp == "IDF"].sort_values(["d", "exp"])

rows, skip = [], 0
for e_day in sorted(opt[opt.exp == opt.d].d.unique()):
    ch = opt[(opt.d == e_day) & (opt.exp == e_day)]
    fu = fut[fut.d == e_day]
    if not len(fu):
        skip += 1; continue
    f_open, f_close = fu.OpnPric.iloc[0], fu.ClsPric.iloc[0]
    if not (f_open > 0 and f_close > 0):
        skip += 1; continue
    # ATM strike nearest futures open with BOTH legs traded (vol>0, open>0)
    got = None
    for k in sorted(ch.StrkPric.unique(), key=lambda k: abs(k - f_open))[:6]:
        ce = ch[(ch.StrkPric == k) & (ch.OptnTp == "CE")]
        pe = ch[(ch.StrkPric == k) & (ch.OptnTp == "PE")]
        if len(ce) and len(pe) and ce.OpnPric.iloc[0] > 0 and pe.OpnPric.iloc[0] > 0 \
           and ce.TtlTradgVol.iloc[0] > 0 and pe.TtlTradgVol.iloc[0] > 0:
            got = (k, ce.OpnPric.iloc[0], pe.OpnPric.iloc[0]); break
    if got is None:
        skip += 1; continue
    K, ce0, pe0 = got
    prem = ce0 + pe0
    gross = prem - abs(f_close - K)  # LANDMINE #9 discipline: intrinsic from underlying proxy
    rows.append(dict(day=e_day, K=K, prem=prem, prem_pct=prem / f_open * 100, gross=gross,
                     gross_pct=gross / f_open * 100))
sx = pd.DataFrame(rows)
sx.to_csv(OUT / "sx1_days.csv", index=False)

# ---- NIFTY comparator from 1-min chain (same window as SENSEX sample) ----
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
mapping, exps = chain.build_expiry_index()
spot_dates = pd.Series(spot.index.date, index=spot.index)
w0, w1 = sx.day.min(), sx.day.max()
nf = []
for exp in [e for e in sorted(exps) if w0 <= e <= w1]:
    sd = spot[spot_dates == exp]
    if len(sd) < 100:
        continue
    sp_open = sd["close"].iloc[0]
    sp_close = sd[sd.index.time <= dt.time(15, 25)]["close"].iloc[-1]
    K = round(sp_open / 50) * 50
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type", "close", "trading_day"]).to_pandas()
    except Exception:
        continue
    df = df[df.trading_day == str(exp)]
    ts = pd.to_datetime(df.timestamp)
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)
    prem = 0.0, 0.0
    legs = []
    ok = True
    for cp in ("CE", "PE"):
        s = df[(df.strike == float(K)) & (df.option_type == cp) & (df.ts.dt.time >= dt.time(9, 15)) &
               (df.ts.dt.time <= dt.time(9, 20))].sort_values("ts")
        if not len(s):
            ok = False; break
        legs.append(s["close"].iloc[0])
    if not ok:
        continue
    prem = sum(legs)
    nf.append(dict(day=exp, prem_pct=prem / sp_open * 100, gross_pct=(prem - abs(sp_close - K)) / sp_open * 100))
nfd = pd.DataFrame(nf)

def stat(x):
    x = np.asarray(x, float)
    return len(x), x.mean(), x.mean() / (x.std(ddof=1) / np.sqrt(len(x))), (x > 0).mean() * 100

n, m, t, w = stat(sx.gross)
_, mp, _, _ = stat(sx.prem_pct)
_, nmp, _, _ = stat(nfd.prem_pct)
_, ngp, nt, _ = stat(nfd.gross_pct)
_, mgp, tgp, _ = stat(sx.gross_pct)
ratio = mp / nmp if nmp else np.nan
bar1 = (m > 0) and (t >= 2)
bar2 = 0.8 <= ratio <= 1.5
verdict = "STAGE-1 PASS -> Stage 2 shadow (13 Thursdays, zero size)" if (bar1 and bar2) else "PARKED (no expansion)"

lines = [f"SENSEX 0DTE days: n={n} ({sx.day.min()}..{sx.day.max()}), skips={skip}",
         f"premium: mean {sx.prem.mean():.0f} pts = {mp:.3f}% of spot | NIFTY same-window: {nmp:.3f}% -> ratio {ratio:.2f}x (bar 0.8-1.5)",
         f"raw gross (no SL): mean {m:+.1f} pts ({mgp:+.3f}% of spot), t={t:.2f}, win% {w:.0f}% (bar: >0, t>=2)",
         f"NIFTY comparator raw gross: {ngp:+.3f}% of spot (t={nt:.2f}, n={len(nfd)})",
         f"bars: gross>0&t>=2 = {'PASS' if bar1 else 'FAIL'} | prem ratio = {'PASS' if bar2 else 'FAIL'}",
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "SX1-CARD-stage1", "frozen_commit": "26e1684", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "sx1_stage1.py", "data": ["bse_fo_bhavcopy (D-033 2026-07-11)", "NIFTY 1-min chain comparator"],
        "n_obs": int(n), "metrics": {"gross_pts": round(float(m), 1), "t": round(float(t), 2),
        "prem_ratio_vs_nifty": round(float(ratio), 2)},
        "validation": {"era_split": "single era (2023-26)", "bootstrap_ci95": None,
                       "lookahead_ast": "pre-flight", "one_day_lag": "daily prints; futures spot proxy declared"},
        "verdict": verdict, "bars_hit": [b for b, hit in [("gross_t2", bar1), ("prem_ratio", bar2)] if hit],
        "trials_increment": 1, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written")
