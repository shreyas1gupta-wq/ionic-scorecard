# -*- coding: utf-8 -*-
"""Annexure A3 - who drives portfolio risk: top-10 estimated risk contributions
(weight x volatility proxy, normalised) paired against capital weight."""
import chart_ext_a as CA
from slidekit import ML, RX

# assumed annualised volatility proxy per name (synthetic, size/sector patterned)
VOL_SYM = {
    "RELIANCE": 18, "TITAN": 24, "BAJFINANCE": 28, "HDFCBANK": 17, "ICICIBANK": 18,
    "TATAPOWER": 30, "SBIN": 24, "SUNPHARMA": 18, "BHARTIARTL": 20, "M&M": 24,
    "ITC": 16, "LT": 22, "TATASTEEL": 32, "HINDALCO": 33, "MARUTI": 22,
    "JIOFIN": 30, "DEEPAKNTR": 32, "PIDILITIND": 20, "ABB": 27, "SIEMENS": 27,
    "BHEL": 38, "POWERINDIA": 30, "GAIL": 24, "CIPLA": 18, "APLAPOLLO": 30,
    "PERSISTENT": 28, "COCHINSHIP": 40, "HINDCOPPER": 42, "TATATECH": 30, "BOSCHLTD": 22,
    "NATIONALUM": 34, "MOTHERSON": 30, "VBL": 26, "ULTRACEMCO": 20, "BANDHANBNK": 34,
    "IRCTC": 28, "ITCHOTELS": 30, "CMSINFO": 30,
}
BAND_VOL = {"Large": 20, "Mid": 27, "Small": 33, "Micro": 38}

LABELS = {
    "hni":    ("Capital weight is not risk weight",
               "Estimated risk contribution vs capital weight · top 10 names"),
    "std":    ("Where the portfolio's risk actually sits",
               "The biggest rupee positions are not always the biggest risks"),
    "simple": ("Where the risk sits",
               "Some smaller positions swing more than the big ones"),
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    as_of = ctx["client"]["as_of"]
    eyebrow, title = LABELS.get(reg, LABELS["std"])

    eq = ctx["equity"]
    tot_w = sum(e["weight_pct"] for e in eq)
    raw = []
    for e in eq:
        vol = VOL_SYM.get(e["symbol"]) or BAND_VOL.get(e["mcap_band"], 24)
        raw.append((e["symbol"], e["weight_pct"] / tot_w * 100.0, e["weight_pct"] * vol))
    tot_r = sum(r for _, _, r in raw)
    items = [(sym, cw, r / tot_r * 100.0) for sym, cw, r in raw]
    top = sorted(items, key=lambda t: -t[2])[:10]
    labels = [t[0] for t in top]
    cap_w = [t[1] for t in top]
    risk_w = [t[2] for t in top]
    capsum = sum(cap_w); risksum = sum(risk_w)
    hot = [sym for sym, c, r in top if r >= 1.35 * c]
    hot_txt = " and ".join(hot[:2]) if hot else "the mid and small caps"
    cap_leader = max(items, key=lambda t: t[1])[0]
    if cap_leader == labels[0]:
        lead_txt = f"{labels[0]} leads both lists on sheer size"
    else:
        lead_txt = (f"{cap_leader} is the biggest rupee position, yet {labels[0]} tops the "
                    f"risk list")

    s = deck.content(5, "Annexure", eyebrow, title)
    deck.scope_tag(s, f"[ILLUSTRATIVE] Direct-equity book · risk contribution = weight x "
                      f"volatility proxy, normalised to 100% · as of {as_of}")

    png = CA.risk_vs_weight(labels, cap_w, risk_w, "axa_riskw")
    deck.pic(s, png, ML, 1.85, 6.9, 4.55, valign="top")

    tx = 8.0; tw = RX - tx
    body1 = (f"The ten largest risk contributors hold {capsum:.0f}% of equity capital but an "
             f"estimated {risksum:.0f}% of its risk. {lead_txt}, while higher-volatility names "
             f"such as {hot_txt} carry clearly more risk than their capital weight "
             f"(gold figures).")
    deck.callout(s, tx, 1.95, tw, 2.1, "Capital weight is not risk weight", body1, kind="note")

    body2 = ("Use this page when a trim looks too small to matter in rupee terms. Risk is "
             "weight times volatility: a one-point trim of a high-volatility name removes more "
             "portfolio risk than the same point off a steady large cap, and the trim list is "
             "sequenced accordingly.")
    deck.callout(s, tx, 4.25, tw, 2.05, "When to use this view", body2, kind="human")

    deck.source(s, "Risk contribution estimated as capital weight times an assumed per-name "
                   "volatility proxy (synthetic), normalised to 100%; a full covariance "
                   "treatment would shift details, the ordering is the point. [ILLUSTRATIVE]")
    return 1
