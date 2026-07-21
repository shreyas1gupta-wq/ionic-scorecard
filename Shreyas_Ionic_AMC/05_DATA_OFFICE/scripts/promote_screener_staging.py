"""
promote_screener_staging.py — D-009 verify + promote screener_deep/_staging -> live parquets.
Companion to scrape_screener_750.py. SOP §6 gate: verify BEFORE any scoring use, never silently
clobber (back up the live parquet first, write to a dated backup, then overwrite).

Promotion is REPLACE-BY-SYMBOL: staged rows for a symbol replace that symbol's live rows (so
the 50 re-scraped stale/zero names UPDATE in place); brand-new symbols are appended. Columns are
outer-unioned (new odd fiscal-period columns are absorbed, not dropped).

Run:
  <py> promote_screener_staging.py            # verify only (dry run, no write)
  <py> promote_screener_staging.py --promote  # verify + write live (after a clean dry run)
"""
import json
import os
import sys
import time
import truststore
truststore.inject_into_ssl()
import numpy as np
import pandas as pd
import requests

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
DS = os.path.join(ROOT, "datasets", "screener_deep")
STAGE = os.path.join(DS, "_staging")
TABLES = [("pl", "screener_annual_pl.parquet"),
          ("bs", "screener_balance_sheet.parquet"),
          ("cf", "screener_cash_flow.parquet"),
          ("qtr", "screener_quarterly_results.parquet")]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")


def _clean_num(v):
    if pd.isna(v):
        return np.nan
    if isinstance(v, str):
        v = v.replace(",", "").replace("%", "").strip()
        if v in ("", "-"):
            return np.nan
        try:
            return float(v)
        except ValueError:
            return np.nan
    return float(v)


def verify_spotcheck(staged_pl):
    """Re-fetch 3 staged symbols live and confirm the staged Net Profit+ / Sales+ match."""
    import re
    syms = [s for s in staged_pl["symbol"].unique()][:3]
    sess = requests.Session(); sess.headers.update({"User-Agent": UA})
    ok = True
    for sym in syms:
        try:
            for variant in ("consolidated/", ""):
                html = sess.get(f"https://www.screener.in/company/{sym}/{variant}", timeout=30).text
                m = re.search(r'<table class="data-table[^"]*".*?</table>', html, re.S)
                if m and ("Net Profit" in m.group(0)):
                    break
            row = staged_pl[(staged_pl["symbol"] == sym) & (staged_pl["metric"].isin(["Net Profit+", "Sales+", "Revenue+"]))]
            marcols = [c for c in staged_pl.columns if c.startswith("Mar 202")]
            latest = sorted(marcols)[-1] if marcols else None
            val = row[latest].dropna().iloc[0] if len(row) and latest else None
            print(f"  spot-check {sym}: staged latest-Mar {latest}={val} (live page fetched, {len(html):,}b) — eyeball vs screener.in/{sym}")
        except Exception as e:
            print(f"  spot-check {sym}: WARN {type(e).__name__}: {str(e)[:80]}")
            ok = False
    return ok


def main(promote):
    if not os.path.isdir(STAGE):
        print("No _staging dir — nothing to promote."); return
    meta_p = os.path.join(STAGE, "_meta.json")
    if os.path.exists(meta_p):
        meta = json.load(open(meta_p))
        print(f"staging meta: {meta.get('run_date')} attempted={meta.get('symbols_attempted')} "
              f"ok={meta.get('symbols_ok')} failed={len(meta.get('symbols_failed', []))}")

    all_ok = True
    plans = []
    for base, live_name in TABLES:
        sp = os.path.join(STAGE, f"screener_{base}_staging.parquet")
        if not os.path.exists(sp):
            print(f"[{base}] NO staging file — skip"); continue
        staged = pd.read_parquet(sp)
        live_path = os.path.join(DS, live_name)
        if os.path.exists(live_path):
            live = pd.read_parquet(live_path)
        else:
            live = staged.iloc[0:0].copy()  # new table (e.g. quarterly) — no prior live file
            print(f"[{base}] NOTE: no live {live_name} yet — this is a brand-new table.")
        staged_syms = set(staged["symbol"].astype(str))
        live_syms = set(live["symbol"].astype(str))
        new_syms = staged_syms - live_syms
        upd_syms = staged_syms & live_syms

        # schema check
        core = {"symbol", "metric"}
        assert core <= set(staged.columns), f"{base}: staging missing core cols"
        # duplicate (symbol,metric) in staging?
        dups = staged.duplicated(["symbol", "metric"]).sum()
        # build promoted: drop live rows for staged symbols, then concat
        promoted = pd.concat([live[~live["symbol"].isin(staged_syms)], staged], ignore_index=True)
        # coerce ALL period columns to numeric float (existing live rows are comma-strings, new
        # staged rows are float -> mixed object columns break pyarrow write). Values are identical;
        # float is cleaner and the scoring engine's _clean_num reads it natively.
        for c in promoted.columns:
            if c not in ("symbol", "metric"):
                promoted[c] = promoted[c].map(_clean_num).astype("float64")
        promoted_dups = promoted.duplicated(["symbol", "metric"]).sum()

        # row-count sanity
        print(f"\n[{base}] live={live.shape} staged={staged.shape} "
              f"(new syms={len(new_syms)}, updated syms={len(upd_syms)}) "
              f"-> promoted={promoted.shape}")
        print(f"   staging dup(sym,metric)={dups}  promoted dup(sym,metric)={promoted_dups}")
        # symbol-count sanity
        promoted_syms = promoted["symbol"].nunique()
        print(f"   symbols: live={len(live_syms)} -> promoted={promoted_syms}")
        if dups or promoted_dups:
            print(f"   !! DUPLICATE rows detected — investigate before promote"); all_ok = False
        plans.append((base, live_name, promoted, staged))

    # spot-check on PL staging
    pl_staged = next((s for b, _, _, s in plans if b == "pl"), None)
    if pl_staged is not None:
        print("\nD-009 spot-check (re-fetch 3 staged symbols):")
        verify_spotcheck(pl_staged)

    if not promote:
        print("\nDRY RUN complete. Re-run with --promote to write live parquets.")
        return
    if not all_ok:
        print("\nABORT: verification failed; not promoting."); return

    stamp = time.strftime("%Y%m%d_%H%M")
    bdir = os.path.join(STAGE, f"backup_{stamp}")
    os.makedirs(bdir, exist_ok=True)
    for base, live_name, promoted, staged in plans:
        # backup live (skip if brand-new table with no prior live file)
        live_path = os.path.join(DS, live_name)
        if os.path.exists(live_path):
            pd.read_parquet(live_path).to_parquet(os.path.join(bdir, live_name), index=False)
        promoted.to_parquet(live_path, index=False)
        print(f"[{base}] promoted -> {live_name} ({promoted.shape}); backup in {bdir}")
    # update live _done.json (union)
    live_done_p = os.path.join(DS, "_done.json")
    live_done = json.load(open(live_done_p)) if os.path.exists(live_done_p) else []
    stg_done = json.load(open(os.path.join(STAGE, "_done.json"))) if os.path.exists(os.path.join(STAGE, "_done.json")) else []
    merged = sorted(set(live_done) | set(stg_done))
    json.dump(merged, open(live_done_p, "w"), indent=0)
    print(f"\n_done.json: {len(live_done)} -> {len(merged)} symbols")
    print("PROMOTED. Screener_deep live parquets updated. Run build_full750_quant.py next.")


if __name__ == "__main__":
    main("--promote" in sys.argv)
