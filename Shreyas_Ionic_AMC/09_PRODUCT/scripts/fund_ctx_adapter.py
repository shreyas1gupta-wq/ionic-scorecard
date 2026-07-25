# -*- coding: utf-8 -*-
"""fund_ctx_adapter.py — auto-wire REAL fund calls into the NDPMS deck (Principal ruling
2026-07-26: no synthetic/manual fund numbers on real client decks).

Sources
  QFRA-2 (long-term):  QFRA2_current.csv (qfra_score, merit_grade, loser_flags, hit_3y,
                       down_capture, asof) — the frozen long-term engine's latest run.
  QFRA-1 (short-term): mf_capture_recomm.compute_category() — the verified capture engine
                       (BUY/SELL/HOLD per scheme at the latest anchor).
Merge rule (skill: agentic-fund-manager): a client-facing fund Sell requires BOTH
frameworks non-Hold; disagreement defaults HOLD (flagged); structural actions
(Redeem-to-Direct, mandate) are exempt and set by the FM layer, not here.

Usage
  from fund_ctx_adapter import build_fund_entries
  entries = build_fund_entries([
      {"name": "Parag Parikh Flexi Cap Fund", "category": "flexi", "plan": "Direct",
       "weight_pct": 7.5, "value_inr": 5_100_000, "ter": 0.55, "holding_years": 4.6}, ...])
Each entry returns the deck's funds-ctx keys (fund score, grade, verdict, captures,
hit-rate) with `data_asof` stamps. NAV-series risk metrics (sortino/maxDD/worst-year)
need the AMFI series wiring — returned as None for now and flagged in `gaps`.
"""
import os
import re
import sys
import importlib.util

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QFRA2_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001\Mf_qfra2\mr_x_framework\outputs\recommendations\QFRA2_current.csv"
DASHBOARD = os.path.join(os.path.dirname(ROOT), "MF Dashboard.xlsx")
CAT_SHEETS = {"large": ("large", "large2"), "largemid": ("largemid", "largemid2"),
              "mid": ("mid", "mid2"), "flexi": ("flexi", "flexi2"),
              "multi": ("multi", "multi2"), "small": ("small", "small2")}


def _norm(name):
    return re.sub(r"[^a-z]", "", str(name).lower())


def _prefix_len(a, b):
    n = 0
    while n < min(len(a), len(b)) and a[n] == b[n]:
        n += 1
    return n


def _fuzzy_get(dic, name, min_prefix=10):
    """Scheme names differ in suffix decoration across sources ('-Reg(G)', 'Fund', plan
    markers): match on the longest shared normalized prefix instead of exact keys."""
    key = _norm(name)
    if key in dic:
        return dic[key]
    best, best_n = None, 0
    for k, v in dic.items():
        n = _prefix_len(key, k)
        if n > best_n:
            best, best_n = v, n
    return best if best_n >= min_prefix else None


def _load_qfra1():
    spec = importlib.util.spec_from_file_location(
        "mf_capture_recomm",
        os.path.join(ROOT, "05_DATA_OFFICE", "scripts", "mf_capture_recomm.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def qfra2_lookup(scheme_name, df=None):
    """Longest-prefix fuzzy match into QFRA2_current.csv. Returns row dict or None.
    NOTE: QFRA-2 exports cover only the ~40 curated verdict funds — a held fund outside
    that set correctly returns None (gap = 'needs a QFRA-2 scoring run', never a made-up
    score; D-035)."""
    if df is None:
        df = pd.read_csv(QFRA2_CSV)
    key = _norm(scheme_name)
    best, best_len = None, 0
    for _, r in df.iterrows():
        n = _prefix_len(key, _norm(r["fund"]))
        if n > best_len and n >= 10:
            best, best_len = r, n
    if best is None:
        return None
    call = "Sell" if (best.get("loser_flags", 0) or 0) > 0 or best.get("qfra_score", 100) < 40 else "Hold"
    return {"qfra": int(best["qfra_score"]), "merit": str(best["merit_grade"]),
            "hit3y": float(best.get("hit_3y_pct") or 0), "down_capture_lt": best.get("down_capture"),
            "call_lt": call, "asof_lt": str(best.get("asof"))}


def _open_dashboard(mod):
    import openpyxl
    return openpyxl.load_workbook(mod.resolve_path(DASHBOARD), read_only=True, data_only=True)


def qfra1_calls(category, mod=None, wb=None):
    """Latest-anchor recommendation per fund for a category. Returns {norm_name: (rec, FN, HC)}."""
    mod = mod or _load_qfra1()
    wb = wb if wb is not None else _open_dashboard(mod)
    raw_name, cat2 = CAT_SHEETS[category]
    df, anchor = mod.compute_category(wb, raw_name, cat2, category, verbose=False)
    out = {}
    for _, r in df.iterrows():
        out[_norm(r["fund"])] = (str(r.get("recommendation", "HOLD")).title(),
                                 r.get("FN_downside_cap_6M"), r.get("HC_total_cap_6M"), anchor)
    return out


def merge_calls(call_lt, call_st):
    """Dual-framework rule: Sell only when BOTH non-Hold; disagreement -> Hold (flagged)."""
    lt_sell = call_lt == "Sell"
    st_sell = str(call_st).lower() == "sell"
    if lt_sell and st_sell:
        return "Sell", ""
    if lt_sell != st_sell:
        return "Hold", "frameworks disagree, defaulted Hold (dual-framework rule)"
    return "Hold", ""


def build_fund_entries(held):
    """held: list of dicts (name, category ∈ CAT_SHEETS or 'hybrid'/'passive', plan,
    weight_pct, value_inr, ter, holding_years). Returns (entries, gaps)."""
    q2 = pd.read_csv(QFRA2_CSV)
    mod = _load_qfra1()
    wb = _open_dashboard(mod)
    q1_cache = {}
    entries, gaps = [], []
    for h in held:
        cat = h["category"]
        e = dict(h)
        lt = qfra2_lookup(h["name"], q2)
        if lt:
            e.update(qfra=lt["qfra"], merit=lt["merit"], hit3y=lt["hit3y"], data_asof=lt["asof_lt"])
        else:
            gaps.append(f"{h['name']}: no QFRA-2 match (category coverage or naming)")
            e.update(qfra=None, merit="-", hit3y=None)
        st_rec = None
        if cat in CAT_SHEETS:
            if cat not in q1_cache:
                q1_cache[cat] = qfra1_calls(cat, mod, wb)
            hit = _fuzzy_get(q1_cache[cat], h["name"])
            if hit:
                st_rec, fn, hc, anchor = hit
                # FN = 6M downside capture, HC = 6M total capture (both vs category benchmark)
                e.update(down_capture=round(float(fn) * 100, 1) if fn == fn else None,
                         capture_asof=str(getattr(anchor, "date", lambda: anchor)()))
            else:
                gaps.append(f"{h['name']}: not in QFRA-1 {cat} sheet")
        else:
            gaps.append(f"{h['name']}: category '{cat}' has no QFRA-1 counterpart "
                        f"(single-framework; needs FM sign-off per skill)")
        if lt or st_rec:
            call, note = merge_calls(lt["call_lt"] if lt else "Hold", st_rec or "Hold")
            e.update(verdict=call, action=call.upper() if call == "Sell" else "HOLD", merge_note=note)
        else:
            e.update(verdict="Hold", action="HOLD", merge_note="no framework coverage — manual review")
        # NAV-series risk metrics need the AMFI wiring (next build step)
        e.setdefault("sortino", None); e.setdefault("calmar", None)
        e.setdefault("max_dd", None); e.setdefault("worst_1y", None)
        e.setdefault("flags", [])
        entries.append(e)
    return entries, gaps


if __name__ == "__main__":
    # self-test on three known names (verification: Bandhan must NOT come out a Sell)
    test = [
        {"name": "Bandhan Small Cap Fund", "category": "small", "plan": "Direct",
         "weight_pct": 1.0, "value_inr": 1_000_000, "ter": 0.55, "holding_years": 2},
        {"name": "PGIM India Small Cap Fund", "category": "small", "plan": "Direct",
         "weight_pct": 1.0, "value_inr": 1_000_000, "ter": 0.55, "holding_years": 2},
        {"name": "Parag Parikh Flexi Cap Fund", "category": "flexi", "plan": "Direct",
         "weight_pct": 1.0, "value_inr": 1_000_000, "ter": 0.55, "holding_years": 4},
    ]
    entries, gaps = build_fund_entries(test)
    for e in entries:
        print(f"{e['name'][:34]:34s} verdict={e['verdict']:4s} qfra={e.get('qfra')} "
              f"merit={e.get('merit')} dcap={e.get('down_capture')} note={e.get('merge_note', '')}")
    print("gaps:", gaps or "none")
