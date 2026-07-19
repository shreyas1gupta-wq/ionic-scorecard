"""Build THE single master fundamentals file — all companies, PIT-safe, quarterly-rebuildable.
Backbone : earnings_pit yearly_profit_loss_pit + yearly_balance_sheet_pit (4,491 co, FY2004->FY2023,
           available_date built in, source='mc_pit').
Fresh overlay: screener_live consolidated (profit_loss/balance_sheet/cash_flow) FY up to 2026, source='screener_live'.
Fresh wins over PIT for overlapping (symbol, fiscal_year, statement, metric). available_date for fresh =
conservative period_end + 90d (so it stays usable in PIT backtests).
Output: data/fundamentals/MASTER_fundamentals_pit.parquet  (LONG, tidy) + MASTER_coverage.csv.
Idempotent: re-run any time (e.g. after each quarter's scrape) to refresh.
"""
import os, glob, json, re
import numpy as np, pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
DS = os.path.join(ROOT, "datasets", "earnings_pit")
CONS = os.path.join(ROOT, "ALPHA_RANKER", "data", "fundamentals", "consolidated")
OUT = os.path.join(ROOT, "ALPHA_RANKER", "data", "fundamentals")

def fyear(label):
    m = re.search(r"(\d{4})", str(label))
    return int(m.group(1)) if m else np.nan

def norm(metric):
    return re.sub(r"\s+", " ", str(metric).lower().replace("\xa0", " ").replace("+", "").strip())

PL_METRICS = ["Depreciation","EPS in Rs","Expenses","Financing Margin %","Financing Profit","Interest",
              "Net Profit","OPM %","Operating Profit","Other Income","Profit before tax","Revenue","Sales","Tax %"]
BS_METRICS = ["Borrowings","CWIP","Equity Capital","Fixed Assets","Investments","Other Assets",
              "Other Liabilities","Preference Capital","Reserves","Total Assets","Total Liabilities"]

def load_pit(fname, metrics, statement):
    d = pd.read_parquet(os.path.join(DS, fname))
    keep = ["company", "nse_symbol", "year_end", "available_date"] + [m for m in metrics if m in d.columns]
    d = d[keep].copy()
    long = d.melt(id_vars=["company","nse_symbol","year_end","available_date"], var_name="metric", value_name="value")
    long["fiscal_year"] = long["year_end"].map(fyear)
    long["period_label"] = long["year_end"]
    long["statement"] = statement
    long["source"] = "mc_pit"; long["is_fresh"] = False
    return long.drop(columns=["year_end"])

def load_fresh(fname, statement):
    p = os.path.join(CONS, fname)
    if not os.path.exists(p): return None
    d = pd.read_parquet(p)                                   # cols: symbol, metric, period, value
    d = d.rename(columns={"symbol":"nse_symbol", "period":"period_label"})
    d = d[d["period_label"].astype(str).str.match(r"[A-Za-z]{3}\s+\d{4}", na=False)].copy()  # drop TTM/junk
    d["fiscal_year"] = d["period_label"].map(fyear)
    d["company"] = d["nse_symbol"]
    # conservative available_date = period-end + ~90d
    d["available_date"] = pd.to_datetime(d["period_label"], format="%b %Y", errors="coerce") + pd.offsets.MonthEnd(1) + pd.Timedelta(days=90)
    d["statement"] = statement; d["source"] = "screener_live"; d["is_fresh"] = True
    return d[["company","nse_symbol","metric","value","fiscal_year","period_label","statement","available_date","source","is_fresh"]]

frames = [load_pit("yearly_profit_loss_pit.parquet", PL_METRICS, "PL"),
          load_pit("yearly_balance_sheet_pit.parquet", BS_METRICS, "BS")]
for fn, st in [("profit_loss.parquet","PL"),("balance_sheet.parquet","BS"),("cash_flow.parquet","CF")]:
    f = load_fresh(fn, st)
    if f is not None: frames.append(f)

m = pd.concat(frames, ignore_index=True)
m["value"] = pd.to_numeric(m["value"], errors="coerce")
m["metric_norm"] = m["metric"].map(norm)
m["key_symbol"] = m["nse_symbol"].fillna("").astype(str).str.upper().str.strip()
m.loc[m["key_symbol"]=="", "key_symbol"] = "NAME::" + m["company"].astype(str)
m = m.dropna(subset=["fiscal_year"])
m["fiscal_year"] = m["fiscal_year"].astype(int)
# dedup: prefer fresh (is_fresh True) over PIT for same (key, fy, statement, metric_norm)
m = m.sort_values(["is_fresh"], ascending=False)
m = m.drop_duplicates(subset=["key_symbol","fiscal_year","statement","metric_norm"], keep="first")
m = m.dropna(subset=["value"])
m["available_date"] = pd.to_datetime(m["available_date"], errors="coerce")   # unify PIT str + fresh Timestamp
for c in ["key_symbol","nse_symbol","company","period_label","statement","metric","metric_norm","source"]:
    m[c] = m[c].astype("string")
m = m[["key_symbol","nse_symbol","company","fiscal_year","period_label","statement","metric","metric_norm",
       "value","available_date","source","is_fresh"]].reset_index(drop=True)
m.to_parquet(os.path.join(OUT, "MASTER_fundamentals_pit.parquet"))

# coverage manifest
cov = (m.groupby("key_symbol")
         .agg(company=("company","first"), nse_symbol=("nse_symbol","first"),
              n_rows=("value","size"), min_fy=("fiscal_year","min"), max_fy=("fiscal_year","max"),
              has_fresh=("is_fresh","max"), statements=("statement", lambda s: "".join(sorted(set(s)))))
         .reset_index())
cov.to_csv(os.path.join(OUT, "MASTER_coverage.csv"), index=False)

print("MASTER built:", m.shape, "-> MASTER_fundamentals_pit.parquet")
print("unique companies:", m["key_symbol"].nunique(),
      "| with fresh overlay:", int(cov["has_fresh"].sum()),
      "| mapped nse_symbol:", int(cov["nse_symbol"].notna().sum()))
print("fiscal_year span:", int(m["fiscal_year"].min()), "->", int(m["fiscal_year"].max()))
print("rows by source:\n", m["source"].value_counts().to_string())
print("companies reaching FY>=2024 (fresh):", int((cov["max_fy"]>=2024).sum()))
