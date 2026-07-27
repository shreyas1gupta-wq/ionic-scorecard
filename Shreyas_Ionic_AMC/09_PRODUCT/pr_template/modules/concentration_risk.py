# -*- coding: utf-8 -*-
"""concentration_risk, top-10 holdings treemap; flag names above the IPS single-name cap."""
from slidekit import (NAVY, GOLD, INK, SLATE, SELL, SANS, SERIF, ML, UW, RX)
import charts as CH

CNAVY, CNT1, CNT2, CNT3, CSELL = "#1B27A3", "#4A57C4", "#8C95DE", "#C9CEF0", "#E0402F"
_RAMP = [CNAVY, CNT1, CNT2, CNT3]

LABELS = {
    "hni":    {"eyebrow": "Concentration risk",
               "title": "Single-name concentration against the IPS cap"},
    "std":    {"eyebrow": "Concentration risk",
               "title": "Your ten largest positions, and where they breach the cap"},
    "simple": {"eyebrow": "Too much in too few names",
               "title": "Your ten biggest holdings"},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    eq = ctx["equity"]; cap = ctx["ips"]["single_name_cap_pct"]; as_of = ctx["client"]["as_of"]
    t = ctx["totals"]

    top = sorted(eq, key=lambda e: e["weight_pct"], reverse=True)[:10]
    breaches = [e for e in top if e["weight_pct"] > cap]
    top2 = sum(e["weight_pct"] for e in top[:2])

    s = deck.content(1, "Portfolio X-ray", L["eyebrow"], L["title"])
    deck.anchor("mod:concentration", s, prio=5)
    deck.scope_tag(s, f"Direct equity only · as of {as_of}")

    # ---- treemap (left) ----
    labels = [e["symbol"] for e in top]
    sizes = [e["weight_pct"] for e in top]
    vlab = [f"{e['weight_pct']:.1f}%" for e in top]
    colors = [CSELL if e["weight_pct"] > cap else _RAMP[i % 4] for i, e in enumerate(top)]
    tpath = CH.treemap(labels, sizes, "azby_conc_tree", colors=colors, value_labels=vlab)
    deck.pic(s, tpath, ML, 2.05, 7.55, 3.15, valign="top", halign="left")

    # ---- breach callout (right) ----
    cx = ML + 7.8; cw = RX - cx
    if breaches:
        names = ", ".join(f"{e['symbol']} ({e['weight_pct']:.1f}%)" for e in breaches[:2])
        extra = f" and {len(breaches)-2} more" if len(breaches) > 2 else ""
        comb = sum(e["weight_pct"] for e in breaches)
        # call-aware treatment line: a breach that is also a Sell EXITS, it doesn't trim
        sell_b = [e["symbol"] for e in breaches if e["rec"] == "Sell"]
        hold_b = [e["symbol"] for e in breaches if e["rec"] != "Sell"]
        if reg == "simple":
            body = (f"{len(breaches)} shares are bigger than our {cap:.0f}% single-name limit: "
                    f"{names}{extra}. ")
            if sell_b:
                body += f"{', '.join(sell_b)} is on the sell list anyway. "
            if hold_b:
                body += f"{', '.join(hold_b)} we reduce slowly toward {cap:.0f}%."
        else:
            body = (f"{len(breaches)} names sit above the {cap:.0f}% IPS single-name guideline: "
                    f"{names}{extra}, together {comb:.1f}% of the book. ")
            if sell_b:
                body += f"{', '.join(sell_b)} exits via the sell programme. "
            if hold_b:
                body += (f"{', '.join(hold_b)} is trimmed toward {cap:.0f}% into strength, "
                         f"sliced across days, never in one print.")
        deck.callout(s, cx, 2.05, cw, deck.callout_h(cw, body, min_h=1.7, max_h=3.15),
                     "SINGLE-NAME CAP", body, kind="warn")
    else:
        deck.callout(s, cx, 2.05, cw, 3.15, "SINGLE-NAME CAP",
                     f"No position exceeds the {cap:.0f}% IPS single-name guideline. Concentration is "
                     "within policy; monitor on drift.", kind="good")

    # ---- concentration KPIs ----
    deck.kpi_strip(s, [
        (f"{top2:.1f}%", "Top 2 names"),
        (f"{t['top10_pct']:.0f}%", "Top 10 names"),
        (f"{cap:.0f}%", "Our single-stock limit" if reg == "simple" else "IPS single-name cap"),
        (str(len(breaches)), "Names over the cap", None, (SELL if breaches else INK)),
    ], y=5.55)

    ips_note = ("IPS single-name guideline per the Investment Policy Statement."
                if ctx["ips"].get("on_file", True) else
                "Single-name guideline per house risk policy — no client-specific IPS on file yet.")
    deck.source(s, f"Source: client holdings as of {as_of}. Weights as % of total AUM; {ips_note}")
    return 1
