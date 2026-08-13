# -*- coding: utf-8 -*-
"""mf_benchmark_indices_build.py — ONE consistent-basis benchmark-index panel for every MF category.

Principal ruling 2026-08-06 (verbatim): "take whichever we can find tri non-tri and save using
skills we had skill to scrap from nse we have but be consistent i.e. same for all funds and same
for all workflow." Consistency across funds/workflow beats TRI purity. This script answers: what
CAN we source, on what basis, and builds ONE tidy panel so every downstream consumer (category
return tables, up/down-capture pages, QFRA-1 Indices-sheet rebuild) reads the same series the
same way.

FINDING (this session, confirmed by a fresh live D-009 cross-check, not assumed from old docs):
NO TRI series is reachable from the office today, for ANY index:
  - niftyindices.com (the only real TRI source) is proxy-blocked at the office (factor-indices
    skill, re-confirmed 2026-07-26; not re-tested here, would need home network).
  - NSE's own live API (https://www.nseindia.com/api/allIndices, tested live this session,
    2026-08-06) returns PRI + PE/PB/DivYield only, same fields as our archive pull -- no TRI
    field anywhere in the payload.
  - Nothing named *TRI*/"Total Return" exists anywhere on disk in datasets/.
So the "single consistent basis" is not a judgment call between two available options -- PRI is
the ONLY basis obtainable for these indices at the office right now. Recommendation: PRI for
every series in this panel, labelled loudly and structurally (a `basis` column on every row, not
a footnote), so no downstream consumer can mix bases by accident. See DATA_QUALITY_RULES.md and
DATA_CATALOG.md for the full writeup and the div_yield TRI-reconstruction test (item 4 of the
brief) -- validated as a return-GAP estimator (reproduces the independently-documented ~1.1-1.4
pp/yr TRI-PRI drag), NOT as an absolute-level TRI (structurally understates it -- the source
panel only starts 2016, missing pre-2016 dividend compounding). Not adopted into this panel
because it only exists for equity indices; adopting it here while debt/hybrid stays PRI would
recreate exactly the "TRI for some, PRI for others" inconsistency the ruling says to avoid.

Per D-009 protocol: DOES NOT re-scrape. Reuses two already-verified, already-freshness-pinged
office-OK assets:
  1. datasets/index_daily/nse_official_all_indices.parquet -- built + maintained by the existing
     factor-indices skill's EOD puller (nse_indices_close_pull.py / nsearchives.nseindia.com).
     176 official NSE indices, PRI + OHLC + PE/PB/DivYield, 2016-01-01 -> most recent EOD.
  2. The ACE MF "Advisory V2" extract (Downloads/10. V2 Data_31th July_2026.xlsx), read via the
     existing pr_template/lib/acemf.py loader -- gives the real `Benchmark Indices` name per fund,
     Direct-plan-filtered, so the mapping below is driven by what funds ACTUALLY cite, not a
     guessed list.

Matching is DETERMINISTIC name normalization (strip "- TRI"/"TRI" suffix, then alnum-lowercase),
never string-similarity fuzzy matching -- this firm's standing rule against fuzzy joins (feedback-
mf-mapping-no-fuzzy) is about FUND-name matching, but the same discipline is right here too: a
wrong index join is worse than an honest "not sourced".

Outputs (both under datasets/index_daily/, same convention as nse_official_all_indices.parquet):
  - benchmark_index_levels.parquet   tidy long panel: index_name, date, level, basis, div_yield
  - benchmark_category_map.csv       ACE category x benchmark name -> matched index_name (or
                                      reason not sourced) x row-count, for the consistency report

No network calls. Fully deterministic/idempotent given the two input files above -- rerun any
time either input refreshes. D-009 live spot-checks (18/18 exact vs a fresh NSE archive re-fetch,
3 dates x 6 core indices) and the div_yield reconstruction test were run separately this session
and are recorded in the catalog/quality-rules entries, not repeated here to keep this script
network-free and fast.

Usage: python mf_benchmark_indices_build.py
"""
import os
import re
import sys

import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
NSE_IDX = os.path.join(ROOT, "datasets", "index_daily", "nse_official_all_indices.parquet")
ACE_XLSX = r"C:\Users\Shreyas.1Gupta\Downloads\10. V2 Data_31th July_2026.xlsx"
OUT_PARQUET = os.path.join(ROOT, "datasets", "index_daily", "benchmark_index_levels.parquet")
OUT_MAP_CSV = os.path.join(ROOT, "datasets", "index_daily", "benchmark_category_map.csv")

# acemf.py lives in the tracked repo tree; import it directly rather than re-implementing the
# (non-trivial, already-verified) header-location + de-dup + numeric-coercion logic.
sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "09_PRODUCT", "pr_template", "lib"))
import acemf  # noqa: E402

# The 6 SEBI-category benchmarks the FM brief names explicitly. Everything else in the panel is
# "bonus" coverage of whatever ELSE ACE's Benchmark Indices column maps to on the same NSE source.
CORE_CATEGORY_LABELS = {
    "Nifty 100": "Large", "NIFTY LargeMidcap 250": "LargeMid", "Nifty Midcap 150": "Mid",
    "Nifty 500": "Flexi", "Nifty500 Multicap 50:25:25": "Multi", "Nifty Smallcap 250": "Small",
}


def norm(s):
    """Deterministic index-name key: strip a trailing '- TRI' / 'TRI', then alnum-lowercase.
    Never similarity-scored -- an index join is either exact after normalization or it is
    reported as unmatched."""
    s = re.sub(r"\s*-\s*TRI$", "", str(s), flags=re.I)
    s = re.sub(r"\s*TRI$", "", s, flags=re.I)
    return re.sub(r"[^a-z0-9]", "", s.lower())


def main():
    # ACE MF is a MONTHLY drop with a filename that does not follow a fixed pattern (verified
    # 2026-08-05: the file named "31th July_2026" was actually June data) -- never hardcode past
    # one refresh. Accept an override so next month's run doesn't need a code edit.
    ace_path = sys.argv[1] if len(sys.argv) > 1 else ACE_XLSX
    if not os.path.exists(NSE_IDX):
        raise FileNotFoundError(f"missing {NSE_IDX} -- run the factor-indices skill's EOD puller first")
    if not os.path.exists(ace_path):
        raise FileNotFoundError(
            f"missing {ace_path} -- pass the current ACE MF Advisory V2 monthly extract path as "
            f"argv[1], e.g.: python {os.path.basename(__file__)} \"C:\\Users\\Shreyas.1Gupta\\"
            f"Downloads\\<this month's file>.xlsx\"")

    nse = pd.read_parquet(NSE_IDX)
    nse["date"] = pd.to_datetime(nse["date"])
    nse_names = sorted(nse["index_name"].unique())
    nse_by_norm = {}
    for n in nse_names:
        nse_by_norm.setdefault(norm(n), n)  # first-seen wins; NSE names are already unique pre-norm

    tri_like = [n for n in nse_names if re.search(r"\btri\b|total\s*return", n, re.I)]
    if tri_like:
        raise RuntimeError(
            f"nse_official_all_indices.parquet now contains TRI-named series {tri_like} -- the "
            "no-TRI-at-the-office assumption this script documents has changed; re-check basis "
            "before trusting the PRI label below.")

    ace_df, ace_meta = acemf.load(ace_path, cache_parquet=None)
    direct = acemf.direct_growth(ace_df)
    bidx = direct["Benchmark Indices"].astype(str).str.strip()
    have_bm = bidx != "nan"
    print(f"ACE file as-of (modal, per acemf.block_asof): {ace_meta['file_asof']}")
    print(f"Direct-plan rows: {len(direct)}; with a Benchmark Indices value: {have_bm.sum()}")

    cat_series = direct["Category"].astype(str).str.strip()
    grp = (pd.DataFrame({"category": cat_series[have_bm], "benchmark": bidx[have_bm]})
           .value_counts().reset_index(name="n_direct_schemes"))

    rows = []
    matched_index_names = set()
    for _, r in grp.iterrows():
        key = norm(r["benchmark"])
        m = nse_by_norm.get(key)
        if m:
            matched_index_names.add(m)
        rows.append({
            "ace_category": r["category"], "ace_benchmark_name": r["benchmark"],
            "n_direct_schemes": int(r["n_direct_schemes"]),
            "matched_index_name": m if m else "",
            "basis": "PRI" if m else "",
            "sourced": bool(m),
            "reason_not_sourced": "" if m else _reason(r["benchmark"]),
        })
    map_df = pd.DataFrame(rows).sort_values(["sourced", "n_direct_schemes"], ascending=[False, False])
    map_df.to_csv(OUT_MAP_CSV, index=False, encoding="utf-8")

    # map_df is one row per (category, benchmark) COMBINATION -- the same benchmark name (e.g.
    # "NIFTY 500 - TRI") is cited by several categories (Flexi/ELSS/Value/Thematic/...), so this
    # is NOT the same denominator as "unique benchmark names". Report both, do not conflate them.
    n_sourced = int(map_df["sourced"].sum())
    n_total = len(map_df)
    rows_sourced = int(map_df.loc[map_df["sourced"], "n_direct_schemes"].sum())
    rows_total = int(map_df["n_direct_schemes"].sum())
    uniq_bm = map_df.drop_duplicates("ace_benchmark_name")
    n_uniq_sourced, n_uniq_total = int(uniq_bm["sourced"].sum()), len(uniq_bm)
    print(f"\n(category, benchmark) combinations: {n_sourced}/{n_total} sourced "
          f"({n_sourced/n_total*100:.1f}%)")
    print(f"UNIQUE benchmark names: {n_uniq_sourced}/{n_uniq_total} sourced "
          f"({n_uniq_sourced/n_uniq_total*100:.1f}%)")
    print(f"Direct-plan scheme-rows covered: {rows_sourced}/{rows_total} "
          f"({rows_sourced/rows_total*100:.1f}%)")

    missing_core = [c for c in CORE_CATEGORY_LABELS if c not in matched_index_names]
    if missing_core:
        raise RuntimeError(f"a CORE category benchmark failed to match: {missing_core} -- fix "
                            "before shipping the panel, do not ship silently short of the ask")
    print(f"All {len(CORE_CATEGORY_LABELS)} core SEBI-category benchmarks matched: "
          f"{list(CORE_CATEGORY_LABELS.items())}")

    panel = (nse[nse["index_name"].isin(matched_index_names)]
             [["index_name", "date", "close", "div_yield"]]
             .rename(columns={"close": "level"})
             .sort_values(["index_name", "date"])
             .reset_index(drop=True))
    panel["basis"] = "PRI"  # every row, structurally -- see module docstring for why

    # PERIODS-PER-YEAR discipline (Lessons Learned 2026-07: "the 17-month option gap hid inside
    # healthy-looking yearly aggregates" / "READY tags require cadence checks, not just row
    # counts"). A name match is NOT the same as usable coverage -- several of the ~86 "bonus"
    # sector/strategy indices beyond the 6 core categories have multi-YEAR holes in NSE's own
    # archive (thin/irregular publication of newer thematic indices), which would silently wreck
    # a 1Y/3Y/5Y period return if unflagged. Flag per-series, do not silently drop -- a consumer
    # building a 1Y number off a gappy series needs to know before trusting it, not have the row
    # disappear with no explanation.
    GAP_OK_DAYS = 10  # a long Indian-market holiday cluster; anything past this is a real hole
    RECENT_START = pd.Timestamp("2023-06-30")  # 3y window ending at the ACE as-of, per the brief
    cont_flags = {}
    for name in matched_index_names:
        sub = panel.loc[panel["index_name"] == name, "date"]
        gaps_full = sub.diff().dt.days.dropna()
        gaps_recent = sub[sub >= RECENT_START].diff().dt.days.dropna()
        cont_flags[name] = {
            "max_gap_days_full_history": int(gaps_full.max()) if len(gaps_full) else 0,
            "max_gap_days_last_3y": int(gaps_recent.max()) if len(gaps_recent) else None,
            "continuous_3y": bool(len(gaps_recent) and gaps_recent.max() <= GAP_OK_DAYS),
        }
    panel["continuous_3y"] = panel["index_name"].map(lambda n: cont_flags[n]["continuous_3y"])
    panel = panel[["index_name", "date", "level", "basis", "div_yield", "continuous_3y"]]
    panel.to_parquet(OUT_PARQUET, index=False)

    n_clean = sum(1 for v in cont_flags.values() if v["continuous_3y"])
    n_gappy = len(cont_flags) - n_clean
    print(f"\nWrote {OUT_PARQUET}: {len(panel):,} rows, {panel['index_name'].nunique()} index series")
    print(f"  continuous_3y=True (max gap <={GAP_OK_DAYS}d over the last 3y): {n_clean} series")
    print(f"  continuous_3y=False (a hole >{GAP_OK_DAYS}d somewhere in the last 3y -- DO NOT "
          f"trust a period return off these without checking WHICH sub-window is populated): {n_gappy} series")
    print(f"Wrote {OUT_MAP_CSV}: {n_total} benchmark-name rows")

    # fold the continuity flag into the map CSV too, so the "which benchmarks can we source"
    # report doesn't have to be read jointly with the parquet to know which matches are trustworthy
    map_df["continuous_3y"] = map_df["matched_index_name"].map(
        lambda n: cont_flags.get(n, {}).get("continuous_3y") if n else None)
    map_df.to_csv(OUT_MAP_CSV, index=False, encoding="utf-8")

    print("\n--- CORE 6 gap sanity (must all be clean) ---")
    for name, label in CORE_CATEGORY_LABELS.items():
        sub = panel[panel["index_name"] == name]
        v = cont_flags[name]
        print(f"  {label:9s} ({name:28s}) n={len(sub):5d}  "
              f"max_gap_full={v['max_gap_days_full_history']}d  "
              f"max_gap_last3y={v['max_gap_days_last_3y']}d  continuous_3y={v['continuous_3y']}")
        if not v["continuous_3y"]:
            raise RuntimeError(f"CORE category {label} ({name}) is NOT continuous over the last "
                                "3 years -- this must be clean before the panel ships")

    print(f"\n--- bonus (non-core) series flagged continuous_3y=False (name matched, coverage NOT verified clean) ---")
    for name in sorted(matched_index_names - set(CORE_CATEGORY_LABELS)):
        if not cont_flags[name]["continuous_3y"]:
            print(f"  {name:42s} max_gap_full={cont_flags[name]['max_gap_days_full_history']:5d}d  "
                  f"max_gap_last3y={cont_flags[name]['max_gap_days_last_3y']}")


def _reason(benchmark_name):
    b = benchmark_name
    if b.upper().startswith("CRISIL"):
        return "CRISIL proprietary bond index -- not published by NSE/AMFI; no free office-accessible source found"
    if b.upper().startswith("BSE"):
        return "BSE (not NSE) index -- outside nse_official_all_indices' NSE-only universe"
    if "MSCI" in b.upper():
        return "international index -- outside any current NSE/AMFI/free-source route"
    if re.search(r"gold", b, re.I):
        return "commodity reference index, not an NSE equity/debt index -- GOLDBEES/SILVERBEES ETF NAVs (datasets/etf_gold_silver/) are a separate, imperfect proxy, not this index itself"
    if re.search(r"debt|duration|bond|gilt|money market|liquid|overnight|1d rate", b, re.I):
        return "NSE-computed debt index by name, but NOT in nse_official_all_indices.parquet's current 176-name pull (that puller's scope is equity/factor/thematic indices) -- would need the EOD puller's index list extended, out of scope here per 'do not write a new scraper'"
    return "no normalized-name match in nse_official_all_indices.parquet; not investigated further this pass"


if __name__ == "__main__":
    main()
