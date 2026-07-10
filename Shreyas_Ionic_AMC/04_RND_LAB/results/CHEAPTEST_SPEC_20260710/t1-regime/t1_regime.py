# T1 - Regime-engine predictivity cheap-test (Gate-3, pre-registered)
# Triage: Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260710_principal_intraday_spec_triage.md
#
# PRE-REGISTERED KILL THRESHOLD (FROZEN, from triage doc):
#   A regime SURVIVES only if day-clustered |t| >= 3 AND |effect| >= 6 NIFTY pts per 30-min
#   (conditional mean 30-min forward return vs unconditional baseline).
#   A+C both fail -> System 1 dead as designed; <2/4 regimes survive -> Layer-1 killed
#   (families may only be run unconditioned).
#
# SPEC RECONSTRUCTION NOTE (declared BEFORE first run, one pass, no tuning):
#   The Principal's exact A/B/C/D formulas were not persisted to disk (triage doc names
#   the regimes only). Canonical fixed classifier pre-registered here:
#     5-min bars from 1-min NIFTY spot (>=09:15 IST only, guards.drop_preopen).
#     Indicators on concatenated 5-min closes (computed at bar CLOSE, used for the
#     window starting at that close -> no lookahead):
#       EMA20, EMA50 (adjust=False), ATR14 (Wilder, 5-min OHLC),
#       RV12 = rolling std of last 12 5-min log returns, in % per 5-min bar.
#     Trend score s = (EMA20 - EMA50) / ATR14.
#     FIXED thresholds (single pass):
#       D (Volatile)   : RV12 > 0.12%  (takes precedence)
#       A (Trend-up)   : s > +0.5
#       B (Trend-down) : s < -0.5
#       C (Range/chop) : otherwise
#   Horizons: fwd30 = close[t+6]-close[t], fwd60 = close[t+12]-close[t], same-day only.
#   Eras: 2020-2022 vs 2023-2025 (+ per-year). Sample 2020-01-01..2025-12-31.
#   Stats: OLS fwd30 ~ 1{regime=r}, cluster-robust SE by trading date;
#          effect reported = mean_r - overall_mean (t identical to dummy t).
#   Battery: within-day label-shuffle placebo (seed 42) + 1-bar-lag test (<50% collapse).
#   Trial ledger: T1 = 4 trials (4 regimes), one pass, no variants.
import sys, os
import numpy as np
import pandas as pd

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
sys.path.insert(0, ROOT + "/Shreyas_Ionic_AMC/04_RND_LAB/lib")
import guards as G

OUT = ROOT + "/Shreyas_Ionic_AMC/04_RND_LAB/results/CHEAPTEST_SPEC_20260710/t1-regime"
SRC = ROOT + "/intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv"

# frozen params
RV_D, S_TREND = 0.12, 0.5
EMA_F, EMA_S, ATR_N, RV_N = 20, 50, 14, 12
KILL_T, KILL_PTS = 3.0, 6.0

df = pd.read_csv(SRC, parse_dates=["date"])
df = df.rename(columns={"date": "timestamp"})
# source is naive IST (kaggle zerodha-style dump, first bar 09:15) - NOT the HF-UTC parquet;
# fix_ist_dates not applicable (would refuse naive tz); document instead of guessing.
df = G.drop_preopen(df)                      # landmine #2: kill pre-09:15 prints
df = df[df["timestamp"].dt.time < pd.Timestamp("15:30").time()]
df = df[(df["timestamp"] >= "2020-01-01") & (df["timestamp"] < "2026-01-01")].copy()
df["day"] = df["timestamp"].dt.date

# ---- 5-min bars, stamped by bar END (signal usable from bar close onward) ----
g = df.set_index("timestamp").groupby("day")
b = g.resample("5min", closed="left", label="left").agg(
    open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
b = b.dropna().reset_index()
b["bar_end"] = b["timestamp"] + pd.Timedelta(minutes=5)

# ---- indicators on concatenated 5-min series (past-only at each bar close) ----
c = b["close"]
ema_f = c.ewm(span=EMA_F, adjust=False).mean()
ema_s = c.ewm(span=EMA_S, adjust=False).mean()
prev_c = c.shift(1)
tr = pd.concat([b["high"] - b["low"], (b["high"] - prev_c).abs(), (b["low"] - prev_c).abs()], axis=1).max(axis=1)
atr = tr.ewm(alpha=1.0 / ATR_N, adjust=False).mean()
rv = (np.log(c).diff().rolling(RV_N).std() * 100)

s = (ema_f - ema_s) / atr
regime = pd.Series("C", index=b.index)
regime[s > S_TREND] = "A"
regime[s < -S_TREND] = "B"
regime[rv > RV_D] = "D"   # precedence
b["regime"], b["s"], b["rv"] = regime, s, rv
b = b.iloc[EMA_S:]        # warmup: drop first 50 bars of sample

# ---- same-day forward returns from bar close ----
grp = b.groupby("day")["close"]
for h, k in ((6, "fwd30"), (12, "fwd60")):
    b[k] = grp.shift(-h) - b["close"]
# guard L5 analog: forward window starts strictly after signal bar close
G.assert_next_bar(b["bar_end"] - pd.Timedelta(minutes=5), b["bar_end"])

b["year"] = pd.to_datetime(b["day"].astype(str)).dt.year
b["era"] = np.where(b["year"] <= 2022, "2020-22", "2023-25")


def cluster_t(sub, ycol, r):
    """OLS y = a + b*1{regime==r}; day-clustered SE; effect = mean_r - overall mean."""
    d = sub.dropna(subset=[ycol])
    y = d[ycol].to_numpy(float)
    x = (d["regime"] == r).to_numpy(float)
    n, nr = len(y), int(x.sum())
    if nr < 30 or nr == n:
        return dict(n=n, n_r=nr, effect=np.nan, t=np.nan)
    X = np.column_stack([np.ones(n), x])
    XtX_inv = np.linalg.inv(X.T @ X)
    beta = XtX_inv @ (X.T @ y)
    e = y - X @ beta
    days = d["day"].to_numpy()
    meat = np.zeros((2, 2))
    ed = pd.DataFrame({"e": e, "x": x, "day": days})
    for _, gg in ed.groupby("day"):
        Xg = np.column_stack([np.ones(len(gg)), gg["x"].to_numpy()])
        ue = Xg.T @ gg["e"].to_numpy()
        meat += np.outer(ue, ue)
    V = XtX_inv @ meat @ XtX_inv
    G_ = ed["day"].nunique()
    V *= G_ / (G_ - 1) * (n - 1) / (n - 2)   # CR1 small-sample
    t = beta[1] / np.sqrt(V[1, 1])
    effect = beta[1] * (1 - nr / n)          # mean_r - overall mean
    return dict(n=n, n_r=nr, share=nr / n, mean_r=y[x == 1].mean(),
                base=y.mean(), effect=effect, t=t,
                vol_r=y[x == 1].std(), vol_all=y.std())


rows = []
for scope_name, sub in [("FULL", b)] + [(e, b[b["era"] == e]) for e in ("2020-22", "2023-25")] \
        + [(str(yy), b[b["year"] == yy]) for yy in sorted(b["year"].unique())]:
    for r in "ABCD":
        for ycol in ("fwd30", "fwd60"):
            st = cluster_t(sub, ycol, r)
            st.update(scope=scope_name, regime=r, horizon=ycol)
            rows.append(st)
res = pd.DataFrame(rows)

# ---- placebo: shuffle regime labels within day ----
rng = np.random.default_rng(42)
bp = b.copy()
bp["regime"] = bp.groupby("day")["regime"].transform(lambda x: rng.permutation(x.to_numpy()))
plac = pd.DataFrame([dict(cluster_t(bp, "fwd30", r), regime=r) for r in "ABCD"])

# ---- 1-bar-lag test (regime lagged 5 min) ----
bl = b.copy()
bl["regime"] = bl.groupby("day")["regime"].shift(1)
bl = bl.dropna(subset=["regime"])
lag = pd.DataFrame([dict(cluster_t(bl, "fwd30", r), regime=r) for r in "ABCD"])

res.to_csv(OUT + "/RESULTS.csv", index=False)
plac.to_csv(OUT + "/PLACEBO_SHUFFLE.csv", index=False)
lag.to_csv(OUT + "/LAG1BAR.csv", index=False)
b[["bar_end", "day", "close", "s", "rv", "regime", "fwd30", "fwd60"]].to_csv(
    OUT + "/regime_bars.csv.gz", index=False, compression="gzip")

# ---- verdict vs frozen bar ----
full30 = res[(res.scope == "FULL") & (res.horizon == "fwd30")].set_index("regime")
print("bars=%d days=%d span=%s..%s" % (len(b), b["day"].nunique(), b["day"].min(), b["day"].max()))
print("\nregime shares:", b["regime"].value_counts(normalize=True).round(3).to_dict())
print("\nFULL fwd30 (pts):")
print(full30[["n_r", "share", "mean_r", "base", "effect", "t", "vol_r", "vol_all"]].round(3).to_string())
surv = {r: (abs(full30.loc[r, "t"]) >= KILL_T) and (abs(full30.loc[r, "effect"]) >= KILL_PTS) for r in "ABCD"}
print("\nSURVIVES (|t|>=3 & |effect|>=6pts/30min):", surv)
print("A+C both fail ->", (not surv["A"]) and (not surv["C"]))
print("survivors:", sum(surv.values()), "/4")
print("\nERA fwd30:")
print(res[(res.scope.isin(["2020-22", "2023-25"])) & (res.horizon == "fwd30")]
      [["scope", "regime", "n_r", "effect", "t"]].round(3).to_string(index=False))
print("\nPER-YEAR fwd30 effect(t):")
py = res[(res.horizon == "fwd30") & (res.scope.str.match(r"^\d{4}$"))]
print(py.pivot(index="scope", columns="regime", values="effect").round(2).to_string())
print(py.pivot(index="scope", columns="regime", values="t").round(2).to_string())
print("\nPLACEBO shuffle fwd30 effect(t):")
print(plac[["regime", "effect", "t"]].round(3).to_string(index=False))
print("\nLAG-1-BAR fwd30 effect(t) [collapse check]:")
print(lag[["regime", "effect", "t"]].round(3).to_string(index=False))
print("\nFULL fwd60 (pts):")
print(res[(res.scope == "FULL") & (res.horizon == "fwd60")]
      [["regime", "n_r", "effect", "t"]].round(3).to_string(index=False))
