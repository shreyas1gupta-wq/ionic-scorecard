# -*- coding: utf-8 -*-
"""build_factor_nav_excel.py — the Principal's factor-NAV workbook (order fixed 2026-07-26).

Column order (Principal's spec; these lead in EXACTLY this order, everything else after):
  NAV Date | NIFTY 200 Momentum 30 | Nifty Midcap Momentum 50 |
  Nifty Smallcap Quality Momentum 100 | NIFTY 200 Quality 30 | GOLDBEES |
  HDFC Liquid Fund(G) | NIFTY 100 Low Vol 30 | NIFTY 200 Value 30 | <rest>

Data layers (merged, newest wins):
  1. SEED  datasets/nifty_factor_indices/factor_navs_seed.csv — the Principal's own
     factor NAV history (2005-04-01 .. 2026-01-05, copied from the Mf_qfra2 project
     into the firm tree 2026-07-26 per backup policy).
  2a. INDEX EXTENSION (primary, OFFICE-OK)  datasets/index_daily/
      nse_official_all_indices.parquet — the firm's NSE official daily index closes
      (EOD-maintained, all factor indices present), mapped by normalized name.
  2b. INDEX EXTENSION (secondary)  datasets/nifty_factor_indices/
      factor_indices_close.parquet — nifty_indices_download.py output
      (niftyindices.com; the office proxy STRIPS COOKIES so this leg only works from
      the home network; auto-attempted 16th + 29th per OPERATING_CALENDAR).
  3. FUND EXTENSION  GOLDBEES + HDFC Liquid Fund(G) daily NAVs from AMFI per-house
     history (30-day chunks; works on the office proxy), cached under
     datasets/mf_nav/daily_cache/.

Output: Shreyas_Ionic_AMC/09_PRODUCT/reports/FACTOR_NAVS.xlsx
Usage:  python build_factor_nav_excel.py
"""
import os
import re
import time
import datetime as dt

import truststore; truststore.inject_into_ssl()
import requests
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
SEED = os.path.join(ROOT, "datasets", "nifty_factor_indices", "factor_navs_seed.csv")
FACTOR_PARQUET = os.path.join(ROOT, "datasets", "nifty_factor_indices", "factor_indices_close.parquet")
CACHE = os.path.join(ROOT, "datasets", "mf_nav", "daily_cache")
OUT_XLSX = os.path.join(ROOT, "Shreyas_Ionic_AMC", "09_PRODUCT", "reports", "FACTOR_NAVS.xlsx")
AMFI_HIST = "https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"

LEAD = ["NIFTY 200 Momentum 30", "Nifty Midcap Momentum 50",
        "Nifty Smallcap Quality Momentum 100", "NIFTY 200 Quality 30",
        "GOLDBEES", "HDFC Liquid Fund(G)", "NIFTY 100 Low Vol 30", "NIFTY 200 Value 30"]

# downloader index name -> seed column header
IDX_TO_SEED = {
    "NIFTY200MOMENTM30": "NIFTY 200 Momentum 30",
    "NIFTY MIDCAP150 MOMENTUM 50": "Nifty Midcap Momentum 50",
    "NIFTY SMALLCAP250 MOMENTUM QUALITY 100": "Nifty Smallcap Quality Momentum 100",
    "NIFTY200 QUALITY 30": "NIFTY 200 Quality 30",
    "NIFTY100 LOWVOL30": "NIFTY 100 Low Vol 30",
    "NIFTY200 VALUE 30": "NIFTY 200 Value 30",
    "NIFTY200 ALPHA 30": "NIFTY 200 Alpha 30",
    "NIFTY500 MOMENTUM 50": "NIFTY 500 Momentum 50",
    "NIFTY500 VALUE 50": "NIFTY 500 Value 50",
    "NIFTY HIGH BETA 50": "NIFTY HIGH BETA 50",
    "NIFTY 50": "NIFTY 50", "NIFTY 100": "NIFTY 100", "NIFTY 500": "NIFTY 500",
    "NIFTY MIDCAP 150": "NIFTY MIDCAP 150", "NIFTY SMLCAP 100": "NIFTY SMALLCAP 100",
    "NIFTY SMALLCAP 250": "NIFTY SMALLCAP 250", "NIFTY500 MULTICAP": "NIFTY MULTICAP 50:25:25",
    "NIFTY LARGEMID250": "NIFTY 250",
}
# AMFI house codes (mf= parameter) — probed empirically 2026-07-26:
# mf=9 -> "HDFC Mutual Fund", mf=21 -> "Nippon India Mutual Fund"
AMFI_FUNDS = {"GOLDBEES": (21, "goldbees"), "HDFC Liquid Fund(G)": (9, "hdfcliquidfund")}


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def amfi_extend(col_disp, house, key, start, end):
    """Daily NAVs for one scheme from AMFI history, cached + resume-safe."""
    os.makedirs(CACHE, exist_ok=True)
    cache_p = os.path.join(CACHE, _norm(col_disp) + ".parquet")
    have = pd.read_parquet(cache_p) if os.path.exists(cache_p) else pd.DataFrame(columns=["date", "nav"])
    if len(have):
        have["date"] = pd.to_datetime(have["date"])
        start = max(pd.Timestamp(start), have["date"].max() + pd.Timedelta(days=1))
    s = requests.Session(); s.headers["User-Agent"] = "Mozilla/5.0"
    rows, cur, endts = [], pd.Timestamp(start), pd.Timestamp(end)
    while cur <= endts:
        # 30-day chunks: house-level pulls run ~700KB/month and 90-day chunks timed out
        # through the corporate proxy (2026-07-26)
        chunk_end = min(cur + pd.Timedelta(days=29), endts)
        params = {"mf": house, "frmdt": cur.strftime("%d-%b-%Y"), "todt": chunk_end.strftime("%d-%b-%Y")}
        for attempt in (1, 2, 3):
            try:
                r = s.get(AMFI_HIST, params=params, timeout=180); r.raise_for_status()
                break
            except Exception as e:
                print(f"  {col_disp}: {params['frmdt']} attempt {attempt}: {repr(e)[:70]}")
                time.sleep(4 * attempt)
        else:
            print(f"  {col_disp}: AMFI unreachable — partial extension banked, resume later")
            break
        for line in r.text.splitlines():
            p = line.split(";")
            if len(p) >= 8 and p[0].strip().isdigit():
                nkey = _norm(p[1])
                # growth/primary plan of the target scheme only — no IDCW, no Direct
                if key in nkey and all(x not in nkey for x in ("idcw", "dividend", "direct", "premium", "bonus", "unclaimed")):
                    # regular Growth plan only (the seed column is the Regular-plan G series)
                    if key == "hdfcliquidfund" and "growth" not in nkey:
                        continue
                    try:
                        rows.append({"date": pd.to_datetime(p[7].strip(), format="%d-%b-%Y"),
                                     "nav": float(p[4])})
                    except (ValueError, IndexError):
                        pass
        cur = chunk_end + pd.Timedelta(days=1)
        time.sleep(1.2)
    out = pd.concat([have, pd.DataFrame(rows)], ignore_index=True) if rows else have
    if len(out):
        out = out.drop_duplicates("date").sort_values("date")
        out.to_parquet(cache_p, index=False)
    return out.set_index("date")["nav"] if len(out) else pd.Series(dtype=float)


# seed column -> normalized NSE-official index_name candidates (layer 2a)
NSE_ALIAS = {
    "NIFTY 50": ["nifty50"], "NIFTY 100": ["nifty100"], "NIFTY 250": ["niftylargemidcap250"],
    "NIFTY 500": ["nifty500"], "NIFTY MIDCAP 150": ["niftymidcap150"],
    "NIFTY SMALLCAP 100": ["niftysmallcap100"], "NIFTY SMALLCAP 250": ["niftysmallcap250"],
    "NIFTY MULTICAP 50:25:25": ["nifty500multicap502525"],
    "NIFTY 100 Low Vol 30": ["nifty100lowvolatility30"],
    "NIFTY 200 Quality 30": ["nifty200quality30"],
    "NIFTY 200 Value 30": ["nifty200value30"],
    "NIFTY 200 Momentum 30": ["nifty200momentum30"],
    "NIFTY 200 Alpha 30": ["nifty200alpha30"],
    "NIFTY 500 Momentum 50": ["nifty500momentum50"],
    "NIFTY 500 Value 50": ["nifty500value50"],
    "Nifty Midcap Momentum 50": ["niftymidcap150momentum50"],
    "Nifty Smallcap Quality Momentum 100": ["niftysmallcap250momentumquality100"],
    "NIFTY HIGH BETA 50": ["niftyhighbeta50"],
}
NSE_OFFICIAL = os.path.join(ROOT, "datasets", "index_daily", "nse_official_all_indices.parquet")


def main():
    seed = pd.read_csv(SEED, parse_dates=["Date"]).set_index("Date").sort_index()
    print(f"seed: {len(seed)} rows to {seed.index.max().date()}")
    seed_cut0 = seed.index.max()
    # layer 2a: the firm's NSE official daily closes (EOD-maintained, office-OK)
    if os.path.exists(NSE_OFFICIAL):
        nse = pd.read_parquet(NSE_OFFICIAL)[["index_name", "date", "close"]]
        nse["nkey"] = nse["index_name"].map(_norm)
        nse["date"] = pd.to_datetime(nse["date"])
        nse = nse[nse["date"] > seed_cut0]
        n_ext = 0
        for col, cands in NSE_ALIAS.items():
            sub = nse[nse["nkey"].isin(cands)]
            if len(sub):
                ser = sub.sort_values("date").drop_duplicates("date").set_index("date")["close"]
                for d, v in ser.items():
                    seed.loc[d, col] = v
                n_ext = max(n_ext, len(ser))
        if n_ext:
            seed = seed.sort_index()
            print(f"NSE-official extension: index columns to {seed.index.max().date()} (+{n_ext} days)")
    # layer 2b: niftyindices downloader output (home-network leg), newest wins
    if os.path.exists(FACTOR_PARQUET):
        idx = pd.read_parquet(FACTOR_PARQUET)
        wide = idx.pivot_table(index="date", columns="index", values="close", aggfunc="last")
        wide.index = pd.to_datetime(wide.index)
        wide = wide.rename(columns=IDX_TO_SEED)
        newer = wide[wide.index > seed.index.max()]
        if len(newer):
            seed = pd.concat([seed, newer.reindex(columns=seed.columns)])
            print(f"index extension: +{len(newer)} rows to {seed.index.max().date()}")
    else:
        print("[DATA] no factor_indices_close.parquet yet — index columns end at the seed "
              "cut until nifty_indices_download.py succeeds (HOME NETWORK / 16th+29th job)")
    # layer 3: the two fund columns extend via AMFI regardless of the index feed.
    # seed_cut is captured BEFORE the loop — the first fund's extension grows
    # seed.index.max() and was starving the second fund's fetch window (bug 2026-07-26)
    end = dt.date.today().isoformat()
    # anchor to the ORIGINAL seed cut — the NSE index extension advances seed.index.max()
    # and was starving the fund columns' window (bug round 2, 2026-07-26)
    for disp, (house, key) in AMFI_FUNDS.items():
        ser = amfi_extend(disp, house, key, seed_cut0 + pd.Timedelta(days=1), end)
        ext = ser[ser.index > seed_cut0] if len(ser) else ser
        for d, v in ext.items():
            seed.loc[d, disp] = v
        if len(ext):
            print(f"{disp}: +{len(ext)} rows to {ext.index.max().date()}")
    seed = seed.sort_index()
    rest = [c for c in seed.columns if c not in LEAD]
    seed = seed[LEAD + rest]
    seed.index.name = "NAV Date"
    out = OUT_XLSX
    for suffix in ("", "_v2", "_v3"):
        try:
            out = OUT_XLSX.replace(".xlsx", f"{suffix}.xlsx")
            with pd.ExcelWriter(out, engine="openpyxl", datetime_format="DD-MM-YYYY") as xw:
                seed.reset_index().to_excel(xw, sheet_name="factor_navs", index=False)
            break
        except PermissionError:
            print(f"{out} is open in Excel (locked) — versioning up")
    print(f"\nwrote {out}\nrows {len(seed)} ({seed.index.min().date()} -> {seed.index.max().date()}) · "
          f"cols: {len(LEAD)} lead + {len(rest)} rest")


if __name__ == "__main__":
    main()
