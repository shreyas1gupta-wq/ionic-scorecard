"""Phase-1.2/1.3 : fundamental factor library (1Y & 5Y cores) — Quality / Growth / Value / Leverage.
Tidies the screener_deep long-format annual P&L / balance-sheet / cash-flow parquets into per-symbol
yearly series, derives raw factors, then cross-sectional-percentiles them among the pilot (relative
scoring, NO hard cutoffs). Value factors need shares outstanding, which the raw data does not carry
directly; shares are DERIVED from real reported Net Profit / EPS (an accounting identity on real
numbers, not a fabrication) and flagged [INFERENCE]. Anything that cannot be derived is left NaN
("missing") — never imputed, never invented, per ALPHA_RANKER hard rules.

Schema notes (screener_deep, discovered by inspection, 2026-07-16):
- symbol format = bare NSE symbol (e.g. "MARUTI", "HDFCBANK") — matches the pilot list directly.
- Non-bank P&L: Sales+, Expenses+, Operating Profit, OPM %, Other Income+, Interest, Depreciation,
  Profit before tax, Tax %, Net Profit+, EPS in Rs, Dividend Payout %.
- Bank P&L (HDFCBANK): Revenue+ (not Sales+), Interest, Expenses+, Financing Profit, Financing
  Margin % (not Operating Profit/OPM%), Other Income+, Depreciation, Profit before tax, Tax %,
  Net Profit+, EPS in Rs, Dividend Payout %. No "Operating Profit" row -> EBIT/EBITDA are derived
  generically below (schema-agnostic) instead of relying on Operating Profit.
- Balance sheet: Equity Capital, Reserves, Borrowings+ (non-bank) / Borrowing (+Deposits, bank),
  Other Liabilities+, Total Liabilities, ... No shares-outstanding or market-cap line anywhere in
  the repo's fundamentals sources (screener_deep, mc_fundamentals_parsed, india_stock_metadata all
  checked) -> shares must be derived (see above) or the value theme is marked missing.
- Cash flow: Cash from Operating Activity+ (CFO), Free Cash Flow, CFO/OP.
- Periods: most names report on a Mar-ending FY; NESTLEIND has a broken series (only "Dec 2023"
  stub + "Mar 2025"/"Mar 2026" — an FY-end transition) giving just 2 usable Mar points -> growth
  CAGRs for NESTLEIND are correctly starved and marked missing, not fabricated.
- SHAKTIPUMP is ABSENT from all three screener_deep parquets -> entire fundamental row is missing.

Generic (schema-agnostic) derivations used for EBIT/EBITDA/interest-cover so bank and non-bank rows
are computed the same way (avoids relying on Operating Profit, which doesn't exist for banks):
    EBIT_proxy    = Profit-before-tax + Interest         (add back interest expense)
    EBITDA_proxy  = EBIT_proxy + Depreciation             (add back D&A)
    interest_cover = EBIT_proxy / Interest
These are algebraic identities off real reported P&L lines, not invented figures.
"""
import os, re, glob
import numpy as np, pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
PROJ = os.path.join(BASE, "ALPHA_RANKER")
SCREEN = os.path.join(BASE, "datasets", "screener_deep")
PRICES = os.path.join(PROJ, "data", "prices")
RES = os.path.join(PROJ, "results"); os.makedirs(RES, exist_ok=True)
REP = os.path.join(PROJ, "reports"); os.makedirs(REP, exist_ok=True)

PILOT = ["HDFCBANK", "ASIANPAINT", "NESTLEIND", "TATASTEEL", "HINDALCO",
         "MARUTI", "TCS", "INFY", "GRAVITA", "SHAKTIPUMP"]

PERIOD_RE = re.compile(r"^(Mar|Dec) (19|20)\d{2}$")  # exclude stub cols like "Mar 202315m","Mar 20228m"

def parse_num(x, is_pct=False):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).strip()
    if s in ("", "-", "nan", "NaN", "None"):
        return np.nan
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = s.replace(",", "").replace("%", "")
    try:
        v = float(s)
    except ValueError:
        return np.nan
    if neg:
        v = -v
    if is_pct:
        v = v / 100.0
    return v

def load_screener(name):
    return pd.read_parquet(os.path.join(SCREEN, f"screener_{name}.parquet"))

pl_df = load_screener("annual_pl")
bs_df = load_screener("balance_sheet")
cf_df = load_screener("cash_flow")

def dominant_suffix_years(df, symbol, anchor_metrics):
    """For a symbol, find which period-suffix (Mar/Dec) carries the most non-null data on an
    anchor top-line metric, then return the sorted list of (year:int, colname) using ONLY that
    suffix's clean 4-digit columns (stub/transition columns like '...15m' excluded)."""
    sub = df[df.symbol == symbol]
    if sub.empty:
        return []
    row = None
    for m in anchor_metrics:
        r = sub[sub.metric == m]
        if not r.empty:
            row = r.iloc[0]
            break
    if row is None:
        return []
    period_cols = [c for c in df.columns if PERIOD_RE.match(c)]
    counts = {"Mar": 0, "Dec": 0}
    for c in period_cols:
        if pd.notna(row[c]):
            counts[c.split()[0]] += 1
    dominant = "Mar" if counts["Mar"] >= counts["Dec"] else "Dec"
    years = []
    for c in period_cols:
        if c.split()[0] != dominant:
            continue
        if pd.notna(row[c]):
            years.append((int(c.split()[1]), c))
    return sorted(years)

def series_for(df, symbol, metric, years):
    sub = df[(df.symbol == symbol) & (df.metric == metric)]
    is_pct = "%" in metric
    if sub.empty:
        return pd.Series({y: np.nan for y, _ in years}, dtype=float)
    row = sub.iloc[0]
    return pd.Series({y: parse_num(row[c], is_pct=is_pct) for y, c in years}, dtype=float)

def cagr(series, years_back):
    """CAGR using the actual calendar gap between the latest year and the nearest available year
    >= years_back away (never assumes evenly-spaced data). Requires both endpoints positive."""
    s = series.dropna()
    if len(s) < 2:
        return np.nan
    latest_y = s.index.max()
    latest_v = s.loc[latest_y]
    candidates = [y for y in s.index if y <= latest_y - years_back]
    if not candidates:
        return np.nan
    base_y = max(candidates)
    base_v = s.loc[base_y]
    n = latest_y - base_y
    if n <= 0 or latest_v <= 0 or base_v <= 0:
        return np.nan
    return (latest_v / base_v) ** (1 / n) - 1

def trend_slope(series, lookback=5):
    """OLS slope of the last <=lookback annual values, normalised by the series mean (so it's a
    %-per-year drift, comparable across stocks of different absolute margin levels)."""
    s = series.dropna()
    if len(s) < 3:
        return np.nan
    s = s.sort_index().iloc[-lookback:]
    x = np.arange(len(s))
    if np.nanmean(np.abs(s.values)) == 0:
        return np.nan
    slope = np.polyfit(x, s.values, 1)[0]
    return slope / abs(np.nanmean(s.values))

def stability(series, lookback=5):
    """Negative coefficient of variation over the last <=lookback years -> higher (closer to 0)
    means more stable margins."""
    s = series.dropna()
    if len(s) < 3:
        return np.nan
    s = s.sort_index().iloc[-lookback:]
    m = np.nanmean(s.values)
    if m == 0:
        return np.nan
    return -np.nanstd(s.values) / abs(m)

def last_price(symbol):
    fp = os.path.join(PRICES, f"{symbol}.parquet")
    if not os.path.exists(fp):
        return np.nan
    df = pd.read_parquet(fp).sort_index()
    return float(df["Close"].iloc[-1])

raw = {}
notes = {}

for sym in PILOT:
    f = {}
    n = []
    has_screener = sym in set(pl_df.symbol.unique())
    if not has_screener:
        n.append("ABSENT from screener_deep (all 3 statements) -> entire fundamental row missing.")
        raw[sym] = f
        notes[sym] = n
        continue

    pl_years = dominant_suffix_years(pl_df, sym, ["Sales+", "Revenue+"])
    bs_years = dominant_suffix_years(bs_df, sym, ["Equity Capital"])
    cf_years = dominant_suffix_years(cf_df, sym, ["Cash from Operating Activity+"])
    if len(pl_years) < 2:
        n.append(f"Only {len(pl_years)} usable annual P&L period(s) after excluding stub columns.")

    is_bank = not pl_df[(pl_df.symbol == sym) & (pl_df.metric == "Operating Profit")].shape[0]
    sales_metric = "Revenue+" if is_bank else "Sales+"

    sales   = series_for(pl_df, sym, sales_metric, pl_years)
    exp_    = series_for(pl_df, sym, "Expenses+", pl_years)
    opm     = series_for(pl_df, sym, "OPM %", pl_years)          # NaN for bank (no such row)
    interest= series_for(pl_df, sym, "Interest", pl_years)
    dep     = series_for(pl_df, sym, "Depreciation", pl_years)
    pbt     = series_for(pl_df, sym, "Profit before tax", pl_years)
    netprofit = series_for(pl_df, sym, "Net Profit+", pl_years)
    eps     = series_for(pl_df, sym, "EPS in Rs", pl_years)

    npm = (netprofit / sales).replace([np.inf, -np.inf], np.nan)
    ebit = pbt + interest.fillna(0)
    ebitda = ebit + dep.fillna(0)

    eq_cap  = series_for(bs_df, sym, "Equity Capital", bs_years)
    reserves= series_for(bs_df, sym, "Reserves", bs_years)
    borrow_col = "Borrowings+" if pl_df is not None and bs_df[(bs_df.symbol==sym)&(bs_df.metric=="Borrowings+")].shape[0] else "Borrowing"
    borrow  = series_for(bs_df, sym, borrow_col, bs_years)
    networth = eq_cap + reserves
    cap_employed = networth + borrow.fillna(0)

    cfo = series_for(cf_df, sym, "Cash from Operating Activity+", cf_years)

    latest_y = max(pl_years)[0] if pl_years else None
    latest_bs_y = max(bs_years)[0] if bs_years else None

    # ---------------- QUALITY ----------------
    if latest_y is not None and latest_bs_y is not None and networth.get(latest_bs_y, np.nan) not in (0, np.nan) and not pd.isna(networth.get(latest_bs_y, np.nan)):
        f["roe_last"] = netprofit.get(latest_y, np.nan) / networth.get(latest_bs_y, np.nan)
    else:
        f["roe_last"] = np.nan
    if latest_y is not None and latest_bs_y is not None and not pd.isna(cap_employed.get(latest_bs_y, np.nan)) and cap_employed.get(latest_bs_y, 0) != 0:
        f["roce_last"] = ebit.get(latest_y, np.nan) / cap_employed.get(latest_bs_y, np.nan)
    else:
        f["roce_last"] = np.nan
    f["opm_level"] = opm.get(latest_y, np.nan) if latest_y is not None else np.nan
    if is_bank:
        n.append("Bank schema: no Operating Profit/OPM% row -> opm_level & opm_trend/stability left missing (Financing Margin% is not comparable to non-bank OPM%).")
    f["npm_level"] = npm.get(latest_y, np.nan) if latest_y is not None else np.nan
    f["opm_trend_5y"]  = trend_slope(opm, 5)
    f["npm_trend_5y"]  = trend_slope(npm, 5)
    f["opm_stability_5y"] = stability(opm, 5)
    f["npm_stability_5y"] = stability(npm, 5)
    if latest_y is not None and netprofit.get(latest_y, np.nan) not in (0,) and not pd.isna(netprofit.get(latest_y, np.nan)) and latest_y in cfo.index and not pd.isna(cfo.get(latest_y, np.nan)):
        f["cfo_pat_last"] = cfo.get(latest_y) / netprofit.get(latest_y)
    else:
        f["cfo_pat_last"] = np.nan

    # ---------------- GROWTH ----------------
    f["sales_cagr_3y"] = cagr(sales, 3)
    f["sales_cagr_5y"] = cagr(sales, 5)
    f["eps_cagr_3y"]   = cagr(eps, 3)
    f["eps_cagr_5y"]   = cagr(eps, 5)
    f["sales_yoy_last"] = cagr(sales, 1)
    f["eps_yoy_last"]   = cagr(eps, 1)
    f["sales_accel"] = (f["sales_cagr_3y"] - f["sales_cagr_5y"]) if pd.notna(f["sales_cagr_3y"]) and pd.notna(f["sales_cagr_5y"]) else np.nan
    f["eps_accel"]   = (f["eps_cagr_3y"] - f["eps_cagr_5y"]) if pd.notna(f["eps_cagr_3y"]) and pd.notna(f["eps_cagr_5y"]) else np.nan

    # ---------------- VALUE (needs derived shares) ----------------
    eps_last = eps.get(latest_y, np.nan) if latest_y is not None else np.nan
    np_last  = netprofit.get(latest_y, np.nan) if latest_y is not None else np.nan
    price = last_price(sym)
    shares = np.nan
    if pd.notna(eps_last) and eps_last > 0.05 and pd.notna(np_last) and np_last > 0:
        shares = np_last / eps_last   # [INFERENCE] derived from real Net Profit / EPS identity
    if pd.isna(shares) or pd.isna(price):
        n.append("Value theme: shares-outstanding could not be derived (EPS<=0 / missing) or price missing -> P/E, P/B, EV/EBITDA left missing (no fabrication).")
        f["pe"] = f["pb"] = f["ev_ebitda"] = np.nan
    else:
        mcap = price * shares
        bvps = networth.get(latest_bs_y, np.nan) / shares if latest_bs_y is not None else np.nan
        f["pe"] = price / eps_last if eps_last > 0 else np.nan
        f["pb"] = price / bvps if pd.notna(bvps) and bvps > 0 else np.nan
        debt_last = borrow.get(latest_bs_y, np.nan) if latest_bs_y is not None else np.nan
        ebitda_last = ebitda.get(latest_y, np.nan) if latest_y is not None else np.nan
        if pd.notna(debt_last) and pd.notna(ebitda_last) and ebitda_last > 0:
            ev = mcap + debt_last   # [INFERENCE] EV approximated as MCap+Debt, NO cash netting (cash not separately itemised in screener's condensed BS) -> approximate, flagged
            f["ev_ebitda"] = ev / ebitda_last
            n.append("EV/EBITDA is APPROXIMATE: EV = MCap + gross Borrowings, cash NOT netted off (screener's condensed balance sheet has no standalone cash line) -> overstates EV/understates cheapness for cash-rich names.")
        else:
            f["ev_ebitda"] = np.nan

    # ---------------- LEVERAGE ----------------
    if latest_bs_y is not None and networth.get(latest_bs_y, np.nan) not in (0, np.nan) and not pd.isna(networth.get(latest_bs_y, np.nan)):
        f["debt_equity"] = borrow.get(latest_bs_y, np.nan) / networth.get(latest_bs_y, np.nan)
    else:
        f["debt_equity"] = np.nan
    int_last = interest.get(latest_y, np.nan) if latest_y is not None else np.nan
    if pd.notna(int_last) and int_last > 0:
        f["interest_cover"] = ebit.get(latest_y, np.nan) / int_last
    else:
        f["interest_cover"] = np.nan
        n.append("interest_cover missing where reported Interest expense is 0/NaN (would be undefined/infinite, not fabricated).")
    ebitda_last2 = ebitda.get(latest_y, np.nan) if latest_y is not None else np.nan
    if pd.notna(ebitda_last2) and ebitda_last2 > 0 and latest_bs_y is not None:
        f["debt_ebitda_gross"] = borrow.get(latest_bs_y, np.nan) / ebitda_last2
        n.append("debt_ebitda_gross is GROSS debt/EBITDA (no cash netted off, same cash-line limitation as EV/EBITDA) -- not true 'net debt'.")
    else:
        f["debt_ebitda_gross"] = np.nan

    if is_bank:
        n.append("HDFCBANK: leverage ratios (D/E, debt/EBITDA) are NOT comparable to non-financials -- deposits (a bank's core funding) are not counted as 'Borrowings'; interpret leverage theme for this name with caution.")

    raw[sym] = f
    notes[sym] = n

raw_df = pd.DataFrame(raw).T
raw_df = raw_df.reindex(PILOT)

QUALITY = ["roe_last","roce_last","opm_level","npm_level","opm_trend_5y","npm_trend_5y",
           "opm_stability_5y","npm_stability_5y","cfo_pat_last"]
GROWTH  = ["sales_cagr_3y","sales_cagr_5y","eps_cagr_3y","eps_cagr_5y","sales_yoy_last","eps_yoy_last",
           "sales_accel","eps_accel"]
VALUE   = ["pe","pb","ev_ebitda"]
LEVERAGE= ["debt_equity","interest_cover","debt_ebitda_gross"]
ALL_FACTORS = QUALITY + GROWTH + VALUE + LEVERAGE
for c in ALL_FACTORS:
    if c not in raw_df.columns:
        raw_df[c] = np.nan
raw_df = raw_df[ALL_FACTORS].astype(float)

# ---- cross-sectional percentile (relative, no hard cutoffs); NaN stays NaN (rank skips it) ----
pct = raw_df.rank(pct=True) * 100
LOWER_BETTER = {"pe","pb","ev_ebitda","debt_equity","debt_ebitda_gross"}
adj = pct.copy()
for c in LOWER_BETTER:
    adj[c] = 100 - pct[c]

theme_quality  = adj[QUALITY].mean(axis=1, skipna=True)
theme_growth   = adj[GROWTH].mean(axis=1, skipna=True)
theme_value    = adj[VALUE].mean(axis=1, skipna=True)
theme_leverage = adj[LEVERAGE].mean(axis=1, skipna=True)

n_quality  = adj[QUALITY].notna().sum(axis=1)
n_growth   = adj[GROWTH].notna().sum(axis=1)
n_value    = adj[VALUE].notna().sum(axis=1)
n_leverage = adj[LEVERAGE].notna().sum(axis=1)

scores = pd.DataFrame({
    "Quality":  theme_quality.where(n_quality > 0).round(1),
    "Growth":   theme_growth.where(n_growth > 0).round(1),
    "Value":    theme_value.where(n_value > 0).round(1),
    "Leverage": theme_leverage.where(n_leverage > 0).round(1),
    "n_quality_factors":  n_quality,
    "n_growth_factors":   n_growth,
    "n_value_factors":    n_value,
    "n_leverage_factors": n_leverage,
})

raw_out = os.path.join(RES, "pilot_fundamental_factors_raw.csv")
scores_out = os.path.join(RES, "pilot_fundamental_scores.csv")
raw_df.round(4).to_csv(raw_out)
scores.to_csv(scores_out)

# ---------------- report ----------------
lines = []
lines.append("# AG1 — Fundamental factor library (Quality / Growth / Value / Leverage), pilot-10")
lines.append("")
lines.append(f"Generated: 2026-07-16. Source: `datasets/screener_deep/*.parquet` (annual, long format) "
             f"+ last Close from `ALPHA_RANKER/data/prices/*.parquet`. All scores are UNCALIBRATED "
             f"cross-sectional relative percentiles among these 10 names only -- NOT absolute grades, "
             f"NOT comparable outside this pilot set.")
lines.append("")
lines.append("## Screener coverage")
covered = [s for s in PILOT if s in set(pl_df.symbol.unique())]
missing_cov = [s for s in PILOT if s not in set(pl_df.symbol.unique())]
lines.append(f"- Covered in screener_deep: {len(covered)}/10 -> {', '.join(covered)}")
lines.append(f"- ABSENT from screener_deep (all 3 statements): {', '.join(missing_cov) if missing_cov else 'none'} "
             f"-> fundamental row is fully NaN/missing for these, not zero-filled.")
lines.append("")
lines.append("## Method notes / limitations (read before using scores)")
lines.append("- **Shares outstanding are not in any fundamentals source checked** (screener_deep, "
              "`datasets/earnings_pit/mc_fundamentals_parsed.parquet`, `datasets/india_stock_metadata`). "
              "Shares are [INFERENCE]-derived as `Net Profit / EPS` off the same year's reported figures "
              "(a real accounting identity, not a guess); if EPS<=0 or missing, the whole Value theme for "
              "that name is left missing rather than fabricated.")
lines.append("- **EV/EBITDA and debt/EBITDA are approximate**: EV = MCap + gross Borrowings with **no cash "
              "netting** (screener's condensed balance sheet has no standalone cash line) -> both ratios "
              "run rich for cash-heavy names (e.g. TCS/INFY) versus a true net-debt calc.")
lines.append("- **EBIT/EBITDA are computed schema-agnostically** as `PBT+Interest` / `+Depreciation` so "
              "bank and non-bank P&L layouts (which differ) are treated consistently.")
lines.append("- **HDFCBANK**: no Operating Profit/OPM% row exists for banks -> opm_level/trend/stability "
              "are missing for it; its leverage ratios (D/E, debt/EBITDA) are not economically comparable "
              "to non-financials (deposits, its core funding, aren't counted as Borrowings).")
lines.append("- **NESTLEIND**: broken/short annual series after an FY-end transition (only 2 usable Mar "
              "points) -> growth CAGRs (3y/5y) are correctly starved and left missing, not fabricated.")
lines.append("- **SHAKTIPUMP**: absent from screener_deep entirely -> its whole fundamental row is missing.")
lines.append("- Theme scores are the mean of that theme's AVAILABLE (non-missing) factor percentiles for "
              "each name -- factor counts per theme are in `pilot_fundamental_scores.csv` "
              "(n_quality_factors etc.) so a low count (thin evidence) is visible, not hidden inside an "
              "average.")
lines.append("")
lines.append("## Per-symbol data notes")
for sym in PILOT:
    if notes.get(sym):
        lines.append(f"- **{sym}**: " + " ".join(notes[sym]))
lines.append("")
lines.append("## Outputs")
lines.append(f"- Raw factors: `{raw_out}`")
lines.append(f"- Theme scores (0-100, uncalibrated, relative to pilot): `{scores_out}`")
lines.append("")
lines.append("## Theme scores snapshot")
lines.append("")
lines.append(scores[["Quality","Growth","Value","Leverage"]].to_markdown())

report_path = os.path.join(REP, "AG1_fundamentals.md")
with open(report_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))

print("Wrote:", raw_out)
print("Wrote:", scores_out)
print("Wrote:", report_path)
print()
print(scores[["Quality","Growth","Value","Leverage"]].to_string())
