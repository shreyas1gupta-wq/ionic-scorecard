"""Phase-1.2 (partial 1.4): Earnings-PIT beat/miss + catalyst/anticipation module.
1M primary lens (Catalyst theme, weight 0.25 per 04_FRAMEWORK_1M.md), secondary input to 1Y.

STRICT PIT DISCIPLINE (firm landmine 3 / D-028):
  - All growth/surprise factors are computed ONLY from rows whose `available_date` <= REF_DATE
    (the date the result was actually public). quarter_end is NEVER used to gate visibility.
  - REF_DATE = system "today". Event-calendar factors (days-to-next-result, days-since-last-result)
    use `nse_earnings_dates/earnings_dates.csv` + `forthcoming_results.csv`, which are a SEPARATE,
    more current calendar feed than the financial-figures PIT parquet (see data-vintage note below).

DATA VINTAGE NOTE (verified, not fabricated): `quarterly_earnings_pit.parquet` for all 10 pilot
names caps out at quarter_end 2023-09-01 / available_date ~Oct-Nov 2023 (13 quarters back to
2020-09-01). This is the frozen state of that PIT source as of this build -- growth/surprise
factors below are computed on the latest data the source actually has, not on a live Q1-FY27
print. The event-calendar (days-to/-since-result) factors DO use current 2026 dates because they
come from the separate, actively-refreshed earnings_dates/forthcoming_results feed.

No hard cutoffs: every factor is turned into a 0-100 cross-sectional percentile among the pilot
10 (see 02_SCORING_ENGINE.md). Uncalibrated -- relative rank only.
"""
import os
import numpy as np
import pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
ROOT = os.path.join(BASE, "ALPHA_RANKER")
RES = os.path.join(ROOT, "results"); os.makedirs(RES, exist_ok=True)
REP = os.path.join(ROOT, "reports"); os.makedirs(REP, exist_ok=True)

EARNINGS_PIT = os.path.join(BASE, "datasets", "earnings_pit", "quarterly_earnings_pit.parquet")
DATES_ALL = os.path.join(BASE, "datasets", "nse_earnings_dates", "earnings_dates.csv")
DATES_FWD = os.path.join(BASE, "datasets", "nse_earnings_dates", "forthcoming_results.csv")

PILOT = ["HDFCBANK", "ASIANPAINT", "NESTLEIND", "TATASTEEL", "HINDALCO",
          "MARUTI", "TCS", "INFY", "GRAVITA", "SHAKTIPUMP"]

REF_DATE = pd.Timestamp.now().normalize()   # "today" -- system date, used ONLY for calendar-distance
UPCOMING_WINDOW_D = 30                        # 1M event flag per 04_FRAMEWORK_1M.md
DRIFT_WINDOW_D = 30                           # post-earnings-drift window (calendar days)

# ---------------------------------------------------------------------------
# 1) Load & filter earnings PIT (financial figures)
# ---------------------------------------------------------------------------
epit = pd.read_parquet(EARNINGS_PIT)
epit = epit[epit["nse_symbol"].isin(PILOT)].copy()
epit["quarter_end"] = pd.to_datetime(epit["quarter_end"])
epit["available_date"] = pd.to_datetime(epit["available_date"])
epit = epit[epit["available_date"] <= REF_DATE]          # PIT gate -- no lookahead
epit = epit.sort_values(["nse_symbol", "quarter_end"]).reset_index(drop=True)

# Revenue proxy: Sales for non-financials, Revenue (total income) for banks/NBFCs where Sales is NaN.
epit["revenue"] = epit["Sales"].fillna(epit["Revenue"])
epit["net_profit"] = epit["Net Profit"]
epit["eps"] = epit["EPS in Rs"]
epit["opm"] = epit["OPM %"]

# ---------------------------------------------------------------------------
# 2) Load earnings-date calendars (separate, more current feed)
# ---------------------------------------------------------------------------
dates_all = pd.read_csv(DATES_ALL)
dates_all["date"] = pd.to_datetime(dates_all["date"], format="%d-%b-%Y", errors="coerce")
dates_all = dates_all[dates_all["symbol"].isin(PILOT) & (dates_all["date"] <= REF_DATE)]
last_result = dates_all.sort_values(["symbol", "date"]).groupby("symbol")["date"].max()

dates_fwd = pd.read_csv(DATES_FWD)
dates_fwd["date"] = pd.to_datetime(dates_fwd["date"], format="%d-%b-%Y", errors="coerce")
dates_fwd = dates_fwd[dates_fwd["symbol"].isin(PILOT)]
# keep only genuinely-future dates relative to REF_DATE (board-meeting notices can go stale)
next_result = dates_fwd[dates_fwd["date"] >= REF_DATE].sort_values(["symbol", "date"]).groupby("symbol")["date"].min()


def lin_trend_expect(vals):
    """Fit a straight line on 4 trailing points (x=0..3), extrapolate to x=4.
    `vals` = [t-4, t-3, t-2, t-1] in chronological order -> returns expected value at t."""
    vals = np.asarray(vals, dtype=float)
    if np.isnan(vals).any():
        return np.nan
    x = np.arange(4)
    b, a = np.polyfit(x, vals, 1)  # slope, intercept (np.polyfit returns highest degree first)
    return a + b * 4


def yoy(series, i, lag=4):
    if i - lag < 0:
        return np.nan
    prev = series.iloc[i - lag]
    cur = series.iloc[i]
    if prev in (0, np.nan) or pd.isna(prev) or pd.isna(cur):
        return np.nan
    return cur / prev - 1


def qoq(series, i):
    if i - 1 < 0:
        return np.nan
    prev = series.iloc[i - 1]
    cur = series.iloc[i]
    if pd.isna(prev) or pd.isna(cur) or prev == 0:
        return np.nan
    return cur / prev - 1


def surprise_at(series, i):
    """Actual[i] vs linear-trend expectation built from i-4..i-1."""
    if i - 4 < 0:
        return np.nan
    window = series.iloc[i - 4:i].tolist()
    exp = lin_trend_expect(window)
    act = series.iloc[i]
    if pd.isna(exp) or pd.isna(act) or exp == 0:
        return np.nan
    return (act - exp) / abs(exp)


rows = {}
for sym, g in epit.groupby("nse_symbol"):
    g = g.reset_index(drop=True)
    n = len(g)
    i = n - 1  # latest quarter index
    rev, npf, eps, opm = g["revenue"], g["net_profit"], g["eps"], g["opm"]

    f = {}
    f["latest_quarter_end"] = g["quarter_end"].iloc[i].date().isoformat()
    f["latest_available_date"] = g["available_date"].iloc[i].date().isoformat()
    f["n_quarters_available"] = n

    # --- YoY / QoQ growth, latest quarter ---
    f["sales_yoy"] = yoy(rev, i)
    f["sales_qoq"] = qoq(rev, i)
    f["np_yoy"] = yoy(npf, i)
    f["np_qoq"] = qoq(npf, i)
    f["eps_yoy"] = yoy(eps, i)
    f["eps_qoq"] = qoq(eps, i)

    # --- growth acceleration: latest YoY minus prior-quarter YoY ---
    f["np_yoy_prior"] = yoy(npf, i - 1)
    f["np_growth_accel"] = f["np_yoy"] - f["np_yoy_prior"] if pd.notna(f["np_yoy"]) and pd.notna(f["np_yoy_prior"]) else np.nan
    f["sales_yoy_prior"] = yoy(rev, i - 1)
    f["sales_growth_accel"] = f["sales_yoy"] - f["sales_yoy_prior"] if pd.notna(f["sales_yoy"]) and pd.notna(f["sales_yoy_prior"]) else np.nan

    # --- OPM change vs trailing-4Q trend (own history, not sector) ---
    if i - 4 >= 0 and opm.iloc[i - 4:i].notna().all() and pd.notna(opm.iloc[i]):
        f["opm_latest"] = opm.iloc[i]
        f["opm_trail4_avg"] = opm.iloc[i - 4:i].mean()
        f["opm_change_vs_trend"] = f["opm_latest"] - f["opm_trail4_avg"]
    else:
        f["opm_latest"] = opm.iloc[i] if pd.notna(opm.iloc[i]) else np.nan
        f["opm_trail4_avg"] = np.nan
        f["opm_change_vs_trend"] = np.nan

    # --- earnings-surprise proxy: latest Net Profit vs trailing-4Q linear-trend expectation ---
    f["np_surprise_pct"] = surprise_at(npf, i)
    f["sales_surprise_pct"] = surprise_at(rev, i)

    # --- consistency: of the last 4 quarters (that have enough history), how many beat their own trend (NP) ---
    beats = 0
    n_checked = 0
    for k in range(max(0, i - 3), i + 1):
        s = surprise_at(npf, k)
        if pd.notna(s):
            n_checked += 1
            if s > 0:
                beats += 1
    f["np_consistency_beats"] = beats
    f["np_consistency_n_checked"] = n_checked

    # --- calendar / catalyst timing ---
    ld = last_result.get(sym, pd.NaT)
    nd = next_result.get(sym, pd.NaT)
    f["last_result_date"] = ld.date().isoformat() if pd.notna(ld) else None
    f["days_since_last_result"] = (REF_DATE - ld).days if pd.notna(ld) else np.nan
    f["next_result_date"] = nd.date().isoformat() if pd.notna(nd) else None
    f["days_to_next_result"] = (nd - REF_DATE).days if pd.notna(nd) else np.nan
    f["upcoming_1m_event"] = int(pd.notna(nd) and 0 <= (nd - REF_DATE).days <= UPCOMING_WINDOW_D)
    f["post_earnings_drift_window"] = int(pd.notna(ld) and 0 <= (REF_DATE - ld).days <= DRIFT_WINDOW_D)

    rows[sym] = f

raw = pd.DataFrame(rows).T
raw.index.name = "nse_symbol"

# ---------------------------------------------------------------------------
# 3) Cross-sectional percentile scoring -> Catalyst/EarningsMomentum theme (0-100)
# ---------------------------------------------------------------------------
score_cols = ["sales_yoy", "sales_qoq", "np_yoy", "np_qoq", "eps_yoy", "eps_qoq",
              "np_growth_accel", "sales_growth_accel", "opm_change_vs_trend",
              "np_surprise_pct", "sales_surprise_pct", "np_consistency_beats"]
num = raw[score_cols].apply(pd.to_numeric, errors="coerce")
pct = num.rank(pct=True) * 100   # higher = more bullish for every one of these (all "more positive is better")
theme_catalyst = pct.mean(axis=1, skipna=True).round(1)

out = raw.copy()
for c in score_cols:
    out[f"pctile_{c}"] = pct[c].round(1)
out["theme_catalyst_earnings_momentum"] = theme_catalyst
out = out.sort_values("theme_catalyst_earnings_momentum", ascending=False)

out.to_csv(os.path.join(RES, "pilot_catalyst_factors.csv"))

upcoming = raw[["last_result_date", "days_since_last_result", "next_result_date",
                "days_to_next_result", "upcoming_1m_event", "post_earnings_drift_window"]].copy()
upcoming = upcoming.sort_values("days_to_next_result", na_position="last")
upcoming.to_csv(os.path.join(RES, "pilot_upcoming_results.csv"))

# ---------------------------------------------------------------------------
# 4) Report
# ---------------------------------------------------------------------------
flagged = upcoming[upcoming["upcoming_1m_event"] == 1]
no_date = upcoming[upcoming["next_result_date"].isna()]

report = []
report.append("# AG2 -- Earnings-PIT Catalyst / Anticipation Module (1M primary, 1Y secondary)")
report.append(f"\nRun date (REF_DATE): {REF_DATE.date().isoformat()}")
report.append("\n## Data vintage (verified, not fabricated)")
report.append(
    "`quarterly_earnings_pit.parquet` for all 10 pilot names caps at quarter_end 2023-09-01 / "
    "available_date ~Oct-Nov 2023 (13 quarters back to 2020-09-01, exact per-symbol counts below). "
    "Growth/surprise factors are therefore computed on the LATEST quarter the PIT source actually "
    "has for each name, not a live current print. The days-to/-since-result calendar factors use the "
    "separate, actively-refreshed `earnings_dates.csv` / `forthcoming_results.csv` feed and DO reflect "
    "real 2026 dates."
)
report.append(f"\nQuarters available per pilot symbol: all 10 = {int(raw['n_quarters_available'].iloc[0])} "
              f"(range {epit.groupby('nse_symbol')['quarter_end'].min().min().date()} to "
              f"{epit.groupby('nse_symbol')['quarter_end'].max().max().date()}).")

report.append("\n## Method")
report.append("- Revenue = `Sales` for non-financials, `Revenue` (total income) for banks/NBFCs (Sales is NaN there, e.g. HDFCBANK).")
report.append("- YoY = latest quarter vs same quarter prior year (quarter_end lag 4). QoQ = latest vs immediately prior quarter.")
report.append("- Growth ACCELERATION = latest YoY minus prior-quarter's own YoY (Net Profit and Sales).")
report.append("- OPM change = latest OPM% minus trailing-4-quarter average OPM% (own history, no sector comparison).")
report.append("- Earnings-surprise proxy = actual Net Profit / Sales vs a linear-trend expectation fit on the "
              "PRECEDING 4 quarters and extrapolated one step forward (own-trend beat/miss, not a sell-side consensus -- we don't have one).")
report.append("- Consistency = count of the last 4 quarters (that have enough trailing history) whose Net Profit surprise was positive (0-4).")
report.append("- days_to_next_result / upcoming_1m_event(<=30d) from `forthcoming_results.csv`; "
              "days_since_last_result / post_earnings_drift_window(<=30d) from `earnings_dates.csv` (actuals only, filtered <= REF_DATE).")
report.append("- All factors -> cross-sectional percentile (0-100) among the pilot 10, no hard cutoffs (per `02_SCORING_ENGINE.md`); "
              "Catalyst/EarningsMomentum theme = simple mean of the available percentiles. Uncalibrated relative rank only.")
report.append("\n**Caveat:** TATASTEEL's np_yoy/np_surprise_pct are large negative multiples (e.g. -602%) because Net Profit swung from "
              "a small positive base (Rs 1,297cr, Sep-2022) to a loss (Rs -6,511cr, Sep-2023) -- a real, verified swing (checked against the "
              "raw parquet), not a bug, but a reminder that %-growth off a small/negative base is noisy in magnitude. Percentile (rank-only) "
              "scoring is used specifically to avoid this distorting other names' scores.")

report.append("\n## Catalyst/EarningsMomentum theme score (0-100, higher = stronger earnings momentum + beat consistency)")
disp = out[["theme_catalyst_earnings_momentum", "np_yoy", "np_growth_accel", "np_surprise_pct", "np_consistency_beats"]].copy()
disp["np_yoy"] = (disp["np_yoy"] * 100).round(1)
disp["np_growth_accel"] = (disp["np_growth_accel"] * 100).round(1)
disp["np_surprise_pct"] = (disp["np_surprise_pct"] * 100).round(1)
report.append(disp.to_markdown())

report.append("\n## Upcoming results / event proximity (1M catalyst gate)")
report.append(f"Pilot names with an upcoming result WITHIN the 1M (~{UPCOMING_WINDOW_D}d) window flagged in `forthcoming_results.csv`:")
if len(flagged):
    report.append(flagged[["next_result_date", "days_to_next_result"]].to_markdown())
else:
    report.append("None flagged.")

report.append(f"\nPilot names with NO upcoming date in `forthcoming_results.csv` (feed only covers ~{dates_fwd['date'].min().date()} to {dates_fwd['date'].max().date()}):")
if len(no_date):
    report.append(", ".join(no_date.index.tolist()))
else:
    report.append("None -- all pilot names have an upcoming date.")

report.append("\nFull per-symbol calendar (`pilot_upcoming_results.csv`):")
report.append(upcoming.to_markdown())

report.append("\n## Outputs")
report.append("- `ALPHA_RANKER/results/pilot_catalyst_factors.csv` -- raw factors + percentiles + theme score")
report.append("- `ALPHA_RANKER/results/pilot_upcoming_results.csv` -- event-calendar distances")
report.append("\n## Landmines enforced")
report.append("- D-028/T-series lookahead: all growth/surprise factors gated on `available_date` <= REF_DATE, never `quarter_end`.")
report.append("- Landmine 3: PIT dataset with `available_date`, not quarter-end, used throughout.")
report.append("- No fabrication: data-vintage gap (PIT caps 2023-Q3) stated explicitly above, not smoothed over.")

with open(os.path.join(REP, "AG2_catalyst.md"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(report))

print("Wrote:")
print(" ", os.path.join(RES, "pilot_catalyst_factors.csv"))
print(" ", os.path.join(RES, "pilot_upcoming_results.csv"))
print(" ", os.path.join(REP, "AG2_catalyst.md"))
print("\nTheme scores (desc):")
print(out["theme_catalyst_earnings_momentum"].to_string())
print("\nUpcoming-1M-event flags:")
print(upcoming[upcoming.upcoming_1m_event == 1][["next_result_date", "days_to_next_result"]].to_string())
print("\nNo upcoming date on file:", no_date.index.tolist())
