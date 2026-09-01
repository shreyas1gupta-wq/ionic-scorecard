# -*- coding: utf-8 -*-
"""fund_ctx_adapter.py — auto-wire REAL fund calls into the NDPMS deck (Principal ruling
2026-07-26: no synthetic/manual fund numbers on real client decks).

Sources
  QFRA-1 (short-term): mf_capture_recomm.compute_category() — the verified capture engine
                       (BUY/SELL/HOLD per scheme at the latest anchor). THE ONLY FRAMEWORK
                       WITH A SELL VERDICT, and the only one with a replayed backtest.
  QFRA-2 (long-term):  QFRA2_current.csv (qfra_score, CALIBRE grade, loser_flags, hit_3y,
                       down_capture, asof) — the frozen long-term SELECTION engine. Emits
                       ACTIVE / INDEX CORE only. It has NO Sell verdict.

MERGE RULE — "originate and veto" (Principal ruling 2026-08-04, options A+B+C):
  * QFRA-1 originates the Sell (option B: the sell BASIS is QFRA-1, which is backtested).
  * QFRA-2 vetoes it when its CALIBRE grade is A or B, and the disagreement is SURFACED as a
    contradiction, never silently resolved (the Principal's explicit requirement, and
    NEXT_WEEK_QUEUE item 1d).
  * QFRA-2 can never originate a Sell (option C). The old `loser_flags > 0 OR qfra_score < 40`
    proxy is RETIRED (option A) — it fired on the engine's own rank-2 A-grade picks.
  * Structural actions (Redeem-to-Direct, mandate, liquid/debt/index consolidation) are exempt
    and set by the FM layer, not here — they need no framework Sell at all.
  * No client Buy is ever issued; this reviews existing holdings (Sell / Trim / Hold only).

Two caveats that must travel with any number this module produces:
  1. The legs are NOT independent — QFRA-1's HC is 40.5-47.5% of the QFRA-2 score. See merge_calls().
  2. QFRA-1's backtest is strong on BUY (+2.59% median, 66% hit) and WEAK on SELL (hit 49.3%
     pooled, below 50% in all six anchor pairs). See merge_calls() for the full honest reading.

Matching is CANONICAL-EXACT, never fuzzy (Principal standing order 2026-08-01). See _canon();
verification suite in test_fund_matching.py.

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

# CALIBRE grades that VETO a QFRA-1 Sell (Principal ruling 2026-08-04). A/B are the
# long-term engine's buy-side grades: in QFRA2_current.csv A maps to conviction High and
# B to Medium, while C is "Low/Index-lean" and D is the bottom. So an A or B grade is a
# positive long-term view and must never coexist silently with a client Sell.
CALIBRE_VETO_GRADES = ("A", "B")


_MFMAP = None


def _mf_mapping():
    """Load the shared identity-resolution tables (pr_template/lib/mf_mapping.py)."""
    global _MFMAP
    if _MFMAP is None:
        p = os.path.join(ROOT, "09_PRODUCT", "pr_template", "lib", "mf_mapping.py")
        spec = importlib.util.spec_from_file_location("mf_mapping", p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        _MFMAP = m
    return _MFMAP


# Decoration that NEVER distinguishes two funds: plan markers, growth/payout markers, the
# generic word "fund"/"scheme", and the "&"/"and" connector. Removed as WHOLE WORDS via regex,
# never as substrings — a naive `k.replace("g", "")` on the normalized string turns "large"
# into "lare" and "growth" markers cannot be stripped after normalization at all.
# Nothing carrying fund identity (large/mid/small/flexi/multi/focused/value/cap/series/
# numerals) may ever be added here.
_DECOR_RE = re.compile(
    r"\(\s*g\s*\)|\(\s*idcw\s*\)"
    r"|\b(?:direct|regular|reg|growth|option|plan|fund|scheme|idcw|dividend|payout"
    r"|reinvestment|and)\b",
    re.I)

# Source-decoration ABBREVIATIONS — verified equivalences only, same contract as
# mf_mapping.AMC_ALIASES: a curated table of known-identical variants, NOT a similarity
# scorer. Adding a pair here is a factual claim that both strings name the same scheme.
_TOKEN_EQUIV = {
    r"\bopp\b": "opportunities", r"\bopps\b": "opportunities",
    r"\bcos\b": "companies",
    r"\bequity\s+opp\b": "equity opportunities",
}


def _norm(name):
    return re.sub(r"[^a-z]", "", str(name).lower())


def _canon(name):
    """Canonical fund key: AMC aliases -> scheme renames -> abbreviations -> drop decoration.

    NO FUZZY MATCHING (Principal standing order, 2026-08-01: "REMOVE FUZZY ENTIRELY ALWAYS USE
    SONNET AND ONE FUND AT A TIME MAPPING GOOGLE SEARCH AND LOGICALLY EVALUATION ONLY").
    Every step is a lookup in a curated table or a deletion of a closed list of decoration
    words, applied identically to both sides. Two names match only if their canonical forms are
    IDENTICAL — no threshold, no best-match, no similarity score. A miss goes to `gaps` for a
    one-fund-at-a-time Sonnet + web-search pass; "not found" beats a wrong guess.

    Replaced the `_fuzzy_get` 85%-prefix matcher on 2026-08-04.
    """
    mm = _mf_mapping()
    s = mm.canonical_amc(str(name))
    for pat, rep in _TOKEN_EQUIV.items():
        s = re.sub(pat, rep, s, flags=re.I)
    s = _DECOR_RE.sub(" ", s)
    k = _norm(s)
    # Scheme renames, compared on the canonical form so decorated variants
    # ("ICICI Pru Bluechip Fund(G)") still resolve to the renamed scheme.
    for old, info in mm.SCHEME_RENAMES.items():
        if k == _norm(_DECOR_RE.sub(" ", mm.canonical_amc(old))):
            return _norm(_DECOR_RE.sub(" ", mm.canonical_amc(info["renamed_to"])))
    return k


def _exact_get(dic, name):
    """Canonical-exact lookup. Returns (value, note); (None, reason) on a miss.

    `dic` is keyed by _norm(); we re-key it canonically on the way in so both sides
    go through the identical transform."""
    key = _canon(name)
    if not key:
        return None, "empty name after canonicalization"
    canon_index = {}
    for k, v in dic.items():
        ck = _canon(k)
        canon_index.setdefault(ck, []).append((k, v))
    hits = canon_index.get(key, [])
    if len(hits) == 1:
        return hits[0][1], ""
    if len(hits) > 1:
        names = ", ".join(h[0] for h in hits)
        return None, (f"AMBIGUOUS: {len(hits)} entries share the canonical key "
                      f"'{key}' ({names}) — resolve by hand, never auto-pick")
    return None, ("no canonical-exact match — needs a one-fund-at-a-time Sonnet + "
                  "web-search mapping pass (no fuzzy fallback by design)")


def _load_qfra1():
    spec = importlib.util.spec_from_file_location(
        "mf_capture_recomm",
        os.path.join(ROOT, "05_DATA_OFFICE", "scripts", "mf_capture_recomm.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def qfra2_lookup(scheme_name, df=None):
    """Longest-prefix fuzzy match into QFRA2_current.csv. Returns row dict or None.

    *** CORRECTED 2026-08-04 — the previous docstring here was WRONG and caused a real defect. ***
    It claimed "QFRA-2 exports cover only the ~40 curated verdict funds", so a miss was a genuine
    coverage gap. It is not. QFRA2_current.csv = 8 categories x top-5 = 40 ROWS, a PUBLICATION SLICE.
    The engine actually ranks 99 Direct-plan funds (large 8 · largemid 5 · mid 8 · flexi 6 · multi 5 ·
    small 6 · focused 30 · value 31). A None from this function therefore means "not in the published
    top-5", NOT "not covered" — the fund may well have a real engine score one rank below the cut.
    Believing the old docstring put 6 substituted scores into a shipped client deck (Client A):
    3 Focused funds and 3 that only needed a rename resolved (ICICI Pru Bluechip -> ICICI Pru Large
    Cap; Kotak Emerging Equity -> Kotak Midcap). Before recording a gap: check
    Mf_qfra2/data/verified_navs_<cat>.csv and resolve renames via pr_template/lib/mf_mapping.py.
    Never fabricate a score for a miss (D-035) — that part of the old note stands.

    *** STANDING-ORDER VIOLATION, NOT YET FIXED: this function fuzzy-matches. *** Principal
    2026-08-01: "REMOVE FUZZY ENTIRELY ALWAYS USE SONNET AND ONE FUND AT A TIME MAPPING GOOGLE
    SEARCH AND LOGICALLY EVALUATION ONLY". client_intake.py was converted; this path was missed.
    Fix = normalized-exact + SCHEME_RENAMES only, everything else to the gaps list for a
    one-fund-at-a-time Sonnet mapping pass. Needs a go-ahead because it is on the intake path.
    """
    if df is None:
        df = pd.read_csv(QFRA2_CSV)
    rows = {str(r["fund"]): r for _, r in df.iterrows()}
    best, _note = _exact_get(rows, scheme_name)
    if best is None:
        return None
    # ---------------------------------------------------------------------------------
    # QFRA-2 NEVER PRODUCES A SELL (Principal ruling 2026-08-04, options A + C).
    # The frozen engine has no Sell verdict at all — it emits ACTIVE / INDEX CORE
    # (+ satellites) and is a top-2 SELECTION engine. The old line here was
    #     call = "Sell" if loser_flags > 0 or qfra_score < 40 else "Hold"
    # and it was retired for two demonstrated defects:
    #  (A) `loser_flags > 0` fired on the engine's OWN final-2 picks — Franklin India Equity
    #      Advantage Fund(G) is rank 2 in Large & Mid, score 80, grade A, conviction High,
    #      verdict ACTIVE, and that line called it a client Sell. SENTINEL is a
    #      shortlist-refinement screen (eff = blend - loser: prefer loser-clean INTO the
    #      top-5), never a verdict on a holding. RETIRED from the sell path entirely.
    #  (B) `qfra_score < 40` is a WITHIN-CATEGORY RANK percentile, so it sold a fixed
    #      fraction of every category by construction (N=5 -> bottom 20%, N=8 -> bottom 37%,
    #      N=30 -> bottom 40%) with no reference to whether the fund beats its benchmark.
    #      The sell BASIS is now QFRA-1, which has an actual backtest (906 formations) —
    #      see merge_calls() for the honest reading of how strong that backtest is.
    # What QFRA-2 contributes instead is a STANCE: a CALIBRE A/B grade VETOES a QFRA-1 Sell
    # and the disagreement is surfaced (never silently resolved). C/D grades do not veto.
    # `loser_flags` is still returned, for disclosure and FM review only.
    # ---------------------------------------------------------------------------------
    grade = str(best["merit_grade"]).strip().upper()[:1]
    flags = int(best.get("loser_flags", 0) or 0)
    stance = "Veto" if grade in CALIBRE_VETO_GRADES else "Neutral"
    return {"qfra": int(best["qfra_score"]), "merit": str(best["merit_grade"]),
            "hit3y": float(best.get("hit_3y_pct") or 0), "down_capture_lt": best.get("down_capture"),
            "grade_lt": grade, "stance_lt": stance, "loser_flags": flags,
            "rank_lt": int(best.get("rank") or 0), "verdict_lt": str(best.get("verdict") or ""),
            "asof_lt": str(best.get("asof"))}


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


def merge_calls(q1_call, q2=None):
    """ORIGINATE-AND-VETO rule (Principal ruling 2026-08-04, options A + B + C).

    Returns (call, note, contradiction) — `contradiction` is a string when the two frameworks
    materially disagree, and it MUST be surfaced to a human, never silently resolved.

      QFRA-1 originates.  It is the only framework with a Sell verdict AND the only one with a
                          replayed backtest (906 formations, 2012-2024, all 6 category sheets).
      QFRA-2 vetoes.      A CALIBRE **A or B** grade blocks the Sell -> Hold + CONTRADICTION.
                          C/D grades do not veto. QFRA-2 can never originate a Sell (it has no
                          Sell verdict; `loser_flags` was retired from this path — see
                          qfra2_lookup()).
      Nothing else sells. No coverage on either side -> Hold + a gap note. We never emit Buy
                          client-side; this reviews existing holdings (Sell / Trim / Hold only).

    *** HONEST READING OF QFRA-1'S SELL BACKTEST (measured 2026-08-04, do not overstate it) ***
    The 906-formation replay is strong on the BUY leg and WEAK on the SELL leg:
      BUY  cohort, Apr/Oct pooled : median +2.59%, plain mean +2.62%, hit 66%   <- robust
      SELL cohort, Apr/Oct pooled : median -0.57%, plain mean -0.13%, hit 49.3% <- ~coin flip
      SELL cohort, Apr/Oct SMALLCAP: median -1.05%, plain mean -0.92%, hit 44%  <- real but
                                     low-hit / tail-weighted (right rarely, but very right)
    `sell_hit` is BELOW 50% in every one of the six anchor pairs. So the sold funds went on to
    outperform slightly more often than not, pooled. The Sell leg is therefore directionally
    right in the typical case (negative median) with essentially no average edge outside
    smallcap. Treat a QFRA-1 Sell as a genuine but MODEST signal that still needs the analyst's
    reason to stand on -- never as "the backtest says sell". Evidence + full tables:
    04_RND_LAB/STOCK_SCORECARD_750/results/anchor_pair_study/{ANCHOR_PAIR_STUDY.md,
    anchor_pair_study_ext.py, ANCHOR_PAIR_EXT.csv}.

    The two frameworks are also NOT independent: QFRA-1's HC (6M total capture) IS QFRA-2's
    `_cap6`, weighted 0.30 in QFRA-2's blend, plus ~10.5% more from 3y down-capture -- the
    capture family is ~40% of the QFRA Score. Never write "two independent frameworks agree".
    """
    q1 = str(q1_call or "").strip().lower()
    q1_sell = q1 == "sell"
    q1_buy = q1 == "buy"
    grade = (q2 or {}).get("grade_lt") or ""
    stance = (q2 or {}).get("stance_lt") or ""
    rank = (q2 or {}).get("rank_lt") or 0
    verdict = ((q2 or {}).get("verdict_lt") or "").upper()
    have_q2 = bool(q2)

    # --- the contradiction the Principal named: QFRA-1 Sell vs a QFRA-2 A/B-grade buy-side view
    if q1_sell and have_q2 and stance == "Veto":
        extra = ""
        if rank and rank <= 2 and verdict.startswith("ACTIVE"):
            extra = (f" It is also rank {rank} in its category, i.e. one of the long-term "
                     f"engine's own final-2 picks.")
        return ("Hold",
                "long-term grade vetoes the short-term exit; held pending FM review",
                (f"CONTRADICTION: short-term framework says SELL while the long-term engine "
                 f"grades this {grade}.{extra} Resolved to HOLD (veto), NOT silently — this "
                 f"must appear in the FM review pack before the deck ships."))

    if q1_sell:
        if not have_q2:
            return ("Sell", "short-term framework at Sell; no long-term coverage to veto it",
                    ("SINGLE-FRAMEWORK SELL: no QFRA-2 coverage for this fund, so nothing could "
                     "veto. Needs explicit FM sign-off per the ionic-wealth-complete skill."))
        return ("Sell", f"short-term framework at Sell; long-term grade {grade} does not veto", None)

    # --- reverse disagreement: QFRA-1 wants to BUY something the long-term engine grades D
    if q1_buy and have_q2 and grade == "D":
        return ("Hold", "short-term Buy against a D grade; no client Buy is ever issued",
                (f"CONTRADICTION (reverse): short-term framework says BUY while the long-term "
                 f"engine grades this D. No Sell results either way, but the disagreement is "
                 f"logged rather than dropped."))

    return "Hold", "", None


def build_fund_entries(held):
    """held: list of dicts (name, category ∈ CAT_SHEETS or 'hybrid'/'passive', plan,
    weight_pct, value_inr, ter, holding_years). Returns (entries, gaps)."""
    q2 = pd.read_csv(QFRA2_CSV)
    mod = _load_qfra1()
    wb = _open_dashboard(mod)
    q1_cache = {}
    entries, gaps, contradictions = [], [], []
    for h in held:
        cat = h["category"]
        e = dict(h)
        lt = qfra2_lookup(h["name"], q2)
        if lt:
            e.update(qfra=lt["qfra"], merit=lt["merit"], hit3y=lt["hit3y"], data_asof=lt["asof_lt"],
                     qfra2_grade=lt["grade_lt"], qfra2_flags=lt["loser_flags"])
        else:
            # NOTE: a miss means "not in the published top-5", NOT "not covered" — the engine
            # ranks 99 Direct-plan funds. Check verified_navs_<cat>.csv before recording a gap.
            gaps.append(f"{h['name']}: not in the QFRA-2 published top-5 rows — check "
                        f"verified_navs_{cat}.csv for a real engine score before treating "
                        f"this as no coverage")
            e.update(qfra=None, merit="-", hit3y=None)
        st_rec = None
        if cat in CAT_SHEETS:
            if cat not in q1_cache:
                q1_cache[cat] = qfra1_calls(cat, mod, wb)
            hit, note = _exact_get(q1_cache[cat], h["name"])
            if hit:
                st_rec, fn, hc, anchor = hit
                if note:
                    gaps.append(f"{h['name']}: {note}")
                if not (st_rec and str(st_rec).strip() and str(st_rec).strip().lower() != "nan"):
                    # an empty recommendation is a DATA GAP, never a silent Hold (audit 2026-07-26)
                    st_rec = None
                    gaps.append(f"{h['name']}: QFRA-1 anchor rated no recommendation "
                                f"(incomplete NAV rows) — manual review")
                # FN = 6M downside capture, HC = 6M total capture (both vs category benchmark)
                e.update(down_capture=round(float(fn) * 100, 1) if fn == fn else None,
                         capture_asof=str(getattr(anchor, "date", lambda: anchor)()))
                # staleness gate: a QFRA-1 anchor older than one Apr/Oct cycle must be
                # acknowledged by the FM before the deck ships (audit 2026-07-26)
                try:
                    age_days = (pd.Timestamp.today() - pd.Timestamp(anchor)).days
                    if age_days > 245:
                        gaps.append(f"{h['name']}: QFRA-1 anchor {pd.Timestamp(anchor).date()} is "
                                    f"~{age_days // 30} months stale — FM must acknowledge before ship")
                except Exception:
                    pass
            else:
                gaps.append(f"{h['name']}: not in QFRA-1 {cat} sheet ({note})")
        else:
            gaps.append(f"{h['name']}: category '{cat}' has no QFRA-1 counterpart "
                        f"(single-framework; needs FM sign-off per skill)")
        if lt or st_rec:
            call, note, contra = merge_calls(st_rec or "Hold", lt)
            e.update(verdict=call, action=call.upper() if call == "Sell" else "HOLD",
                     merge_note=note, contradiction=contra)
            if contra:
                # a cross-framework disagreement must reach a human, never resolve silently
                # (NEXT_WEEK_QUEUE item 1d, implemented 2026-08-04)
                contradictions.append(f"{h['name']}: {contra}")
                gaps.append(f"{h['name']}: {contra}")
        else:
            e.update(verdict="Hold", action="HOLD", contradiction=None,
                     merge_note="no framework coverage — manual review")
        # NAV-series risk metrics need the AMFI wiring (next build step)
        e.setdefault("sortino", None); e.setdefault("calmar", None)
        e.setdefault("max_dd", None); e.setdefault("worst_1y", None)
        e.setdefault("flags", [])
        entries.append(e)
    # 3-tuple since 2026-08-04: contradictions are returned SEPARATELY so a caller cannot
    # lose them in the general gaps list. They are also appended to `gaps` for back-compat.
    return entries, gaps, contradictions


if __name__ == "__main__":
    # self-test (verification: Bandhan must NOT come out a Sell; Franklin India Equity
    # Advantage is the known A-grade / rank-2 name that must trip the contradiction gate
    # rather than ever being sold silently)
    test = [
        {"name": "Bandhan Small Cap Fund", "category": "small", "plan": "Direct",
         "weight_pct": 1.0, "value_inr": 1_000_000, "ter": 0.55, "holding_years": 2},
        {"name": "PGIM India Small Cap Fund", "category": "small", "plan": "Direct",
         "weight_pct": 1.0, "value_inr": 1_000_000, "ter": 0.55, "holding_years": 2},
        {"name": "Parag Parikh Flexi Cap Fund", "category": "flexi", "plan": "Direct",
         "weight_pct": 1.0, "value_inr": 1_000_000, "ter": 0.55, "holding_years": 4},
        {"name": "Franklin India Equity Advantage Fund", "category": "largemid",
         "plan": "Direct", "weight_pct": 1.0, "value_inr": 1_000_000, "ter": 0.55,
         "holding_years": 3},
    ]
    entries, gaps, contras = build_fund_entries(test)
    for e in entries:
        print(f"{e['name'][:34]:34s} verdict={e['verdict']:4s} qfra={e.get('qfra')} "
              f"grade={e.get('merit')} dcap={e.get('down_capture')} "
              f"note={e.get('merge_note', '')}")
    print("\ncontradictions (must reach a human):", contras or "none")
    print("gaps:", gaps or "none")


# ---------------------------------------------------------------------------------------
# Unit-testable merge behaviour, no data needed. `python -c "import fund_ctx_adapter as A;
# A.selftest_merge()"` — or it runs as part of test_fund_matching.py's sibling checks.
# ---------------------------------------------------------------------------------------
def selftest_merge():
    A = dict(grade_lt="A", stance_lt="Veto", rank_lt=2, verdict_lt="ACTIVE")
    B = dict(grade_lt="B", stance_lt="Veto", rank_lt=3, verdict_lt="ACTIVE")
    C = dict(grade_lt="C", stance_lt="Neutral", rank_lt=5, verdict_lt="ACTIVE")
    D = dict(grade_lt="D", stance_lt="Neutral", rank_lt=5, verdict_lt="ACTIVE")
    cases = [
        # (q1 call, q2 view, expected call, expect a contradiction?)
        ("Sell", A, "Hold", True),    # A-grade vetoes -> the Principal's named case
        ("Sell", B, "Hold", True),    # B-grade vetoes too
        ("Sell", C, "Sell", False),   # C does not veto -> sell stands
        ("Sell", D, "Sell", False),   # D does not veto
        ("Sell", None, "Sell", True), # single-framework sell -> needs FM sign-off
        ("Hold", A, "Hold", False),
        ("Hold", D, "Hold", False),
        ("Buy",  A, "Hold", False),   # never issue a client Buy
        ("Buy",  D, "Hold", True),    # reverse disagreement, logged not dropped
    ]
    bad = []
    for q1, q2, exp_call, exp_contra in cases:
        call, _note, contra = merge_calls(q1, q2)
        got = (call, bool(contra))
        if got != (exp_call, exp_contra):
            bad.append((q1, (q2 or {}).get("grade_lt"), got, (exp_call, exp_contra)))
    if bad:
        for b in bad:
            print("  MERGE FAIL q1=%s grade=%s got=%s want=%s" % b)
        raise AssertionError(f"{len(bad)} merge_calls case(s) failed")
    print(f"merge_calls: {len(cases)}/{len(cases)} cases pass "
          f"(QFRA-2 can never originate a Sell; A/B grade always vetoes and surfaces)")
    return True
