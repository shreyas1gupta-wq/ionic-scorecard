# -*- coding: utf-8 -*-
"""deployment (Section 04, Recommendations, v8 #27, F6).
CH.waterfall of the deployment sleeves on a net-of-tax base, with an explicit
'less: est. tax leakage' step; a numbered sequencing-rationale panel (ctx sequence);
one-line rationale per sleeve; non-solicitation framing (liquidity logic, not a market call)."""
import charts as CH
from slidekit import NAVY, GOLD, INK, SLATE, NT2, SERIF, SANS, ML, UW, RX, PANEL, HAIR, clip_clause
from pptx.enum.text import PP_ALIGN

SECTION_NO, SECTION = 5, "Annexure"   # transition plan lives in the annexure (Principal 2026-07-25)


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
    "hni": {"eyebrow": "Transition framework · on request", "title": "How net proceeds could be staged, sequenced by liquidity",
            "seq": "Sequencing", "foot": "Annexure framework, not a recommendation: no scheme or security is being recommended here. Sequencing reflects liquidity and settlement logic, not a market-timing call; sleeves are illustrative (advisory / CIO-owned) and nothing executes without client authorisation. Amounts are net of estimated tax."},
    "std": {"eyebrow": "Transition framework · on request", "title": "How net proceeds could be staged, sequenced by liquidity",
            "seq": "Sequencing", "foot": "Annexure framework, not a recommendation: no scheme or security is being recommended here. Sequencing reflects liquidity and settlement logic, not a market-timing call; sleeves are illustrative (advisory / CIO-owned) and nothing executes without client authorisation. Amounts are net of estimated tax."},
    "simple": {"eyebrow": "If and when we reinvest", "title": "How the freed cash could go back to work, step by step",
               "seq": "The order we'd do it in", "foot": "This page is a framework, not a recommendation. The destinations are examples; nothing moves without your approval. All figures are after estimated tax."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    dep = ctx["deployment"]
    sleeves = dep["sleeves"]
    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])
    deck.anchor("mod:deployment", s, prio=5)

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

    # --- left below chart: one-line rationale per sleeve (amounts in ink — one gold accent per page) ---
    ry = 4.62
    for i, (name, amt, rat) in enumerate(sleeves):
        deck.txt(s, ML, ry + i * 0.44, 7.0, 0.42,
                 [(f"{name}  ", SANS, 9, NAVY, True), (_money(amt) + "   ", SANS, 9, INK, True),
                  (clip_clause(rat, 66), SERIF, 8.5, SLATE, False, True)], ls=1.0)

    # --- right below sequencing: personalised-transition block (Principal 2026-07-25) ---
    pers = dep.get("personalization") or []
    if pers:
        py2 = py + ph + 0.12
        deck.txt(s, px + 0.02, py2, pw, 0.22,
                 [(("PERSONALISED TO THIS MANDATE" if reg != "simple" else "BUILT AROUND YOUR GOALS"),
                   SANS, 8.5, GOLD, True, False, 80)])
        ly = py2 + 0.26
        for head, line in pers[:3]:
            deck.txt(s, px + 0.02, ly, pw, 0.28,
                     [(head + "  ·  ", SANS, 8, NAVY, True), (line[:46], SERIF, 8.5, INK, False, True)], ls=1.0)
            ly += 0.30

    deck.source(s, L["foot"])
    return 1
