# -*- coding: utf-8 -*-
"""eval_framework, how we evaluate what you hold. The method page that sits in front of the
holding pages and tells the reader what is coming.

Four readings travel with a holding through this deck: how far ahead or behind it finished against
its own category, how steadily it got there, what can go wrong with it and how fast it turns into
cash, and how much of the book it carries. The page names all four in one plain sentence each, and
then states the rule that turns them into an action, which is the reason the page exists: several
readings pointing the same way is a priority, only some of them pointing that way is a watch.

WHAT MAKES THIS PAGE HONEST RATHER THAN A DIAGRAM. Every coverage number on it is counted from
THIS book at render time, funds and non-funds together, so the page says how many holdings each
reading actually reaches and how many it does not. The two performance readings reach only the
schemes that carry a score; the risk and liquidity bands reach everything the framework could
place, and the value it could not place is printed rather than smoothed away; concentration is the
one reading that reaches every holding, because a weight exists for all of them. A book where the
scored sleeve is a minority of the money will say so on this page in its own numbers.

THE LIMIT IS PART OF THE METHOD, not a disclaimer. The closing line, that these readings describe
a record and a structure and are not a forecast of return, is rendered in the body of the page at
body size. It is not softened, shortened or moved into the source line in any register.

This page NEVER self-gates to zero. A book with no scored fund at all still has a method, and the
reader is owed the method plus the honest statement that the performance readings reach nothing
here. Every count is guarded so an empty list prints a true sentence instead of raising, because
engine.build swallows a module exception and the page would vanish with no error.

Every shape on this page is a PowerPoint primitive, deliberately: there is no chart image, so both
geometry gates can see all of it. The two vertical stacks chain each y off the ACTUAL height of
the block above, and the three fixed anchors near the bottom carry clamps, because that is where a
later copy edit would otherwise push text into the source line.
"""
import math

from slidekit import (NAVY, GOLD, INK, SLATE, HAIR, SANS, SERIF, ML, UW, RX, clip_sentences)

LABELS = {
    "hni": {"eyebrow": "How we evaluate what you hold",
            "title": "The four readings behind every call, and how they combine",
            "left": "WHAT WE JUDGE A HOLDING ON",
            "right": "HOW THE FOUR COMBINE INTO AN ACTION",
            "rule_title": "Where several point the same way",
            "cover": "WHAT THIS REVIEW READS, AND WHAT IT DOES NOT"},
    "std": {"eyebrow": "How we evaluate what you hold",
            "title": "The four readings behind every call, and how they combine",
            "left": "WHAT WE JUDGE A HOLDING ON",
            "right": "HOW THE FOUR COMBINE INTO AN ACTION",
            "rule_title": "Where several point the same way",
            "cover": "WHAT THIS REVIEW READS, AND WHAT IT DOES NOT"},
    "simple": {"eyebrow": "How we look at what you hold",
               "title": "The four things we check, and how they add up to an action",
               "left": "WHAT WE LOOK AT",
               "right": "HOW THE FOUR ADD UP",
               "rule_title": "When several agree",
               "cover": "WHAT WE CAN READ, AND WHAT WE CANNOT"},
}

# One plain sentence per reading. The order is the order the deck uses them in.
DIMS = {
    "std": [
        ("Performance against its own category",
         "How far ahead or behind a fund finished, over three and five years, against funds "
         "with the same mandate."),
        ("Consistency",
         "Whether it got there steadily or in bursts."),
        ("Risk and liquidity",
         "What can go wrong with a holding, and how quickly you could get out of it."),
        ("Concentration",
         "How much of the book any one holding, manager or issuer carries."),
    ],
    "simple": [
        ("How it did against similar holdings",
         "How far ahead or behind a fund finished over three and five years, set against "
         "funds doing the same job."),
        ("How steady that was",
         "Whether it got there steadily or in bursts."),
        ("Risk, and how fast you could get out",
         "What can go wrong with a holding, and how fast you could turn it into cash."),
        ("How much sits in one place",
         "How much of your money sits with one holding, one manager or one borrower."),
    ],
}
DIMS["hni"] = DIMS["std"]

COVER_ROWS = {
    "std": ("Performance", "Consistency", "Risk and liquidity", "Concentration"),
    "simple": ("How it did", "How steady", "Risk and getting out", "All in one place"),
}
COVER_ROWS["hni"] = COVER_ROWS["std"]

RULE = {
    "std": ("Where several of these readings point the same way, the action is a high priority. "
            "Where only some of them do, it is a watch rather than a trade."),
    "simple": ("When several of these point the same way, we act on it first. When only some do, "
               "we watch it rather than trade it."),
}
RULE["hni"] = RULE["std"]

# The required sentence, rendered verbatim in every register. The second half is the half that
# gets softened when anyone paraphrases it, so it is a separate bold run and reads as the claim
# the page is making rather than as a trailing qualifier.
LIMIT = ("These readings describe a record and a structure. ",
         "They are not a forecast of return.")

# A status is not a recommendation, so it is not a call. "No View" is the firm's own label for a
# holding outside framework coverage, and "Suspended" is a state of the instrument (delisted,
# insolvent, under NCLT). Counting either as a call would overstate what this desk has said.
NO_CALL = {"", "-", "no view", "none", "suspended", "not covered"}

# The width model check_geometry2 uses for Georgia, with slack. Line counts here decide box
# heights, so guessing is how a paragraph ends up clipped or in the footer band.
_GEO_W = 0.0102


def _num(v):
    """A reading, or None. A score file carries blanks for schemes outside coverage."""
    try:
        if v is None:
            return None
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None          # a not-a-number value is no reading at all


def _val(h):
    return _num(h.get("value_inr")) or 0.0


def _placed(h):
    """Both bands, because the reading is one reading. The framework sets a risk band and a
    liquidity band from the same sub-category, so a holding carries both or neither; requiring
    both means a half-placed holding is reported as a gap rather than counted as covered."""
    return bool((h.get("risk_band") or "").strip()) and bool((h.get("liq_band") or "").strip())


def _call(h):
    """The label this desk has put on the holding, lower-cased for the no-call test. Funds carry
    a verdict, direct shares and everything else carry rec; either may be absent."""
    for k in ("verdict", "rec"):
        v = (h.get(k) or "").strip()
        if v:
            return v.lower()
    return ""


def _lines(text, w, pt, fac=1.08):
    """Wrapped line count for Georgia at pt in a box w inches wide, on the gate's own model."""
    if w <= 0.05:
        return 1
    return max(1, math.ceil(len(text or "") * _GEO_W * pt * fac / w))


def _count(n, sing, plur):
    return f"{n} {sing}" if n == 1 else f"{n} {plur}"


def _cov_row(label, read, of, unit_s, unit_p):
    """One coverage row: what the reading reaches, and what it does not, on the same base.
    Both numbers are on the SAME denominator so the row cannot be read as a rate."""
    if of <= 0:
        return [label, ("c", f"no {unit_p} held", SLATE, True), ("c", "none", SLATE, True)]
    miss = of - read
    return [label,
            ("c", f"{read} of {of} {unit_p}", INK, True),
            ("c", "none" if miss <= 0 else _count(miss, unit_s, unit_p),
             SLATE if miss <= 0 else INK, True)]


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    dims = DIMS.get(reg, DIMS["std"])
    rule_body = RULE.get(reg, RULE["std"])
    as_of = (ctx.get("client") or {}).get("as_of", "")

    funds = list(ctx.get("funds") or [])
    allh = funds + list(ctx.get("equity") or []) + list(ctx.get("other") or [])
    n_funds, n_all = len(funds), len(allh)

    # ---- coverage, counted from this book rather than described ----
    n_perf = sum(1 for f in funds if _num(f.get("qfra")) is not None)
    n_cons = sum(1 for f in funds if _num(f.get("consistency")) is not None)
    n_band = sum(1 for h in allh if _placed(h))
    n_wt = sum(1 for h in allh if _num(h.get("weight_pct")) is not None)
    unbanded_val = sum(_val(h) for h in allh if not _placed(h))
    nocall = [h for h in allh if _call(h) in NO_CALL]
    nocall_val = sum(_val(h) for h in nocall)
    n_called = n_all - len(nocall)

    s = deck.content(0, "Understanding", L["eyebrow"], L["title"])
    deck.anchor("mod:eval_framework", s, prio=1)
    deck.scope_tag(s, "Every holding in the book, funds and everything else · "
                      + (_count(n_all, "holding", "holdings") if n_all else "none held")
                      + f" · as of {as_of}")

    # ================= left: the four readings =================
    lx, lw = ML, 5.35
    deck.txt(s, lx, 1.98, lw, 0.22, [(L["left"], SANS, 8, NAVY, True, False, 80)])
    tw = lw - 0.42                      # text column, right of the index numeral
    # Each block is sized to its own sentence, then the leftover height is shared between the
    # separators so the column lands level with the right one. A fixed gap left an inch of dead
    # white below Concentration on the first render and the page looked half-finished.
    LY0, LY1 = 2.26, 6.02
    heights = [0.28 + _lines(t, tw, 9.5) * 0.165 + 0.06 for _n, t in dims]
    gap = 0.20 if len(dims) < 2 else max(0.18, min(0.46,
          (LY1 - LY0 - sum(heights)) / (len(dims) - 1)))
    y = LY0
    for i, (name, sentence) in enumerate(dims):
        deck.txt(s, lx, y + 0.03, 0.34, 0.20,
                 [(f"{i + 1:02d}", SANS, 8.5, GOLD, True, False, 60)])
        deck.txt(s, lx + 0.42, y, tw, 0.24, [(name, SANS, 10.5, INK, True)])
        deck.txt(s, lx + 0.42, y + 0.28, tw, heights[i] - 0.28,
                 [(sentence, SERIF, 9.5, SLATE, False)], ls=1.06)
        y += heights[i]
        if i < len(dims) - 1:
            deck.rule(s, lx, y + gap / 2.0, lw, HAIR, 0.006)
            y += gap
    left_end = y

    # ================= right: the rule, then the coverage =================
    rx, rw = 6.65, RX - 6.65
    deck.vrule(s, 6.46, 1.98, max(left_end, 6.10) - 1.98, HAIR, 0.008)
    deck.txt(s, rx, 1.98, rw, 0.22, [(L["right"], SANS, 8, NAVY, True, False, 80)])

    # The priority rule is the point of the page, so it gets the firm's own voice box. Height is
    # callout_h-derived and then capped: everything below this block is chained off it, and an
    # over-tall box here is how a later edit would push the closing line into the source line.
    ph = min(deck.callout_h(rw, rule_body, min_h=0.95, max_h=1.45), 1.24)
    deck.callout(s, rx, 2.26, rw, ph, L["rule_title"], rule_body, kind="human")

    cy = min(2.26 + ph + 0.13, 3.60)
    deck.txt(s, rx, cy, rw, 0.22, [(L["cover"], SANS, 8, NAVY, True, False, 80)])
    cols = [("Reading", 0.44, "l"), ("Read on", 0.28, "r"), ("Not read", 0.28, "r")]
    # Short row labels, not the full reading names above them: the column is 2.4in wide and a
    # wrapped label inside a 0.32in row reads as a rendering fault rather than as a name.
    rl = COVER_ROWS.get(reg, COVER_ROWS["std"])
    rows = [
        _cov_row(rl[0], n_perf, n_funds, "fund", "funds"),
        _cov_row(rl[1], n_cons, n_funds, "fund", "funds"),
        _cov_row(rl[2], n_band, n_all, "holding", "holdings"),
        _cov_row(rl[3], n_wt, n_all, "holding", "holdings"),
    ]
    ty = deck.table(s, rx, min(cy + 0.30, 3.90), rw, cols, rows, rowh=0.32, fs=8, hfs=7)

    # ---- the two honest counts, in words: what the performance readings reach, and how much of
    # the book this desk has issued no call on at all ----
    reach = ("The readings on how a fund did reach" if reg == "simple"
             else "The performance readings reach")
    # "reach 0 of these 75" reads like a broken count; "none of these 75" reads like the fact it is
    reach += " none of" if n_perf == 0 else f" {n_perf} of"
    if n_all == 0:
        note = "There are no holdings in this book to read."
    elif nocall:
        # Kept short on purpose. The first draft ran to 187 characters in the plain-language
        # register, the three-line budget below then dropped its LAST sentence, and the sentence it
        # dropped was the no-call count: the one fact on this page a reader is owed. Two short
        # sentences survive the clip in every register instead of one long one that does not.
        note = (f"{reach} these {n_all} holdings. A call is issued on {n_called}. "
                f"The other {len(nocall)}, Rs {nocall_val:,.0f} of the book, are read here "
                f"but carry no call.")
    else:
        note = f"{reach} these {n_all} holdings. A call is issued on every one of them."
    # Clipped to whole sentences inside a three-line budget, as the last line of defence only.
    # The paragraph sits directly above the closing line, so it is the one block on the page that
    # must not be allowed to grow.
    note = clip_sentences(note, int(3 * rw / (_GEO_W * 8.5 * 1.03)) - 6)
    deck.txt(s, rx, min(ty + 0.11, 5.60), rw, 0.58,
             [(note, SERIF, 8.5, SLATE, False, True)], ls=1.04)

    # ================= the limit, in the body of the page =================
    deck.rule(s, ML, 6.18, UW, NAVY, 0.014)
    deck.txt(s, ML, 6.26, UW, 0.26,
             [[(LIMIT[0], SERIF, 11, INK, False), (LIMIT[1], SERIF, 11, INK, True)]])

    src = (f"Source: the holdings in this book as of {as_of}. Every count above is taken from "
           f"the holdings themselves, not assumed.")
    if unbanded_val > 0:
        src += (f" Rs {unbanded_val:,.0f} carries no risk or liquidity band and is counted here "
                f"as unbanded.")
    deck.source(s, src)
    return 1
