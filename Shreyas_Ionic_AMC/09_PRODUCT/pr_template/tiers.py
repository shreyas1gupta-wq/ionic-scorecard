# -*- coding: utf-8 -*-
"""tiers.py — v9 build presets. A tier selects which optional modules render, the language
register, and chart density. Content/numbers are identical across tiers (§1 of the spec)."""

TIERS = {
    "HNI_DEEP": {
        "label": "Family office / sophisticated HNI",
        "register": "hni",          # technical voice, full methodology
        "chart_density": "rich",
        "show_horizon_legs": True,
        "optional_on": {            # every annexure module on
            "deployment", "before_after",
            "opportunity_set", "quality_vs_price", "factor_profile", "growth_projection",
            "spotlight_holdings", "holdings_detail", "sell_cards", "scheme_overlap_full",
            "scheme_scorecards", "appendix",
            # extended visual annexure (Principal cut 2026-07-25: seasonality,
            # drawdown-history, sip-vs-lumpsum, fee-compounding, tax-lot-aging and the
            # glossary page are out of the client deck; modules stay in the library)
            "annex_score_vs_call", "annex_valuation_bands", "annex_returns_quilt",
            "annex_correlation", "annex_risk_contribution", "annex_stress_scenarios",
            "annex_beta_ladder", "annex_concentration_curve", "annex_liquidity_ladder",
            "annex_currency_geo", "annex_mcap_migration", "annex_income_ladder",
            "annex_goal_mapping",
        },
        "spotlight_count": 3,
    },
    "STANDARD": {
        "label": "Typical NDPMS client",
        "register": "std",          # professional, accessible
        "chart_density": "standard",
        "show_horizon_legs": False,
        "optional_on": {"deployment", "before_after", "opportunity_set", "growth_projection",
                        "spotlight_holdings", "appendix"},
        "spotlight_count": 2,
    },
    "RM_SIMPLE": {
        "label": "RM-led / newer investor — under 20 slides, plain language",
        "register": "simple",       # plain language, bigger type, fewer numbers
        "chart_density": "minimal",
        "show_horizon_legs": False,
        "optional_on": set(),       # core only
        "spotlight_count": 0,
        # RM-LITE redesign (Principal 2026-07-26): keep only the story beats — plan,
        # what you own, strong/weak picture, sells, funds, cost/tax, next steps.
        # Empty sections auto-drop their dividers (engine). Target ≤19 slides.
        "skip_core": {"contents_legend", "mandate_method", "allocation_house_view",
                      "group_concentration", "sector_exposure", "mcap_positioning",
                      "score_method", "book_scored", "hold_rationale", "funds_equity",
                      "funds_hybrid", "fund_category_rules", "house_view_fit",
                      "fund_quality_alloc", "fund_overlap"},
    },
}


def get(tier):
    if tier not in TIERS:
        raise SystemExit(f"unknown tier {tier}; choose {list(TIERS)}")
    t = dict(TIERS[tier]); t.setdefault("skip_core", set()); t["name"] = tier
    return t
