# -*- coding: utf-8 -*-
"""Unit tests for mf_sell_score.py (Layer 2-4) and the Layer-1 extensions in mf_sell_gates.py
(manual-override/avoid-list gate, refine_priority_with_score). Plain assert-based, matching the
house convention (see scripts/test_fund_matching.py) -- no new test-framework dependency.

Run: python test_mf_sell_score.py    (from this directory; exit 0 = all pass)
"""
import os
import sys

_LIB_DIR = os.path.dirname(os.path.abspath(__file__))
_PRT = os.path.abspath(os.path.join(_LIB_DIR, ".."))
if _PRT not in sys.path:
    sys.path.insert(0, _PRT)

import mf_sell_score as S
import mf_sell_gates as G

FAILS = []


def check(name, cond):
    if not cond:
        FAILS.append(name)
        print(f"FAIL: {name}")
    else:
        print(f"ok:   {name}")


# ---------------------------------------------------------------------------------------- curves
check("_sigmoid at midpoint == 50", abs(S._sigmoid(8.0, 8.0, 0.3) - 50.0) < 1e-6)
check("_sigmoid rises with x", S._sigmoid(16.0, 8.0, 0.3) > S._sigmoid(0.0, 8.0, 0.3))
check("_sigmoid bounded [0,100]", 0.0 <= S._sigmoid(1000, 8.0, 0.3) <= 100.0
      and 0.0 <= S._sigmoid(-1000, 8.0, 0.3) <= 100.0)
check("_sigmoid_desc falls with x", S._sigmoid_desc(0.6, 0.25, 9.2) < S._sigmoid_desc(0.0, 0.25, 9.2))

cfg = S.CONFIG
# performance axis
p_none, why = S._axis_performance(None, cfg)
check("performance axis: None gap -> None score with reason", p_none is None and bool(why))
p_zero, _ = S._axis_performance(0.0, cfg)
p_big, _ = S._axis_performance(30.0, cfg)
check("performance axis: bigger trailing gap scores higher", p_big > p_zero)
check("performance axis: fund exactly at benchmark scores low, not exactly 0",
      0.0 < p_zero < 15.0)

# risk-adjusted axis: floor-becomes-gate
r_floor, breach, _ = S._axis_risk_adjusted(0.0, cfg)
check("risk-adjusted: Sortino at floor forces score=100 + floor_breach", r_floor == 100.0 and breach is True)
r_neg, breach2, _ = S._axis_risk_adjusted(-0.4, cfg)
check("risk-adjusted: Sortino below floor also gates", r_neg == 100.0 and breach2 is True)
r_comfy, breach3, _ = S._axis_risk_adjusted(0.5, cfg)
check("risk-adjusted: Sortino at the comfortable reference scores near 0",
      r_comfy < 5.0 and breach3 is False)
r_mid, _, _ = S._axis_risk_adjusted(0.25, cfg)
check("risk-adjusted: monotonic between floor and comfortable", r_floor > r_mid > r_comfy)
r_none, _, why_r = S._axis_risk_adjusted(None, cfg)
check("risk-adjusted: no Sortino -> gap, not a fabricated score", r_none is None and bool(why_r))

# concentration axis: anchors reproduce house guidance exactly
c_concern, _ = S._axis_concentration(cfg["CONC_CONCERN_PP"], cfg)
check("concentration: anchor at 10% == CONC_SCORE_AT_CONCERN",
      abs(c_concern - cfg["CONC_SCORE_AT_CONCERN"]) < 1e-6)
c_extreme, _ = S._axis_concentration(cfg["CONC_EXTREME_PP"], cfg)
check("concentration: anchor at 20% == CONC_SCORE_AT_EXTREME",
      abs(c_extreme - cfg["CONC_SCORE_AT_EXTREME"]) < 1e-6)
c_half, _ = S._axis_concentration(cfg["CONC_CONCERN_PP"] / 2, cfg)
check("concentration: convex, not linear -- half the concern-pp scores <1/2 the concern-score",
      c_half < cfg["CONC_SCORE_AT_CONCERN"] / 2)
c_huge, _ = S._axis_concentration(80.0, cfg)
check("concentration: saturates toward 100 for extreme positions, never exceeds it", c_huge < 100.0 and c_huge > 90.0)
c_zero, _ = S._axis_concentration(0.0, cfg)
check("concentration: 0% position scores 0", c_zero == 0.0)

# persistence axis
pers_gap_reason = S._axis_persistence({}, cfg)
check("persistence: no data -> gap", pers_gap_reason[0] is None and bool(pers_gap_reason[1]))
pers_one = S._axis_persistence({"horizon_vs_bench": [("1Y", -2.0, 1.0)]}, cfg)
check("persistence: single horizon insufficient (not a pattern)", pers_one[0] is None)
pers_two = S._axis_persistence({"horizon_vs_bench": [("1Y", -2.0, 1.0), ("3Y", -1.0, 0.5)]}, cfg)
check("persistence: 2/2 behind -> 100", pers_two[0] == 100.0)
pers_mixed = S._axis_persistence(
    {"horizon_vs_bench": [("1Y", -2.0, 1.0), ("3Y", 5.0, 3.0)]}, cfg)
check("persistence: 1/2 behind -> 50", pers_mixed[0] == 50.0)

# --------------------------------------------------------------------------------- score_fund()
def _base_fund(**kw):
    f = dict(name="Test Fund", weight_pct=3.0, category="equity", sortino=1.2,
             is_stcg=None, action="HOLD", verdict="Hold")
    f.update(kw)
    return f


ctx_no_ips = {"ips": {"on_file": False}, "equity": [], "funds": [], "totals": {}}

r_clean = S.score_fund(_base_fund(), ctx_no_ips)
check("score_fund: a clean fund (good Sortino, small weight) lands in the hold band",
      r_clean["band"] == "hold")

r_conc = S.score_fund(_base_fund(weight_pct=35.0), ctx_no_ips)
check("score_fund: a 35% position alone drives a sell-band score (concentration axis)",
      r_conc["band"] == "sell" and r_conc["driver_axis"] == "concentration")

r_riskfloor = S.score_fund(_base_fund(sortino=-0.2), ctx_no_ips)
check("score_fund: Sortino floor breach forces the sell band regardless of everything else",
      r_riskfloor["band"] == "sell" and r_riskfloor["floor_breach"] is True)

r_stcg = S.score_fund(_base_fund(weight_pct=35.0, is_stcg=True), ctx_no_ips)
r_ltcg = S.score_fund(_base_fund(weight_pct=35.0, is_stcg=False), ctx_no_ips)
check("score_fund: STCG damps final_score more than LTCG on an identical raw score",
      r_stcg["final_score"] < r_ltcg["final_score"] < r_conc["final_score"] + 1e-6)
check("score_fund: STCG damping never suppresses an elevated score to zero",
      r_stcg["final_score"] >= cfg["TAX_DAMPING_FLOOR"])

# the floor cannot bind under today's defaults (documented in CONFIG) -- prove the MECHANISM
# under a perturbed config where it can, so the code path itself is actually exercised.
cfg_low_stcg = dict(cfg, TAX_DAMPING_STCG=0.05)
r_stcg_extreme = S.score_fund(_base_fund(weight_pct=35.0, is_stcg=True), ctx_no_ips, cfg=cfg_low_stcg)
check("score_fund: floor DOES bind once damping would otherwise push below it",
      abs(r_stcg_extreme["final_score"] - cfg["TAX_DAMPING_FLOOR"]) < 1e-6)

# _axis_ips_gap's "no IPS on file" path returns a real 0.0, not None (see its own docstring) --
# so forcing every axis to a genuine gap needs an IPS that IS on file (past that early return)
# but a ctx missing 'equity'/'funds' entirely, so lookthrough.equity_lookthrough_pct's direct
# ctx["equity"] access raises and _axis_ips_gap's except-branch is what returns None here.
ctx_broken = {"ips": {"on_file": True, "alloc_bands": {"Equity": (65, 78, 85)}}}
r_nothing = S.score_fund({"name": "No Data Fund"}, ctx_broken)
check("score_fund: a fund with zero measurable axes gets band='no_score', never a fabricated Hold",
      r_nothing["band"] == "no_score")
check("score_fund: with ctx present but no IPS on file, ips_gap is a real 0 (not a gap) -- a "
      "near-empty fund dict still lands in the hold band, not no_score, because position size "
      "(weight_pct) is the one thing always known about a real holding",
      S.score_fund({"name": "Thin Data Fund", "weight_pct": 1.0}, ctx_no_ips)["band"] == "hold")

# IPS-gap attribution
ctx_over_equity = {
    "ips": {"on_file": True, "alloc_bands": {"Equity": (65, 78, 85)}},
    "equity": [{"weight_pct": 90.0}], "funds": [], "totals": {"cash_pct": 0.0},
}
f_eq_oriented = _base_fund(equity_gross_pct=95.0)
f_debt_oriented = _base_fund(equity_gross_pct=5.0)
r_over_eq = S.score_fund(f_eq_oriented, ctx_over_equity)
r_over_debt = S.score_fund(f_debt_oriented, ctx_over_equity)
check("IPS gap: book over its equity band -> an equity-oriented fund feels the axis",
      (r_over_eq["axes"]["ips_gap"] or 0) > 0)
check("IPS gap: book over its equity band -> a debt-oriented fund does NOT feel the axis",
      (r_over_debt["axes"]["ips_gap"] or 0) == 0)

# --------------------------------------------------------------------------- Layer 3 discretion
band, note = S.apply_discretion("sell", override="discretion", reason="analyst read: thin data")
check("discretion: softening sell->discretion is allowed and records the reason",
      band == "discretion" and note)

raised = False
try:
    S.apply_discretion("hold", override="sell", reason="anything")
except ValueError:
    raised = True
check("discretion: raising hold->sell RAISES (one-directional enforced in code, not just prose)", raised)

raised2 = False
try:
    S.apply_discretion("sell", override="hold", reason=None)
except ValueError:
    raised2 = True
check("discretion: an override with no reason raises", raised2)

unchanged, note0 = S.apply_discretion("sell", override=None)
check("discretion: no override passed through unchanged", unchanged == "sell" and note0 is None)

# ------------------------------------------------------------------------------------ score_all
ctx_all = {
    "ips": {"on_file": False},
    "equity": [], "totals": {},
    "funds": [
        _base_fund(name="Gated Fund", gate_note="Grandfathered debt holding"),
        _base_fund(name="Big Position", weight_pct=35.0, action="SELL", verdict="Sell"),
        _base_fund(name="Quiet Hold", weight_pct=2.0, sortino=1.5, action="HOLD", verdict="Hold"),
        _base_fund(name="Hidden Risk", weight_pct=35.0, action="HOLD", verdict="Hold"),
    ],
}
summary = S.score_all(ctx_all)
check("score_all: a gated fund is skipped and gets sell_score=None",
      ctx_all["funds"][0]["sell_score"] is None and summary["n_gated"] == 1)
check("score_all: n_scored excludes the gated fund", summary["n_scored"] == 3)
check("score_all: escalation raised for a high score sitting on an existing Hold",
      any("Hidden Risk" in e["situation"] for e in summary["escalations"]))
check("score_all: no escalation for a high score that already has a non-Hold action",
      not any("Big Position" in e["situation"] for e in summary["escalations"]))
for e in summary["escalations"]:
    check(f"escalation shape complete for {e['situation'][:20]!r}",
          all(k in e for k in ("situation", "our_view", "counter_view", "what_would_settle_it")))

# --------------------------------------------------------------- mf_sell_gates.py Layer-1 extensions
restrictions = {"Big Position": {"restriction": "Locked-in, do not touch", "note": "family trust"}}
f1 = {"name": "Big Position", "action": "SELL", "verdict": "Sell", "category": "equity"}
a, v, note = G.apply_manual_override_gate(f1, restrictions, False, None)
check("manual override gate: a restriction forces Hold and records why",
      a == "HOLD" and v == "Hold" and "Locked-in" in note)

f2 = {"name": "Clean Fund", "action": "HOLD", "verdict": "Hold", "category": "equity"}
a2, v2, note2 = G.apply_manual_override_gate(f2, {}, True, "Principal flagged 2026-08-01")
check("manual override gate: an avoid-list hit forces Exit", a2 == "EXIT" and v2 == "Exit")

a3, v3, note3 = G.apply_manual_override_gate(f2, {}, False, None)
check("manual override gate: nothing on file -> pure passthrough, no note",
      a3 == "HOLD" and v3 == "Hold" and note3 is None)

hit, reason = G.check_avoid_list({"name": "X"}, ask_analyst_fn=None)
check("avoid-list: no callback -> nil, never blocks", hit is False and "nil" in reason)

hit2, _ = G.check_avoid_list({"name": "X"}, ask_analyst_fn=lambda f: True)
check("avoid-list: callback returning True -> hit", hit2 is True)

hit3, _ = G.check_avoid_list({"name": "X"}, ask_analyst_fn=lambda f: (_ for _ in ()).throw(RuntimeError("boom")))
check("avoid-list: a raising callback degrades to nil, never crashes the build", hit3 is False)

check("load_restrictions: no path -> empty map, never blocks", G.load_restrictions(None) == {})
check("load_restrictions: nonexistent path -> empty map, never blocks",
      G.load_restrictions("Z:/does/not/exist.xlsx") == {})

check("refine_priority_with_score: softens High->Low when the score reads hold-band",
      G.refine_priority_with_score("High", "hold") == "Low")
check("refine_priority_with_score: never raises Low->High",
      G.refine_priority_with_score("Low", "sell") == "Low")
check("refine_priority_with_score: passthrough when there's no band at all",
      G.refine_priority_with_score("High", None) == "High")
check("refine_priority_with_score: passthrough when priority itself is None",
      G.refine_priority_with_score(None, "hold") is None)

# regression: apply_to's existing 3-positional-arg call shape (data/azby_family.py's own call)
# must still work with zero behaviour change now that restrictions/ask_analyst_fn exist.
eq_reg, funds_reg = [], [dict(name="Reg Fund", category="equity", action="SELL", verdict="Sell",
                               weight_pct=5.0, holding_years=2.0)]
churn = G.apply_to(eq_reg, funds_reg, "2026-08-06")
check("apply_to: legacy 3-arg call shape still works unchanged", churn["pct"] == 5.0
      and funds_reg[0]["gate_note"] is None)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("ALL PASS")
sys.exit(0)
