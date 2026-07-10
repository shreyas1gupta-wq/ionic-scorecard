"""SCALPING V7 (Pine port) — 0DTE NIFTY expiry days ONLY. CHEAPTEST_SPEC_20260710/scalpv7-0dte.

PRE-REGISTERED (FROZEN before run):
  Universe: NIFTY 1-min spot; trading days where day == weekly expiry (0DTE), expiry dates
    DERIVED FROM OPTION DATA (handles Thu->Tue migration automatically). 2021-06..2026-06.
  Signal: faithful port of Principal's Pine "Scalping System V7 (Close-Based Execution)":
    EMA9/26 trend, pullback (low<=ema on long side), rejection candle, body>0.8*SMA(body,10),
    RSI50 gate + 70/30 late-avoid, |close-ema9|<=120 chase-avoid, max 3 entries per trend leg,
    single position, entry & exit AT BAR CLOSE, exit when close<ema9 or ema9<ema26 or
    (profit>15pts and red candle), no same-bar exit.
  Vehicle: nearest-50 strike 0DTE CE (long) / PE (short), bought at option 1-min close at the
    signal bar's close time; exit at option close at exit time; held-to-EOD settles at last print.
    No new entries after 15:00; forced flat at 15:25 (calibration rule). Missing option print at
    entry = NO FILL = dropped (counted).
  Costs (2026-07-10 calibration): BASE 1.0 pt one-way, STRESS 2.0 pts; x2 if leg in 09:15-09:30.
  PRIMARY: 5-min bars (scalping TF). SECONDARY: 1-min bars. Trials ledger: 2.
  KILL (primary): net expectancy/trade at BASE costs <= 0, OR PF < 1.15. n < 60 -> INSUFFICIENT.
"""
import sys, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CHEAPTEST_SPEC_20260710/scalpv7-0dte"
OUT.mkdir(exist_ok=True)
GRID, CHASE, LOCK = 50, 120.0, 15.0
BASE_COST, STRESS_COST = 1.0, 2.0

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
mapping, exps = chain.build_expiry_index()
expiry_days = sorted(set(exps) & set(pd.Series(spot.index.date).unique()))
print(f"0DTE days with spot data: {len(expiry_days)}  ({expiry_days[0]} .. {expiry_days[-1]})")

def wilder_rsi(c, n=14):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))

def load_day_options(day):
    """1-min option closes for expiry==day: dict (ts, strike, cp) -> close"""
    try:
        df = pq.read_table(mapping[day], columns=["timestamp", "strike", "option_type",
                                                  "close", "trading_day"]).to_pandas()
    except Exception as ex:
        print(f"[optskip] {day}: {ex}"); return None
    df = df[df["trading_day"] == str(day)]
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)
    return df.set_index(["ts", "strike", "option_type"])["close"].to_dict(), \
           df.groupby(["strike", "option_type"])["close"].last().to_dict()

def opt_px(book, ts, k, cp):
    return book.get((ts, float(k), cp)) or book.get((ts, k, cp))

def run_tf(tf_min):
    trades = []
    nofill = 0
    for day in expiry_days:
        s1 = spot[pd.Series(spot.index.date, index=spot.index) == day]
        if len(s1) < 200:
            continue
        bars = s1.resample(f"{tf_min}min", label="right", closed="right").agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}).dropna() \
            if tf_min > 1 else s1[["open", "high", "low", "close"]].copy()
        # warmup indicators on the day (Pine uses continuous series; day-scoped is the
        # conservative 0DTE-only equivalent — declared deviation)
        e9 = bars["close"].ewm(span=9, adjust=False).mean()
        e26 = bars["close"].ewm(span=26, adjust=False).mean()
        rsi = wilder_rsi(bars["close"])
        body = (bars["close"] - bars["open"]).abs()
        avgb = body.rolling(10).mean()
        opt = load_day_options(day)
        if opt is None:
            continue
        book, last_px = opt
        inpos, side, entry_ts, entry_spot, entry_k, entry_px, entry_i = False, 0, None, 0, 0, 0, -1
        lt = st = 0
        bull_prev = None
        for i in range(30, len(bars)):
            t = bars.index[i]
            c, o, lo, hi = bars["close"].iloc[i], bars["open"].iloc[i], bars["low"].iloc[i], bars["high"].iloc[i]
            E9, E26, R, B, AB = e9.iloc[i], e26.iloc[i], rsi.iloc[i], body.iloc[i], avgb.iloc[i]
            if np.isnan(AB) or np.isnan(R):
                continue
            bull = E9 > E26
            if bull_prev is not None:
                if bull and not bull_prev: lt = 0
                if (not bull) and bull_prev: st = 0
            bull_prev = bull
            mom = B > AB * 0.8
            eL = bull and (lo <= E9 or lo <= E26) and c > o and mom and R > 50 and R <= 70 and abs(c - E9) <= CHASE and lt < 3
            eS = (not bull) and (hi >= E9 or hi >= E26) and c < o and mom and R < 50 and R >= 30 and abs(c - E9) <= CHASE and st < 3
            if eL: lt += 1
            if eS: st += 1
            # exits first (Pine: exit needs bar_index > entryBar)
            if inpos and i > entry_i:
                prof = (c - entry_spot) if side > 0 else (entry_spot - c)
                lock = prof > LOCK and ((c < o) if side > 0 else (c > o))
                struct = (c < E9 or E9 < E26) if side > 0 else (c > E9 or E9 > E26)
                eod = t.time() >= dt.time(15, 25)
                if struct or lock or eod:
                    k, cp = entry_k, ("CE" if side > 0 else "PE")
                    xp = opt_px(book, t, k, cp) or last_px.get((float(k), cp)) or last_px.get((k, cp))
                    if xp is not None:
                        cost = (BASE_COST + (BASE_COST if entry_ts.time() < dt.time(9, 30) else 0)
                                + (BASE_COST if t.time() < dt.time(9, 30) else 0))
                        trades.append(dict(day=str(day), side=side, ts_in=entry_ts, ts_out=t,
                                           spot_pts=prof, prem_in=entry_px, prem_out=xp,
                                           gross=xp - entry_px, net=xp - entry_px - cost,
                                           net_stress=xp - entry_px - cost * STRESS_COST / BASE_COST))
                    inpos = False
            # entries (flat only, before 15:00)
            if (not inpos) and (eL or eS) and t.time() < dt.time(15, 0):
                k = round(c / GRID) * GRID
                cp = "CE" if eL else "PE"
                px = opt_px(book, t, k, cp)
                if px is None or px <= 0:
                    nofill += 1
                else:
                    inpos, side, entry_ts, entry_spot, entry_k, entry_px, entry_i = True, (1 if eL else -1), t, c, k, px, i
    df = pd.DataFrame(trades)
    if not len(df):
        return df, nofill
    df["era"] = np.where(df["day"] < "2024-01-01", "2021-23", "2024-26")
    return df, nofill

report = []
for tf, tag in [(5, "PRIMARY_5min"), (1, "SECONDARY_1min")]:
    df, nofill = run_tf(tf)
    if not len(df):
        report.append(f"{tag}: 0 trades"); continue
    df.to_csv(OUT / f"trades_{tag}.csv", index=False)
    for scope, g in [("ALL", df)] + [(e, df[df.era == e]) for e in df.era.unique()]:
        w = g[g.net > 0]; l = g[g.net <= 0]
        pf = w.net.sum() / abs(l.net.sum()) if len(l) and l.net.sum() != 0 else np.inf
        exp_pct = (g.net / g.prem_in).mean() * 100
        report.append(
            f"{tag} [{scope}] n={len(g)} nofill={nofill if scope=='ALL' else ''} | spot_pts/trade={g.spot_pts.mean():+.2f} | "
            f"gross={g.gross.mean():+.2f} net={g.net.mean():+.2f} netStress={g.net_stress.mean():+.2f} pts/trade | "
            f"exp={exp_pct:+.1f}% of premium | win={len(w)/len(g)*100:.0f}% PF={pf:.2f} | "
            f"total_net={g.net.sum():+.0f} pts")
txt = "\n".join(report)
print(txt)
(OUT / "SUMMARY.md").write_text(
    "# SCALP V7 0DTE-only — results vs frozen bars (KILL if net<=0 @BASE or PF<1.15; n<60 insufficient)\n\n```\n"
    + txt + "\n```\n", encoding="utf-8")
print("saved ->", OUT)
