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


def _mix(ctx):
    """2026-07-28 fix: trims are now computed from each holding's real weight vs the real
    single-name cap (same logic as the priority_actions/tax trim total elsewhere in the deck)
    -- the old TRIM_PT=2.0 constant applied a fixed "two >11% trims" shift unconditionally,
    which was FALSE for any client (e.g. Anand Reddy, n_trim=0) whose book has no over-cap
    Hold names. A per-band trim total that's genuinely zero now shows as zero, not -2pt."""
    eq = ctx["equity"]; grand = ctx["totals"]["grand_inr"]
    cap = ctx.get("ips", {}).get("single_name_cap_pct")
    band = {"Large": 0.0, "Mid": 0.0, "Small": 0.0, "Micro": 0.0}
    sells = dict(band); trims = dict(band)
    n_trim = 0
    for e in eq:
        b = e["mcap_band"] if e["mcap_band"] in band else "Small"
        band[b] += e["weight_pct"]
        if e["rec"] == "Sell":
            sells[b] += e["weight_pct"]
        elif cap and e["weight_pct"] > cap:
            trims[b] += e["weight_pct"] - cap
            n_trim += 1
    net_pt = ctx["deployment"]["net_inr"] / grand * 100
    slv = ctx["deployment"]["sleeves"]
    tot = sum(a for _, a, _ in slv) or 1
    # no low-vol/foreign sleeve on file yet (e.g. a single "Liquid / cash" holding sleeve while
    # goals/IPS are pending) -> nothing to redeploy into those buckets, default to 0 rather than crash
    add_large = net_pt * next((a for n, a, _ in slv if n.lower().startswith("low-vol")), 0) / tot
    add_foreign = net_pt * next((a for n, a, _ in slv if n.lower().startswith("foreign")), 0) / tot
    before = [band["Large"], band["Mid"], band["Small"] + band["Micro"], 0.0]
    after = [band["Large"] - sells["Large"] - trims["Large"] + add_large,
             band["Mid"] - sells["Mid"] - trims["Mid"],
             band["Small"] + band["Micro"] - sells["Small"] - sells["Micro"] - trims["Small"] - trims["Micro"],
             add_foreign]
    bsum, asum = sum(before), sum(after)
    return ([round(v / bsum * 100, 1) for v in before],
            [round(v / asum * 100, 1) for v in after], net_pt, add_large, add_foreign, n_trim)


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    n_sell = ctx["totals"]["n_sell"]
    before, after, net_pt, add_large, add_foreign, n_trim = _mix(ctx)

    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(5, "Annexure", eyebrow, title)
    trim_clause = f"{n_trim} over-cap trim(s)" if n_trim else "no trims (no position over the single-name cap)"
    deck.scope_tag(s, f"Equity sleeve only (gold and staged cash excluded) · after = Sells + {trim_clause}, "
                      f"a PROPOSED redeployment per the transition framework, not yet executed · as of {as_of}")

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

    no_redeploy_plan = add_large <= 0 and add_foreign <= 0
    trim_phrase = (f"trimming {n_trim} over-cap position(s)" if n_trim
                   else "no position needing a trim")
    if no_redeploy_plan:
        body = ("No redeployment plan is set yet for this account. Proceeds are held as cash "
                "pending your goals and IPS discussion — nothing here is executed.")
    elif reg == "simple":
        body = (f"Selling the {n_sell} weak names, with {trim_phrase}, frees up cash. Most of it "
                f"could go back into steadier large-caps, and a part could start the foreign holding "
                f"the plan calls for — a proposal, not yet acted on.")
    else:
        body = (f"The plan is a quality rotation, and the cap mix would show it: proceeds from the "
                f"{n_sell} Sells, with {trim_phrase} (~{net_pt:.1f}% of the book, net of estimated "
                f"tax), are proposed to go back into a low-vol large-cap core and open the first "
                f"foreign sleeve. This is the transition framework, not a recommendation already "
                f"acted on — nothing executes without your authorisation.")
    deck.callout(s, tx, 3.85, tw, 2.35, "Tied to the deployment plan", body, kind="note")

    deck.source(s, "Cap mix as % of the equity sleeve, before vs a PROPOSED after (transition "
                   "framework, not executed); redeployment split per the deployment-plan sleeves; "
                   "net of estimated tax leak.")
    return 1
