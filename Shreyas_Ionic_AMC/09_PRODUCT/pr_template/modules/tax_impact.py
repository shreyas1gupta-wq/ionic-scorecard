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


# CEO sweep 2026-07-26: the table (fund actions) and the bridge chart (direct-equity
# sell/trim plan) are DIFFERENT transaction sets — each panel now names its scope.
LABELS = {
    "hni": {"eyebrow": "Tax impact of this plan", "title": "What the recommended moves trigger · before you authorise anything",
            "tcap": "Mutual-fund actions · est. tax character per move",
            "cap": "Direct-equity sells & trims · net of est. tax", "ct": "Direct-equity tax: estimate for now",
            "foot": "Left: mutual-fund actions. Right: direct-equity sell/trim plan. Tax characterisations are indicative and preliminary, confirm holding period, character and applicable rates with the client's tax adviser before dealing. Illustrative."},
    "std": {"eyebrow": "Tax impact of this plan", "title": "What the recommended moves trigger · before you authorise anything",
            "tcap": "Mutual-fund actions · est. tax character per move",
            "cap": "Direct-equity sells & trims · net of est. tax", "ct": "Direct-equity tax: estimate for now",
            "foot": "Left: mutual-fund actions. Right: direct-equity sell/trim plan. Tax characterisations are indicative and preliminary, confirm holding period, character and applicable rates with the client's tax adviser before dealing. Illustrative."},
    "simple": {"eyebrow": "What tax this plan may cost", "title": "The tax on these moves · an estimate to confirm with your adviser",
               "tcap": "Your fund changes · the tax type each may trigger",
               "cap": "Selling the weak shares · what's left after est. tax", "ct": "The share-sale tax is an estimate for now",
               "foot": "The table covers your fund changes; the chart covers the share sales. These tax numbers are estimates only. Please confirm the exact tax with your tax adviser before we act. Illustrative."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    tax = ctx["tax"]
    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    # --- left: fund-action tax table (own scope caption; NOT the chart's numbers) ---
    deck.txt(s, ML, 1.72, 6.95, 0.24, [(L["tcap"].upper(), SANS, 8, SLATE, True, False, 80)])
    rows = []
    total_l = 0.0
    for (action, scheme, amt, holding, character, note) in tax["fund_rows"]:
        disp, kind = ACT_MAP.get(action, (action.title(), action.title()))
        from slidekit import short_name
        rows.append([("pill", disp, kind), short_name(scheme, 30), _money(amt), character])
        total_l += round(amt / 1e5, 1)   # total = sum of the DISPLAYED row values,
    total_l = round(total_l, 1)          # so the printed column visibly adds up
    total_disp = f"Rs {total_l/100:.2f} Cr" if total_l >= 100 else f"Rs {total_l:.1f} L"
    rows.append(["", ("b", "Total fund actions"), ("b", total_disp), ""])
    cols = [("Action", 0.16, "l"), ("Scheme", 0.44, "l"), ("Amount", 0.18, "r"), ("Tax character", 0.22, "l")]
    # 7 rows (6 actions + total) x 0.42 + header keeps the block above the y=5.5 callouts
    deck.table(s, ML, 2.02, 6.95, cols, rows, rowh=0.42, fs=9.5, hfs=8)

    # --- right: tax bridge chart (direct-equity sell/trim plan, a separate set) ---
    deck.txt(s, ML + 7.15, 1.72, UW - 7.15, 0.5, [(L["cap"].upper(), SANS, 8, SLATE, True, False, 80)], ls=1.05)
    png = CH.tax_bridge(tax["gross"], tax["ltcg"], tax["stcg"], "azby_tax_bridge")
    deck.pic(s, png, ML + 7.15, 2.25, UW - 7.15, 3.0, valign="middle")
    deck.txt(s, ML + 7.15, 5.05, UW - 7.15, 0.24,
             [("Net after est. tax feeds the deployment plan.", SERIF, 9, NT2, False, True)])

    # --- bottom: two callouts — direct-equity tax gap + the tax-inertia rule (Principal 2026-07-25) ---
    half = (UW - 0.3) / 2
    # deck.source() sits fixed at y=6.66 -- max_h must keep this box's bottom edge (y=5.5+h)
    # clear of that, whatever the text length (2026-07-27: 1.4 let the box reach y=6.9, which
    # already overlaps the 6.66-6.90 source-line band regardless of how much text is in it)
    gap_h = deck.callout_h(half, tax["de_gap_note"], min_h=0.98, max_h=1.05)
    deck.callout(s, ML, 5.5, half, gap_h, L["ct"], tax["de_gap_note"], kind="warn")
    inertia = ("Units held >5y (>10y more so) carry gains that offset switching alpha; their bar "
               "rises to structural-only. Stocks get no such pass."
               if tier.get("register") != "simple" else
               "For funds held over 5 years the tax bill can eat the gain from switching, so we "
               "switch those only for structural reasons.")
    deck.callout(s, ML + half + 0.3, 5.5, half, 0.98, "Long-held units: a higher bar to sell", inertia, kind="note")

    deck.source(s, L["foot"])
    return 1
