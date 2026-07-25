# -*- coding: utf-8 -*-
"""group_concentration (Principal 2026-07-25): single-PROMOTER-GROUP exposure monitor.
ALWAYS checked at build; the slide renders ONLY if some group exceeds the 20% line
(of the direct-equity sleeve) — below the line it stays out of the client deck.
Returns 0 slides when nothing trips."""
from slidekit import (NAVY, INK, SLATE, SELL, AMBER, HOLD, SERIF, SANS, ML, UW, RX)

THRESHOLD = 20.0   # % of the direct-equity sleeve

# promoter-group map (symbols we cover; extend as the universe grows)
GROUP = {
    "TITAN": "Tata", "TATAPOWER": "Tata", "TATASTEEL": "Tata", "TATATECH": "Tata",
    "TCS": "Tata", "TATACONSUM": "Tata", "INDHOTEL": "Tata", "TMCV": "Tata", "TMPV": "Tata",
    "TATACAP": "Tata",
    "RELIANCE": "Reliance", "JIOFIN": "Reliance",
    "ADANIENT": "Adani", "ADANIPORTS": "Adani", "ADANIGREEN": "Adani", "ADANIPOWER": "Adani",
    "ADANIENSOL": "Adani", "ATGL": "Adani", "AMBUJACEM": "Adani", "ACC": "Adani",
    "BAJFINANCE": "Bajaj", "BAJAJ-AUTO": "Bajaj", "BAJAJFINSV": "Bajaj", "BAJAJHFL": "Bajaj",
    "BAJAJHLDNG": "Bajaj",
    "HINDALCO": "Aditya Birla", "ULTRACEMCO": "Aditya Birla", "GRASIM": "Aditya Birla",
    "ABCAPITAL": "Aditya Birla",
    "M&M": "Mahindra", "M&MFIN": "Mahindra",
    "JSWSTEEL": "JSW", "JSWENERGY": "JSW", "JSWINFRA": "JSW",
    "VEDL": "Vedanta", "HINDZINC": "Vedanta",
    "LT": "L&T", "LTM": "L&T", "LTF": "L&T",
}

LABELS = {
    "hni":    ("Group concentration", "One promoter group is more than a fifth of the equity book"),
    "std":    ("Group concentration", "One promoter group is more than a fifth of the equity book"),
    "simple": ("Companies from one family group", "A large share of your shares belongs to one business group"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]
    eq_total = sum(e["weight_pct"] for e in eq) or 1.0

    groups = {}
    for e in eq:
        g = GROUP.get(e["symbol"])
        if g:
            groups.setdefault(g, []).append(e)
    hits = []
    for g, members in groups.items():
        share = 100.0 * sum(e["weight_pct"] for e in members) / eq_total
        if share > THRESHOLD:
            hits.append((g, share, sorted(members, key=lambda e: -e["weight_pct"])))
    if not hits:
        return 0                       # monitored, nothing trips, no slide

    hits.sort(key=lambda h: -h[1])
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(1, "Portfolio X-ray", eyebrow, title)
    deck.scope_tag(s, f"Direct equity sleeve · promoter-group mapping · threshold {THRESHOLD:.0f}% "
                      f"of the sleeve · as of {ctx['client']['as_of']}")

    kpis = []
    for g, share, members in hits[:3]:
        kpis.append((f"{share:.1f}%", f"{g} group", f"{len(members)} holdings", SELL if share > 25 else AMBER))
    deck.kpi_strip(s, kpis, y=1.9)

    g, share, members = hits[0]
    cols = [("Holding", 0.34, "l"), ("Wt % of book", 0.22, "r"), ("Ionic Score", 0.22, "l"), ("Call", 0.22, "c")]
    rows = [[("b", e["name"]), f"{e['weight_pct']:.1f}", ("bar", e.get("ionic_score")),
             ("pill", e["rec"], e["rec"])] for e in members]
    ty = deck.table(s, ML, 3.05, 7.1, cols, rows, rowh=0.32, fs=9.5, hfs=8)

    after = 100.0 * sum(e["weight_pct"] for e in members if e["rec"] != "Sell") / eq_total
    cx = ML + 7.35
    cw = RX - cx
    if reg == "simple":
        body = (f"Different companies, one owner: if the group hits trouble, several of your holdings "
                f"can fall together. The sells we already suggest bring the {g} share to about "
                f"{after:.0f}%; we would not add more {g}-group names for now.")
    else:
        body = (f"A promoter group is one balance sheet, one management culture and one event risk. "
                f"The sell calls already on the table take {g} from {share:.1f}% to ~{after:.0f}% of "
                f"the sleeve; we would cap any single group near {THRESHOLD:.0f}% and not add "
                f"{g}-group names until it is back inside the line.")
    deck.callout(s, cx, 3.05, cw, deck.callout_h(cw, body, min_h=1.6, max_h=3.2),
                 f"How we treat the {g} group", body, "human")

    deck.source(s, "Group mapping = promoter affiliation of listed holdings; share measured on the "
                   "direct-equity sleeve. This page appears only when a group crosses the threshold.")
    deck.score_band(s)
    return 1
