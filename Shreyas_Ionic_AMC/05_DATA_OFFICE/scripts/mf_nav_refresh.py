# -*- coding: utf-8 -*-
"""mf_nav_refresh.py — AMFI official NAV pull, storage-frugal (Principal 2026-07-25).
Design: scripts do everything (~0 tokens). Latest NAVs from NAVAll.txt (verified working on the
office proxy). Retention: daily raw snapshots pruned after RETAIN_DAYS; month-end NAV history is
kept forever (tiny). D-009 sample check on every run (NAV sanity vs prior snapshot).

Usage:
  python mf_nav_refresh.py                 # pull today's NAVs, update parquet, prune old raws
  python mf_nav_refresh.py --digest        # also write a compact .md digest (for model reading)
Outputs (datasets/mf_nav/):
  navall_YYYY-MM-DD.txt.gz    raw snapshot (pruned > RETAIN_DAYS)
  nav_latest.parquet          scheme_code, isin, name, nav, date  (today's full cross-section)
  nav_monthend.parquet        appended month-end history (kept forever)
  NAV_DIGEST.md               tiny summary for token-cheap model reads (--digest)
"""
import os, sys, gzip, io, datetime
import truststore; truststore.inject_into_ssl()
import requests
import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
OUT = os.path.join(ROOT, "datasets", "mf_nav")
os.makedirs(OUT, exist_ok=True)
RETAIN_DAYS = 180          # raw daily snapshots kept ~6 months, then deleted (Principal rule)
URL = "https://portal.amfiindia.com/spages/NAVAll.txt"


def fetch():
    r = requests.Session().get(URL, timeout=60)
    r.raise_for_status()
    return r.text


def parse(text):
    rows, category = [], ""
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        if ";" not in ln:
            category = ln
            continue
        p = ln.split(";")
        if len(p) >= 6 and p[0] != "Scheme Code":
            try:
                nav = float(p[4])
            except ValueError:
                continue
            rows.append((p[0], p[1].strip(), p[3].strip(), nav, p[5].strip(), category))
    df = pd.DataFrame(rows, columns=["scheme_code", "isin", "name", "nav", "date", "category"])
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["date"])
    # drop non-priced rows: defunct options & side-pocketed segregated portfolios carry NAV 0
    return df[df["nav"] > 0.01].reset_index(drop=True)


def d009_check(df):
    """Sample verification: cross-section sane + spot drift vs last snapshot < 15% for large schemes."""
    assert len(df) > 8000, f"suspiciously few NAV rows: {len(df)}"
    assert df["nav"].between(0.5, 5_000_000).mean() > 0.97, "NAV range insane"
    prev = os.path.join(OUT, "nav_latest.parquet")
    if os.path.exists(prev):
        old = pd.read_parquet(prev)[["scheme_code", "nav"]].rename(columns={"nav": "nav_old"})
        m = df.merge(old, on="scheme_code").query("nav_old > 10")
        if len(m) > 100:
            drift = (m["nav"] / m["nav_old"] - 1).abs()
            frac_big = (drift > 0.15).mean()
            assert frac_big < 0.02, f"{frac_big:.1%} of schemes moved >15% in one refresh — source suspect"
    return True


def main(digest=False):
    today = datetime.date.today()
    text = fetch()
    df = parse(text)
    d009_check(df)
    # raw snapshot (gz) + prune old
    raw = os.path.join(OUT, f"navall_{today}.txt.gz")
    with gzip.open(raw, "wt", encoding="utf-8") as f:
        f.write(text)
    for fn in os.listdir(OUT):
        if fn.startswith("navall_") and fn.endswith(".txt.gz"):
            d = fn[7:17]
            try:
                age = (today - datetime.date.fromisoformat(d)).days
                if age > RETAIN_DAYS:
                    os.remove(os.path.join(OUT, fn))
            except ValueError:
                pass
    # latest cross-section
    df.to_parquet(os.path.join(OUT, "nav_latest.parquet"), index=False)
    # month-end history — per-scheme, per-month upsert (audit fix 2026-07-26).
    # THE OLD BUG: a global max-date filter kept only schemes stamped with the single
    # newest NAV date, then replaced the whole month. Schemes carry DIFFERENT last-NAV
    # dates (equity = Friday, liquid = Sunday), so a weekend month-end banked ~700
    # liquid funds and silently dropped the entire equity cross-section.
    # THE FIX: take each scheme's own latest row, then keep — per (scheme, month) —
    # the latest-dated row across old+new. Idempotent and self-healing: mid-month
    # writes are provisional and later runs replace them; the first run on/after
    # month-end banks the true month-end row for every scheme.
    me_path = os.path.join(OUT, "nav_monthend.parquet")
    latest_navdate = df["date"].max()
    hist = pd.read_parquet(me_path) if os.path.exists(me_path) else pd.DataFrame()
    add = (df.sort_values("date").groupby("scheme_code", as_index=False).last()
             [["scheme_code", "isin", "name", "nav", "date"]])
    both = pd.concat([hist, add], ignore_index=True)
    both["ym"] = pd.to_datetime(both["date"]).dt.to_period("M").astype(str)
    both = both.sort_values("date").groupby(["scheme_code", "ym"], as_index=False).last()
    both.drop(columns=["ym"]).to_parquet(me_path, index=False)
    print(f"NAV refresh OK: {len(df):,} schemes, nav-date {latest_navdate.date()}, raw snapshots kept <= {RETAIN_DAYS}d")
    if digest:
        eq = df[df["category"].str.contains("Equity", case=False, na=False)]
        with io.open(os.path.join(OUT, "NAV_DIGEST.md"), "w", encoding="utf-8") as f:
            f.write(f"# MF NAV digest — {latest_navdate.date()}\n\n"
                    f"- Schemes: {len(df):,} (equity-category rows: {len(eq):,})\n"
                    f"- Source: AMFI NAVAll.txt (official), D-009 checks passed\n"
                    f"- Files: nav_latest.parquet (full cross-section) · nav_monthend.parquet "
                    f"({len(pd.read_parquet(me_path)['date'].unique())} month-ends)\n"
                    f"- Retention: raw snapshots {RETAIN_DAYS}d; month-end history permanent\n")
        print("digest written")


if __name__ == "__main__":
    main(digest="--digest" in sys.argv)
