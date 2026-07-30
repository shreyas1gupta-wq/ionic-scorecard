# -*- coding: utf-8 -*-
"""exec_summary (F2/F8, core), Executive summary.
KPI stat band (AUM · stocks/schemes · top-10 weight · Sell count · fund actions) THEN a
category gap->action grid: Category | Gap vs policy | What we'd do | See. Every row resolves
to a non-empty action and a section pointer. Sell/Trim/Hold and fund-action counts are read
straight from ctx['totals'] so they equal the book-scored counts by construction."""
from slidekit import (NAVY, NT2, GOLD, INK, SLATE, HOLD, SELL, AMBER, PANEL, HAIR,
                      SERIF, SANS, ML, UW, RX)
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
    hv = ctx["house_view"]["alloc_gap"]
    n_fund_act = sum(1 for f in ctx["funds"] if f["action"] not in ("HOLD", "Hold"))
    n_switch = sum(1 for f in ctx["funds"] if f["action"].upper() == "SWITCH")
    has_redeem = any(f["action"].upper() == "REDEEM" for f in ctx["funds"])
    # a 0-count "gap" isn't a gap to flag in a "things that need attention" list -- if this
    # book has fund actions but none of them are SWITCH specifically (e.g. all Exit), name
    # what's actually happening instead of a fabricated zero-count line item
    show_switch_row = n_switch > 0
    reg_drag = ctx["cost"]["reg_drag_inr"]
    foreign_gap = abs(hv.get("Foreign", -12.0))
    cap = ips["single_name_cap_pct"]
    # no bespoke IPS -> don't claim a foreign-allocation target or house "plan" that was
    # never agreed with this client; and a real reg_drag of 0 (every fund already Direct)
    # is a fee non-issue, not a "Rs 0k/yr avoidable fee" to report as if it were a gap
    ips_on_file = ips.get("on_file", True)
    show_foreign_row = ips_on_file
    show_fee_row = reg_drag > 0

    title = ("The five things that need attention" if simple
             else "Where the book differs from your policy, and what we'd do")
    s = deck.content(0, "Understanding", "Executive summary", title)

    # ---- KPI stat band ----
    deck.kpi_strip(s, [
        (_cr(t["grand_inr"]), "Portfolio value"),
        (f"{t['n_stocks']} / {t['n_funds']}", "Stocks / funds"),
        (f"{t['top10_pct']:.0f}%", "Top-10 weight"),
        (str(t["n_sell"]), "Equity sells", None, SELL),
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
             f"{n_fund_act} funds exit for structural reasons (overlap, consolidation) — none for performance.",
             ("c", "See the fund actions detail for the reasoning on each.", NAVY), "03 · Funds"])
        rows = [
            [("b", "Too concentrated"),
             f"Your 2 biggest shares are over 11%; our guideline caps any one at {cap:.0f}%.",
             ("c", "One exits via the sell list; the other is reduced slowly.", NAVY), "01 · X-ray"],
            [("b", "Weak holdings"),
             f"{t['n_sell']} shares score in the Sell zone.",
             ("c", "Sell all of them, in a planned order.", NAVY), "02 · Equity"],
            foreign_row,
            fee_row,
            fundline_row,
        ]
    else:
        foreign_row = ([("b", "Foreign under-allocation"),
             f"~{foreign_gap:.0f} pts below the {ips['foreign_target_pct']:.0f}% foreign-equity target.",
             ("c", "Plan a foreign sleeve at deployment (annexure framework).", NAVY), "04 · Plan"]
            if show_foreign_row else
            [("b", "No investment policy on file"),
             "This is a first review; no written mandate (goals, timeline, risk tier) exists yet for this account.",
             ("c", "Agree an IPS with the RM before the next review cycle.", NAVY), "01 · X-ray"])
        fee_row = ([("b", "Regular-plan cost"),
             f"~{_k(reg_drag)}/yr avoidable trail on Regular-plan funds.",
             ("c", "Switch to Direct where the same scheme exists Direct." if has_redeem
              else "Every recommended fund move lands in a Direct plan.", NAVY), "04 · Plan"]
            if show_fee_row else
            [("b", "Plan cost"),
             "Every scheme in this account is already held Direct — no Regular-plan drag to correct.",
             ("c", "The fund actions below address structure and consistency, not cost.", NAVY), "03 · Funds"])
        fundline_row = ([("b", "Fund structure"),
             f"{n_switch} schemes: index-trailing or rigid mandate.",
             ("c", "Switch to passive-LC / factor + a Flexi-Cap.", NAVY), "03 · Funds"]
            if show_switch_row else
            [("b", "Fund structure"),
             f"{n_fund_act} schemes exit for structural reasons (overlap, consolidation), not performance.",
             ("c", "See the fund actions detail for the reasoning on each.", NAVY), "03 · Funds"])
        rows = [
            [("b", "Concentration"),
             f"Top-2 names each >11%; our guideline caps a single name at {cap:.0f}%.",
             ("c", "One exits via the sell programme; the other trims toward the cap.", NAVY), "01 · X-ray"],
            [("b", "Sell programme"),
             f"{t['n_sell']} direct holdings score in the Sell band (<40).",
             ("c", "Exit all {n}, sliced by liquidity.".format(n=t["n_sell"]), NAVY), "02 · Equity"],
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
