# -*- coding: utf-8 -*-
"""risk_liquidity, the whole book read on both risk axes at once.

The firm's Risk and Liquidity framework places every holding twice: on what can go wrong, and on
how fast the holder gets out. Read one at a time, each axis is ordinary. Read together they answer
the question a mandate actually asks, which is how much of the book is both risky and slow to sell,
and this page is the reason the framework exists.

WHAT THE PAGE IS. A 3x3 grid of the whole portfolio, risk down and liquidity across, each cell
carrying its rupee value and its share of the book. Shading deepens toward the corner where high
risk meets low liquidity, so the corner that matters is the one the eye lands on. Beside it sit the
four mandate tests this grid decides, each computed live against its own cap or floor, and a breach
is stated in the same flat voice as a pass.

WHAT IT IS NOT. It is not a forecast and carries no view on what any holding does next. Every figure
is the book as it stands on the as-of date.

THE UNBANDED FIGURE IS PART OF THE ANSWER, not a footnote. A holding the framework could not place
carries no band at all, and the honest reading is that it is absent from the grid, never that it is
low risk. It gets its own block, in rupees and as a share of the book, next to the grid it is not on.

Self-gates to 0 slides when fewer than five holdings carry both bands, which is what a book looks
like when the band file is missing: the axes are simply absent and the page never appears.

The grid is drawn in PowerPoint shapes rather than as a chart image on purpose. A nine-cell matrix
of numbers is text, the layout gates can read text, and a chart image would hide any overlap inside
it from every check that runs on this deck.
"""
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from slidekit import (NAVY, INK, SLATE, HAIR, PANEL, WHITE, SELL, SELLBG, HOLDBG, AMBERBG,
                      SANS, SERIF, ML, RX, short_name, clip_sentences)

BANDS = ("High", "Medium", "Low")
# Severity is position on the grid, not size of the holding. Risk climbs one way and liquidity the
# other, so the sum runs 0 at the safe corner (low risk, sells quickly) to 4 at the corner the
# mandate caps (high risk, slow to sell).
RISK_RANK = {"High": 2, "Medium": 1, "Low": 0}
LIQ_RANK = {"High": 0, "Medium": 1, "Low": 2}
SEV_FILL = {0: HOLDBG,                          # the safe corner, sells quickly and low risk
            1: RGBColor(0xED, 0xF6, 0xF1),      # HOLDBG lightened, the only tint the brand lacks
            2: PANEL,
            3: AMBERBG,
            4: SELLBG}                          # high risk meets low liquidity

# Two of the four limits are published on ctx["ips"]; the other two live in the mandate's written
# constraints, which arrive as prose rather than as numbers. Parsing a sentence for a threshold is
# how a cap silently becomes whatever a rewording leaves behind, so they are named here and printed
# on the page beside the figure they judge. Both match ctx["ips"]["constraints"] as written.
HIGH_RISK_ILLIQUID_CAP_PCT = 30.0     # high risk and low liquidity together
PRIORITY1_FLOOR_PCT = 5.0             # the minimum liquid buffer, a floor and not a cap

N_WORD = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four"}

LABELS = {
    "hni": {"eyebrow": "Risk and liquidity profile",
            "title": "The whole book, by what can go wrong and how fast you get out",
            "left": "EVERY HOLDING THE FRAMEWORK COULD PLACE, AS A SHARE OF THE BOOK",
            "right": "THE MANDATE TESTS THIS GRID DECIDES",
            "rows": ("HIGH RISK", "MEDIUM RISK", "LOW RISK"),
            "cols": ("HIGH LIQUIDITY", "MEDIUM LIQUIDITY", "LOW LIQUIDITY"),
            "corner": "IN THE HIGH RISK, LOW LIQUIDITY CELL",
            "gap": "NOT ON THIS GRID",
            "tests": ("High risk and low liquidity", "All low liquidity holdings",
                      "Priority 1 holdings", "Equity share of the book")},
    "std": {"eyebrow": "Risk and liquidity profile",
            "title": "The whole book, by what can go wrong and how fast you get out",
            "left": "EVERY HOLDING THE FRAMEWORK COULD PLACE, AS A SHARE OF THE BOOK",
            "right": "THE MANDATE TESTS THIS GRID DECIDES",
            "rows": ("HIGH RISK", "MEDIUM RISK", "LOW RISK"),
            "cols": ("HIGH LIQUIDITY", "MEDIUM LIQUIDITY", "LOW LIQUIDITY"),
            "corner": "IN THE HIGH RISK, LOW LIQUIDITY CELL",
            "gap": "NOT ON THIS GRID",
            "tests": ("High risk and low liquidity", "All low liquidity holdings",
                      "Priority 1 holdings", "Equity share of the book")},
    "simple": {"eyebrow": "How risky, and how quickly you can sell",
               "title": "Where your money sits on both questions at once",
               "left": "YOUR HOLDINGS, AS A SHARE OF EVERYTHING YOU HOLD",
               "right": "WHAT YOUR MANDATE ASKS OF THIS GRID",
               # Row labels sit in a 1.11in column and must hold ONE line at 8.5pt: the first
               # draft ran to "LEAST CAN GO WRONG", which wrapped onto the share figure below it.
               "rows": ("HIGHER RISK", "MEDIUM RISK", "LOWER RISK"),
               "cols": ("QUICK TO SELL", "SLOWER TO SELL", "SLOWEST TO SELL"),
               "corner": "HIGHER RISK AND SLOWEST TO SELL",
               "gap": "NOT ON THIS GRID",
               "tests": ("Higher risk, slowest to sell", "Everything slowest to sell",
                         "Your first source of cash", "Equity share of the book")},
}

# ---- geometry, every number chained off the house margins so nothing drifts ------------------
GX, GW = ML, 7.13                      # the grid block
LAB_W = 1.25                           # row-label column
CELL_W = (GW - LAB_W) / 3.0
Y_LABEL, Y_HEAD, Y_CELLS = 1.98, 2.24, 2.70
CELL_H = 0.90
Y_FOOT_HEAD, Y_FOOT = 5.48, 5.70
RIGHT_X = 8.30
RIGHT_W = RX - RIGHT_X
BLK_A_W = 4.25                         # the named holdings in the warning cell
BLK_B_X = GX + BLK_A_W + 0.20
BLK_B_W = GX + GW - BLK_B_X


def _rs(v):
    """A rupee figure with thousands separators. House style is Rs, never the rupee glyph."""
    return f"Rs {v:,.0f}"


def _holdings(n):
    return "1 holding" if n == 1 else f"{n} holdings"


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    as_of = ctx.get("client", {}).get("as_of", "")
    total = float(ctx.get("totals", {}).get("grand_inr") or 0)
    if total <= 0:
        return 0

    rows = []
    for key in ("funds", "equity", "other"):
        rows.extend(ctx.get(key) or [])

    # ---- place the book on the grid ----------------------------------------------------------
    cells = {(r, l): {"v": 0.0, "n": 0} for r in BANDS for l in BANDS}
    placed, corner = [], []
    gap_v, gap_n = 0.0, 0
    for h in rows:
        v = float(h.get("value_inr") or 0)
        rb, lb = h.get("risk_band"), h.get("liq_band")
        if rb in BANDS and lb in BANDS:
            cells[(rb, lb)]["v"] += v
            cells[(rb, lb)]["n"] += 1
            placed.append(h)
            if rb == "High" and lb == "Low":
                corner.append(h)
        else:
            # No band is not a low band. The value is carried and named, never folded into a cell.
            gap_v += v
            gap_n += 1
    # SELF-GATE: without the band file every holding lands here, and a 3x3 grid drawn on four
    # holdings says nothing. No page at all beats a page that invents its own axes.
    if len(placed) < 5:
        return 0

    def pct(v):
        return v / total * 100.0

    row_tot = {r: sum(cells[(r, l)]["v"] for l in BANDS) for r in BANDS}
    col_tot = {l: sum(cells[(r, l)]["v"] for r in BANDS) for l in BANDS}

    # ---- the four mandate tests, computed live -----------------------------------------------
    ips = ctx.get("ips") or {}
    hr_ll = cells[("High", "Low")]["v"]
    low_liq = col_tot["Low"]
    p1 = sum(float(h.get("value_inr") or 0) for h in rows if h.get("liq_priority") == 1)
    liq_cap = float(ips.get("locked_in_cap_pct") or 0)
    band = (ips.get("alloc_bands") or {}).get("Equity") or (0, 0, 100)
    b_lo, b_hi = float(band[0]), float(band[-1])
    eq_pct = float(ctx.get("totals", {}).get("eq_pct") or 0)

    tests = []

    # Each test carries the full sentence AND a compact clause. One breach gets the full sentence,
    # rupee figure and all. Two or more share the same box, and four full sentences do not fit it:
    # the first build of this page printed "Rs 1,095,869,547 at today's..." on a two-breach book,
    # which trails off exactly where the figure's meaning completes. The clause version drops the
    # rupee restatement instead, because the rupee figure is already in the grid and the table.
    def cap_test(i, phrase, short, held_v, cap):
        # The prose uses PHRASES, not the table's own column label. Building a sentence out of a
        # label that changes with the register is how "Everything slowest to sell are 4.6%" prints.
        p = pct(held_v)
        ok = p <= cap
        tests.append({"name": L["tests"][i], "held": f"{p:.1f}%", "limit": f"max {cap:.0f}%",
                      "status": "Inside" if ok else "Over", "ok": ok,
                      "line": (f"{phrase} are {p:.1f}% of the book, {_rs(held_v)}, against a cap "
                               f"of {cap:.0f}%."),
                      "clause": f"{short}, {p:.1f}% against a cap of {cap:.0f}%."})

    cap_test(0, "High risk and low liquidity together", "High risk and low liquidity",
             hr_ll, HIGH_RISK_ILLIQUID_CAP_PCT)
    cap_test(1, "Low liquidity holdings", "Low liquidity holdings", low_liq, liq_cap)

    p1_pct = pct(p1)
    p1_ok = p1_pct >= PRIORITY1_FLOOR_PCT
    tests.append({"name": L["tests"][2], "held": f"{p1_pct:.1f}%",
                  "limit": f"min {PRIORITY1_FLOOR_PCT:.0f}%",
                  "status": "Above" if p1_ok else "Below", "ok": p1_ok,
                  "line": (f"Priority 1 holdings, the first source of cash, are {p1_pct:.1f}% of "
                           f"the book, {_rs(p1)}, against a floor of "
                           f"{PRIORITY1_FLOOR_PCT:.0f}%, so the book carries less than the liquid "
                           f"buffer the mandate asks for."),
                  "clause": (f"Priority 1 holdings, {p1_pct:.1f}% against a floor of "
                             f"{PRIORITY1_FLOOR_PCT:.0f}%.")})

    eq_ok = b_lo <= eq_pct <= b_hi
    eq_edge = b_lo if eq_pct < b_lo else b_hi
    eq_short = abs(eq_pct - eq_edge) / 100.0 * total
    tests.append({"name": L["tests"][3], "held": f"{eq_pct:.1f}%",
                  "limit": f"{b_lo:.0f} to {b_hi:.0f}%",
                  "status": "Inside" if eq_ok else ("Below" if eq_pct < b_lo else "Above"),
                  "ok": eq_ok,
                  "line": (f"Equity is {eq_pct:.1f}% of the book against a band of {b_lo:.0f} to "
                           f"{b_hi:.0f}%, {abs(eq_pct - eq_edge):.1f} points "
                           f"{'below' if eq_pct < b_lo else 'above'} that band, "
                           f"{_rs(eq_short)} at today's values."),
                  "clause": (f"Equity, {eq_pct:.1f}% against a band of {b_lo:.0f} to "
                             f"{b_hi:.0f}%.")})

    out = [t for t in tests if not t["ok"]]
    n_ok = len(tests) - len(out)

    # ---- the page ----------------------------------------------------------------------------
    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])
    deck.anchor("mod:risk_liquidity", s, prio=4)
    deck.scope_tag(s, f"Every holding, funds and direct  ·  {len(placed)} of {len(rows)} carry "
                      f"both bands  ·  as of {as_of}")

    # ---- left: the 3x3 ------------------------------------------------------------------------
    deck.txt(s, GX, Y_LABEL, GW, 0.22, [(L["left"], SANS, 8, NAVY, True, False, 80)])

    for j, lb in enumerate(BANDS):
        cx = GX + LAB_W + j * CELL_W
        deck.txt(s, cx, Y_HEAD, CELL_W, 0.20, [(L["cols"][j], SANS, 8.5, INK, True, False, 40)],
                 align=PP_ALIGN.CENTER)
        deck.txt(s, cx, Y_HEAD + 0.20, CELL_W, 0.20,
                 [(f"{pct(col_tot[lb]):.1f}% of the book", SANS, 7.5, SLATE, False)],
                 align=PP_ALIGN.CENTER)

    for i, rb in enumerate(BANDS):
        cy = Y_CELLS + i * CELL_H
        deck.txt(s, GX, cy + CELL_H / 2 - 0.23, LAB_W - 0.14, 0.20,
                 [(L["rows"][i], SANS, 8.5, INK, True, False, 40)], align=PP_ALIGN.RIGHT)
        deck.txt(s, GX, cy + CELL_H / 2 - 0.02, LAB_W - 0.14, 0.20,
                 [(f"{pct(row_tot[rb]):.1f}% of the book", SANS, 7.5, SLATE, False)],
                 align=PP_ALIGN.RIGHT)
        for j, lb in enumerate(BANDS):
            cx = GX + LAB_W + j * CELL_W
            c = cells[(rb, lb)]
            sev = RISK_RANK[rb] + LIQ_RANK[lb]
            if c["n"] == 0:
                # An empty cell reads as empty. Tinting it would put colour where there is no money.
                deck.rect(s, cx + 0.03, cy + 0.03, CELL_W - 0.06, CELL_H - 0.06,
                          fill=WHITE, line=HAIR, lw=0.75)
                deck.txt(s, cx + 0.12, cy + CELL_H / 2 - 0.11, CELL_W - 0.24, 0.22,
                         [("Nothing held", SANS, 8, SLATE, False)],
                         align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
                continue
            deck.rect(s, cx + 0.03, cy + 0.03, CELL_W - 0.06, CELL_H - 0.06,
                      fill=SEV_FILL[sev], line=(SELL if sev == 4 else HAIR),
                      lw=(1.0 if sev == 4 else 0.75))
            deck.txt(s, cx + 0.12, cy + 0.12, CELL_W - 0.24, 0.34,
                     [(f"{pct(c['v']):.1f}%", SANS, 19, (SELL if sev == 4 else INK), False)],
                     align=PP_ALIGN.CENTER)
            deck.txt(s, cx + 0.12, cy + 0.47, CELL_W - 0.24, 0.20,
                     [(_rs(c["v"]), SANS, 8.5, INK, False)], align=PP_ALIGN.CENTER)
            deck.txt(s, cx + 0.12, cy + 0.66, CELL_W - 0.24, 0.18,
                     [(_holdings(c["n"]), SANS, 7.5, SLATE, False)], align=PP_ALIGN.CENTER)

    # ---- left foot, block A: the names an adviser is asked for first --------------------------
    deck.txt(s, GX, Y_FOOT_HEAD, BLK_A_W, 0.20, [(L["corner"], SANS, 8, NAVY, True, False, 80)])
    if corner:
        top = sorted(corner, key=lambda h: -float(h.get("value_inr") or 0))[:4]
        # 25 characters is what the name column holds at 8pt Georgia. Below that, short_name drops
        # the series marker off a fund ("Ascertis Credit SSTIF - I" becomes a different holding),
        # and the series is exactly what an adviser is asked to distinguish here.
        body = [[short_name(h.get("name", ""), 25),
                 ("b", _rs(float(h.get("value_inr") or 0))),
                 ("b", f"{pct(float(h.get('value_inr') or 0)):.1f}%")] for h in top]
        deck.table(s, GX, Y_FOOT, BLK_A_W,
                   [("Holding", 0.55, "l"), ("Value", 0.29, "r"), ("Share", 0.16, "r")],
                   body, rowh=0.215, fs=8, header=False)
    else:
        deck.txt(s, GX, Y_FOOT, BLK_A_W, 0.40,
                 [("Nothing in the book sits in that cell.", SERIF, 9, INK, False)])

    # ---- left foot, block B: what the framework could not place ------------------------------
    deck.txt(s, BLK_B_X, Y_FOOT_HEAD, BLK_B_W, 0.20, [(L["gap"], SANS, 8, NAVY, True, False, 80)])
    if gap_v > 0:
        gap_txt = (f"{_rs(gap_v)}, {pct(gap_v):.1f}% of the book, sits in {_holdings(gap_n)} the "
                   f"framework could not place. That value is absent from the grid above rather "
                   f"than counted as low risk.")
    else:
        gap_txt = "Every holding carries both bands, so nothing sits outside the grid above."
    deck.txt(s, BLK_B_X, Y_FOOT, BLK_B_W, 0.80, [(gap_txt, SERIF, 8.5, INK, False)], ls=1.04)

    # ---- right: the mandate tests -------------------------------------------------------------
    deck.txt(s, RIGHT_X, Y_LABEL, RIGHT_W, 0.22, [(L["right"], SANS, 8, NAVY, True, False, 80)])
    tbody = [[t["name"], ("b", t["held"]), ("b", t["limit"]),
              ("pill", t["status"], "Hold" if t["ok"] else "Breach")] for t in tests]
    ty = deck.table(s, RIGHT_X, Y_HEAD, RIGHT_W,
                    [("Mandate test", 0.38, "l"), ("Book", 0.17, "r"), ("Limit", 0.22, "r"),
                     ("Status", 0.23, "c")],
                    tbody, rowh=0.46, fs=8, hfs=7)

    # A breach is stated in the same voice as a pass. No hedging, no alarm.
    if out:
        note = " ".join((t["line"] if len(out) == 1 else t["clause"]) for t in out)
        if n_ok:
            note += (f" The other {N_WORD[n_ok]} test{'s' if n_ok > 1 else ''} "
                     f"{'are' if n_ok > 1 else 'is'} inside {'their' if n_ok > 1 else 'its'} "
                     f"limit{'s' if n_ok > 1 else ''}.")
        head = ("One test is outside its limit" if len(out) == 1
                else f"{N_WORD[len(out)].capitalize()} tests are outside their limits")
        kind = "warn"
    else:
        note = (f"All four tests are inside their limits. {tests[0]['line']} "
                f"{tests[1]['line']}")
        head = "Every test is inside its limit"
        kind = "good"
    # The box runs from under the table to just above the source line, and the copy is cut to
    # whole SENTENCES inside that budget rather than to a fixed line count. callout_h models
    # 10.5pt serif at this width, so the same arithmetic sizes the box and the text that fills it.
    cy = ty + 0.11
    budget = 6.55 - cy
    cpl = max(10, int((RIGHT_W - 0.44) / (0.0102 * 10.5)))
    note = clip_sentences(note, cpl * max(3, int((budget - 0.62) / 0.185)))
    nh = deck.callout_h(RIGHT_W, note, min_h=0.95, max_h=budget)
    deck.callout(s, RIGHT_X, cy, RIGHT_W, nh, head, note, kind=kind)

    deck.source(s, f"Source: every holding placed on the firm's risk and liquidity framework, as "
                   f"of {as_of}. Each cell is that share of the whole book at today's values, and "
                   f"shading deepens toward the corner where high risk meets low liquidity. "
                   f"Priority 1 is the first source of cash the framework would draw on. This "
                   f"page describes the book as it stands.")
    return 1
