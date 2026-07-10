"""COVID BACKCAST (MODEL-BASED — label everything): what would S1 / S1b / V2 have done
Jan-2020..May-2021, before our real 1-min option data begins?
METHOD:
  1. Real 1-min NIFTY spot for the whole period (incl 2020 crash).
  2. Weekly expiry days 2020-01..2021-05 = Thursdays (prev trading day if holiday).
  3. Option legs priced by Black-Scholes on the ACTUAL minute spot path.
     IV_0 = k * RV3d_annualized (k CALIBRATED on 2021-06..2026-06 vs real 09:20 ATM straddle
     premiums). Two IV paths: CONST (IV frozen intraday, optimistic in a crash) and
     STRESS (IV_t = IV_0*(1+0.5*|move%|), pessimistic-ish).
  4. Same rules as final_three: 09:20 entry, 30%/35% SLs, next-minute fills, 15:25 settle,
     fees = 1% slip + 0.2% + Rs20/order.
  5. VALIDATION: run the same model on 2021-06..2026-06 expiry days and compare modeled vs
     ACTUAL daily P&L (corr + mean bias). The backcast is only as credible as this agreement.
OUTPUT: validation stats; 2020-21 monthly P&L; worst days (Mar-2020!); both-legs-stopped days;
  survival check at 75%-deployment sizing. NOT a backtest — a stress reconstruction."""
import sys, math, datetime as dt
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SELLSIDE_20260710/covid_backcast"
OUT.mkdir(parents=True, exist_ok=True)

KAGGLE = ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv"
spot = pd.read_csv(KAGGLE, parse_dates=["date"]).rename(columns={"date": "timestamp"})
spot = spot.set_index("timestamp")[["open", "high", "low", "close"]].sort_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
sd = pd.Series(spot.index.date, index=spot.index)
all_days = sorted(set(sd))
print("spot span:", all_days[0], "->", all_days[-1])
mapping, exps = chain.build_expiry_index()

MIN_YR = 252 * 375.0
def N(x): return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))
def bs(S, K, T, sig, cp):
    if T <= 0 or sig <= 0:
        return max((S - K) if cp == "CE" else (K - S), 0.0)
    sq = sig * math.sqrt(T)
    d1 = (math.log(S / K) + 0.5 * sig * sig * T) / sq
    d2 = d1 - sq
    if cp == "CE":
        return S * N(d1) - K * N(d2)
    return K * N(-d2) - S * N(-d1)

# 3-day trailing RV (1-min) annualized, per day
ret2 = spot["close"].pct_change() ** 2
rv_day = ret2.groupby(sd).sum() ** 0.5          # daily sigma
rv3 = rv_day.rolling(3).mean()
rv3_ann = rv3 * math.sqrt(252)

def fee(px): return 0.012 * px + 0.267

def minutes_to_close(ts):
    endm = 15 * 60 + 30
    return max(endm - (ts.hour * 60 + ts.minute), 1)

def sim_day(day, iv0, stress=False):
    """Model S1/S1b/V2 on day with BS legs; returns dict strat->net or None."""
    bars = spot[sd == day]
    if len(bars) < 100:
        return None
    cand = bars[bars.index.time >= dt.time(9, 20)]
    if not len(cand):
        return None
    t0 = cand.index[0]
    S0 = bars["close"].loc[t0]
    atm = round(S0 / 50) * 50
    path = bars[(bars.index >= t0) & (bars.index.time <= dt.time(15, 25))]["close"]
    tss = list(path.index); Ss = path.values
    def iv_at(i):
        if not stress:
            return iv0
        return iv0 * (1 + 0.5 * abs(Ss[i] / S0 - 1) * 100)
    def px(i, K, cp):
        return bs(Ss[i], K, minutes_to_close(tss[i]) / MIN_YR, iv_at(i), cp)
    def short(K, cp, sl):
        e = px(0, K, cp)
        for i in range(1, len(tss)):
            if px(i, K, cp) >= e * (1 + sl):
                j = min(i + 1, len(tss) - 1)
                xp = px(j, K, cp)
                return (e - xp) - fee(e) - fee(xp), True, j, e
        xp = px(len(tss) - 1, K, cp)
        return (e - xp) - fee(e) - fee(xp), False, None, e
    def long_from(j, K, cp, sl):
        e = px(j, K, cp)
        if e <= 0: return 0.0
        for i in range(j + 1, len(tss)):
            if px(i, K, cp) <= e * (1 - sl):
                jj = min(i + 1, len(tss) - 1)
                return (px(jj, K, cp) - e) - fee(e) - fee(px(jj, K, cp))
        return (px(len(tss) - 1, K, cp) - e) - fee(e) - fee(px(len(tss) - 1, K, cp))
    out = {}
    for name, k0 in (("S1", atm), ("S1b", atm - 50)):
        out[name] = sum(short(k0, cp, 0.30)[0] for cp in ("CE", "PE"))
    v = 0.0
    for cp, K in (("CE", atm + 50), ("PE", atm - 50)):
        pnl, hit, j, e = short(K, cp, 0.35)
        v += pnl
        if hit and j is not None:
            k0 = round(Ss[j] / 50) * 50
            k_itm = k0 - 50 if cp == "CE" else k0 + 50
            v += long_from(j, k_itm, cp, 0.25)
    out["V2"] = v
    return out

# ---- calibrate k on real 2021-26 entry premiums ----
prem_actual = {}
for exp in exps:
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type",
                                                  "close", "trading_day"]).to_pandas()
    except Exception:
        continue
    df = df[df["trading_day"] == str(exp)]
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)
    bars = spot[sd == exp]
    cand = bars[bars.index.time >= dt.time(9, 20)]
    if not len(cand): continue
    t0 = cand.index[0]
    atm = round(bars["close"].loc[t0] / 50) * 50
    snap = df[(df.ts == t0) & (df.strike == float(atm))]
    if len(snap) == 2:
        prem_actual[exp] = (snap["close"].sum(), bars["close"].loc[t0], t0)

ks = []
for d, (prem, S0, t0) in prem_actual.items():
    if d not in rv3_ann.index or pd.isna(rv3_ann.loc[d]): continue
    T = minutes_to_close(t0) / MIN_YR
    base = bs(S0, round(S0/50)*50, T, rv3_ann.loc[d], "CE") + bs(S0, round(S0/50)*50, T, rv3_ann.loc[d], "PE")
    if base > 0:
        ks.append(prem / base * rv3_ann.loc[d] / rv3_ann.loc[d])  # ratio of premiums
        ks[-1] = prem / base
k = float(np.median(ks))
print(f"calibration: n={len(ks)} k(median premium multiplier on RV3-BS)={k:.3f}")

# ---- validation on 2021-26 ----
val = []
for d in list(prem_actual.keys()):
    if d not in rv3_ann.index or pd.isna(rv3_ann.loc[d]): continue
    r = sim_day(d, k * rv3_ann.loc[d])
    if r: val.append(dict(day=str(d), model=r["S1"]))
val = pd.DataFrame(val).set_index("day")
act = pd.read_csv(OUT.parent / "final_three/final_three_trades.csv")
act = act[act.strat == "S1"].set_index("day")["net"]
j = val.join(act.rename("actual"), how="inner").dropna()
corr = j.model.corr(j.actual)
print(f"VALIDATION S1 2021-26: n={len(j)} corr(model,actual)={corr:.2f} "
      f"mean model={j.model.mean():+.2f} vs actual={j.actual.mean():+.2f}")

# ---- backcast 2020-01 .. 2021-05 ----
bdays = [d for d in all_days if dt.date(2020, 1, 1) <= d <= dt.date(2021, 5, 26)]
# weekly expiries = Thursdays present in data, else prior trading day
expiry_days = []
d0 = dt.date(2020, 1, 2)
cur = d0 + dt.timedelta(days=(3 - d0.weekday()) % 7)
while cur <= dt.date(2021, 5, 26):
    e = cur
    while e not in all_days and e > cur - dt.timedelta(days=5):
        e -= dt.timedelta(days=1)
    if e in all_days:
        expiry_days.append(e)
    cur += dt.timedelta(days=7)
print(f"backcast expiry days: {len(expiry_days)}")

rows = []
for d in expiry_days:
    if d not in rv3_ann.index or pd.isna(rv3_ann.loc[d]): continue
    iv0 = k * rv3_ann.loc[d]
    for mode, stress in (("CONST", False), ("STRESS", True)):
        r = sim_day(d, iv0, stress)
        if r:
            for st, v in r.items():
                rows.append(dict(day=str(d), mode=mode, strat=st, net=v, iv0=iv0))
bc = pd.DataFrame(rows)
bc.to_csv(OUT / "backcast_2020.csv", index=False)

lines = [f"# COVID BACKCAST (MODEL — validated corr={corr:.2f} vs real 2021-26; k={k:.2f}, n_val={len(j)})"]
for mode in ("CONST", "STRESS"):
    for st in ("S1", "S1b", "V2"):
        g = bc[(bc["mode"] == mode) & (bc.strat == st)].set_index("day")["net"]
        if not len(g): continue
        cum = g.cumsum(); dd = (cum - cum.cummax()).min()
        mar = g[(g.index >= "2020-02-20") & (g.index <= "2020-04-10")]
        lines.append(f"{mode} {st}: n={len(g)} net={g.mean():+.2f} total={g.sum():+.0f} pts | maxDD={dd:.0f} | "
                     f"CRASH WINDOW (20Feb-10Apr 2020): n={len(mar)} total={mar.sum():+.0f} worst={mar.min():+.0f} | "
                     f"worst5={g.nsmallest(5).round(0).to_dict()}")
# survival at 75% deployment
for st in ("S1", "S1b", "V2"):
    g = bc[(bc["mode"] == "STRESS") & (bc.strat == st)].set_index("day")["net"]
    eq, peak, mdd = 1_000_000.0, 1_000_000.0, 0.0
    for pnl in g:
        lots = int(0.75 * eq / 110000)
        eq += pnl * 75 * lots
        peak = max(peak, eq); mdd = min(mdd, (eq - peak) / peak)
    lines.append(f"SURVIVAL(STRESS,{st}) @75% deploy on 10L: final={eq/1e5:.1f}L maxDD={mdd*100:.0f}%")
txt = "\n\n".join(lines)
print(txt)
(OUT / "SUMMARY.md").write_text(txt + "\n", encoding="utf-8")
print("saved ->", OUT)
