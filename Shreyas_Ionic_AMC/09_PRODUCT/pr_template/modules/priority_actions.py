# -*- coding: utf-8 -*-
"""priority_actions (Section 04, Recommendations, v8 #29). THE LAST CORE SLIDE.
Numbered action list (sell programme, trim, fund switches, redeploy) with amounts, read from
ctx cost/tax/deployment/totals/equity/funds. Closes on the NDPMS authorisation line."""
from slidekit import NAVY, GOLD, INK, SLATE, NT2, WHITE, SERIF, SANS, ML, UW, RX, HAIR, AMBER, AMBERBG
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

SECTION_NO, SECTION = 4, "Recommendations"


def _first_clause(s, n=70):
    """The first clause of a written reason, lower-cased to run on inside a sentence."""
    s = " ".join(str(s or "").split())
    if not s:
        return "term-locked"
    # The shortest complete clause the sentence offers, wherever its boundary falls. Bounding the
    # SEARCH to n characters and then cutting at n produced half-clauses on any reason whose first
    # full stop sat past the bound: "surrender terms depend on the premium against the sum assured
    # and on" -- a sentence that stops at "and on" reads as a rendering fault, not as a reason.
    cuts = [s.find(x) for x in (". ", "; ", ": ", ", ") if s.find(x) > 12]
    if cuts:
        s = s[:min(cuts)]
    if len(s) > n:
        s = s[:n].rsplit(" ", 1)[0].rstrip(" ,;:") + "..."
    return s[0].lower() + s[1:] if s else s


def _money(v):
    if isinstance(v, str):
        return v
    # None means the figure could not be computed from what the statement carries, which is not the
    # same statement as "nothing". Printing Rs 0.0 L for an unknown is how this page came to show
    # "Rs 0.0 L gross freed" three lines above Rs 96.29 Cr of fund actions on the same page.
    if v is None:
        return "Not estimated"
    return f"Rs {v/1e7:.2f} Cr" if abs(v) >= 1e7 else f"Rs {v/1e5:.1f} L"


# canonical action order + per-register nouns (mix text is built from the ACTUAL actions —
# a hardcoded 'switches / redeem-to-Direct / exit' went stale the day the book changed)
_ACT_ORDER = ["SWITCH", "REDEEM", "EXIT", "SELL", "TRIM"]
_ACT_NOUN = {"SWITCH": ("switch", "switches"), "REDEEM": ("redeem-to-Direct", "redeems-to-Direct"),
             "EXIT": ("exit", "exits"), "SELL": ("full exit", "full exits"),
             "TRIM": ("trim", "trims")}


def _act_code(f):
    """One of _ACT_ORDER, from whatever the data layer spells the action as.

    The demo data layer writes codes ("SWITCH", "REDEEM"); the statement pipeline writes a
    sentence ("Sell in full", "Trim to 10% of the portfolio"). Keying the counter on the raw
    string meant the sentence form matched none of the four codes, so the mix text came out
    empty and the page read "Fund actions ; every destination is a Direct-plan or passive
    vehicle." with a leading semicolon and no actions named."""
    a = str(f.get("action") or "").strip().upper()
    for code in _ACT_ORDER:
        if a.startswith(code):
            return code
    if a.startswith("SELL"):
        return "SELL"
    v = str(f.get("verdict") or "").strip().upper()
    return "SELL" if v == "SELL" else "TRIM" if v == "TRIM" else "SWITCH"


def _mix(act_counts):
    parts = []
    for a in _ACT_ORDER:
        n = act_counts.get(a, 0)
        if n:
            parts.append(f"{n} {_ACT_NOUN[a][0 if n == 1 else 1]}")
    return ", ".join(parts)


def _fund_desc(act_counts):
    """A destination clause belongs only to an action that HAS a destination. A full exit and a
    trim send money to cash, so promising "every destination is a Direct-plan or passive vehicle"
    beside them described a plan the deck was not recommending."""
    mix = _mix(act_counts)
    moved = sum(act_counts.get(a, 0) for a in ("SWITCH", "REDEEM"))
    if not mix:
        return "No change to the fund book this cycle."
    if moved:
        return f"{mix}; every switch or redemption lands in a Direct-plan or passive vehicle."
    return f"{mix}; the proceeds go to cash, not to a replacement scheme."


def _rows(reg, n_sell, k, act_counts, n_quality_sell, n_liquidity_sell, trim_reason,
          sell_noun="holdings"):
    n_exit = act_counts.get("EXIT", 0)
    n_move = k - n_exit
    sell_desc_hni = (f"{n_sell} names sold, {n_quality_sell} score below the gate; "
                      f"{n_liquidity_sell} are directed liquidity exits, not a quality call."
                      if n_liquidity_sell else
                      f"{n_sell} names scored below the gate, staged in slices at <=10% ADV.")
    if reg == "simple":
        # THE PLAIN-LANGUAGE REGISTER WAS NEVER SWEPT when the other two were, and it drifted
        # further than either. "Replace N weak funds with stronger, cheaper ones" promises the
        # client a REPLACEMENT this deck does not recommend and is not allowed to: the review is
        # Sell, Trim and Hold on what is already owned, no client Buy is ever issued, and the
        # proceeds here go to cash pending a separate conversation. Saying it in simpler words does
        # not make it a smaller claim; it makes it a likelier one to be believed.
        _moved = sum(act_counts.get(a, 0) for a in ("SWITCH", "REDEEM"))
        if _moved:
            fund_sub = (f"Move {_moved} fund" + ("" if _moved == 1 else "s") +
                        " into a cheaper version of the same kind")
            _rest = k - _moved
            fund_sub += (f", and sell {_rest} outright." if _rest else ".")
        else:
            fund_sub = (f"Sell {k} fund" + ("" if k == 1 else "s") +
                        " and hold the money as cash; what to buy is a separate conversation.")
        # "stocks" on a book whose every Sell is a FUND. The word has to follow the holding, and
        # the caller resolves it because _rows() cannot see the book.
        _noun = sell_noun
        sell_sub = (f"Sell the {n_sell} weakest-scoring {_noun}; {n_liquidity_sell} more are sold just "
                    "for cash, not because they're weak."
                    if n_liquidity_sell else
                    f"Sell the {n_sell} weakest-scoring {_noun}, a little at a time.")
        return [
            ("Sell the weak names", sell_sub, "First"),
            ("Free up cash", trim_reason, "Soon"),
            ("Fix the funds", fund_sub, "A few days"),
            ("Keep the cash ready", "The freed money sits safely in a liquid fund; where it goes next is decided with you, separately.", "Together"),
        ]
    return [
        ("Sell programme", sell_desc_hni, "Wave 1"),
        ("Trim / liquidity", trim_reason, "This cycle"),
        ("Fund actions", _fund_desc(act_counts), "T+2–T+3"),
        ("Park net proceeds", "Held in liquid / overnight funds pending your goals and IPS discussion; no redeployment is assumed or recommended here.", "On authorisation"),
    ]


LABELS = {
    "hni": {"eyebrow": "Your priority actions", "title": "What we'd do next · in order, with amounts",
            "k1": "Gross freed", "k1s": "sells + trim", "k2": "Fund actions", "k2s": "switch / redeem / exit",
            "k3": "Net proceeds", "k3s": "to cash, after est. tax",
            "auth": "Nothing executes until you authorise it, this is a Non-Discretionary (NDPMS) mandate."},
    "std": {"eyebrow": "Your priority actions", "title": "What we'd do next · in order, with amounts",
            "k1": "Gross freed", "k1s": "sells + trim", "k2": "Fund actions", "k2s": "switch / redeem / exit",
            "k3": "Net proceeds", "k3s": "to cash, after est. tax",
            "auth": "Nothing executes until you authorise it, this is a Non-Discretionary (NDPMS) mandate."},
    "simple": {"eyebrow": "What happens next", "title": "Your action plan, step by step",
               "k1": "Cash freed", "k1s": "from sells + trim", "k2": "Fund changes", "k2s": "switch / move / drop",
               "k3": "Cash in hand", "k3s": "after estimated tax",
               "auth": "Nothing happens without your approval; every step is yours to confirm."},
}


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    L = LABELS.get(reg, LABELS["std"])
    t = ctx["totals"]
    dep, funds, equity = ctx["deployment"], ctx["funds"], ctx["equity"]
    proceeds, net = dep["proceeds_inr"], dep["net_inr"]
    # With no acquisition dates there is no tax estimate, so there is no NET. Show the gross and
    # label it gross, rather than printing a gross number under a "net of tax" heading.
    _net_known = net is not None
    net_shown = net if _net_known else proceeds
    # Every holding, not the direct-share sleeve alone. On a book whose Sells and Trim are all
    # funds this summed to nothing and printed Rs 0.0 L against a live sell programme.
    _book = list(equity) + list(funds) + list(ctx.get("other") or [])

    def _call(h):
        return str(h.get("rec") or h.get("verdict") or "").strip()

    sell_sum = sum(h.get("value_inr") or 0 for h in _book if _call(h) == "Sell")
    # real trim cash = money actually coming off over-cap Hold names, reduced toward the
    # single-name cap -- NOT "whatever proceeds are left over once sells are subtracted"
    # (that residual silently included fund-exit money whenever a book has zero Trim-rec
    # equities, e.g. Client B 2026-07-27: showed fund-exit cash against a stock-trim
    # action label, wrongly implying HDFCBANK/TCS trims were worth the fund-exit amount)
    cap = (ctx.get("ips") or {}).get("single_name_cap_pct") or 0.0
    grand = t["grand_inr"]
    # Where the scoring engine has already sized the trim, use ITS number: it is the slice above
    # the cap and it is what the fund book, the tax page and this page must all agree on. Fall
    # back to the cap arithmetic only for a holding the engine did not size.
    def _trim_amt(h):
        v = h.get("trim_value_inr")
        if v:
            return float(v)
        w = h.get("weight_pct") or 0
        return (w - cap) / 100 * grand if w > cap else 0.0

    trim_cash = round(sum(_trim_amt(h) for h in _book
                          if _call(h) != "Sell" and (_trim_amt(h) > 0 or _call(h) == "Trim")))
    # THE DESK'S OWN FUND ACTIONS. A client-directed exit and a Retain are actions on the book,
    # but they are not calls this firm made, and counting them here would put the firm's name on
    # them; leaving them out of the page altogether -- which is what happened -- hid the largest
    # single movement of money in the plan. They get their own numbered row below instead.
    _CLIENT_ACTS = ("EXIT (CLIENT)", "RETAIN")
    fund_acts = [f for f in funds
                 if str(f.get("action") or "").strip().upper() not in ("HOLD",) + _CLIENT_ACTS]
    k = len(fund_acts)
    act_counts = {}
    for f in fund_acts:
        act_counts[_act_code(f)] = act_counts.get(_act_code(f), 0) + 1
    # KPI sub-label mirrors the actions actually present, register-appropriate nouns
    _sub_noun = ({"SWITCH": "switch", "REDEEM": "move", "EXIT": "drop", "SELL": "sell",
                  "TRIM": "trim"}
                 if reg == "simple" else
                 {"SWITCH": "switch", "REDEEM": "redeem", "EXIT": "exit", "SELL": "sell",
                  "TRIM": "trim"})
    L = dict(L)
    # .get, not [a]: an action code with no noun here raised, and engine.build swallows a module
    # exception, so the whole priority-actions page left the deck with nothing said about it.
    L["k2s"] = " / ".join(_sub_noun[a] for a in _ACT_ORDER
                          if act_counts.get(a) and a in _sub_noun)
    # displayed as the sum of the ROUNDED per-fund amounts so it matches the tax-slide
    # total digit-for-digit (independent rounding printed 82.1 here vs 82.2 there)
    # A trim moves the slice above the cap, not the position. Pricing the whole position here put
    # 100% of a trim-only holding into a line the reader reads as money coming off the table.
    fund_sum = round(sum(round((_trim_amt(f) if _act_code(f) == "TRIM" else f["value_inr"]) / 1e5, 1)
                         for f in fund_acts), 1) * 1e5
    n_sell = t["n_sell"]
    n_liquidity_sell = sum(1 for e in equity if e["rec"] == "Sell" and e.get("sell_reason_type") == "liquidity")
    n_quality_sell = n_sell - n_liquidity_sell
    # equity-only here read "nothing to trim" beside Rs 23.04 Cr of trim cash, because the one
    # position over the cap was a fund.
    trim_names = [h for h in _book if _call(h) == "Trim"]
    if trim_names and any((e["weight_pct"] or 0) > cap for e in trim_names):
        trim_reason = (f"Positions above the {cap:.0f}% single-name cap eased back toward it, into strength.")
    elif trim_names:
        trim_reason = (f"{trim_names[0]['name'].title()} trimmed for a directed cash need, not a "
                       f"concentration or quality concern; no position here is above the {cap:.0f}% cap.")
    else:
        trim_reason = f"No position in this book exceeds the {cap:.0f}% single-name cap; nothing to trim."

    s = deck.content(SECTION_NO, SECTION, L["eyebrow"], L["title"])

    # WHAT "GROSS FREED" MEANS ON THIS BOOK. proceeds is the desk's own sells and trims; where
    # the client has directed exits as well, the money actually coming off the table is both, and
    # printing only the desk's half beside four rows that add to the whole is how this page came
    # to headline Rs 45.4 L over a Rs 3.37 Cr programme.
    _CD = ctx.get("client_directive") or {}
    _v_client = _CD.get("exit_value_inr") or 0.0
    _gross_all = (proceeds or 0.0) + _v_client
    _k1s = (L["k1s"] if not _v_client else
            ("sells, trims and your exits" if reg != "simple" else "everything being sold"))
    deck.kpi_strip(s, [
        (_money(_gross_all), L["k1"], _k1s, INK),
        (str(k), L["k2"], L["k2s"] or "desk calls", NT2),
        (_money(net_shown if _net_known else _gross_all),
         L["k3"] if _net_known else "Gross proceeds",
         L["k3s"] if _net_known else "before tax", NAVY),
    ], y=1.8)

    # Rows 1 and 2 price the sells and the trims wherever they sit, funds included. Where the fund
    # actions ARE those same sells and trims, printing the fund total again gives a reader a column
    # that appears to add to twice the money actually moving.
    _fund_ids = {id(f) for f in fund_acts}
    _already = sum((_trim_amt(h) if _call(h) == "Trim" else (h.get("value_inr") or 0))
                   for h in _book if id(h) in _fund_ids and _call(h) in ("Sell", "Trim"))
    fund_shown = fund_sum if fund_sum - _already > 1e4 else "Included in 1 and 2"
    amounts = [sell_sum, trim_cash, fund_shown, net_shown]
    _nf_sell = sum(1 for f in funds if str(f.get("verdict") or "").strip() == "Sell")
    _ne_sell = sum(1 for e in equity if str(e.get("rec") or "").strip() == "Sell")
    _sell_noun = ("funds" if _nf_sell and not _ne_sell else
                  "shares" if _ne_sell and not _nf_sell else "holdings")
    rows = _rows(reg, n_sell, k, act_counts, n_quality_sell, n_liquidity_sell, trim_reason,
                 sell_noun=_sell_noun)
    # v7 device (p.29): every action row carries a REF back to the page that justifies it
    refs = ["tbl:sell_list", "mod:concentration", "mod:fund_actions", "mod:tax_impact"]

    # THE CLIENT'S OWN INSTRUCTION, FIRST AND IN WORDS. On this book it was Rs 2.74 crore, a
    # quarter of the portfolio, and this page -- the page the client signs -- did not mention it.
    CD = ctx.get("client_directive") or {}
    if CD.get("exits"):
        _n_ce, _v_ce = len(CD["exits"]), CD.get("exit_value_inr") or 0.0
        _sleeves = []
        for _d in CD["exits"]:
            _a = (_d.get("asset_class") or "").strip()
            if _a and _a not in _sleeves:
                _sleeves.append(_a)
        _where = " and ".join(x.lower() for x in _sleeves) if _sleeves else "these holdings"
        _sub = ("%d holdings in the %s sleeve, on your instruction, not on a view of ours."
                % (_n_ce, _where))
        if reg == "simple":
            # THE PLAIN REGISTER HAS LESS ROOM, NOT MORE. Repeating the instruction verbatim here
            # overran the row by 0.31in and landed on the row below it. The instruction is on the
            # mandate page in full; this row says what is happening and why.
            _sub = ("%d holdings, because you asked us to, not because we think they are weak."
                    % _n_ce)
        # THE HOLDINGS THAT CANNOT GO, with the reason each carries. Three of them appeared in the
        # annexure as a bare word, "Retain", with the fund-coverage boilerplate against them in the
        # workbook: neither the right sentence nor, as an explanation of why a holding is kept, a
        # true one.
        if CD.get("retains"):
            # NAMED HERE, REASONED IN THE NOTES. Three written reasons do not fit the two lines
            # this row is laid into -- they overflowed it by 0.28in and landed on the row below --
            # so the row names them and the coverage notes carry the reason for each in full.
            _sub += ((" %d cannot be redeemed on request." % len(CD["retains"])) if reg == "simple"
                     else (" %d cannot be redeemed on request; the reason for each is in the "
                           "coverage notes." % len(CD["retains"])))
        rows = [("At your instruction: exit the fixed-income sleeve"
                 if reg != "simple" else "The change you asked for", _sub,
                 "On authorisation")] + rows
        amounts = [_v_ce] + amounts
        refs = ["mod:tax_impact"] + refs
        if len(rows) > 5:            # keep the page to five numbered rows
            rows, amounts, refs = rows[:5], amounts[:5], refs[:5]
    # A FIVE-ROW PAGE NEEDS THE HEIGHT ITS ROWS ASK FOR. At a 0.62in pitch the client-instruction
    # row, which carries the longest sub-line on the page, ran into the Sell-programme row beneath
    # it. The rows start higher and the pitch is set from the count.
    ry0, rowh = (2.98, 0.78) if len(rows) <= 4 else (2.74, 0.66)
    for i, ((title, sub, when), amt) in enumerate(zip(rows, amounts)):
        ry = ry0 + i * rowh
        deck.oval(s, ML, ry + 0.04, 0.42, NAVY)
        deck.txt(s, ML, ry + 0.04, 0.42, 0.42, [(str(i + 1), SANS, 14, WHITE, True)],
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        deck.txt(s, ML + 0.62, ry, 8.0, 0.3, [(title, SANS, 13, INK, True)])
        # the sub-line takes whatever the row's own pitch leaves it, rather than a fixed 0.34in
        # that a five-row page cannot honour
        deck.txt(s, ML + 0.62, ry + 0.31, 8.0, max(0.30, rowh - 0.36),
                 [(sub, SERIF, 9.5 if rowh >= 0.72 else 9, SLATE, False, True)], ls=1.02)
        deck.txt(s, RX - 2.55, ry + 0.02, 2.55, 0.3, [(_money(amt), SANS, 15, GOLD, True)],
                 align=PP_ALIGN.RIGHT)
        deck.txt(s, RX - 2.55, ry + 0.42, 2.55, 0.22, [(when.upper(), SANS, 7.5, SLATE, True, False, 60)],
                 align=PP_ALIGN.RIGHT)
        if reg != "simple":
            deck.pageref(s, ML - 0.04, ry + 0.50, refs[i], w=0.62, align=PP_ALIGN.CENTER)
        deck.rule(s, ML, ry + rowh - 0.06, UW, HAIR, 0.006)

    # authorisation band, with the signature blank beside it (v7 p.29: the deck gets signed)
    bw = UW - 3.95
    deck.rect(s, ML, 6.1, bw, 0.46, fill=AMBERBG, round_=0.06)
    # BRAND: no coloured edge-stripe on a card. The guidelines prohibit it and it was on every panel in this template. The panel's own fill and the pill carry the colour.
    deck.txt(s, ML + 0.22, 6.1, bw - 0.4, 0.46,
             [("AUTHORISATION   ", SANS, 8.5, AMBER, True, False, 60), (L["auth"], SERIF, 9.5, INK, False)],
             anchor=MSO_ANCHOR.MIDDLE, ls=1.0)
    deck.txt(s, RX - 3.75, 6.1, 3.75, 0.46,
             [("Reviewed with client on  ____________________", SANS, 8, SLATE, False)],
             align=PP_ALIGN.RIGHT, anchor=MSO_ANCHOR.MIDDLE)
    demo_tag = "Amounts illustrative for the AZBY demo · " if ctx.get("is_demo", False) else ""
    # THE OLD FOOTNOTE FLATLY CONTRADICTED THE PAGE BEFORE IT. It said the tax could not be
    # estimated, on a deck carrying a tax page that estimates it holding by holding. It is true
    # only of a book with no cost basis at all, so it is now said only when that is the case.
    _has_basis = any(h.get("cost_inr") for h in _book)
    _net_note = ("Net figures after estimated tax" if net is not None else
                 "Amounts are before tax; the estimated tax on each move is set out on the tax page"
                 if _has_basis else
                 "Amounts are before tax: this statement carries no acquisition cost, so the tax "
                 "on these sales cannot be estimated from it")
    deck.source(s, f"{demo_tag}{_net_note} · as of {ctx['client']['as_of']}.")
    return 1
