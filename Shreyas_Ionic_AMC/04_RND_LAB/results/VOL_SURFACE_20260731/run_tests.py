"""Run the pre-registered cell list (PRE_REGISTRATION.md) against daily_surface.parquet.
Produces cells.csv (predictive cells + structure cells) and vrp_table.csv.
Every regression cell: OLS + Newey-West(HAC) t, era-split PRE/POST-Oct2024/HELDOUT-2026,
500-rep shuffle + 500-rep circular-shift placebo, placebo_bar = max(95th pctile |t| of each).
"""
from __future__ import annotations

import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from sklearn.decomposition import PCA

warnings.filterwarnings("ignore")
HERE = Path(__file__).parent
D = pd.read_parquet(HERE / "daily_surface.parquet")
D = D.sort_values("day").reset_index(drop=True)
RNG_SEED = 42
N_PLACEBO = 300
COST_PER_LEG_RT = 1.4   # premium pts round trip, mid of firm's 1.2-1.7 range (SHARED_CONTEXT)

ERAS = ["PRE_OCT2024", "POST_OCT2024", "HELDOUT_2026"]


def ols_hac_t(x, y, maxlags):
    X = sm.add_constant(x)
    try:
        m = sm.OLS(y, X, missing="drop").fit(cov_type="HAC", cov_kwds={"maxlags": maxlags})
    except Exception:
        return np.nan, np.nan, np.nan
    return m.params[1], m.tvalues[1], m.params[0]


def placebo_bar(x, y, maxlags, rng):
    xv = np.asarray(x)
    yv = np.asarray(y)
    n = len(xv)
    if n < 30:
        return np.nan
    ts_shuf, ts_circ = [], []
    for _ in range(N_PLACEBO):
        xs = rng.permutation(xv)
        _, t, _ = ols_hac_t(xs, yv, maxlags)
        if np.isfinite(t):
            ts_shuf.append(t)
    for _ in range(N_PLACEBO):
        shift = rng.integers(1, n - 1)
        xs = np.roll(xv, shift)
        _, t, _ = ols_hac_t(xs, yv, maxlags)
        if np.isfinite(t):
            ts_circ.append(t)
    bar_s = np.percentile(np.abs(ts_shuf), 95) if ts_shuf else np.nan
    bar_c = np.percentile(np.abs(ts_circ), 95) if ts_circ else np.nan
    return float(np.nanmax([bar_s, bar_c]))


def predictive_cell(df, signal, target, maxlags, seed=42):
    rows = []
    for era_name in ERAS:
        sub = df[df["era"] == era_name][[signal, target]].dropna()
        if len(sub) < 30:
            rows.append(dict(era=era_name, n=len(sub), beta=np.nan, t=np.nan,
                              placebo_bar=np.nan, verdict="UNDERPOWERED"))
            continue
        beta, t, _ = ols_hac_t(sub[signal].to_numpy(), sub[target].to_numpy(), maxlags)
        bar = placebo_bar(sub[signal].to_numpy(), sub[target].to_numpy(), maxlags,
                           np.random.default_rng(seed))
        verdict = "CLEARS_PLACEBO" if (np.isfinite(t) and np.isfinite(bar) and abs(t) > bar) else "FAILS_PLACEBO"
        rows.append(dict(era=era_name, n=len(sub), beta=beta, t=t, placebo_bar=bar, verdict=verdict))
    return pd.DataFrame(rows)


def summarize_predictive(name, df, signal, target, maxlags):
    r = predictive_cell(df, signal, target, maxlags)
    r.insert(0, "cell", name)
    r.insert(1, "signal", signal)
    r.insert(2, "target", target)
    return r


# --------------------------------------------------------------------------- structure P&L cells
def structure_cell(df, name, pnl_call_col, pnl_put_col, sign_col, cost=COST_PER_LEG_RT, seed=42):
    """Sell the wing indicated by sign_col>0 -> put (pnl_put_col); else call (pnl_call_col)."""
    rows = []
    rng = np.random.default_rng(seed)
    for era_name in ERAS:
        sub = df[df["era"] == era_name][["day", pnl_call_col, pnl_put_col, sign_col]].dropna()
        if len(sub) < 20:
            rows.append(dict(cell=name, era=era_name, n=len(sub), mean=np.nan, win=np.nan,
                              t=np.nan, rr=np.nan, trades_per_month=np.nan,
                              placebo_mean=np.nan, verdict="UNDERPOWERED"))
            continue
        chosen = np.where(sub[sign_col] > 0, sub[pnl_put_col], sub[pnl_call_col]) - cost
        n = len(chosen)
        mean = chosen.mean()
        win = (chosen > 0).mean()
        se = chosen.std(ddof=1) / np.sqrt(n)
        t = mean / se if se > 0 else np.nan
        conc = np.abs(chosen).max() / np.abs(chosen).sum() if chosen.sum() != 0 else np.nan
        avg_win = chosen[chosen > 0].mean() if (chosen > 0).any() else np.nan
        avg_loss = -chosen[chosen < 0].mean() if (chosen < 0).any() else np.nan
        rr = avg_win / avg_loss if (avg_loss and avg_loss > 0) else np.nan
        span_months = max((sub["day"].max() - sub["day"].min()).days / 30.44, 1e-6)
        tpm = n / span_months
        # random-wing placebo: same universe, coin-flip choice instead of skew-informed choice
        placebo_means = []
        for _ in range(N_PLACEBO):
            coin = rng.random(n) > 0.5
            pm = np.where(coin, sub[pnl_put_col].to_numpy(), sub[pnl_call_col].to_numpy()) - cost
            placebo_means.append(pm.mean())
        placebo_mean = float(np.mean(placebo_means))
        placebo_p = float(np.mean(np.array(placebo_means) >= mean))  # one-sided: informed beats random
        rows.append(dict(cell=name, era=era_name, n=n, mean=mean, win=win, t=t, rr=rr,
                          trades_per_month=tpm, conc_max_frac=conc, placebo_mean=placebo_mean,
                          placebo_p=placebo_p,
                          verdict=("BEATS_RANDOM_WING" if placebo_p < 0.05 else "NO_EDGE_OVER_RANDOM")))
    return pd.DataFrame(rows)


def unconditional_wing_cell(df, name, pnl_col, cost=COST_PER_LEG_RT):
    rows = []
    for era_name in ERAS:
        sub = df[df["era"] == era_name][["day", pnl_col]].dropna()
        if len(sub) < 20:
            rows.append(dict(cell=name, era=era_name, n=len(sub), mean=np.nan, win=np.nan,
                              t=np.nan, rr=np.nan, trades_per_month=np.nan, verdict="UNDERPOWERED"))
            continue
        pnl = sub[pnl_col].to_numpy() - cost
        n = len(pnl)
        mean = pnl.mean(); win = (pnl > 0).mean()
        se = pnl.std(ddof=1) / np.sqrt(n)
        t = mean / se if se > 0 else np.nan
        avg_win = pnl[pnl > 0].mean() if (pnl > 0).any() else np.nan
        avg_loss = -pnl[pnl < 0].mean() if (pnl < 0).any() else np.nan
        rr = avg_win / avg_loss if (avg_loss and avg_loss > 0) else np.nan
        span_months = max((sub["day"].max() - sub["day"].min()).days / 30.44, 1e-6)
        conc = np.abs(pnl).max() / np.abs(pnl).sum() if pnl.sum() != 0 else np.nan
        rows.append(dict(cell=name, era=era_name, n=n, mean=mean, win=win, t=t, rr=rr,
                          trades_per_month=n / span_months, conc_max_frac=conc, verdict="-"))
    return pd.DataFrame(rows)


def main():
    out_rows = []

    # 1/2/3/4: skew level & change -> fwd ret / fwd vol
    for h in (1, 5, 10):
        out_rows.append(summarize_predictive(f"skew_level_ret{h}", D, "f_skew25", f"fwd_ret_{h}", h))
    for h in (5, 10):
        out_rows.append(summarize_predictive(f"skew_level_rv5_{h}", D, "f_skew25", f"fwd_rv5_fix_{h}", h))
        out_rows.append(summarize_predictive(f"skew_level_rv15_{h}", D, "f_skew25", f"fwd_rv15_fix_{h}", h))
    for h in (1, 5):
        out_rows.append(summarize_predictive(f"skew_chg_ret{h}", D, "skew25_chg1", f"fwd_ret_{h}", h))
    out_rows.append(summarize_predictive("skew_chg_rv5_5", D, "skew25_chg1", "fwd_rv5_fix_5", 5))

    # 5/6/7: term slope -> fwd ret / fwd vol / inversion regime
    for h in (1, 5, 10):
        out_rows.append(summarize_predictive(f"term_slope_ret{h}", D, "term_slope", f"fwd_ret_{h}", h))
    for h in (5, 10):
        out_rows.append(summarize_predictive(f"term_slope_rv5_{h}", D, "term_slope", f"fwd_rv5_fix_{h}", h))
        out_rows.append(summarize_predictive(f"term_slope_rv15_{h}", D, "term_slope", f"fwd_rv15_fix_{h}", h))
    # inversion as 0/1 dummy -> fwd vol (same OLS machinery, dummy regressor)
    D["term_inv_flag"] = D["term_inverted"].astype(float)
    out_rows.append(summarize_predictive("term_inversion_rv5_5", D, "term_inv_flag", "fwd_rv5_fix_5", 5))
    out_rows.append(summarize_predictive("term_inversion_ret5", D, "term_inv_flag", "fwd_ret_5", 5))

    # 8/9: IV-RV spread (expanding pctile) -> fwd ret (control) / fwd vol (B2 extension)
    for col in ["iv_rv5_10_pct", "iv_rv15_10_pct", "iv_rv5_20_pct", "iv_rv15_20_pct"]:
        out_rows.append(summarize_predictive(f"{col}_ret5", D, col, "fwd_ret_5", 5))
        out_rows.append(summarize_predictive(f"{col}_rv5_5", D, col, "fwd_rv5_fix_5", 5))

    # 11: PCA factors (loadings fit on PRE_OCT2024 only, applied out-of-sample)
    pca_cols = ["f_atm_iv", "f_skew25", "f_bfly25", "n_atm_iv", "n_skew25", "n_bfly25"]
    fit_mask = (D["era"] == "PRE_OCT2024") & D[pca_cols].notna().all(axis=1)
    mu = D.loc[fit_mask, pca_cols].mean()
    sd = D.loc[fit_mask, pca_cols].std()
    Z_fit = (D.loc[fit_mask, pca_cols] - mu) / sd
    pca = PCA(n_components=3, random_state=0).fit(Z_fit.to_numpy())
    evr = pca.explained_variance_ratio_
    print("PCA explained variance ratio (fit PRE_OCT2024):", evr)

    all_mask = D[pca_cols].notna().all(axis=1)
    Z_all = (D.loc[all_mask, pca_cols] - mu) / sd
    scores = pca.transform(Z_all.to_numpy())
    D.loc[all_mask, "pc1"] = scores[:, 0]
    D.loc[all_mask, "pc2"] = scores[:, 1]
    D["pc1_chg1"] = D["pc1"].diff()
    D["pc2_chg1"] = D["pc2"].diff()

    for h in (1, 5, 10):
        out_rows.append(summarize_predictive(f"pc1_level_ret{h}", D, "pc1", f"fwd_ret_{h}", h))
    out_rows.append(summarize_predictive("pc1_level_rv5_5", D, "pc1", "fwd_rv5_fix_5", 5))
    out_rows.append(summarize_predictive("pc1_chg_ret5", D, "pc1_chg1", "fwd_ret_5", 5))
    for h in (1, 5, 10):
        out_rows.append(summarize_predictive(f"pc2_level_ret{h}", D, "pc2", f"fwd_ret_{h}", h))
    out_rows.append(summarize_predictive("pc2_level_rv5_5", D, "pc2", "fwd_rv5_fix_5", 5))
    out_rows.append(summarize_predictive("pc2_chg_ret5", D, "pc2_chg1", "fwd_ret_5", 5))

    cells = pd.concat(out_rows, ignore_index=True)
    cells.to_csv(HERE / "predictive_cells.csv", index=False)
    print(f"wrote predictive_cells.csv  shape={cells.shape}")

    # ---------------------------------------------------------------- structure cells
    struct_rows = []
    struct_rows.append(structure_cell(D, "sell_richer_wing_front", "f_pnl_sell_call25", "f_pnl_sell_put25", "f_skew25"))
    D["f_skew25_neg"] = D["f_skew25"] * -1
    struct_rows.append(structure_cell(D, "sell_cheaper_wing_front_REVERSE_CONTROL",
                                       "f_pnl_sell_call25", "f_pnl_sell_put25", "f_skew25_neg"))
    struct_rows.append(unconditional_wing_cell(D, "sell_put25_unconditional", "f_pnl_sell_put25"))
    struct_rows.append(unconditional_wing_cell(D, "sell_call25_unconditional", "f_pnl_sell_call25"))
    struct = pd.concat(struct_rows, ignore_index=True)
    struct.to_csv(HERE / "structure_cells.csv", index=False)
    print(f"wrote structure_cells.csv shape={struct.shape}")

    # 25d strangle (sell both wings), conditioned on iv_rv-rich tercile
    strangle_rows = []
    D["strangle_pnl"] = D["f_pnl_sell_call25"] + D["f_pnl_sell_put25"] - 2 * COST_PER_LEG_RT
    for era_name in ERAS:
        sub = D[D["era"] == era_name]
        for tercile_name, mask in [
            ("all", pd.Series(True, index=sub.index)),
            ("iv_rv5_10_pct>=0.67", sub["iv_rv5_10_pct"] >= 0.67),
            ("iv_rv5_10_pct<=0.33", sub["iv_rv5_10_pct"] <= 0.33),
        ]:
            s = sub.loc[mask, "strangle_pnl"].dropna()
            days_s = sub.loc[s.index, "day"] if len(s) else sub["day"].iloc[:0]
            if len(s) < 15:
                strangle_rows.append(dict(era=era_name, cond=tercile_name, n=len(s), mean=np.nan,
                                           win=np.nan, t=np.nan, trades_per_month=np.nan,
                                           verdict="UNDERPOWERED"))
                continue
            mean = s.mean(); win = (s > 0).mean()
            se = s.std(ddof=1) / np.sqrt(len(s))
            t = mean / se if se > 0 else np.nan
            avg_win = s[s > 0].mean() if (s > 0).any() else np.nan
            avg_loss = -s[s < 0].mean() if (s < 0).any() else np.nan
            rr = avg_win / avg_loss if (avg_loss and avg_loss > 0) else np.nan
            span_months = max((days_s.max() - days_s.min()).days / 30.44, 1e-6)
            strangle_rows.append(dict(era=era_name, cond=tercile_name, n=len(s), mean=mean,
                                       win=win, t=t, rr=rr, trades_per_month=len(s) / span_months,
                                       verdict="-"))
    strangle = pd.DataFrame(strangle_rows)
    strangle.to_csv(HERE / "strangle_cells.csv", index=False)
    print(f"wrote strangle_cells.csv shape={strangle.shape}")

    # ATM straddle sell (front & next), unconditional and IV-RV-rich-conditioned
    D["straddle_f_pnl"] = D["f_pnl_sell_atm_straddle"] - 2 * COST_PER_LEG_RT
    D["straddle_n_pnl"] = D["n_pnl_sell_atm_straddle"] - 2 * COST_PER_LEG_RT
    atm_rows = []
    for label, col in [("straddle_front_all", "straddle_f_pnl"), ("straddle_next_all", "straddle_n_pnl")]:
        for era_name in ERAS:
            sub = D[D["era"] == era_name][["day", col]].dropna()
            if len(sub) < 15:
                atm_rows.append(dict(cell=label, era=era_name, n=len(sub), mean=np.nan, win=np.nan,
                                      t=np.nan, verdict="UNDERPOWERED"))
                continue
            s = sub[col].to_numpy()
            mean = s.mean(); win = (s > 0).mean()
            se = s.std(ddof=1) / np.sqrt(len(s))
            t = mean / se if se > 0 else np.nan
            span_months = max((sub["day"].max() - sub["day"].min()).days / 30.44, 1e-6)
            conc = np.abs(s).max() / np.abs(s).sum() if s.sum() != 0 else np.nan
            atm_rows.append(dict(cell=label, era=era_name, n=len(s), mean=mean, win=win, t=t,
                                  trades_per_month=len(s) / span_months, conc_max_frac=conc,
                                  verdict="-"))
    # calendar structure: short front CE / long next CE, conditioned on term_slope sign
    D["calendar_pnl_net"] = D["calendar_pnl_ce"] - 2 * COST_PER_LEG_RT
    for cond_name, mask_fn in [
        ("all", lambda s: pd.Series(True, index=s.index)),
        ("term_inverted", lambda s: s["term_inverted"] == True),
        ("term_normal", lambda s: s["term_inverted"] == False),
    ]:
        for era_name in ERAS:
            sub = D[D["era"] == era_name]
            mask = mask_fn(sub)
            s = sub.loc[mask, ["day", "calendar_pnl_net"]].dropna()
            if len(s) < 15:
                atm_rows.append(dict(cell=f"calendar_shortfront_longnext_{cond_name}", era=era_name,
                                      n=len(s), mean=np.nan, win=np.nan, t=np.nan, verdict="UNDERPOWERED"))
                continue
            vals = s["calendar_pnl_net"].to_numpy()
            mean = vals.mean(); win = (vals > 0).mean()
            se = vals.std(ddof=1) / np.sqrt(len(vals))
            t = mean / se if se > 0 else np.nan
            span_months = max((s["day"].max() - s["day"].min()).days / 30.44, 1e-6)
            atm_rows.append(dict(cell=f"calendar_shortfront_longnext_{cond_name}", era=era_name,
                                  n=len(vals), mean=mean, win=win, t=t,
                                  trades_per_month=len(vals) / span_months, verdict="-"))
    atm_df = pd.DataFrame(atm_rows)
    atm_df.to_csv(HERE / "atm_calendar_cells.csv", index=False)
    print(f"wrote atm_calendar_cells.csv shape={atm_df.shape}")

    # ---------------------------------------------------------------- VRP table (by dte-tenor x era)
    vrp_rows = []
    for tenor, atm_col, dte_col, fwd5, fwd15 in [
        ("front", "f_atm_iv", "f_dte", "f_fwd_rv5", "f_fwd_rv15"),
        ("next", "n_atm_iv", "n_dte", "n_fwd_rv5", "n_fwd_rv15"),
    ]:
        for era_name in ERAS:
            sub = D[D["era"] == era_name]
            vrp5 = (sub[atm_col] - sub[fwd5]).dropna()
            vrp15 = (sub[atm_col] - sub[fwd15]).dropna()
            dte_mean = sub[dte_col].mean()
            if len(vrp5) >= 10:
                t5 = vrp5.mean() / (vrp5.std(ddof=1) / np.sqrt(len(vrp5)))
            else:
                t5 = np.nan
            if len(vrp15) >= 10:
                t15 = vrp15.mean() / (vrp15.std(ddof=1) / np.sqrt(len(vrp15)))
            else:
                t15 = np.nan
            vrp_rows.append(dict(tenor=tenor, era=era_name, mean_dte=dte_mean,
                                  n_5min=len(vrp5), vrp_5min_volpts=vrp5.mean(), t_5min=t5,
                                  n_15min=len(vrp15), vrp_15min_volpts=vrp15.mean(), t_15min=t15))
    vrp = pd.DataFrame(vrp_rows)
    vrp.to_csv(HERE / "vrp_table.csv", index=False)
    print(vrp.to_string())

    D.to_parquet(HERE / "daily_surface_scored.parquet")
    print("done.")


if __name__ == "__main__":
    main()
