# -*- coding: utf-8 -*-
"""Annexure, Spotlight holdings: one slide each for the top-N positions (N = tier['spotlight_count']),
business line + Ionic Score + analyst read + the call. Returns the number of slides added
(v8 #14/#15, de-hardcoded)."""
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from slidekit import (INK, SLATE, NAVY, GOLD, HOLD, SELL, PANEL, HAIR, SERIF, SANS, ML, UW, RX,
                      clip_sentences)


def _one(deck, e, tier):
    reg = tier.get("register", "std")
    s = deck.content(5, "Annexure", "Spotlight",
                     f"{e['name']}  ·  {e['sector']}  ·  {e['weight_pct']:.1f}% of the book")
    deck.anchor(f"stock:{e['symbol']}", s, prio=1)

    # --- left: score panel ---
    px, py, pw, ph = ML, 1.95, 3.5, 3.7
    deck.rect(s, px, py, pw, ph, fill=PANEL, line=HAIR, round_=0.03)
    deck.txt(s, px + 0.25, py + 0.22, pw - 0.5, 0.22, [("IONIC SCORE", SANS, 8.5, SLATE, True, False, 140)])
    _sc = e.get("ionic_score")
    _sc_txt = f"{_sc:.0f}" if _sc is not None else "-"
    _s3 = e.get("score_3y")
    _s1 = e.get("score_1y")
    _sub = f"3Y {_s3:.0f}   ·   1Y {_s1:.0f}" if _s3 is not None and _s1 is not None else "Pending scoring"
    deck.txt(s, px + 0.22, py + 0.44, pw - 0.5, 0.8, [(_sc_txt, SANS, 52, INK, False)])
    deck.score_bar(s, px + 0.28, py + 1.42, _sc, w=2.3)
    deck.txt(s, px + 0.25, py + 1.72, pw - 0.5, 0.22,
             [(_sub, SANS, 10, SLATE, False)])
    deck.pill(s, px + 0.25, py + 2.15, e["rec"], w=1.3, kind=e["rec"])
    deck.txt(s, px + 0.25, py + 2.6, pw - 0.5, 0.7,
             [(f"{e['mcap_band']}-cap   ·   {e['conviction']}", SANS, 9.5, SLATE, False)])

    # --- right: read + the call (the verdict lives in the pill + one call box; a third
    # and fourth restatement of HOLD read as templated filler — cut, declutter 2026-07-25) ---
    rx = ML + 3.75
    rw = RX - rx
    # client_case/detailed are the scrubbed client-safe text (2026-07-27 sweep); summary
    # carries the raw internal audit trail (pf_qual/analyst-name citations) and must never
    # be shown to a client directly, so it's the last resort, not the first.
    read = clip_sentences((e.get("client_case") or e.get("detailed") or e.get("analyst_read")
                            or e.get("summary") or "").strip(), 480)
    deck.callout(s, rx, py, rw, 2.44, "Our read", read or "Analyst read on file.", "note")

    call = f"{e['rec']}"
    if e["rec"] == "Hold":
        call_body = f"Keep the position ({e['conviction']} conviction). "
    elif e["rec"] == "Trim":
        call_body = "Reduce toward target; the thesis is intact but the risk/reward is only fair. "
    else:
        call_body = "Exit, the forward risk/reward no longer justifies the position. "
    if e.get("reason_category"):
        call_body += f"Driver: {e['reason_category']}."
    deck.callout(s, rx, py + 2.6, rw, 1.1, f"The call, {call}", call_body, "human")

    deck.pageref(s, RX - 2.4, 6.42, "tbl:book", w=2.4, label="BACK TO THE BOOK")
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
