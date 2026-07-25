# -*- coding: utf-8 -*-
"""Annexure B, market-cap mix, before vs after the deployment plan. Two 100% stacked columns
with per-segment change labels. After = Sells and the two >11% trims executed, net proceeds
redeployed per the deployment sleeves (low-vol large-cap add + first foreign sleeve)."""
import chart_ext_b as CB
from slidekit import ML, UW, RX, HOLD, SELL, INK

LABELS = {
    "hni":    ("Market-cap migration", "What the deployment plan does to the cap mix"),
    "std":    ("Market-cap migration", "What the plan changes in the cap mix"),
    "simple": ("Market-cap migration", "The mix, before and after the plan"),
}

CATS = ["Large cap", "Mid cap", "Small cap", "Foreign"]
TRIM_PT = 2.0  # the two >11% names trimmed toward the single-name cap (both Large)


def _mix(ctx):
    eq = ctx["equity"]; grand = ctx["totals"]["grand_inr"]
    band = {"Large": 0.0, "Mid": 0.0, "Small": 0.0, "Micro": 0.0}
    sells = dict(band)
    for e in eq:
        b = e["mcap_band"] if e["mcap_band"] in band else "Small"
        band[b] += e["weight_pct"]
        if e["rec"] == "Sell":
            sells[b] += e["weight_pct"]
    net_pt = ctx["deployment"]["net_inr"] / grand * 100
    slv = ctx["deployment"]["sleeves"]
    tot = sum(a for _, a, _ in slv) or 1
    add_large = net_pt * next(a for n, a, _ in slv if n.lower().startswith("low-vol")) / tot
    add_foreign = net_pt * next(a for n, a, _ in slv if n.lower().startswith("foreign")) / tot
    before = [band["Large"], band["Mid"], band["Small"] + band["Micro"], 0.0]
    after = [band["Large"] - sells["Large"] - TRIM_PT + add_large,
             band["Mid"] - sells["Mid"],
             band["Small"] + band["Micro"] - sells["Small"] - sells["Micro"],
             add_foreign]
    bsum, asum = sum(before), sum(after)
    return ([round(v / bsum * 100, 1) for v in before],
            [round(v / asum * 100, 1) for v in after], net_pt)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    n_sell = ctx["totals"]["n_sell"]
    before, after, net_pt = _mix(ctx)

    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"Equity sleeve only (gold and staged cash excluded) · after = Sells + the two "
                      f">11% trims executed, net proceeds redeployed per plan · as of {as_of}")

    png = CB.mcap_migration(CATS, before, after, "annexb_mig")
    deck.pic(s, png, ML, 1.95, 6.7, 4.5, valign="top", halign="left")

    tx = ML + 6.95
    tw = RX - tx
    cols = [("Segment", 0.36, "l"), ("Before", 0.20, "r"), ("After", 0.20, "r"), ("Change", 0.24, "r")]
    rows = []
    for c, b, a in zip(CATS, before, after):
        d = a - b
        rows.append([c, f"{b:.1f}%", f"{a:.1f}%",
                     ("c", f"{d:+.1f} pt", (HOLD if d >= 0 else SELL) if abs(d) > 0.05 else INK, abs(d) > 0.05)])
    deck.table(s, tx, 2.0, tw, cols, rows, rowh=0.34, fs=9.5, hfs=7.5)

    if reg == "simple":
        body = (f"Selling the {n_sell} weak names and trimming the two largest positions frees up cash. "
                f"Most of it goes back into steadier large-caps, and a part starts the foreign holding "
                f"the plan calls for. The overall shape of the book barely changes.")
    else:
        body = (f"The plan is a quality rotation, and the cap mix shows it: proceeds from the {n_sell} "
                f"Sells and the two concentration trims (~{net_pt:.1f}% of the book, net of estimated tax) "
                f"go back into a low-vol large-cap core and open the first foreign sleeve. Large-cap "
                f"character is preserved; what changes is single-name risk and the zero foreign weight.")
    deck.callout(s, tx, 3.85, tw, 2.35, "Tied to the deployment plan", body, kind="note")

    deck.source(s, "Cap mix as % of the equity sleeve, before vs after the recommended actions; "
                   "redeployment split per the deployment-plan sleeves; net of estimated tax leak.")
    return 1
