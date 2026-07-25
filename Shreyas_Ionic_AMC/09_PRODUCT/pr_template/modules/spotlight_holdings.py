# -*- coding: utf-8 -*-
"""Annexure, Spotlight holdings: one slide each for the top-N positions (N = tier['spotlight_count']),
business line + Ionic Score + analyst read + the call. Returns the number of slides added
(v8 #14/#15, de-hardcoded)."""
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from slidekit import (INK, SLATE, NAVY, GOLD, HOLD, SELL, PANEL, HAIR, SERIF, SANS, ML, UW, RX)


def _sent2(txt, fallback=""):
    txt = (txt or "").strip() or (fallback or "").strip()
    parts = [p.strip() for p in txt.replace("\n", " ").split(". ") if p.strip()]
    out = ". ".join(parts[:2]).strip()
    if out and not out.endswith("."):
        out += "."
    return out


def _human_read(e, reg):
    sc = e["ionic_score"]
    rec = e["rec"]
    if rec == "Sell":
        return f"Score {sc:.0f} sits below our line, a sell candidate the team has confirmed."
    if rec == "Trim":
        return f"Score {sc:.0f} is middling, we would trim rather than exit."
    if reg == "simple":
        return f"Score {sc:.0f} clears our bar, we are happy to keep it."
    return f"Score {sc:.0f} clears our bar, the read supports holding."


def _one(deck, e, tier):
    reg = tier.get("register", "std")
    s = deck.content(5, "Annexure", "Spotlight",
                     f"{e['name']}  ·  {e['sector']}  ·  {e['weight_pct']:.1f}% of the book")

    # --- left: score panel ---
    px, py, pw, ph = ML, 1.95, 3.5, 3.7
    deck.rect(s, px, py, pw, ph, fill=PANEL, line=HAIR, round_=0.03)
    deck.txt(s, px + 0.25, py + 0.22, pw - 0.5, 0.22, [("IONIC SCORE", SANS, 8.5, SLATE, True, False, 140)])
    deck.txt(s, px + 0.22, py + 0.44, pw - 0.5, 0.8, [(f"{e['ionic_score']:.0f}", SANS, 52, INK, False)])
    deck.score_bar(s, px + 0.28, py + 1.42, e["ionic_score"], w=2.3)
    deck.txt(s, px + 0.25, py + 1.72, pw - 0.5, 0.22,
             [(f"3Y {e['score_3y']:.0f}   ·   1Y {e['score_1y']:.0f}", SANS, 10, SLATE, False)])
    deck.pill(s, px + 0.25, py + 2.15, e["rec"], w=1.3, kind=e["rec"])
    deck.txt(s, px + 0.25, py + 2.6, pw - 0.5, 0.7,
             [(f"{e['mcap_band']}-cap   ·   {e['conviction']}", SANS, 9.5, SLATE, False)])

    # --- right: read + the call ---
    rx = ML + 3.75
    rw = RX - rx
    deck.txt(s, rx, py, rw, 0.24, [(_human_read(e, reg), SERIF, 11, NAVY, False, True)], ls=1.05)
    read = _sent2(e.get("summary"), e.get("detailed") or e.get("analyst_read"))
    deck.callout(s, rx, py + 0.42, rw, 2.0, "Our read", read or "Analyst read on file.", "note")

    call = f"{e['rec']}"
    if e["rec"] == "Hold":
        call_body = f"Keep the position ({e['conviction']}). "
    elif e["rec"] == "Trim":
        call_body = "Reduce toward target; the thesis is intact but the risk/reward is only fair. "
    else:
        call_body = "Exit, the forward risk/reward no longer justifies the position. "
    if e.get("reason_category"):
        call_body += f"Driver: {e['reason_category']}."
    deck.callout(s, rx, py + 2.6, rw, 1.1, f"The call, {call}", call_body, "human")

    deck.score_band(s)
    deck.source(s, f"Ionic Score is a quantitative input; the Portfolio Review team confirms every call. "
                   f"Point-in-time as of {e['pit_date']}.")


def render(deck, ctx, tier):
    n = int(tier.get("spotlight_count", 0) or 0)
    if n <= 0:
        return 0
    eq = sorted(ctx["equity"], key=lambda e: -e["weight_pct"])[:n]
    for e in eq:
        _one(deck, e, tier)
    return len(eq)
