"""Analyze the DTE-sweep + partial-hold + gated-subset + CE/PE-asymmetry cells.
Writes: cells.csv (the master table), plus supporting csvs (era splits, decomposition, placebo).
"""
import numpy as np
import pandas as pd

CKPT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
        r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731\checkpoints")
OUT = (r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
       r"\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTBUY_CONVEXITY_20260731")

LEG_COST_RT = 1.77
rng = np.random.default_rng(20260731)


def tstat(x):
    x = np.asarray(x, float)
    n = len(x)
    if n < 2 or x.std(ddof=1) == 0:
        return np.nan
    return float(x.mean() / (x.std(ddof=1) / np.sqrt(n)))


def concentration(pnl):
    pos = pnl[pnl > 0]
    if len(pos) == 0 or pos.sum() <= 0:
        return np.nan
    return float(pos.max() / pos.sum())


def max_dd(pnl_ordered_by_date, avg_capital):
    curve = np.cumsum(pnl_ordered_by_date)
    peak = np.maximum.accumulate(curve)
    dd = curve - peak
    dd_pts = float(dd.min()) if len(dd) else 0.0
    dd_pct = dd_pts / avg_capital * 100 if avg_capital else np.nan
    return dd_pts, dd_pct


def avg_rr(pnl):
    wins = pnl[pnl > 0]
    losses = pnl[pnl < 0]
    if len(wins) == 0 or len(losses) == 0:
        return np.nan
    return float(wins.mean() / abs(losses.mean()))


def era_table(df, pnlcol="net_pnl"):
    rows = []
    for era, g in df.groupby("era"):
        rows.append(dict(era=era, n=len(g), mean=g[pnlcol].mean(), win_rate=(g[pnlcol] > 0).mean()))
    ho = df[df["heldout_2026"]]
    rows.append(dict(era="HELDOUT_2026", n=len(ho), mean=ho[pnlcol].mean() if len(ho) else np.nan,
                      win_rate=(ho[pnlcol] > 0).mean() if len(ho) else np.nan))
    return pd.DataFrame(rows)


def random_subset_placebo(full_pnl, k, observed_mean, draws=500):
    if k == 0 or k > len(full_pnl):
        return np.nan, np.nan
    vals = full_pnl.to_numpy(float)
    means = np.array([rng.choice(vals, size=k, replace=False).mean() for _ in range(draws)])
    pctile = float((means < observed_mean).mean())
    p_two_sided = float((np.abs(means - vals.mean()) >= abs(observed_mean - vals.mean())).mean())
    return pctile, p_two_sided


def summarize(df, label, pnlcol="net_pnl", capital_col="entry_premium"):
    n = len(df)
    if n == 0:
        return dict(label=label, n=0)
    pnl = df[pnlcol].to_numpy(float)
    span_days = (df["entry_date"].max() - df["entry_date"].min()).days
    span_months = max(span_days / 30.44, 1e-9)
    dd_pts, dd_pct = max_dd(pnl[np.argsort(df["entry_date"].to_numpy())], df[capital_col].mean())
    return dict(
        label=label, n=n, trades_per_month=n / span_months,
        mean_net_pnl=float(pnl.mean()), median_net_pnl=float(np.median(pnl)),
        win_rate=float((pnl > 0).mean()), avg_rr=avg_rr(pnl), t_stat=tstat(pnl),
        concentration_top1_frac=concentration(pnl),
        maxDD_pts=dd_pts, maxDD_pct_of_avg_capital=dd_pct,
        mean_premium_pts=float(df[capital_col].mean()),
        mean_dte_actual=float(df["dte_actual"].mean()) if "dte_actual" in df else np.nan,
    )


def theta_gamma_decomp(df):
    entry_extr = df["entry_premium"] - df["entry_intrinsic"]
    exit_extr = df["exit_value"] - df["exit_intrinsic"]
    theta_paid = entry_extr - exit_extr
    gamma_captured = df["exit_intrinsic"] - df["entry_intrinsic"]
    check = (gamma_captured - theta_paid) - df["gross_pnl"]
    return dict(
        mean_theta_paid=float(theta_paid.mean()),
        mean_gamma_captured=float(gamma_captured.mean()),
        mean_gross_pnl=float(df["gross_pnl"].mean()),
        decomposition_residual_check=float(check.abs().max()),
        pct_cycles_gamma_gt_theta=float((gamma_captured > theta_paid).mean()),
    )


cells = []
era_rows = []
decomp_rows = []
placebo_rows = []

dte_arms = {}
for dte in (15, 30, 45, 60, 90):
    df = pd.read_csv(f"{CKPT}\\trades_dte{dte}_expiry.csv", parse_dates=["entry_date", "expiry", "exit_date"])
    dte_arms[dte] = df
    s = summarize(df, f"straddle_DTE{dte}_hold=expiry")
    s.update(structure="straddle", dte_target=dte, hold="expiry", gate="unconditional")
    cells.append(s)
    et = era_table(df)
    et["arm"] = f"DTE{dte}_expiry"
    era_rows.append(et)
    dec = theta_gamma_decomp(df)
    dec["arm"] = f"DTE{dte}_expiry"
    decomp_rows.append(dec)

df_partial = pd.read_csv(f"{CKPT}\\trades_dte45_partial50.csv", parse_dates=["entry_date", "expiry", "exit_date"])
s = summarize(df_partial, "straddle_DTE45_hold=partial50pct")
s.update(structure="straddle", dte_target=45, hold="partial50pct", gate="unconditional")
cells.append(s)
et = era_table(df_partial)
et["arm"] = "DTE45_partial50"
era_rows.append(et)
dec = theta_gamma_decomp(df_partial)
dec["arm"] = "DTE45_partial50"
decomp_rows.append(dec)

# ---- vol-level gates (post-hoc subset of the unconditional trade list; NOT a new roll schedule) ----
GATE_DTE = 60   # the best-performing unconditional DTE arm; pre-registered as "the best/representative DTE"
base = dte_arms[GATE_DTE].dropna(subset=["vix_pct_trail"]).copy()
overall_mean = base["net_pnl"].mean()

for gname, mask in [
    ("vix_low_le25pct", base["vix_pct_trail"] <= 0.25),
    ("vix_high_ge75pct", base["vix_pct_trail"] >= 0.75),
    ("rv20_low_le25pct", base["rv20_pct_trail"] <= 0.25),
]:
    sub = base[mask]
    s = summarize(sub, f"straddle_DTE{GATE_DTE}_gate={gname}")
    s.update(structure="straddle", dte_target=GATE_DTE, hold="expiry", gate=gname)
    if len(sub) > 0:
        pctile, p2 = random_subset_placebo(base["net_pnl"], len(sub), sub["net_pnl"].mean())
        s["placebo_percentile_rank"] = pctile
        s["placebo_p_two_sided"] = p2
    cells.append(s)
    placebo_rows.append(dict(gate=gname, dte=GATE_DTE, n=len(sub),
                              observed_mean=sub["net_pnl"].mean() if len(sub) else np.nan,
                              baseline_mean=overall_mean,
                              placebo_pctile=s.get("placebo_percentile_rank"),
                              placebo_p=s.get("placebo_p_two_sided")))

# ---- CE-only / PE-only asymmetry, same DTE/entries as the gate arm ----
base_full = dte_arms[GATE_DTE]
ce_pnl = base_full["ce_exit"] - base_full["ce_entry"] - LEG_COST_RT
pe_pnl = base_full["pe_exit"] - base_full["pe_entry"] - LEG_COST_RT
for legname, pnl in [("CE_only", ce_pnl), ("PE_only", pe_pnl)]:
    tmp = base_full.copy()
    tmp["net_pnl"] = pnl
    tmp["entry_premium"] = tmp["ce_entry"] if legname == "CE_only" else tmp["pe_entry"]
    s = summarize(tmp, f"{legname}_DTE{GATE_DTE}_hold=expiry")
    s.update(structure=legname, dte_target=GATE_DTE, hold="expiry", gate="unconditional")
    cells.append(s)

cells_df = pd.DataFrame(cells)
cells_df.to_csv(f"{OUT}\\cells.csv", index=False)
pd.concat(era_rows, ignore_index=True).to_csv(f"{OUT}\\era_splits.csv", index=False)
pd.DataFrame(decomp_rows).to_csv(f"{OUT}\\theta_gamma_decomposition.csv", index=False)
pd.DataFrame(placebo_rows).to_csv(f"{OUT}\\gate_placebo_results.csv", index=False)

print(cells_df[["label", "n", "trades_per_month", "mean_net_pnl", "win_rate", "avg_rr", "t_stat",
                "concentration_top1_frac", "maxDD_pct_of_avg_capital"]].to_string())
print("\n--- era splits ---")
print(pd.concat(era_rows, ignore_index=True).to_string())
print("\n--- theta/gamma decomposition ---")
print(pd.DataFrame(decomp_rows).to_string())
print("\n--- gate placebo ---")
print(pd.DataFrame(placebo_rows).to_string())
print("DONE")
