"""
ALPHA_RANKER Phase 4 -- Forensic / Red-Flag module.

Computes per-flag forensic indicators for the 10-symbol pilot, per
Shreyas_Ionic_AMC/ALPHA_RANKER/08_FORENSICS_REDFLAGS.md.

HARD RULES (no exceptions):
  - A flag is computed ONLY if its required inputs exist in the source data.
    If not, it is emitted with data_status='insufficient-data' and NO raw
    value / no severity is fabricated.
  - No lookahead: every ratio uses only data dated <= the statement period
    it claims to describe (screener/mc_fundamentals are already point-in-period
    annual filings; mc_fundamentals additionally carries available_date which
    we do not need to shift further for this module -- it is used as-is,
    consistent with 09_DATA_LAYER contract).
  - Red flags are NOT hard vetoes here (per user ruling in 08_FORENSICS_REDFLAGS.md
    "Severity model"). Each flag emits (raw_signal, base_severity 0-3, and a
    plain-English note on how size/regime should modulate it downstream in the
    scoring engine's Step 6). This module does NOT apply size/regime multipliers
    itself -- that is the scoring engine's job with market-cap + regime context
    this module does not have.

Outputs:
  results/pilot_forensic_flags.csv   -- one row per symbol x flag
  results/pilot_forensic_score.csv   -- one row per symbol, aggregate score

Run: python forensic_checks.py
"""
import re
import sys
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DATASETS = ROOT / "datasets"
PROJECT = ROOT / "ALPHA_RANKER"
RESULTS = PROJECT / "results"
RESULTS.mkdir(exist_ok=True)

PILOT = ["HDFCBANK", "ASIANPAINT", "NESTLEIND", "TATASTEEL", "HINDALCO",
         "MARUTI", "TCS", "INFY", "GRAVITA", "SHAKTIPUMP"]

# Financial-institution symbols in the pilot: several standard non-financial
# forensic ratios (interest-cover, net-debt/EBITDA, COGS-based gross margin)
# are not meaningful for a bank's balance sheet and are marked not-applicable
# rather than computed on numbers that don't mean what they'd mean for an
# industrial company.
BANKS = {"HDFCBANK"}

FLAG_ROWS = []  # accumulator of dicts -> pilot_forensic_flags.csv


def add_flag(symbol, category, flag, raw_value, years_used, base_severity,
             data_status, badness, modulation_note, source):
    """One row per symbol x flag. badness in [0,1] or None. base_severity 0-3."""
    flag_points = None
    if data_status == "ok" and badness is not None:
        flag_points = round(base_severity * badness, 3)
    FLAG_ROWS.append(dict(
        symbol=symbol, category=category, flag=flag,
        raw_value=raw_value, years_used=years_used,
        base_severity=base_severity if data_status == "ok" else None,
        data_status=data_status,
        badness=round(badness, 3) if (data_status == "ok" and badness is not None) else None,
        flag_points=flag_points,
        modulation_note=modulation_note,
        source=source,
    ))


def clip01(x, lo, hi):
    """Linear badness map: <=lo -> 0, >=hi -> 1 (or reversed if hi<lo)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if lo == hi:
        return 0.0
    v = (x - lo) / (hi - lo)
    return float(np.clip(v, 0.0, 1.0))


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------
def parse_num(v):
    """Screener cells are strings like '1,847' / '-2,772' / '62%' / '' / NaN."""
    if v is None:
        return np.nan
    if isinstance(v, float) and np.isnan(v):
        return np.nan
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return np.nan
    pct = s.endswith("%")
    s = s.replace("%", "").replace(",", "").strip()
    if s in ("", "-"):
        return np.nan
    try:
        x = float(s)
    except ValueError:
        return np.nan
    return x / 100.0 if pct else x


YEAR_RE = re.compile(r"^Mar (\d{4})$")


def load_screener_pivot(fname):
    """Return dict[symbol][metric] -> pd.Series indexed by int fiscal year (Mar-end)."""
    df = pd.read_parquet(DATASETS / "screener_deep" / fname)
    year_cols = [c for c in df.columns if YEAR_RE.match(c)]
    out = {}
    for sym, g in df[df.symbol.isin(PILOT)].groupby("symbol"):
        metrics = {}
        for _, row in g.iterrows():
            years, vals = [], []
            for c in year_cols:
                y = int(YEAR_RE.match(c).group(1))
                v = parse_num(row[c])
                if not np.isnan(v):
                    years.append(y)
                    vals.append(v)
            if years:
                metrics[row["metric"]] = pd.Series(vals, index=years).sort_index()
        out[sym] = metrics
    return out


def load_mc_fundamentals():
    """dict[symbol][metric] -> pd.Series indexed by int fiscal year, pilot only."""
    df = pd.read_parquet(DATASETS / "earnings_pit" / "mc_fundamentals_parsed.parquet")
    df = df[df.Symbol.isin(PILOT)].copy()
    cols = ["Contingent Liabilities", "Trade Receivables", "Inventories",
            "CURRENT ASSETS", "CURRENT LIABILITIES", "Cost Of Materials Consumed",
            "Total Shareholders Funds", "Cash And Cash Equivalents",
            "Tangible Assets", "Net CashFlow From Operating Activities",
            "Profit/Loss For The Period", "Revenue From Operations [Net]",
            "Depreciation And Amortisation Expenses"]
    out = {}
    for sym, g in df.groupby("Symbol"):
        g = g.sort_values("year").drop_duplicates("year", keep="last")
        metrics = {}
        for c in cols:
            if c not in g.columns:
                continue
            s = pd.Series(g[c].values, index=g["year"].astype(int).values).dropna()
            if len(s):
                metrics[c] = s.sort_index()
        out[sym] = metrics
    return out


def load_shareholding():
    df = pd.read_parquet(DATASETS / "derived" / "shareholding_changes.parquet")
    df = df[df.symbol.isin(PILOT)].copy()
    df["quarter_end"] = pd.to_datetime(df["quarter_end"])
    out = {}
    for sym, g in df.groupby("symbol"):
        out[sym] = g.sort_values("quarter_end").reset_index(drop=True)
    return out


print("Loading screener_deep (balance sheet / cash flow / annual P&L)...")
BS = load_screener_pivot("screener_balance_sheet.parquet")
CF = load_screener_pivot("screener_cash_flow.parquet")
PL = load_screener_pivot("screener_annual_pl.parquet")
print("Loading mc_fundamentals_parsed (contingent liab / receivables / inventory)...")
MC = load_mc_fundamentals()
print("Loading shareholding_changes (promoter holding)...")
SH = load_shareholding()

# metric aliases: non-bank vs bank naming differs in screener
REV_KEYS = ["Sales+", "Revenue+"]
OP_KEYS = ["Operating Profit", "Financing Profit"]
BORROW_KEYS = ["Borrowings+", "Borrowing"]


def get_metric(d, keys):
    for k in keys:
        if k in d:
            return d[k]
    return None


# ---------------------------------------------------------------------------
# Per-symbol flag computation
# ---------------------------------------------------------------------------
for sym in PILOT:
    is_bank = sym in BANKS
    bs, cf, pl = BS.get(sym, {}), CF.get(sym, {}), PL.get(sym, {})
    mc = MC.get(sym, {})
    sh = SH.get(sym)

    have_core = bool(bs) and bool(cf) and bool(pl)

    pat = get_metric(pl, ["Net Profit+"])
    cfo = get_metric(cf, ["Cash from Operating Activity+"])
    ta = bs.get("Total Assets")
    op = get_metric(pl, OP_KEYS)
    rev = get_metric(pl, REV_KEYS)
    interest = pl.get("Interest")
    borrow = get_metric(bs, BORROW_KEYS)
    other_income = pl.get("Other Income+")
    pbt = pl.get("Profit before tax")
    tax_pct = pl.get("Tax %")

    # ---- A. Accruals quality --------------------------------------------
    # A1. CFO vs PAT divergence, multi-year (spec: "3-5y")
    if pat is not None and cfo is not None:
        common = sorted(set(pat.index) & set(cfo.index))
        common = [y for y in common if abs(pat[y]) > 1e-6]
        recent = [y for y in common if y >= (max(common) - 4)] if common else []
        if len(recent) >= 3:
            gaps = [(pat[y] - cfo[y]) / abs(pat[y]) for y in recent]
            avg_gap = float(np.mean(gaps))
            badness = clip01(avg_gap, 0.0, 0.5)
            add_flag(sym, "accruals", "cfo_pat_divergence_multiyear",
                      round(avg_gap, 3), f"{min(recent)}-{max(recent)}", 2, "ok", badness,
                      "Persistent PAT-without-cash is a stronger flag on a microcap/leveraged "
                      "name than on a large-cap with deep cash reserves; escalate in credit-scare "
                      "or high-growth-guided regimes where the market is pricing cash conversion.",
                      "screener_annual_pl.Net Profit+, screener_cash_flow.Cash from Operating Activity+")
        else:
            add_flag(sym, "accruals", "cfo_pat_divergence_multiyear", None, None, 2,
                      "insufficient-data", None,
                      "Needs >=3 years of overlapping PAT and CFO with non-trivial PAT.",
                      "screener_annual_pl / screener_cash_flow")
    else:
        add_flag(sym, "accruals", "cfo_pat_divergence_multiyear", None, None, 2,
                  "insufficient-data", None, "PAT or CFO series absent for this symbol.",
                  "screener_annual_pl / screener_cash_flow")

    # A2. Sloan accruals proxy: (PAT-CFO)/avg(Total Assets), most recent year.
    # NOTE: true Sloan uses delta-working-capital; this dataset's screener BS
    # is a compact schema with NO current-asset/current-liability split, and
    # mc_fundamentals' CURRENT ASSETS/CURRENT LIABILITIES columns are populated
    # for only 99/3968 rows firm-wide (0 for this pilot) -- so the classic
    # NWC-decomposed Sloan accrual is genuinely insufficient-data here. We
    # report the well-known asset-scaled (NI-CFO)/TotalAssets proxy instead
    # and say so explicitly, rather than fabricate a NWC delta.
    if pat is not None and cfo is not None and ta is not None:
        common = sorted(set(pat.index) & set(cfo.index) & set(ta.index))
        if len(common) >= 2:
            y1, y0 = common[-1], common[-2]
            avg_ta = (ta[y1] + ta[y0]) / 2.0
            if avg_ta > 0:
                accr = (pat[y1] - cfo[y1]) / avg_ta
                badness = clip01(accr, 0.0, 0.10)
                add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy",
                          round(accr, 4), str(y1), 2, "ok", badness,
                          "This is the asset-scaled proxy, NOT the classic Sloan "
                          "delta-working-capital decomposition -- current-asset/liability "
                          "split is not available in screener_deep or mc_fundamentals for "
                          "this pilot (mc_fundamentals CURRENT ASSETS populated 99/3968 rows "
                          "firm-wide, 0 for this pilot). High accrual ratio on a small/illiquid "
                          "name deserves materially more weight than the same ratio on a "
                          "mega-cap compounder.",
                          "screener_annual_pl.Net Profit+, screener_cash_flow.CFO, screener_balance_sheet.Total Assets")
            else:
                add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy", None, None, 2,
                          "insufficient-data", None, "Total assets <= 0.", "screener_balance_sheet")
        else:
            add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy", None, None, 2,
                      "insufficient-data", None, "Need >=2 overlapping years of PAT/CFO/Total Assets.",
                      "screener_annual_pl / screener_cash_flow / screener_balance_sheet")
    else:
        add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy", None, None, 2,
                  "insufficient-data", None, "PAT, CFO or Total Assets series absent.",
                  "screener_annual_pl / screener_cash_flow / screener_balance_sheet")

    # A3. Cash conversion: CFO/EBITDA-proxy (Operating Profit), avg last <=3y.
    if not is_bank and cfo is not None and op is not None:
        common = sorted(set(cfo.index) & set(op.index))
        recent = [y for y in common if y >= (max(common) - 2)] if common else []
        recent = [y for y in recent if abs(op[y]) > 1e-6]
        if len(recent) >= 2:
            ratios = [cfo[y] / op[y] for y in recent]
            avg_ratio = float(np.mean(ratios))
            badness = clip01(avg_ratio, 1.0, 0.3)  # reversed: high ratio = good = 0 badness
            add_flag(sym, "accruals", "cash_conversion_cfo_ebitda",
                      round(avg_ratio, 3), f"{min(recent)}-{max(recent)}", 1, "ok", badness,
                      "Weak cash conversion is more forgivable in a capex/build-out phase "
                      "(industrials/capex-cycle names) than in an asset-light business (IT/FMCG) "
                      "that should be converting near 1x; check regime (credit availability) too.",
                      "screener_cash_flow.CFO, screener_annual_pl.Operating Profit")
        else:
            add_flag(sym, "accruals", "cash_conversion_cfo_ebitda", None, None, 1,
                      "insufficient-data", None, "Need >=2 overlapping years of CFO/Operating Profit.",
                      "screener_cash_flow / screener_annual_pl")
    else:
        add_flag(sym, "accruals", "cash_conversion_cfo_ebitda", None, None, 1,
                  "not-applicable" if is_bank else "insufficient-data", None,
                  "Bank: 'Operating Profit' EBITDA proxy is not meaningful for a financial "
                  "institution's income statement (net-interest-income model)." if is_bank
                  else "CFO or Operating Profit series absent.",
                  "screener_cash_flow / screener_annual_pl")

    # ---- B. Earnings quality ---------------------------------------------
    # B1. Other-income dependence: OtherIncome / PBT, latest year.
    if other_income is not None and pbt is not None:
        common = sorted(set(other_income.index) & set(pbt.index))
        common = [y for y in common if abs(pbt[y]) > 1e-6]
        if common:
            y = common[-1]
            ratio = other_income[y] / pbt[y]
            badness = clip01(ratio, 0.10, 0.50)
            note = ("For HDFCBANK, 'Other Income' is core fee/treasury income, not a one-off -- "
                    "the standard non-financial-company threshold does NOT apply; flag reported "
                    "for completeness only, treat as not-applicable in scoring." if is_bank else
                    "High other-income dependence matters much more for a name trading on an "
                    "'operating momentum' narrative/premium multiple than for a conglomerate with "
                    "disclosed treasury income as a stable, recurring line.")
            add_flag(sym, "earnings_quality", "other_income_dependence",
                      round(ratio, 3), str(y), (1 if is_bank else 1), "ok", (0.0 if is_bank else badness),
                      note, "screener_annual_pl.Other Income+, Profit before tax")
        else:
            add_flag(sym, "earnings_quality", "other_income_dependence", None, None, 1,
                      "insufficient-data", None, "PBT near zero in all overlapping years.",
                      "screener_annual_pl")
    else:
        add_flag(sym, "earnings_quality", "other_income_dependence", None, None, 1,
                  "insufficient-data", None, "Other Income or PBT series absent.", "screener_annual_pl")

    # B2. Tax-rate anomaly: level vs ~25% post-2019 statutory reference + volatility.
    if tax_pct is not None and len(tax_pct) >= 3:
        recent = tax_pct[tax_pct.index >= (tax_pct.index.max() - 4)]
        level = float(recent.mean())
        vol = float(recent.std()) if len(recent) >= 2 else 0.0
        level_badness = clip01(abs(level - 0.25), 0.05, 0.25)
        vol_badness = clip01(vol, 0.03, 0.15)
        badness = float(np.clip(0.5 * level_badness + 0.5 * vol_badness, 0, 1))
        add_flag(sym, "earnings_quality", "tax_rate_anomaly",
                  f"mean={level:.3f},std={vol:.3f}", f"{recent.index.min()}-{recent.index.max()}",
                  1, "ok", badness,
                  "An unusually low/volatile effective tax rate is a mild flag alone (many "
                  "legitimate causes: SEZ benefits, MAT credit, one-off deferred-tax reversal) "
                  "-- weight up only if it co-occurs with other earnings-quality flags or the "
                  "company is aggressively guided/expensive.",
                  "screener_annual_pl.Tax %")
    else:
        add_flag(sym, "earnings_quality", "tax_rate_anomaly", None, None, 1,
                  "insufficient-data", None, "Need >=3 years of Tax % data.", "screener_annual_pl")

    # B3 / B4. Receivables-growth vs Sales-growth, and Inventory-growth vs Sales
    # (needs mc_fundamentals for Trade Receivables / Inventories -- sparse, non-contiguous years)
    for label, mc_key, sev in [("receivables_growth_vs_sales_growth", "Trade Receivables", 2.0),
                                ("inventory_growth_vs_sales_growth", "Inventories", 1.5)]:
        series = mc.get(mc_key)
        if series is not None and rev is not None:
            yrs = sorted(series.index)
            consec = [(y0, y1) for y0, y1 in zip(yrs, yrs[1:]) if y1 - y0 == 1
                      and y0 in rev.index and y1 in rev.index and rev[y0] > 0 and series[y0] > 0]
            if consec:
                y0, y1 = consec[-1]
                item_g = series[y1] / series[y0] - 1.0
                sales_g = rev[y1] / rev[y0] - 1.0
                divergence = item_g - sales_g
                badness = clip01(divergence, 0.0, 0.30)
                add_flag(sym, "earnings_quality", label, round(divergence, 3), f"{y0}->{y1}",
                          sev, "ok", badness,
                          "Receivables/inventory outrunning sales is a genuine revenue-recognition "
                          "or channel-stuffing tell -- much more serious for a company already "
                          "guiding aggressive growth or trading at a growth premium than for a "
                          "cheap, slow-grower where it may just reflect one lumpy order.",
                          f"mc_fundamentals_parsed.{mc_key}, screener_annual_pl.{'Sales+' if 'Sales+' in pl else 'Revenue+'}")
            else:
                add_flag(sym, "earnings_quality", label, None, None, sev,
                          "insufficient-data", None,
                          f"No consecutive-year pair with positive {mc_key}/Sales found in "
                          "mc_fundamentals (coverage is sparse/non-contiguous for this symbol).",
                          "mc_fundamentals_parsed / screener_annual_pl")
        else:
            add_flag(sym, "earnings_quality", label, None, None, sev,
                      "insufficient-data", None,
                      f"{mc_key} not present in mc_fundamentals_parsed for this symbol.",
                      "mc_fundamentals_parsed")

    # ---- C. Beneish M-score components (report what's computable only) ---
    # SGI: Sales_t / Sales_{t-1}, most recent pair, from screener (best coverage)
    if rev is not None and len(rev) >= 2:
        y1, y0 = rev.index[-1], rev.index[-2]
        if rev[y0] > 0:
            sgi = rev[y1] / rev[y0]
            badness = clip01(sgi, 1.0, 1.6)
            add_flag(sym, "beneish", "SGI_sales_growth_index", round(sgi, 3), f"{y0}->{y1}", 1.5,
                      "ok", badness,
                      "High SGI alone is not manipulation -- it is a genuine growth-company "
                      "artifact of the Beneish model. Weight it up only in combination with "
                      "DSRI/accruals flags, and more so for a name already priced for that growth.",
                      "screener_annual_pl.Sales+/Revenue+")
        else:
            add_flag(sym, "beneish", "SGI_sales_growth_index", None, None, 1.5,
                      "insufficient-data", None, "Prior-year sales <= 0.", "screener_annual_pl")
    else:
        add_flag(sym, "beneish", "SGI_sales_growth_index", None, None, 1.5,
                  "insufficient-data", None, "Need >=2 years of sales/revenue.", "screener_annual_pl")

    # TATA: (PAT-CFO)/TotalAssets_t (shares math with Sloan proxy above; reported
    # separately as the named Beneish component per spec).
    if pat is not None and cfo is not None and ta is not None:
        common = sorted(set(pat.index) & set(cfo.index) & set(ta.index))
        if common and ta[common[-1]] > 0:
            y = common[-1]
            tata = (pat[y] - cfo[y]) / ta[y]
            badness = clip01(tata, 0.0, 0.10)
            add_flag(sym, "beneish", "TATA_total_accruals_to_assets", round(tata, 4), str(y), 1.5,
                      "ok", badness,
                      "Same underlying math as the Sloan asset-scaled proxy above -- "
                      "shown separately because it is a named Beneish input. Treat the two "
                      "rows as one signal, not two independent ones, when aggregating by hand.",
                      "screener_annual_pl.Net Profit+, screener_cash_flow.CFO, screener_balance_sheet.Total Assets")
        else:
            add_flag(sym, "beneish", "TATA_total_accruals_to_assets", None, None, 1.5,
                      "insufficient-data", None, "No overlapping year with positive Total Assets.",
                      "screener_annual_pl / screener_cash_flow / screener_balance_sheet")
    else:
        add_flag(sym, "beneish", "TATA_total_accruals_to_assets", None, None, 1.5,
                  "insufficient-data", None, "PAT, CFO or Total Assets series absent.",
                  "screener_annual_pl / screener_cash_flow / screener_balance_sheet")

    # DSRI: (Receivables_t/Sales_t)/(Receivables_{t-1}/Sales_{t-1}) -- needs
    # mc_fundamentals receivables, consecutive years.
    recv = mc.get("Trade Receivables")
    if recv is not None and rev is not None:
        yrs = sorted(recv.index)
        consec = [(y0, y1) for y0, y1 in zip(yrs, yrs[1:]) if y1 - y0 == 1
                  and y0 in rev.index and y1 in rev.index and rev[y0] > 0 and rev[y1] > 0]
        if consec:
            y0, y1 = consec[-1]
            dsri = (recv[y1] / rev[y1]) / (recv[y0] / rev[y0])
            badness = clip01(dsri, 1.0, 1.5)
            add_flag(sym, "beneish", "DSRI_days_sales_receivables_index", round(dsri, 3), f"{y0}->{y1}",
                      2.0, "ok", badness,
                      "DSRI>1 rising is the single most predictive Beneish component in the "
                      "original study -- weight it up if it co-occurs with high SGI (growth "
                      "story) or if the company is a serial 'growth at any cost' promoter type.",
                      "mc_fundamentals_parsed.Trade Receivables, screener_annual_pl.Sales+/Revenue+")
        else:
            add_flag(sym, "beneish", "DSRI_days_sales_receivables_index", None, None, 2.0,
                      "insufficient-data", None,
                      "No consecutive-year receivables/sales pair in mc_fundamentals for this symbol.",
                      "mc_fundamentals_parsed / screener_annual_pl")
    else:
        add_flag(sym, "beneish", "DSRI_days_sales_receivables_index", None, None, 2.0,
                  "insufficient-data", None, "Trade Receivables not in mc_fundamentals_parsed for this symbol.",
                  "mc_fundamentals_parsed")

    # GMI: prior-year gross margin / current-year gross margin, using COGS =
    # Cost Of Materials Consumed (mc_fundamentals) -- not meaningful for a bank.
    cogs = mc.get("Cost Of Materials Consumed")
    if is_bank:
        add_flag(sym, "beneish", "GMI_gross_margin_index", None, None, 1.0,
                  "not-applicable", None,
                  "Bank: no 'cost of materials'/COGS concept applies to a financial institution's "
                  "income statement.", "mc_fundamentals_parsed.Cost Of Materials Consumed")
    elif cogs is not None and rev is not None:
        yrs = sorted(set(cogs.index) & set(rev.index))
        pairs = [(y0, y1) for y0, y1 in zip(yrs, yrs[1:]) if y1 - y0 == 1 and rev[y0] > 0 and rev[y1] > 0]
        if pairs:
            y0, y1 = pairs[-1]
            gm0 = (rev[y0] - cogs[y0]) / rev[y0]
            gm1 = (rev[y1] - cogs[y1]) / rev[y1]
            if gm1 != 0:
                gmi = gm0 / gm1
                badness = clip01(gmi, 1.0, 1.3)
                add_flag(sym, "beneish", "GMI_gross_margin_index", round(gmi, 3), f"{y0}->{y1}", 1.0,
                          "ok", badness,
                          "Deteriorating gross margin (GMI>1) creates an incentive to manipulate "
                          "earnings elsewhere -- context matters: a genuine input-cost cycle "
                          "(commodity names like TATASTEEL/HINDALCO) explains this cleanly without "
                          "implying manipulation; treat as a co-factor, not standalone.",
                          "mc_fundamentals_parsed.Cost Of Materials Consumed, screener_annual_pl.Sales+/Revenue+")
            else:
                add_flag(sym, "beneish", "GMI_gross_margin_index", None, None, 1.0,
                          "insufficient-data", None, "Current-year gross margin = 0.",
                          "mc_fundamentals_parsed / screener_annual_pl")
        else:
            add_flag(sym, "beneish", "GMI_gross_margin_index", None, None, 1.0,
                      "insufficient-data", None,
                      "No consecutive-year COGS/Sales pair in mc_fundamentals for this symbol.",
                      "mc_fundamentals_parsed / screener_annual_pl")
    else:
        add_flag(sym, "beneish", "GMI_gross_margin_index", None, None, 1.0,
                  "insufficient-data", None, "Cost Of Materials Consumed not in mc_fundamentals_parsed.",
                  "mc_fundamentals_parsed")

    # AQI: needs CURRENT ASSETS split, which is populated in 99/3968 rows
    # firm-wide (0 for this pilot symbol-year set) -- genuinely insufficient.
    add_flag(sym, "beneish", "AQI_asset_quality_index", None, None, 1.5,
              "insufficient-data", None,
              "Requires a Current-Assets/PPE split; mc_fundamentals_parsed 'CURRENT ASSETS' is "
              "populated for only 99/3968 rows firm-wide and 0 rows for this pilot's symbol-years. "
              "screener_deep balance sheet has no current-asset breakdown at all (compact schema). "
              "No proxy computed -- would require fabricating a current/non-current split.",
              "mc_fundamentals_parsed.CURRENT ASSETS (absent)")

    # Composite M-score: explicitly NOT computed (would need DEPI/SGAI/LVGI too).
    add_flag(sym, "beneish", "beneish_M_score_composite", None, None, None,
              "insufficient-data", None,
              "Composite M-score requires 8 inputs (DSRI,GMI,AQI,SGI,DEPI,SGAI,LVGI,TATA). "
              "AQI is insufficient-data (see above) and DEPI/SGAI/LVGI have no source columns "
              "in screener_deep or mc_fundamentals_parsed at all. Reporting standalone components "
              "only (DSRI/GMI/SGI/TATA where computable) rather than a fabricated composite.",
              "n/a")

    # ---- D. Balance-sheet stress ------------------------------------------
    # D1. Interest coverage trend (not meaningful for a bank).
    if is_bank:
        add_flag(sym, "balance_sheet", "interest_cover_trend", None, None, 2,
                  "not-applicable", None,
                  "Bank: interest expense is a core funding cost (deposits/borrowings), not debt "
                  "service on top of an operating business -- 'interest coverage' as used for a "
                  "non-financial company does not apply. Use NIM/CAR/NPA-based metrics instead "
                  "(not available in current datasets).", "screener_annual_pl")
    elif op is not None and interest is not None:
        common = sorted(set(op.index) & set(interest.index))
        common = [y for y in common if interest[y] > 1e-6]
        if len(common) >= 3:
            recent = common[-3:]
            covers = [op[y] / interest[y] for y in recent]
            trend = covers[-1] - covers[0]
            level = covers[-1]
            level_badness = clip01(level, 8.0, 1.0)  # reversed: low cover = bad
            trend_badness = clip01(trend, 0.0, -5.0)  # reversed: falling cover = bad
            badness = float(np.clip(0.6 * level_badness + 0.4 * trend_badness, 0, 1))
            add_flag(sym, "balance_sheet", "interest_cover_trend",
                      f"level={level:.2f}x,3y_chg={trend:+.2f}x", f"{recent[0]}-{recent[-1]}", 2,
                      "ok", badness,
                      "A deteriorating interest cover is far more dangerous for a leveraged "
                      "microcap in a rising-rate/credit-scare regime than for an under-levered "
                      "large-cap -- this is the textbook size x regime modulation case from the "
                      "08 doc's severity model.",
                      "screener_annual_pl.Operating Profit/Financing Profit, Interest")
        else:
            add_flag(sym, "balance_sheet", "interest_cover_trend", None, None, 2,
                      "insufficient-data", None, "Need >=3 years of Operating Profit & non-zero Interest.",
                      "screener_annual_pl")
    else:
        add_flag(sym, "balance_sheet", "interest_cover_trend", None, None, 2,
                  "insufficient-data", None, "Operating Profit or Interest series absent.",
                  "screener_annual_pl")

    # D2. Net-debt/EBITDA rising (gross-debt fallback if cash unavailable; labeled honestly).
    if is_bank:
        add_flag(sym, "balance_sheet", "debt_to_ebitda_trend", None, None, 2,
                  "not-applicable", None,
                  "Bank: deposits/borrowings ARE the business (funding the loan book) -- "
                  "debt/EBITDA is not a meaningful leverage metric for a financial institution.",
                  "screener_balance_sheet")
    elif borrow is not None and op is not None:
        cash = mc.get("Cash And Cash Equivalents")
        common = sorted(set(borrow.index) & set(op.index))
        common = [y for y in common if op[y] > 1e-6]
        if len(common) >= 2:
            y1, y0 = common[-1], common[-2]
            if cash is not None and y1 in cash.index and y0 in cash.index:
                nd1 = borrow[y1] - cash[y1]
                nd0 = borrow[y0] - cash[y0]
                label = "net_debt"
            else:
                nd1, nd0 = borrow[y1], borrow[y0]
                label = "gross_debt (cash unavailable in mc_fundamentals for this symbol/year)"
            r1, r0 = nd1 / op[y1], nd0 / op[y0]
            badness = clip01(max(r1, 0), 1.0, 4.0)
            trend_up = r1 > r0
            add_flag(sym, "balance_sheet", "debt_to_ebitda_trend",
                      f"{label}: {y0}={r0:.2f}x -> {y1}={r1:.2f}x", f"{y0}->{y1}", 2, "ok",
                      badness if trend_up or badness > 0.5 else badness * 0.7,
                      "Rising leverage/EBITDA is a survival-threatening flag for a small/cyclical "
                      "name in a tightening-credit regime; largely cosmetic for a large-cap with "
                      "abundant refinancing access in an easy-credit regime.",
                      "screener_balance_sheet.Borrowings+/Borrowing, screener_annual_pl.Operating Profit, "
                      "mc_fundamentals_parsed.Cash And Cash Equivalents")
        else:
            add_flag(sym, "balance_sheet", "debt_to_ebitda_trend", None, None, 2,
                      "insufficient-data", None, "Need >=2 years of Borrowings & positive Operating Profit.",
                      "screener_balance_sheet / screener_annual_pl")
    else:
        add_flag(sym, "balance_sheet", "debt_to_ebitda_trend", None, None, 2,
                  "insufficient-data", None, "Borrowings or Operating Profit series absent.",
                  "screener_balance_sheet / screener_annual_pl")

    # D3. Contingent liabilities / net worth, latest available year.
    cl = mc.get("Contingent Liabilities")
    nw = mc.get("Total Shareholders Funds")
    if cl is not None and nw is not None:
        common = sorted(set(cl.index) & set(nw.index))
        common = [y for y in common if nw[y] > 0]
        if common:
            y = common[-1]
            ratio = cl[y] / nw[y]
            badness = clip01(ratio, 0.10, 0.75)
            add_flag(sym, "balance_sheet", "contingent_liabilities_to_networth",
                      round(ratio, 3), str(y), 2, "ok", badness,
                      "A large contingent-liability overhang (guarantees, disputed tax demands) is "
                      "existential risk for a thinly-capitalized microcap and a rounding error for "
                      "a cash-rich large-cap -- classic size_mult case.",
                      "mc_fundamentals_parsed.Contingent Liabilities, Total Shareholders Funds")
        else:
            add_flag(sym, "balance_sheet", "contingent_liabilities_to_networth", None, None, 2,
                      "insufficient-data", None, "No year with positive net worth.",
                      "mc_fundamentals_parsed")
    else:
        add_flag(sym, "balance_sheet", "contingent_liabilities_to_networth", None, None, 2,
                  "insufficient-data", None,
                  "Contingent Liabilities or Total Shareholders Funds not in mc_fundamentals_parsed "
                  "for this symbol.", "mc_fundamentals_parsed")

    # ---- E. Promoter holding & pledge --------------------------------------
    # KNOWN DATA-QUALITY CAVEAT: datasets/derived/shareholding_changes.parquet
    # is stale firm-wide -- max quarter_end across the ENTIRE dataset (not just
    # this pilot) is 2023-12-01 (verified by direct query), i.e. ~2.5 years
    # old as of today (2026-07-16). Every promoter-holding row below is a
    # historical snapshot, not current positioning -- flagged explicitly so
    # the scoring engine does not treat it as live.
    STALE_CUTOFF = pd.Timestamp("2025-01-01")
    if sh is not None and len(sh) >= 2:
        last = sh.iloc[-1]
        holding = last["Promoters"]
        yoy = last["Promoters_yoy"]
        qend = last["quarter_end"]
        stale_note = (f"[DATA] STALE: latest promoter-holding data point available firm-wide is "
                       f"{qend.date()} (~{(pd.Timestamp('2026-07-16')-qend).days//30} months old as "
                       f"of 2026-07-16, per datasets/derived/shareholding_changes.parquet max "
                       f"quarter_end). Treat as historical context only, not current positioning. ")
        merger_note = ""
        if sym == "HDFCBANK" and pd.notna(yoy) and yoy < -10:
            merger_note = ("[INFERENCE] This -25.6pp jump to 0.00% in 2023-09 coincides with the "
                            "HDFC Ltd -> HDFCBANK reverse-merger (completed Jul-2023) and is very "
                            "likely a promoter-classification reclassification artifact (HDFCBANK "
                            "is a widely-held bank with no controlling promoter post-merger), NOT "
                            "organic promoter selling -- verify against the actual merger scheme "
                            "before treating this as a governance red flag. ")
        badness = clip01(-yoy if pd.notna(yoy) else None, 0.0, 5.0)  # falling holding = bad
        add_flag(sym, "promoter", "promoter_holding_level_and_yoy_change",
                  f"holding={holding:.2f}%, yoy_chg={yoy:+.2f}pp" if pd.notna(yoy) else f"holding={holding:.2f}%",
                  str(qend.date()), 2,
                  "ok" if pd.notna(yoy) else "insufficient-data", badness,
                  stale_note + merger_note +
                  "Falling promoter holding is a much sharper tell on an overvalued, "
                  "high-conviction-narrative small/microcap in a risk-off regime than a modest "
                  "trim by a diversified large-cap promoter family in a bull run -- do not treat "
                  "as automatically bearish without checking size/regime/reason (e.g. estate "
                  "planning, block deal to a DII, or the merger artifact above).",
                  "datasets/derived/shareholding_changes.parquet")
    else:
        add_flag(sym, "promoter", "promoter_holding_level_and_yoy_change", None, None, 2,
                  "insufficient-data", None, "No shareholding history for this symbol.",
                  "datasets/derived/shareholding_changes.parquet")

    # Pledge: no column in any dataset checked (shareholding_changes.parquet,
    # quarterly/yearly_shareholding.parquet, screener_dump_20260704/screener/
    # excel_reports/ is EMPTY -- 0 files). Explicit insufficient-data hook.
    add_flag(sym, "promoter", "promoter_pledge_pct_and_trend", None, None, 3,
              "insufficient-data", None,
              "No pledge-% column found in any checked dataset: "
              "datasets/derived/shareholding_changes.parquet, "
              "datasets/earnings_pit/quarterly_shareholding_pit.parquet, "
              "datasets/kaggle_indian_financials/{quarterly,yearly}_shareholding.parquet all lack "
              "it; datasets/screener_dump_20260704/screener/excel_reports/ exists but is EMPTY "
              "(0 files) -- the intended BSE/NSE pledge-disclosure source was never populated. "
              "Hook is ready (symbol,quarter_end,pledge_pct schema) for D-033 ingestion once a "
              "source is found. base_severity=3 reflects the 08 doc's ranking of pledge as one "
              "of the more serious heavy-penalty flags once data exists -- NOT computed here.",
              "none found -- see note")

print(f"Computed {len(FLAG_ROWS)} flag rows across {len(PILOT)} symbols.")

flags_df = pd.DataFrame(FLAG_ROWS)
flags_path = RESULTS / "pilot_forensic_flags.csv"
flags_df.to_csv(flags_path, index=False)
print(f"Wrote {flags_path} ({len(flags_df)} rows)")

# ---------------------------------------------------------------------------
# Aggregate to Forensic-Risk score, 0-100, higher = worse.
# Base-severity-weighted average badness of flags that were actually computed
# (data_status=='ok'); NOT size/regime-adjusted -- that happens downstream in
# the scoring engine (02_SCORING_ENGINE.md Step 6). Coverage is reported
# alongside so a high score on thin coverage isn't mistaken for a thorough one.
# ---------------------------------------------------------------------------
score_rows = []
for sym, g in flags_df.groupby("symbol"):
    ok = g[g.data_status == "ok"]
    total_flags = len(g)
    n_ok = len(ok)
    n_insufficient = int((g.data_status == "insufficient-data").sum())
    n_na = int((g.data_status == "not-applicable").sum())
    denom = ok["base_severity"].sum()
    if n_ok > 0 and denom and denom > 0:
        score = 100.0 * (ok["base_severity"] * ok["badness"]).sum() / denom
    else:
        score = None
    score_rows.append(dict(
        symbol=sym,
        forensic_risk_score_0_100=round(score, 1) if score is not None else None,
        flags_computed=n_ok,
        flags_insufficient_data=n_insufficient,
        flags_not_applicable=n_na,
        flags_total=total_flags,
        coverage_pct=round(100.0 * n_ok / total_flags, 1),
        note="Base severity-weighted avg badness of flags with data (x100). NOT yet "
             "size/regime-modulated -- scoring engine Step 6 applies size_mult/regime_mult/offset "
             "per 08_FORENSICS_REDFLAGS.md before this becomes a portfolio-level penalty.",
    ))

score_df = pd.DataFrame(score_rows).sort_values("symbol")
score_path = RESULTS / "pilot_forensic_score.csv"
score_df.to_csv(score_path, index=False)
print(f"Wrote {score_path}")
print(score_df.to_string(index=False))
