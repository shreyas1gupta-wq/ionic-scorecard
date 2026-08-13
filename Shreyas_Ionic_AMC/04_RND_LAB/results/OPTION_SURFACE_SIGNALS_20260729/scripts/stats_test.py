"""
Predictive-content tests for the option-surface panel. See PREREGISTRATION.md.
Build window: <=2025-12-31. Held-out: >=2026-01-01 (reported only, never used to pick anything).

Outputs: results_table.csv (every cell run), results_table.md (formatted), stats_log.txt
"""
import datetime as dt
import numpy as np
import pandas as pd
import statsmodels.api as sm

OUT_ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\OPTION_SURFACE_SIGNALS_20260729"
from pathlib import Path
OUT = Path(OUT_ROOT)
LOG = open(OUT / "stats_log.txt", "w", encoding="utf-8")


def log(msg):
    print(msg)
    LOG.write(str(msg) + "\n")
    LOG.flush()


BUILD_END = dt.date(2025, 12, 31)
HORIZONS = [1, 3, 5]
N_PLACEBO = 200
RNG = np.random.default_rng(20260729)  # fixed seed, filed in pre-registration spirit: reproducible


def to_date(x):
    if isinstance(x, dt.date) and not isinstance(x, dt.datetime):
        return x
    return pd.Timestamp(x).date()


# ---------------- load ----------------
panel = pd.read_parquet(OUT / "panel_raw.parquet")
panel["day"] = panel["day"].map(to_date)
panel = panel.sort_values("day").drop_duplicates("day").reset_index(drop=True)

n_close = pd.read_parquet(OUT / "nifty_daily_close.parquet")["nifty_close"]
n_close.index = [to_date(x) for x in n_close.index]
n_close = n_close.sort_index()
b_close = pd.read_parquet(OUT / "bn_daily_close.parquet")["bn_close"]
b_close.index = [to_date(x) for x in b_close.index]
b_close = b_close.sort_index()

n_dates = n_close.index.to_numpy()
n_vals = n_close.values.astype(float)
n_pos = {d: i for i, d in enumerate(n_dates)}

b_dates = b_close.index.to_numpy()
b_vals = b_close.values.astype(float)
b_pos = {d: i for i, d in enumerate(b_dates)}

log(f"panel rows {len(panel)}  nifty_close days {len(n_close)}  bn_close days {len(b_close)}")


def fwd_logret(pos_map, vals, day, h):
    p = pos_map.get(day)
    if p is None or p + h >= len(vals):
        return np.nan
    return float(np.log(vals[p + h] / vals[p]))


def fwd_rv(pos_map, vals, day, h):
    p = pos_map.get(day)
    if p is None or p + h >= len(vals):
        return np.nan
    seg = vals[p:p + h + 1]
    if (seg <= 0).any():
        return np.nan
    r = np.diff(np.log(seg))
    return float(np.sqrt(252.0 / h * np.sum(r ** 2)))


def trailing_corr20(day):
    p = n_pos.get(day)
    q = b_pos.get(day)
    if p is None or q is None or p < 21 or q < 21:
        return np.nan
    rn = np.diff(np.log(n_vals[p - 20:p + 1]))
    rb = np.diff(np.log(b_vals[q - 20:q + 1]))
    if len(rn) != len(rb):
        return np.nan
    if np.std(rn) == 0 or np.std(rb) == 0:
        return np.nan
    return float(np.corrcoef(rn, rb)[0, 1])


def fwd_corr5(day):
    p = n_pos.get(day)
    q = b_pos.get(day)
    if p is None or q is None or p + 5 >= len(n_vals) or q + 5 >= len(b_vals):
        return np.nan
    rn = np.diff(np.log(n_vals[p:p + 6]))
    rb = np.diff(np.log(b_vals[q:q + 6]))
    if np.std(rn) == 0 or np.std(rb) == 0:
        return np.nan
    return float(np.corrcoef(rn, rb)[0, 1])


# ---------------- build targets ----------------
rows = []
for _, r in panel.iterrows():
    day = r["day"]
    rec = {"day": day}
    for h in HORIZONS:
        rec[f"T_ret_{h}"] = fwd_logret(n_pos, n_vals, day, h)
        rec[f"T_rvgap_{h}"] = fwd_rv(n_pos, n_vals, day, h) - r["atm1_iv"] if not np.isnan(r["atm1_iv"]) else np.nan
        rec[f"REL_{h}"] = fwd_logret(b_pos, b_vals, day, h) - rec[f"T_ret_{h}"] if not np.isnan(fwd_logret(b_pos, b_vals, day, h)) and not np.isnan(rec[f"T_ret_{h}"]) else np.nan
    rec["CORRGAP_5"] = fwd_corr5(day) - trailing_corr20(day) if not np.isnan(fwd_corr5(day)) and not np.isnan(trailing_corr20(day)) else np.nan
    rows.append(rec)
targets = pd.DataFrame(rows)

df = panel.merge(targets, on="day", how="left")
df["is_build"] = df["day"] <= BUILD_END
log(f"merged df {df.shape}; build rows {df['is_build'].sum()}, heldout rows {(~df['is_build']).sum()}")


# ---------------- regression + placebo machinery ----------------
def hac_t(y, x, h):
    d = pd.DataFrame({"y": y, "x": x}).dropna()
    n = len(d)
    if n < 30:
        return np.nan, n
    xs = (d["x"] - d["x"].mean()) / d["x"].std(ddof=0)
    X = sm.add_constant(xs)
    try:
        fit = sm.OLS(d["y"], X).fit(cov_type="HAC", cov_kwds={"maxlags": max(h, 1)})
        return float(fit.tvalues["x"]), n
    except Exception:
        return np.nan, n


def placebo_dist(y, x, h, n_draws=N_PLACEBO):
    d = pd.DataFrame({"y": y, "x": x}).dropna()
    if len(d) < 30:
        return np.array([])
    yv, xv = d["y"].values, d["x"].values
    ts = []
    for i in range(n_draws):
        if i % 2 == 0:
            xp = RNG.permutation(xv)
        else:
            shift = RNG.integers(20, 61)
            xp = np.roll(xv, shift)
        t, _ = hac_t(yv, xp, h)
        if not np.isnan(t):
            ts.append(abs(t))
    return np.array(ts)


def run_cell(candidate, feature, target, h, build_df, heldout_df):
    y_b, x_b = build_df[target], build_df[feature]
    t_build, n_build = hac_t(y_b.values, x_b.values, h)
    placebo = placebo_dist(y_b.values, x_b.values, h)
    p95 = float(np.percentile(placebo, 95)) if len(placebo) > 20 else np.nan
    beats_placebo = (not np.isnan(t_build)) and (not np.isnan(p95)) and (abs(t_build) > p95)
    y_h, x_h = heldout_df[target], heldout_df[feature]
    t_held, n_held = hac_t(y_h.values, x_h.values, h)
    verdict = "KILL"
    if not np.isnan(t_build) and abs(t_build) >= 2 and beats_placebo:
        verdict = "SURVIVES (pending cross-horizon check)"
    return dict(
        candidate=candidate, feature=feature, target=target, h=h,
        n_build=n_build, t_build=round(t_build, 2) if not np.isnan(t_build) else np.nan,
        placebo_p95=round(p95, 2) if not np.isnan(p95) else np.nan,
        beats_placebo=beats_placebo,
        n_held=n_held, t_held=round(t_held, 2) if not np.isnan(t_held) else np.nan,
        verdict=verdict,
    )


build_df = df[df["is_build"]].copy()
heldout_df = df[~df["is_build"]].copy()

cells = []
# Candidate 1: skew
for h in HORIZONS:
    cells.append(run_cell("C1_skew", "skew", f"T_ret_{h}", h, build_df, heldout_df))
    cells.append(run_cell("C1_skew", "skew", f"T_rvgap_{h}", h, build_df, heldout_df))
# Candidate 2: term structure (2 features)
for feat in ["ts_near", "ts_far"]:
    for h in HORIZONS:
        cells.append(run_cell("C2_termstructure", feat, f"T_ret_{h}", h, build_df, heldout_df))
        cells.append(run_cell("C2_termstructure", feat, f"T_rvgap_{h}", h, build_df, heldout_df))
# Candidate 3: PCR
for h in HORIZONS:
    cells.append(run_cell("C3_PCR", "pcr", f"T_ret_{h}", h, build_df, heldout_df))
    cells.append(run_cell("C3_PCR", "pcr", f"T_rvgap_{h}", h, build_df, heldout_df))
# Candidate 4: NIFTY-BANKNIFTY IV spread
for h in HORIZONS:
    cells.append(run_cell("C4_ivspread", "ivspread", f"REL_{h}", h, build_df, heldout_df))
cells.append(run_cell("C4_ivspread", "ivspread", "CORRGAP_5", 5, build_df, heldout_df))

res = pd.DataFrame(cells)
res.to_csv(OUT / "results_table.csv", index=False)
log(f"\nTOTAL CELLS RUN: {len(res)}\n")
log(res.to_string())

# markdown
with open(OUT / "results_table.md", "w", encoding="utf-8") as f:
    f.write(res.to_markdown(index=False))

log("\nDONE")
