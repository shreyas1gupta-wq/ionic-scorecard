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
from lib import lookthrough as LT

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
        if current > band + 1e-9:
            return "Gap"
        # A holding inside a cap by a hundredth of a point is not the same risk as one inside it
        # by ten. One AMC at 24.9855% of this book, displayed as "25.0%" against a "max 25%" cap,
        # was stamped ALIGNED and read to a client as comfortable. A cap the book is sitting on
        # says so, because the next market move decides it, not the desk.
        if band and current >= band - 1.0:
            return "At limit"
        return "Aligned"
    # bands come in BOTH shapes by design (_band_txt has always handled both): 3-tuple
    # min/target/max for allocation and commodity bands, 2-tuple min/max for the equity
    # market-cap and credit bands. This used to unpack 3 unconditionally, so any 2-tuple
    # band raised mid-render; engine.build catches a module exception and moves on, so the
    # IPS page silently lost its whole right half (equity-level + commodities) while still
    # passing both geometry gates. Fixed 2026-08-03 — see the equity_mcap_bands shape in
    # data/azby_family.py, which is what every client data file is copied from.
    if isinstance(band, (tuple, list)) and len(band) == 3:
        lo, _tgt, hi = band
    elif isinstance(band, (tuple, list)) and len(band) == 2:
        lo, hi = band
    else:
        return "Pending"
    return "Aligned" if lo - 1e-9 <= current <= hi + 1e-9 else "Gap"


def _all_holdings(ctx):
    """Every position: funds, direct shares, and everything else the desk does not score."""
    return list(ctx.get("funds") or []) + list(ctx.get("equity") or []) + list(ctx.get("other") or [])


def _combined_band(ab):
    """One row covers fixed income AND alternates, so it needs the band for both.

    It looked up "Hybrid/Debt", a key nothing in this kit sets, so the row read TBD / Pending on
    every statement-driven deck while the mandate carried a band for each of the two sleeves. The
    envelope is the two bands added: a book can be anywhere inside either one."""
    fi, alt = ab.get("Fixed Income"), ab.get("Alternatives")
    if ab.get("Hybrid/Debt") is not None:
        return ab["Hybrid/Debt"]
    if fi is None and alt is None:
        return None

    def _hi(b):
        return 0.0 if b is None else float(b[-1])

    def _lo(b):
        return 0.0 if b is None else float(b[0])

    return (_lo(fi) + _lo(alt), _hi(fi) + _hi(alt))


def _computed(ips, name, unit="%"):
    """A figure the IPS workbook computed, or "Not tracked" where it could not."""
    v = (ips.get("computed") or {}).get(name)
    return "Not tracked" if v is None else (f"{v:.0f}{unit}" if unit else f"{v:.1f}")


def _current_values(ctx):
    """Every 'Current' figure computed live from ctx, over the WHOLE book.

    This module used to carry its OWN copy of the look-through maths, which lib/lookthrough.py
    documents as having been moved out of here in 2026-08-06 precisely so every page reads the
    identical number. The copy stayed behind and drifted. On a book that is 30% AIFs, a PMS, REITs,
    a ULIP and direct bonds, this page reported EQUITY AT 9% against a true 75.9%, because its copy
    summed direct shares and funds only, and it printed "fixed income and alternates 61%" which was
    the fund sleeve, not fixed income.

    Three figures were hardcoded to zero with comments asserting facts about ONE client's book:
    international equity, unlisted equity and silver. This book holds two overseas feeders and four
    unlisted companies, so both of those "facts" were false and the page said 0% to a client whose
    mandate caps unlisted at 30% and who is at 16% of the equity sleeve. Nothing here is hardcoded
    now; a figure that cannot be computed is left to the caller's band as TBD.
    """
    t = ctx["totals"]
    everything = _all_holdings(ctx)
    true_equity, true_debt, true_cash, true_other = LT.full_lookthrough_mix(ctx)

    def w(h):
        return float(h.get("weight_pct") or 0.0)

    def sub(h):
        return (h.get("risk_sub") or "").strip()

    all_weights = [w(h) for h in everything]
    single_scheme = max(all_weights) if all_weights else 0.0
    amc_share = LT.amc_concentration(ctx)
    single_amc = max(amc_share.values()) if amc_share else 0.0

    # Locked in means the holder cannot get out inside a year, whatever the wrapper. Counting only
    # ELSS missed every AIF, the ULIP and the private-equity funds, which is most of the real
    # lock-up in a book like this one.
    locked_in = sum(w(h) for h in everything if (h.get("days_to_cash") or 0) > 365)

    eq_holdings = [h for h in everything
                   if (h.get("asset_class") or "").strip().lower() == "equity"] or                   (list(ctx.get("equity") or []) + list(ctx.get("funds") or []))
    eq_sleeve_w = sum(w(h) for h in eq_holdings) or 1.0
    LARGE = {"Direct Equity - Large Cap", "Large Cap Fund", "Index Fund / ETF - Broad Market",
             "Factor / Smart Beta Fund"}
    MIDSMALL = {"Direct Equity - Mid Cap", "Direct Equity - Small Cap", "Direct Equity - Micro Cap",
                "Direct Equity - Recent IPO", "Mid Cap Fund", "Small Cap Fund"}
    capped = [h for h in eq_holdings if sub(h) in LARGE or sub(h) in MIDSMALL]
    cap_w = sum(w(h) for h in capped)
    if cap_w:
        large_share = sum(w(h) for h in capped if sub(h) in LARGE) / cap_w * 100.0
    else:   # fall back to the older mcap_band field where the framework has not placed anything
        band_w = sum(w(h) for h in eq_holdings if h.get("mcap_band")) or 1.0
        large_share = sum(w(h) for h in eq_holdings
                          if h.get("mcap_band") == "Large") / band_w * 100.0
    midsmall_share = 100.0 - large_share
    # The market-cap split is struck on the holdings whose mandate FIXES a cap band, which on this
    # book is about half the equity sleeve. Printed under a heading reading "Equity-level
    # parameters" with no scope, a client reads 73% large cap as 73% of their equity. It is 73% of
    # the part that has been placed, and the page now says which part that is.
    mcap_cover = (cap_w / eq_sleeve_w * 100.0) if eq_sleeve_w else 0.0

    UNLISTED = ("Unlisted Equity", "AIF Cat I", "AIF Cat II")
    intl_equity = sum(w(h) for h in eq_holdings
                      if sub(h) == "International Fund / FoF") / eq_sleeve_w * 100.0
    unlisted_equity = sum(w(h) for h in eq_holdings
                          if sub(h).startswith(UNLISTED)) / eq_sleeve_w * 100.0
    gold_share = sum(w(h) for h in everything if "gold" in (sub(h) + " " +
                     str(h.get("name") or "")).lower())
    silver_share = sum(w(h) for h in everything if "silver" in (sub(h) + " " +
                       str(h.get("name") or "")).lower())

    return {
        "equity_pct": true_equity, "hybrid_debt_pct": true_debt + true_other,
        "cash_pct": true_cash,
        "single_scheme_pct": single_scheme, "single_amc_pct": single_amc,
        "locked_in_pct": locked_in, "cash_cap_pct": true_cash,
        "large_pct": large_share, "midsmall_pct": midsmall_share,
        "mcap_cover_pct": mcap_cover,
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
    deck.txt(s, ML, 2.00, 1.6, 0.42, [(str(ips.get("risk_tier") or "Not set").upper(), SANS, 11, WHITE, True, False, 20)],
             align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    ox = ML + 1.85
    deck.txt(s, ox, 1.80, 5.2, 0.2, [("OBJECTIVE", SANS, 7.5, SLATE, True, False, 100)])
    deck.txt(s, ox, 2.00, 5.2, 0.42, [(str(ips.get("objective") or "Not stated"), SERIF, 9.5, INK, False, True)], ls=1.02)
    hx = ox + 5.4
    horizon_txt = f"{ips['horizon_yrs']} yr+" if ips.get("horizon_yrs") is not None else "TBD"
    deck.txt(s, hx, 1.80, RX - hx, 0.2, [("HORIZON", SANS, 7.5, SLATE, True, False, 100)])
    deck.txt(s, hx, 2.00, RX - hx, 0.42, [(horizon_txt, SANS, 14, NAVY, True)], anchor=MSO_ANCHOR.MIDDLE)

    colw = (UW - 0.24) / 2
    lx, rxc = ML, ML + colw + 0.24

    # ---- LEFT column: Portfolio-Level + Fixed-Income ----
    y = 2.58
    ab = ips.get("alloc_bands") or {}
    port_rows = [
        ("Equity", _band_txt(ab.get("Equity")), f"{cur['equity_pct']:.0f}%",
         _fit(cur["equity_pct"], ab.get("Equity"))),
        ("Fixed income & alternates", _band_txt(_combined_band(ab)),
         f"{cur['hybrid_debt_pct']:.0f}%", _fit(cur["hybrid_debt_pct"], _combined_band(ab))),
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
    _CREDIT_ROW = {"AAA": "AAA rated", "AA": "AA rated", "Below AA": "Below AA rated"}
    fi_rows = []
    for k, v in fib.items():
        _c = _computed(ips, _CREDIT_ROW.get(k, k))
        fi_rows.append((f"Credit — {k}", _band_txt(v), _c,
                        None if _c == "Not tracked" else
                        _fit((ips.get("computed") or {}).get(_CREDIT_ROW.get(k, k)), v)))
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
        ("Thematic / sectoral", _band_txt(ips.get("thematic_sectoral_cap_pct")),
         _computed(ips, "Thematic and sectoral"),
         _fit((ips.get("computed") or {}).get("Thematic and sectoral"),
              ips.get("thematic_sectoral_cap_pct"), cap_style=True)),
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
    # Two things a reader of this page is entitled to know and could not previously learn from it:
    # that the market-cap rows are struck on part of the equity sleeve rather than all of it, and
    # that the bands themselves may not yet be signed off.
    _cov = cur.get("mcap_cover_pct")
    _cov_note = ("" if _cov is None or _cov >= 99.5 else
                 f" Market-cap rows are struck on the {_cov:.0f}% of the equity sleeve whose "
                 "mandate fixes a cap band; a fund without one is not forced into a band.")
    _draft_note = ("" if ips.get("bands_approved", True) else
                   " The bands for this profile are a DRAFT pending the desk's sign-off; the "
                   "Aggressive profile is the approved one.")
    deck.source(s, "Ideal bands per the house IPS framework; Current computed live from actual "
                   "holdings (direct equity + fund look-through by category)."
                   + _cov_note + _draft_note + demo_tag)
    return 1
