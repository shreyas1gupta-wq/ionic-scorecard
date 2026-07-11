"""A4-CARD: COVID replication — monthly NIFTY ATM short straddle w/ 30% daily-settle SL, 2011-2021.06.
Spec frozen in commit f923851 BEFORE this run. All option/fut prices = SETTLE_PR (bhavcopy daily).
KILL: (a) 2020-Feb..Jun per-lot DD > 3x max 2011-2019 DD, or (b) full-period expectancy <= 0.
"""
import datetime as dt
import json
import numpy as np, pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/A4_COVID_REPLICATION_20260711"
OUT.mkdir(parents=True, exist_ok=True)
D = ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist"

frames = [pd.read_parquet(p) for p in sorted(D.glob("fo_idx_*.parquet"))]
fo = pd.concat(frames, ignore_index=True)
fo = fo[fo.SYMBOL == "NIFTY"].copy()
fo["d"] = pd.to_datetime(fo.TIMESTAMP, format="%d-%b-%Y", errors="coerce")
if fo["d"].isna().any():
    fo.loc[fo.d.isna(), "d"] = pd.to_datetime(fo.loc[fo.d.isna(), "TIMESTAMP"], errors="coerce")
fo["exp"] = pd.to_datetime(fo.EXPIRY_DT, format="%d-%b-%Y", errors="coerce")
fo = fo.dropna(subset=["d", "exp"])
for c in ["STRIKE_PR", "SETTLE_PR", "CONTRACTS"]:
    fo[c] = pd.to_numeric(fo[c], errors="coerce")

fut = fo[fo.INSTRUMENT == "FUTIDX"].sort_values(["d", "exp"]).drop_duplicates("d")  # near-month fut per day
fut_settle = fut.set_index("d")["SETTLE_PR"]
opt = fo[fo.INSTRUMENT == "OPTIDX"]
tdays = sorted(fut_settle.index)

# crash rule: 3d realized vol of fut settles vs 1yr rolling median
ret = fut_settle.sort_index().pct_change()
rv3 = ret.rolling(3).std()
rv_med = rv3.rolling(252, min_periods=200).median()
halve = (rv3 > 2 * rv_med).fillna(False)

trades, skipped = [], 0
cursor = tdays[0]
while True:
    # entry = first trading day > cursor
    nxt = [t for t in tdays if t > cursor]
    if not nxt:
        break
    e_day = nxt[0]
    spot = fut_settle.get(e_day, np.nan)
    day_opts = opt[(opt.d == e_day)]
    # expiry nearest 30 cal DTE in [20,45]
    exps = day_opts.exp.unique()
    cand = [x for x in exps if 20 <= (x - e_day).days <= 45]
    if not cand or np.isnan(spot):
        cursor = e_day + pd.Timedelta(days=27); skipped += 1; continue
    # try candidate expiries by |DTE-30| preference; within each, nearest tradeable strike.
    # (2020 lesson: far weeklies are LISTED with model settles but CONTRACTS=0 — untraded-but-priced
    # trap; fall back to the liquid monthly instead of skipping the month.)
    ok_strikes, exp = None, None
    for exp_try in sorted(cand, key=lambda x: abs((x - e_day).days - 30)):
        ch = day_opts[day_opts.exp == exp_try]
        for k in sorted(ch.STRIKE_PR.unique(), key=lambda k: abs(k - spot))[:8]:
            ce = ch[(ch.STRIKE_PR == k) & (ch.OPTION_TYP == "CE")]
            pe = ch[(ch.STRIKE_PR == k) & (ch.OPTION_TYP == "PE")]
            if len(ce) and len(pe) and ce.SETTLE_PR.iloc[0] > 0.05 and pe.SETTLE_PR.iloc[0] > 0.05 \
               and ce.CONTRACTS.iloc[0] > 0 and pe.CONTRACTS.iloc[0] > 0:
                ok_strikes = (k, ce.SETTLE_PR.iloc[0], pe.SETTLE_PR.iloc[0])
                exp = exp_try
                break
        if ok_strikes is not None:
            break
    if ok_strikes is None:
        cursor = min(cand, key=lambda x: abs((x - e_day).days - 30)); skipped += 1; continue
    K, ce0, pe0 = ok_strikes
    # walk daily settles STRICTLY BEFORE expiry (LANDMINE #9: expiry-day option SETTLE_PR
    # in bhavcopy = UNDERLYING settlement level, not option price — never read it)
    path = opt[(opt.exp == exp) & (opt.STRIKE_PR == K) & (opt.d > e_day) & (opt.d < exp)]
    # underlying settle at expiry for intrinsic: near-fut settle on expiry day (or last day <= exp)
    s_exp = fut_settle.get(exp, np.nan)
    if np.isnan(s_exp):
        prior = [t for t in tdays if t <= exp]
        s_exp = fut_settle[prior[-1]] if prior else np.nan
    if np.isnan(s_exp):
        cursor = exp; skipped += 1; continue
    pnl, legs_traded = 0.0, 2
    for cp, entry_px in [("CE", ce0), ("PE", pe0)]:
        ser = path[path.OPTION_TYP == cp].sort_values("d").set_index("d")["SETTLE_PR"]
        exit_px, hit = None, False
        days = list(ser.index)
        for i, dd in enumerate(days):
            if ser[dd] >= 1.30 * entry_px:
                exit_px = ser[days[i + 1]] if i + 1 < len(days) else ser[dd]
                hit = True
                break
        if exit_px is None:  # survived to expiry -> cash-settle at intrinsic
            exit_px = max(s_exp - K, 0.0) if cp == "CE" else max(K - s_exp, 0.0)
        pnl += entry_px - exit_px
        legs_traded += 1 if hit else 0  # exit-before-expiry costs a trade; expiry cash-settle doesn't
    cost = 2.0 + (legs_traded - 2) * 1.0  # 1pt/leg one-way: 2 entries + SL exits
    cost_pct = 0.005 * (ce0 + pe0)
    trades.append(dict(entry=e_day, expiry=exp, K=K, prem=ce0 + pe0, gross=pnl,
                       net=pnl - cost, net_pct=pnl - cost_pct, halve=bool(halve.get(e_day, False))))
    cursor = exp

tr = pd.DataFrame(trades)
tr.to_csv(OUT / "a4_cycles.csv", index=False)

# per-lot cumulative (points), drawdowns
cum = tr.set_index("entry")["net"].cumsum()
dd = cum - cum.cummax()
pre = dd[dd.index < "2020-01-01"]
covid = dd[(dd.index >= "2020-02-01") & (dd.index <= "2020-06-30")]
max_dd_pre = -pre.min() if len(pre) else np.nan
max_dd_covid = -(covid.min() - cum.cummax()[covid.index[0]] + cum.cummax()[covid.index[0]]) if len(covid) else np.nan
# simpler: covid window drawdown relative to running peak
max_dd_covid = -covid.min() if len(covid) else np.nan
exp_mean = tr.net.mean()
t = exp_mean / (tr.net.std(ddof=1) / np.sqrt(len(tr)))

# equity sim at spec sizing
eq, path_eq = 1_000_000.0, []
for _, r in tr.iterrows():
    spot = fut_settle.get(r.entry, np.nan)
    margin = spot * 75 * 0.15
    lots = max(0, int(0.75 * eq / margin)) if margin > 0 and eq > 0 else 0
    if r.halve:
        lots //= 2
    eq += r.net * 75 * lots
    path_eq.append(eq)
eqs = pd.Series(path_eq, index=tr.entry)
eq_dd = ((eqs - eqs.cummax()) / eqs.cummax() * 100)

bar_a = bool(max_dd_covid > 3 * max_dd_pre)
bar_b = bool(exp_mean <= 0)
verdict = "KILL" if (bar_a or bar_b) else "COVID-SURVIVABLE"

lines = [f"cycles={len(tr)} skipped={skipped} span {tr.entry.min().date()}..{tr.expiry.max().date()}",
         f"per-lot: mean net {exp_mean:+.1f} pts/cycle (t={t:.2f}), median {tr.net.median():+.1f}, win% {(tr.net>0).mean()*100:.0f}%",
         f"alt cost (0.5% prem): mean {tr.net_pct.mean():+.1f}",
         f"maxDD per-lot 2011-2019: {max_dd_pre:.0f} pts | COVID window (2020-02..06): {max_dd_covid:.0f} pts | ratio {max_dd_covid/max_dd_pre:.2f}x (bar: >3x)",
         f"BAR (a) covid>3x pre: {bar_a} | BAR (b) expectancy<=0: {bar_b}",
         f"equity sim Rs10L @15% notional margin, 75% deploy, crash-halving: final Rs {eqs.iloc[-1]:,.0f}, maxDD {eq_dd.min():.1f}%",
         f"2020 cycles: " + " | ".join(f"{r.entry:%b}: {r.net:+.0f}" for _, r in tr[(tr.entry>='2020-01-01')&(tr.entry<='2020-12-31')].iterrows()),
         f"worst-5 cycles: " + ", ".join(f"{r.entry:%Y-%m} {r.net:+.0f}" for _, r in tr.nsmallest(5, 'net').iterrows()),
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "A4-CARD", "frozen_commit": "f923851", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "a4_covid_replication.py", "data": ["fo_bhavcopy_hist (D-009 verified 2026-07-11)"],
        "n_obs": int(len(tr)), "metrics": {"mean_net_pts": round(float(exp_mean), 2), "t": round(float(t), 2),
        "covid_dd_pts": round(float(max_dd_covid), 0), "pre_dd_pts": round(float(max_dd_pre), 0),
        "eq_final": round(float(eqs.iloc[-1]), 0), "eq_maxdd_pct": round(float(eq_dd.min()), 1)},
        "validation": {"era_split": "see RESULTS_RAW", "bootstrap_ci95": None,
                       "lookahead_ast": "pre-flight run", "one_day_lag": "daily settles, SL fills next-day settle"},
        "verdict": verdict, "bars_hit": [b for b, hit in [("covid>3x", bar_a), ("expectancy<=0", bar_b)] if hit],
        "trials_increment": 1, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written")
