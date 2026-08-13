# -*- coding: utf-8 -*-
"""hybrid_benchmark.py — per-fund BLENDED benchmark for hybrid schemes (FM #20, Principal
2026-08-06: "you create method basis adjusted bm and best possible").

THE PROBLEM THIS FIXES
-----------------------
Balanced Advantage funds alone range from 52.8% to 90.4% equity (research on file). Measuring
every hybrid against ONE fixed-ratio index (today: "NIFTY 50 Hybrid Composite 65:35", see
data/azby_family.py's BENCH dict and funds_hybrid.py's slide caption) punishes whichever manager
was correctly defensive and flatters whichever one happened to run hot equity in an up market —
it is comparing funds to a benchmark most of them were never trying to track.

THE FIX
-------
Build each fund ITS OWN benchmark from its own disclosed mix:
    blended_return = equity_pct% x EQUITY_LEG_INDEX return
                    + debt_pct%   x DEBT_LEG_INDEX return
                    + others_pct% x OTHERS proxy return
EQUITY_LEG_INDEX = NIFTY 500 TRI, not a cap-specific index: ACE's hybrid disclosure gives an
equity/debt/others split, not a cap-wise breakdown of the equity sleeve, so a single broad-market
proxy is the most defensible choice — and it matches this codebase's own existing convention
(azby_family.py already treats "NIFTY 500 TRI" as the broad-market factor; SKILL.md's category
map already uses it for "Flexi"). DEBT_LEG_INDEX = "NIFTY Composite Debt Index" — reused, not
invented: it is the exact debt-leg name already used inside today's fixed 65:35 composite
(data/azby_family.py: "NIFTY 50 Hybrid Composite 65:35": rmkt*0.65 + rbond, "NIFTY Composite Debt
Index": rbond). OTHERS proxy = the risk-free rate (CONFIG, same number as #15's ruling, not a
second invented figure) — ACE's "Others" bucket (cash/gold/REIT/misc residual) has no single
clean index, and treating an undifferentiated residual at the risk-free rate is a conservative,
stated default, flagged for improvement once "Others" is disclosed at finer grain.

DEGRADATION PATH, STATED HONESTLY (per the task brief)
--------------------------------------------------------
ACE gives a month-end SNAPSHOT, not a history. A genuine "trailing 3-year average mix" needs 36
monthly extracts accumulated over time. record_snapshot() below appends today's mix to a small
append-only store every time a new ACE file lands; trailing_mix() then reports:
  - "trailing-Nmo-average" once >=MIN_MONTHS_FOR_TRAILING_AVG (6 — a documented default: two
    points barely differ from a single snapshot and would misleadingly claim a stabilised
    number, so we wait for a real quarter's worth before calling it an average) months exist.
  - "current-mix" otherwise — the Principal's own words, used verbatim rather than "3-year-
    average mix" (Principal 2026-08-05 ruling per MF_SELL_METHOD_SPEC.md). The method gets more
    accurate every month it runs; nothing pretends to be right on the first file.

ONE INTERFACE DELIBERATELY LEFT UNBUILT (separate in-flight workstream, 2026-08-06)
---------------------------------------------------------------------------------------
lib.benchmark_returns.get_series(index_key, start_date, end_date) -> list[float] | None
    Periodic (monthly) % returns for one named index (e.g. "NIFTY 500 TRI",
    "NIFTY Composite Debt Index") between two dates, aligned month-to-month. THIS IS THE ENTIRE
    CONTRACT THIS MODULE NEEDS — one function, one signature. Every figure below (blended_return,
    down_capture_vs_blended, total_capture_6m) is built from it via _blended_series(); until it
    exists, every function here returns None plus an explicit gap reason, never a guessed number.
"""
import os
import csv
import datetime as _dt

CONFIG = {
    # Reused from the house's OWN existing fixed-ratio composite (see module docstring) — not a
    # new invention.
    "EQUITY_LEG_INDEX": "NIFTY 500 TRI",
    "DEBT_LEG_INDEX": "NIFTY Composite Debt Index",
    # Others proxy: same number as #15's ruling, reused rather than a second invented figure.
    "RISK_FREE_RATE": 0.065,
    # Degradation threshold — see module docstring for the justifying sentence.
    "MIN_MONTHS_FOR_TRAILING_AVG": 6,
    "TRAILING_WINDOW_MONTHS": 36,     # "3-year average" per the spec, once enough months exist
}

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))                      # .../pr_template/lib
_AMC_ROOT = os.path.abspath(os.path.join(_LIB_DIR, "..", "..", ".."))      # .../Shreyas_Ionic_AMC
DEFAULT_STORE_PATH = os.path.join(_AMC_ROOT, "05_DATA_OFFICE", "mf_mix_history.csv")
_STORE_FIELDS = ["key", "scheme_name", "asof_month", "equity_pct", "debt_pct", "others_pct"]


# ------------------------------------------------------------------------------------------------
# Monthly-mix accumulator
# ------------------------------------------------------------------------------------------------
def _fund_key(fund):
    return str(fund.get("isin") or fund.get("ISIN") or fund.get("name") or "").strip()


def record_snapshot(funds, asof_month, store_path=None):
    """Append one row per fund (that has a disclosed equity_gross_pct) for this ACE month, keyed
    by (key, asof_month). Idempotent: re-running on the same month is a no-op, so a re-build never
    double-counts a month. `asof_month` should be a 'YYYY-MM' string — the calendar month the ACE
    block's own as-of date falls in (use acemf.block_asof(), never the filename — see acemf.py)."""
    store_path = store_path or DEFAULT_STORE_PATH
    existing = set()
    if os.path.exists(store_path):
        with open(store_path, "r", newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                existing.add((row["key"], row["asof_month"]))
    new_rows = []
    for f in funds:
        g = f.get("equity_gross_pct")
        if g is None:
            continue
        key = _fund_key(f)
        if not key or (key, asof_month) in existing:
            continue
        d = f.get("debt_pct")
        o = f.get("others_pct")
        if d is None:
            d = max(0.0, 100.0 - g - (o or 0.0))
        if o is None:
            o = max(0.0, 100.0 - g - d)
        new_rows.append({"key": key, "scheme_name": f.get("name", ""), "asof_month": asof_month,
                          "equity_pct": round(g, 2), "debt_pct": round(d, 2), "others_pct": round(o, 2)})
    if not new_rows:
        return 0
    write_header = not os.path.exists(store_path)
    os.makedirs(os.path.dirname(store_path), exist_ok=True)
    with open(store_path, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_STORE_FIELDS)
        if write_header:
            w.writeheader()
        w.writerows(new_rows)
    return len(new_rows)


def _read_store(store_path):
    store_path = store_path or DEFAULT_STORE_PATH
    if not os.path.exists(store_path):
        return []
    with open(store_path, "r", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def trailing_mix(fund, store_path=None, months=None, cfg=None):
    """Resolve the mix to benchmark THIS fund against — see module docstring's degradation path.
    Returns {"equity_pct", "debt_pct", "others_pct", "basis", "n_months"} or None if the fund has
    neither accumulated history nor a current ACE-derived equity_gross_pct (i.e. no ACE match at
    all — a coverage gap, not a guess)."""
    cfg = cfg or CONFIG
    months = months or cfg["TRAILING_WINDOW_MONTHS"]
    key = _fund_key(fund)
    rows = sorted((r for r in _read_store(store_path) if r["key"] == key),
                  key=lambda r: r["asof_month"])[-months:]
    n = len(rows)
    if n >= cfg["MIN_MONTHS_FOR_TRAILING_AVG"]:
        eq = sum(float(r["equity_pct"]) for r in rows) / n
        db = sum(float(r["debt_pct"]) for r in rows) / n
        ot = sum(float(r["others_pct"]) for r in rows) / n
        return {"equity_pct": eq, "debt_pct": db, "others_pct": ot,
                "basis": f"trailing-{n}mo-average", "n_months": n}
    g = fund.get("equity_gross_pct")
    if g is None:
        return None
    d = fund.get("debt_pct")
    o = fund.get("others_pct")
    if d is None:
        d = max(0.0, 100.0 - g - (o or 0.0))
    if o is None:
        o = max(0.0, 100.0 - g - d)
    return {"equity_pct": g, "debt_pct": d, "others_pct": o, "basis": "current-mix", "n_months": n}


# ------------------------------------------------------------------------------------------------
# Blended series / return, via the ONE pending interface
# ------------------------------------------------------------------------------------------------
def _blended_series(mix, start, end, cfg):
    """Per-period blended returns from lib.benchmark_returns.get_series(). Raises ImportError /
    AttributeError if that module/function doesn't exist yet — callers catch and turn it into a
    gap reason, never a fabricated series."""
    from lib import benchmark_returns as _bmk  # may raise ImportError — caller's job to catch
    if not hasattr(_bmk, "get_series"):
        raise AttributeError("lib.benchmark_returns has no get_series() yet")
    eq_s = _bmk.get_series(cfg["EQUITY_LEG_INDEX"], start, end) if mix["equity_pct"] > 0 else None
    db_s = _bmk.get_series(cfg["DEBT_LEG_INDEX"], start, end) if mix["debt_pct"] > 0 else None
    if (mix["equity_pct"] > 0 and eq_s is None) or (mix["debt_pct"] > 0 and db_s is None):
        return None
    n = len(eq_s) if eq_s is not None else len(db_s)
    if eq_s is not None and db_s is not None and len(eq_s) != len(db_s):
        return None  # misaligned series — refuse to blend rather than guess an alignment
    rf_period = (1 + cfg["RISK_FREE_RATE"]) ** (1.0 / 12) - 1.0
    out = []
    for i in range(n):
        r = 0.0
        if eq_s is not None:
            r += mix["equity_pct"] / 100.0 * eq_s[i]
        if db_s is not None:
            r += mix["debt_pct"] / 100.0 * db_s[i]
        r += mix["others_pct"] / 100.0 * rf_period
        out.append(r)
    return out


def blended_return(fund, start, end, store_path=None, cfg=None):
    """Total % return of this fund's OWN blended benchmark over [start, end].
    Returns (return_pct | None, mix | None, gap_reason | None)."""
    cfg = cfg or CONFIG
    mix = trailing_mix(fund, store_path, cfg=cfg)
    if mix is None:
        return None, None, "no disclosed mix on file for this fund (no ACE match yet)"
    try:
        series = _blended_series(mix, start, end, cfg)
    except ImportError:
        return None, mix, "lib.benchmark_returns not available yet (separate workstream, 2026-08-06)"
    except AttributeError as ex:
        return None, mix, str(ex)
    if series is None:
        return None, mix, "benchmark_returns.get_series() returned no data for one or both legs"
    total = 1.0
    for r in series:
        total *= (1.0 + r)
    return round((total - 1.0) * 100.0, 2), mix, None


# ------------------------------------------------------------------------------------------------
# Borrowed metrics, re-pointed at the blended benchmark
# ------------------------------------------------------------------------------------------------
def down_capture_vs_blended(fund, start, end, store_path=None, cfg=None):
    """Down-capture (QFRA-2 concept) against the fund's OWN blended benchmark instead of a fixed
    category one. Uses the fund's own NAV series (fund['nav'], already on every fund dict per the
    ctx schema) for the fund side; the benchmark side needs the pending get_series() interface.

    `start`/`end` must bracket the SAME period fund['nav'] covers, at the SAME period frequency
    (e.g. monthly) — this module has no per-NAV-point date list to infer that alignment from
    today's ctx schema (fund['nav'] is a bare list[float]), so it is the caller's job to supply
    dates it knows are aligned; if the resulting benchmark series comes back a different length
    than the fund's own return series, this refuses to blend rather than guess an alignment.
    Returns (down_capture_pct | None, gap_reason | None)."""
    cfg = cfg or CONFIG
    nav = fund.get("nav")
    if not nav or len(nav) < 3:
        return None, "insufficient NAV history on file for this fund"
    mix = trailing_mix(fund, store_path, cfg=cfg)
    if mix is None:
        return None, "no disclosed mix on file for this fund"
    fund_rets = [(nav[i] / nav[i - 1] - 1.0) for i in range(1, len(nav)) if nav[i - 1]]
    try:
        bmk_series = _blended_series(mix, start, end, cfg)
    except ImportError:
        return None, "lib.benchmark_returns not available yet (separate workstream, 2026-08-06)"
    except AttributeError as ex:
        return None, str(ex)
    if bmk_series is None or len(bmk_series) != len(fund_rets):
        return None, "benchmark_returns could not supply a blended series matching the fund's own NAV dates"
    down_periods = [(f_r, b_r) for f_r, b_r in zip(fund_rets, bmk_series) if b_r < 0]
    if not down_periods:
        return None, "no down-periods in the fund's own NAV window to measure against"
    fund_down = sum(f_r for f_r, _ in down_periods) / len(down_periods)
    bmk_down = sum(b_r for _, b_r in down_periods) / len(down_periods)
    if bmk_down == 0:
        return None, "benchmark showed zero average decline in its own down-periods"
    return round(100.0 * fund_down / bmk_down, 1), None


def total_capture_6m(fund, asof=None, store_path=None, cfg=None):
    """6-month total capture (QFRA-1 concept): fund's own 6-month return as a % of its blended
    benchmark's 6-month return over the SAME window — re-pointed at the blended benchmark instead
    of a fixed category one. Sign-aware by construction (a straight ratio already handles a fund
    falling less than a falling benchmark correctly; it is a genuine < 100% capture, not flipped).
    Returns (capture_pct | None, gap_reason | None)."""
    cfg = cfg or CONFIG
    asof = asof or _dt.date.today()
    start = asof - _dt.timedelta(days=183)
    fund_r = fund.get("ret_6m_pct")
    if fund_r is None:
        return None, "no 6-month return on file for this fund"
    bench_r, _mix, gap = blended_return(fund, start, asof, store_path, cfg)
    if bench_r is None:
        return None, gap or "blended benchmark return unavailable"
    if bench_r == 0:
        return None, "blended benchmark's own 6-month return is exactly zero"
    return round(100.0 * fund_r / bench_r, 1), None


def suitability_vs_ips(fund, ctx, cfg=None):
    """Does THIS fund's own disclosed mix fit the client's IPS Equity band? A different question
    from mf_sell_score._axis_ips_gap (which asks whether the BOOK, in aggregate, is within band)
    — reuses the same band, no second threshold invented.
    Returns (is_suitable: bool | None, gap_reason | None)."""
    ips = (ctx or {}).get("ips") or {}
    if not ips.get("on_file"):
        return None, "no IPS on file: assumed no restriction (#18/#23 pattern)"
    band = (ips.get("alloc_bands") or {}).get("Equity")
    g = fund.get("equity_gross_pct")
    if not band or g is None:
        return None, "no IPS Equity band or no disclosed equity% for this fund"
    lo, _, hi = band
    if lo <= g <= hi:
        return True, None
    return False, (f"fund's own equity mix ({g:.0f}%) sits outside the client's IPS Equity band "
                    f"({lo:.0f}-{hi:.0f}%)")
