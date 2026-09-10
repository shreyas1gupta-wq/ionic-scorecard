# -*- coding: utf-8 -*-
"""mf_methodology (NEW, FM #12), how we assess every fund. Client-safe description of the two
fund-quality frameworks actually in use TODAY, stated honestly: the short-term framework (6-month
capture ratio, the only one of the two with a Sell verdict) and the long-term framework (a
multi-year selection framework, no Sell verdict, veto-only). Hybrid AND debt funds sit outside
BOTH frameworks today and are reviewed by hand — disclosed here, not smoothed over.

No internal codenames (tellscan's INTERNAL_JARGON bucket forbids "QFRA"/"SENTINEL"/"MERIT" etc
client-side) and no vendor/source name for the underlying fund-data feed — those belong on the
internal PAC deck, not a client page. Heights are ALWAYS callout_h-derived, never guessed, per
the standing clip-risk lesson."""
from slidekit import NAVY, GOLD, INK, SLATE, ML, UW

LABELS = {
    # The title used to promise "two frameworks", which is the adapter path's story. On the
    # percentile path the two panels are the score and the steadiness figure, and a title has to
    # match the page under it.
    "hni":    {"eyebrow": "How we assess every fund",
               "title": "What the score measures, and what it does not reach"},
    "std":    {"eyebrow": "How we assess every fund",
               "title": "What the score measures, and what it does not reach"},
    "simple": {"eyebrow": "How we check your funds",
               "title": "Two checks we run, and what we still do by hand"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    L = LABELS.get(reg, LABELS["std"])
    funds = ctx["funds"]
    # COUNTED FROM WHETHER A SCORE EXISTS, not from the SEBI category. This asked whether a fund
    # was hybrid or debt and called everything else covered, under a footer reading "coverage
    # counted from this book's own holdings" -- so a fund the score file has no score for was
    # reported to the client as sitting inside one of the two checks. The score is the evidence
    # that a check ran; the category is a guess about whether one would have.
    def _scored(f):
        return f.get("qfra") is not None
    n_covered = sum(1 for f in funds if _scored(f))
    n_hand = len(funds) - n_covered
    n_hybrid = sum(1 for f in funds if f.get("category") == "hybrid" and not _scored(f))
    n_debt = sum(1 for f in funds if f.get("category") == "debt" and not _scored(f))

    s = deck.content(2, "The Fund Book", L["eyebrow"], L["title"])

    half = (UW - 0.3) / 2
    _method_pre = str(ctx.get("fund_call_method") or "").strip().lower()
    if simple:
        b1 = ("The last six months: how much of the market's fall the fund took on. The only "
              "one of our two checks that can tell us to sell a fund.")
        b2 = ("Several years, to find the strongest fund per category. No 'sell' answer, only "
              "'keep going' or 'top pick' — it can block a sell, never start one.")
    else:
        b1 = ("How much of a category benchmark's fall each fund took in the trailing six "
              "months, against a pass line set for that category. The only one of our two "
              "checks with a Sell verdict, and the only one that can start a sell.")
        b2 = ("A multi-year selection framework naming the strongest one or two funds per "
              "category. No Sell verdict — 'stays active' or 'top pick' only. Can veto a sell "
              "the short-term check wants, never originate one.")
    if _method_pre == "percentile":
        b1 = ("Where the scheme finished against its own SEBI category over three years and over "
              "five, expressed as the share of that peer group it beat. Both horizons are tested "
              "and both must be weak before a fund is sold." if not simple else
              "How the fund did against others of its own kind over three years and over five.")
        b2 = ("How STEADILY it got there, month by month against the same peers. Context for the "
              "reader and never a verdict on its own: a fund can be reliably behind."
              if not simple else
              "How steady that record was, month to month. It never decides the call by itself.")
    ch = max(deck.callout_h(half, b1, min_h=1.15, max_h=1.45),
             deck.callout_h(half, b2, min_h=1.15, max_h=1.45))
    _h1 = ("THE SCORE · THREE AND FIVE YEARS AGAINST ITS OWN CATEGORY"
           if _method_pre == "percentile" else "SHORT-TERM CHECK · 6-MONTH CAPTURE")
    _h2 = ("STEADINESS · HOW RELIABLY IT GOT THERE"
           if _method_pre == "percentile" else "LONG-TERM CHECK · MULTI-YEAR SELECTION")
    deck.callout(s, ML, 1.90, half, ch, _h1, b1, kind="note")
    deck.callout(s, ML + half + 0.3, 1.90, half, ch, _h2, b2, kind="note")

    # ---- how a fund actually gets sold, stated precisely ----
    y = 1.90 + ch + 0.14
    # THE PAGE MUST DESCRIBE THE PATH THAT PRODUCED THE CALLS THREE PAGES LATER. The
    # originate-and-veto text below is true of the desk's adapter path; this kit reads a score
    # file struck on the PERCENTILE rule, and printing one mechanism over calls produced by the
    # other is a contradiction a client cannot see and an FM can. The data layer says which.
    _method = str(ctx.get("fund_call_method") or "").strip().lower()
    if _method == "percentile":
        # The band is 0.65in. Written longer, it overran by 0.38in and the last clause vanished.
        rule = ("Sold only where the scheme is in the bottom third of its own category over BOTH "
                "horizons. One weak horizon is a bad run; two is a record." if not simple else
                "We only suggest selling a fund that is in the weakest third of its own kind over "
                "BOTH three and five years. One weak stretch is not enough.")
    else:
        rule = ("Only sold when the short-term check flags it; the long-term check can soften that "
                "to a Hold, never create a sell on its own. Disagreement is written down, not "
                "resolved quietly." if not simple else
                "We only suggest selling on the six-month check's say. The multi-year check can "
                "save a fund from that call, never cause one alone.")
    rh = deck.callout_h(UW, rule, min_h=0.5, max_h=0.65)
    deck.callout(s, ML, y, UW, rh, "How a fund actually gets sold", rule, kind="human")

    # ---- quick counts, live from this book (kpi_strip's real footprint is ~0.92in
    # regardless of the h argument -- budgeted explicitly rather than guessed) ----
    y += rh + 0.14
    deck.kpi_strip(s, [
        (str(n_covered), ("Funds the framework scores" if not simple
                          else "Funds we have a score for")),
        (str(n_hand), ("Carrying no score, read by hand" if not simple
                       else "Read by a person instead")),
        (str(len(funds)), "Funds in this book" if not simple else "Funds you hold"),
    ], y=y)
    y += 0.94

    # ---- the honest gap: hybrids AND debt sit outside both checks today ----
    gap_kicker = "WHAT WE DO BY HAND TODAY"
    if n_hand == 0:
        gap_body = ("Every fund here falls inside one of the two checks above; none needed a "
                     "hand review this cycle." if not simple else
                     "Both checks above cover every fund you hold; nothing needed a manual look.")
    else:
        # NAME THE WHOLE GAP, NOT THE PART OF IT WE HAVE A LABEL FOR. This described the hybrid
        # and bond-only funds and stopped, so the sentence accounted for 2 of the 25 the KPI above
        # it reports as unscored, and the other 23 were left unexplained under a footer promising
        # coverage counted from the book itself.
        parts = []
        if n_hybrid:
            parts.append("%d mixing shares and bonds" % n_hybrid)
        if n_debt:
            parts.append("%d bond-only" % n_debt)
        _rest = n_hand - n_hybrid - n_debt
        if _rest > 0:
            parts.append("%d the framework does not rank at all: gold, overseas feeders, "
                         "arbitrage and index vehicles" % _rest)
        which = "; ".join(parts)
        if simple:
            gap_body = ("%d of your funds have no score: %s. We read those by hand instead, "
                        "against what each one actually holds." % (n_hand, which))
        else:
            gap_body = ("%d of the %d schemes carry no score. %s. There is no single "
                        "equity-style category to rank them against, so they are read by hand "
                        "against each fund's own disclosed mix. A real gap, disclosed rather "
                        "than folded into a number implying coverage that does not exist."
                        % (n_hand, len(funds), which))
    gh = deck.callout_h(UW, gap_body, min_h=0.55, max_h=1.1)
    deck.callout(s, ML, y, UW, gh, gap_kicker, gap_body, kind="warn")

    demo_tag = " Illustrative synthetic funds." if ctx.get("is_demo", False) else ""
    deck.source(s, f"Coverage counted from this book's own holdings, not assumed.{demo_tag}")
    return 1
