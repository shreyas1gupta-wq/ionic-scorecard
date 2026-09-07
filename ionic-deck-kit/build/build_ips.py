# -*- coding: utf-8 -*-
"""Generate the Investment Policy Statement for a book, from the profile and the holdings.

    from build_ips import compute, write_workbook
    rows = compute(holdings, profile="Aggressive")

MANDATORY INPUTS, and there are only three: the client's name, the risk profile, and the holdings.
Every band comes from the profile in ips_profiles.py; every current figure is computed from the book.

WHAT IT WILL NOT DO. A parameter that a holdings statement cannot support is reported as not
available, not estimated. Modified duration needs a duration per instrument and credit quality needs
a rating per issuer; neither is on a statement. An IPS that quietly guesses those is worse than one
that says it does not know, because the reader cannot tell the difference.
"""
import ips_profiles as P


def _pct(v, tot):
    return None if not tot else v / tot * 100.0


def _sub(h):
    return (h.get("risk_sub") or "").strip()


def _val(h):
    return float(h.get("value_inr") or 0.0)


def _is_direct(h):
    return _sub(h).startswith(P.DIRECT_SUBS_PREFIX)


def _is_satellite(h):
    return _sub(h) in P.SATELLITE_SUBS


def compute(holdings, profile="Aggressive"):
    """holdings: every position, each carrying value_inr, asset_class, risk_sub, days_to_cash,
    liq_priority and, for a fund, an amc. Returns a list of section dicts ready to render."""
    prof = P.PROFILES[profile]
    tot = sum(_val(h) for h in holdings)

    def share(pred):
        return _pct(sum(_val(h) for h in holdings if pred(h)), tot)

    def cls(name):
        return share(lambda h: (h.get("asset_class") or "").strip().lower() == name)

    # ---- portfolio level ------------------------------------------------------------------------
    eq_val = sum(_val(h) for h in holdings
                 if (h.get("asset_class") or "").strip().lower() == "equity")
    amc = {}
    for h in holdings:
        a = (h.get("amc") or "").strip()
        if a and a != "-":
            amc[a] = amc.get(a, 0.0) + _val(h)
    top_amc = max(amc.values()) if amc else None
    locked = share(lambda h: (h.get("days_to_cash") or 0) > 365)
    cash = share(lambda h: _sub(h) in P.CASH_SUBS)

    portfolio = [
        ("Equity", cls("equity")),
        ("Fixed Income", cls("fixed income")),
        ("Alternates", cls("alternates")),
        ("Cash and equivalents", cash),
        ("Allocation to a single AMC", _pct(top_amc, tot) if top_amc is not None else None),
        ("Locked-in products, over one year", locked),
    ]

    # ---- equity level, as a share of the EQUITY sleeve ------------------------------------------
    eqh = [h for h in holdings if (h.get("asset_class") or "").strip().lower() == "equity"]

    def eshare(pred):
        return _pct(sum(_val(h) for h in eqh if pred(h)), eq_val)

    # market cap is struck on the holdings whose cap is actually known, and the page says so: a
    # fund whose mandate does not fix a cap band cannot be forced into one.
    capped = [h for h in eqh if _sub(h) in P.LARGE_CAP_SUBS or _sub(h) in P.MIDSMALL_SUBS]
    cap_val = sum(_val(h) for h in capped)
    # A single listed SECURITY is a share the client owns directly, not a fund. Taking the largest
    # of everything made the biggest index ETF the answer and read 18% of the equity sleeve against
    # a 15% cap, which is a false breach: the cap exists for single-name risk.
    biggest_listed = max([_val(h) for h in eqh
                          if _sub(h).startswith("Direct Equity")] or [0.0])
    biggest_strategy = max([_val(h) for h in eqh if not _is_direct(h)] or [0.0])

    equity = [
        ("Core exposure", eshare(lambda h: not _is_satellite(h))),
        ("Satellite exposure", eshare(_is_satellite)),
        ("Pooled vehicles", eshare(lambda h: not _is_direct(h))),
        ("Direct holdings", eshare(_is_direct)),
        ("Large cap", _pct(sum(_val(h) for h in capped if _sub(h) in P.LARGE_CAP_SUBS), cap_val)),
        ("Mid and small cap", _pct(sum(_val(h) for h in capped if _sub(h) in P.MIDSMALL_SUBS),
                                   cap_val)),
        ("Thematic and sectoral", eshare(lambda h: _sub(h) in P.THEMATIC_SUBS)),
        ("Listed securities", eshare(lambda h: not _sub(h).startswith(P.UNLISTED_PREFIX))),
        ("Unlisted securities", eshare(lambda h: _sub(h).startswith(P.UNLISTED_PREFIX))),
        ("A single listed security", _pct(biggest_listed, eq_val)),
        ("International equity", eshare(lambda h: _sub(h) in P.INTERNATIONAL_SUBS)),
        ("A single strategy or scheme", _pct(biggest_strategy, eq_val)),
    ]

    # ---- fixed income, as a share of the FI sleeve ----------------------------------------------
    fih = [h for h in holdings if (h.get("asset_class") or "").strip().lower() == "fixed income"]
    fi_val = sum(_val(h) for h in fih)

    def fshare(pred):
        return _pct(sum(_val(h) for h in fih if pred(h)), fi_val)

    fixed_income = [
        ("AAA rated", fshare(lambda h: _sub(h) in P.AAA_SUBS)),
        ("AA rated", None),                  # needs a rating per issuer
        ("Below AA rated", fshare(lambda h: _sub(h) in P.BELOW_AA_SUBS)),
        ("Modified duration, years", None),  # needs a duration per instrument
        ("NCDs and structured notes",
         fshare(lambda h: _sub(h) in ("NCD - AA and below / unrated / market-linked",
                                      "Market Linked Debenture / Structured Note"))),
    ]

    alth = [h for h in holdings if (h.get("asset_class") or "").strip().lower() == "alternates"]
    alt_val = sum(_val(h) for h in alth)
    alternates = [("Gold", _pct(sum(_val(h) for h in alth
                                    if "Gold" in _sub(h) or "Silver" in _sub(h)), alt_val))]

    out = []
    for key, title, rows, base in (
            ("portfolio", "Portfolio level", portfolio, tot),
            ("equity", "Equity level, as a share of the equity sleeve", equity, eq_val),
            ("fixed_income", "Fixed income, as a share of the fixed-income sleeve",
             fixed_income, fi_val),
            ("alternates", "Alternates, as a share of the alternates sleeve", alternates, alt_val)):
        bands = prof[key]
        body = []
        for name, cur in rows:
            lo, hi = bands.get(name, (None, None))
            unit = " yrs" if "duration" in name.lower() else "%"
            body.append(dict(name=name, current=cur, lo=lo, hi=hi,
                             band=P.band_text(lo, hi, unit),
                             fit=P.fit(cur, lo, hi)))
        out.append(dict(key=key, title=title, base=base, rows=body))
    return dict(profile=profile, approved=prof["approved"], drawdown=prof["drawdown"],
                total=tot, sections=out)


def write_workbook(ips, path, client="Client", as_of=""):
    """The IPS as a workbook, in the shape the desk's own sheet uses."""
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "IPS"
    NAVY = "FF1B27A3"
    hdr = Font(bold=True, color="FFFFFFFF", name="Calibri", size=10)
    fill = PatternFill("solid", fgColor=NAVY)
    thin = Border(bottom=Side(style="thin", color="FFD9D9D9"))
    STATUS = {"Inside": "FFE0F2EA", "Above": "FFFBE3E0", "Below": "FFFBEFDC"}

    ws["A1"] = "Investment Policy Statement"
    ws["A1"].font = Font(bold=True, size=14, color=NAVY)
    ws["A2"] = "%s · %s profile · as of %s" % (client, ips["profile"], as_of)
    ws["A3"] = ips["drawdown"]
    ws["A4"] = ("Bands are the desk's own, approved." if ips["approved"] else
                "The bands for this profile are a DRAFT and need the desk's sign-off. The "
                "Aggressive profile is the approved one.")
    ws["A4"].font = Font(italic=True, size=9,
                         color=("FF6B7280" if ips["approved"] else "FF92400E"))
    ws["A5"] = ("A parameter a holdings statement cannot support is shown as not available. "
                "Nothing on this sheet is estimated.")
    ws["A5"].font = Font(italic=True, size=9, color="FF6B7280")

    r = 7
    for sec in ips["sections"]:
        ws.cell(r, 1, sec["title"]).font = Font(bold=True, size=11, color=NAVY)
        if sec["base"]:
            ws.cell(r, 4, "sleeve Rs %s" % format(round(sec["base"]), ",")).font = Font(
                italic=True, size=9, color="FF6B7280")
        r += 1
        for j, h in enumerate(("Parameter", "Ideal band", "Current", "Fit"), start=1):
            c = ws.cell(r, j, h)
            c.font = hdr
            c.fill = fill
            c.alignment = Alignment(horizontal="center" if j > 1 else "left")
        r += 1
        for row in sec["rows"]:
            ws.cell(r, 1, row["name"]).border = thin
            ws.cell(r, 2, row["band"]).alignment = Alignment(horizontal="center")
            if row["current"] is None:
                cc = ws.cell(r, 3, P.NOT_AVAILABLE)
                cc.font = Font(italic=True, size=9, color="FF6B7280")
                cc.alignment = Alignment(horizontal="center")
            else:
                unit = "" if "duration" in row["name"].lower() else "%"
                cc = ws.cell(r, 3, "%.1f%s" % (row["current"], unit))
                cc.alignment = Alignment(horizontal="center")
            fc = ws.cell(r, 4, row["fit"] or "-")
            fc.alignment = Alignment(horizontal="center")
            if row["fit"] in STATUS:
                fc.fill = PatternFill("solid", fgColor=STATUS[row["fit"]])
                fc.font = Font(bold=row["fit"] != "Inside", size=10)
            for j in (2, 3, 4):
                ws.cell(r, j).border = thin
            r += 1
        r += 1

    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 18
    ws.column_dimensions["C"].width = 30
    ws.column_dimensions["D"].width = 12
    ws.freeze_panes = "A7"
    wb.save(path)
    return path
