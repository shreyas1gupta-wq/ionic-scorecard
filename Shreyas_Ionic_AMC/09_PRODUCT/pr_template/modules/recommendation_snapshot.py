# -*- coding: utf-8 -*-
"""recommendation_snapshot: every holding mapped to an action, reconciled to the whole book.

THIS IS THE PAGE THE STANDARD DECK OPENS ITS RECOMMENDATIONS WITH and this kit did not have. The
desk's own reference review carries it as a category-by-call pivot that foots to the portfolio
total, and it is the one page on which a client can satisfy themselves that nothing was left out:
if the Total column sums to the number on the cover, every rupee has been accounted for and given
a verdict.

IT INVENTS NOTHING. Every cell is a sum over the same row objects the rest of the deck reads, and
the columns are the calls this book actually carries - not a fixed list, so a book with no Trim
does not print an empty Trim column and a book carrying client-directed exits gets one.

THE RECONCILIATION IS THE POINT, so it is asserted on the page rather than assumed: the footer
states the total and whether it foots, and a gap is printed rather than hidden.
"""
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

from slidekit import (NAVY, NAVYD, GOLD, INK, SLATE, NT2, NT3, SELL, AMBER, HOLD, PANEL, HAIR,
                      WHITE, SERIF, SANS, ML, UW, RX, REC_STYLE)

SECTION_NO, SECTION = 4, "Recommendations"

LABELS = {
    "hni": ("Recommendation snapshot", "Every holding mapped to an action, reconciled to the whole book"),
    "std": ("Recommendation snapshot", "Every holding mapped to an action, reconciled to the whole book"),
    "simple": ("What we suggest, all together", "Everything you hold, and what we suggest for each"),
}

# The order a reader expects to meet them in: what moves first, what stays, what carries no view.
CALL_ORDER = ["Sell", "Trim", "Exit (client)", "Switch", "Hold (watch)", "Hold", "Retain",
              "No View", "Suspended"]
# Asset classes in the order the book is usually described.
CLASS_ORDER = ["Equity", "Fixed income", "Alternates", "Cash and equivalents", "Cash",
               "Unclassified", "Other"]


def _money(v):
    if not v:
        return "-"
    # A PRINTED "0.00 L" IS A ZERO, and the desk forbids one. A holding worth a few hundred rupees
    # is real and belongs in the total, but its cell says so rather than rounding to nought.
    if abs(v) < 1000:
        return "<0.01 L"
    return f"{v / 1e7:.2f} Cr" if abs(v) >= 1e7 else f"{v / 1e5:.2f} L"


def _rows(ctx):
    """(class, sub) -> {call: value}, over every holding in the book."""
    out, calls = {}, {}
    for r in (list(ctx.get("funds") or []) + list(ctx.get("equity") or [])
              + list(ctx.get("other") or [])):
        cls = str(r.get("asset_class") or "Other").strip() or "Other"
        # WITHIN A CLASS, THE INSTRUMENT. The reference deck splits equity into listed and
        # unlisted, and debt into funds and bonds, because a client reads those as different
        # things. sub_category is what the statement itself said.
        sub = str(r.get("sub_category") or r.get("category") or "").strip()
        call = str(r.get("verdict") or r.get("rec") or "No View").strip() or "No View"
        v = float(r.get("value_inr") or 0.0)
        if v <= 0:
            continue
        key = (cls, _bucket(cls, sub, r))
        out.setdefault(key, {})
        out[key][call] = out[key].get(call, 0.0) + v
        calls[call] = calls.get(call, 0.0) + v
    return out, calls


# The engine's own coarse category tokens, which are lowercase and internal, mapped to words a
# client reads. Without this the page printed rows headed "debt short", "gilt" and "overnight" --
# raw field values as client-facing labels, the exact defect the tell-scanner exists to catch and
# cannot see, because it has no way to know a lowercase word is a field name.
_ENGINE_LABEL = {
    "debt": "Debt funds", "debt_short": "Short-duration debt funds",
    "gilt": "Gilt funds", "overnight": "Liquid and overnight funds",
    "hybrid": "Hybrid funds", "conservative_hybrid": "Conservative hybrid funds",
    "passive": "Index funds and ETFs", "elss": "Tax-saving funds (ELSS)",
    "large": "Large-cap funds", "largemid": "Large and mid-cap funds",
    "mid": "Mid-cap funds", "small": "Small-cap funds", "flexi": "Flexi-cap funds",
    "multi": "Multi-cap funds", "focused": "Focused funds", "value": "Value and contra funds",
    "dividend_yield": "Dividend-yield funds", "thematic_mnc": "Thematic funds",
    "equity": "Equity funds",
}


def _bucket(cls, sub, row):
    """The line a client would recognise. Coarse on purpose: this page is a summary."""
    s = sub.lower()
    nm = str(row.get("name") or "").lower()
    # CASE-INSENSITIVE. The statement writes "Fixed Income" and the test read "Fixed income", so
    # every deposit, PPF and debt fund fell past its own branch to the raw-token fallback and the
    # page printed rows headed "gilt", "overnight" and "Fixed deposit" side by side.
    cls = {"equity": "Equity", "fixed income": "Fixed income",
           "alternates": "Alternates"}.get(str(cls).strip().lower(), cls)
    if cls == "Equity":
        if "direct equity" in s:
            return "Listed, held directly"
        if s.startswith("pms"):
            return "Discretionary mandates (PMS)"
        if s.startswith("aif") or "unlisted" in s:
            return "AIF and unlisted"
        return "Equity funds and ETFs"
    if cls == "Fixed income":
        if any(k in s for k in ("deposit", "ppf", "scss", "savings", "provident", "fixed depo")):
            return "Deposits and small savings"
        if any(k in s for k in ("bond", "ncd", "sdl", "g-sec", "t-bill", "perpetual")):
            return "Bonds and government paper"
        return "Debt funds"
    if cls == "Alternates":
        if "gold" in s or "gold" in nm or "silver" in s:
            return "Gold and silver"
        if "ulip" in s or "ulip" in nm:
            return "Insurance-linked"
        if "reit" in s or "invit" in s:
            return "REITs and InvITs"
        return "Other alternates"
    # NEVER A RAW TOKEN. A lowercase, underscored or unrecognised sub-category is an internal
    # field value, not a label, and it goes through the engine map or falls back to the class.
    key = s.strip()
    if key in _ENGINE_LABEL:
        return _ENGINE_LABEL[key]
    if not sub or sub == key and ("_" in key or key.islower()):
        return cls
    return sub


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eyebrow, title = LABELS.get(reg, LABELS["std"])
    grid, totals = _rows(ctx)
    if not grid:
        return 0
    grand = (ctx.get("totals") or {}).get("grand_inr") or sum(totals.values()) or 1.0

    s = deck.content(SECTION_NO, SECTION, eyebrow, title)
    deck.anchor("mod:rec_snapshot", s, prio=4)

    # ---- the columns this book actually carries ---------------------------------------------
    present = [c for c in CALL_ORDER if totals.get(c)]
    present += sorted(c for c in totals if c not in CALL_ORDER)
    # a pivot wider than six call columns stops being readable at this width; the rarest are
    # folded into one disclosed column rather than dropped
    folded = []
    if len(present) > 6:
        folded = sorted(present[6:], key=lambda c: -totals[c])
        present = present[:6]

    cols = [("Category", 0.29, "l")]
    for c in present:
        cols.append((c, 0.53 / (len(present) + (1 if folded else 0)), "r"))
    if folded:
        cols.append(("Other calls", 0.53 / (len(present) + 1), "r"))
    cols += [("Total", 0.10, "r"), ("% of book", 0.08, "r")]

    body, footed = [], 0.0
    for cls in CLASS_ORDER + sorted({k[0] for k in grid} - set(CLASS_ORDER)):
        keys = sorted((k for k in grid if k[0] == cls),
                      key=lambda k: -sum(grid[k].values()))
        for k in keys:
            vals = grid[k]
            tot = sum(vals.values())
            footed += tot
            row = [("b", k[1])]
            for c in present:
                row.append(_money(vals.get(c)))
            if folded:
                row.append(_money(sum(vals.get(c, 0.0) for c in folded)))
            row += [("b", _money(tot)), f"{tot / grand * 100:.2f}%"]
            body.append(row)

    # the foot: one row that has to match the cover
    frow = [("b", "TOTAL")]
    for c in present:
        frow.append(("b", _money(totals.get(c))))
    if folded:
        frow.append(("b", _money(sum(totals.get(c, 0.0) for c in folded))))
    frow += [("b", _money(footed)), ("b", f"{footed / grand * 100:.2f}%")]
    body.append(frow)

    rowh = max(0.22, min(0.34, 3.15 / max(1, len(body))))
    fs = 9 if rowh >= 0.28 else 8
    deck.table(s, ML, 1.94, UW, cols, body, rowh=rowh, fs=fs, hfs=7.5)

    # ---- what the plan does, in five figures a client repeats ------------------------------
    y = 1.94 + 0.33 + len(body) * rowh + 0.18
    _sell = totals.get("Sell", 0.0)
    _trim = sum(float(r.get("trim_value_inr") or 0.0)
                for r in (list(ctx.get("funds") or []) + list(ctx.get("equity") or []))
                if str(r.get("verdict") or r.get("rec") or "") == "Trim")
    _client = totals.get("Exit (client)", 0.0)
    _switch = totals.get("Switch", 0.0)
    _untouched = grand - _sell - _trim - _client - _switch
    tiles = [(_money(_sell + _trim + _client), "Freed by the plan",
              "sells, trims and your exits", INK),
             (_money(_sell), "The desk's own sells", "our call", SELL if _sell else NT2),
             (_money(_client) if _client else "-", "At your instruction",
              "not a call of ours", AMBER if _client else NT2),
             (f"{_untouched / grand * 100:.0f}%", "Left untouched",
              "held or retained", HOLD)]
    if y < 5.95:
        deck.kpi_strip(s, tiles, y=min(y, 5.6))

    # ---- the reconciliation, asserted -------------------------------------------------------
    _gap = grand - footed
    note = ("Every holding in the book appears in exactly one cell above and the Total row foots "
            "to Rs %s, the figure on the cover." % f"{grand:,.0f}")
    if abs(_gap) > 1.0:
        note = ("The Total row foots to Rs %s against a book of Rs %s, a difference of Rs %s. "
                "That difference is a defect in this page, not in the portfolio: tell the desk "
                "before this deck is used." % (f"{footed:,.0f}", f"{grand:,.0f}", f"{_gap:,.0f}"))
    if folded:
        note += (" The 'Other calls' column carries %s."
                 % ", ".join(folded))
    deck.source(s, note)
    return 1
