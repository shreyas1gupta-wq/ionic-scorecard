"""Quality-factor PIT cache builder (D-029 factor family, step 0).
Owner: Arjun Rao (E-004).

PRIMARY SOURCE (chosen after inspecting both): stocks_data_cache.pkl['funda'] — a dict of 378
per-symbol annual (Mar) DataFrames with pre-parsed columns Equity, Reserves, Borrowings,
Profit_TTM, BookValue, IsFinProxy. Cleaner and wider (378 vs 268) than scraping the raw screener
FALLBACK xlsx, and it carries a financial-proxy flag so banks/NBFCs are handled correctly. This is
the SAME underlying screener.in data (restated), just pre-extracted. The raw screener_dump xlsx is
kept as a CROSS-CHECK on ROE (logged, not merged).

Derived per (symbol, fy):
  ROE = Profit_TTM / (Equity + Reserves) * 100        [book equity = Equity + Reserves]
  DE  = Borrowings / (Equity + Reserves)
  EPS_proxy = Profit_TTM / (Equity/BookValue?)  -> we use Profit_TTM growth for EPS-growth stability
             (screener EPS series available in raw PnL; Profit growth is an equivalent stability proxy
              and avoids share-count splits — STATED as a proxy)

PIT DISCIPLINE (Kavya D-009): screener data RESTATED as-of 2026-07-04 (original prints lost).
  availability_date = fiscal-year-end (Mar 31) + 90 days (T+90 fence).
  CAVEAT (loud in report): quality RANKS approximate, esp. pre-2020; data starts FY2014 so any
  quality index before ~2015 is momentum-only. Financial-proxy names: DE is not comparable
  (leverage is the business) -> DE z-score computed within non-fin names only; fins get DE-neutral.

Output: quality_pit.parquet (symbol, fy_end, avail_date, roe, de, profit, is_fin) + coverage log.
Run once; light (pkl load).
"""
from __future__ import annotations
import os, glob, pickle
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
PKL = os.path.join(ROOT, "stocks_data_cache.pkl")
SCR = os.path.join(ROOT, r"datasets\screener_dump_20260704\screener")
OUT = os.path.join(ROOT, r"results\factor_replication\20260704_factor_family")


def log(*a): print(*a, flush=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    log("=" * 70)
    log("QUALITY PIT CACHE — pkl funda primary (RESTATED, T+90 fence)")
    log("=" * 70)
    with open(PKL, "rb") as f:
        cache = pickle.load(f)
    funda = cache["funda"]
    log(f"[funda] {len(funda)} symbols")
    rows = []
    for sym, df in funda.items():
        if not isinstance(df, pd.DataFrame) or df.empty:
            continue
        d = df.copy()
        d.index = pd.to_datetime(d.index)
        for ts, r in d.iterrows():
            # fiscal-year end: the funda index is 'Mar 1' of the FY year; treat as FY-end Mar 31
            fy_end = pd.Timestamp(year=ts.year, month=3, day=31)
            eq = r.get("Equity", np.nan); rs = r.get("Reserves", np.nan)
            bw = r.get("Borrowings", np.nan); pf = r.get("Profit_TTM", np.nan)
            isfin = bool(r.get("IsFinProxy", False))
            book = (eq + rs) if (pd.notna(eq) and pd.notna(rs)) else np.nan
            roe = (pf / book * 100) if (pd.notna(pf) and pd.notna(book) and book > 0) else np.nan
            de = (bw / book) if (pd.notna(bw) and pd.notna(book) and book > 0) else np.nan
            rows.append({"symbol": str(sym).strip().upper(), "fy_end": fy_end,
                         "avail_date": fy_end + pd.Timedelta(days=90),
                         "roe": roe, "de": de, "profit": pf, "is_fin": isfin})
    q = pd.DataFrame(rows).dropna(subset=["fy_end"])
    q = q.sort_values(["symbol", "fy_end"]).drop_duplicates(["symbol", "fy_end"], keep="last")
    log(f"[quality] rows={len(q)} symbols={q['symbol'].nunique()} "
        f"fy {q['fy_end'].min().date()}->{q['fy_end'].max().date()}")
    log(f"[quality] non-null: roe={q['roe'].notna().mean():.1%} de={q['de'].notna().mean():.1%} "
        f"profit={q['profit'].notna().mean():.1%} | is_fin={q['is_fin'].mean():.1%}")

    # cross-check ROE vs raw screener xlsx Table_6 '10 Years' summary on a sample (log only)
    sample = q[q["fy_end"].dt.year == 2024].head(30)["symbol"].tolist()
    xc = []
    for s in sample:
        fb = os.path.join(SCR, f"{s}_FALLBACK_FULL.xlsx")
        if os.path.exists(fb):
            try:
                t6 = pd.read_excel(fb, sheet_name="Table_6")
                # last-year ROE
                ly = t6[t6.iloc[:, 0].astype(str).str.contains("Last Year", na=False)]
                if len(ly):
                    v = str(ly.iloc[0, 1]).replace("%", "").strip()
                    xc.append((s, float(v) if v not in ("", "nan") else np.nan))
            except Exception:
                pass
    if xc:
        merged = q[(q["fy_end"].dt.year == 2024)].set_index("symbol")["roe"]
        diffs = [abs(merged.get(s, np.nan) - v) for s, v in xc if pd.notna(merged.get(s, np.nan)) and pd.notna(v)]
        if diffs:
            log(f"[xcheck] ROE pkl-vs-screener-xlsx (2024, n={len(diffs)}): "
                f"median abs diff={np.median(diffs):.1f}pp (expect small; same source, TTM vs FY timing)")

    q.to_parquet(os.path.join(OUT, "quality_pit.parquet"), index=False)
    cov = q.groupby(q["fy_end"].dt.year).agg(
        n=("symbol", "nunique"),
        roe_cov=("roe", lambda s: round(s.notna().mean(), 3)),
        de_cov=("de", lambda s: round(s.notna().mean(), 3))).reset_index()
    cov.to_csv(os.path.join(OUT, "quality_coverage_by_fy.csv"), index=False)
    log("\n[coverage by fiscal year]")
    log(cov.to_string(index=False))
    log(f"\n[done] quality_pit.parquet written")


if __name__ == "__main__":
    main()
