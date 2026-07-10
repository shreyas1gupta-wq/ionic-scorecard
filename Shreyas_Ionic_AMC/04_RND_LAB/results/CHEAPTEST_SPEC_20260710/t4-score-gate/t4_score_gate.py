"""
T4 - GLBS score-gate (>=4/6) confluence monotonicity cheap-test.
Pre-registered (triage doc 20260710_principal_intraday_spec_triage.md, Arjun design):
  KILL if: day-clustered Spearman t < 2  OR  (bucket>=4 - bucket<=1) spread < 6 NIFTY pts.
  Top bucket (>=4) alone must clear 10 pts (2x stressed round-trip) or System 2 has no vehicle.
FROZEN BEFORE RUN. No threshold adjustment after results.

FLAGS (6 in spec; implemented 5 - deviations DOCUMENTED):
  1 liq_break   : within last 6 5-min bars, close crossed a level (PDH/PDL/round-100/OR15 hi-lo) in event direction.
  2 fvg         : directional 5-min fair-value gap (bull: low[t]>high[t-2]) within last 12 bars.
  3 vwap_side   : close on event side of session cumulative TWAP of typical price
                  (index volume==0 on disk -> VWAP impossible; TWAP proxy, documented deviation).
  4 volume      : dir-side ATM option 5-min volume > 1.5x trailing 20-bar median (same strike, shifted 1;
                  index has no volume -> ATM option volume proxy per Kavya ask #3, documented deviation).
  5 prem_break  : dir-side ATM option 5-min close > max of prior 12 closes of same strike (F8-style).
  6 oi_confirm  : DROPPED - deferred to T6 (3-bar OI lag column not yet built). Documented.

EVENTS: 5-min impulse bars 09:30-14:50 IST, |close-to-close 5-min move| >= trailing-20-day 75th pctile
        of |5-min moves| (adaptive, trailing only - no lookahead). Direction = sign of move.
        Entry = NEXT 5-min bar open (guards.assert_next_bar). Forward = dir * (close[entry+30min] - entry_open) pts.
COSTS: thresholds are pre-registered in NIFTY points and already encode COST_STANDARDS (D-021 APPROVED)
       2x stressed ATM weekly round-trip ~ 10 pts; no separate cost subtraction.
GUARDS: drop_preopen, assert_next_bar, audit_session, one-bar-lag test (<50% collapse), within-day label-shuffle placebo.
"""
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path(r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500")
sys.path.insert(0, str(BASE / "Shreyas_Ionic_AMC/04_RND_LAB/lib"))
import guards, lookahead_audit  # noqa

RAW = BASE / "intraday_options_strategy/datasets/raw/hf_index_options_1m"
OUT = BASE / "Shreyas_Ionic_AMC/04_RND_LAB/results/CHEAPTEST_SPEC_20260710/t4-score-gate"

# ---------- 1. spot 5-min bars ----------
spot = pd.read_parquet(RAW / "index/NIFTY.parquet")
spot = guards.drop_preopen(spot, "timestamp")
spot = spot[spot["timestamp"].dt.time <= pd.Timestamp("15:29").time()]
findings = lookahead_audit.audit_session(spot, "timestamp")
spot = spot.set_index("timestamp").sort_index()
b5 = spot.groupby(spot.index.floor("5min")).agg(
    open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"))
b5["day"] = b5.index.date
b5["bar_time"] = b5.index.time
print("spot 5-min bars:", b5.shape, "days:", b5["day"].nunique(),
      "range:", b5["day"].min(), "->", b5["day"].max())

# prior-day high/low (post-preopen-drop)
dstat = b5.groupby("day").agg(PDH=("high", "max"), PDL=("low", "min"))
dstat[["PDH", "PDL"]] = dstat[["PDH", "PDL"]].shift(1)  # PRIOR day
b5 = b5.join(dstat, on="day")

# OR15 (09:15-09:29 range)
or15 = b5[b5.index.time < pd.Timestamp("09:30").time()].groupby("day").agg(
    ORH=("high", "max"), ORL=("low", "min"))
b5 = b5.join(or15, on="day")

# session TWAP of typical price (VWAP proxy - index volume is 0)
tp = (b5["high"] + b5["low"] + b5["close"]) / 3
b5["twap"] = tp.groupby(b5["day"]).expanding().mean().reset_index(level=0, drop=True)

# ---------- flags on spot ----------
g = b5.groupby("day")
prev_close = g["close"].shift(1)

def crossed_up(level):
    return (prev_close < level) & (b5["close"] >= level)
def crossed_dn(level):
    return (prev_close > level) & (b5["close"] <= level)

r100_up = np.floor(prev_close / 100) * 100 + 100   # nearest round-100 above prev close
r100_dn = np.ceil(prev_close / 100) * 100 - 100
up_cross = (crossed_up(b5["PDH"]) | crossed_up(b5["ORH"]) | crossed_up(r100_up)).fillna(False)
dn_cross = (crossed_dn(b5["PDL"]) | crossed_dn(b5["ORL"]) | crossed_dn(r100_dn)).fillna(False)
# within last 6 bars incl current, same day
b5["liq_up"] = up_cross.groupby(b5["day"]).rolling(6, min_periods=1).max().reset_index(level=0, drop=True).astype(bool)
b5["liq_dn"] = dn_cross.groupby(b5["day"]).rolling(6, min_periods=1).max().reset_index(level=0, drop=True).astype(bool)

# FVG (3-bar, within same day, present in last 12 bars)
h2 = g["high"].shift(2); l2 = g["low"].shift(2)
fvg_bull = (b5["low"] > h2).fillna(False)
fvg_bear = (b5["high"] < l2).fillna(False)
b5["fvg_up"] = fvg_bull.groupby(b5["day"]).rolling(12, min_periods=1).max().reset_index(level=0, drop=True).astype(bool)
b5["fvg_dn"] = fvg_bear.groupby(b5["day"]).rolling(12, min_periods=1).max().reset_index(level=0, drop=True).astype(bool)

b5["vwap_up"] = b5["close"] > b5["twap"]
b5["vwap_dn"] = b5["close"] < b5["twap"]

# impulse events: |5-min move| >= trailing-20-DAY 75th pctile of |moves|
b5["mv"] = (b5["close"] - prev_close)
b5["mv_pct"] = b5["mv"].abs() / prev_close
day_p75 = b5.groupby("day")["mv_pct"].quantile(0.75)
thr = day_p75.rolling(20, min_periods=10).mean().shift(1)  # trailing, excludes today
b5["thr"] = b5["day"].map(thr)

# ---------- 2. ATM option 5-min series (front weekly) ----------
opt_dir = RAW / "options/NIFTY"
files = sorted(opt_dir.glob("*.parquet"))
print("expiry files:", len(files))
expiries = pd.to_datetime([f.stem for f in files])
day_close = b5.groupby("day")["close"].agg(["min", "max"])

CACHE = OUT / "atm5_cache"
CACHE.mkdir(exist_ok=True)
atm_parts = []
for i, (f, exp) in enumerate(zip(files, expiries)):
    cf = CACHE / (f.stem + ".parquet")
    if cf.exists():
        atm_parts.append(pd.read_parquet(cf)); continue
    if i % 20 == 0: print("opt file", i, f.stem, flush=True)
    try:
        o = pd.read_parquet(f, columns=["timestamp", "close", "volume", "strike",
                                        "option_type", "trading_day"])
    except Exception as e:
        print("READFAIL", f.stem, e); continue
    o["td"] = pd.to_datetime(o["trading_day"]).dt.date
    lo = (exp - pd.Timedelta(days=6)).date()
    o = o[(o["td"] > lo) & (o["td"] <= exp.date())]           # front-weekly window only
    if o.empty: continue
    # strike band around each day's spot range
    dc = day_close.reindex(o["td"].unique()).dropna()
    if dc.empty: continue
    lob = o["td"].map(dc["min"] - 150); hib = o["td"].map(dc["max"] + 150)
    o = o[(o["strike"] >= lob) & (o["strike"] <= hib)]
    if o.empty: continue
    o = guards.drop_preopen(o, "timestamp")
    o["bar"] = o["timestamp"].dt.floor("5min")
    ag = o.groupby(["bar", "strike", "option_type"]).agg(
        pclose=("close", "last"), pvol=("volume", "sum")).reset_index()
    ag["expiry"] = exp.date()
    ag.to_parquet(cf)
    atm_parts.append(ag)
opt5 = pd.concat(atm_parts, ignore_index=True)
del atm_parts
print("option 5-min rows:", opt5.shape)

# per (bar,strike,type): trailing features WITHIN day (cythonized groupby-rolling on sorted frame)
opt5["day"] = opt5["bar"].dt.date
opt5 = opt5.sort_values(["day", "strike", "option_type", "bar"]).reset_index(drop=True)
gcols = ["day", "strike", "option_type"]
opt5["pclose_s"] = opt5.groupby(gcols, sort=False)["pclose"].shift(1)
opt5["pvol_s"] = opt5.groupby(gcols, sort=False)["pvol"].shift(1)
opt5["prior12max"] = opt5.groupby(gcols, sort=False)["pclose_s"] \
    .rolling(12, min_periods=6).max().reset_index(drop=True).values
opt5["volmed20"] = opt5.groupby(gcols, sort=False)["pvol_s"] \
    .rolling(20, min_periods=4).median().reset_index(drop=True).values
print("rolling features done", flush=True)

# ---------- 3. events + score ----------
b5r = b5.reset_index()
b5r = b5r.rename(columns={b5r.columns[0]: "bar"})
b5r["bar"] = pd.to_datetime(b5r["bar"])
ev = b5r[(b5r["bar_time"] >= pd.Timestamp("09:30").time()) &
         (b5r["bar_time"] <= pd.Timestamp("14:50").time()) &
         (b5r["mv_pct"] >= b5r["thr"]) & b5r["thr"].notna()].copy()
ev["dir"] = np.sign(ev["mv"]).astype(int)
ev = ev[ev["dir"] != 0]
ev["atm"] = (ev["close"] / 50).round() * 50
ev["otype"] = np.where(ev["dir"] > 0, "CE", "PE")

ev = ev.merge(opt5[["bar", "strike", "option_type", "pclose", "pvol", "prior12max", "volmed20"]],
              left_on=["bar", "atm", "otype"], right_on=["bar", "strike", "option_type"], how="left")
opt_cov = ev["pclose"].notna().mean()
print("ATM option coverage on events: %.1f%%" % (100 * opt_cov))
ev = ev[ev["pclose"].notna()].copy()   # restrict to option-covered events (documented)

ev["f_liq"] = np.where(ev["dir"] > 0, ev["liq_up"], ev["liq_dn"]).astype(int)
ev["f_fvg"] = np.where(ev["dir"] > 0, ev["fvg_up"], ev["fvg_dn"]).astype(int)
ev["f_vwap"] = np.where(ev["dir"] > 0, ev["vwap_up"], ev["vwap_dn"]).astype(int)
ev["f_vol"] = ((ev["pvol"] > 1.5 * ev["volmed20"]) & ev["volmed20"].notna()).astype(int)
ev["f_prem"] = ((ev["pclose"] > ev["prior12max"]) & ev["prior12max"].notna()).astype(int)
FLAGS = ["f_liq", "f_fvg", "f_vwap", "f_vol", "f_prem"]
ev["score"] = ev[FLAGS].sum(axis=1)

# ---------- 4. forward return: entry next bar open, +30min ----------
b5i = b5r.set_index("bar")
ev["entry_bar"] = ev["bar"] + pd.Timedelta(minutes=5)
ev["exit_bar"] = ev["bar"] + pd.Timedelta(minutes=35)   # entry + 6 x 5-min
ev["entry_open"] = b5i["open"].reindex(ev["entry_bar"]).values
ev["exit_close"] = b5i["close"].reindex(ev["exit_bar"]).values
ev = ev[ev["entry_open"].notna() & ev["exit_close"].notna()]
ev = ev[ev["exit_bar"].dt.date == ev["bar"].dt.date]     # same-day window
guards.assert_next_bar(ev["bar"], ev["entry_bar"])
ev["fwd_pts"] = ev["dir"] * (ev["exit_close"] - ev["entry_open"])
print("events scored:", len(ev), "days:", ev["day"].nunique())

# ---------- 5. stats ----------
def clustered_t(y, x, cl):
    X = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    e = y - X @ beta
    XtX_inv = np.linalg.inv(X.T @ X)
    meat = np.zeros((2, 2))
    df_ = pd.DataFrame({"cl": cl})
    for _, idx in df_.groupby("cl").groups.items():
        Xg = X[idx]; eg = e[idx]
        s = Xg.T @ eg
        meat += np.outer(s, s)
    V = XtX_inv @ meat @ XtX_inv
    G = df_["cl"].nunique()
    V *= G / (G - 1)
    return beta[1], beta[1] / np.sqrt(V[1, 1]), G

def headline(df):
    y = df["fwd_pts"].values; s = df["score"].values
    ry = pd.Series(y).rank().values; rs = pd.Series(s).rank().values
    rho = np.corrcoef(ry, rs)[0, 1]
    _, t_sp, G = clustered_t(ry, rs, df["day"].values.astype(str))
    top = df.loc[df["score"] >= 4, "fwd_pts"]
    bot = df.loc[df["score"] <= 1, "fwd_pts"]
    return dict(n=len(df), days=G, rho=rho, t_spearman_dayclust=t_sp,
                top_mean=top.mean(), top_n=len(top), bot_mean=bot.mean(), bot_n=len(bot),
                spread=(top.mean() - bot.mean()) if len(top) and len(bot) else np.nan)

H = headline(ev)
bucket = ev.groupby("score")["fwd_pts"].agg(["count", "mean", "median", "std"])
bucket["t_vs0"] = bucket["mean"] / (bucket["std"] / np.sqrt(bucket["count"]))
print(bucket)
print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in H.items()}, indent=1))

# era table
ev["era"] = pd.cut(pd.to_datetime(ev["day"].astype(str)),
                   bins=pd.to_datetime(["2021-01-01", "2023-01-01", "2025-01-01", "2027-01-01"]),
                   labels=["2021-22", "2023-24", "2025-26"])
era_rows = []
for e_, d in ev.groupby("era", observed=True):
    if len(d) < 50: continue
    h = headline(d); h["era"] = str(e_); era_rows.append(h)
era_df = pd.DataFrame(era_rows).set_index("era")
print(era_df)

# per-flag marginals (documented as the +5 marginal trials)
marg = []
for f in FLAGS:
    on = ev.loc[ev[f] == 1, "fwd_pts"]; off = ev.loc[ev[f] == 0, "fwd_pts"]
    _, tt, _ = clustered_t(ev["fwd_pts"].values, ev[f].values.astype(float), ev["day"].values.astype(str))
    marg.append(dict(flag=f, on_n=len(on), on_mean=on.mean(), off_mean=off.mean(),
                     spread=on.mean() - off.mean(), t_dayclust=tt))
marg_df = pd.DataFrame(marg)
print(marg_df)

# placebo: within-day shuffle of scores, 200 reps
rng = np.random.default_rng(42)
def shuffled_spread():
    s = ev.groupby("day")["score"].transform(lambda x: rng.permutation(x.values))
    top = ev.loc[s >= 4, "fwd_pts"].mean(); bot = ev.loc[s <= 1, "fwd_pts"].mean()
    return top - bot
plc = np.array([shuffled_spread() for _ in range(200)])
plc_p = float((plc >= (H["spread"] if np.isfinite(H["spread"]) else 0)).mean())
print("placebo spread mean %.2f sd %.2f p(placebo>=real)=%.3f" % (plc.mean(), plc.std(), plc_p))

# one-bar-lag test: lag ALL flags/score by one extra 5-min bar within day
ev2 = ev.sort_values("bar").copy()
ev2["score_lag"] = ev2.groupby("day")["score"].shift(1)
ev2 = ev2[ev2["score_lag"].notna()]
top_l = ev2.loc[ev2["score_lag"] >= 4, "fwd_pts"].mean()
bot_l = ev2.loc[ev2["score_lag"] <= 1, "fwd_pts"].mean()
lag_spread = top_l - bot_l
base_spread = H["spread"]
collapse = 1 - (lag_spread / base_spread) if (np.isfinite(base_spread) and base_spread != 0) else np.nan
print("one-bar-lag spread %.2f vs base %.2f collapse %.1f%%" % (lag_spread, base_spread, 100 * collapse))

# ---------- 6. verdict (FROZEN thresholds) ----------
kill_reasons = []
if not (H["t_spearman_dayclust"] >= 2): kill_reasons.append("Spearman day-clustered t=%.2f < 2" % H["t_spearman_dayclust"])
if not (H["spread"] >= 6): kill_reasons.append("top-vs-bottom spread=%.2f pts < 6" % H["spread"])
top_fail = not (H["top_mean"] >= 10)
verdict = "KILL" if kill_reasons else ("PASS" if not top_fail else "KILL")
if not kill_reasons and top_fail:
    kill_reasons.append("top bucket mean=%.2f pts < 10 (2x stressed round-trip) - no vehicle" % H["top_mean"])
print("VERDICT:", verdict, kill_reasons)

# ---------- save ----------
ev_out = ev[["bar", "day", "dir", "score"] + FLAGS + ["fwd_pts", "mv_pct", "atm", "otype", "pclose", "pvol"]]
ev_out.to_csv(OUT / "t4_events.csv", index=False)
bucket.to_csv(OUT / "t4_bucket_stats.csv")
era_df.to_csv(OUT / "t4_era_stats.csv")
marg_df.to_csv(OUT / "t4_flag_marginals.csv", index=False)
res = dict(headline=H, verdict=verdict, kill_reasons=kill_reasons, placebo_p=plc_p,
           placebo_mean=float(plc.mean()), placebo_sd=float(plc.std()),
           lag_spread=float(lag_spread), lag_collapse_pct=float(100 * collapse),
           opt_coverage=float(opt_cov), audit_findings=findings)
with open(OUT / "t4_result.json", "w") as fh:
    json.dump(res, fh, indent=1, default=str)
print("SAVED to", OUT)
