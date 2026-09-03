# -*- coding: utf-8 -*-
"""quality_consistency, the fund score set against how steadily each fund earned it.

Two readings now travel with every scored scheme. The score says how far ahead of its own
category a fund finished over three and five years. The steadiness reading says how evenly it
got there: the month-by-month hit rate against its category, and how much the relative return
moved about. The two agree only loosely, so the second is new information rather than the first
restated, and a fund's place on one axis does not tell you its place on the other.

THE RULE THIS PAGE OBEYS (Principal ruling 2026-09-03). Steadiness is CONTEXT, never a verdict.
The desk's call always wins. A large share of the funds this desk tells a client to sell sit in
the top half on steadiness, and that is not a contradiction to be hidden or softened: it is a
fund that is reliably behind. So the quadrant naming says exactly that, and every plotted fund
carries its call, by dot colour on the chart and by a pill in the table beside it. An adviser
holding this page in front of a client has something true to say about a Sell sitting high on
the steadiness axis.

Self-gates to 0 slides when fewer than four held funds carry both readings, which is what an
older score file looks like: the two columns are simply absent and the page never appears.

The 2x2 is built in this file rather than in chart_lib because it exists for this page alone.
It goes through chart_lib's own figure scaffold and palette by the same import route
chart_ext_a/chart_ext_b use, so it matches every other chart in the deck.
"""
import re

import charts as _CH  # noqa: F401  (side effect: scripts on sys.path + CHART_OUTDIR set)
import matplotlib.pyplot as plt                                              # noqa: E402
from chart_lib import _fig, _save, SLATE, HAIR, PANEL, SELL as CSELL, SELLBG, \
    HOLD as CHOLD, HOLDBG                                                    # noqa: E402
from slidekit import (NAVY, INK as PINK, SLATE as PSLATE, SELL, HOLD, AMBER, GOLD, SANS, SERIF,
                      ML, RX, short_name)

CAMBER = "#92400E"
CGOLD = "#F2A93C"      # slidekit GOLD, byte-exact; chart_lib carries no counterpart          # matplotlib mirror of slidekit AMBER
CGOLDTEXT = "#8A6E1B"       # the readable gold used for chart annotation across chart_lib

SPLIT = 50.0                # both readings run 0-100; at or above 50 is the top half
X0, X1 = -4.0, 104.0        # a little air so a fund at 0 or 100 is not clipped by the frame
Y0, Y1 = -5.0, 105.0

# The desk's vocabulary, kept intact. REC_STYLE has no "Hold (watch)" key of its own, so the
# pill borrows the amber caution styling; the label a client reads is still the real call.
CALL_PILL = {"Sell": "Sell", "Trim": "Trim", "Hold": "Hold", "Hold (watch)": "Trim"}
# Trim and Hold (watch) had the same amber. The legend then printed two identical swatches against
# two different names, and an unlabelled amber dot could not be resolved to a call at all, which on a
# real book hid the single largest actioned position among four Hold (watch) dots. Trim takes gold.
CALL_DOT = {"Sell": CSELL, "Trim": CGOLD, "Hold (watch)": CAMBER, "Hold": CHOLD}
CALL_RGB = {"Sell": SELL, "Trim": GOLD, "Hold (watch)": AMBER, "Hold": HOLD}
ACTING = ("Sell", "Trim", "Hold (watch)")   # calls the desk would act on
LEGEND_ORDER = ("Sell", "Trim", "Hold (watch)", "Hold")

LABELS = {
    "hni": {"eyebrow": "Score against steadiness",
            "title": "How far ahead each fund finished, and how steadily it got there",
            "left": "EVERY SCORED FUND, PLACED ON BOTH READINGS",
            "right": "FUNDS WE WOULD ACT ON, RANKED BY STEADINESS",
            "xlab": "How far ahead of its own category  (0 to 100)",
            "ylab": "How steadily it got there  (0 to 100)"},
    "std": {"eyebrow": "Score against steadiness",
            "title": "How far ahead each fund finished, and how steadily it got there",
            "left": "EVERY SCORED FUND, PLACED ON BOTH READINGS",
            "right": "FUNDS WE WOULD ACT ON, RANKED BY STEADINESS",
            "xlab": "How far ahead of its own category  (0 to 100)",
            "ylab": "How steadily it got there  (0 to 100)"},
    "simple": {"eyebrow": "Ahead or behind, and how steadily",
               "title": "Where each of your funds sits, and what we suggest",
               "left": "YOUR FUNDS, ON BOTH READINGS",
               "right": "THE FUNDS WE WOULD CHANGE",
               "xlab": "Ahead of similar funds  (0 to 100)",
               "ylab": "How steady that has been  (0 to 100)"},
}

# The naming is the whole point of the page. Low score with high steadiness is a fund that is
# reliably behind, and it is named that way rather than softened.
QUADS = {
    "hi_hi": "Ahead of its category, and steadily",
    "hi_lo": "Ahead overall, in bursts",
    "lo_hi": "Reliably behind",
    "lo_lo": "Behind, and erratic",
}
QUADS_SIMPLE = {
    "hi_hi": "Ahead of similar funds, and steadily",
    "hi_lo": "Ahead overall, in bursts",
    "lo_hi": "Reliably behind",
    "lo_lo": "Behind, and erratic",
}


def _num(v):
    """A reading, or None. Score files carry blanks for uncovered schemes."""
    try:
        if v is None:
            return None
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f else None          # a not-a-number value is no reading at all


def _quad_key(score, cons):
    return ("hi_" if score >= SPLIT else "lo_") + ("hi" if cons >= SPLIT else "lo")


# Everything from the plan or option marker onward is administrative tail, and it is the part
# a client never needs to read on a chart. Cutting it first is what lets the SCHEME survive.
_TAIL = re.compile(r"\s*[-–]\s*(?:regular|direct|growth|payout|idcw|dividend|income|bonus)\b.*$",
                   re.IGNORECASE)


_FUNDWORD = re.compile(r"\s+fund$", re.IGNORECASE)


def _core(name):
    """The scheme, with the plan and option tail removed. The trailing word "fund" goes too:
    short_name() only strips it in title case, so an all-capitals statement name kept it and
    the chart printed "CANARA ROBECO SMALL CAP FUND (Reg)" where the word earns no room."""
    return _FUNDWORD.sub("", _TAIL.sub("", (name or "")).strip(" -–")).strip()


def _plan(name):
    up = (name or "").upper()
    return "Dir" if "DIRECT" in up else ("Reg" if "REGULAR" in up else "")


def _labels(names, n, dup_n):
    """Display names that stay distinct from each other.

    short_name() drops words from the TAIL, and the tail is where a scheme's identity lives, so
    two schemes from one house ("CANARA ROBECO SMALL CAP", "CANARA ROBECO LARGE AND MID CAP") and
    the two plans of one scheme all collapse to the same string. The first render of this page put
    two rows reading "CANARA ROBECO" side by side and two dots both reading "ICICI Prudential",
    which a client reads as a rendering fault rather than as the separate holdings they are.

    So: cut the plan and option tail first, shorten what is left, and where entries still land on
    the same string spend more room on them, at `dup_n`, plus the plan marker. Names that are
    already distinct pay nothing. `dup_n` is generous for the chart, which measures each label and
    drops any that will not fit, and tight for the table, whose column has a hard width."""
    base = [short_name(_core(x), n) for x in names]
    tally = {}
    for b in base:
        tally[b] = tally.get(b, 0) + 1
    out = list(base)
    for i, b in enumerate(base):
        if tally[b] < 2:
            continue
        plan = _plan(names[i])
        wide = short_name(_core(names[i]), dup_n)
        out[i] = f"{wide} ({plan})" if plan else wide
    return out


# OFFSETS IN POINTS, not data units. Displacing a label by up to 15 DATA units moved it roughly an
# inch on a 6.93in chart, and five of eight labels ended up closer to a different fund's dot than to
# their own. One printed a red Sell name 6.7 units from a green Hold dot. The house pattern
# everywhere else in chart_lib is textcoords="offset points" at 6 to 11 points, which keeps a label
# glued to the point it names; anything past ~12 points earns a leader line.
_OFFSETS = ((0, 10), (0, -12), (14, 5), (-14, 5), (14, -8), (-14, -8),
            (0, 19), (0, -21), (22, 10), (-22, 10), (22, -12), (-22, -12),
            (0, 28), (0, -30), (32, 14), (-32, 14), (32, -16), (-32, -16))
_LEADER_AT = 12.0           # points of displacement past which the label gets a leader line


def _place(fig, ax, items, reserved):
    """Direct labels, positioned against MEASURED text extents rather than a character-count
    guess. The guess was wrong by a factor of two on the first render and two labels printed on
    top of each other; matplotlib will tell us the real box if we ask it. A label that finds no
    clear air is dropped, because an unreadable pile-up costs more than one missing name and the
    dot still carries the call by its colour (value_map's rule, applied here)."""
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()

    def ext(artist, pad_x=1.2, pad_y=1.2):
        bb = artist.get_window_extent(renderer=rend)
        p0 = inv.transform((bb.x0, bb.y0))
        p1 = inv.transform((bb.x1, bb.y1))
        return (min(p0[0], p1[0]) - pad_x, min(p0[1], p1[1]) - pad_y,
                max(p0[0], p1[0]) + pad_x, max(p0[1], p1[1]) + pad_y)

    taken = [ext(a) if hasattr(a, "get_window_extent") else a for a in reserved]

    def clashes(b):
        return any(not (b[2] <= t[0] or b[0] >= t[2] or b[3] <= t[1] or b[1] >= t[3])
                   for t in taken)

    pts = [(x, y) for x, y, _t, _c in items]

    # Two share classes of one scheme carry the SAME score and the same steadiness by construction,
    # so they plot on top of each other. Counting a co-located twin as "another fund" made ownership
    # unsatisfiable and silently dropped every label on the chart. Anything inside this radius of the
    # anchor is the same position, not a rival for the name.
    SAME = 1.5

    def owns(b, xi, yi):
        """The label's box must sit nearer the dot it names than any DISTINCT other dot. A name that
        drifts onto a neighbour is worse than a missing name: the reader has no way to tell."""
        cx, cy = (b[0] + b[2]) / 2.0, (b[1] + b[3]) / 2.0
        mine = (cx - xi) ** 2 + (cy - yi) ** 2
        return all(mine <= (cx - px) ** 2 + (cy - py) ** 2
                   for px, py in pts
                   if (px - xi) ** 2 + (py - yi) ** 2 > SAME ** 2)

    for x, y, text, col in items:
        # The leader is built at construction and then hidden. matplotlib creates the arrow patch
        # in Annotation.__init__ from arrowprops, so it cannot be attached later; assigning to the
        # attribute afterwards raises and, because engine.build swallows module exceptions, the
        # whole page would vanish from the deck with no error on any book dense enough to need one.
        t = ax.annotate(text, xy=(x, y), xytext=(0, 9), textcoords="offset points",
                        ha="center", va="center", fontsize=7.4, color=col,
                        fontweight="bold", zorder=6,
                        arrowprops=dict(arrowstyle="-", color=col, lw=0.6,
                                        alpha=0.55, shrinkA=1, shrinkB=3))
        t.arrow_patch.set_visible(False)
        for dx, dy in _OFFSETS:
            t.set_position((dx, dy))
            b = ext(t)
            if b[0] < X0 + 0.5 or b[2] > X1 - 0.5 or b[1] < Y0 + 0.5 or b[3] > Y1 - 0.5:
                continue
            if clashes(b) or not owns(b, x, y):
                continue
            t.arrow_patch.set_visible((dx * dx + dy * dy) ** 0.5 > _LEADER_AT)
            taken.append(b)
            break
        else:
            t.remove()


def _chart(rows, counts, quads, xlab, ylab, name, figsize=(9.0, 4.28)):
    """rows: [(score, steadiness, value_inr, call, short label)]. counts: per-quadrant tally."""
    fig, ax = _fig(figsize)
    tints = [((SPLIT, SPLIT, X1 - SPLIT, Y1 - SPLIT), HOLDBG, 0.55),
             ((SPLIT, Y0, X1 - SPLIT, SPLIT - Y0), PANEL, 0.90),
             ((X0, SPLIT, SPLIT - X0, Y1 - SPLIT), SELLBG, 0.30),
             ((X0, Y0, SPLIT - X0, SPLIT - Y0), SELLBG, 0.50)]
    for (rx, ry, rw, rh), col, al in tints:
        ax.add_patch(plt.Rectangle((rx, ry), rw, rh, color=col, alpha=al, zorder=0))
    ax.axvline(SPLIT, color=SLATE, lw=1.1, ls=(0, (4, 3)), zorder=1)
    ax.axhline(SPLIT, color=SLATE, lw=1.1, ls=(0, (4, 3)), zorder=1)

    def tally(k):
        n = counts.get(k, 0)
        return f"{n} fund" if n == 1 else f"{n} funds"

    caps = [("lo_hi", X0 + 3, Y1 - 2, "left", "top", CSELL, 9.4, "bold"),
            ("hi_hi", X1 - 3, Y1 - 2, "right", "top", CHOLD, 8.6, "normal"),
            ("lo_lo", X0 + 3, Y0 + 2, "left", "bottom", CSELL, 8.6, "normal"),
            ("hi_lo", X1 - 3, Y0 + 2, "right", "bottom", CGOLDTEXT, 8.6, "normal")]
    cap_art = [ax.text(tx, ty, f"{quads[key]}\n{tally(key)}", ha=ha, va=va, fontsize=fs,
                       color=col, fontweight=wt, linespacing=1.45, zorder=2)
               for key, tx, ty, ha, va, col, fs, wt in caps]

    xs = [r[0] for r in rows]
    ys = [r[1] for r in rows]
    sz = [min(620, max(78, (r[2] or 0) / 1e5 * 2.2)) for r in rows]
    cols = [CALL_DOT.get(r[3], SLATE) for r in rows]
    ax.scatter(xs, ys, s=sz, c=cols, alpha=0.85, edgecolors="white", linewidths=1.2, zorder=3)

    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1)
    fig.canvas.draw()
    # the caption corners and the dots themselves are occupied ground before any label is placed
    ab = ax.get_window_extent()
    sx, sy = ab.width / (X1 - X0), ab.height / (Y1 - Y0)
    # Only the quadrant captions are hard-reserved. Reserving all 28 dots as well left no clear air
    # anywhere in the crowded quadrant, and the previous code bought room by flinging labels up to
    # an inch from their own point, which is how five of eight ended up nearer a different fund's
    # dot. A label may now sit close to a dot that is not its own; what stops it being MISREAD is
    # the ownership test in _place, not distance from every marker. Labels still never overlap each
    # other, and one that cannot be placed honestly is dropped.
    reserved = list(cap_art)
    order = sorted(rows, key=lambda r: (0 if r[3] in ACTING else 1, -(r[2] or 0)))
    # Name the funds the desk would act on, plus the largest holdings. Naming all 28 on a chart this
    # size cannot be done without either overlap or misattribution.
    named = [r for r in order if r[3] in ACTING][:8] +             [r for r in order if r[3] not in ACTING][:4]
    _place(fig, ax, [(r[0], r[1], r[4], CALL_DOT.get(r[3], SLATE)) for r in named], reserved)

    ax.set_xticks([0, 25, 50, 75, 100]); ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xlabel(xlab, fontsize=9.6, color=SLATE)
    ax.set_ylabel(ylab, fontsize=9.6, color=SLATE)
    ax.tick_params(labelsize=9)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_visible(True); ax.spines[sp].set_color(HAIR)
    return _save(fig, name)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    quads = QUADS_SIMPLE if reg == "simple" else QUADS
    as_of = ctx.get("client", {}).get("as_of", "")

    held = ctx.get("funds") or []
    rows = []
    for f in held:
        sc, cs = _num(f.get("qfra")), _num(f.get("consistency"))
        if sc is None or cs is None:
            continue
        call = f.get("verdict") or "Hold"
        rows.append({"name": f.get("name", ""), "score": sc, "cons": cs, "call": call,
                     "value": float(f.get("value_inr") or 0)})
    # SELF-GATE: an older score file carries neither reading, and a 2x2 drawn on three points
    # says nothing. No page at all beats a thin one.
    if len(rows) < 4:
        return 0

    counts = {}
    for r in rows:
        k = _quad_key(r["score"], r["cons"])
        r["quad"] = k
        counts[k] = counts.get(k, 0) + 1

    acting = [r for r in rows if r["call"] in ACTING]
    cutting = [r for r in rows if r["call"] in ("Sell", "Trim")]
    steady_cut = [r for r in cutting if r["cons"] >= SPLIT]
    steady_val = sum(r["value"] for r in steady_cut)
    # The mirror of the case the callout was written for. Funds we are KEEPING also land in the
    # "reliably behind" field, and an adviser is far more likely to be asked about those: a green
    # Hold dot sitting inside a red-tinted quadrant reads as a contradiction unless the page says
    # why. It was silent on this direction until now.
    held_behind = [r for r in rows if r["quad"] == "lo_hi" and r["call"] == "Hold"]
    held_val = sum(r["value"] for r in held_behind)

    s = deck.content(2, "The Fund Book", L["eyebrow"], L["title"])
    deck.anchor("mod:quality_consistency", s, prio=3)
    deck.scope_tag(s, f"MF sleeve · {len(rows)} of {len(held)} funds carry both readings · "
                      f"as of {as_of}")

    # ---------------- left: the 2x2 ----------------
    CHW = 6.93
    deck.txt(s, ML, 1.98, CHW, 0.22, [(L["left"], SANS, 8, NAVY, True, False, 80)])
    plotted = _labels([r["name"] for r in rows], 24, dup_n=40)
    png = _chart([(r["score"], r["cons"], r["value"], r["call"], lab)
                  for r, lab in zip(rows, plotted)],
                 counts, quads, L["xlab"], L["ylab"], "qc_quadrant")
    deck.pic(s, png, ML, 2.20, CHW, 3.30, valign="top", halign="left")

    # colour legend in PowerPoint rather than inside the PNG: the call vocabulary is house
    # chrome and stays in Bahnschrift, at the same size as every other legend in the deck
    lx, ly = ML, 5.62
    for call in LEGEND_ORDER:
        if not any(r["call"] == call for r in rows):
            continue
        deck.oval(s, lx, ly + 0.045, 0.11, CALL_RGB.get(call, PSLATE))
        # 0.0638 in/char is what check_geometry2 models for 8.5pt Bahnschrift; a guess here is the
        # same character-count estimate that put labels on the wrong dots, so it carries real slack.
        tw = 0.0638 * len(call) + 0.16
        deck.txt(s, lx + 0.17, ly, tw, 0.22,
                 [(call, SANS, 8.5, PINK, False)], wrap=False)
        lx += 0.17 + tw + 0.26
    deck.txt(s, ML, 5.98, CHW, 0.34,
             [("Dot colour is the call and dot size is the amount held. Both readings run 0 to "
               "100 and the page splits each at 50.", SERIF, 8, PSLATE, False, True)], ls=1.0)

    # ---------------- right: the calls, with the steadiness beside them ----------------
    cx = 8.05; cw = RX - cx
    deck.txt(s, cx, 1.98, cw, 0.22, [(L["right"], SANS, 8, NAVY, True, False, 80)])
    cols = [("Scheme", 0.47, "l"), ("Score", 0.13, "r"), ("Steadiness", 0.16, "r"),
            ("Call", 0.24, "c")]
    ranked = sorted(acting, key=lambda r: (-r["cons"], -r["value"]))
    shown = ranked[:5]
    names = _labels([r["name"] for r in shown], 22, dup_n=15)
    body = [[nm, f"{r['score']:.0f}", f"{r['cons']:.0f}",
             ("pill", r["call"], CALL_PILL.get(r["call"], r["call"]))]
            for r, nm in zip(shown, names)]
    if body:
        ty = deck.table(s, cx, 2.20, cw, cols, body, rowh=0.34, fs=8, hfs=7)
        if len(ranked) > 5:
            rest = len(ranked) - 5
            deck.txt(s, cx, ty + 0.06, cw, 0.24,
                     [(f"and {rest} more, each listed in the fund book.", SERIF, 8,
                       PSLATE, False, True)])
    else:
        deck.txt(s, cx, 2.24, cw, 0.60,
                 [("Every scored fund here is a Hold. Steadiness stays context on this page "
                   "either way.", SERIF, 9.5, PINK, False)], ls=1.08)

    if steady_cut:
        note = (f"A fund can be steady and still be behind. {len(steady_cut)} of the "
                f"{len(cutting)} funds we would sell or trim sit in the top half on steadiness, "
                f"Rs {steady_val:,.0f} between them, and the call stands.")
    elif cutting:
        note = (f"None of the {len(cutting)} funds we would sell or trim sits in the top half "
                f"on steadiness here. Where one does, it is a fund that is reliably behind, and "
                f"the call still stands.")
    elif acting:
        # `acting` includes Hold (watch), `cutting` does not. Keying the copy off `cutting` alone
        # printed "Nothing on this page is a call" directly above a populated table headed with
        # the funds we would act on, which contradicted itself.
        note = (f"No fund here is sold or trimmed. {len(acting)} sit under review, listed beside "
                f"this chart, and steadiness is one of the readings that keeps them there.")
    else:
        note = ("Nothing on this page is a call. Steadiness tells you how evenly a fund earned "
                "its position, and the desk decides what to do about it.")
    if held_behind:
        n = len(held_behind)
        note += (f" {n} we are keeping sit{'' if n > 1 else 's'} there too, Rs {held_val:,.0f}: "
                 f"behind so far, steady about it, not yet a sell."
                 if n > 1 else
                 f" One we are keeping sits there too, Rs {held_val:,.0f}: behind so far, steady "
                 f"about it, not yet a sell.")
    nh = deck.callout_h(cw, note, min_h=1.0, max_h=1.92)
    deck.callout(s, cx, 4.62, cw, nh,
                 "Steadiness is context, not the call" if reg != "simple"
                 else "How to read this page", note, kind="note")

    deck.source(s, f"Source: each scheme's fund score, how far it finished ahead of its own "
                   f"category over three and five years, set against how steadily it got there. "
                   f"Both readings run 0 to 100. Scores as of {as_of}. Where a fund sits here is "
                   f"context; the desk sets every call.")
    deck.score_band(s)
    return 1
