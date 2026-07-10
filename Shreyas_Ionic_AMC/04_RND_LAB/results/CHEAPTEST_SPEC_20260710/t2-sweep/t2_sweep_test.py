"""T2 CHEAP-TEST — Liquidity-sweep reversal on the UNDERLYING (NIFTY spot 1-min).
Pre-registered (triage 20260710_principal_intraday_spec_triage.md, T2, FROZEN):
  Event: level sweep >=0.05% penetration + close-back within k in {1,3,5} bars.
  Levels: PDH / PDL (kill-relevant), round-100 and OR15 (variants, reported).
  Metric: 30-min forward signed return (pts) from next-bar open, MINUS
          time-of-day-matched unconditional baseline (5-min buckets).
  KILL: mean reversal edge <5 pts OR day-clustered t<2.5 on BOTH PDH & PDL.
        Era split (era1 <=2022-12-31 vs era2 2023-01-01..2025-12-31): sign flip = kill
        regardless of pooled t.
  Guards: drop_preopen BEFORE PDH/PDL, assert_next_bar, audit_session,
          within-day label-shuffle placebo, one-bar-lag test.
Data: intraday_options_strategy/datasets/raw/hf_index_options_1m/index/NIFTY.parquet
      (2021-05-24 -> 2026-06-03; NOTE: no 2020 spot minutes on disk, era1 starts 2021-06).
"""
import sys, os
import numpy as np
import pandas as pd

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
sys.path.insert(0, os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "lib"))
import guards as G
import lookahead_audit as LA

OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "results",
                   "CHEAPTEST_SPEC_20260710", "t2-sweep")
os.makedirs(OUT, exist_ok=True)

SWEEP_PCT = 0.0005          # 0.05% penetration beyond the level
KS = [1, 3, 5]              # close-back windows (bars)
HORIZON = 30                # forward minutes
DEDUP_MIN = 30              # min minutes between events, same level-type+side
RNG = np.random.default_rng(20260710)

# ---------------- load ----------------
df = pd.read_parquet(os.path.join(ROOT, "intraday_options_strategy", "datasets",
                                  "raw", "hf_index_options_1m", "index", "NIFTY.parquet"))
df = G.drop_preopen(df, "timestamp")                     # L2 BEFORE PDH/PDL
df = df[df["timestamp"].dt.time <= pd.Timestamp("15:30").time()]
assert LA.audit_session(df.assign(ts=df["timestamp"].dt.tz_localize(None)), "ts") == []
df = df.sort_values("timestamp").reset_index(drop=True)
df["date"] = df["timestamp"].dt.date
df["minofday"] = df["timestamp"].dt.hour * 60 + df["timestamp"].dt.minute

# per-day arrays
days = sorted(df["date"].unique())
day_hi = df.groupby("date")["high"].max()
day_lo = df.groupby("date")["low"].min()
pdh = {d2: day_hi[d1] for d1, d2 in zip(days[:-1], days[1:])}
pdl = {d2: day_lo[d1] for d1, d2 in zip(days[:-1], days[1:])}

# OR15 (first 15 min 09:15-09:29)
or15 = df[df["minofday"] < 9 * 60 + 30].groupby("date").agg(orh=("high", "max"), orl=("low", "min"))

# ---------------- baseline: time-of-day-matched 30-min forward move ----------------
# unconditional (close[t+30] - open[t+1]) per 5-min entry bucket, full sample
g = {d: sub.reset_index(drop=True) for d, sub in df.groupby("date")}
base_rows = []
for d, sub in g.items():
    o = sub["open"].values; c = sub["close"].values; m = sub["minofday"].values
    n = len(sub)
    for i in range(n - 1 - HORIZON):
        base_rows.append((d, m[i], c[i + 1 + HORIZON] - o[i + 1]))
base = pd.DataFrame(base_rows, columns=["date", "minofday", "fwd"])
base["bucket"] = base["minofday"] // 5
tod_base = base.groupby("bucket")["fwd"].mean()          # signed drift per TOD bucket

# ---------------- event detection ----------------
def detect(level_type):
    """Return event list: (date, signal_idx_in_day, side) side=+1 long(PDL/low), -1 short(PDH/high)."""
    ev = []
    for d, sub in g.items():
        h = sub["high"].values; l = sub["low"].values; c = sub["close"].values
        m = sub["minofday"].values; n = len(sub)
        levels = []  # (level_price, side)
        if level_type == "PDH":
            if d in pdh: levels = [(pdh[d], -1)]
        elif level_type == "PDL":
            if d in pdl: levels = [(pdl[d], +1)]
        elif level_type == "OR15":
            if d in or15.index:
                levels = [(or15.loc[d, "orh"], -1), (or15.loc[d, "orl"], +1)]
        elif level_type == "ROUND":
            lo100 = int(np.floor(l.min() / 100)) * 100
            hi100 = int(np.ceil(h.max() / 100)) * 100
            for L in range(lo100, hi100 + 100, 100):
                levels += [(float(L), -1), (float(L), +1)]
        for L, side in levels:
            last_ev = -10**9
            i = 0
            start = np.searchsorted(m, 9 * 60 + 30) if level_type == "OR15" else 0
            i = start
            while i < n - 1:
                pen = (h[i] - L) / L if side == -1 else (L - l[i]) / L
                crossed = h[i] > L if side == -1 else l[i] < L
                if crossed and pen >= SWEEP_PCT:
                    # find first close-back within max(KS) bars
                    jb = None
                    for j in range(0, max(KS) + 1):
                        if i + j >= n: break
                        back = c[i + j] < L if side == -1 else c[i + j] > L
                        if back:
                            jb = j; break
                    if jb is not None:
                        sig = i + jb                     # signal bar = close-back bar
                        if m[sig] <= 15 * 60 + 30 - HORIZON - 2 and sig + 1 + HORIZON < n \
                           and m[sig] - last_ev >= DEDUP_MIN:
                            ev.append((d, sig, side, jb, L))
                            last_ev = m[sig]
                        i = sig + 1
                        continue
                i += 1
    return ev

def build_trades(events, lag_extra=0):
    rows = []
    for d, sig, side, jb, L in events:
        sub = g[d]
        e = sig + 1 + lag_extra                          # entry = NEXT bar open (+optional lag)
        x = e + HORIZON
        if x >= len(sub): continue
        entry = sub["open"].iloc[e]; exitp = sub["close"].iloc[x]
        fwd = side * (exitp - entry)
        bkt = sub["minofday"].iloc[e] // 5
        bl = side * tod_base.get(bkt, 0.0)
        rows.append((d, str(sub["timestamp"].iloc[sig]), str(sub["timestamp"].iloc[e]),
                     side, jb, L, entry, exitp, fwd, bl, fwd - bl))
    t = pd.DataFrame(rows, columns=["date", "signal_ts", "entry_ts", "side", "close_back_j",
                                    "level", "entry", "exit", "fwd_pts", "baseline_pts", "excess_pts"])
    if len(t):
        G.assert_next_bar(t["signal_ts"], t["entry_ts"])  # L5
    return t

def day_clustered_t(x: pd.DataFrame, col="excess_pts"):
    dm = x.groupby("date")[col].mean()
    if len(dm) < 5: return np.nan
    return dm.mean() / (dm.std(ddof=1) / np.sqrt(len(dm)))

def era(dte):
    d = pd.Timestamp(dte)
    if d <= pd.Timestamp("2022-12-31"): return "era1_2021-22"
    if d <= pd.Timestamp("2025-12-31"): return "era2_2023-25"
    return "era3_2026tail"

# ---------------- run all variants ----------------
all_trades = {}
stats = []
for lt in ["PDH", "PDL", "ROUND", "OR15"]:
    events = detect(lt)
    tr = build_trades(events)
    tr["era"] = tr["date"].map(era)
    all_trades[lt] = tr
    for k in KS:
        s = tr[tr["close_back_j"] <= k]
        if len(s) < 10:
            stats.append((lt, k, len(s), np.nan, np.nan, np.nan, np.nan, np.nan, np.nan)); continue
        edge = s["excess_pts"].mean()
        t_plain = s["excess_pts"].mean() / (s["excess_pts"].std(ddof=1) / np.sqrt(len(s)))
        t_day = day_clustered_t(s)
        e1 = s[s["era"] == "era1_2021-22"]["excess_pts"].mean()
        e2 = s[s["era"] == "era2_2023-25"]["excess_pts"].mean()
        e3 = s[s["era"] == "era3_2026tail"]["excess_pts"].mean()
        stats.append((lt, k, len(s), edge, t_plain, t_day, e1, e2, e3))
st = pd.DataFrame(stats, columns=["level_type", "k", "n", "edge_pts", "t_plain",
                                  "t_dayclust", "era1_edge", "era2_edge", "era3_edge"])
st.to_csv(os.path.join(OUT, "t2_variant_stats.csv"), index=False)
pd.concat([t.assign(level_type=lt) for lt, t in all_trades.items()]) \
  .to_csv(os.path.join(OUT, "t2_events.csv"), index=False)

# ---------------- placebo: within-day time-of-day-matched random bars ----------------
plc = []
for lt in ["PDH", "PDL"]:
    tr = all_trades[lt]
    means = []
    for _ in range(200):
        vals = []
        for _, r in tr.iterrows():
            sub = g[r["date"]]
            bkt = pd.Timestamp(r["entry_ts"]).hour * 60 + pd.Timestamp(r["entry_ts"]).minute
            # random bar same day, entry index range valid
            n = len(sub)
            e = RNG.integers(1, n - HORIZON - 1)
            fwd = r["side"] * (sub["close"].iloc[e + HORIZON] - sub["open"].iloc[e])
            bl = r["side"] * tod_base.get(sub["minofday"].iloc[e] // 5, 0.0)
            vals.append(fwd - bl)
        means.append(np.mean(vals))
    real = tr["excess_pts"].mean()
    pval = (np.sum(np.array(means) >= real) + 1) / 201 if real > 0 else \
           (np.sum(np.array(means) <= real) + 1) / 201
    plc.append((lt, real, np.mean(means), np.std(means), pval))
plc = pd.DataFrame(plc, columns=["level_type", "real_edge", "placebo_mean", "placebo_std", "p_shuffle"])
plc.to_csv(os.path.join(OUT, "t2_placebo.csv"), index=False)

# ---------------- one-bar-lag test (pooled PDH+PDL excess, k=5) ----------------
def metric_with_lag(lag):
    vals = []
    for lt in ["PDH", "PDL"]:
        t = build_trades(detect(lt), lag_extra=lag)
        vals.append(t["excess_pts"].mean() * len(t))
    return float(np.sum(vals))
lag = LA.one_day_lag_test(metric_with_lag)

with open(os.path.join(OUT, "t2_console.txt"), "w", encoding="utf-8") as f:
    f.write(st.to_string(index=False) + "\n\n")
    f.write(plc.to_string(index=False) + "\n\n")
    f.write(f"one-bar-lag: {lag}\n")
    for lt, tr in all_trades.items():
        f.write(f"{lt}: n={len(tr)} days={tr['date'].nunique()}\n")
print(st.to_string(index=False))
print(plc.to_string(index=False))
print("one-bar-lag:", lag)
