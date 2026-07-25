# -*- coding: utf-8 -*-
"""Annexure B, score vs final call (F13). Real points from ctx['equity']: quant Ionic Score on x,
the final analyst call as coloured bands, overrides ringed. The anti-over-harp slide: the score
flags candidates, the human makes the call, and every disagreement is visible and documented."""
import chart_ext_b as CB
from slidekit import ML, UW, RX, HOLD, SELL, AMBER, SERIF, SLATE

LABELS = {
    "hni":    ("Score vs final call", "Where the human moved the machine"),
    "std":    ("Score vs final call", "Where the human moved the machine"),
    "simple": ("Score vs final call", "The score suggests, the analyst decides"),
}


def _band(e):
    if e["rec"] == "Sell":
        return 0
    return 1 if e.get("escalation") else 2


def _override(e):
    # firm bars (2026-07-26): a Sell on a >40 scorer IS the exceptional case (90% bar) —
    # the old >=50 cut hid HINDCOPPER (Sell at 48) and left the register empty
    if e["rec"] == "Sell" and e["ionic_score"] > 40:
        return "down"
    if e["rec"] == "Hold" and e["ionic_score"] < 40:
        return "up"
    return None


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]
    if not any(_override(e) for e in eq):
        return 0        # no overrides this review — an empty register is not a slide
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"All {len(eq)} direct equity holdings · quant score vs final analyst call · as of {as_of}")

    scores = [e["ionic_score"] for e in eq]
    bands = [_band(e) for e in eq]
    sizes = [e["value_inr"] for e in eq]
    ovr = [_override(e) for e in eq]
    labs = [e["symbol"] for e in eq]
    png = CB.score_vs_call(scores, bands, sizes, ovr, labs, "annexb_svc")
    deck.pic(s, png, ML, 1.95, 7.15, 4.35, valign="top", halign="left")
    deck.txt(s, ML, 6.32, 7.15, 0.2,
             [("Bubble = position value · gold ring = the analyst moved away from the quant read",
               SERIF, 8, SLATE, False, True)])

    # --- override register (right) ---
    tx = ML + 7.35
    tw = RX - tx
    ups = [e for e in eq if _override(e) == "up"]
    dns = [e for e in eq if _override(e) == "down"]
    cols = [("Stock", 0.34, "l"), ("Score", 0.18, "r"), ("Call", 0.26, "c"), ("Quant said", 0.22, "c")]
    rows = []
    for e in sorted(ups + dns, key=lambda x: x["ionic_score"]):
        rows.append([e["symbol"], f"{e['ionic_score']:.0f}",
                     ("pill", e["rec"], e["rec"]),
                     ("c", "Sell zone" if e["ionic_score"] < 40 else "Pass", SELL if e["ionic_score"] < 40 else HOLD, False)])
    deck.txt(s, tx, 1.86, tw, 0.22, [("WHERE ANALYSTS OVERRULED THE MODEL", "Bahnschrift", 9, AMBER, True, False, 80)])
    # every ringed point on the chart gets its register row — the table and the claim
    # must reconcile 1:1 (critique 2026-07-25); callout position follows the table end
    ty = deck.table(s, tx, 2.14, tw, cols, rows, rowh=0.26, fs=8.5, hfs=7)

    body = (f"The quant score is a screen; a verdict needs a person. On {len(ups)} names the analyst "
            f"holds a low scorer for reasons the model cannot see; on {len(dns)} the call is Sell despite "
            f"a passing score. Every override carries a written rationale, on the record.")
    deck.callout(s, tx, min(ty + 0.14, 4.75), tw, 1.75,
                 f"{len(rows)} calls moved, each documented", body, kind="human")

    deck.source(s, "Ionic quant score (0-100, PIT 2026-07-21) vs final Portfolio Review call per holding; "
                   "escalated Holds shown as Under review; overrides ringed in gold.")
    deck.score_band(s)
    return 1
