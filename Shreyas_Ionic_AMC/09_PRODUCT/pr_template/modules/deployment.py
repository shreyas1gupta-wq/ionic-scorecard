# -*- coding: utf-8 -*-
"""deployment (Section 04, Recommendations, v8 #27, F6).
CH.waterfall of the deployment sleeves on a net-of-tax base, with an explicit
'less: est. tax leakage' step; a numbered sequencing-rationale panel (ctx sequence);
one-line rationale per sleeve; non-solicitation framing (liquidity logic, not a market call)."""
import charts as CH
from slidekit import NAVY, GOLD, INK, SLATE, NT2, SERIF, SANS, ML, UW, RX, PANEL, HAIR
from pptx.enum.text import PP_ALIGN

SECTION_NO, SECTION = 4, "Recommendations"


def _money(v):
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


def _short(name):
    n = name.lower()
    if "low-vol" in n or "value" in n: return "Low-vol\ncore"
    if "foreign" in n or "global" in n: return "Foreign\nequity"
    if "gold" in n: return "Gold &\nsilver"
    if "cash" in n: return "Cash\n(staged)"
    return name[:10]


LABELS = {
    "hni": {"eyebrow": "Where the money moves · and why", "title": "Net proceeds redeployed by sleeve, sequenced by liquidity",
            "seq": "Sequencing", "foot": "Sequencing reflects liquidity and settlement logic, not a market-timing call. Redeployment destinations are illustrative (advisory / CIO-owned) and execute only on client authorisation. Amounts are net of estimated tax."},
    "std": {"eyebrow": "Where the money moves · and why", "title": "Net proceeds redeployed by sleeve, sequenced by liquidity",
            "seq": "Sequencing", "foot": "Sequencing reflects liquidity and settlement logic, not a market-timing call. Redeployment destinations are illustrative (advisory / CIO-owned) and execute only on client authorisation. Amounts are net of estimated tax."},
    "simple": {"eyebrow": "Where the money goes next", "title": "How we'd put the freed cash back to work, step by step",
               "seq": "The order we'd do it in", "foot": "This is a liquidity plan, not a market call. The destinations are illustrative and nothing moves until you say yes. All figures are after estimated tax."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    dep = ctx["deployment"]
    sleeves = dep["sleeves"]
    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    # --- left: waterfall (gross -> less tax -> sleeves -> cash) ---
    steps = [("Gross\nproceeds", dep["proceeds_inr"], "open"),
             ("less\nest. tax", dep["tax_leak_inr"], "flow")]
    for (name, amt, _rat) in sleeves[:-1]:
        steps.append((_short(name), amt, "flow"))
    steps.append((_short(sleeves[-1][0]), sleeves[-1][1], "close"))
    png = CH.waterfall(steps, "azby_deploy_wf", gold_idx=1)
    deck.pic(s, png, ML, 1.95, 7.0, 2.55, valign="top")

    # --- right: numbered sequencing-rationale panel ---
    px, pw, py, ph = ML + 7.25, UW - 7.25, 1.95, 3.35
    deck.rect(s, px, py, pw, ph, fill=PANEL, line=HAIR, round_=0.04)
    deck.txt(s, px + 0.22, py + 0.16, pw - 0.4, 0.24, [(L["seq"].upper(), SANS, 9, NAVY, True, False, 80)])
    seq = dep["sequence"]
    iy, step = py + 0.52, (ph - 0.62) / max(len(seq), 1)
    for i, q in enumerate(seq):
        deck.txt(s, px + 0.22, iy + i * step, 0.3, 0.24, [(f"{i+1}", SANS, 10, GOLD, True)])
        deck.txt(s, px + 0.5, iy + i * step, pw - 0.72, step, [(q, SERIF, 9, INK, False)], ls=1.04)

    # --- left below chart: one-line rationale per sleeve ---
    ry = 4.62
    for i, (name, amt, rat) in enumerate(sleeves):
        deck.txt(s, ML, ry + i * 0.44, 7.0, 0.42,
                 [(f"{name}  ", SANS, 9, NAVY, True), (_money(amt) + "   ", SANS, 9, GOLD, True),
                  (rat[:70], SERIF, 8.5, SLATE, False, True)], ls=1.0)

    deck.source(s, L["foot"])
    return 1
