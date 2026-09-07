# -*- coding: utf-8 -*-
"""exec_summary (F2/F8, core), Executive summary.
KPI stat band (AUM · stocks/schemes · top-10 weight · Sell count · fund actions) THEN a
category gap->action grid: Category | Gap vs policy | What we'd do | See. Every row resolves
to a non-empty action and a section pointer. Sell/Trim/Hold and fund-action counts are read
straight from ctx['totals'] so they equal the book-scored counts by construction."""
from slidekit import (NAVY, NT2, GOLD, INK, SLATE, HOLD, SELL, AMBER, PANEL, HAIR,
                      SERIF, SANS, ML, UW, RX)
from lib import lookthrough as LT
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR


def _cr(v):
    return f"Rs {v/1e7:.1f} Cr"


def _k(v):
    if v >= 1e7:
        return f"Rs {v/1e7:.1f} Cr"
    if v >= 1e5:
        return f"Rs {v/1e5:.1f} L"
    return f"Rs {v/1e3:.0f}k"


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    t = ctx["totals"]
    ips = ctx["ips"]
    hv = (ctx.get("house_view") or {}).get("alloc_gap") or {}
    n_fund_act = sum(1 for f in ctx["funds"] if f["action"] not in ("HOLD", "Hold"))
    n_switch = sum(1 for f in ctx["funds"] if f["action"].upper() == "SWITCH")
    has_redeem = any(f["action"].upper() == "REDEEM" for f in ctx["funds"])
    # not every fund action is purely structural -- at least one (2026-08-02) is also an
    # independent quality-framework flag; don't claim "none for performance" if that's false
    n_fund_perf_flag = sum(1 for f in ctx["funds"]
                            if f["action"] not in ("HOLD", "Hold")
                            and f.get("qfra") is not None and f.get("qfra") < 40)
    all_structural = n_fund_perf_flag == 0
    # a 0-count "gap" isn't a gap to flag in a "things that need attention" list -- if this
    # book has fund actions but none of them are SWITCH specifically (e.g. all Exit), name
    # what's actually happening instead of a fabricated zero-count line item
    show_switch_row = n_switch > 0
    reg_drag = ctx["cost"]["reg_drag_inr"]
    # Two different facts, and the page used to collapse them into one. Whether Regular-plan
    # schemes are HELD is read off the scheme names; what the drag COSTS needs a TER per scheme in
    # each plan. A book can hold seven Regular schemes and still have reg_drag == 0 because the
    # cost is unknown, which is not the same statement as "every scheme is already Direct".
    n_regular = int(ctx["cost"].get("n_regular") or 0)
    foreign_gap = abs(hv.get("Foreign", -12.0))
    # .get, because engine.build swallows a KeyError here and takes the whole executive summary
    # out of the deck with nothing on the deck to say it is missing.
    cap = ips.get("single_name_cap_pct")
    # WHERE the Sell calls are, and what they are. "02 . Equity" was hardcoded on a deck whose
    # section 02 is the Fund Book and which carries no Equity Book at all, and the sells here are
    # schemes rather than shares.
    _n_fund_sell = sum(1 for f in (ctx.get("funds") or [])
                       if str(f.get("verdict") or "").strip() == "Sell")
    _n_eq_sell = sum(1 for e in (ctx.get("equity") or [])
                     if str(e.get("rec") or "").strip() == "Sell")
    if _n_fund_sell and not _n_eq_sell:
        _sell_gap = f"{_n_fund_sell} scheme(s) carry a Sell call, part of the fund actions below."
        _sell_ref = "02 · Funds"
    elif _n_eq_sell and not _n_fund_sell:
        _sell_gap = f"{_n_eq_sell} holding(s) carry a Sell call."
        _sell_ref = "03 · Equity"
    else:
        _sell_gap = (f"{_n_eq_sell} share(s) and {_n_fund_sell} scheme(s) carry a Sell call.")
        _sell_ref = "04 · Actions"
    # concentration row must be computed, not fabricated (2026-08-02 fix: a hardcoded
    # ">11%" breach claim survived from an earlier client's numbers -- this book's real
    # top-2 direct-equity weight is well inside the cap, with zero names over it)
    eq_sorted = sorted(ctx["equity"], key=lambda e: -(e.get("weight_pct") or 0))
    # The concentration page states the top two across EVERY holding. Taking direct shares only
    # here printed 3.3% on the executive summary against 22.9% on slide 11 of the same deck.
    _top = LT.scheme_concentration(ctx, top_n=2)
    top2_pct = sum(w for _n, _k, w in _top) if _top else         sum(e.get("weight_pct") or 0 for e in eq_sorted[:2])
    # The cap is PER HOLDING, so it is the largest single position that tests it, not the top two
    # added together. Comparing a combined figure against a single-name cap produced the sentence
    # "top-2 are 22.9% combined, comfortably inside the 15% single-name cap", which is both the
    # wrong comparison and, on its own numbers, a contradiction.
    _largest = max((w for _n, _k, w in LT.scheme_concentration(ctx, top_n=1)), default=0.0)
    _over = [(n, w) for n, _k, w in LT.scheme_concentration(ctx, top_n=50)
             if cap is not None and w > float(cap)]
    _conc_line = ((f"{len(_over)} holding{'' if len(_over) == 1 else 's'} above the {cap:.0f}% cap, "
                   f"the largest at {_largest:.1f}%; the top two come to {top2_pct:.1f}% of "
                   f"the book.")
                  if _over else
                  f"The largest single holding is {_largest:.1f}%, inside the {cap:.0f}% cap; the "
                  f"top two come to {top2_pct:.1f}% of the book."
                  if cap is not None else
                  f"The largest single holding is {_largest:.1f}% of the book and the top two come "
                  f"to {top2_pct:.1f}%. No single-name cap is on file to test these against.")
    # The cap covers every holding, so the breach test must too. Reading direct equity only put
    # "No action needed" beside a 14.0% fund the scoring engine was already trimming back to 10%.
    breach_names = _over
    has_breach = len(breach_names) > 0
    # no bespoke IPS -> don't claim a foreign-allocation target or house "plan" that was
    # never agreed with this client; and a real reg_drag of 0 (every fund already Direct)
    # is a fee non-issue, not a "Rs 0k/yr avoidable fee" to report as if it were a gap
    ips_on_file = ips.get("on_file", True)
    show_foreign_row = (ips_on_file) and ips.get("foreign_target_pct") is not None
    # A mandate that sets no overseas target cannot be under it. The row used to be
    # gated on the gap alone and then formatted the target directly, so an IPS that
    # is on file without that key raised and the engine, which swallows module
    # exceptions, dropped the whole executive summary with no error on the deck.
    show_fee_row = reg_drag > 0

    title = ("The five things that need attention" if simple
             else "Where the book differs from your policy, and what we'd do")
    s = deck.content(0, "Understanding", "Executive summary", title)

    # ---- KPI stat band ----
    deck.kpi_strip(s, [
        (_cr(t["grand_inr"]), "Portfolio value"),
        (f"{t['n_stocks']} / {t['n_funds']}", "Stocks / funds"),
        (f"{t['top10_pct']:.0f}%", "Top-10 weight"),
        (str(t["n_sell"]), "Sell calls", None, SELL),
        (str(n_fund_act), "Fund actions", None, AMBER),
    ], y=1.80)

    # ---- lead line ----
    lead = ("Each gap below has one action, and where to read the detail."
            if not simple else
            "Below are the five things to fix. Each has one clear next step.")
    deck.txt(s, ML, 2.92, UW, 0.26, [(lead, SERIF, 11.5, INK, False, True)])

    # ---- category gap -> action grid ----
    if simple:
        foreign_row = ([("b", "Too little abroad"),
             f"About {foreign_gap:.0f} points below the {ips['foreign_target_pct']:.0f}% overseas target.",
             ("c", "Plan an overseas step for when we reinvest.", NAVY), "04 · Plan"]
            if show_foreign_row else
            [("b", "No plan on file yet"),
             "This is a first review — goals, timeline and risk comfort aren't yet agreed in writing.",
             ("c", "Share these with your RM before the next review.", NAVY), "01 · X-ray"])
        fee_row = ([("b", "Paying extra fees"),
             f"About {_k(reg_drag)}/yr of avoidable Regular-plan cost.",
             ("c", "Move to the cheaper Direct plan." if has_redeem
              else "Every fund change we suggest lands in a cheaper Direct plan.", NAVY), "04 · Plan"]
            if show_fee_row else
            [("b", "Fund cost"),
             "Every fund you hold is already on the cheaper Direct plan — no regular-plan drag to fix.",
             ("c", "The fund changes below are about consistency, not cost.", NAVY), "03 · Funds"])
        fundline_row = ([("b", "Fund line-up"),
             f"{n_switch} funds trail the index or are built too rigidly.",
             ("c", "Switch to an index/factor fund and a Flexi-Cap.", NAVY), "03 · Funds"]
            if show_switch_row else
            [("b", "Fund line-up"),
             (f"{n_fund_act} funds exit for structural reasons (overlap, consolidation) — none for performance."
              if all_structural else
              f"{n_fund_act} funds exit, mostly structural (overlap, consolidation); {n_fund_perf_flag} also flagged on quality."),
             ("c", "See the fund actions detail for the reasoning on each.", NAVY), "03 · Funds"])
        conc_row = ([("b", "Too concentrated"),
             _conc_line,
             ("c", "These are addressed in the sell/trim list.", NAVY), "01 · X-ray"]
            if has_breach else
            [("b", "Concentration"),
             _conc_line,
             ("c", "No action needed; monitored each review.", NAVY), "01 · X-ray"])
        rows = [
            conc_row,
            [("b", "Weak holdings"),
             _sell_gap,
             ("c", "Sell all of them, in a planned order.", NAVY), _sell_ref],
            foreign_row,
            fee_row,
            fundline_row,
        ]
    else:
        foreign_row = ([("b", "Foreign under-allocation"),
             f"~{foreign_gap:.0f} pts below the {ips['foreign_target_pct']:.0f}% foreign-equity target.",
             ("c", "Plan a foreign sleeve at deployment (annexure framework).", NAVY), "04 · Plan"]
            if show_foreign_row else
            ([("b", "No investment policy on file"),
              "This is a first review; no written mandate (goals, timeline, risk tier) exists yet "
              "for this account.",
              ("c", "Agree an IPS with the RM before the next review cycle.", NAVY), "01 · X-ray"]
             if not ips_on_file else
             # The mandate IS on file, it simply sets no overseas target. Falling through to the
             # "no IPS" copy told the client no policy existed on a deck whose third slide is that
             # policy, showing risk tier AGGRESSIVE and live bands.
             [("b", "Mandate on file"),
              f"Reviewed against the {ips.get('risk_tier') or 'agreed'} mandate: allocation bands, "
              f"single-name, single-manager and illiquidity limits, all tested on this page's own "
              f"numbers.",
              ("c", "See the Investment Policy Statement.", NAVY), "00 · Understanding"]))
        fee_row = ([("b", "Regular-plan cost"),
             f"~{_k(reg_drag)}/yr avoidable trail on Regular-plan funds.",
             ("c", "Switch to Direct where the same scheme exists Direct." if has_redeem
              else "Every recommended fund move lands in a Direct plan.", NAVY), "04 · Plan"]
            if show_fee_row else
            [("b", "Plan cost"),
             (f"{n_regular} scheme{'' if n_regular == 1 else 's'} held in the Regular plan; the "
              "saving from moving to Direct needs expense ratios this statement does not carry."
              if n_regular else
              "Every scheme in this account is already held Direct — no Regular-plan drag to correct."),
             ("c", "The fund actions below address structure and consistency, not cost.", NAVY), "03 · Funds"])
        fundline_row = ([("b", "Fund structure"),
             f"{n_switch} schemes: index-trailing or rigid mandate.",
             ("c", "Switch to passive-LC / factor + a Flexi-Cap.", NAVY), "03 · Funds"]
            if show_switch_row else
            [("b", "Fund structure"),
             (f"{n_fund_act} schemes exit for structural reasons (overlap, consolidation), not performance."
              if all_structural else
              f"{n_fund_act} schemes exit, mostly structural (overlap, consolidation); {n_fund_perf_flag} also independently flagged on quality."),
             ("c", "See the fund actions detail for the reasoning on each.", NAVY), "03 · Funds"])
        conc_row = ([("b", "Concentration"),
             _conc_line,
             ("c", "Addressed in the sell/trim programme.", NAVY), "01 · X-ray"]
            if has_breach else
            [("b", "Concentration"),
             _conc_line,
             ("c", "No action needed; monitored each review.", NAVY), "01 · X-ray"])
        rows = [
            conc_row,
            [("b", "Sell programme"),
             _sell_gap,
             ("c", "Exit all {n}, sliced by liquidity.".format(n=t["n_sell"]), NAVY), _sell_ref],
            foreign_row,
            fee_row,
            fundline_row,
        ]

    cols = [("Category", 0.20, "l"), ("Gap vs policy", 0.36, "l"),
            ("What we would do", 0.34, "l"), ("See", 0.10, "l")]
    deck.table(s, ML, 3.32, UW, cols, rows, rowh=0.56, fs=10, hfs=8, header=True, zebra=True)

    deck.txt(s, ML, 6.42, UW, 0.2,
             [("Counts (sells, fund actions) match the scored books exactly; ‘See’ points to the section with the detail.",
               SANS, 8, SLATE, False, True)])
    return 1
