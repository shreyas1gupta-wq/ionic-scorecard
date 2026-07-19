"""
Portfolio analytics engine for STOCK_SCORECARD_750 holdings reviews (2026-07-18).
Computes, from on-disk verified data only (no fetches):
  - simulated portfolio (current weights, daily-rebalanced constant mix,
    renormalized over names trading each day) over 3y and 1y windows
  - benchmark = Nifty 50 total-return PROXY (price index + div_yield accrual)
  - CAGR, vol, Sharpe, Sortino, max drawdown, beta, Jensen alpha, tracking
    error, information ratio, up/down capture, correlation
  - 4-factor daily regression (MKT excess, SIZE = Midcap150-Nifty50,
    VALUE = NIFTY500 Value 50 - Nifty 500, MOM = Nifty200 Momentum 30 - Nifty 500)
  - top-15 holdings correlation matrix (full-3y names only)
  - forward stats from the analyst layer (weighted 3-5y growth) and a clearly
    labeled [ESTIMATE] forward-alpha band vs Nifty 50 trailing EPS growth
  - mid/small-cap valuation context (index PE percentile vs own 2016+ history)
Outputs (results dir): pf_analytics.json, pf_analytics_series.csv, pf_corr_matrix.csv
Assumptions are labeled in the JSON: RF = 6.5% p.a. [ASSUMPTION], dividend-accrual
TRI proxy, renormalized constant-mix simulation. Past simulation, not client returns.
Usage: python compute_portfolio_analytics.py
"""
import os, json
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
RESULTS = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\STOCK_SCORECARD_750\results")
PRICES = os.path.join(ROOT, r"ALPHA_RANKER\data\prices")
INDEX_PQ = os.path.join(ROOT, r"datasets\index_daily\nse_official_all_indices.parquet")
RF_ANNUAL = 0.065  # [ASSUMPTION] India 10Y G-sec neighbourhood; stated in outputs
TDAYS = 252


def load_holdings():
    mech = json.load(open(os.path.join(RESULTS, "pf_mech_flags.json"), encoding="utf-8"))
    h = pd.DataFrame(mech["holdings"])
    h["weight"] = h["weight"].astype(float)
    return h, mech


def load_price_matrix(symbols):
    cols = {}
    for s in symbols:
        fp = os.path.join(PRICES, f"{s}.parquet")
        if not os.path.exists(fp):
            continue
        px = pd.read_parquet(fp, columns=["Adj Close"])["Adj Close"]
        px.index = pd.to_datetime(px.index)
        cols[s] = px[~px.index.duplicated(keep="last")].sort_index()
    return pd.DataFrame(cols)


def load_indices():
    idx = pd.read_parquet(INDEX_PQ, columns=["index_name", "date", "close", "pe", "div_yield"])
    idx["date"] = pd.to_datetime(idx["date"])
    out = {}
    for name in ["Nifty 50", "Nifty 500", "Nifty Midcap 150", "Nifty Smallcap 250",
                 "NIFTY500 Value 50", "Nifty200 Momentum 30", "Nifty Microcap 250"]:
        sub = idx[idx["index_name"] == name].set_index("date").sort_index()
        if len(sub):
            out[name] = sub[["close", "pe", "div_yield"]]
    return out


def tri_proxy_returns(ind):
    """Price return + dividend-yield accrual = total-return proxy."""
    r = ind["close"].pct_change()
    dy = pd.to_numeric(ind["div_yield"], errors="coerce").ffill() / 100.0 / TDAYS
    return (r + dy).dropna()


def sim_portfolio(pxm, weights, start, end):
    """Constant-mix daily-rebalanced; weights renormalized over names trading that day."""
    px = pxm.loc[(pxm.index >= start) & (pxm.index <= end)]
    rets = px.pct_change()
    w = pd.Series(weights)
    have = rets.notna()
    wmat = have.mul(w, axis=1)
    wsum = wmat.sum(axis=1)
    port = (rets.fillna(0.0) * wmat).sum(axis=1) / wsum.replace(0, np.nan)
    return port.dropna()


def ann_metrics(r, bench=None, rf=RF_ANNUAL):
    r = r.dropna()
    n = len(r)
    if n < 60:
        return {}
    nav = (1 + r).cumprod()
    yrs = n / TDAYS
    cagr = nav.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(TDAYS)
    rf_d = rf / TDAYS
    ex = r - rf_d
    sharpe = ex.mean() / r.std() * np.sqrt(TDAYS) if r.std() > 0 else np.nan
    dn = r[r < 0]
    sortino = ex.mean() * TDAYS / (dn.std() * np.sqrt(TDAYS)) if len(dn) > 5 else np.nan
    dd = (nav / nav.cummax() - 1).min()
    out = {"cagr_pct": round(cagr * 100, 2), "vol_pct": round(vol * 100, 2),
           "sharpe": round(float(sharpe), 2), "sortino": round(float(sortino), 2),
           "max_dd_pct": round(dd * 100, 2), "n_days": n}
    if bench is not None:
        b = bench.reindex(r.index).dropna()
        r2 = r.reindex(b.index)
        cov = np.cov(r2, b)
        beta = cov[0, 1] / cov[1, 1]
        alpha_d = (r2 - rf_d).mean() - beta * (b - rf_d).mean()
        te = (r2 - b).std() * np.sqrt(TDAYS)
        ir = ((r2 - b).mean() * TDAYS) / te if te > 0 else np.nan
        up = b > 0
        upc = r2[up].mean() / b[up].mean() if up.sum() > 10 else np.nan
        dnm = b < 0
        dnc = r2[dnm].mean() / b[dnm].mean() if dnm.sum() > 10 else np.nan
        out.update({"beta": round(float(beta), 2),
                    "alpha_ann_pct": round(float(alpha_d * TDAYS * 100), 2),
                    "tracking_error_pct": round(float(te * 100), 2),
                    "info_ratio": round(float(ir), 2),
                    "up_capture": round(float(upc), 2), "down_capture": round(float(dnc), 2),
                    "corr_bench": round(float(np.corrcoef(r2, b)[0, 1]), 2)})
    return out


def factor_regression(port, indices):
    """Daily OLS: port excess ~ MKT excess + SIZE + VALUE + MOM. Plain OLS t-stats."""
    rf_d = RF_ANNUAL / TDAYS
    mkt = tri_proxy_returns(indices["Nifty 50"])
    n500 = indices["Nifty 500"]["close"].pct_change()
    fac = pd.DataFrame({
        "MKT": (mkt - rf_d),
        "SIZE": indices["Nifty Midcap 150"]["close"].pct_change() - indices["Nifty 50"]["close"].pct_change(),
        "VALUE": indices["NIFTY500 Value 50"]["close"].pct_change() - n500,
        "MOM": indices["Nifty200 Momentum 30"]["close"].pct_change() - n500,
    })
    df = fac.join((port - rf_d).rename("Y"), how="inner").dropna()
    if len(df) < 120:
        return {}
    X = np.column_stack([np.ones(len(df))] + [df[c].values for c in ["MKT", "SIZE", "VALUE", "MOM"]])
    y = df["Y"].values
    coef, res, _, _ = np.linalg.lstsq(X, y, rcond=None)
    yhat = X @ coef
    resid = y - yhat
    dof = len(df) - X.shape[1]
    s2 = (resid @ resid) / dof
    se = np.sqrt(np.diag(s2 * np.linalg.inv(X.T @ X)))
    tstats = coef / se
    r2 = 1 - (resid @ resid) / ((y - y.mean()) @ (y - y.mean()))
    names = ["alpha", "MKT", "SIZE", "VALUE", "MOM"]
    out = {"n_days": len(df), "r2": round(float(r2), 3),
           "alpha_ann_pct": round(float(coef[0] * TDAYS * 100), 2),
           "alpha_t": round(float(tstats[0]), 2)}
    for i, nm in enumerate(names[1:], 1):
        out[nm] = {"beta": round(float(coef[i]), 3), "t": round(float(tstats[i]), 2)}
    return out


def pe_context(indices):
    ctx = {}
    for name, key in [("Nifty 50", "nifty50"), ("Nifty Midcap 150", "midcap150"),
                      ("Nifty Smallcap 250", "smallcap250")]:
        pe = pd.to_numeric(indices[name]["pe"], errors="coerce").dropna()
        if len(pe) < 500:
            continue
        now = float(pe.iloc[-1])
        pct = float((pe < now).mean() * 100)
        ctx[key] = {"pe_now": round(now, 1), "pe_pctile_since2016": round(pct, 0),
                    "pe_median": round(float(pe.median()), 1)}
    return ctx


def main():
    h, mech = load_holdings()
    weights = dict(zip(h["symbol"], h["weight"]))
    pxm = load_price_matrix(list(weights))
    indices = load_indices()

    end = min(pxm.index.max(), indices["Nifty 50"].index.max())
    start3 = end - pd.DateOffset(years=3)
    start1 = end - pd.DateOffset(years=1)

    bench = tri_proxy_returns(indices["Nifty 50"])
    bench_px = indices["Nifty 50"]["close"].pct_change().dropna()

    port3 = sim_portfolio(pxm, weights, start3, end)
    port1 = port3[port3.index >= start1]
    b3 = bench[(bench.index >= start3) & (bench.index <= end)]
    b1 = b3[b3.index >= start1]

    # coverage disclosure: weight with full-3y history
    first_dates = pxm.apply(lambda c: c.first_valid_index())
    full3 = [s for s in weights if pd.notna(first_dates.get(s)) and first_dates[s] <= start3 + pd.Timedelta(days=7)]
    cov_w = sum(weights[s] for s in full3)

    res = {
        "as_of": str(end.date()), "window_3y_start": str(start3.date()),
        "assumptions": {
            "risk_free_annual_pct": RF_ANNUAL * 100,
            "benchmark": "Nifty 50 total-return proxy (price index + dividend-yield accrual)",
            "simulation": "current weights held as a daily-rebalanced constant mix; weights renormalized across names listed on each date; recent listings join when trading starts",
            "coverage_full_3y_weight_pct": round(cov_w, 2),
            "nature": "SIMULATED look-back of today's mix. Not the client's realized return; not a forecast.",
        },
        "portfolio_3y": ann_metrics(port3, b3),
        "bench_3y": ann_metrics(b3),
        "portfolio_1y": ann_metrics(port1, b1),
        "bench_1y": ann_metrics(b1),
        "factors_3y": factor_regression(port3, indices),
        "valuation_context": pe_context(indices),
    }

    # forward stats from the analyst layer (data-backed weighted aggregates)
    wsum = h["weight"].sum()
    wgrowth = float((h["growth"] * h["weight"]).sum() / wsum)
    hi = h[h["growth"] >= 15]["weight"].sum()
    lo = h[h["growth"] < 10]["weight"].sum()
    # Nifty 50 trailing EPS (close/pe) 3y CAGR — data-derived continuation proxy
    n50 = indices["Nifty 50"]
    eps = (n50["close"] / pd.to_numeric(n50["pe"], errors="coerce")).dropna()
    eps3 = eps[eps.index >= start3]
    eps_cagr = float((eps3.iloc[-1] / eps3.iloc[0]) ** (1 / 3) - 1) * 100 if len(eps3) > 500 else None
    res["forward_view"] = {
        "weighted_fwd_growth_pct": round(wgrowth, 1),
        "weight_growth_ge_15_pct": round(float(hi), 1),
        "weight_growth_lt_10_pct": round(float(lo), 1),
        "nifty50_trailing_eps_cagr_3y_pct": round(eps_cagr, 1) if eps_cagr is not None else None,
        "expected_alpha_note": ("[ESTIMATE, internal] growth-differential proxy: portfolio weighted forward growth "
                                f"{wgrowth:.1f}% vs Nifty 50 trailing 3y EPS CAGR "
                                f"{eps_cagr:.1f}%; if valuations are unchanged, the spread is the alpha engine. "
                                "Valuation drift and estimate error dominate a 3y horizon; treat as a band, not a point."
                                if eps_cagr is not None else "n/a"),
    }

    # series for charts (weekly NAV rebased 100 + drawdown)
    nav_p = (1 + port3).cumprod()
    nav_b = (1 + b3.reindex(port3.index).fillna(0)).cumprod()
    wk = pd.DataFrame({"pf_nav": nav_p, "bench_nav": nav_b}).resample("W-FRI").last().dropna()
    wk = wk / wk.iloc[0] * 100
    wk["pf_dd"] = (wk["pf_nav"] / wk["pf_nav"].cummax() - 1) * 100
    wk["bench_dd"] = (wk["bench_nav"] / wk["bench_nav"].cummax() - 1) * 100
    wk.round(2).to_csv(os.path.join(RESULTS, "pf_analytics_series.csv"), index_label="date")

    # top-15 correlation matrix (full-3y names only)
    top15 = [s for s in h.sort_values("weight", ascending=False)["symbol"] if s in full3][:15]
    rets3 = pxm[top15].loc[port3.index].pct_change()
    corr = rets3.corr().round(2)
    corr.to_csv(os.path.join(RESULTS, "pf_corr_matrix.csv"))
    res["corr_top15_mean_offdiag"] = round(float((corr.values[np.triu_indices(len(corr), 1)]).mean()), 2)

    with open(os.path.join(RESULTS, "pf_analytics.json"), "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1)
    print(json.dumps(res, indent=1)[:3000])
    print("saved pf_analytics.json, pf_analytics_series.csv, pf_corr_matrix.csv")


if __name__ == "__main__":
    main()
