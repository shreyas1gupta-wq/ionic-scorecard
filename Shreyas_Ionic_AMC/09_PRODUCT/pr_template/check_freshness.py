# -*- coding: utf-8 -*-
"""check_freshness.py — QA gate 4: is the data behind this deck actually current?

FM comment #4 (2026-08-05): "In your QA engine, outdated files should be flagged. Monthly asset X,
MF data etc." He is right, and the first ACE MF extract showed the ask is understated in two ways:

  * The FILENAME lied about the date. It read "31th July_2026" while every holdings-derived block
    inside was stamped 202606 (30-June). A gate that trusts filenames or mtimes learns nothing.
  * 40.5% of rows were behind the file's own modal month-end, some dating to 2018. So staleness is
    a PER-FUND, PER-BLOCK property. A file-level check passes the file while a client's own fund
    silently carries seven-year-old allocation data.

This gate therefore checks three different things, because they fail independently:
  1. FILE age      - is the artefact itself old (mtime)?
  2. CONTENT as-of - what date does the data inside claim (never the filename)?
  3. ROW as-of     - within a current file, which specific funds are behind?

Also covers the non-MF sources, because the Angel option capture silently wrote nothing for two
days in Aug-2026 while its directory mtimes kept moving (it overwrites parquet in place), and no
gate noticed. Directory mtimes are never trusted here; only file mtimes and in-file dates.

Usage
  python check_freshness.py                       # all configured sources
  python check_freshness.py --ace <extract.xlsx>  # add row-level ACE checks
  python check_freshness.py --isins a,b,c         # restrict row checks to a client's holdings
Exit code 1 if any source is STALE at its threshold, so it can gate a build.
"""
import argparse
import datetime as dt
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "lib"))

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def _nifty_root(start):
    """The real 'NIFTY 500' tree, found by walking up.

    Naive dirname(ROOT) resolves to the WORKTREE root when this runs from a git worktree
    (.../NIFTY 500/.claude/worktrees/<name>/), and the shared data - the MF Dashboard workbook, the
    NAV store, the Angel capture output - lives in the main tree, not the worktree. The first run of
    this gate reported three sources MISSING for exactly that reason, which is the wrong answer in
    the most dangerous direction: a freshness gate that cannot find a file must not look like a
    freshness gate that found a fresh file."""
    d = os.path.abspath(start)
    while True:
        if os.path.basename(d) == "NIFTY 500":
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return os.path.dirname(start)      # give up; caller reports MISSING honestly
        d = parent


NIFTY = _nifty_root(ROOT)

# Thresholds in days. Defaults chosen from each source's own refresh cadence, doubled, so a single
# missed run warns rather than fails. The FM sets the final numbers (his C5); these are placeholders
# that are honest about being placeholders.
SOURCES = [
    # (label, path, max_age_days, cadence note)
    ("ACE MF extract (monthly)",
     None, 45, "monthly from the advisory; 45d = one missed month"),
    ("MF Dashboard workbook",
     os.path.join(NIFTY, "MF Dashboard.xlsx"), 120, "Apr/Oct anchors, so ~6-monthly"),
    ("Fund month-end NAV store",
     os.path.join(NIFTY, "datasets", "mf_nav", "nav_monthend.parquet"), 45,
     "monthly on the 1st"),
    ("QFRA-2 recommendations",
     r"C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2"
     r"\mr_x_framework\outputs\recommendations\QFRA2_current.csv", 200,
     "6-monthly model run"),
    # Limit is in WEEKDAYS for this one, and it is 1. A 3-calendar-day limit passed the real
    # Aug-2026 outage: the capture last wrote on 03-Aug and the gate still said "ok" on 05-Aug
    # because 1.7 days rounded under 3. For a job that runs three times every trading day, no write
    # since yesterday's close IS the alarm. Weekday counting is what stops a flat 1-day limit
    # crying wolf every Monday.
    ("Angel option capture",
     None, 1, "daily post-close; newest FILE mtime, weekday-aged, never directory mtime"),
]

ANGEL_OUT = os.path.join(NIFTY, "intraday_options_strategy", "datasets", "angel_capture_2026")


def _age_days(path):
    if not path or not os.path.exists(path):
        return None
    return (dt.datetime.now() - dt.datetime.fromtimestamp(os.path.getmtime(path))).days


def _weekdays_between(then, now):
    """Weekdays elapsed, so a Friday-close write is 1 weekday old on Monday rather than 3 days old.
    Exchange holidays are not modelled; the effect is at most one extra day of tolerance, which errs
    toward silence rather than toward a false alarm."""
    d, n = then.date(), now.date()
    if n <= d:
        return 0
    days = 0
    cur = d
    while cur < n:
        cur += dt.timedelta(days=1)
        if cur.weekday() < 5:
            days += 1
    return days


def _newest_file_age(root, suffix=".parquet"):
    """Newest FILE mtime under root. Directory mtimes are useless for the capture, which
    overwrites parquet in place and so never moves a directory's timestamp."""
    newest = None
    for dp, _dn, fn in os.walk(root or ""):
        for f in fn:
            if f.endswith(suffix):
                m = os.path.getmtime(os.path.join(dp, f))
                if newest is None or m > newest:
                    newest = m
    if newest is None:
        return None, None
    ts = dt.datetime.fromtimestamp(newest)
    return (_weekdays_between(ts, dt.datetime.now()),
            ts.strftime("%Y-%m-%d %H:%M"))


def check(ace_path=None, isins=None, verbose=True):
    findings = []
    rows = []

    for entry in SOURCES:
        label, path, limit, note = entry[0], entry[1], entry[2], entry[3]

        if label.startswith("Angel"):
            age, when = _newest_file_age(ANGEL_OUT)
            detail = f"newest write {when}" if when else "no parquet found"
        elif label.startswith("ACE"):
            path = ace_path
            age = _age_days(path)
            detail = os.path.basename(path) if path else "not supplied"
        else:
            age = _age_days(path)
            detail = os.path.basename(path) if path else "-"

        if age is None:
            state = "MISSING"
            findings.append(f"{label}: MISSING ({detail})")
        elif age > limit:
            state = "STALE"
            findings.append(f"{label}: STALE - {age}d old, limit {limit}d ({detail})")
        else:
            state = "ok"
        rows.append((label, state, f"{age}d" if age is not None else "-", f"{limit}d", detail))

    # ---- content and row level, only possible for the ACE extract -------------------------
    ace_rows = []
    if ace_path and os.path.exists(ace_path):
        import acemf
        df, meta = acemf.load(ace_path)

        # CONTENT as-of vs the filename. The filename is not evidence.
        fname_year_month = None
        base = os.path.basename(ace_path)
        for mon, num in (("jan", "01"), ("feb", "02"), ("mar", "03"), ("apr", "04"),
                         ("may", "05"), ("jun", "06"), ("jul", "07"), ("aug", "08"),
                         ("sep", "09"), ("oct", "10"), ("nov", "11"), ("dec", "12")):
            if mon in base.lower():
                yr = "".join(c for c in base if c.isdigit())[-4:]
                fname_year_month = f"{yr}{num}"
                break
        if fname_year_month and meta["file_asof"] and fname_year_month != meta["file_asof"]:
            findings.append(
                f"ACE MF: FILENAME/CONTENT MISMATCH - name implies {fname_year_month}, "
                f"data is stamped {meta['file_asof']}. Label pages from the data, not the name.")

        # ROW level, per block
        sub = df
        if isins:
            want = {s.strip().upper() for s in isins if s.strip()}
            sub = df[df["ISIN Code"].astype(str).str.upper().isin(want)]
            if len(sub) == 0:
                findings.append(f"ACE MF: none of the {len(want)} supplied ISINs are in the extract")

        for blk in ("asset_allocation", "sector_allocation", "maturity_ytm", "expense"):
            stale = acemf.stale_rows(sub, blk, asof=meta["block_asof"].get(blk))
            pct = (len(stale) / len(sub) * 100) if len(sub) else 0.0
            ace_rows.append((blk, meta["block_asof"].get(blk), len(stale), len(sub), pct))
            # A client's own holdings carrying stale data is a hard stop; a background rate across
            # the whole 19k-row universe is context, not a defect.
            if isins and len(stale):
                findings.append(
                    f"ACE MF [{blk}]: {len(stale)} of {len(sub)} CLIENT holdings are behind "
                    f"{meta['block_asof'].get(blk)} - do not print these figures unlabelled")

    if verbose:
        print(f"{'SOURCE':32s} {'STATE':8s} {'AGE':>6s} {'LIMIT':>6s}  DETAIL")
        print("-" * 96)
        for label, state, age, limit, detail in rows:
            print(f"{label:32s} {state:8s} {age:>6s} {limit:>6s}  {detail[:34]}")
        if ace_rows:
            print()
            print(f"{'ACE BLOCK':24s} {'AS-OF':>8s} {'STALE ROWS':>12s} {'OF':>7s} {'%':>7s}")
            print("-" * 96)
            for blk, asof, n, tot, pct in ace_rows:
                print(f"{blk:24s} {str(asof):>8s} {n:>12d} {tot:>7d} {pct:>6.1f}%")
        print()
        if findings:
            print(f"{len(findings)} FINDING(S):")
            for f in findings:
                print(f"  - {f}")
        else:
            print("0 findings")
    return findings


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ace", help="path to the ACE MF Advisory-V2 extract")
    ap.add_argument("--isins", help="comma-separated ISINs to restrict row-level checks to")
    a = ap.parse_args()
    f = check(a.ace, a.isins.split(",") if a.isins else None)
    sys.exit(1 if f else 0)
