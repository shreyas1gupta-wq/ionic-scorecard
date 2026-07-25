# -*- coding: utf-8 -*-
"""funds_hybrid (F15), hybrid schemes on risk-adjusted return, drawdown and the worst year.
Per fund: Sortino, Calmar, max drawdown (as a number in the table), worst 1-yr rolling return
(the headline), down-capture (is it actually cushioning?).

Principal correction 2026-07-25: the drawdown-from-peak chart is removed (not required). The freed
space carries a per-fund BIAS COMMENTARY block, 2-3 sentences per hybrid on why each verdict
stands, built from verdict/flags/structural_reason/worst_1y/down_capture. rolling_return_band was
dropped with it: three commentary cards plus the metric table fill the slide and the chart
crowded it. The _synth_nav reconstruction is gone with the charts.
"""
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, SERIF, SANS, ML, UW

VDISP = {"Redeem-to-Direct": "To-Direct"}
_ORDER = {"Exit": 0, "Switch": 1, "Trim": 2, "Redeem-to-Direct": 3, "Hold": 4}
_KIND = {"Hold": "good", "Trim": "warn", "Exit": "warn", "Switch": "warn", "Redeem-to-Direct": "human"}
_FLAG_READ = {"DOWN_CAP_HI": "high down-capture", "DEEP_DD": "deep drawdown",
              "REG_PLAN_DRAG": "Regular-plan cost drag", "CLOSET_INDEX": "closet indexing",
              "NEG_ALPHA": "negative net alpha", "WEAK_CONSIST": "weak 3-yr consistency",
              "MANDATE_RIGIDITY": "mandate rigidity", "CAPACITY": "capacity strain",
              "OVER_ALLOC": "over-allocation", "SUB_SCALE": "sub-scale AUM",
              "SHORT_RECORD": "record under 4 years"}


def _short(name, n=28):
    """Fund-name shortener that never cuts mid-word: strip suffixes first, then
    drop trailing words until it fits (a clean shorter name beats a broken one)."""
    name = name.replace(" Fund", "").replace(" (Regular)", " (Reg)").replace(" (Direct)", " (Dir)")
    if len(name) <= n:
        return name
    words = name.split(" ")
    while len(words) > 2 and len(" ".join(words)) > n:
        words.pop()
    out = " ".join(words)
    return out if len(out) <= n else out[:n - 1].rsplit(" ", 1)[0]


def _scrub(t):
    """House style: no em-dashes in client-facing strings, even when the data carries them."""
    return (t or "").replace(", ", ", ").replace(", ", ", ").strip()


def _sort_col(v):
    return HOLD if v >= 1 else (SELL if v < 0 else INK)


def _bias_body(f, simple):
    """2-3 sentences of Sell/Hold bias reasoning per hybrid, from ctx fields."""
    w1, dc, so = f["worst_1y"], f["down_capture"], f["sortino"]
    v = f["verdict"]
    sr = _scrub(f.get("structural_reason"))
    flags = [_FLAG_READ.get(x, x.lower().replace("_", " ")) for x in (f.get("flags") or [])]
    # scale/record Trims are consolidation calls — never dressed as a cushioning failure
    structural_trim = bool({"SHORT_RECORD", "SUB_SCALE"} & set(f.get("flags") or []))
    if simple:
        if v == "Hold":
            worst_read = (f"In its worst year it still made {w1:+.0f}%" if w1 >= 0
                          else f"In its worst year it lost only {abs(w1):.0f}%")
            return (f"Keep. {worst_read}, and it falls only {dc:.0f}% as "
                    f"much as the market. This is what a hybrid is for.")
        if v == "Trim":
            if structural_trim:
                return ("Reduce, gently. Nothing is wrong with how it has done so far; it is simply "
                        "a young fund with a small asset base, so we lean on the bigger, proven "
                        "fund until this one has a longer record.")
            return (f"Reduce. It lost {abs(w1):.0f}% in its worst year and falls about as much as the "
                    f"market itself, so it is not protecting you.")
        if v == "Redeem-to-Direct":
            return ("Keep the fund, change the plan. The same fund is cheaper in its Direct version; "
                    "the Regular version pays a yearly commission you do not need to pay.")
        return (f"Our suggestion is {v}. Worst year {w1:+.0f}%, and it falls {dc:.0f}% as much as "
                f"the market.")
    if v == "Hold":
        # no per-card "book's benchmark" claim — with two hybrid Holds it printed twice
        return (f"Stays a Hold. A {w1:+.1f}% worst year at {dc:.0f}% down-capture (Sortino {so:.2f}) "
                f"means it gives up some upside and buys back the bad year, which is exactly the trade "
                f"a hybrid is hired for.")
    if v == "Trim":
        if structural_trim:
            return (f"Our bias is Trim, on scale and record, not results. Under four years old, "
                    f"sub-scale, {dc:.0f}% down-capture so far is fine; it cannot yet carry a full "
                    f"allocation next to the proven core.")
        s = (f"Our bias is Trim. Down-capture of {dc:.0f}% with a {w1:+.1f}% worst year means it falls "
             f"like pure equity while charging for protection; Sortino at {so:.2f} says holders were "
             f"not paid for that downside.")
        if flags:
            s += f" Flags firing: {', '.join(flags)}."
        return s + " We would cut the allocation, not the asset class."
    if v == "Redeem-to-Direct":
        s = (f"To-Direct, not a quality call. The fund passes the bad-year test: {w1:+.1f}% worst year, "
             f"{dc:.0f}% down-capture, Sortino {so:.2f}.")
        if sr:
            s += f" {sr}"
        return s + " We keep the exposure and change the plan."
    s = f"Our bias is {v}. Worst year {w1:+.1f}% at {dc:.0f}% down-capture, Sortino {so:.2f}."
    if sr:
        s += f" {sr}"
    if flags:
        s += f" Flags firing: {', '.join(flags)}."
    return s


def _bias_cards(deck, s, funds, y, h, simple):
    gap = 0.15
    cw = (UW - gap * (len(funds) - 1)) / max(len(funds), 1)
    for i, f in enumerate(funds):
        title = f"{_short(f['name'], 26)} · {VDISP.get(f['verdict'], f['verdict'])}"
        deck.callout(s, ML + i * (cw + gap), y, cw, h, title,
                     _bias_body(f, simple), kind=_KIND.get(f["verdict"], "note"))


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    hyb = [f for f in ctx["funds"] if f["category"] == "hybrid"]
    worst = min(hyb, key=lambda f: f["worst_1y"])
    best = max(hyb, key=lambda f: f["worst_1y"])
    as_of = ctx["client"]["as_of"]

    # cards: problems first, the fix second, the benchmark Hold last; cap at 3
    cards = sorted(hyb, key=lambda f: (_ORDER.get(f["verdict"], 2), f["worst_1y"]))[:3]

    if simple:
        eyebrow, title = "Hybrid funds · the bad-year test", "A hybrid should protect you when markets fall"
    else:
        eyebrow = "Hybrid funds · return-for-risk, drawdown, worst year"
        title = "A hybrid earns its keep in the bad year, not the good one"
    s = deck.content(3, "Funds", eyebrow, title)
    deck.scope_tag(s, f"MF sleeve only: hybrid schemes · Direct-plan NAV vs TR benchmark · as of {as_of}")

    if simple:
        cols = [("Scheme", 0.40, "l"), ("Worst 1-yr", 0.20, "r"),
                ("Falls vs market", 0.18, "r"), ("Suggested", 0.22, "c")]
        rows = []
        for f in hyb:
            rows.append([_short(f["name"], 26),
                         ("c", f"{f['worst_1y']:+.0f}%", SELL if f["worst_1y"] < 0 else HOLD, True),
                         ("c", f"{f['down_capture']:.0f}%", SELL if f["down_capture"] >= 90 else HOLD, True),
                         ("pill", VDISP.get(f["verdict"], f["verdict"]), f["verdict"])])
        ty = deck.table(s, ML, 2.05, UW, cols, rows, rowh=0.5, fs=11, hfs=9)
        cy = ty + 0.22
        _bias_cards(deck, s, cards, cy, min(2.2, 6.45 - cy), True)
        deck.source(s, "Worst 1-yr rolling return and down-capture vs total-return benchmark; Direct-plan NAV. "
                       "Illustrative synthetic funds.")
        return 1

    # --- metrics table (all hybrids); max drawdown stays a number, per the Principal ---
    cols = [("Scheme", 0.24, "l"), ("Sortino", 0.11, "r"), ("Calmar", 0.11, "r"),
            ("Max DD", 0.12, "r"), ("Worst 1-yr", 0.13, "r"), ("Down-cap", 0.13, "r"), ("Verdict", 0.16, "c")]
    rows = []
    for f in hyb:
        dd = f["max_dd"]
        w1 = f["worst_1y"]
        dc = f["down_capture"]
        rows.append([_short(f["name"]),
                     ("c", f"{f['sortino']:.2f}", _sort_col(f["sortino"]), True),
                     ("c", f"{f['calmar']:.2f}", _sort_col(f["calmar"]), True),
                     ("c", f"{dd:.1f}%", SELL if dd <= -20 else (AMBER if dd <= -12 else INK), True),
                     ("c", f"{w1:+.1f}%", SELL if w1 < 0 else HOLD, True),
                     ("c", f"{dc:.0f}%", SELL if dc >= 90 else (HOLD if dc < 75 else AMBER), True),
                     ("pill", VDISP.get(f["verdict"], f["verdict"]), f["verdict"])])
    ty = deck.table(s, ML, 1.9, UW, cols, rows, rowh=0.34, fs=9.5, hfs=8)

    # --- per-fund bias commentary (replaces the removed drawdown / rolling-band zoom) ---
    hy = ty + 0.12
    deck.txt(s, ML, hy, UW, 0.2,
             [("OUR BIAS, FUND BY FUND   ", SANS, 8.5, NAVY, True, False, 60),
              ("why each verdict stands", SERIF, 9, SLATE, False, True)])
    cy = hy + 0.30
    # cards sized to their text, not to the void — a half-empty tinted box reads as filler
    chh = min(1.95, 6.30 - cy)
    _bias_cards(deck, s, cards, cy, chh, False)

    deck.source(s, "Sortino / Calmar, max drawdown, worst 1-yr rolling return & down-capture vs "
                   "total-return benchmark; Direct-plan NAV. Illustrative synthetic funds.")
    return 1
