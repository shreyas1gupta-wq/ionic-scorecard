# -*- coding: utf-8 -*-
"""Annexure, Sell rationale cards (F3): one slide per rec=='Sell' name. Score + why-out
(negative_para) + the bull we rejected (positive_para) + reverse-DCF + what-would-change-our-mind
(reversal) + PIT stamp. Returns the count of cards added."""
from slidekit import (INK, SLATE, NAVY, SELL, SANS, SERIF, ML, UW, RX)


_REVERSAL = {
    "Forensic / governance flag":
        "A clean forensic re-audit · related-party / pledge / governance concerns resolved and two "
        "consecutive clean reporting cycles.",
    "Balance-sheet strain":
        "Genuine deleveraging · interest cover back above our comfort level and net-debt/EBITDA "
        "normalising toward peers.",
    "Rich valuation, thin margin of safety":
        "A valuation reset (through time or price) that restores a real margin of safety at our "
        "reverse-DCF hurdle.",
    "Quality below peers":
        "A durable step-up in ROE / margins back to peer level, sustained over several quarters.",
    "Slowing growth":
        "Re-acceleration in revenue and earnings for two consecutive quarters, not a one-off beat.",
    "Weaker forward risk-reward":
        "A better forward risk/reward · a cheaper entry or a clear fundamental inflection.",
}


def _clip(txt, n=340):
    txt = (txt or "").strip()
    if not txt:
        return "On file with the analyst desk."
    return txt if len(txt) <= n else txt[:n - 1].rsplit(" ", 1)[0] + "…"


def _reversal(e):
    return _REVERSAL.get(e.get("reason_category"), _REVERSAL["Weaker forward risk-reward"])


def _card(deck, e, tier):
    reg = tier.get("register", "std")
    reason = e.get("reason_category") or "Weaker forward risk-reward"
    s = deck.content(5, "Annexure", "Sell rationale", f"{e['name']}  ·  {reason}")
    deck.anchor(f"stock:{e['symbol']}", s, prio=2)

    # --- score strip ---
    deck.txt(s, ML, 1.74, 2.0, 0.2, [("IONIC SCORE", SANS, 8.5, SLATE, True, False, 140)])
    deck.txt(s, ML, 1.95, 1.3, 0.4, [(f"{e['ionic_score']:.0f}", SANS, 24, INK, False)])
    deck.score_bar(s, ML + 1.35, 2.06, e["ionic_score"], w=1.9)
    deck.txt(s, ML + 3.7, 1.95, 3.0, 0.3,
             [(f"3Y {e['score_3y']:.0f}  ·  1Y {e['score_1y']:.0f}  ·  {e['weight_pct']:.2f}% of book",
               SANS, 10, SLATE, False)])
    deck.pill(s, RX - 1.4, 1.9, "Sell", w=1.4, kind="Sell")

    # --- 2x2 rationale grid ---
    colw = (UW - 0.3) / 2
    x2 = ML + colw + 0.3
    y1, y2, h = 2.5, 4.5, 1.9
    deck.callout(s, ML, y1, colw, h, "Why it's on the sell list", _clip(e.get("negative")), "warn")
    deck.callout(s, x2, y1, colw, h, "The bull we rejected", _clip(e.get("positive")), "note")
    deck.callout(s, ML, y2, colw, h, "Reverse-DCF: margin of safety", _clip(e.get("reverse_dcf")), "note")
    deck.callout(s, x2, y2, colw, h, "What would change our mind", _clip(_reversal(e)), "human")

    deck.pageref(s, RX - 2.7, 6.42, "tbl:sell_list", w=2.7, label="BACK TO THE SELL LIST")
    deck.score_band(s)
    deck.source(s, f"Analyst-confirmed Sell. Point-in-time as of {e['pit_date']}. "
                   f"The Ionic Score flags candidates; the team confirms every call.")


def render(deck, ctx, tier):
    sells = [e for e in ctx["equity"] if e["rec"] == "Sell"]
    for e in sells:
        _card(deck, e, tier)
    return len(sells)
