# -*- coding: utf-8 -*-
"""tax_impact (Section 04, Recommendations, NEW split from v8 #26, F7).
Fund-action tax table (ctx['tax']['fund_rows']) + a direct-equity tax-GAP callout
(ctx tax de_gap_note) + CH.tax_bridge(gross, ltcg, stcg) + confirm-with-adviser footnote."""
import charts as CH
from slidekit import NAVY, GOLD, INK, SLATE, SELL, HOLD, NT2, SERIF, SANS, ML, UW, RX
from pptx.enum.text import PP_ALIGN

SECTION_NO, SECTION = 4, "Recommendations"

# fund_rows action codes are UPPERCASE -> (pill display, REC_STYLE kind)
ACT_MAP = {"SWITCH": ("Switch", "Switch"), "REDEEM": ("Redeem", "Redeem-to-Direct"),
           "EXIT": ("Exit", "Exit"), "TRIM": ("Trim", "Trim"), "HOLD": ("Hold", "Hold")}


def _money(v):
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


LABELS = {
    "hni": {"eyebrow": "Tax impact of this plan", "title": "What the recommended moves trigger · before you authorise anything",
            "cap": "Proceeds → net of est. tax", "ct": "Direct-equity tax, gap",
            "foot": "Tax characterisations are indicative and preliminary, confirm holding period, character and applicable rates with the client's tax adviser before dealing. Statutory rates need Compliance sign-off. Illustrative."},
    "std": {"eyebrow": "Tax impact of this plan", "title": "What the recommended moves trigger · before you authorise anything",
            "cap": "Proceeds → net of est. tax", "ct": "Direct-equity tax, gap",
            "foot": "Tax characterisations are indicative and preliminary, confirm holding period, character and applicable rates with the client's tax adviser before dealing. Statutory rates need Compliance sign-off. Illustrative."},
    "simple": {"eyebrow": "What tax this plan may cost", "title": "The tax on these moves · an estimate to confirm with your adviser",
               "cap": "Money freed → what's left after est. tax", "ct": "One tax figure we can't finish yet",
               "foot": "These tax numbers are estimates only. Please confirm the exact tax with your tax adviser before we act. Illustrative."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    tax = ctx["tax"]
    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    # --- left: fund-action tax table ---
    rows = []
    for (action, scheme, amt, holding, character, note) in tax["fund_rows"]:
        disp, kind = ACT_MAP.get(action, (action.title(), action.title()))
        from slidekit import short_name
        rows.append([("pill", disp, kind), short_name(scheme, 30), _money(amt), character])
    cols = [("Action", 0.16, "l"), ("Scheme", 0.44, "l"), ("Amount", 0.18, "r"), ("Tax character", 0.22, "l")]
    deck.table(s, ML, 1.98, 6.95, cols, rows, rowh=0.5, fs=9.5, hfs=8)

    # --- right: tax bridge chart ---
    deck.txt(s, ML + 7.15, 1.95, UW - 7.15, 0.24, [(L["cap"].upper(), SANS, 8, SLATE, True, False, 80)])
    png = CH.tax_bridge(tax["gross"], tax["ltcg"], tax["stcg"], "azby_tax_bridge")
    deck.pic(s, png, ML + 7.15, 2.25, UW - 7.15, 3.0, valign="middle")
    deck.txt(s, ML + 7.15, 5.05, UW - 7.15, 0.24,
             [("Net after est. tax feeds the deployment plan.", SERIF, 9, NT2, False, True)])

    # --- bottom: two callouts — direct-equity tax gap + the tax-inertia rule (Principal 2026-07-25) ---
    half = (UW - 0.3) / 2
    deck.callout(s, ML, 5.5, half, 0.98, L["ct"], tax["de_gap_note"], kind="warn")
    inertia = ("Units held >5y (>10y more so) carry gains that offset switching alpha; their bar "
               "rises to structural-only. Stocks get no such pass."
               if tier.get("register") != "simple" else
               "For funds held over 5 years the tax bill can eat the gain from switching, so we "
               "switch those only for structural reasons.")
    deck.callout(s, ML + half + 0.3, 5.5, half, 0.98, "Long-held units: a higher bar to sell", inertia, kind="note")

    deck.source(s, L["foot"])
    return 1
