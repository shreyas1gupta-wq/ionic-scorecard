# -*- coding: utf-8 -*-
"""sell_list (F3), the names we would sell.
Table of the rec=='Sell' holdings: Name | Wt | Score-bar | Action | Reason category | binding
trigger, ordered so actionable Sells lead and forensic / balance-sheet-gate reasons rank above
valuation / trend ones. A fixed reason-taxonomy legend sits beneath. score_band + scope_tag attach.

FROZEN-METHODOLOGY rule (2026-07-25): escalated names (equity 'escalation'==True) may NOT carry an
actionable Sell in a client deck until the Principal rules. They stay in the table with score and
reason, their action pill renders 'Under review' (Watch), a footnote states the committee status,
and the lead-in counts N actionable + M under review. This module carries no proceeds phrasing;
proceeds numbers come from ctx['deployment'] in other modules.
"""
from slidekit import NAVY, INK, SLATE, SELL, AMBER, SERIF, SANS, ML, UW
from pptx.enum.text import MSO_ANCHOR

# ctx reason_category -> (rank, short client-facing label). Lower rank = ranks higher (shown first).
TAXONOMY = {
    "Forensic / governance flag":            (1, "Forensic / governance"),
    "Balance-sheet strain":                  (2, "Balance-sheet gate"),
    "Quality below peers":                   (3, "Quality below peers"),
    "Slowing growth":                        (4, "Weak long-term growth"),
    "Rich valuation, thin margin of safety": (5, "Rich valuation"),
    "Weaker forward risk-reward":            (6, "Weak forward risk-reward"),
}
# the fixed legend, in rank order (gate/forensic first)
LEGEND = [
    ("Forensic / governance", "Accounting, disclosure or governance red flag; ranks first."),
    ("Balance-sheet gate", "Debt or interest-cover breach caps the score at 40."),
    ("Quality below peers", "Returns on capital lag the sector."),
    ("Weak long-term growth", "Forward 3-5yr growth too thin to justify holding."),
    ("Rich valuation", "Price already prices in more than we can underwrite."),
    ("Weak forward risk-reward", "Trend and flow no longer pay for the risk."),
]

LABELS = {
    "hni":    {"title": "The names we would sell · reason, then trigger",
               "lead": "Forensic and balance-sheet-gate reasons are listed first; valuation and trend "
                       "reasons follow. Each row carries the exact binding trigger behind the call."},
    "std":    {"title": "The names we would sell",
               "lead": "Ordered by reason: forensic and balance-sheet issues first, then valuation and "
                       "trend. Each has the specific trigger behind the call."},
    "simple": {"title": "The shares we would sell",
               "lead": "The most serious reasons (accounting, debt) come first. Each name shows the one "
                       "thing that tips it into a Sell."},
}

FOOTNOTE = "Names marked Under review are with the investment committee; no action until resolved."


def _clip(txt, n):
    txt = (txt or "").strip()
    if len(txt) <= n:
        return txt
    cut = txt[:n]
    sp = cut.rfind(" ")
    if sp > n * 0.6:
        cut = cut[:sp]
    return cut.rstrip(" ,.;:") + "…"


def _lead(reg, n, n_act, n_rev):
    if not n_rev:
        return LABELS.get(reg, LABELS["std"])["lead"]
    a = str(n_act) if n_act else "none"
    if reg == "hni":
        return (f"Of the {n} names in the Sell zone, {a} are cleared to execute today; {n_rev} sit "
                f"with the investment committee as Under review. Forensic and gate reasons list first.")
    if reg == "simple":
        return (f"We can act on {a} of these {n} shares today. The other {n_rev} are being "
                f"double-checked by our committee first, so no action on those yet.")
    return (f"Of {n} Sell-zone names, {a} are cleared to execute and {n_rev} are Under review with the "
            f"investment committee. Ordered by reason: forensic and balance-sheet issues first, then "
            f"valuation and trend.")


def render(deck, ctx, tier):
    reg = tier["register"]
    L = LABELS.get(reg, LABELS["std"])
    as_of = ctx["client"].get("as_of", "")
    sells = [e for e in ctx["equity"] if e["rec"] == "Sell"]
    n_rev = sum(1 for e in sells if e.get("escalation"))
    n_act = len(sells) - n_rev

    s = deck.content(2, "Equity", "What we would sell", L["title"])
    deck.scope_tag(s, f"Direct equity only · as of {as_of}")
    deck.txt(s, ML, 1.80, UW, 0.42, [(_lead(reg, len(sells), n_act, n_rev), SERIF, 10.5, SLATE, False, True)],
             ls=1.03)

    def rank(e):
        r = TAXONOMY.get(e.get("reason_category"), (7, e.get("reason_category") or "Weak forward risk-reward"))[0]
        # actionable Sells lead the table; under-review names group after, same reason ordering
        return (1 if e.get("escalation") else 0, r, -(e.get("weight_pct") or 0))
    sells = sorted(sells, key=rank)

    cols = [("Holding", 0.17, "l"), ("Wt %", 0.06, "r"), ("Ionic Score", 0.13, "l"),
            ("Action", 0.13, "c"), ("Reason category", 0.19, "l"), ("Binding trigger", 0.32, "l")]
    rows = []
    for e in sells:
        short = TAXONOMY.get(e.get("reason_category"), (7, e.get("reason_category") or "Weak forward risk-reward"))[1]
        under = bool(e.get("escalation"))
        rows.append([
            ("b", e["name"]),
            ("c", f"{e['weight_pct']:.2f}", INK),
            ("bar", e.get("ionic_score")),
            ("pill", "Under review", "Watch") if under else ("pill", "Sell", "Sell"),
            ("c", short, AMBER if under else SELL, True),
            _clip(e.get("binding_trigger", ""), 38),
        ])
    n = len(rows)
    rowh = 0.44 if n <= 6 else (0.34 if n <= 8 else 0.30)
    ty = deck.table(s, ML, 2.32, UW, cols, rows, rowh=rowh, fs=9, hfs=8)

    # under-review footnote (frozen methodology) ------------------------------
    fy = ty + 0.06
    if n_rev:
        deck.txt(s, ML, fy, UW, 0.18, [(FOOTNOTE, SERIF, 8.5, SLATE, False, True)])
        fy += 0.24

    # reason-taxonomy legend --------------------------------------------------
    lgy = min(fy + 0.06, 6.30)
    deck.txt(s, ML, lgy, UW, 0.22,
             [("REASON TAXONOMY   ", SANS, 8.5, NAVY, True, False, 60),
              ("fixed categories, forensic and gate reasons rank first · full definitions and "
               "per-name rationale cards in the annexure", SERIF, 9, SLATE, False, True)])

    deck.source(s, "Reason category is a fixed client-facing taxonomy · binding trigger is the specific "
                   "analyst finding behind each call · full rationale cards in the annexure.")
    deck.score_band(s)
    return 1
