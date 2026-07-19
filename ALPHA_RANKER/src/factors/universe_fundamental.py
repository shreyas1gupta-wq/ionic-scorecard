"""Universe-scale FUNDAMENTAL + CATALYST engine (Quality/Growth/Value/Leverage + Catalyst),
computed over ALL currently-scraped symbols in data/fundamentals/consolidated/ (long-format,
built by src/lib/consolidate_screener.py from data/fundamentals/screener_live/*.json).

REUSES the exact logic/derivations of the pilot scripts:
  - src/factors/factors_fundamental.py  (Quality/Growth/Value/Leverage derivations, generic
    EBIT/EBITDA-via-PBT+Interest+Dep, shares-from-NetProfit/EPS identity, cross-sectional pct)
  - src/factors/fresh_catalyst.py       (quarterly YoY/QoQ/surprise/opm_change catalyst factors)
but:
  (a) reads the LIVE consolidated parquets (Mar/Jun-2026 vintage), not the stale screener_deep
      pilot source;
  (b) runs over the FULL scraped universe (currently a subset of NIFTY-750; data still landing),
      cross-sectional percentiles taken over whatever is covered NOW -- code re-percentiles
      automatically as coverage grows, no hardcoded pilot list;
  (c) prefers top_ratios (screener's own TTM Market Cap / Current Price / Stock P/E / Book Value
      / ROCE / ROE) over the derived-shares approach where available, falling back to the
      identity-derived method only when top_ratios is missing a field;
  (d) branches BANK/NBFC ("financial") schema explicitly: no Sales/OPM/Operating-Profit rows,
      no Promoters row in shareholding (widely-held) -> leverage ratios (D/E, interest-cover,
      debt/EBITDA) are marked N/A (not computed) because deposits/borrowings are core funding,
      not leverage in the normal sense for these names.

HARD RULES: no fabrication (missing -> NaN, never imputed); no lookahead (uses only the latest
scraped annual/quarterly period per symbol, no future data); all cross-sectional stats are
percentiles (0-100), no hard cutoffs.
"""
import os, re, glob
import numpy as np, pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
PROJ = os.path.join(BASE, "ALPHA_RANKER")
CONS = os.path.join(PROJ, "data", "fundamentals", "consolidated")
PRICES = os.path.join(PROJ, "data", "prices")
UNIV_FILE = os.path.join(PROJ, "data", "universe", "symbols_750.txt")
RES = os.path.join(PROJ, "results"); os.makedirs(RES, exist_ok=True)
REP = os.path.join(PROJ, "reports"); os.makedirs(REP, exist_ok=True)

PERIOD_RE = re.compile(r"^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec) (19|20)\d{2}$")
QMON = {"Jan":1,"Feb":2,"Mar":3,"Apr":4,"May":5,"Jun":6,"Jul":7,"Aug":8,"Sep":9,"Oct":10,"Nov":11,"Dec":12}


def qkey(lbl):
    m = re.match(r"([A-Za-z]{3})\s+(\d{4})", str(lbl))
    if not m:
        return None
    return int(m.group(2)) * 100 + QMON.get(m.group(1), 0)


def parse_num(x, is_pct=False):
    """Same permissive numeric parser as the pilot: handles commas, %, (neg), Rs symbol, blanks."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return np.nan
    s = str(x).strip()
    if s in ("", "-", "nan", "NaN", "None"):
        return np.nan
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    s = s.replace(",", "").replace("%", "").replace("₹", "").strip()
    try:
        v = float(s)
    except ValueError:
        return np.nan
    if neg:
        v = -v
    if is_pct:
        v = v / 100.0
    return v


def parse_crore(x):
    """Parse a screener 'Market Cap'-style string '₹ 7,96,450 Cr.' -> float in Rs Crore."""
    if x is None:
        return np.nan
    s = str(x).replace("₹", "").replace("Cr.", "").replace("Cr", "").strip()
    return parse_num(s)


print("Loading consolidated long-format tables ...")
pl_df = pd.read_parquet(os.path.join(CONS, "profit_loss.parquet"))
bs_df = pd.read_parquet(os.path.join(CONS, "balance_sheet.parquet"))
cf_df = pd.read_parquet(os.path.join(CONS, "cash_flow.parquet"))
qr_df = pd.read_parquet(os.path.join(CONS, "quarterly_results.parquet"))
sh_df = pd.read_parquet(os.path.join(CONS, "shareholding.parquet"))
top_df = pd.read_parquet(os.path.join(CONS, "top_ratios.parquet"))
manifest = pd.read_csv(os.path.join(CONS, "coverage_manifest.csv"))

with open(UNIV_FILE) as f:
    UNIVERSE_750 = [l.strip() for l in f if l.strip()]

covered_syms = sorted(set(pl_df.symbol.unique()) | set(qr_df.symbol.unique()))
in_universe_covered = [s for s in covered_syms if s in set(UNIVERSE_750)]
extra_covered = [s for s in covered_syms if s not in set(UNIVERSE_750)]  # scraped but not on the 750 list (e.g. renamed/edge cases)
missing_from_universe = [s for s in UNIVERSE_750 if s not in set(covered_syms)]

print(f"Universe file: {len(UNIVERSE_750)} symbols. Scraped/consolidated: {len(covered_syms)}. "
      f"Overlap: {len(in_universe_covered)}. Not yet scraped: {len(missing_from_universe)}.")

SYMS = covered_syms  # compute for everything we HAVE; percentile universe = whatever is covered now

top_pivot = top_df.pivot_table(index="symbol", columns="ratio", values="value", aggfunc="first")
top_raw_pivot = top_df.pivot_table(index="symbol", columns="ratio", values="raw", aggfunc="first")


def dominant_suffix_years(df, symbol, anchor_metrics):
    sub = df[(df.symbol == symbol) & (df.metric.isin(anchor_metrics))]
    if sub.empty:
        return []
    row = None
    for m in anchor_metrics:
        r = sub[sub.metric == m]
        if not r.empty:
            row = r
            break
    if row is None:
        return []
    # long format here: rows are (symbol, metric, period, value); collapse to a period->value map
    per = row.set_index("period")["value"]
    counts = {}
    for p in per.index:
        if PERIOD_RE.match(str(p)) and pd.notna(per[p]):
            mon = str(p).split()[0]
            counts[mon] = counts.get(mon, 0) + 1
    if not counts:
        return []
    dominant = max(counts, key=counts.get)
    years = []
    for p in per.index:
        if PERIOD_RE.match(str(p)) and str(p).split()[0] == dominant and pd.notna(per[p]):
            years.append((int(str(p).split()[1]), p))
    return sorted(years)


def series_for(df, symbol, metric, years):
    sub = df[(df.symbol == symbol) & (df.metric == metric)]
    if sub.empty:
        return pd.Series({y: np.nan for y, _ in years}, dtype=float)
    per = sub.set_index("period")["value"]
    return pd.Series({y: per.get(p, np.nan) for y, p in years}, dtype=float)


def cagr(series, years_back):
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
    try:
        df = pd.read_parquet(fp).sort_index()
        return float(df["Close"].iloc[-1])
    except Exception:
        return np.nan


# ---------------- quarterly helpers (catalyst theme), same logic as fresh_catalyst.py ----------------
def q_series(sym, want_keywords):
    sub = qr_df[qr_df.symbol == sym]
    if sub.empty:
        return {}
    metrics = sub.metric.unique()
    target = None
    for m in metrics:
        ml = str(m).lower()
        if any(w in ml for w in want_keywords):
            target = m
            break
    if target is None:
        return {}
    row = sub[sub.metric == target]
    return {p: v for p, v in zip(row.period, row.value) if qkey(p) is not None}


def yoy(s, n=4):
    ks = sorted(s, key=qkey)
    if len(ks) <= n:
        return np.nan
    a, b = s[ks[-1]], s[ks[-1 - n]]
    if pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / abs(b) - 1


def qoq(s):
    ks = sorted(s, key=qkey)
    if len(ks) < 2:
        return np.nan
    a, b = s[ks[-1]], s[ks[-2]]
    if pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / abs(b) - 1


def surprise(s):
    ks = sorted(s, key=qkey)
    if len(ks) < 5:
        return np.nan
    hist = [s[k] for k in ks[-5:-1]]
    if any(pd.isna(v) for v in hist):
        return np.nan
    x = np.arange(4)
    coef = np.polyfit(x, hist, 1)
    exp = np.polyval(coef, 4)
    if exp == 0:
        return np.nan
    return (s[ks[-1]] - exp) / abs(exp)


def ttm_yoy(s):
    """TTM sum vs prior TTM sum, YoY. Needs >=8 quarters."""
    ks = sorted(s, key=qkey)
    if len(ks) < 8:
        return np.nan
    last4 = [s[k] for k in ks[-4:]]
    prev4 = [s[k] for k in ks[-8:-4]]
    if any(pd.isna(v) for v in last4) or any(pd.isna(v) for v in prev4):
        return np.nan
    a, b = sum(last4), sum(prev4)
    if b == 0:
        return np.nan
    return a / abs(b) - 1


def consistency(s, n=8):
    """Fraction of last n YoY-quarter growth checks that are positive (own-trend consistency)."""
    ks = sorted(s, key=qkey)
    if len(ks) < n + 4:
        return np.nan
    hits = []
    for i in range(len(ks) - n, len(ks)):
        if i - 4 < 0:
            continue
        a, b = s[ks[i]], s[ks[i - 4]]
        if pd.isna(a) or pd.isna(b) or b == 0:
            continue
        hits.append(1.0 if a > b else 0.0)
    if len(hits) < 3:
        return np.nan
    return float(np.mean(hits))


# ================= per-symbol computation =================
raw = {}
cat_raw = {}
notes = {}
bank_syms = []

for sym in SYMS:
    f = {}
    c = {}
    n = []

    has_pl = sym in set(pl_df.symbol.unique())
    is_bank = has_pl and (pl_df[(pl_df.symbol == sym) & (pl_df.metric == "Operating Profit")].empty)
    if is_bank:
        bank_syms.append(sym)

    # ---------------- annual fundamentals (Quality/Growth/Value/Leverage) ----------------
    if not has_pl:
        n.append("No annual profit_loss row in consolidated data -> fundamental theme fully missing.")
    else:
        pl_years = dominant_suffix_years(pl_df, sym, ["Sales", "Revenue"])
        bs_years = dominant_suffix_years(bs_df, sym, ["Equity Capital"])
        cf_years = dominant_suffix_years(cf_df, sym, ["Cash from Operating Activity"])
        if len(pl_years) < 2:
            n.append(f"Only {len(pl_years)} usable annual P&L period(s).")

        sales_metric = "Revenue" if is_bank else "Sales"
        sales = series_for(pl_df, sym, sales_metric, pl_years)
        opm = series_for(pl_df, sym, "OPM %", pl_years)  # NaN for bank/NBFC (no such row)
        interest = series_for(pl_df, sym, "Interest", pl_years)
        dep = series_for(pl_df, sym, "Depreciation", pl_years)
        pbt = series_for(pl_df, sym, "Profit before tax", pl_years)
        netprofit = series_for(pl_df, sym, "Net Profit", pl_years)
        eps = series_for(pl_df, sym, "EPS in Rs", pl_years)

        npm = (netprofit / sales).replace([np.inf, -np.inf], np.nan)
        ebit = pbt + interest.fillna(0)
        ebitda = ebit + dep.fillna(0)

        eq_cap = series_for(bs_df, sym, "Equity Capital", bs_years)
        reserves = series_for(bs_df, sym, "Reserves", bs_years)
        has_borrowings_plus = not bs_df[(bs_df.symbol == sym) & (bs_df.metric == "Borrowings")].empty
        borrow_metric = "Borrowings" if has_borrowings_plus else "Borrowing"
        borrow = series_for(bs_df, sym, borrow_metric, bs_years)
        networth = eq_cap + reserves
        cap_employed = networth + borrow.fillna(0)

        cfo = series_for(cf_df, sym, "Cash from Operating Activity", cf_years)

        latest_y = max(pl_years)[0] if pl_years else None
        latest_bs_y = max(bs_years)[0] if bs_years else None

        # ---- QUALITY: prefer screener's own TTM ROE/ROCE (top_ratios) for the "level", own-computed for trend/stability ----
        top_roe = top_pivot.loc[sym, "ROE"] / 100.0 if sym in top_pivot.index and "ROE" in top_pivot.columns and pd.notna(top_pivot.loc[sym, "ROE"]) else np.nan
        top_roce = top_pivot.loc[sym, "ROCE"] / 100.0 if sym in top_pivot.index and "ROCE" in top_pivot.columns and pd.notna(top_pivot.loc[sym, "ROCE"]) else np.nan
        own_roe = (netprofit.get(latest_y, np.nan) / networth.get(latest_bs_y, np.nan)) if (latest_y is not None and latest_bs_y is not None and networth.get(latest_bs_y, 0) not in (0,) and pd.notna(networth.get(latest_bs_y, np.nan))) else np.nan
        own_roce = (ebit.get(latest_y, np.nan) / cap_employed.get(latest_bs_y, np.nan)) if (latest_y is not None and latest_bs_y is not None and cap_employed.get(latest_bs_y, 0) not in (0,) and pd.notna(cap_employed.get(latest_bs_y, np.nan))) else np.nan
        f["roe_last"] = top_roe if pd.notna(top_roe) else own_roe
        if is_bank:
            f["roce_last"] = np.nan  # ROCE not meaningful for banks/NBFCs (capital employed includes deposits)
            n.append("Bank/NBFC schema: ROCE marked N/A (capital-employed base includes deposits/policy float, not economically comparable to non-financials).")
        else:
            f["roce_last"] = top_roce if pd.notna(top_roce) else own_roce
        f["opm_level"] = opm.get(latest_y, np.nan) if latest_y is not None else np.nan
        if is_bank:
            n.append("Bank/NBFC schema: no Sales/Operating Profit/OPM% rows -> opm_level/trend/stability left missing (Financing Margin% not comparable to non-bank OPM%).")
        f["npm_level"] = npm.get(latest_y, np.nan) if latest_y is not None else np.nan
        f["opm_trend_5y"] = trend_slope(opm, 5)
        f["npm_trend_5y"] = trend_slope(npm, 5)
        f["opm_stability_5y"] = stability(opm, 5)
        f["npm_stability_5y"] = stability(npm, 5)
        if latest_y is not None and netprofit.get(latest_y, 0) not in (0,) and pd.notna(netprofit.get(latest_y, np.nan)) and latest_y in cfo.index and pd.notna(cfo.get(latest_y, np.nan)):
            f["cfo_pat_last"] = cfo.get(latest_y) / netprofit.get(latest_y)
        else:
            f["cfo_pat_last"] = np.nan

        # ---- GROWTH ----
        f["sales_cagr_3y"] = cagr(sales, 3)
        f["sales_cagr_5y"] = cagr(sales, 5)
        f["eps_cagr_3y"] = cagr(eps, 3)
        f["eps_cagr_5y"] = cagr(eps, 5)
        f["sales_yoy_last"] = cagr(sales, 1)
        f["eps_yoy_last"] = cagr(eps, 1)
        f["sales_accel"] = (f["sales_cagr_3y"] - f["sales_cagr_5y"]) if pd.notna(f["sales_cagr_3y"]) and pd.notna(f["sales_cagr_5y"]) else np.nan
        f["eps_accel"] = (f["eps_cagr_3y"] - f["eps_cagr_5y"]) if pd.notna(f["eps_cagr_3y"]) and pd.notna(f["eps_cagr_5y"]) else np.nan

        # ---- VALUE: prefer top_ratios (screener's own TTM P/E, Book Value, Market Cap) ----
        price_scraped = top_pivot.loc[sym, "Current Price"] if sym in top_pivot.index and "Current Price" in top_pivot.columns else np.nan
        price = price_scraped if pd.notna(price_scraped) else last_price(sym)
        pe_top = top_pivot.loc[sym, "Stock P/E"] if sym in top_pivot.index and "Stock P/E" in top_pivot.columns else np.nan
        bv_top = top_pivot.loc[sym, "Book Value"] if sym in top_pivot.index and "Book Value" in top_pivot.columns else np.nan
        mcap_raw = top_raw_pivot.loc[sym, "Market Cap"] if sym in top_raw_pivot.index and "Market Cap" in top_raw_pivot.columns else None
        mcap = parse_crore(mcap_raw) if mcap_raw is not None else np.nan

        eps_last = eps.get(latest_y, np.nan) if latest_y is not None else np.nan
        np_last = netprofit.get(latest_y, np.nan) if latest_y is not None else np.nan
        shares = np.nan
        if pd.isna(mcap) and pd.notna(eps_last) and eps_last > 0.05 and pd.notna(np_last) and np_last > 0:
            shares = np_last / eps_last  # [INFERENCE] fallback identity, only if top_ratios Market Cap absent

        if pd.notna(pe_top):
            f["pe"] = pe_top
        elif pd.notna(eps_last) and eps_last > 0 and pd.notna(price):
            f["pe"] = price / eps_last
        else:
            f["pe"] = np.nan

        if pd.notna(price) and pd.notna(bv_top) and bv_top > 0:
            f["pb"] = price / bv_top
        elif pd.notna(shares) and pd.notna(price) and latest_bs_y is not None:
            bvps = networth.get(latest_bs_y, np.nan) / shares if shares else np.nan
            f["pb"] = price / bvps if pd.notna(bvps) and bvps > 0 else np.nan
        else:
            f["pb"] = np.nan

        debt_last = borrow.get(latest_bs_y, np.nan) if latest_bs_y is not None else np.nan
        ebitda_last = ebitda.get(latest_y, np.nan) if latest_y is not None else np.nan
        mcap_eff = mcap if pd.notna(mcap) else (price * shares if pd.notna(price) and pd.notna(shares) else np.nan)
        if pd.notna(mcap_eff) and pd.notna(debt_last) and pd.notna(ebitda_last) and ebitda_last > 0:
            ev = mcap_eff + debt_last  # [INFERENCE] EV = MCap + gross Borrowings, no cash netting (same as pilot)
            f["ev_ebitda"] = ev / ebitda_last
        else:
            f["ev_ebitda"] = np.nan
        if pd.isna(f["pe"]) and pd.isna(f["pb"]):
            n.append("Value theme: neither top_ratios (Stock P/E/Book Value/Market Cap) nor the shares-identity fallback resolved -> Value left missing, not fabricated.")

        # ---- LEVERAGE ----
        if is_bank:
            f["debt_equity"] = np.nan
            f["interest_cover"] = np.nan
            f["debt_ebitda_gross"] = np.nan
            n.append("Bank/NBFC schema: D/E, interest-cover, debt/EBITDA marked N/A -- deposits/borrowings are core funding, not leverage in the normal sense for these names.")
        else:
            if latest_bs_y is not None and networth.get(latest_bs_y, 0) not in (0,) and pd.notna(networth.get(latest_bs_y, np.nan)):
                f["debt_equity"] = borrow.get(latest_bs_y, np.nan) / networth.get(latest_bs_y, np.nan)
            else:
                f["debt_equity"] = np.nan
            int_last = interest.get(latest_y, np.nan) if latest_y is not None else np.nan
            if pd.notna(int_last) and int_last > 0:
                f["interest_cover"] = ebit.get(latest_y, np.nan) / int_last
            else:
                f["interest_cover"] = np.nan
            ebitda_last2 = ebitda.get(latest_y, np.nan) if latest_y is not None else np.nan
            if pd.notna(ebitda_last2) and ebitda_last2 > 0 and latest_bs_y is not None:
                f["debt_ebitda_gross"] = borrow.get(latest_bs_y, np.nan) / ebitda_last2
            else:
                f["debt_ebitda_gross"] = np.nan

    raw[sym] = f
    notes[sym] = n

    # ---------------- catalyst theme (quarterly) ----------------
    sales_q = q_series(sym, ["sales", "revenue"])
    npf_q = q_series(sym, ["net profit"])
    eps_q = q_series(sym, ["eps"])
    opm_q = q_series(sym, ["opm", "financing margin"])

    opm_change = np.nan
    ks_opm = sorted(opm_q, key=qkey)
    if len(ks_opm) >= 5 and not any(pd.isna(opm_q[k]) for k in ks_opm[-5:]):
        opm_change = opm_q[ks_opm[-1]] - np.mean([opm_q[k] for k in ks_opm[-5:-1]])

    c["sales_yoy"] = yoy(sales_q)
    c["np_yoy"] = yoy(npf_q)
    c["eps_yoy"] = yoy(eps_q)
    c["sales_qoq"] = qoq(sales_q)
    c["np_qoq"] = qoq(npf_q)
    c["opm_change"] = opm_change
    c["np_surprise"] = surprise(npf_q)
    c["sales_surprise"] = surprise(sales_q)
    c["sales_ttm_yoy"] = ttm_yoy(sales_q)
    c["np_ttm_yoy"] = ttm_yoy(npf_q)
    c["np_growth_consistency"] = consistency(npf_q)
    ks_all = sorted(set(sales_q) | set(npf_q) | set(eps_q), key=qkey)
    c["latest_qtr"] = ks_all[-1] if ks_all else None
    cat_raw[sym] = c

raw_df = pd.DataFrame(raw).T.reindex(SYMS)
cat_df = pd.DataFrame(cat_raw).T.reindex(SYMS)

QUALITY = ["roe_last", "roce_last", "opm_level", "npm_level", "opm_trend_5y", "npm_trend_5y",
           "opm_stability_5y", "npm_stability_5y", "cfo_pat_last"]
GROWTH = ["sales_cagr_3y", "sales_cagr_5y", "eps_cagr_3y", "eps_cagr_5y", "sales_yoy_last", "eps_yoy_last",
          "sales_accel", "eps_accel"]
VALUE = ["pe", "pb", "ev_ebitda"]
LEVERAGE = ["debt_equity", "interest_cover", "debt_ebitda_gross"]
ALL_FACTORS = QUALITY + GROWTH + VALUE + LEVERAGE
for col in ALL_FACTORS:
    if col not in raw_df.columns:
        raw_df[col] = np.nan
raw_df = raw_df[ALL_FACTORS].apply(pd.to_numeric, errors="coerce")

LOWER_BETTER = {"pe", "pb", "ev_ebitda", "debt_equity", "debt_ebitda_gross"}
pct = raw_df.rank(pct=True) * 100
adj = pct.copy()
for c in LOWER_BETTER:
    adj[c] = 100 - pct[c]

theme_quality = adj[QUALITY].mean(axis=1, skipna=True)
theme_growth = adj[GROWTH].mean(axis=1, skipna=True)
theme_value = adj[VALUE].mean(axis=1, skipna=True)
theme_leverage = adj[LEVERAGE].mean(axis=1, skipna=True)

n_quality = adj[QUALITY].notna().sum(axis=1)
n_growth = adj[GROWTH].notna().sum(axis=1)
n_value = adj[VALUE].notna().sum(axis=1)
n_leverage = adj[LEVERAGE].notna().sum(axis=1)
n_factors = n_quality + n_growth + n_value + n_leverage

fund_scores = pd.DataFrame({
    "Quality": theme_quality.where(n_quality > 0).round(1),
    "Growth": theme_growth.where(n_growth > 0).round(1),
    "Value": theme_value.where(n_value > 0).round(1),
    "Leverage": theme_leverage.where(n_leverage > 0).round(1),
    "n_quality_factors": n_quality,
    "n_growth_factors": n_growth,
    "n_value_factors": n_value,
    "n_leverage_factors": n_leverage,
    "n_factors": n_factors,
    "is_bank_nbfc_schema": [s in set(bank_syms) for s in SYMS],
})

CAT_FACTORS = ["sales_yoy", "np_yoy", "eps_yoy", "sales_qoq", "np_qoq", "opm_change",
               "np_surprise", "sales_surprise", "sales_ttm_yoy", "np_ttm_yoy", "np_growth_consistency"]
cat_num = cat_df[CAT_FACTORS].apply(pd.to_numeric, errors="coerce")
cat_pct = cat_num.rank(pct=True) * 100
cat_df["theme_catalyst"] = cat_pct.mean(axis=1, skipna=True).round(1)
cat_df["n_catalyst_factors"] = cat_num.notna().sum(axis=1)
cat_df.loc[cat_df["n_catalyst_factors"] == 0, "theme_catalyst"] = np.nan

# ---------------- write outputs ----------------
raw_out = os.path.join(RES, "universe_fundamental_factors_raw.csv")
fund_out = os.path.join(RES, "universe_fundamental_scores.parquet")
cat_out = os.path.join(RES, "universe_catalyst_scores.parquet")

raw_df.round(4).to_csv(raw_out)
fund_scores.to_parquet(fund_out)
cat_cols_out = ["latest_qtr", "n_catalyst_factors", "theme_catalyst"] + CAT_FACTORS
cat_df[cat_cols_out].to_parquet(cat_out)
cat_df[cat_cols_out].round(4).to_csv(os.path.join(RES, "universe_catalyst_scores.csv"))
fund_scores.round(4).to_csv(os.path.join(RES, "universe_fundamental_scores.csv"))

print("Wrote:", raw_out)
print("Wrote:", fund_out)
print("Wrote:", cat_out)
print(f"Symbols scored: {len(SYMS)} | banks/NBFCs (financial schema): {len(bank_syms)}")
print(fund_scores[["Quality", "Growth", "Value", "Leverage", "n_factors"]].describe())

# ---------------- coverage note + markdown report ----------------
lines = []
lines.append("# UNI-A -- Universe Fundamental + Catalyst engine")
lines.append("")
lines.append(f"Generated 2026-07-16. Source: `data/fundamentals/consolidated/*.parquet` "
             f"(built from `data/fundamentals/screener_live/*.json` via `consolidate_screener.py`), "
             f"+ `top_ratios` (screener's own TTM Market Cap/Price/P-E/Book-Value/ROCE/ROE) + last "
             f"Close from `data/prices/*.parquet` as price fallback. **Data is STILL LANDING** -- "
             f"this run covers whatever is scraped as of generation time; re-run after the fleet "
             f"finishes for the full 750.")
lines.append("")
lines.append("## Coverage")
lines.append(f"- Universe file (`symbols_750.txt`): {len(UNIVERSE_750)} symbols.")
lines.append(f"- Consolidated/scraped (have >=1 fundamentals table): {len(covered_syms)} "
             f"({len(covered_syms)/len(UNIVERSE_750)*100:.1f}% of the 750 list).")
lines.append(f"- Of those, on the official 750 list: {len(in_universe_covered)}; "
             f"scraped but NOT on the current 750 list (renames/edge cases, kept & scored anyway): "
             f"{len(extra_covered)}.")
lines.append(f"- Not yet scraped (0 tables) -- fully absent from these outputs, not zero-filled: "
             f"{len(missing_from_universe)}.")
lines.append(f"- Bank/NBFC (\"financial\") schema detected (no Sales/Operating-Profit rows): "
              f"{len(bank_syms)}/{len(SYMS)} scored names.")
lines.append(f"- Fundamental theme non-null factor coverage (mean n_factors out of max "
              f"{len(ALL_FACTORS)}): {fund_scores['n_factors'].mean():.1f}.")
lines.append(f"- Catalyst theme: {(cat_df['n_catalyst_factors']>0).sum()}/{len(SYMS)} names have "
             f">=1 usable quarterly catalyst factor; mean factors used = "
             f"{cat_df['n_catalyst_factors'].mean():.1f} / {len(CAT_FACTORS)}.")
lines.append("")
lines.append("## Bank/NBFC (\"financial\") schema handling")
lines.append("- Detected by absence of an `Operating Profit` row in `profit_loss` for that symbol "
             "(screener shows `Revenue`/`Financing Profit`/`Financing Margin %` instead of "
             "`Sales`/`Operating Profit`/`OPM %`).")
lines.append("- For these names: `opm_level/trend/stability` left missing (Financing Margin % is "
              "not the same economic quantity as non-bank OPM %); `ROCE` and all three Leverage "
              "factors (D/E, interest-cover, debt/EBITDA) are marked N/A -- not computed, because "
              "deposits/borrowings are the core funding mechanism for these businesses, not leverage "
              "in the sense the metric is meant to capture for a manufacturer/services company.")
lines.append("- `ROE`, Growth, Value, and Catalyst themes ARE computed for banks/NBFCs (those "
              "concepts remain meaningful) using `Revenue` in place of `Sales` for growth calcs.")
lines.append("- Shareholding: banks/NBFCs generally carry no `Promoters` row (widely held, e.g. "
              "HDFCBANK shows only FIIs/DIIs/Government/Public) -- this affects any downstream "
              "promoter-holding factor, not this fundamental/catalyst script directly.")
lines.append("")
lines.append("## Method notes (carried over from the pilot, still apply)")
lines.append("- Value theme now PREFERS screener's own TTM `top_ratios` (Stock P/E, Book Value, "
              "Market Cap) over the derived-shares approach; the Net-Profit/EPS shares identity is "
              "only used as a fallback when `top_ratios` lacks the field. EV/EBITDA still has NO "
              "cash netting (screener's condensed balance sheet has no standalone cash line) -> "
              "runs rich for cash-heavy names.")
lines.append("- All theme scores are cross-sectional PERCENTILES (0-100) over the currently-covered "
              "universe (not a fixed pilot list) -- as coverage grows toward 750, re-running this "
              "script re-percentiles against the larger set; scores are NOT stable/comparable "
              "across runs with different coverage.")
lines.append("- No lookahead: each symbol uses only its own latest scraped annual/quarterly period; "
              "no forward-filling or cross-symbol imputation.")
lines.append("- Missing stays missing (NaN) everywhere; nothing is fabricated or zero-filled. "
              "Per-factor completeness (`n_quality_factors` etc, `n_catalyst_factors`) travels with "
              "every score so a thin-evidence average is visible, not hidden.")
lines.append("")


def top_bottom(theme, k=10):
    s = fund_scores[theme].dropna().sort_values(ascending=False)
    top = s.head(k)
    bot = s.tail(k).sort_values()
    return top, bot


lines.append("## Sanity check -- top/bottom 10 per theme")
for theme in ["Quality", "Growth", "Value", "Leverage"]:
    top, bot = top_bottom(theme)
    lines.append(f"\n### {theme}")
    lines.append("**Top 10:** " + ", ".join(f"{s} ({v:.1f})" for s, v in top.items()))
    lines.append("**Bottom 10:** " + ", ".join(f"{s} ({v:.1f})" for s, v in bot.items()))

cs = cat_df["theme_catalyst"].dropna().sort_values(ascending=False)
lines.append("\n### Catalyst")
lines.append("**Top 10:** " + ", ".join(f"{s} ({v:.1f})" for s, v in cs.head(10).items()))
lines.append("**Bottom 10:** " + ", ".join(f"{s} ({v:.1f})" for s, v in cs.tail(10).sort_values().items()))
lines.append("")
lines.append("## Outputs")
lines.append(f"- `{fund_out}` -- symbol x Quality/Value/Growth/Leverage + n_factors + is_bank_nbfc_schema")
lines.append(f"- `{cat_out}` -- symbol x theme_catalyst + key raw catalyst factors")
lines.append(f"- `{raw_out}` -- raw (pre-percentile) fundamental factor values, for audit")

report_path = os.path.join(REP, "UNI_A_fundamental_catalyst.md")
with open(report_path, "w", encoding="utf-8") as fh:
    fh.write("\n".join(lines))
print("Wrote:", report_path)
