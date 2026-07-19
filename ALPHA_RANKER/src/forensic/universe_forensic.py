"""
ALPHA_RANKER -- Universe-scale Forensic / Red-Flag engine (NIFTY-750).

Scales src/forensic/forensic_checks.py (10-stock pilot, screener_deep +
mc_fundamentals_parsed source) to the FULL universe using the fresh
data/fundamentals/consolidated/*.parquet tables built by
src/lib/consolidate_screener.py from data/fundamentals/screener_live/*.json
(live screener.in scrape, landing now -- 619/751 symbols consolidated as of
this run; script is written to just pick up more coverage on re-run, no
code change needed).

SCHEMA DIFFERENCES vs the pilot (screener_live is a different scrape than
screener_deep/mc_fundamentals_parsed) -- these are real, verified structural
differences, not approximations:
  - Annual columns are "<Mon> <YYYY>" (fiscal year-end month varies by
    company -- most are Mar, some Dec/Jun -- NOT assumed Mar-only like the
    pilot). Percent-metrics (OPM %, Tax %, ROE % etc.) are stored as raw
    points (62.0 == 62%), NOT pilot's /100-scaled fractions -- verified by
    direct read (360ONE OPM% Mar-2026 = 62.0).
  - Bank/NBFC-schema symbols use Revenue/Financing Profit/Deposits instead of
    Sales/Operating Profit/Borrowings -- detected PER-SYMBOL from which
    metric names are actually present (schema-driven), not from the
    Industry label (Industry=="Financial Services" also contains non-bank-
    schema names like ICICIGI which reports Operating Profit/OPM% normally).
  - `ratios` table gives Debtor Days / Inventory Days / Cash Conversion
    Cycle DIRECTLY -- the pilot had to fall back on a sparse, non-contiguous
    mc_fundamentals Trade Receivables/Inventories series for the equivalent
    checks. This is a strict data upgrade, so B3/B4 here are a Debtor/
    Inventory-DAYS trend, not a receivables/inventory-vs-sales-growth
    divergence -- noted as [INFERENCE substitution] where it stands in for
    a pilot-style Beneish component (DSRI).
  - `cash_flow` table gives CFO/OP DIRECTLY (screener's own cash-conversion
    ratio) -- used instead of hand-dividing CFO by an Operating-Profit proxy
    that doesn't exist for bank-schema names; this lets A3 be computed for
    banks too (screener reports CFO/OP off Financing Profit for them),
    unlike the pilot which marked cash-conversion not-applicable for banks.
  - No Contingent Liabilities, no Cash&CashEquivalents, no CURRENT ASSETS
    split anywhere in this schema -> D3 (contingent-liab/networth), the
    net-debt refinement of D2, and AQI remain genuinely insufficient-data
    (same conclusion as the pilot, for the same underlying reason: no
    source column, not a lookup bug).
  - No pledge-% column anywhere in this schema either -- same insufficient-
    data hook as the pilot, confirmed again on this new source.

HARD RULES (unchanged from pilot):
  - A flag is computed ONLY if its required inputs exist. Otherwise
    data_status='insufficient-data' (or 'not-applicable' for bank-schema
    metrics that don't mean what they'd mean for a financial institution),
    no fabricated raw value/severity.
  - No lookahead: annual figures are FY-end filings as published; shareholding
    is used as-of its own quarter_end, nothing back-filled or interpolated.
  - Red flags are NOT hard vetoes. Each flag emits (raw, base_severity 0-3,
    badness 0-1, modulation_note) for the downstream scoring engine to
    sze/regime-adjust -- this module does not apply size/regime multipliers.

Outputs:
  results/universe_forensic_flags.parquet  -- one row per symbol x flag
  results/universe_forensic_score.parquet  -- one row per symbol, aggregate

Run: python universe_forensic.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THIS = Path(__file__).resolve()
SRC = THIS.parents[1]          # ALPHA_RANKER/src
PROJECT = THIS.parents[2]      # ALPHA_RANKER
ROOT = THIS.parents[3]         # NIFTY 500 repo root

CONSOL = PROJECT / "data" / "fundamentals" / "consolidated"
UNIVERSE_CSV = PROJECT / "data" / "universe" / "nifty_total_market_750.csv"
RESULTS = PROJECT / "results"
RESULTS.mkdir(exist_ok=True, parents=True)

PERIOD_RE = re.compile(r"^([A-Za-z]{3}) (\d{4})$")  # exact match only; excludes "Mar 2023  15m" stubs

FLAG_ROWS = []  # accumulator -> universe_forensic_flags.parquet


def add_flag(symbol, category, flag, raw_value, years_used, base_severity,
             data_status, badness, modulation_note, source):
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
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    if lo == hi:
        return 0.0
    v = (x - lo) / (hi - lo)
    return float(np.clip(v, 0.0, 1.0))


def get_metric(d, keys):
    for k in keys:
        if k in d:
            return d[k]
    return None


# ---------------------------------------------------------------------------
# Loaders -- long-format consolidated parquets -> dict[symbol][metric] -> Series
# ---------------------------------------------------------------------------
def load_annual_table(fname):
    """balance_sheet / cash_flow / profit_loss / ratios: pivot to
    dict[symbol][metric] -> pd.Series indexed by fiscal-period Timestamp
    (ascending). Only exact '<Mon> <YYYY>' columns kept -- excludes 'TTM'
    and stub periods like 'Mar 2023  15m' (fiscal-year-change artifacts)."""
    path = CONSOL / fname
    if not path.exists():
        print(f"  [WARN] {fname} not found -- consolidated dir stale/empty. Run consolidate_screener.py.")
        return {}
    df = pd.read_parquet(path)
    df = df[df["period"].astype(str).str.match(PERIOD_RE)].copy()
    df["pdate"] = pd.to_datetime(df["period"], format="%b %Y", errors="coerce")
    df = df.dropna(subset=["pdate"])
    out = {}
    for sym, g in df.groupby("symbol"):
        metrics = {}
        for metric, gm in g.groupby("metric"):
            s = gm.dropna(subset=["value"]).drop_duplicates("pdate", keep="last").sort_values("pdate")
            if len(s):
                metrics[metric] = pd.Series(s["value"].values, index=s["pdate"].values)
        out[sym] = metrics
    return out


def load_shareholding():
    """dict[symbol][holder] -> pd.Series indexed by quarter_end Timestamp.
    Accepts any 3-letter-month quarter label (Jun/Sep/Dec/Mar and the odd
    off-cycle 'May 2026'/'Jul 2026' seen in the live scrape)."""
    path = CONSOL / "shareholding.parquet"
    if not path.exists():
        return {}
    df = pd.read_parquet(path)
    df = df[df["period"].astype(str).str.match(PERIOD_RE)].copy()
    df["qend"] = pd.to_datetime(df["period"], format="%b %Y", errors="coerce")
    df = df.dropna(subset=["qend"])
    out = {}
    for sym, g in df.groupby("symbol"):
        holders = {}
        for holder, gh in g.groupby("metric"):
            s = gh.dropna(subset=["value"]).drop_duplicates("qend", keep="last").sort_values("qend")
            if len(s):
                holders[holder] = pd.Series(s["value"].values, index=s["qend"].values)
        out[sym] = holders
    return out


print("Loading universe list...")
uni = pd.read_csv(UNIVERSE_CSV)
UNIVERSE = uni["Symbol"].tolist()
INDUSTRY = dict(zip(uni["Symbol"], uni["Industry"]))
print(f"  {len(UNIVERSE)} symbols in universe csv")

print("Loading consolidated annual tables (balance_sheet/cash_flow/profit_loss/ratios)...")
BS = load_annual_table("balance_sheet.parquet")
CF = load_annual_table("cash_flow.parquet")
PL = load_annual_table("profit_loss.parquet")
RT = load_annual_table("ratios.parquet")
print(f"  coverage: BS={len(BS)} CF={len(CF)} PL={len(PL)} RT={len(RT)} symbols")

print("Loading shareholding (promoter holding)...")
SH = load_shareholding()
print(f"  coverage: SH={len(SH)} symbols")

REV_KEYS = ["Sales", "Revenue"]
OP_KEYS = ["Operating Profit", "Financing Profit"]
BORROW_KEYS = ["Borrowings", "Borrowing"]
OPM_KEYS = ["OPM %", "Financing Margin %"]

N_TOTAL = len(UNIVERSE)
for i, sym in enumerate(UNIVERSE):
    if i and i % 150 == 0:
        print(f"  ... {i}/{N_TOTAL} symbols processed")

    bs, cf, pl, rt = BS.get(sym, {}), CF.get(sym, {}), PL.get(sym, {}), RT.get(sym, {})
    sh = SH.get(sym, {})

    is_bank_like = ("Financing Profit" in pl) or ("Deposits" in bs)

    pat = get_metric(pl, ["Net Profit"])
    cfo = get_metric(cf, ["Cash from Operating Activity"])
    ta = bs.get("Total Assets")
    op = get_metric(pl, OP_KEYS)
    rev = get_metric(pl, REV_KEYS)
    interest = pl.get("Interest")
    borrow = get_metric(bs, BORROW_KEYS)
    other_income = pl.get("Other Income")
    pbt = pl.get("Profit before tax")
    tax_pct = pl.get("Tax %")
    cfo_op_pct = cf.get("CFO/OP")
    debtor_days = rt.get("Debtor Days")
    inv_days = rt.get("Inventory Days")
    ccc = rt.get("Cash Conversion Cycle")
    opm = get_metric(pl, OPM_KEYS)

    # ---- A. Accruals quality ----------------------------------------------
    # A1. CFO vs PAT divergence, multi-year (last <=5 FYE with |PAT|>0).
    if pat is not None and cfo is not None:
        common = sorted(set(pat.index) & set(cfo.index))
        common = [y for y in common if abs(pat[y]) > 1e-6]
        recent = [y for y in common if y >= (max(common) - pd.DateOffset(years=5))] if common else []
        if len(recent) >= 3:
            gaps = [(pat[y] - cfo[y]) / abs(pat[y]) for y in recent]
            avg_gap = float(np.mean(gaps))
            badness = clip01(avg_gap, 0.0, 0.5)
            add_flag(sym, "accruals", "cfo_pat_divergence_multiyear",
                      round(avg_gap, 3), f"{pd.Timestamp(min(recent)).date()}-{pd.Timestamp(max(recent)).date()}",
                      2, "ok", badness,
                      "Persistent PAT-without-cash is a stronger flag on a microcap/leveraged "
                      "name than a large-cap with deep cash reserves; escalate in credit-scare "
                      "or high-growth-guided regimes.",
                      "profit_loss.Net Profit, cash_flow.Cash from Operating Activity")
        else:
            add_flag(sym, "accruals", "cfo_pat_divergence_multiyear", None, None, 2,
                      "insufficient-data", None, "Needs >=3 years of overlapping PAT and CFO with non-trivial PAT.",
                      "profit_loss / cash_flow")
    else:
        add_flag(sym, "accruals", "cfo_pat_divergence_multiyear", None, None, 2,
                  "insufficient-data", None, "PAT or CFO series absent for this symbol.",
                  "profit_loss / cash_flow")

    # A2. Sloan accruals proxy: (PAT-CFO)/avg(Total Assets), most recent year.
    # (No current-asset/liability split in this schema -> asset-scaled proxy,
    # not the classic NWC-decomposed Sloan accrual -- same limitation as pilot.)
    if pat is not None and cfo is not None and ta is not None:
        common = sorted(set(pat.index) & set(cfo.index) & set(ta.index))
        if len(common) >= 2:
            y1, y0 = common[-1], common[-2]
            avg_ta = (ta[y1] + ta[y0]) / 2.0
            if avg_ta > 0:
                accr = (pat[y1] - cfo[y1]) / avg_ta
                badness = clip01(accr, 0.0, 0.10)
                add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy",
                          round(accr, 4), str(pd.Timestamp(y1).date()), 2, "ok", badness,
                          "Asset-scaled proxy, not the classic Sloan NWC-decomposition (no "
                          "current-asset/liability split in this schema). High accrual ratio on "
                          "a small/illiquid name deserves materially more weight than on a mega-cap.",
                          "profit_loss.Net Profit, cash_flow.CFO, balance_sheet.Total Assets")
            else:
                add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy", None, None, 2,
                          "insufficient-data", None, "Total assets <= 0.", "balance_sheet")
        else:
            add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy", None, None, 2,
                      "insufficient-data", None, "Need >=2 overlapping years of PAT/CFO/Total Assets.",
                      "profit_loss / cash_flow / balance_sheet")
    else:
        add_flag(sym, "accruals", "sloan_accruals_asset_scaled_proxy", None, None, 2,
                  "insufficient-data", None, "PAT, CFO or Total Assets series absent.",
                  "profit_loss / cash_flow / balance_sheet")

    # A3. Cash conversion: screener's own CFO/OP ratio (points, e.g. 85.0=0.85x),
    # avg of last <=3 FYE. Computed for bank-schema names too -- screener
    # reports this off Financing Profit for them (unlike Operating-Profit-based
    # interest cover / debt-EBITDA below, which genuinely don't apply to banks).
    if cfo_op_pct is not None and len(cfo_op_pct) >= 1:
        recent = cfo_op_pct.sort_index().tail(3)
        avg_ratio = float(recent.mean()) / 100.0
        badness = clip01(avg_ratio, 1.0, 0.3)  # reversed: high ratio = good = 0 badness
        add_flag(sym, "accruals", "cash_conversion_cfo_op",
                  round(avg_ratio, 3), f"{pd.Timestamp(recent.index.min()).date()}-{pd.Timestamp(recent.index.max()).date()}",
                  1, "ok", badness,
                  "Weak cash conversion is more forgivable in a capex/build-out phase than in an "
                  "asset-light business that should convert near 1x; direct screener CFO/OP ratio, "
                  "computed for bank-schema names too (off Financing Profit).",
                  "cash_flow.CFO/OP")
    else:
        add_flag(sym, "accruals", "cash_conversion_cfo_op", None, None, 1,
                  "insufficient-data", None, "CFO/OP ratio absent for this symbol.", "cash_flow")

    # ---- B. Earnings quality ----------------------------------------------
    # B1. Other-income dependence: OtherIncome / PBT, latest year.
    if other_income is not None and pbt is not None:
        common = sorted(set(other_income.index) & set(pbt.index))
        common = [y for y in common if abs(pbt[y]) > 1e-6]
        if common:
            y = common[-1]
            ratio = other_income[y] / pbt[y]
            badness = clip01(ratio, 0.10, 0.50)
            note = ("Bank/NBFC-schema name: 'Other Income' can be core fee/treasury income, not a "
                    "one-off -- standard threshold doesn't apply as cleanly; flag reported for "
                    "completeness, treat as low-weight/not-applicable in scoring." if is_bank_like else
                    "High other-income dependence matters more for a name on an 'operating momentum' "
                    "narrative/premium multiple than for a conglomerate with disclosed recurring "
                    "treasury income.")
            add_flag(sym, "earnings_quality", "other_income_dependence",
                      round(ratio, 3), str(pd.Timestamp(y).date()), 1, "ok",
                      (0.0 if is_bank_like else badness), note,
                      "profit_loss.Other Income, Profit before tax")
        else:
            add_flag(sym, "earnings_quality", "other_income_dependence", None, None, 1,
                      "insufficient-data", None, "PBT near zero in all overlapping years.", "profit_loss")
    else:
        add_flag(sym, "earnings_quality", "other_income_dependence", None, None, 1,
                  "insufficient-data", None, "Other Income or PBT series absent.", "profit_loss")

    # B2. Tax-rate anomaly: level vs ~25pt statutory reference + volatility.
    # NOTE units: Tax % stored as raw points (23.0 == 23%), not /100 fraction.
    if tax_pct is not None and len(tax_pct) >= 3:
        recent = tax_pct.sort_index().tail(5)
        level = float(recent.mean())
        vol = float(recent.std()) if len(recent) >= 2 else 0.0
        level_badness = clip01(abs(level - 25.0), 5.0, 25.0)
        vol_badness = clip01(vol, 3.0, 15.0)
        badness = float(np.clip(0.5 * level_badness + 0.5 * vol_badness, 0, 1))
        add_flag(sym, "earnings_quality", "tax_rate_anomaly",
                  f"mean={level:.1f}pt,std={vol:.1f}pt",
                  f"{pd.Timestamp(recent.index.min()).date()}-{pd.Timestamp(recent.index.max()).date()}",
                  1, "ok", badness,
                  "Unusually low/volatile effective tax rate is a mild flag alone (SEZ benefits, "
                  "MAT credit, deferred-tax reversal are all legitimate) -- weight up only if it "
                  "co-occurs with other earnings-quality flags.",
                  "profit_loss.Tax %")
    else:
        add_flag(sym, "earnings_quality", "tax_rate_anomaly", None, None, 1,
                  "insufficient-data", None, "Need >=3 years of Tax % data.", "profit_loss")

    # B3/B4/B5: Debtor Days / Inventory Days / Cash Conversion Cycle trend --
    # a strict upgrade over the pilot's sparse mc_fundamentals receivables/
    # inventory series: these are DIRECT screener ratios at full coverage.
    # Not-applicable for bank-schema names (no working-capital cycle concept;
    # confirmed these rows are simply absent from `ratios` for banks/NBFCs).
    for label, series, sev, unit in [
        ("receivables_days_trend", debtor_days, 1.5, "days"),
        ("inventory_days_trend", inv_days, 1.0, "days"),
        ("cash_conversion_cycle_trend", ccc, 1.0, "days"),
    ]:
        if is_bank_like:
            add_flag(sym, "earnings_quality", label, None, None, sev, "not-applicable", None,
                      "Bank/NBFC-schema name: no receivables/inventory working-capital cycle "
                      "concept applies.", "ratios")
            continue
        if series is not None and len(series) >= 2:
            s = series.dropna().sort_index()
            if len(s) >= 3:
                latest, baseline = s.iloc[-1], float(s.iloc[-4:-1].mean())
            elif len(s) == 2:
                latest, baseline = s.iloc[-1], float(s.iloc[-2])
            else:
                latest, baseline = None, None
            if latest is not None and baseline is not None:
                if unit == "days" and label != "cash_conversion_cycle_trend":
                    if abs(baseline) > 1e-6:
                        pct = (latest - baseline) / abs(baseline)
                        badness = clip01(pct, 0.0, 0.35)
                        raw = round(pct, 3)
                    else:
                        badness, raw = None, None
                else:
                    # CCC can cross zero -- absolute day-change, not pct.
                    day_chg = latest - baseline
                    badness = clip01(day_chg, 0.0, 25.0)
                    raw = round(float(day_chg), 1)
                if raw is not None:
                    add_flag(sym, "earnings_quality", label, raw,
                              f"{pd.Timestamp(s.index[-1]).date()} vs trailing avg", sev, "ok", badness,
                              "Rising receivables/inventory days or a lengthening cash-conversion "
                              "cycle is a genuine revenue-recognition/channel-stuffing or working-"
                              "capital-stress tell -- more serious for a name guiding aggressive "
                              "growth or trading at a growth premium than for a cheap, slow-grower.",
                              "ratios.Debtor Days/Inventory Days/Cash Conversion Cycle")
                else:
                    add_flag(sym, "earnings_quality", label, None, None, sev, "insufficient-data",
                              None, "Baseline value is ~0, pct-change undefined.", "ratios")
            else:
                add_flag(sym, "earnings_quality", label, None, None, sev, "insufficient-data", None,
                          "Need >=2 years of this ratio.", "ratios")
        else:
            add_flag(sym, "earnings_quality", label, None, None, sev, "insufficient-data", None,
                      f"{label.split('_')[0].title()} series absent for this symbol.", "ratios")

    # ---- C. Beneish M-score components (report what's computable only) ----
    # SGI: Sales_t / Sales_{t-1}, most recent pair.
    if rev is not None and len(rev) >= 2:
        s = rev.sort_index()
        y1, y0 = s.index[-1], s.index[-2]
        if s[y0] > 0:
            sgi = s[y1] / s[y0]
            badness = clip01(sgi, 1.0, 1.6)
            add_flag(sym, "beneish", "SGI_sales_growth_index", round(sgi, 3),
                      f"{pd.Timestamp(y0).date()}->{pd.Timestamp(y1).date()}", 1.5, "ok", badness,
                      "High SGI alone is not manipulation -- a genuine growth-company artifact. "
                      "Weight up only combined with DSRI/accruals flags.",
                      "profit_loss.Sales/Revenue")
        else:
            add_flag(sym, "beneish", "SGI_sales_growth_index", None, None, 1.5,
                      "insufficient-data", None, "Prior-year sales <= 0.", "profit_loss")
    else:
        add_flag(sym, "beneish", "SGI_sales_growth_index", None, None, 1.5,
                  "insufficient-data", None, "Need >=2 years of sales/revenue.", "profit_loss")

    # TATA: same math as Sloan proxy, reported separately as named Beneish input.
    if pat is not None and cfo is not None and ta is not None:
        common = sorted(set(pat.index) & set(cfo.index) & set(ta.index))
        if common and ta[common[-1]] > 0:
            y = common[-1]
            tata = (pat[y] - cfo[y]) / ta[y]
            badness = clip01(tata, 0.0, 0.10)
            add_flag(sym, "beneish", "TATA_total_accruals_to_assets", round(tata, 4),
                      str(pd.Timestamp(y).date()), 1.5, "ok", badness,
                      "Same math as the Sloan asset-scaled proxy above -- treat as one signal, not two.",
                      "profit_loss.Net Profit, cash_flow.CFO, balance_sheet.Total Assets")
        else:
            add_flag(sym, "beneish", "TATA_total_accruals_to_assets", None, None, 1.5,
                      "insufficient-data", None, "No overlapping year with positive Total Assets.",
                      "profit_loss / cash_flow / balance_sheet")
    else:
        add_flag(sym, "beneish", "TATA_total_accruals_to_assets", None, None, 1.5,
                  "insufficient-data", None, "PAT, CFO or Total Assets series absent.",
                  "profit_loss / cash_flow / balance_sheet")

    # DSRI [INFERENCE substitution]: classic DSRI = (Recv_t/Sales_t)/(Recv_{t-1}/Sales_{t-1}).
    # No rupee receivables figure in this schema, but Debtor Days IS
    # proportional to Receivables/Sales*365 -- so DebtorDays_t/DebtorDays_{t-1}
    # is a valid ratio-equivalent of DSRI (the 365/Sales terms cancel).
    if is_bank_like:
        add_flag(sym, "beneish", "DSRI_days_sales_receivables_index", None, None, 2.0,
                  "not-applicable", None, "Bank/NBFC-schema: no receivables/Debtor-Days concept.",
                  "ratios")
    elif debtor_days is not None and len(debtor_days.dropna()) >= 2:
        s = debtor_days.dropna().sort_index()
        y1, y0 = s.index[-1], s.index[-2]
        if s[y0] > 1e-6:
            dsri = s[y1] / s[y0]
            badness = clip01(dsri, 1.0, 1.5)
            add_flag(sym, "beneish", "DSRI_days_sales_receivables_index", round(dsri, 3),
                      f"{pd.Timestamp(y0).date()}->{pd.Timestamp(y1).date()}", 2.0, "ok", badness,
                      "[INFERENCE substitution] Debtor-Days ratio used in place of the classic "
                      "(Receivables/Sales) ratio -- mathematically equivalent (365/Sales terms "
                      "cancel), NOT a fabricated number, just a different but exact route to the "
                      "same index using this schema's directly-reported ratio.",
                      "ratios.Debtor Days")
        else:
            add_flag(sym, "beneish", "DSRI_days_sales_receivables_index", None, None, 2.0,
                      "insufficient-data", None, "Prior-year Debtor Days ~0.", "ratios")
    else:
        add_flag(sym, "beneish", "DSRI_days_sales_receivables_index", None, None, 2.0,
                  "insufficient-data", None, "Debtor Days series absent.", "ratios")

    # GMI [INFERENCE substitution]: classic GMI = GM_{t-1}/GM_t using COGS,
    # which has NO source column in this schema (only aggregate 'Expenses').
    # OPM% (or Financing Margin % for bank-schema names) is used as the
    # margin-compression proxy instead -- the %scale cancels in the ratio.
    if opm is not None and len(opm.dropna()) >= 2:
        s = opm.dropna().sort_index()
        y1, y0 = s.index[-1], s.index[-2]
        if s[y1] != 0:
            gmi = s[y0] / s[y1]
            badness = clip01(gmi, 1.0, 1.3)
            add_flag(sym, "beneish", "GMI_gross_margin_index", round(gmi, 3),
                      f"{pd.Timestamp(y0).date()}->{pd.Timestamp(y1).date()}", 1.0, "ok", badness,
                      "[INFERENCE substitution] OPM%/Financing-Margin% used in place of a true "
                      "gross-margin (COGS-based) GMI -- this schema has no COGS/'cost of materials' "
                      "column, only aggregate 'Expenses'. Deteriorating margin (GMI>1) is a co-factor, "
                      "not standalone -- a genuine input-cost or competitive cycle explains it cleanly "
                      "without implying manipulation.",
                      "profit_loss.OPM %/Financing Margin %")
        else:
            add_flag(sym, "beneish", "GMI_gross_margin_index", None, None, 1.0,
                      "insufficient-data", None, "Current-year margin = 0.", "profit_loss")
    else:
        add_flag(sym, "beneish", "GMI_gross_margin_index", None, None, 1.0,
                  "insufficient-data", None, "OPM %/Financing Margin % series absent.", "profit_loss")

    # AQI: needs a current-assets/PPE split -- this schema's balance_sheet is
    # compact (Equity Capital/Reserves/Borrowings/Other Liabilities/Fixed
    # Assets/CWIP/Investments/Other Assets/Total Assets only), same as pilot.
    add_flag(sym, "beneish", "AQI_asset_quality_index", None, None, 1.5,
              "insufficient-data", None,
              "Requires a current-assets/PPE split; screener_live balance_sheet has no such "
              "breakdown (compact schema, same limitation as the pilot's screener_deep source). "
              "No proxy computed -- would require fabricating a current/non-current split.",
              "balance_sheet (no current-asset column)")

    # Composite M-score: explicitly NOT computed (needs DEPI/SGAI/LVGI too).
    add_flag(sym, "beneish", "beneish_M_score_composite", None, None, None,
              "insufficient-data", None,
              "Composite M-score needs 8 inputs (DSRI,GMI,AQI,SGI,DEPI,SGAI,LVGI,TATA). AQI is "
              "insufficient-data and DEPI/SGAI/LVGI have no source columns in this schema at all. "
              "Reporting standalone components only.", "n/a")

    # ---- D. Balance-sheet stress -------------------------------------------
    # D1. Interest coverage trend -- not-applicable for bank-schema names.
    if is_bank_like:
        add_flag(sym, "balance_sheet", "interest_cover_trend", None, None, 2, "not-applicable", None,
                  "Bank/NBFC-schema: interest expense is a core funding cost, not debt service on "
                  "top of an operating business -- 'interest coverage' as used for a non-financial "
                  "company doesn't apply. Would need NIM/CAR/NPA-based metrics instead (not in this "
                  "dataset).", "profit_loss")
    elif op is not None and interest is not None:
        common = sorted(set(op.index) & set(interest.index))
        common = [y for y in common if interest[y] > 1e-6]
        if len(common) >= 3:
            recent = common[-3:]
            covers = [op[y] / interest[y] for y in recent]
            trend = covers[-1] - covers[0]
            level = covers[-1]
            level_badness = clip01(level, 8.0, 1.0)
            trend_badness = clip01(trend, 0.0, -5.0)
            badness = float(np.clip(0.6 * level_badness + 0.4 * trend_badness, 0, 1))
            add_flag(sym, "balance_sheet", "interest_cover_trend",
                      f"level={level:.2f}x,3y_chg={trend:+.2f}x",
                      f"{pd.Timestamp(recent[0]).date()}-{pd.Timestamp(recent[-1]).date()}", 2, "ok", badness,
                      "Deteriorating interest cover is far more dangerous for a leveraged microcap "
                      "in a rising-rate/credit-scare regime than an under-levered large-cap.",
                      "profit_loss.Operating Profit/Financing Profit, Interest")
        else:
            add_flag(sym, "balance_sheet", "interest_cover_trend", None, None, 2,
                      "insufficient-data", None, "Need >=3 years of Operating Profit & non-zero Interest.",
                      "profit_loss")
    else:
        add_flag(sym, "balance_sheet", "interest_cover_trend", None, None, 2,
                  "insufficient-data", None, "Operating Profit or Interest series absent.", "profit_loss")

    # D2. Debt/EBITDA trend -- GROSS debt only (no cash line item exists in
    # this schema's balance_sheet at all, unlike the pilot which sometimes had
    # mc_fundamentals Cash And Cash Equivalents) -- labeled honestly.
    # Not-applicable for bank-schema names.
    if is_bank_like:
        add_flag(sym, "balance_sheet", "debt_to_ebitda_trend", None, None, 2, "not-applicable", None,
                  "Bank/NBFC-schema: deposits/borrowings ARE the business (funding the loan book) -- "
                  "debt/EBITDA is not a meaningful leverage metric.", "balance_sheet")
    elif borrow is not None and op is not None:
        common = sorted(set(borrow.index) & set(op.index))
        common = [y for y in common if op[y] > 1e-6]
        if len(common) >= 2:
            y1, y0 = common[-1], common[-2]
            r1, r0 = borrow[y1] / op[y1], borrow[y0] / op[y0]
            badness = clip01(max(r1, 0), 1.0, 4.0)
            trend_up = r1 > r0
            add_flag(sym, "balance_sheet", "debt_to_ebitda_trend",
                      f"gross_debt (no cash line item in this schema): {pd.Timestamp(y0).date()}={r0:.2f}x -> "
                      f"{pd.Timestamp(y1).date()}={r1:.2f}x",
                      f"{pd.Timestamp(y0).date()}->{pd.Timestamp(y1).date()}", 2, "ok",
                      badness if trend_up or badness > 0.5 else badness * 0.7,
                      "Rising leverage/EBITDA is survival-threatening for a small/cyclical name in a "
                      "tightening-credit regime; largely cosmetic for a large-cap with abundant "
                      "refinancing access.",
                      "balance_sheet.Borrowings/Borrowing, profit_loss.Operating Profit")
        else:
            add_flag(sym, "balance_sheet", "debt_to_ebitda_trend", None, None, 2,
                      "insufficient-data", None, "Need >=2 years of Borrowings & positive Operating Profit.",
                      "balance_sheet / profit_loss")
    else:
        add_flag(sym, "balance_sheet", "debt_to_ebitda_trend", None, None, 2,
                  "insufficient-data", None, "Borrowings or Operating Profit series absent.",
                  "balance_sheet / profit_loss")

    # D3. Contingent liabilities / net worth -- no such column anywhere in
    # this schema (verified: balance_sheet metric set has no Contingent
    # Liabilities line; no equivalent table either). Explicit hook.
    add_flag(sym, "balance_sheet", "contingent_liabilities_to_networth", None, None, 2,
              "insufficient-data", None,
              "No Contingent Liabilities column in screener_live balance_sheet/profit_loss/ratios "
              "for any symbol checked -- same conclusion as the pilot (mc_fundamentals had it sparsely; "
              "this scrape doesn't carry it at all). Hook ready if a source is found.",
              "none found in this schema")

    # ---- E. Promoter holding & pledge --------------------------------------
    # FRESH data: shareholding lands to Mar/Jun/Jul-2026 in this scrape --
    # no staleness caveat needed (unlike the pilot's ~2.5yr-stale source).
    promo = sh.get("Promoters")
    if promo is not None and len(promo.dropna()) >= 2:
        s = promo.dropna().sort_index()
        latest_q, latest_v = s.index[-1], s.iloc[-1]
        # find a quarter ~12mo (365d +-45d) prior for YoY.
        target = pd.Timestamp(latest_q) - pd.Timedelta(days=365)
        candidates = s[(s.index >= target - pd.Timedelta(days=45)) & (s.index <= target + pd.Timedelta(days=45))]
        if len(candidates):
            prior_v = float(candidates.iloc[-1])
            yoy = latest_v - prior_v
            badness = clip01(-yoy, 0.0, 5.0)  # falling holding = bad
            add_flag(sym, "promoter", "promoter_holding_level_and_yoy_change",
                      f"holding={latest_v:.2f}%, yoy_chg={yoy:+.2f}pp",
                      str(pd.Timestamp(latest_q).date()), 2, "ok", badness,
                      "[DATA] Fresh shareholding (to " + str(pd.Timestamp(latest_q).date()) + ") -- "
                      "not the pilot's stale (~2023) snapshot. Falling promoter holding is a sharper "
                      "tell on an overvalued, high-conviction-narrative small/microcap in a risk-off "
                      "regime than a modest trim by a diversified large-cap promoter family in a bull "
                      "run -- check size/regime/reason (e.g. merger reclassification, block deal to a "
                      "DII, estate planning) before treating as automatically bearish.",
                      "shareholding.Promoters")
        else:
            add_flag(sym, "promoter", "promoter_holding_level_and_yoy_change",
                      f"holding={latest_v:.2f}% (no ~12mo-prior quarter for YoY)",
                      str(pd.Timestamp(latest_q).date()), 2, "ok", None,
                      "Level only, no comparator quarter for a clean YoY.", "shareholding.Promoters")
    else:
        add_flag(sym, "promoter", "promoter_holding_level_and_yoy_change", None, None, 2,
                  "insufficient-data", None, "No shareholding history for this symbol.", "shareholding")

    # Pledge: still no such column in shareholding.parquet (metrics present:
    # Promoters/FIIs/DIIs/Government/Public/No. of Shareholders/Others only,
    # confirmed by direct inspection) -- same insufficient-data hook as pilot.
    add_flag(sym, "promoter", "promoter_pledge_pct_and_trend", None, None, 3,
              "insufficient-data", None,
              "No pledge-% column in shareholding.parquet (holders present: Promoters/FIIs/DIIs/"
              "Government/Public/No. of Shareholders/Others -- confirmed, no pledge row anywhere). "
              "Hook ready (symbol, quarter_end, pledge_pct) for D-033 ingestion once a source is "
              "found. base_severity=3 reflects pledge's ranking as a heavy-penalty flag once data "
              "exists -- NOT computed here.", "none found -- see note")

print(f"Computed {len(FLAG_ROWS)} flag rows across {len(UNIVERSE)} symbols.")

flags_df = pd.DataFrame(FLAG_ROWS)
flags_df["industry"] = flags_df["symbol"].map(INDUSTRY)
# raw_value mixes floats (most flags) and composite strings (e.g. tax_rate_anomaly's
# "mean=22.8pt,std=1.8pt") -- parquet needs one dtype per column, so stringify
# uniformly (None stays null, not the literal "None").
flags_df["raw_value"] = flags_df["raw_value"].apply(lambda x: None if x is None else str(x))
flags_path = RESULTS / "universe_forensic_flags.parquet"
flags_df.to_parquet(flags_path, index=False)
print(f"Wrote {flags_path} ({len(flags_df)} rows)")

# ---------------------------------------------------------------------------
# Aggregate to Forensic-Risk score, 0-100, higher = worse (unchanged formula
# from the pilot -- base-severity-weighted avg badness of flags with data).
# ---------------------------------------------------------------------------
score_rows = []
for sym, g in flags_df.groupby("symbol"):
    ok = g[g.data_status == "ok"]
    total_flags = len(g)
    n_ok = len(ok)
    n_insufficient = int((g.data_status == "insufficient-data").sum())
    n_na = int((g.data_status == "not-applicable").sum())
    ok_scored = ok.dropna(subset=["base_severity", "badness"])
    denom = ok_scored["base_severity"].sum()
    if len(ok_scored) > 0 and denom and denom > 0:
        score = 100.0 * (ok_scored["base_severity"] * ok_scored["badness"]).sum() / denom
    else:
        score = None
    score_rows.append(dict(
        symbol=sym,
        industry=INDUSTRY.get(sym),
        forensic_risk_score_0_100=round(score, 1) if score is not None else None,
        flags_computed=n_ok,
        flags_insufficient_data=n_insufficient,
        flags_not_applicable=n_na,
        flags_total=total_flags,
        coverage_pct=round(100.0 * n_ok / total_flags, 1) if total_flags else 0.0,
        note="Base severity-weighted avg badness of flags with data (x100). NOT size/regime-"
             "modulated -- scoring engine applies that downstream.",
    ))

score_df = pd.DataFrame(score_rows).sort_values("symbol")
score_path = RESULTS / "universe_forensic_score.parquet"
score_df.to_parquet(score_path, index=False)
print(f"Wrote {score_path}")
print(f"Symbols with any data: {(score_df.flags_computed > 0).sum()}/{len(score_df)}")
print(f"Symbols with a computed score: {score_df.forensic_risk_score_0_100.notna().sum()}/{len(score_df)}")
if score_df.forensic_risk_score_0_100.notna().any():
    print(score_df.dropna(subset=['forensic_risk_score_0_100'])
          .sort_values('forensic_risk_score_0_100', ascending=False)
          .head(10)[['symbol', 'industry', 'forensic_risk_score_0_100', 'coverage_pct']]
          .to_string(index=False))
