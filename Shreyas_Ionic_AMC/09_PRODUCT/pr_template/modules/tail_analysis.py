# -*- coding: utf-8 -*-
"""tail_analysis, position sizing across the whole book and the tail it leaves behind.

WHAT THIS PAGE SAYS, and says only from the live numbers. A book carries two populations at once.
A few large positions account for most of the money, so the book's result is largely theirs. Behind
them sits a tail of positions too small to move the total, each of which still occupies a line on
the statement, a decision at every review, and its own risk band. The page counts both ends and
prints the share each accounts for, so the reader arrives at that reading from arithmetic rather
than being told it.

THE ONE THING THAT MUST NOT GO WRONG HERE is the cap test. The mandate's single-name cap is 5% per
ISIN and applies to DIRECT equity and single-issuer debt. It does NOT apply to a fund, so the
largest position on this page can sit well above 5% without any cap being touched. The AMC cap is
20% measured on the manager, so several schemes from one house aggregate into one number. On the
test book the largest direct security is 2.6%, inside its cap, while one house is at 25.0% across
seven schemes, outside its cap. Reading those two the other way round puts a false alarm on a
client page and misses a real one, so each test is struck against its own population and the page
says in words which population that is.

Weights arrive as shares of the WHOLE book, funds and direct holdings together, and are used as
they arrive. Nothing here is renormalised.

The chart is built in this file rather than in chart_lib because it exists for this page alone. It
goes through chart_lib's own figure scaffold and palette by the same import route
chart_ext_a/chart_ext_b and quality_consistency use, so it matches every other chart in the deck.
Both series are plotted on ONE axis as a share of their own whole, which is what makes the page
legible: the tail is most of the count and a minority of the money, and a reader can see the two
bars disagree without having to trust a second scale.

Self-gates to 0 slides on a book of fewer than five holdings, where a size distribution is just the
holdings list written twice.
"""
import re

import charts as _CH  # noqa: F401  (side effect: scripts on sys.path + CHART_OUTDIR set)
from chart_lib import (_fig, _save, caption_above, NAVY as CNAVY, NT3 as CNT3,  # noqa: E402
                       INK as CINK, SLATE as CSLATE)
from slidekit import (NAVY, SANS, ML, RX, clip_sentences, short_name)

# Both text budgets are the size of the box the house primitive gives the text, measured in the
# character model check_geometry2 uses, not guessed. deck.source() writes into a fixed 0.24in
# strip and the callout into (max_h - 0.5); a body over budget loses whole trailing SENTENCES
# rather than overflowing its box, which is why each fact below is one self-contained sentence.
CALLOUT_MAX_H = 1.40
# 306 is the six-line ceiling for a 5.50in-wide callout body at Georgia 10.5pt, past which
# check_geometry2 raises clip-risk. The copy below is written to land under it on every branch:
# the clip is a backstop for a pathological book, not the normal path. It was firing on the
# ordinary no-funds book at 305 and silently dropping the risk-band disclosure, which is the one
# sentence on the page that must not be the one to go.
CALLOUT_BUDGET = 306
SOURCE_BUDGET = 430
# Characters that fit a table cell / a KPI sub-line, at the per-font widths check_geometry2
# models: Georgia 0.0102in and Bahnschrift 0.0075in per point of size.
NAME_CH = 41             # the Holding cell, 0.66 of a 5.34in column, at Georgia 8pt
KPI_SUB_CH = 44          # the KPI sub-line, 2.72in wide, at Bahnschrift 8pt

# The bands, low edge inclusive. A holding at exactly 5% sits in "5% to 8%".
BANDS = ((0.0, 2.0, "Under 2%"), (2.0, 5.0, "2% to 5%"), (5.0, 8.0, "5% to 8%"),
         (8.0, 12.0, "8% to 12%"), (12.0, float("inf"), "12% and over"))
TAIL_EDGE = 2.0          # the tail is everything under this
BIG_EDGE = 8.0           # the two largest bands together are the positions that carry the book

LABELS = {
    "hni": {"eyebrow": "Position sizing and the tail",
            "title": "How much of the book sits in a few large positions, and how much in many small ones",
            "left": "EVERY HOLDING BY POSITION SIZE, COUNT AGAINST SHARE OF THE BOOK",
            "right": "THE FIVE LARGEST POSITIONS, AND THE CALL ON EACH",
            "mandate": "AGAINST THE MANDATE",
            "legend": "Dark bar, the band's share of the book. Light bar, how many holdings are in it.",
            "k1": "Holdings in the book", "k2": "Held under 2% each",
            "k4": "Largest single position",
            "callout": "What the two ends of the book come to", "whole": "the book",
            "cap_name": "Largest direct security", "amc_name": "Largest fund house"},
    "std": {"eyebrow": "Position sizing and the tail",
            "title": "The few positions that carry the book, and the many that cannot",
            "left": "EVERY HOLDING BY POSITION SIZE, COUNT AGAINST SHARE OF THE BOOK",
            "right": "THE FIVE LARGEST POSITIONS, AND THE CALL ON EACH",
            "mandate": "AGAINST THE MANDATE",
            "legend": "Dark bar, the band's share of the book. Light bar, how many holdings are in it.",
            "k1": "Holdings in the book", "k2": "Held under 2% each",
            "k4": "Largest single position",
            "callout": "What the two ends of the book come to", "whole": "the book",
            "cap_name": "Largest direct security", "amc_name": "Largest fund house"},
    "simple": {"eyebrow": "Your big positions and your small ones",
               "title": "How much of your money sits in your biggest holdings",
               "left": "YOUR HOLDINGS BY SIZE, HOW MANY AGAINST HOW MUCH",
               "right": "YOUR FIVE BIGGEST, AND WHAT WE SUGGEST",
               "mandate": "AGAINST YOUR LIMITS",
               "legend": "Dark bar, the band's share of your money. Light bar, how many you own in it.",
               "k1": "Holdings you own", "k2": "Held under 2% each",
               "k4": "Your biggest holding",
               "callout": "What your biggest and smallest come to", "whole": "your money",
               "cap_name": "One share or deposit", "amc_name": "One fund company"},
}

# Plan and option tails, and the trailing word "fund", are administrative and are the first thing
# to go when a name has to fit a table cell: what a reader needs is the scheme.
_PLAN = re.compile(r"\s*[-–(]?\s*\b(?:direct|regular|institutional)\b\s*(?:plan)?\b.*$",
                   re.IGNORECASE)
_OPT = re.compile(r"\s*[-–]\s*(?:growth|idcw|dividend|bonus|payout|cumulative)\b.*$",
                  re.IGNORECASE)
_FUNDWORD = re.compile(r"\s+fund$", re.IGNORECASE)


def _core(name):
    """The holding, with the plan and option tail removed. short_name() only strips the trailing
    word "fund" in title case, so an all-capitals statement name keeps it otherwise."""
    return _FUNDWORD.sub("", _OPT.sub("", _PLAN.sub("", (name or "")))).strip(" -–").strip()


def _w(h):
    try:
        return float(h.get("weight_pct") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _v(h):
    try:
        return float(h.get("value_inr") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _call(h):
    """The desk's call on this row, whichever of the two fields carries it."""
    return h.get("verdict") or h.get("rec") or "No View"


def _chart(rows, total_n, legend, whole, name, figsize=(7.2, 2.10)):
    """rows: [(band label, n, share of the count, share of the book)] in band order.

    Two bars per band on ONE axis. The dark bar is the band's share of the book. The light bar is
    the band's share of the NUMBER of holdings, and because the number of holdings is the same
    divisor on every row, that bar is proportional to the count printed beside it: the two are one
    fact in two forms, not two scales the reader has to reconcile. Every value is printed at the
    end of its own bar, so the axis needs no ticks.

    Only the first band that holds anything spells its units out. Repeating "of the book" and "of
    75 holdings" down all five rows was ten phrases carrying two facts, and it read as noise."""
    fig, ax = _fig(figsize)
    ys = list(range(len(rows)))[::-1]
    spelled = False
    for y, (lab, cnt, cshare, bshare) in zip(ys, rows):
        if not cnt:
            ax.text(1.2, y, "no holdings in this band", va="center", ha="left",
                    fontsize=8.6, color=CSLATE, style="italic")
            continue
        ax.barh(y + 0.19, bshare, height=0.31, color=CNAVY, zorder=3)
        ax.barh(y - 0.19, cshare, height=0.31, color=CNT3, zorder=3)
        btext = f"{bshare:.1f}% of {whole}" if not spelled else f"{bshare:.1f}%"
        ctext = (f"{cnt} of {total_n} holdings" if not spelled
                 else f"{cnt} holding" + ("" if cnt == 1 else "s"))
        spelled = True
        ax.text(bshare + 1.4, y + 0.19, btext, va="center", ha="left",
                fontsize=9, color=CINK, fontweight="bold")
        ax.text(cshare + 1.4, y - 0.19, ctext, va="center", ha="left",
                fontsize=8.6, color=CSLATE)
    ax.set_yticks(ys)
    ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=CINK)
    ax.set_xticks([])
    ax.set_xlim(0, 104)
    ax.set_ylim(-0.72, len(rows) - 0.28)
    caption_above(ax, legend, y=1.08)
    return _save(fig, name)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    whole = L["whole"]          # what this register calls the portfolio, in running prose
    ips = ctx.get("ips") or {}
    as_of = ctx.get("client", {}).get("as_of", "")

    funds = ctx.get("funds") or []
    equity = ctx.get("equity") or []
    other = ctx.get("other") or []
    book = funds + equity + other
    # SELF-GATE: below five holdings a size distribution restates the holdings list.
    if len(book) < 5:
        return 0

    n_all = len(book)
    grand = float((ctx.get("totals") or {}).get("grand_inr") or sum(_v(h) for h in book))
    ranked = sorted(book, key=lambda h: -_w(h))

    tail = [h for h in book if _w(h) < TAIL_EDGE]
    tail_share = sum(_w(h) for h in tail)
    tail_val = sum(_v(h) for h in tail)
    big = [h for h in book if _w(h) >= BIG_EDGE]
    # Nothing reaching 8% is a perfectly ordinary book, not a missing figure: the top end is then
    # read off the largest five, and the label below says which of the two the number is.
    big_from_edge = bool(big)
    if not big:
        big = ranked[:5]
    big_share = sum(_w(h) for h in big)
    largest = ranked[0]
    # Risk bands are the framework's, never inferred. A holding it could not place is counted and
    # reported as unplaced rather than assigned a band on the page's own authority.
    tail_high = [h for h in tail if h.get("risk_band") == "High"]
    tail_high_share = sum(_w(h) for h in tail_high)
    # Counted across the WHOLE book, not just the tail, because an unplaced holding of any size is
    # a thing this page cannot speak about. The copy below names that population in words, since
    # "and 4 more" sitting after a sentence about the tail reads as 4 more IN the tail.
    unbanded = [h for h in book if h.get("risk_band") is None]
    unbanded_val = sum(_v(h) for h in unbanded)

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])
    deck.anchor("mod:tail_analysis", s, prio=2)
    deck.scope_tag(s, f"Funds, direct shares and everything else held, {n_all} holdings, "
                      f"as of {as_of}")

    # ---------------- the two ends of the book, before anything else on the page ----------------
    deck.kpi_strip(s, [
        (f"{n_all}", L["k1"], f"Rs {grand:,.0f}"),
        (f"{tail_share:.1f}%", L["k2"], f"{len(tail)} of {n_all} holdings"),
        (f"{big_share:.1f}%", f"Held in the {len(big)} largest",
         (f"each above {BIG_EDGE:.0f}% of {whole}" if big_from_edge
          else f"none of them reaches {BIG_EDGE:.0f}%")),
        (f"{_w(largest):.1f}%", L["k4"], short_name(_core(largest.get("name", "")), KPI_SUB_CH)),
    ], y=1.80)
    deck.rule(s, ML, 2.82, RX - ML, h=0.012)

    # ---------------- left: the distribution ----------------
    # 5.90 rather than the 6.45 this started at. short_name() drops whole trailing WORDS, so a
    # column budget of 32 characters cut "ICICI Prudential Nifty 100 Low Volatility 30 ETF" back
    # to "ICICI Prudential Nifty 100 Low", which ends on a dangling adjective and reads as a
    # rendering fault rather than as a shortened name. The chart carried more white space than it
    # needed, so the width went to the table, where 41 characters keeps a real scheme.
    CHW = 5.90
    deck.txt(s, ML, 2.94, CHW, 0.22, [(L["left"], SANS, 8, NAVY, True, False, 80)])
    rows = []
    for lo, hi, lab in BANDS:
        held = [h for h in book if lo <= _w(h) < hi]
        rows.append((lab, len(held), len(held) / n_all * 100.0, sum(_w(h) for h in held)))
    png = _chart(rows, n_all, L["legend"], whole, "tail_size_bands")
    deck.pic(s, png, ML, 3.16, CHW, 1.90, valign="middle", halign="center")

    if len(tail) and big_from_edge:
        body = (f"{len(tail)} of the {n_all} holdings are under {TAIL_EDGE:.0f}% of {whole} each "
                f"and come to {tail_share:.1f}% between them, Rs {tail_val:,.0f}. The "
                f"{len(big)} largest come to {big_share:.1f}%.")
    elif len(tail):
        body = (f"{len(tail)} of the {n_all} holdings are under {TAIL_EDGE:.0f}% of {whole} each "
                f"and come to {tail_share:.1f}% between them, Rs {tail_val:,.0f}. Nothing reaches "
                f"{BIG_EDGE:.0f}%, and the largest five come to {big_share:.1f}%.")
    else:
        body = (f"No holding here is under {TAIL_EDGE:.0f}% of {whole}, so there is no tail. "
                f"The {len(big)} largest positions come to {big_share:.1f}%.")
    # The placed reading and the unplaced count are joined by a semicolon into ONE sentence, so a
    # clip can never leave the High-risk figure standing alone without the count of holdings the
    # framework could not place at all.
    if tail_high and unbanded:
        body += (f" Within the tail, {len(tail_high)} carry a High risk band, "
                 f"{tail_high_share:.1f}% of {whole}; across everything held, {len(unbanded)} "
                 f"holdings carry no risk band at all, Rs {unbanded_val:,.0f}.")
    elif tail_high:
        body += (f" Within the tail, {len(tail_high)} carry a High risk band, "
                 f"{tail_high_share:.1f}% of {whole}.")
    elif unbanded:
        body += (f" Across everything held, {len(unbanded)} holdings carry no risk band at all, "
                 f"Rs {unbanded_val:,.0f}.")
    body = clip_sentences(body, CALLOUT_BUDGET)
    ch = deck.callout_h(CHW, body, min_h=1.0, max_h=CALLOUT_MAX_H)
    deck.callout(s, ML, 5.14, CHW, ch, L["callout"], body, kind="note")

    # ---------------- right: size set against the desk's call ----------------
    cx = ML + CHW + 0.25
    cw = RX - cx
    deck.txt(s, cx, 2.94, cw, 0.22, [(L["right"], SANS, 8, NAVY, True, False, 80)])
    cols = [("Holding", 0.66, "l"), ("Share", 0.16, "r"), ("Call", 0.18, "c")]
    body_rows = [[short_name(_core(h.get("name", "")), NAME_CH), f"{_w(h):.1f}%",
                  ("pill", _call(h), _call(h))] for h in ranked[:5]]
    deck.table(s, cx, 3.16, cw, cols, body_rows, rowh=0.32, fs=8, hfs=7)

    # ---------------- the cap tests, each struck on the population its cap covers ----------------
    # single_name_cap_pct is per ISIN on direct equity and single-issuer debt. A fund is not in that
    # population, so the largest position on this page is not a candidate for this test at all.
    direct = list(equity) + [o for o in other
                             if str(o.get("sub_category") or "").strip().lower()
                             .startswith("direct fixed")]
    name_cap = ips.get("single_name_cap_pct")
    amc_cap = ips.get("single_amc_cap_pct")
    # single_amc_cap_pct is measured on the manager, so every scheme from one house adds up. The
    # house comes from the statement's own fund-house column where it carries one, and otherwise
    # from the scheme's own leading word, which is a reading of the name and never a similarity
    # match against a list of houses.
    houses = {}
    for f in funds:
        raw = str(f.get("amc") or "").strip()
        if raw in ("", "-", "Unknown"):
            raw = str(f.get("name") or "").strip().split(" ")[0]
        if not raw:
            continue
        w, n = houses.get(raw, (0.0, 0))
        houses[raw] = (w + _w(f), n + 1)
    top_house = max(houses.items(), key=lambda kv: kv[1][0]) if houses else None
    # The house name is bounded because it lands in a fixed-height source strip: a statement that
    # spells a house out in full cannot be allowed to push the line past its box.
    house_name, house_share, house_n = (short_name(top_house[0], 24), top_house[1][0],
                                        top_house[1][1]) if top_house else ("", 0.0, 0)

    cap_rows = []
    if direct and name_cap:
        biggest = max(direct, key=_w)
        over = _w(biggest) > float(name_cap)
        cap_rows.append([L["cap_name"], f"{_w(biggest):.1f}%", f"{float(name_cap):.0f}%",
                         ("pill", "Over" if over else "Aligned", "Breach" if over else "Aligned")])
    if top_house and amc_cap:
        over = house_share > float(amc_cap)
        cap_rows.append([L["amc_name"], f"{house_share:.1f}%", f"{float(amc_cap):.0f}%",
                         ("pill", "Over" if over else "Aligned", "Breach" if over else "Aligned")])
    if cap_rows:
        deck.txt(s, cx, 5.14, cw, 0.20, [(L["mandate"], SANS, 8, NAVY, True, False, 80)])
        deck.table(s, cx, 5.36, cw,
                   [("What is capped", 0.52, "l"), ("Book", 0.16, "r"), ("Limit", 0.14, "r"),
                    ("Status", 0.18, "c")],
                   cap_rows, rowh=0.30, fs=8, hfs=7)

    # ---------------- provenance, and what each cap is actually measured on ----------------
    src = (f"Source: holdings as of {as_of}. Shares are struck on the whole Rs {grand:,.0f} held, "
           f"funds and direct holdings together. ")
    if name_cap and direct:
        src += (f"The {float(name_cap):.0f}% single-name limit is measured per holding on the "
                f"{len(direct)} direct shares and single-issuer deposits here, not on a fund. ")
    elif name_cap:
        # A book of nothing but funds has no population for this cap. Saying so beats printing
        # "measured on the 0 direct shares", and beats leaving the reader to assume it passed.
        src += (f"The {float(name_cap):.0f}% single-name limit covers direct shares and "
                f"single-issuer debt, of which this book holds none, so it is not tested here. ")
    if top_house and amc_cap:
        src += (f"The {float(amc_cap):.0f}% limit is measured on the fund house, so the "
                f"{house_n} schemes from {house_name} add up to one number.")
    deck.source(s, clip_sentences(src, SOURCE_BUDGET))
    return 1
