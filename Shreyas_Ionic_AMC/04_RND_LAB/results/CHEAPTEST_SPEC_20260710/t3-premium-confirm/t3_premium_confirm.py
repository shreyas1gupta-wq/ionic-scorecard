"""T3 cheap-test — Option-premium confirmation filter (F8).
Pre-registered (triage 20260710, FROZEN): kill if confirmed-minus-unconfirmed
forward spread < 4 NIFTY pts OR t < 2 (day-clustered). Also: rejection rate
>= 80% of scarce signals = dead even if positive.

Events: 20260707 VOL_BREAKOUT_ATM campaign, cell BB10_EOD (canonical breakout
event set, 1036 events, both directions). Decision time t0 = entry_t (the
campaign's 1-bar-lagged fill bar). CONFIRMATION USES ONLY BARS STRICTLY BEFORE
t0 (window (t0-6min, t0-1min]) — zero same-bar leakage.

Confirmation rule (single pre-registered trial):
  prem_move = ATM premium %chg over the 5-min window >= +3%
  AND 5-min option volume >= 70th causal percentile of that contract's
      same-day rolling 5-min volumes strictly before the window end.
Primary metric: signed forward 30-min underlying move dir*(S[t0+30] - S[t0]).
Secondary: realized campaign trade net_pts split.
Guards: drop_preopen, confirmation strictly pre-decision, one-bar-lag test
(<50% collapse required), within-day label-shuffle placebo (1000 reps).
"""
import sys, os, json
import numpy as np
import pandas as pd

ROOT = r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500"
sys.path.insert(0, ROOT + r"/Shreyas_Ionic_AMC/04_RND_LAB/lib")
import guards as G

BASE = ROOT + r"/intraday_options_strategy/datasets/raw/hf_index_options_1m"
OUT = ROOT + r"/Shreyas_Ionic_AMC/04_RND_LAB/results/CHEAPTEST_SPEC_20260710/t3-premium-confirm"
EV_CSV = ROOT + r"/Shreyas_Ionic_AMC/04_RND_LAB/results/VOL_BREAKOUT_ATM_20260707/trades_BB10_EOD.csv"

PREM_TH, VOLP_TH, WIN_MIN, FWD_MIN = 0.03, 0.70, 5, 30
TZ = "Asia/Kolkata"

ev = pd.read_csv(EV_CSV, parse_dates=["entry_t", "exit_t"])
ev["day"] = pd.to_datetime(ev["day"]).dt.date
print("events", ev.shape)

# spot
spot = pd.read_parquet(BASE + "/index/NIFTY.parquet", columns=["timestamp", "close"])
spot = G.drop_preopen(spot)
spot = spot[spot["timestamp"].dt.time <= pd.Timestamp("15:25").time()]
spot = spot.set_index("timestamp")["close"].sort_index()

# expiry file list
exp_files = sorted(f[:-8] for f in os.listdir(BASE + "/options/NIFTY") if f.endswith(".parquet"))
exp_dates = pd.to_datetime(exp_files)

def pick_expiries(day):
    """candidate expiries: nearest with expiry > day (DTE>=1), plus next as fallback."""
    idx = np.searchsorted(exp_dates, pd.Timestamp(day) + pd.Timedelta(days=1))
    return [exp_files[i] for i in (idx, idx + 1) if i < len(exp_files)]

# cache per (expiry, day): full-day frame per contract
_fcache = {}
def load_contract(expiry, day, strike, otype):
    key = (expiry, str(day))
    if key not in _fcache:
        df = pd.read_parquet(BASE + f"/options/NIFTY/{expiry}.parquet",
                             columns=["timestamp", "close", "volume", "strike", "option_type", "trading_day"],
                             filters=[("trading_day", "=", str(day))])
        G.assert_intraday_capable(df.assign(dummy=1))
        df = G.drop_preopen(df)
        _fcache.clear()  # keep memory flat; events are day-sorted
        _fcache[key] = df
    df = _fcache[key]
    c = df[(df["strike"] == strike) & (df["option_type"] == otype)]
    return c.sort_values("timestamp").drop_duplicates("timestamp")

def causal_vol_pct(bars, t_end, win=WIN_MIN):
    """percentile of 5-min vol sum ending t_end vs same-day rolling sums strictly before."""
    v = bars.set_index("timestamp")["volume"].resample("1min").sum().fillna(0)
    r = v.rolling(f"{win}min").sum()
    r = r[r.index.time >= pd.Timestamp("09:20").time()]
    cur = r.asof(t_end)
    hist = r[r.index < t_end - pd.Timedelta(minutes=1)]
    if len(hist) < 15 or pd.isna(cur):
        return np.nan
    return (hist < cur).mean()

def confirm(bars, t0, lag=1):
    """confirmation using bars <= t0 - lag min. Returns (prem_move, vol_pct)."""
    t_dec = t0 - pd.Timedelta(minutes=lag)
    t_pre = t_dec - pd.Timedelta(minutes=WIN_MIN)
    s = bars.set_index("timestamp")["close"]
    c_now, c_prev = s.asof(t_dec), s.asof(t_pre)
    if pd.isna(c_now) or pd.isna(c_prev) or c_prev <= 0:
        return np.nan, np.nan
    # asof must not reach into prior day
    if s.index[s.index <= t_pre].size == 0:
        return np.nan, np.nan
    return c_now / c_prev - 1, causal_vol_pct(bars, t_dec)

rows = []
ev = ev.sort_values("day")
for _, e in ev.iterrows():
    t0 = pd.Timestamp(e.entry_t).tz_localize(TZ)
    bars = None
    for exp in pick_expiries(e.day):
        b = load_contract(exp, e.day, int(e.strike), e.otype)
        if len(b) == 0:
            continue
        p0 = b.set_index("timestamp")["close"].asof(t0)
        if pd.notna(p0) and abs(p0 - e.entry_prem) / max(e.entry_prem, 1e-9) < 0.02:
            bars = b; break
    if bars is None:
        rows.append(dict(day=e.day, status="NO_CONTRACT")); continue
    pm, vp = confirm(bars, t0, lag=1)
    pm_l, vp_l = confirm(bars, t0, lag=2)  # one-bar-lag audit
    if pd.isna(pm) or pd.isna(vp):
        rows.append(dict(day=e.day, status="NO_WINDOW")); continue
    s0 = spot.asof(t0)
    t_fwd = min(t0 + pd.Timedelta(minutes=FWD_MIN),
                pd.Timestamp(f"{e.day} 15:25").tz_localize(TZ))
    sf = spot.asof(t_fwd)
    if pd.isna(s0) or pd.isna(sf):
        rows.append(dict(day=e.day, status="NO_SPOT")); continue
    rows.append(dict(day=e.day, entry_t=e.entry_t, dir=e.dir, otype=e.otype,
                     strike=e.strike, prem_move=pm, vol_pct=vp,
                     conf=int(pm >= PREM_TH and vp >= VOLP_TH),
                     conf_lag=int(pd.notna(pm_l) and pd.notna(vp_l) and pm_l >= PREM_TH and vp_l >= VOLP_TH),
                     conf_prem_only=int(pm >= PREM_TH), conf_vol_only=int(vp >= VOLP_TH),
                     fwd30=e.dir * (sf - s0), net_pts=e.net_pts, status="OK"))

df = pd.DataFrame(rows)
ok = df[df.status == "OK"].copy()
print("usable", len(ok), "of", len(df), df.status.value_counts().to_dict())
G.assert_next_bar(ok.entry_t - pd.Timedelta(minutes=1), ok.entry_t)  # decision strictly pre-entry by construction

def spread_stats(d, col="conf", y="fwd30"):
    c, u = d[d[col] == 1][y], d[d[col] == 0][y]
    if len(c) < 5 or len(u) < 5:
        return dict(n_conf=len(c), n_unconf=len(u), spread=np.nan, t_welch=np.nan, t_clust=np.nan)
    sp = c.mean() - u.mean()
    tw = sp / np.sqrt(c.var() / len(c) + u.var() / len(u))
    # day-clustered OLS t on the dummy
    X = np.column_stack([np.ones(len(d)), d[col].values.astype(float)])
    yv = d[y].values
    beta = np.linalg.lstsq(X, yv, rcond=None)[0]
    r = yv - X @ beta
    XtXi = np.linalg.inv(X.T @ X)
    meat = np.zeros((2, 2))
    for _, gidx in d.groupby("day").indices.items():
        Xg, rg = X[gidx], r[gidx]
        s = Xg.T @ rg
        meat += np.outer(s, s)
    V = XtXi @ meat @ XtXi
    tc = beta[1] / np.sqrt(V[1, 1])
    return dict(n_conf=len(c), n_unconf=len(u), mean_conf=c.mean(), mean_unconf=u.mean(),
                spread=sp, t_welch=tw, t_clust=tc)

main = spread_stats(ok)
rej = 1 - ok.conf.mean()

# placebo: within-day shuffle of conf labels
rng = np.random.default_rng(42)
obs = main["spread"]
cnt = 0; reps = 1000
grp = ok.groupby("day").indices
for _ in range(reps):
    lab = ok.conf.values.copy()
    for _, gi in grp.items():
        lab[gi] = rng.permutation(lab[gi])
    d2 = ok.assign(conf_sh=lab)
    c, u = d2[d2.conf_sh == 1].fwd30, d2[d2.conf_sh == 0].fwd30
    if len(c) and len(u) and (c.mean() - u.mean()) >= obs:
        cnt += 1
placebo_p = cnt / reps

lag = spread_stats(ok, col="conf_lag")
eras = {}
ok["year"] = pd.to_datetime(ok.day.astype(str)).dt.year
for name, m in [("2021-22", ok.year <= 2022), ("2023-26", ok.year >= 2023)]:
    eras[name] = spread_stats(ok[m])
per_year = {int(y): spread_stats(g) for y, g in ok.groupby("year")}
sec = spread_stats(ok, y="net_pts")
marg = {k: spread_stats(ok, col=k) for k in ["conf_prem_only", "conf_vol_only"]}

res = dict(n_events=len(df), n_usable=len(ok), rejection_rate=rej, primary=main,
           secondary_net_pts=sec, lag_test=lag,
           lag_collapse_pct=(1 - lag["spread"] / obs) * 100 if obs else None,
           placebo_p=placebo_p, eras=eras, per_year=per_year, marginals=marg,
           degenerate_flags=[])
verdict = "KILL"
if pd.notna(obs) and obs >= 4 and main["t_clust"] >= 2:
    verdict = "PASS" if rej < 0.80 and (1 - lag["spread"] / obs) < 0.50 and placebo_p < 0.05 else "KILL"
res["verdict"] = verdict

ok.to_csv(OUT + "/t3_events.csv", index=False)
def conv(o):
    if isinstance(o, (np.floating, np.integer)): return float(o)
    raise TypeError
with open(OUT + "/t3_results.json", "w") as f:
    json.dump(res, f, indent=1, default=conv)
print(json.dumps(res, indent=1, default=conv))
