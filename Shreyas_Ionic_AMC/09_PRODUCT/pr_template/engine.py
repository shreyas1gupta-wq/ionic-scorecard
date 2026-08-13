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
    # ips_summary: RESTORED 2026-07-28 (reverses the 2026-07-27 cut) -- rebuilt v2 with richer
    # parameter coverage and live-computed Current values. Renders ONLY when ctx["ips"]["on_file"]
    # is True (self-gates, always checked) -- a client with no bespoke IPS agreed yet gets no
    # slide at all rather than a page of TBD/Pending rows (Principal 2026-07-28).
    ("ips_summary",        0, "Understanding", True),
    # ips_seven_aspects: NEW (FM #5, Principal ruling 2026-08-06) -- the seven standard IPS
    # aspects (return/risk/liability/liquidity/timelines/tax/unique circumstances). Always
    # checked; self-degrades to "on file with the advisor" when ctx has no seven_aspects on
    # file, so a real client without them renders honestly rather than inheriting ABXY's
    # assumed demo values.
    ("ips_seven_aspects",  0, "Understanding", True),
    ("exec_summary",       0, "Understanding", True),
    # renders ONLY when the client profile has meeting_history (always checked)
    ("since_last_review",  0, "Understanding", True),
    ("mandate_method",     0, "Understanding", True),
    ("_div1",              1, "Portfolio X-ray", True),
    ("snapshot",           1, "Portfolio X-ray", True),
    # core_satellite: NEW (FM #1, Principal ruling 2026-08-06) -- a guidance READ of core vs
    # satellite construction against the mandate's own ~70/30 target (explicitly flexible,
    # never a pass/fail breach test -- see the module docstring). Midcap classifies as Core
    # per the ruling.
    ("core_satellite",     1, "Portfolio X-ray", True),
    # allocation_house_view: RETIRED (Principal, FM #7, 2026-08-06) -- covered by the IPS page
    # (ips_summary already shows Current-vs-target allocation live). Unwired the same way every
    # prior CUT module is: core flipped False, absent from every tier's optional_on, so it never
    # renders while the file stays in the library rather than becoming an orphan reference.
    ("allocation_house_view", 1, "Portfolio X-ray", False),
    ("concentration_risk", 1, "Portfolio X-ray", True),
    # group_concentration: CUT permanently (Principal 2026-07-27) — module stays in the
    # library, renders nowhere by default.
    ("group_concentration", 1, "Portfolio X-ray", False),
    ("sector_exposure",    1, "Portfolio X-ray", True),
    ("mcap_positioning",   1, "Portfolio X-ray", True),
    # ---- restructure (FM #11, 2026-08-06): three parts -- portfolio statistics (above), then
    # MF, then direct equity. Fund Book block now precedes Equity Book block in LIST ORDER
    # (render order follows list position, sec_no is only a per-page display marker), and
    # sec_no is swapped 2<->3 to match, because every module's deck.content(sec_no, ...) call
    # is a literal per file, not derived -- see the section-marker rail top-right of every page
    # and contents_legend.py's section list, both updated to match.
    ("_div2",              2, "The Fund Book",  True),
    # mf_methodology: NEW (FM #12) -- honest description of what covers a fund TODAY and what
    # is still hand-reviewed (hybrids and debt; neither of the two frameworks is built for them).
    ("mf_methodology",     2, "The Fund Book",  True),
    ("fund_book_scored",   2, "The Fund Book",  True),
    ("funds_equity",       2, "The Fund Book",  True),
    ("funds_hybrid",       2, "The Fund Book",  True),
    # funds_debt: NEW (FM #22) -- YTM / modified duration / expense / rating for debt-category
    # funds. Self-gates to 0 slides when the book holds none (common, not an error).
    ("funds_debt",         2, "The Fund Book",  True),
    # fund_category_rules ("Category & structure · preference rules"): CUT 2026-07-28
    # (Principal, permanent, all tiers) -- superseded the 2026-07-25 ruling that its AMC-
    # concentration strip specifically should stay; the whole module is out now.
    ("fund_category_rules", 2, "The Fund Book", False),
    # fund_quality_alloc: PARKED per Principal 2026-07-25 (quadrant graph cut; MF calls come from
    # the desk's own framework, not this deck) — module kept in the library, rendered nowhere.
    ("fund_quality_alloc", 5, "Annexure",       False),
    # fund_overlap: page cut per Principal 2026-07-25 (the double-pay insight folds into
    # fund_actions as a replacement suggestion, e.g. index-sleeve route; module stays in
    # the library, renders nowhere by default).
    ("fund_overlap",       5, "Annexure",       False),
    # scheme_correlation: NEW (FM #24, Principal ruling 2026-08-06) -- "correlation REPLACES
    # overlap." Takes scheme_overlap_full's former slot and former on/off profile exactly:
    # real, NAV-history-derived pairwise correlation between the top funds by weight, main
    # Fund Book section. See the module docstring for why holdings-level overlap cannot be
    # honestly computed from ACE data at all (sector percentages, not a security list).
    ("scheme_correlation", 2, "The Fund Book", False),
    ("fund_actions",       2, "The Fund Book",  True),
    ("_div3",              3, "The Equity Book", True),
    ("score_method",       3, "The Equity Book", True),
    ("book_scored",        3, "The Equity Book", True),
    ("equity_book",        3, "The Equity Book", True),
    ("sell_list",          3, "The Equity Book", True),
    ("hold_rationale",     3, "The Equity Book", True),
    ("_div4",              4, "Recommendations", True),
    ("house_view_fit",     4, "Recommendations", True),
    # cost: CUT permanently (Principal 2026-07-27) — module stays in the library, renders
    # nowhere by default.
    ("cost",               4, "Recommendations", False),
    ("tax_impact",         4, "Recommendations", True),
    ("priority_actions",   4, "Recommendations", True),
    # growth_projection: MOVED from Annexure into Recommendations (Principal 2026-07-27,
    # permanent) — "if you follow our recommendations, here's where this could go" belongs
    # right after priority_actions, not in the back matter.
    ("growth_projection",  4, "Recommendations", False),
    # renders ONLY when ctx['data_notes'] has content (suspended holdings / No-View funds /
    # statement data-quality flags) — always checked, silent on the synthetic demo book.
    ("data_notes",         4, "Recommendations", True),
    # ---- F18 cut line: optional annexure ----
    ("_div5",              5, "Annexure",       False),
    # transition-plan slides live in the ANNEXURE (Principal 2026-07-25: no buy
    # recommendations for now; the deployment/before-after sequence is a framework
    # shown on request, not a recommendation in the main deck)
    ("deployment",         5, "Annexure",       False),
    ("before_after",       5, "Annexure",       False),
    ("opportunity_set",    5, "Annexure",       False),
    ("quality_vs_price",   5, "Annexure",       False),
    # factor_profile ("index/factor fund analysis"): CUT permanently (Principal 2026-07-27)
    # — its factor tilts are an approximated/illustrative proxy, not a real regression; one
    # of the "pages we're not sure of" — module stays in the library, renders nowhere by default.
    ("factor_profile",     5, "Annexure",       False),
    ("spotlight_holdings", 5, "Annexure",       False),
    ("holdings_detail",    5, "Annexure",       False),
    ("sell_cards",         5, "Annexure",       False),
    ("scheme_scorecards",  5, "Annexure",       False),
    # ---- extended visual annexure (18 illustrations) ----
    ("annex_score_vs_call", 5, "Annexure",      False),
    ("annex_valuation_bands", 5, "Annexure",    False),
    ("annex_returns_quilt", 5, "Annexure",      False),
    ("annex_correlation",  5, "Annexure",       False),
    # scheme_overlap_full: MOVED here from "The Fund Book" main section (Principal ruling
    # 2026-08-06, FM #24) -- scheme_correlation.py (above, main Fund Book section) replaced it
    # as the default page. This illustrative fund-vs-fund overlap estimate stays in the
    # library, available on request ("add overlap in annexure if needed"), off by default in
    # every tier -- see the module docstring for why it can never become a real number from
    # data ACE provides today.
    ("scheme_overlap_full", 5, "Annexure",      False),
    ("annex_risk_contribution", 5, "Annexure",  False),
    # annex_stress_scenarios.py DELETED outright 2026-07-28 (not just parked): its TODAY/PROP
    # drawdown arrays were hardcoded constants shown as if computed, AND structurally biased
    # regardless (this deck only ever sells into cash, never buys, so "after" always looks
    # better by construction) -- a dead-code landmine, unlike the honestly-disclosed
    # illustrative modules that stay parked.
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


# divider mini-TOC labels (v7 device: each section divider carries a muted local
# contents list, bottom-left). Filtered to what the tier actually renders, max 5.
DIVIDER_TOC = {
    1: [("snapshot", "Portfolio snapshot"), ("core_satellite", "Core vs satellite"),
        ("concentration_risk", "Concentration risk"), ("sector_exposure", "Sector exposure"),
        ("mcap_positioning", "Market-cap positioning")],
    # restructure (FM #11): Fund Book is section 2, Equity Book is section 3 -- swapped from
    # the original numbering, matching MODULES list order above.
    2: [("mf_methodology", "How we assess every fund"), ("fund_book_scored", "The fund book, scored"),
        ("funds_equity", "Equity funds vs benchmark"), ("funds_hybrid", "Hybrid funds"),
        ("funds_debt", "Debt funds")],
    3: [("score_method", "How we score every stock"), ("book_scored", "The book, scored"),
        ("equity_book", "The book at a glance"), ("sell_list", "What we would sell"),
        ("hold_rationale", "What stays, and why")],
    4: [("house_view_fit", "House-view fit"), ("cost", "What you're paying today"),
        ("tax_impact", "Tax impact"), ("priority_actions", "Your priority actions")],
    5: [("deployment", "Transition framework"), ("before_after", "Before and after"),
        ("spotlight_holdings", "Holding spotlights"), ("holdings_detail", "All holdings, scored"),
        ("sell_cards", "Sell rationale cards")],
}


def _toc_for(sec_no, tier):
    out = []
    for mod_id, label in DIVIDER_TOC.get(sec_no, []):
        core = next((c for m, s, _n, c in MODULES if m == mod_id), None)
        if core is None:
            continue
        if core:
            ok = mod_id not in tier.get("skip_core", set())
        else:
            ok = mod_id in tier["optional_on"]
        if ok:
            out.append(label)
    return out[:5]


def _load(mod_id):
    try:
        return importlib.import_module(f"modules.{mod_id}")
    except Exception:
        return None


def build(ctx, tier_name, verbose=True):
    tier = T.get(tier_name)
    deck = slidekit.new_deck()
    manifest = []
    # a divider with no rendered content behind it is a dangling chapter page — skip it
    sec_counts = {}
    for mod_id, sec_no, sec_name, core in MODULES:
        if mod_id.startswith("_div"):
            continue
        inc = (mod_id not in tier.get("skip_core", set())) if core else (mod_id in tier["optional_on"])
        if inc:
            sec_counts[sec_no] = sec_counts.get(sec_no, 0) + 1
    for mod_id, sec_no, sec_name, core in MODULES:
        # selection
        if mod_id.startswith("_div"):
            included = sec_counts.get(sec_no, 0) > 0
        elif core:
            included = mod_id not in tier.get("skip_core", set())
        else:
            included = mod_id in tier["optional_on"]
        if not included:
            continue
        if mod_id.startswith("_div"):
            # section divider — skip empty sections for light tiers handled implicitly
            titles = {1: ("Portfolio X-ray", "Where the book stands today"),
                      2: ("The Fund Book", "Upside, downside and consistency — not just returns"),
                      3: ("The Equity Book", "Every direct holding, scored and read"),
                      4: ("What We Would Do", "The calls, the cost and the tax"),
                      5: ("Annexure", "Detail and frameworks, on request")}
            t, sub = titles.get(sec_no, (sec_name, ""))
            deck.section_divider(sec_no, t, sub, pages=_toc_for(sec_no, tier))
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
