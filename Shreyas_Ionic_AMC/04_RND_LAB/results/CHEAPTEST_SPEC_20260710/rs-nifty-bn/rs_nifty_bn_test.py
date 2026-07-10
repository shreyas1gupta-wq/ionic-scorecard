"""
CHEAP-TEST F9 (key: rs-nifty-bn) — NIFTY vs BANKNIFTY relative strength.
Pre-registered BEFORE any run (frozen):
  Signal: RS = trailing 30-min log-return(BN) - log-return(NIFTY); z-scored over
          trailing 375 one-min bars (~1 trading day), within-session computation only.
  Event:  z crosses from |z|<1.5 to |z|>=1.5 (activation edge). Entry = NEXT 1-min bar
          open (assert_next_bar). Non-overlapping: next event only after horizon elapses.
          No entries after 14:30 (60-min horizon must complete same session).
  Outcome: signed forward NIFTY return in POINTS over next 30 and 60 min under the
          CONTINUATION convention: effect = sign(z) * (N_fwd - N_entry).
          (Positive => BN outperformance predicts NIFTY up = continuation;
           negative => mean-reversion. Sign discovered, magnitude tested.)
  KILL (frozen): day-clustered |t| < 2 OR |mean effect| < 4 NIFTY pts on BOTH horizons
          (i.e. pass requires at least one horizon with |t|>=2 AND |mean|>=4), AND
          era sign-flip on the passing horizon = KILL regardless of pooled t.
  Guards: drop pre-09:15 bars, next-bar entry assert, within-day label shuffle placebo,
          +1-bar extra-lag test (<50% collapse required), day-clustered SEs.
  Trials ledger: 2 (30-min, 60-min horizons). No parameter search.
"""
import sys, numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:/Users/Shreyas.1Gupta/OneDrive - Angel Broking Limited/Desktop/Backup/NIFTY 500")
sys.path.insert(0, str(ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/lib"))
import guards  # noqa

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/CHEAPTEST_SPEC_20260710/rs-nifty-bn"
RS_WIN, Z_WIN, Z_TH, MAX_ENTRY = 30, 375, 1.5, "14:30"

def load(name):
    df = pd.read_parquet(ROOT / f"intraday_options_strategy/datasets/processed/{name}_1min.parquet")
    df = df.reset_index().rename(columns={"dt": "timestamp"})
    df = guards.drop_preopen(df, "timestamp")          # landmine #2
    df = df[df["timestamp"].dt.time <= pd.Timestamp("15:29").time()]
    return df.set_index("timestamp")[["open", "close"]]

n, b = load("nifty"), load("banknifty")
df = n.join(b, lsuffix="_n", rsuffix="_b", how="inner").sort_index()
df["date"] = df.index.date
g = df.groupby("date", group_keys=False)

# trailing RS within session-safe global series (rolling spans overnight; RS window 30min
# crossing overnight is a stale-signal risk -> restrict signal validity to bars with >=RS_WIN
# bars elapsed in the session)
logn = np.log(df["close_n"]); logb = np.log(df["close_b"])
df["rs"] = (logb - logb.shift(RS_WIN)) - (logn - logn.shift(RS_WIN))
df["bar_in_day"] = g.cumcount()
df.loc[df["bar_in_day"] < RS_WIN, "rs"] = np.nan
# NOTE: each session's first RS_WIN bars are NaN, so a Z_WIN(375)-bar window always
# contains ~30 NaNs; min_periods=300 (mechanical fix, not a threshold change).
m = df["rs"].rolling(Z_WIN, min_periods=300).mean()
s = df["rs"].rolling(Z_WIN, min_periods=300).std()
df["z"] = (df["rs"] - m) / s

# activation edges
df["active"] = df["z"].abs() >= Z_TH
df["edge"] = df["active"] & ~df["active"].shift(1, fill_value=False)

pos = {ts: i for i, ts in enumerate(df.index)}
idx = df.index
close_n = df["close_n"].values; open_n = df["open_n"].values
dates = df["date"].values

results = {}
events_all = {}
for H in (30, 60):
    rows, last_exit = [], -1
    edge_idx = np.flatnonzero(df["edge"].values)
    for i in edge_idx:
        if i <= last_exit or i + 1 + H >= len(df):
            continue
        ts = idx[i]
        if ts.time() > pd.Timestamp(MAX_ENTRY).time():
            continue
        ei = i + 1                      # next-bar entry
        xo = ei + H
        if dates[xo] != dates[ei]:      # horizon must complete same session
            continue
        sgn = np.sign(df["z"].values[i])
        eff = sgn * (close_n[xo] - open_n[ei])
        rows.append((idx[i], idx[ei], dates[ei], sgn, eff,
                     sgn * (close_n[min(xo, ei + 30)] - open_n[ei])))
        last_exit = xo
    ev = pd.DataFrame(rows, columns=["signal_ts", "entry_ts", "date", "sign", "eff_pts", "eff30_dup"])
    guards.assert_next_bar(ev["signal_ts"], ev["entry_ts"])
    events_all[H] = ev
    # day-clustered t: mean of daily means weighted... use cluster-robust: t on daily mean effects
    daily = ev.groupby("date")["eff_pts"].mean()
    tstat = daily.mean() / (daily.std(ddof=1) / np.sqrt(len(daily)))
    results[H] = dict(n=len(ev), n_days=len(daily), mean_pts=ev["eff_pts"].mean(),
                      daily_mean=daily.mean(), t_dayclust=tstat)

# era table (60-min primary + 30-min)
def era(y):
    return "2015-18" if y <= 2018 else ("2019-22" if y <= 2022 else "2023-26")
era_rows = []
for H, ev in events_all.items():
    ev["era"] = pd.to_datetime(ev["date"]).map(lambda d: era(d.year))
    for e, grp in ev.groupby("era"):
        d = grp.groupby("date")["eff_pts"].mean()
        t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d))) if len(d) > 2 else np.nan
        era_rows.append(dict(horizon=H, era=e, n=len(grp), mean_pts=grp["eff_pts"].mean(), t_dayclust=t))
era_df = pd.DataFrame(era_rows)

# placebo: within-day shuffle of sign labels (60-min), 200 reps
rng = np.random.default_rng(42)
ev60 = events_all[60]
obs = abs(ev60["eff_pts"].mean())
raw = ev60["sign"] * ev60["eff_pts"]  # unsigned underlying move
plc = []
for _ in range(200):
    sh = ev60.groupby("date")["sign"].transform(lambda x: rng.permutation(x.values))
    plc.append(abs((sh * raw).mean()))
placebo_p = float(np.mean(np.array(plc) >= obs))

# +1-bar extra lag test (entry at i+2 instead of i+1), 60-min
rows = []
last_exit = -1
edge_idx = np.flatnonzero(df["edge"].values)
for i in edge_idx:
    if i <= last_exit or i + 2 + 60 >= len(df):
        continue
    if idx[i].time() > pd.Timestamp(MAX_ENTRY).time():
        continue
    ei, xo = i + 2, i + 2 + 60
    if dates[xo] != dates[ei] or dates[ei] != dates[i]:
        continue
    sgn = np.sign(df["z"].values[i])
    rows.append(sgn * (close_n[xo] - open_n[ei]))
    last_exit = xo
lag_mean = float(np.mean(rows))
base60 = results[60]["mean_pts"]
collapse = 1 - lag_mean / base60 if base60 != 0 else np.nan

# save
for H, ev in events_all.items():
    ev.drop(columns=["eff30_dup"]).to_csv(OUT / f"events_h{H}.csv", index=False)
era_df.to_csv(OUT / "era_table.csv", index=False)
summ = pd.DataFrame([dict(horizon=H, **v) for H, v in results.items()])
summ.to_csv(OUT / "headline.csv", index=False)

print("bars:", len(df), "span:", df.index.min(), "->", df.index.max())
print(summ.to_string(index=False))
print(era_df.to_string(index=False))
print(f"placebo p(|mean|>=obs) = {placebo_p:.3f} (obs={obs:.2f})")
print(f"lag+1bar mean60 = {lag_mean:.2f} vs base {base60:.2f}, collapse = {collapse:.1%}")
