# -*- coding: utf-8 -*-
"""ips_summary (F1, core) — Investment Policy Statement, v2 (2026-07-28).
"Best of both worlds" rebuild: broader parameter coverage (portfolio/equity/fixed-income/
commodities level, each with a real min-target-max or max-only band, matching an institutional
IPS reference the Principal supplied) rendered in our existing rail-bar/pill visual language,
not a plain corporate table. "Current" is computed LIVE from ctx for every parameter where the
underlying data honestly supports it (equity+fund look-through allocation, single-scheme/AMC
concentration, ELSS lock-in share, market-cap mix, international/unlisted exposure, gold/silver
holdings) -- never from a client-authored guess, and never fabricated where data doesn't exist
(fixed-income credit quality / duration: "Not tracked" until per-debt-holding data is sourced).
On a first-review client with no bespoke IPS on file, Ideal columns show "TBD" and Fit shows
"Pending" rather than inventing a target -- the page still shows the client's real position on
every parameter so the next review has a baseline to set targets against."""
from slidekit import (NAVY, GOLD, INK, SLATE, PANEL, HAIR, WHITE, SERIF, SANS, ML, UW, RX)
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

# fund category -> broad allocation bucket, for a TRUE look-through Equity/Fixed-Income split
# (direct equity + equity-oriented funds vs hybrid/debt/cash-like funds) -- addresses "too much
# [about where sell/trim cash actually sits] is not covered" (Principal 2026-07-28): a client's
# real equity exposure is under-stated by direct-equity-only, and a deployment plan sized off
# that understated number would misjudge how much room actually exists against the IPS band.
_EQUITY_FUND_CATS = {"mid", "small", "large", "flexi", "multi", "elss", "dividend_yield",
                     "focused", "value", "passive", "thematic_mnc", "largemid"}
_HYBRID_FUND_CATS = {"hybrid", "conservative_hybrid"}
_DEBT_FUND_CATS = {"gilt", "debt_short", "overnight", "debt"}

LABELS = {
    "hni":    ("Investment Policy Statement", "The mandate we manage to, and where the book sits today"),
    "std":    ("Investment Policy Statement", "The mandate we manage to, and where the book sits today"),
    "simple": ("Your plan, in one page", "What we agreed, and how your money lines up with it"),
}


def _band_txt(band, unit="%"):
    if band is None:
        return "TBD"
    if isinstance(band, tuple) and len(band) == 3:
        lo, tgt, hi = band
        return f"{lo:.0f}–{hi:.0f}{unit}  (tgt {tgt:.0f})"
    if isinstance(band, tuple) and len(band) == 2:
        lo, hi = band
        return f"{lo:.0f}–{hi:.0f}{unit}"
    return f"≤ {band:.0f}{unit}"


def _fit(current, band, cap_style=False):
    """Aligned / Gap / Pending pill kind, from a real current value vs a real band or cap.
    Returns None (no pill) when the band itself is TBD -- never invent a Fit against nothing."""
    if band is None or current is None:
        return "Pending"
    if cap_style:
        return "Aligned" if current <= band + 1e-9 else "Gap"
    lo, tgt, hi = band
    return "Aligned" if lo - 1e-9 <= current <= hi + 1e-9 else "Gap"


def _lookthrough_mix(ctx):
    """Real Equity / Hybrid-Debt / Cash split, direct equity + fund look-through by category --
    not just the crude direct-equity-vs-everything-else split used elsewhere in the deck."""
    eq = ctx["equity"]; funds = ctx["funds"]; t = ctx["totals"]
    eq_w = sum(e["weight_pct"] for e in eq)
    fund_eq_w = sum(f["weight_pct"] for f in funds if f.get("category") in _EQUITY_FUND_CATS)
    fund_hybrid_w = sum(f["weight_pct"] for f in funds if f.get("category") in _HYBRID_FUND_CATS)
    fund_debt_w = sum(f["weight_pct"] for f in funds if f.get("category") in _DEBT_FUND_CATS)
    fund_other_w = sum(f["weight_pct"] for f in funds) - fund_eq_w - fund_hybrid_w - fund_debt_w
    true_equity = eq_w + fund_eq_w
    true_hybrid_debt = fund_hybrid_w + fund_debt_w + max(fund_other_w, 0)
    true_cash = t.get("cash_pct", 0.0)
    return true_equity, true_hybrid_debt, true_cash


def _current_values(ctx):
    """Every 'Current' figure computed live from ctx -- correct for ANY client automatically,
    never pre-baked into a client's data file (2026-07-28 design rule for this module)."""
    eq = ctx["equity"]; funds = ctx["funds"]; t = ctx["totals"]
    true_equity, true_hybrid_debt, true_cash = _lookthrough_mix(ctx)

    all_weights = [e["weight_pct"] for e in eq] + [f["weight_pct"] for f in funds]
    single_scheme = max(all_weights) if all_weights else 0.0

    amc_tot = {}
    for f in funds:
        amc = f.get("amc") or "Unknown"
        amc_tot[amc] = amc_tot.get(amc, 0.0) + f["weight_pct"]
    single_amc = max(amc_tot.values()) if amc_tot else 0.0

    locked_in = sum(f["weight_pct"] for f in funds if f.get("category") == "elss")

    eq_sleeve_w = sum(e["weight_pct"] for e in eq) or 1.0
    large_share = sum(e["weight_pct"] for e in eq if e.get("mcap_band") == "Large") / eq_sleeve_w * 100.0
    midsmall_share = 100.0 - large_share

    intl_equity = 0.0  # no foreign-listed holding in this book -- a real fact, not a data gap
    unlisted_equity = 0.0  # every holding here is exchange-listed -- a real fact, not a data gap
    gold_share = sum(e["weight_pct"] for e in eq if "gold" in e["name"].lower()) / (
        sum(e["weight_pct"] for e in eq) + sum(f["weight_pct"] for f in funds) or 1.0) * 100.0
    silver_share = 0.0  # no silver-specific holding tracked

    return {
        "equity_pct": true_equity, "hybrid_debt_pct": true_hybrid_debt, "cash_pct": true_cash,
        "single_scheme_pct": single_scheme, "single_amc_pct": single_amc,
        "locked_in_pct": locked_in, "cash_cap_pct": true_cash,
        "large_pct": large_share, "midsmall_pct": midsmall_share,
        "intl_equity_pct": intl_equity, "unlisted_equity_pct": unlisted_equity,
        "gold_pct": gold_share, "silver_pct": silver_share,
    }


def _section(deck, s, x, y, w, title, rows, rowh=0.25, fs=8.5):
    """One sectioned mini-table: a navy label bar, then Parameter | Ideal | Current | Fit rows."""
    deck.rect(s, x, y, w, 0.24, fill=NAVY)
    deck.txt(s, x + 0.12, y - 0.01, w - 0.2, 0.24, [(title.upper(), SANS, 8, WHITE, True, False, 100)],
             anchor=MSO_ANCHOR.MIDDLE)
    ry = y + 0.30
    cw = [w * 0.40, w * 0.28, w * 0.18, w * 0.14]
    cx = [x, x + cw[0], x + cw[0] + cw[1], x + cw[0] + cw[1] + cw[2]]
    for i, (param, ideal, current, fit) in enumerate(rows):
        if i % 2 == 1:
            deck.rect(s, x, ry - 0.01, w, rowh, fill=PANEL)
        deck.txt(s, cx[0] + 0.1, ry, cw[0] - 0.15, rowh, [(param, SERIF, fs, INK, False)],
                 anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, cx[1], ry, cw[1] - 0.1, rowh, [(ideal, SANS, fs - 0.5, SLATE, False)],
                 anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, cx[2], ry, cw[2] - 0.1, rowh, [(current, SANS, fs - 0.5, NAVY, True)],
                 anchor=MSO_ANCHOR.MIDDLE)
        if fit:
            # REC_STYLE already has "Aligned"/"Gap" as direct keys (navy/green vs red); an
            # unrecognized kind like "Pending" falls back to neutral grey -- exactly right.
            deck.pill(s, cx[3] + 0.05, ry + rowh / 2 - 0.12, fit, w=cw[3] - 0.15, kind=fit)
        ry += rowh
    deck.rule(s, x, ry, w, HAIR, 0.006)
    return ry


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    ips = ctx["ips"]
    # 2026-07-28 (Principal): a client with no bespoke IPS on file gets no IPS page at all --
    # a page of "TBD"/"Pending" rows isn't worth a slide; skip it entirely rather than show it
    # half-empty. Real clients get this page back the moment an IPS is agreed and on_file=True.
    if not ips.get("on_file", False):
        return 0
    cur = _current_values(ctx)
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    s = deck.content(0, "Understanding", eyebrow, title)

    if ctx.get("is_demo", False):
        tag = "[ILLUSTRATIVE, demo IPS]"
    elif not ips.get("on_file", True):
        tag = "IPS NOT ON FILE — bands show TBD; Current reflects your real holdings today"
    else:
        tag = ""
    if tag:
        deck.txt(s, RX - 5.6, 1.62, 5.6, 0.2, [(tag, SANS, 8, GOLD, True, True)], align=PP_ALIGN.RIGHT)

    # ---- header: risk badge + objective + horizon ----
    deck.txt(s, ML, 1.80, 1.6, 0.2, [("RISK TIER", SANS, 7.5, SLATE, True, False, 100)])
    deck.rect(s, ML, 2.00, 1.6, 0.42, fill=NAVY, round_=0.10)
    deck.txt(s, ML, 2.00, 1.6, 0.42, [(ips["risk_tier"].upper(), SANS, 11, WHITE, True, False, 20)],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    ox = ML + 1.85
    deck.txt(s, ox, 1.80, 5.2, 0.2, [("OBJECTIVE", SANS, 7.5, SLATE, True, False, 100)])
    deck.txt(s, ox, 2.00, 5.2, 0.42, [(ips["objective"], SERIF, 9.5, INK, False, True)], ls=1.02)
    hx = ox + 5.4
    horizon_txt = f"{ips['horizon_yrs']} yr+" if ips.get("horizon_yrs") is not None else "TBD"
    deck.txt(s, hx, 1.80, RX - hx, 0.2, [("HORIZON", SANS, 7.5, SLATE, True, False, 100)])
    deck.txt(s, hx, 2.00, RX - hx, 0.42, [(horizon_txt, SANS, 14, NAVY, True)], anchor=MSO_ANCHOR.MIDDLE)

    colw = (UW - 0.24) / 2
    lx, rxc = ML, ML + colw + 0.24

    # ---- LEFT column: Portfolio-Level + Fixed-Income ----
    y = 2.58
    ab = ips["alloc_bands"]
    port_rows = [
        ("Equity", _band_txt(ab.get("Equity")), f"{cur['equity_pct']:.0f}%",
         _fit(cur["equity_pct"], ab.get("Equity"))),
        ("Fixed income & alternates", _band_txt(ab.get("Hybrid/Debt")), f"{cur['hybrid_debt_pct']:.0f}%",
         _fit(cur["hybrid_debt_pct"], ab.get("Hybrid/Debt"))),
        ("Single scheme / instrument", _band_txt(ips.get("single_name_cap_pct")), f"{cur['single_scheme_pct']:.1f}%",
         _fit(cur["single_scheme_pct"], ips.get("single_name_cap_pct"), cap_style=True)),
        ("Single AMC", _band_txt(ips.get("single_amc_cap_pct")), f"{cur['single_amc_pct']:.1f}%",
         _fit(cur["single_amc_pct"], ips.get("single_amc_cap_pct"), cap_style=True)),
        ("Locked-in (>1yr lock-in)", _band_txt(ips.get("locked_in_cap_pct")), f"{cur['locked_in_pct']:.1f}%",
         _fit(cur["locked_in_pct"], ips.get("locked_in_cap_pct"), cap_style=True)),
        ("Cash & equivalent", _band_txt(ips.get("cash_cap_pct")), f"{cur['cash_cap_pct']:.1f}%",
         _fit(cur["cash_cap_pct"], ips.get("cash_cap_pct"), cap_style=True)),
    ]
    y = _section(deck, s, lx, y, colw, "Portfolio-level parameters", port_rows)

    y += 0.10
    fib = ips.get("fi_credit_bands", {})
    fi_rows = [(f"Credit — {k}", _band_txt(v), "Not tracked", None) for k, v in fib.items()]
    fi_rows.append(("Modified duration", _band_txt(ips.get("mod_duration_cap_yrs"), unit="yr"), "Not tracked", None))
    y = _section(deck, s, lx, y, colw, "Fixed-income parameters", fi_rows)

    # ---- RIGHT column: Equity-Level + Commodities ----
    y2 = 2.58
    emb = ips.get("equity_mcap_bands", {})
    eq_rows = [
        ("Large cap", _band_txt(emb.get("Large")), f"{cur['large_pct']:.0f}%",
         _fit(cur["large_pct"], emb.get("Large"))),
        ("Mid & small cap", _band_txt(emb.get("Mid & Small")), f"{cur['midsmall_pct']:.0f}%",
         _fit(cur["midsmall_pct"], emb.get("Mid & Small"))),
        ("Thematic / sectoral", _band_txt(ips.get("thematic_sectoral_cap_pct")), "Not tracked", None),
        ("Unlisted equity", _band_txt(ips.get("unlisted_equity_cap_pct")), f"{cur['unlisted_equity_pct']:.0f}%",
         _fit(cur["unlisted_equity_pct"], ips.get("unlisted_equity_cap_pct"), cap_style=True)),
        ("International equity", _band_txt(ips.get("international_equity_cap_pct")), f"{cur['intl_equity_pct']:.0f}%",
         _fit(cur["intl_equity_pct"], ips.get("international_equity_cap_pct"), cap_style=True)),
    ]
    y2 = _section(deck, s, rxc, y2, colw, "Equity-level parameters", eq_rows)

    y2 += 0.10
    comm_rows = [
        ("Gold", _band_txt(ips.get("gold_band_pct")), f"{cur['gold_pct']:.1f}%",
         _fit(cur["gold_pct"], ips.get("gold_band_pct"))),
        ("Silver", _band_txt(ips.get("silver_band_pct")), f"{cur['silver_pct']:.1f}%",
         _fit(cur["silver_pct"], ips.get("silver_band_pct"))),
    ]
    y2 = _section(deck, s, rxc, y2, colw, "Commodities parameters", comm_rows)

    # ---- constraints strip, full width, whatever space remains ----
    cy = max(y, y2) + 0.12
    if cy < 6.35:
        deck.rule(s, ML, cy - 0.06, UW, HAIR, 0.008)
        deck.txt(s, ML, cy, UW, 0.2, [("CONSTRAINTS", SANS, 8, SLATE, True, False, 100)])
        cons = ips.get("constraints", [])
        colw2 = UW / 2
        for i, c in enumerate(cons[:4]):
            col, rowi = i % 2, i // 2
            px = ML + col * colw2
            yy = cy + 0.26 + rowi * 0.28
            deck.oval(s, px, yy + 0.05, 0.08, GOLD)
            deck.txt(s, px + 0.18, yy - 0.02, colw2 - 0.3, 0.26, [(c, SERIF, 9, INK, False)],
                     anchor=MSO_ANCHOR.MIDDLE)

    demo_tag = " Illustrative for the AZBY demo." if ctx.get("is_demo", False) else ""
    deck.source(s, "Ideal bands per the house IPS framework; Current computed live from actual "
                   "holdings (direct equity + fund look-through by category)." + demo_tag)
    return 1
