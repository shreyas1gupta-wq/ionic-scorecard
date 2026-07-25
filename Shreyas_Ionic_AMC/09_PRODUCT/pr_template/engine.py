# -*- coding: utf-8 -*-
"""engine.py — v9 template registry + build(). Modules live in modules/<id>.py, each exposing
render(deck, ctx, tier). MODULES lists them in canonical order with core/optional + section.
build(ctx, tier_name) renders selected modules to one Deck and returns it.

A module render() may return an int = number of slides it added (for the manifest); default 1.
Missing/erroring modules are logged and skipped so a partial library still renders (self-heal-friendly).
"""
import os, importlib, traceback
import slidekit
import tiers as T

# (module_id, section_no, section_name, core?)  — canonical order (spec §2)
MODULES = [
    ("cover",              0, "",              True),
    ("contents_legend",    0, "",              True),
    ("ips_summary",        0, "Understanding", True),
    ("exec_summary",       0, "Understanding", True),
    ("mandate_method",     0, "Understanding", True),
    ("_div1",              1, "Portfolio X-ray", True),
    ("snapshot",           1, "Portfolio X-ray", True),
    ("allocation_house_view", 1, "Portfolio X-ray", True),
    ("concentration_risk", 1, "Portfolio X-ray", True),
    ("sector_exposure",    1, "Portfolio X-ray", True),
    ("mcap_positioning",   1, "Portfolio X-ray", True),
    ("_div2",              2, "The Equity Book", True),
    ("score_method",       2, "The Equity Book", True),
    ("book_scored",        2, "The Equity Book", True),
    ("equity_book",        2, "The Equity Book", True),
    ("sell_list",          2, "The Equity Book", True),
    ("hold_rationale",     2, "The Equity Book", True),
    ("_div3",              3, "The Fund Book",  True),
    ("fund_book_scored",   3, "The Fund Book",  True),
    ("funds_equity",       3, "The Fund Book",  True),
    ("funds_hybrid",       3, "The Fund Book",  True),
    ("fund_category_rules", 3, "The Fund Book", True),
    # fund_quality_alloc: PARKED per Principal 2026-07-25 (quadrant graph cut; MF calls come from
    # the desk's own framework, not this deck) — module kept in the library, rendered nowhere.
    ("fund_quality_alloc", 5, "Annexure",       False),
    ("fund_overlap",       3, "The Fund Book",  True),
    ("fund_actions",       3, "The Fund Book",  True),
    ("_div4",              4, "Recommendations", True),
    ("house_view_fit",     4, "Recommendations", True),
    ("cost",               4, "Recommendations", True),
    ("tax_impact",         4, "Recommendations", True),
    ("deployment",         4, "Recommendations", True),
    ("before_after",       4, "Recommendations", True),
    ("priority_actions",   4, "Recommendations", True),
    # ---- F18 cut line: optional annexure ----
    ("_div5",              5, "Annexure",       False),
    ("opportunity_set",    5, "Annexure",       False),
    ("quality_vs_price",   5, "Annexure",       False),
    ("factor_profile",     5, "Annexure",       False),
    ("growth_projection",  5, "Annexure",       False),
    ("spotlight_holdings", 5, "Annexure",       False),
    ("holdings_detail",    5, "Annexure",       False),
    ("sell_cards",         5, "Annexure",       False),
    ("scheme_overlap_full", 5, "Annexure",      False),
    ("scheme_scorecards",  5, "Annexure",       False),
    # ---- extended visual annexure (18 illustrations) ----
    ("annex_score_vs_call", 5, "Annexure",      False),
    ("annex_valuation_bands", 5, "Annexure",    False),
    ("annex_returns_quilt", 5, "Annexure",      False),
    ("annex_correlation",  5, "Annexure",       False),
    ("annex_risk_contribution", 5, "Annexure",  False),
    ("annex_stress_scenarios", 5, "Annexure",   False),
    ("annex_beta_ladder",  5, "Annexure",       False),
    ("annex_concentration_curve", 5, "Annexure", False),
    ("annex_liquidity_ladder", 5, "Annexure",   False),
    ("annex_currency_geo", 5, "Annexure",       False),
    ("annex_mcap_migration", 5, "Annexure",     False),
    ("annex_income_ladder", 5, "Annexure",      False),
    ("annex_seasonality",  5, "Annexure",       False),
    ("annex_drawdown_history", 5, "Annexure",   False),
    ("annex_sip_vs_lumpsum", 5, "Annexure",     False),
    ("annex_goal_mapping", 5, "Annexure",       False),
    ("annex_fee_compounding", 5, "Annexure",    False),
    ("annex_tax_lot_aging", 5, "Annexure",      False),
    ("appendix",           5, "Annexure",       False),
    ("disclaimer",         0, "",               True),  # always on, tier-exempt
]


def _load(mod_id):
    try:
        return importlib.import_module(f"modules.{mod_id}")
    except Exception:
        return None


def build(ctx, tier_name, verbose=True):
    tier = T.get(tier_name)
    deck = slidekit.new_deck()
    manifest = []
    for mod_id, sec_no, sec_name, core in MODULES:
        # selection
        if mod_id.startswith("_div"):
            included = True
        elif core:
            included = mod_id not in tier.get("skip_core", set())
        else:
            included = mod_id in tier["optional_on"]
        if not included:
            continue
        if mod_id.startswith("_div"):
            # section divider — skip empty sections for light tiers handled implicitly
            titles = {1: ("Portfolio X-ray", "Where the book stands today"),
                      2: ("The Equity Book", "Every direct holding, scored and read"),
                      3: ("The Fund Book", "Upside, downside and consistency — not just returns"),
                      4: ("What We Would Do", "The plan, the cost, the tax and the sequence"),
                      5: ("Annexure", "Detail, on request")}
            t, sub = titles.get(sec_no, (sec_name, ""))
            deck.section_divider(sec_no, t, sub)
            manifest.append((mod_id, 1)); continue
        m = _load(mod_id)
        if m is None or not hasattr(m, "render"):
            if verbose: print(f"  [skip] {mod_id}: not implemented")
            continue
        try:
            n = m.render(deck, ctx, tier)
            manifest.append((mod_id, n if isinstance(n, int) else 1))
        except Exception as e:
            if verbose: print(f"  [ERR ] {mod_id}: {e}")
            if os.environ.get("PR_TRACE"): traceback.print_exc()
    return deck, manifest
