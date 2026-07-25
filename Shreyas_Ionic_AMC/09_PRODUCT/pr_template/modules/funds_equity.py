# -*- coding: utf-8 -*-
"""funds_equity (F14), equity & index schemes on Upside / Downside / Consistency.
up_capture, down_capture, asymmetry (up-down), rolling-3Y hit-rate, alpha, r² (>0.95 = closet index).
Hero = capture scatter; the 'why beating the benchmark isn't enough' callout carries the message."""
import charts as CH
from chart_lib import SELL as CC_SELL, HOLD as CC_HOLD, GOLD as CC_GOLD  # matplotlib-hex brand colors
from slidekit import NAVY, INK, SLATE, HOLD, SELL, AMBER, GOLD, SERIF, ML, UW, RX

VDISP = {"Redeem-to-Direct": "To-Direct"}
VCOL = {"Hold": HOLD, "Switch": GOLD, "Trim": AMBER, "Exit": SELL, "Redeem-to-Direct": AMBER}

LABELS = {
    "hni":    ("Equity funds, upside, downside, consistency",
               "Why beating the benchmark isn't the same as adding value"),
    "std":    ("Equity funds, upside, downside, consistency",
               "How much of the rally each fund catches, and how much of the fall it gives back"),
    "simple": ("Equity funds, up and down",
               "Beating the market isn't enough on its own"),
}


def _short(name, n=16):
    name = name.replace(" Fund", "").replace(" (Regular)", "").replace(" (Direct)", "")
    return name if len(name) <= n else name[:n - 1] + "…"


def _ccol(f):
    a = f["action"]
    if a == "EXIT":
        return CC_SELL
    if a == "HOLD":
        return CC_HOLD
    return CC_GOLD


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    simple = reg == "simple"
    as_of = ctx["client"]["as_of"]
    efunds = [f for f in ctx["funds"] if f["category"] in ("equity", "passive")]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    s = deck.content(3, "Funds", eyebrow, title)
    deck.scope_tag(s, f"MF sleeve only, equity & index schemes · Direct-plan NAV vs TR benchmark · as of {as_of}")

    # funds that give back more than they capture (down-capture > up-capture)
    below = sorted([f for f in efunds if (f["up_capture"] - f["down_capture"]) < 0],
                   key=lambda f: f["up_capture"] - f["down_capture"])
    n_below = len(below)
    below_names = ", ".join(_short(f["name"], 20) for f in below[:2]) or "none of these"

    if simple:
        cols = [("Scheme", 0.40, "l"), ("Catches up-moves", 0.19, "r"),
                ("Gives back on falls", 0.21, "r"), ("Suggested", 0.24, "c")]
        rows = [[_short(f["name"], 26), f"{f['up_capture']:.0f}%", f"{f['down_capture']:.0f}%",
                 ("pill", VDISP.get(f["verdict"], f["verdict"]), f["verdict"])] for f in efunds]
        deck.table(s, ML, 2.0, UW, cols, rows, rowh=0.42, fs=11, hfs=9)
        body = (f"A fund can beat the market and still take more risk to do it. We want funds that catch "
                f"most of the up-moves but give back less when the market falls. {n_below} of these funds "
                f"drop more than the market does, {below_names}.")
        deck.callout(s, ML, 4.95, UW, 1.3, "Beating the market isn't enough", body, kind="warn")
        deck.source(s, "Up / down capture vs total-return benchmark; Direct-plan NAV. Illustrative synthetic funds.")
        return 1

    # --- hero scatter (left) ---
    up = [f["up_capture"] for f in efunds]
    dn = [f["down_capture"] for f in efunds]
    wt = [f["value_inr"] for f in efunds]
    colr = [_ccol(f) for f in efunds]
    labs = [_short(f["name"], 14) for f in efunds]
    png = CH.capture_scatter(up, dn, wt, colr, labs, "fe_capture")
    deck.pic(s, png, ML, 1.95, 6.6, 4.30, valign="top")
    deck.txt(s, ML, 6.28, 6.6, 0.2,
             [("Bubble = position value · shaded corner catches the upside, spares the downside",
               SERIF, 8, SLATE, False, True)])

    # --- consistency table (right) ---
    tx = 7.75
    tw = RX - tx
    cols = [("Scheme", 0.30, "l"), ("Asym", 0.14, "r"), ("3Y hit", 0.14, "r"),
            ("α p.a.", 0.14, "r"), ("r²", 0.12, "r"), ("Verdict", 0.18, "c")]
    rows = []
    for f in efunds:
        asym = f["up_capture"] - f["down_capture"]
        r2 = f["r2"]
        r2cell = ("c", f"{r2:.2f}", SELL, True) if r2 > 0.95 else f"{r2:.2f}"
        rows.append([_short(f["name"], 15),
                     ("c", f"{asym:+.0f}", HOLD if asym >= 0 else SELL, True),
                     f"{f['hit3y']:.0f}%",
                     ("c", f"{f['alpha_ann']:+.1f}", HOLD if f["alpha_ann"] >= 0 else SELL, True),
                     r2cell,
                     ("c", VDISP.get(f["verdict"], f["verdict"]), VCOL.get(f["verdict"], INK), True)])
    deck.table(s, tx, 1.95, tw, cols, rows, rowh=0.34, fs=8, hfs=7)

    # --- callout (right, below table) ---
    body = (f"Alpha alone hides how it was earned. The scatter plots upside capture against downside "
            f"capture; funds in the shaded corner catch the rally and spare the fall. {below_names} sit "
            f"below the symmetric line, they give back more than the market when it drops, so their "
            f"outperformance is bought with extra downside risk. r² above 0.95 = a closet index paying "
            f"active fees for beta.")
    deck.callout(s, tx, 4.45, tw, 1.85, "Why beating the benchmark isn't enough", body, kind="note")

    deck.source(s, "Up / down capture, rolling-3Y hit-rate, annualised alpha & r² vs total-return "
                   "benchmark; Direct-plan NAV. r² > 0.95 = closet-index. Illustrative synthetic funds.")
    return 1
