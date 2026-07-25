# -*- coding: utf-8 -*-
"""since_last_review (personalization block 4, Principal 2026-07-26): what we agreed at
the last review and where each action stands. Renders ONLY when the client profile
carries meeting history (ctx['client']['meeting_history']) — a first review or the
demo book gets no slide. Expected shape:
  meeting_history = [                        # newest first
    {"date": "2026-04-28", "summary": "one-paragraph note of what was discussed",
     "actions": [{"action": "Exit PGIM Small Cap", "owner": "Client",
                  "status": "Done" | "In progress" | "Pending", "note": "optional"}]},
    ...]
"""
from slidekit import (INK, SLATE, NAVY, GOLD, HOLD, SELL, AMBER, PANEL, HAIR,
                      SERIF, SANS, ML, UW, RX, clip_sentences)

SECTION_NO, SECTION = 0, "Understanding"

_STATUS_KIND = {"Done": "Hold", "In progress": "Trim", "Pending": "Sell"}

LABELS = {
    "hni": ("Since our last review", "What we agreed, and where each action stands"),
    "std": ("Since our last review", "What we agreed, and where each action stands"),
    "simple": ("Since we last met", "What we agreed to do, and what has happened"),
}


def render(deck, ctx, tier):
    hist = (ctx.get("client") or {}).get("meeting_history") or []
    if not hist:
        return 0                      # first review / no history on file — no slide
    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    last = hist[0]

    s = deck.content(SECTION_NO, SECTION, eyebrow, title)
    deck.scope_tag(s, f"Last review {last.get('date', '-')} · "
                      f"{len(hist)} review(s) on file · as of {ctx['client']['as_of']}")

    # left: what was discussed
    lw = (UW - 0.3) * 0.42
    body = clip_sentences((last.get("summary") or "").strip(), 520) or "Meeting note on file."
    deck.callout(s, ML, 2.0, lw, deck.callout_h(lw, body, min_h=1.8, max_h=4.2),
                 "What we discussed", body, "note")

    # right: agreed actions with status
    rx = ML + lw + 0.3
    rw = RX - rx
    acts = (last.get("actions") or [])[:8]
    if acts:
        cols = [("Agreed action", 0.52, "l"), ("Owner", 0.16, "l"), ("Status", 0.32, "c")]
        rows = [[a.get("action", "-"), a.get("owner", "-"),
                 ("pill", a.get("status", "Pending"), _STATUS_KIND.get(a.get("status"), "Trim"))]
                for a in acts]
        deck.txt(s, rx, 1.72, rw, 0.24, [("AGREED LAST TIME", SANS, 8, SLATE, True, False, 80)])
        deck.table(s, rx, 2.0, rw, cols, rows, rowh=0.42, fs=9.5, hfs=8)
    done = sum(1 for a in acts if a.get("status") == "Done")
    if acts:
        note = (f"{done} of {len(acts)} agreed actions are complete. Open items roll into "
                f"this review's action list." if reg != "simple" else
                f"{done} of {len(acts)} things we agreed are done. The rest carry into this plan.")
        y = 2.0 + 0.33 + len(acts) * 0.42 + 0.2
        deck.txt(s, rx, y, rw, 0.5, [(note, SERIF, 9.5, INK, False, True)], ls=1.05)

    deck.source(s, "Meeting history from the client file; action status as reported by the "
                   "relationship manager at preparation date.")
    return 1
