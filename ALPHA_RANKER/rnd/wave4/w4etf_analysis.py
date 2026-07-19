"""W4ETF — cross-asset ETF sleeve: factor scoring (1M/1Y/5Y) + rotation backtest.
No fabrication: every asset's history length is used as-is; short-history assets are flagged,
not padded/back-filled. Monthly rebalance frequency throughout (tactical AA convention).
"""
import os, json
import numpy as np
import pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
UNI = os.path.join(BASE, "datasets", "etf_universe")
GS = os.path.join(BASE, "datasets", "etf_gold_silver")
OUTDIR = os.path.join(BASE, "ALPHA_RANKER", "rnd", "wave4")

def load_gs(path, fix_utc_landmine):
    df = pd.read_parquet(path)
    ts = pd.to_datetime(df["timestamp"], utc=True)
    if fix_utc_landmine:
        d = ts.dt.tz_convert("Asia/Kolkata").dt.date
    else:
        d = ts.dt.tz_convert("Asia/Kolkata").dt.date if ts.dt.tz is not None else ts.dt.date
    out = pd.DataFrame({"date": pd.to_datetime(d), "close": df["close"].values})
    return out.dropna().sort_values("date").drop_duplicates("date")

def load_yf(path):
    df = pd.read_parquet(path)
    out = pd.DataFrame({"date": pd.to_datetime(df["Date"]), "close": df["Close"].values})
    return out.dropna().sort_values("date").drop_duplicates("date")

ASSETS = {}
ASSETS["GOLD"] = load_gs(os.path.join(GS, "goldbees_daily.parquet"), True)
ASSETS["SILVER"] = load_gs(os.path.join(GS, "silverbees_daily.parquet"), True)
ASSETS["NIFTY50"] = load_gs(os.path.join(GS, "niftybees_daily.parquet"), False)
ASSETS["COPPER"] = load_yf(os.path.join(UNI, "COPPER_HG.parquet"))
ASSETS["NASDAQ"] = load_yf(os.path.join(UNI, "QQQ.parquet"))
ASSETS["SP500"] = load_yf(os.path.join(UNI, "SPY.parquet"))
ASSETS["MIDCAP"] = load_yf(os.path.join(UNI, "MIDCAP_ETF_A.parquet"))          # MID150BEES, Nippon Nifty Midcap150
ASSETS["SMALLCAP"] = load_yf(os.path.join(UNI, "MOSMALL250.parquet"))          # Motilal Nifty Smallcap250 ETF, SHORT (<2.5y)
ASSETS["MOMENTUM"] = load_yf(os.path.join(UNI, "MOMENTUM_ETF_B.parquet"))      # ABSL Nifty200 Momentum30 ETF
ASSETS["LOWVOL"] = load_yf(os.path.join(UNI, "LOWVOL_ETF_A.parquet"))          # Kotak Nifty100 LowVol30 ETF
# MICROCAP: no verified-identity ETF found on disk/yfinance -> BLOCKED, excluded (not fabricated)

COVERAGE = {k: {"n_obs": len(v), "date_min": str(v["date"].min().date()), "date_max": str(v["date"].max().date()),
                "years": round((v["date"].max() - v["date"].min()).days / 365.25, 2)} for k, v in ASSETS.items()}
COVERAGE["MICROCAP"] = {"status": "BLOCKED - no ETF with verified identity match for Nifty Microcap250 found "
                                   "(tried MICROCAP250.NS, MOMICROCAP.NS, MOM250.NS, MICROCAP.NS - all empty; "
                                   "MOM50.NS resolved but longName 'Motilal Oswal M50 ETF' is NOT confirmed as microcap -> excluded, not guessed)"}

# ---- monthly panel (month-end close, forward-filled within each asset's own history only) ----
monthly = {}
for k, df in ASSETS.items():
    s = df.set_index("date")["close"]
    m = s.resample("ME").last()
    monthly[k] = m
panel = pd.DataFrame(monthly)
panel.to_parquet(os.path.join(OUTDIR, "w4etf_monthly_panel.parquet"))

def ts_mom(s, months):
    return s / s.shift(months) - 1

def dma_dist(daily_close, window):
    ma = daily_close.rolling(window).mean()
    return (daily_close / ma - 1)

def realized_vol(daily_ret, window):
    return daily_ret.rolling(window).std() * np.sqrt(252)

def price_percentile(s):
    # expanding percentile rank of current level vs own trailing history to date (no lookahead)
    return s.expanding(min_periods=12).apply(lambda x: (x.iloc[-1] >= x).mean(), raw=False)

# ---- build daily-derived features, then sample at month-end ----
features = {}
for k, df in ASSETS.items():
    d = df.set_index("date")["close"].asfreq("D").ffill(limit=5)  # tolerate small gaps only
    ret = d.pct_change()
    feat = pd.DataFrame(index=d.index)
    feat["mom_1m"] = d / d.shift(21) - 1
    feat["mom_3m"] = d / d.shift(63) - 1
    feat["mom_6m"] = d / d.shift(126) - 1
    feat["mom_12m"] = d / d.shift(252) - 1
    feat["mom_12m1"] = d.shift(21) / d.shift(252) - 1   # 12-1 relative momentum basis
    feat["dist_200dma"] = dma_dist(d, 200)
    feat["rv_21"] = realized_vol(ret, 21)
    feat["rv_252"] = realized_vol(ret, 252)
    feat["px_pctile"] = price_percentile(d)
    feat["carry_trend"] = d / d.rolling(252).mean() - 1  # spot-vs-trend carry/roll proxy
    features[k] = feat.resample("ME").last()

# cross-sectional rank of 12-1 momentum at each month-end (only among assets with data that date)
mom12m1_wide = pd.DataFrame({k: features[k]["mom_12m1"] for k in features})
cs_rank = mom12m1_wide.rank(axis=1, pct=True)

FACTOR_SNAPSHOT = {}
last_date = panel.index.max()
for k in ASSETS:
    f = features[k]
    if last_date not in f.index:
        f = f.reindex(f.index.union([last_date])).sort_index().ffill()
    row = f.loc[last_date] if last_date in f.index else f.iloc[-1]
    cs = cs_rank[k].iloc[-1] if k in cs_rank.columns else np.nan
    FACTOR_SNAPSHOT[k] = {
        "asof": str(last_date.date()),
        "mom_1m": row.get("mom_1m"), "mom_3m": row.get("mom_3m"), "mom_6m": row.get("mom_6m"),
        "mom_12m": row.get("mom_12m"), "cs_rank_12m1": cs,
        "dist_200dma": row.get("dist_200dma"), "rv_252": row.get("rv_252"),
        "px_pctile": row.get("px_pctile"), "carry_trend": row.get("carry_trend"),
    }

def zscore_series(s):
    return (s - s.rolling(36, min_periods=12).mean()) / s.rolling(36, min_periods=12).std()

# ---- horizon scores (rule-based, no fitted weights -> avoids overfitting a 10-asset universe) ----
scores = {"1M": {}, "1Y": {}, "5Y": {}}
for k in ASSETS:
    f = features[k]
    if last_date not in f.index:
        continue
    row = f.loc[last_date]
    # 1M: short trend continuation + mean-reversion flag at extremes (extreme dist_200dma or rv spike -> discount)
    mom1 = row["mom_1m"]
    extreme_penalty = -0.5 if abs(row["dist_200dma"]) > 0.15 else 0.0
    scores["1M"][k] = (np.sign(mom1) * min(abs(mom1) * 5, 1.0) if pd.notna(mom1) else np.nan) + extreme_penalty
    # 1Y: TS-momentum (12m) + relative strength (cs rank, centered) + carry(trend) proxy
    ts12 = row["mom_12m"]
    csr = cs_rank[k].iloc[-1] if k in cs_rank.columns else np.nan
    carry = row["carry_trend"]
    scores["1Y"][k] = np.nanmean([
        (np.sign(ts12) * min(abs(ts12) * 2, 1.0) if pd.notna(ts12) else np.nan),
        ((csr - 0.5) * 2 if pd.notna(csr) else np.nan),
        (np.sign(carry) * min(abs(carry) * 3, 1.0) if pd.notna(carry) else np.nan),
    ])
    # 5Y: valuation-vs-own-history mean reversion (low percentile = attractive) + long trend sign
    pxp = row["px_pctile"]
    long_trend = row["mom_12m"]  # best available long-trend proxy given history constraints
    val_score = (1 - 2 * pxp) if pd.notna(pxp) else np.nan  # low percentile -> positive (cheap-vs-own-history)
    scores["5Y"][k] = np.nanmean([val_score, (np.sign(long_trend) * 0.5 if pd.notna(long_trend) else np.nan)])

# ---- ROTATION BACKTEST: core-6 (long overlap) + full universe (short overlap) ----
COST_BPS_ROUNDTRIP = {"GOLD": 15, "SILVER": 25, "COPPER": 20, "NASDAQ": 5, "SP500": 5, "NIFTY50": 10,
                       "MIDCAP": 20, "SMALLCAP": 30, "MOMENTUM": 25, "LOWVOL": 25}  # DRAFT proxy, not in COST_STANDARDS.md (equity-only doc) - flagged

def run_rotation(universe, mom_col="mom_12m1", topfrac=0.5, label=""):
    sub = pd.DataFrame({k: features[k][mom_col] for k in universe})
    px = panel[universe]
    rets = px.pct_change()
    fwd_rets = rets.shift(-1)  # signal at t must be applied to the return REALIZED t->t+1, not t-1->t (lookahead fix)
    common = sub.dropna(how="all").index
    dates = [d for d in common if d in fwd_rets.index][:-1]
    strat_ret, ew_ret, turnover_hist, weights_prev = [], [], [], pd.Series(0.0, index=universe)
    for i, d in enumerate(dates):
        avail = sub.loc[d].dropna()
        if len(avail) < 2:
            strat_ret.append(np.nan); ew_ret.append(np.nan); continue
        n_top = max(1, int(np.ceil(len(avail) * topfrac)))
        selected = avail.sort_values(ascending=False).index[:n_top]
        selected = [a for a in selected if avail[a] > 0]  # absolute TS-mom filter: no negative-momentum holdings
        w = pd.Series(0.0, index=universe)
        if len(selected) > 0:
            w[selected] = 1.0 / len(selected)
        else:
            w[:] = 0.0  # all-cash
        turnover = (w - weights_prev).abs().sum() / 2
        turnover_hist.append(turnover)
        nxt = fwd_rets.loc[d] if d in fwd_rets.index else pd.Series(np.nan, index=universe)
        gross = (w * nxt.reindex(universe).fillna(0)).sum()
        cost_bps = sum(COST_BPS_ROUNDTRIP.get(a, 20) for a in universe) / len(universe)
        net = gross - turnover * (cost_bps / 10000.0)
        strat_ret.append(net)
        ewn = nxt.reindex(universe).fillna(0).mean()
        ew_ret.append(ewn)
        weights_prev = w
    strat = pd.Series(strat_ret, index=dates).dropna()
    ew = pd.Series(ew_ret, index=dates).dropna()

    def stats(r):
        if len(r) < 6:
            return {"n": len(r), "ann_ret": None, "ann_vol": None, "sharpe": None, "maxdd": None}
        ann_ret = (1 + r).prod() ** (12 / len(r)) - 1
        ann_vol = r.std() * np.sqrt(12)
        sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
        cum = (1 + r).cumprod()
        maxdd = (cum / cum.cummax() - 1).min()
        return {"n": len(r), "ann_ret": round(float(ann_ret), 4), "ann_vol": round(float(ann_vol), 4),
                "sharpe": round(float(sharpe), 3), "maxdd": round(float(maxdd), 4)}

    result = {"label": label, "universe": universe, "n_months": len(strat),
              "strategy_net": stats(strat), "equal_weight_bh": stats(ew),
              "avg_turnover": round(float(np.mean(turnover_hist)), 3) if turnover_hist else None}

    # drop-one robustness
    dropone = {}
    for a in universe:
        u2 = [x for x in universe if x != a]
        if len(u2) < 3:
            continue
        r2 = run_rotation_simple(u2, mom_col, topfrac)
        dropone[f"drop_{a}"] = r2
    result["drop_one_sharpe"] = dropone

    # era split
    if len(strat) >= 20:
        half = len(strat) // 2
        era1, era2 = strat.iloc[:half], strat.iloc[half:]
        result["era_split"] = {"era1_sharpe": stats(era1)["sharpe"], "era2_sharpe": stats(era2)["sharpe"],
                                "era1_n": len(era1), "era2_n": len(era2)}
    return result

def run_rotation_simple(universe, mom_col, topfrac):
    """lightweight re-run returning just strategy sharpe, for drop-one loop"""
    sub = pd.DataFrame({k: features[k][mom_col] for k in universe})
    px = panel[universe]
    rets = px.pct_change()
    fwd_rets = rets.shift(-1)
    common = sub.dropna(how="all").index
    dates = [d for d in common if d in fwd_rets.index][:-1]
    strat_ret, weights_prev = [], pd.Series(0.0, index=universe)
    for d in dates:
        avail = sub.loc[d].dropna()
        if len(avail) < 2:
            strat_ret.append(np.nan); continue
        n_top = max(1, int(np.ceil(len(avail) * topfrac)))
        selected = avail.sort_values(ascending=False).index[:n_top]
        selected = [a for a in selected if avail[a] > 0]
        w = pd.Series(0.0, index=universe)
        if selected:
            w[selected] = 1.0 / len(selected)
        turnover = (w - weights_prev).abs().sum() / 2
        nxt = fwd_rets.loc[d] if d in fwd_rets.index else pd.Series(np.nan, index=universe)
        gross = (w * nxt.reindex(universe).fillna(0)).sum()
        cost_bps = sum(COST_BPS_ROUNDTRIP.get(a, 20) for a in universe) / len(universe)
        strat_ret.append(gross - turnover * (cost_bps / 10000.0))
        weights_prev = w
    r = pd.Series(strat_ret, index=dates).dropna()
    if len(r) < 6:
        return None
    ann_ret = (1 + r).prod() ** (12 / len(r)) - 1
    ann_vol = r.std() * np.sqrt(12)
    return round(float(ann_ret / ann_vol), 3) if ann_vol > 0 else None

CORE6 = ["GOLD", "SILVER", "COPPER", "NASDAQ", "SP500", "NIFTY50"]
FULL9 = ["GOLD", "SILVER", "COPPER", "NASDAQ", "SP500", "NIFTY50", "MIDCAP", "SMALLCAP", "MOMENTUM", "LOWVOL"]

res_core6_1y = run_rotation(CORE6, "mom_12m1", 0.5, "CORE6_1Y_TSMOM_RS")
res_full9_1y = run_rotation(FULL9, "mom_12m1", 0.5, "FULL9_1Y_TSMOM_RS")
res_core6_1m = run_rotation(CORE6, "mom_1m", 0.5, "CORE6_1M_TSMOM_RS")

# HONESTY CHECK: the "full-history" backtests above run from ~1994-2026, but SILVER (the binding
# constraint) only exists on our disk from 2022-02 -> for most of that window the strategy is
# effectively "SP500/NASDAQ/COPPER only" (pre-2013) then "+NIFTY50" (2013+) then "+GOLD" (2021+),
# NOT the real 6-asset tradable universe. Re-run restricted to dates where ALL core-6 assets are
# concurrently available -- this is the honest test of "what could an India investor actually rotate".
concurrent_start = max(ASSETS[k]["date"].min() for k in CORE6)
panel_concurrent = panel.loc[panel.index >= concurrent_start]
def run_rotation_windowed(universe, mom_col, topfrac, label, start_date):
    # temporarily restrict global panel/features via closures by filtering post-hoc: simplest is to
    # call run_rotation but then slice; re-implement lightweight windowed version instead.
    sub = pd.DataFrame({k: features[k][mom_col] for k in universe})
    px = panel[universe]
    rets = px.pct_change()
    fwd_rets = rets.shift(-1)
    common = sub.dropna(how="all").index
    dates = [d for d in common if d in fwd_rets.index and d >= start_date][:-1]
    strat_ret, ew_ret, turnover_hist, weights_prev = [], [], [], pd.Series(0.0, index=universe)
    for d in dates:
        avail = sub.loc[d].dropna()
        if len(avail) < 2:
            continue
        n_top = max(1, int(np.ceil(len(avail) * topfrac)))
        selected = avail.sort_values(ascending=False).index[:n_top]
        selected = [a for a in selected if avail[a] > 0]
        w = pd.Series(0.0, index=universe)
        if selected:
            w[selected] = 1.0 / len(selected)
        turnover = (w - weights_prev).abs().sum() / 2
        turnover_hist.append(turnover)
        nxt = fwd_rets.loc[d] if d in fwd_rets.index else pd.Series(np.nan, index=universe)
        gross = (w * nxt.reindex(universe).fillna(0)).sum()
        cost_bps = sum(COST_BPS_ROUNDTRIP.get(a, 20) for a in universe) / len(universe)
        net = gross - turnover * (cost_bps / 10000.0)
        strat_ret.append(net); ew_ret.append(nxt.reindex(universe).fillna(0).mean())
        weights_prev = w
    strat = pd.Series(strat_ret, index=dates[:len(strat_ret)]).dropna()
    ew = pd.Series(ew_ret, index=dates[:len(ew_ret)]).dropna()
    def stats(r):
        if len(r) < 6:
            return {"n": len(r), "ann_ret": None, "ann_vol": None, "sharpe": None, "maxdd": None}
        ann_ret = (1 + r).prod() ** (12 / len(r)) - 1
        ann_vol = r.std() * np.sqrt(12)
        sharpe = ann_ret / ann_vol if ann_vol > 0 else np.nan
        cum = (1 + r).cumprod()
        maxdd = (cum / cum.cummax() - 1).min()
        return {"n": len(r), "ann_ret": round(float(ann_ret), 4), "ann_vol": round(float(ann_vol), 4),
                "sharpe": round(float(sharpe), 3), "maxdd": round(float(maxdd), 4)}
    return {"label": label, "start_date": str(start_date.date()), "n_months": len(strat),
            "strategy_net": stats(strat), "equal_weight_bh": stats(ew)}

res_core6_1y_concurrent = run_rotation_windowed(CORE6, "mom_12m1", 0.5, "CORE6_1Y_CONCURRENT_SINCE_ALL6_LIVE", concurrent_start)
res_core6_1m_concurrent = run_rotation_windowed(CORE6, "mom_1m", 0.5, "CORE6_1M_CONCURRENT_SINCE_ALL6_LIVE", concurrent_start)

# ---- per-factor pooled IC (asset-month panel obs), full-history vs concurrent-only ----
def pooled_ic(universe, factor_col, fwd_horizon_months, start_date=None):
    rows = []
    px = panel[universe]
    fwd = px.pct_change(fwd_horizon_months).shift(-fwd_horizon_months)
    for k in universe:
        f = features[k][factor_col]
        fw = fwd[k]
        df = pd.concat([f.rename("factor"), fw.rename("fwd")], axis=1).dropna()
        if start_date is not None:
            df = df.loc[df.index >= start_date]
        df["asset"] = k
        rows.append(df)
    pooled = pd.concat(rows)
    if len(pooled) < 10:
        return {"n": len(pooled), "spearman": None}
    rho = pooled["factor"].corr(pooled["fwd"], method="spearman")
    return {"n": int(len(pooled)), "spearman": round(float(rho), 3)}

FACTOR_IC = {"full_history": {}, "concurrent_only": {}}
for fac_name, col in [("mom_1m", "mom_1m"), ("mom_3m", "mom_3m"), ("mom_12m", "mom_12m"),
                       ("carry_trend", "carry_trend"), ("dist_200dma", "dist_200dma"),
                       ("px_pctile_meanrev", "px_pctile")]:
    for horizon_name, h in [("fwd_1M", 1), ("fwd_1Y", 12)]:
        key = f"{fac_name}__{horizon_name}"
        sign = -1 if fac_name == "px_pctile_meanrev" else 1  # cheap-vs-history should predict positive fwd ret -> invert
        r_full = pooled_ic(CORE6, col, h)
        r_conc = pooled_ic(CORE6, col, h, start_date=concurrent_start)
        if r_full["spearman"] is not None:
            r_full["spearman"] = round(sign * r_full["spearman"], 3)
        if r_conc["spearman"] is not None:
            r_conc["spearman"] = round(sign * r_conc["spearman"], 3)
        FACTOR_IC["full_history"][key] = r_full
        FACTOR_IC["concurrent_only"][key] = r_conc

print("\nFACTOR IC (pooled asset-month, Spearman, sign-adjusted so + = factor helps):")
for scope in ["full_history", "concurrent_only"]:
    print(" ", scope)
    for k, v in FACTOR_IC[scope].items():
        print("   ", k, v)

OUT = {
    "coverage": COVERAGE,
    "factor_snapshot": FACTOR_SNAPSHOT,
    "horizon_scores": scores,
    "backtests": {
        "core6_1y_full_history": res_core6_1y,
        "full9_1y_full_history": res_full9_1y,
        "core6_1m_full_history": res_core6_1m,
        "core6_1y_concurrent_only": res_core6_1y_concurrent,
        "core6_1m_concurrent_only": res_core6_1m_concurrent,
    },
    "factor_ic": FACTOR_IC,
    "cost_note": "ETF cost bps are a DRAFT proxy (not in COST_STANDARDS.md, which is equity-only) - "
                 "large-liquid ETFs 5-15bps roundtrip, factor/smallcap ETFs 25-30bps roundtrip (low AUM/wide spread assumption). Flag to CIO/CEO before any paper capital.",
}

with open(os.path.join(OUTDIR, "w4etf_results.json"), "w") as f:
    json.dump(OUT, f, indent=2, default=str)

print("COVERAGE:")
for k, v in COVERAGE.items():
    print(" ", k, v)
print("\nBACKTEST core6_1y:", json.dumps(res_core6_1y, indent=2, default=str))
print("\nBACKTEST full9_1y:", json.dumps(res_full9_1y, indent=2, default=str))
print("\nBACKTEST core6_1m:", json.dumps(res_core6_1m, indent=2, default=str))
print("\nBACKTEST core6_1y_CONCURRENT (since", concurrent_start, "):", json.dumps(res_core6_1y_concurrent, indent=2, default=str))
print("\nBACKTEST core6_1m_CONCURRENT (since", concurrent_start, "):", json.dumps(res_core6_1m_concurrent, indent=2, default=str))
