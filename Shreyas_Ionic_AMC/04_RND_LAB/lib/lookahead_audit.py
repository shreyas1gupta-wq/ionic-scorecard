"""LOOKAHEAD-BIAS AUDIT BATTERY — D-028 (Principal order 2026-07-04).
Programmatic checks for the T1..T10 taxonomy in 07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md.
Owner: Dr. Sameer Bhat (E-027). Complements (does not replace) lib/guards.py L1-L7b.

Usage in a Gate-4 audit:
    from lookahead_audit import *
    findings = []
    findings += audit_pit_column(panel, event_col="q_end", avail_col="available_date",
                                 decision_col="signal_date")
    findings += audit_same_bar(trades, signal_col="signal_date", entry_col="entry_date")
    findings += audit_session(minute_bars, ts_col="ts")
    findings += audit_code(Path("my_backtest.py"))
    ratio = one_day_lag_test(run_backtest_with_lag)   # callable(extra_lag_days)->metric
    print(report(findings, lag_collapse=ratio))
Every function returns a list of finding dicts: {"check","severity","detail"} — empty list = clean.
severity: "FAIL" (leak), "WARN" (suspicious, human review), "INFO".
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd


def _f(check: str, severity: str, detail: str) -> dict:
    return {"check": check, "severity": severity, "detail": detail}


# ---------- T1: point-in-time availability ----------
def audit_pit_column(df: pd.DataFrame, event_col: str, avail_col: str,
                     decision_col: str | None = None) -> list[dict]:
    """Published data must be used no earlier than its availability date."""
    out = []
    if avail_col not in df.columns:
        return [_f("T1_pit", "FAIL", f"no '{avail_col}' column — event-dated data with no "
                   f"availability stamp is unusable for PIT work (landmine #3)")]
    ev = pd.to_datetime(df[event_col])
    av = pd.to_datetime(df[avail_col])
    bad = int((av < ev).sum())
    if bad:
        out.append(_f("T1_pit", "WARN", f"{bad} rows have {avail_col} BEFORE {event_col} "
                      f"(publication before the event it describes — source error?)"))
    if decision_col is not None:
        dc = pd.to_datetime(df[decision_col])
        leak = int((dc < av).sum())
        if leak:
            out.append(_f("T1_pit", "FAIL", f"{leak} rows use data at {decision_col} BEFORE "
                          f"its {avail_col} — hard lookahead"))
    return out


# ---------- T2: timezone ----------
def audit_tz(ts: pd.Series) -> list[dict]:
    """The HF landmine: daily stamps at 18:30 UTC are NEXT-day 00:00 IST."""
    t = pd.to_datetime(ts)
    out = []
    if getattr(t.dt, "tz", None) is None:
        out.append(_f("T2_tz", "WARN", "timestamps are tz-naive — confirm they are IST dates, "
                      "not raw UTC (landmine #1)"))
        sample = t.dt.time.astype(str)
        if (sample == "18:30:00").mean() > 0.5:
            out.append(_f("T2_tz", "FAIL", ">50% of stamps are exactly 18:30 — this is the UTC "
                          "daily-bar signature; convert tz then take .date (landmine #1)"))
    return out


# ---------- T3: same-bar execution ----------
def audit_same_bar(trades: pd.DataFrame, signal_col: str, entry_col: str) -> list[dict]:
    sg = pd.to_datetime(trades[signal_col])
    en = pd.to_datetime(trades[entry_col])
    same = int((en <= sg).sum())
    if same:
        return [_f("T3_same_bar", "FAIL", f"{same}/{len(trades)} trades enter ON OR BEFORE the "
                   f"signal bar — decision uses a price that finished forming after it (guards L5)")]
    return []


# ---------- T4: session boundary ----------
def audit_session(bars: pd.DataFrame, ts_col: str) -> list[dict]:
    t = pd.to_datetime(bars[ts_col])
    pre = int((t.dt.time < pd.Timestamp("09:15").time()).sum())
    if pre:
        return [_f("T4_session", "FAIL", f"{pre} bars before 09:15 IST in the panel — pre-open "
                   f"auction prints corrupt opens/gaps (landmine #2); filter time>=09:15")]
    return []


# ---------- T5: survivorship / universe ----------
def audit_universe_pit(members_by_date: dict, panel_symbols: set) -> list[dict]:
    """members_by_date: {snapshot_date: set(symbols)} from the 42-snapshot PIT xlsx.
    Flags panel names never present in ANY snapshot (creeping non-universe names) and
    reminds if only ONE snapshot is used (static universe = survivorship)."""
    out = []
    if len(members_by_date) <= 1:
        out.append(_f("T5_universe", "FAIL", "single/static universe snapshot in use — historical "
                      "screens on today's members = survivorship bias; use the 42 PIT snapshots"))
    all_members = set().union(*members_by_date.values()) if members_by_date else set()
    stray = panel_symbols - all_members
    if stray:
        out.append(_f("T5_universe", "WARN", f"{len(stray)} panel symbols never in any PIT "
                      f"snapshot (sample: {sorted(stray)[:5]})"))
    return out


# ---------- T6/T7 + code smells: static source scan ----------
_PATTERNS = [
    (r"\.shift\(\s*-", "FAIL", "T7: negative shift pulls FUTURE values into a feature "
     "(allowed only on an explicitly tagged # LABEL: column)"),
    (r"\.rank\(\s*pct\s*=\s*True\s*\)", "WARN", "T6: full-sample percentile rank — the "
     "percentile at time t includes future cross-sections unless applied per-date group"),
    (r"(?<!rolling\(\)\.)\.(mean|std)\(\)\s*(?!\s*#\s*trailing)", "WARN", "T6: bare .mean()/.std() — "
     "verify it is per-date/rolling/train-window, not full-sample normalization"),
    (r"pd\.merge\((?![^)]*direction)", "WARN", "T1/T7: exact-date merge — published data needs "
     "merge_asof(direction='backward') or an explicit availability lag"),
    (r"fillna\(method\s*=\s*['\"]bfill|\.bfill\(", "FAIL", "T7: backward-fill propagates future "
     "values into the past"),
    (r"train_test_split\((?![^)]*shuffle\s*=\s*False)", "WARN", "T9: shuffled train/test split on "
     "time series mixes future into train"),
]


def audit_code(path: Path) -> list[dict]:
    """Static scan of a backtest/feature file for the classic leak signatures."""
    out = []
    src = Path(path).read_text(encoding="utf-8", errors="replace")
    for i, line in enumerate(src.splitlines(), 1):
        code = line.split("#")[0] if "# LABEL:" not in line else ""
        for pat, sev, msg in _PATTERNS:
            if re.search(pat, code):
                out.append(_f("code_scan", sev, f"{Path(path).name}:{i}: {line.strip()[:90]} -> {msg}"))
    return out


# ---------- T9: OOS discipline ----------
def audit_oos_log(family: str, oos_open_count: int) -> list[dict]:
    if oos_open_count > 1:
        return [_f("T9_oos", "FAIL", f"family '{family}': final OOS opened {oos_open_count} times "
                   f"— SOP allows exactly ONCE; every look after the first is selection on the future")]
    return []


# ---------- The killer diagnostic: one-day-lag collapse ----------
def one_day_lag_test(run_with_lag, base_metric: float | None = None) -> dict:
    """run_with_lag(extra_lag_days:int)->float metric (e.g. total P&L points).
    A real edge degrades gracefully under +1 day of feature lag; a leak collapses.
    Returns {'base','lagged','collapse_ratio','verdict'}."""
    base = float(run_with_lag(0)) if base_metric is None else float(base_metric)
    lag = float(run_with_lag(1))
    if base <= 0:
        return {"base": base, "lagged": lag, "collapse_ratio": None,
                "verdict": "N/A (no positive base edge to test)"}
    ratio = (base - lag) / abs(base)
    verdict = ("FAIL — collapse >50%: strongly suggests leakage" if ratio > 0.50 else
               "WARN — 25-50% decay in one day: fast edge or partial leak, review" if ratio > 0.25 else
               "PASS — graceful decay")
    return {"base": base, "lagged": lag, "collapse_ratio": round(ratio, 3), "verdict": verdict}


# ---------- report ----------
def report(findings: list[dict], lag_collapse: dict | None = None) -> str:
    fails = [f for f in findings if f["severity"] == "FAIL"]
    warns = [f for f in findings if f["severity"] == "WARN"]
    verdict = "FAIL" if fails else ("PASS-WITH-FLAGS" if warns else "PASS")
    if lag_collapse and str(lag_collapse.get("verdict", "")).startswith("FAIL"):
        verdict = "FAIL"
    lines = [f"# LOOKAHEAD AUDIT -- verdict: {verdict}",
             f"FAIL: {len(fails)} | WARN: {len(warns)} (taxonomy: 07_RISK_OFFICE/LOOKAHEAD_CONTROLS.md, D-028)"]
    for f in fails + warns:
        lines.append(f"- [{f['severity']}] {f['check']}: {f['detail']}")
    if lag_collapse:
        lines.append(f"- one-day-lag test: base={lag_collapse['base']:.4g} lagged={lag_collapse['lagged']:.4g} "
                     f"collapse={lag_collapse['collapse_ratio']} -> {lag_collapse['verdict']}")
    return "\n".join(lines)


# ---------- self-test ----------
if __name__ == "__main__":
    ok = 0
    # T1: decision before availability must FAIL
    df = pd.DataFrame({"q_end": ["2025-03-31"], "available_date": ["2025-05-15"],
                       "signal_date": ["2025-04-01"]})
    r = audit_pit_column(df, "q_end", "available_date", "signal_date")
    assert any(x["severity"] == "FAIL" for x in r); ok += 1
    # T3: same-bar entry must FAIL
    tr = pd.DataFrame({"signal_date": ["2025-01-02"], "entry_date": ["2025-01-02"]})
    assert audit_same_bar(tr, "signal_date", "entry_date")[0]["severity"] == "FAIL"; ok += 1
    # T4: 09:00 bar must FAIL
    mb = pd.DataFrame({"ts": ["2026-01-05 09:00:00", "2026-01-05 09:15:00"]})
    assert audit_session(mb, "ts")[0]["severity"] == "FAIL"; ok += 1
    # code scan: negative shift must FAIL, bfill must FAIL
    p = Path(__file__).parent / "_la_selftest_tmp.py"
    p.write_text("x = df['close'].shift(-1)\ny = df.bfill()\n", encoding="utf-8")
    r = audit_code(p); p.unlink()
    assert sum(1 for x in r if x["severity"] == "FAIL") >= 2; ok += 1
    # lag test: fabricated collapse must FAIL
    r = one_day_lag_test(lambda lag: 100.0 if lag == 0 else 5.0)
    assert r["verdict"].startswith("FAIL"); ok += 1
    # lag test: graceful decay must PASS
    r = one_day_lag_test(lambda lag: 100.0 if lag == 0 else 85.0)
    assert r["verdict"].startswith("PASS"); ok += 1
    # clean frame -> PASS report
    clean = audit_same_bar(pd.DataFrame({"signal_date": ["2025-01-02"], "entry_date": ["2025-01-03"]}),
                           "signal_date", "entry_date")
    assert clean == []; ok += 1
    print(f"lookahead_audit self-test: {ok}/7 checks pass")
    print(report([_f("demo", "WARN", "example finding")]))
