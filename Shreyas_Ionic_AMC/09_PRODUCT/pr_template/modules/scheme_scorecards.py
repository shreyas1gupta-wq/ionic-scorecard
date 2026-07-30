# -*- coding: utf-8 -*-
"""Annexure, per-scheme scorecards (F4): one slide per non-Hold fund with the full QFRA/SENTINEL
metric battery, firing flags, exit narrative vs exemplar, and an 'Our read' bias commentary.
Returns the count.

Principal correction 2026-07-25: the drawdown curve (and its _synth_nav reconstruction) is
removed; an 'Our read' commentary paragraph per scheme takes its place, built from
verdict/flags/structural_reason and the metric battery."""
from slidekit import INK, SLATE, SANS, SERIF, ML, UW, RX


_SEVERE = {"CLOSET_INDEX", "NEG_ALPHA", "DEEP_DD", "CAPACITY"}
_FLAB = {"CLOSET_INDEX": "INDEX HUG", "NEG_ALPHA": "TRAILS", "DOWN_CAP_HI": "DOWNSIDE",
         "WEAK_CONSIST": "WEAK 3-YR", "MANDATE_RIGIDITY": "RIGID", "REG_PLAN_DRAG": "COST DRAG",
         "DEEP_DD": "DEEP FALL", "CAPACITY": "TOO LARGE", "OVER_ALLOC": "OVERSIZED",
         "SUB_SCALE": "TINY FUND", "SHORT_RECORD": "NEW FUND"}
_FLAG_READ = {"CLOSET_INDEX": "closet indexing", "NEG_ALPHA": "negative net alpha",
              "DOWN_CAP_HI": "high down-capture", "WEAK_CONSIST": "weak 3-yr consistency",
              "MANDATE_RIGIDITY": "mandate rigidity", "REG_PLAN_DRAG": "Regular-plan cost drag",
              "DEEP_DD": "deep drawdown", "CAPACITY": "capacity strain",
              "OVER_ALLOC": "over-allocation", "SUB_SCALE": "sub-scale AUM",
              "SHORT_RECORD": "record under 4 years"}


def _scrub(t):
    """House style: no em-dashes in client-facing strings, even when the data carries them."""
    return (t or "").replace(", ", ", ").replace(", ", ", ").strip()


def _fmt(v, spec="{:.0f}"):
    """None-safe number formatting: prints 'n/a' instead of crashing or printing 'None' when a
    fund doesn't yet have a full NAV-derived risk battery. Also guards negative zero (2026-07-29:
    a real fund landed at alpha -0.03, which round()s to -0.0 and displays as the cosmetically
    broken-looking '-0.0%' -- snap to positive zero before formatting)."""
    if v is not None and round(v, 6) == 0:
        v = 0.0
    return spec.format(v) if v is not None else "n/a"


def _fmt_abs(v, spec="{:.1f}%"):
    return spec.format(abs(v)) if v is not None else "n/a"


def _flags(deck, s, x, y, flags):
    fx = x
    for fl in flags[:5]:
        deck.pill(s, fx, y, _FLAB.get(fl, fl[:10]), w=1.05,
                  kind="Sell" if fl in _SEVERE else "Trim")
        fx += 1.18


def _no_negzero(v):
    """Snap a value that rounds to 0.0 at 1dp back to positive zero (2026-07-29: a real fund's
    alpha of -0.03 round()ed to -0.0 and rendered as the cosmetically broken-looking '-0.0%' in
    an f-string, which _fmt()'s guard doesn't cover since these are formatted directly)."""
    return 0.0 if (v is not None and round(v, 1) == 0) else v


def _our_read(f, simple):
    """Bias + why, per scheme, from verdict/flags/structural_reason/metrics."""
    v = f["verdict"]
    dc, uc = f["down_capture"], f["up_capture"]
    a = _no_negzero(f["alpha_ann"])
    w1 = _no_negzero(f["worst_1y"])
    dd = f["max_dd"]
    flags = [_FLAG_READ.get(x, x.lower().replace("_", " ")) for x in (f.get("flags") or [])]
    # a Trim driven by scale/record is NOT a performance verdict — say so, never a cushion smear
    structural_trim = bool({"SHORT_RECORD", "SUB_SCALE"} & set(f.get("flags") or []))
    # a portfolio-construction call (consolidate index/passive/debt exposure) has no
    # independently-benchmarked alpha at all -- never format None as "+0.0%" or crash on it;
    # the real rationale lives in structural_reason, which the card already shows separately.
    if a is None:
        note = f.get("structural_reason", "")
        return (f"Our read is {v}, on portfolio construction rather than a performance call. "
                f"{note}" if note else f"Our read is {v}, on portfolio construction rather than a "
                f"performance call — see the rationale above.")
    if simple:
        base = {"Exit": (f"Our read: come out of this fund. It has lost to its benchmark "
                         f"({a:+.1f}% a year) and fell {_fmt_abs(dd)} at its worst."),
                "Switch": (f"Our read: move to a stronger fund in the same category. This one takes "
                           f"{_fmt(dc)}% of the market's falls but only {_fmt(uc)}% of its rises."),
                "Redeem-to-Direct": ("Our read: Switch to its Direct plan. Same fund, "
                                     "lower yearly cost."),
                "Trim": (("Our read: keep it, but smaller. It is a young fund with a small asset "
                          "base; the bigger, proven fund does the heavy lifting while this one "
                          "builds its record.") if structural_trim else
                         (f"Our read: reduce. Its worst year was {_fmt(w1, '{:+.1f}')}% and it falls "
                          f"almost as much as the market itself."))}
        t = base.get(v, f"Our read: {v}.")
        if flags:
            t += " Warning signs: " + ", ".join(flags) + "."
        return t
    lead = {"Exit": (f"Our read is Exit. The case for staying is gone: net alpha runs {a:+.1f}% p.a., "
                     f"down-capture is {_fmt(dc)}% against {_fmt(uc)}% up-capture, and the worst year "
                     f"printed {_fmt(w1, '{:+.1f}')}%."),
            "Switch": (f"Our read is Switch. A fund score of {f['qfra']}/100 (grade {f['merit']}) sits below the "
                       f"category exemplar: {_fmt(uc)}% up-capture does not pay for {_fmt(dc)}% "
                       f"down-capture, and net alpha runs {a:+.1f}% p.a."),
            "Redeem-to-Direct": (f"Our read is Redeem-to-Direct. The scheme itself passes "
                                 f"({a:+.1f}% net alpha p.a., {_fmt(dc)}% down-capture); the Regular "
                                 f"plan is the defect, so we move the same exposure to Direct "
                                 f"rather than exit."),
            "Trim": (("Our read is Trim, on scale and record, not results. The scheme is young "
                      "(under four years) on a sub-scale asset base, so it cannot yet carry a full "
                      "allocation; the position stays, smaller, while the record matures.")
                     if structural_trim else
                     (f"Our read is Trim. Down-capture of {_fmt(dc)}% with a {_fmt(w1, '{:+.1f}')}% worst "
                      f"year is not enough cushion for the current allocation; the position stays, "
                      f"smaller."))}
    t = lead.get(v, (f"Our read is {v}. Net alpha {a:+.1f}% p.a., down-capture {_fmt(dc)}%, "
                     f"worst year {_fmt(w1, '{:+.1f}')}%."))
    if flags:
        t += " Watch-outs: " + ", ".join(flags) + "."
    if dd is not None:
        t += f" Max drawdown on record: {dd:.1f}%."
    return t


def _card(deck, f, tier, idx):
    reg = tier.get("register", "std")
    s = deck.content(5, "Annexure", "Scheme scorecard", f["name"])
    deck.pill(s, RX - 1.7, 1.72, f["verdict"], w=1.7, kind=f["verdict"])

    deck.kpi_strip(s, [
        (f"{f['qfra']:.0f}" if f['qfra'] is not None else "-", "Fund score / 100"),
        (f["merit"] or "-", "Grade"),
        (_fmt(f['up_capture'], "{:.0f}%"), "Up-capture"),
        (_fmt(f['down_capture'], "{:.0f}%"), "Down-capture"),
        (_fmt(f['hit3y'], "{:.0f}%"), "3Y hit-rate"),
        (_fmt(f['alpha_ann'], "{:+.1f}%"), "Net alpha p.a."),
    ], y=1.95)

    # the risk battery (r2/info_ratio/max_dd/worst_1y/sortino/calmar) needs NAV history this
    # fund may not have yet; TER is always on file. If the whole battery is missing, drop that
    # part of the line rather than print a row of "n/a"s — TER still renders normally.
    risk_stats = [("r²", _fmt(f['r2'], "{:.2f}")), ("Info ratio", _fmt(f['info_ratio'], "{:.2f}")),
                  ("Max DD (3y)", _fmt(f['max_dd'], "{:.1f}%")), ("Worst 1-yr", _fmt(f['worst_1y'], "{:.1f}%")),
                  ("Sortino", _fmt(f['sortino'], "{:.2f}")), ("Calmar", _fmt(f['calmar'], "{:.2f}"))]
    risk_available = any(val != "n/a" for _, val in risk_stats)
    ter_clause = f"TER  {f['ter']:.2f}%"
    if risk_available:
        metrics = "      ·      ".join(f"{label}  {val}" for label, val in risk_stats) + f"      ·      {ter_clause}"
    else:
        metrics = ter_clause
    deck.txt(s, ML, 3.02, UW, 0.24, [(metrics, SANS, 9, INK, False)])
    caption = (f"Measured against {f.get('bench_label', 'its SEBI category benchmark')} "
               f"· all risk stats on the common 3-year window" if risk_available else
               f"Measured against {f.get('bench_label', 'its SEBI category benchmark')} "
               f"· full risk-stat battery not yet available for this scheme")
    deck.txt(s, ML, 3.34, UW, 0.16, [(caption, SANS, 7.5, SLATE, False, True)])
    _flags(deck, s, ML, 3.56, f.get("flags") or [])

    narr = _scrub(f.get("structural_reason"))
    if f.get("exemplar") and f["exemplar"] != "-":
        narr = (narr + " ").strip() + f"  Measured against exemplar: {f['exemplar']}."
    kind = "warn" if f["verdict"] in ("Exit", "Switch") else "human"
    read = _our_read(f, reg == "simple")
    # panel heights hug the longer text (shared so the pair stays aligned) — fixed
    # worst-case boxes rendered 40-60% empty tint on short copy
    h = max(deck.callout_h(5.35, narr or "Rationale on file.", min_h=1.3),
            deck.callout_h(UW - 5.55, read, min_h=1.3))
    deck.callout(s, ML, 3.9, 5.35, h, "Why we act", narr or "Rationale on file.", kind)
    deck.callout(s, ML + 5.55, 3.9, UW - 5.55, h, "Our read", read, "note")

    deck.source(s, "Direct-plan NAV vs the scheme's own SEBI category benchmark (TRI), point-in-time · "
                   "risk stats on the common 3y window · Ionic fund-quality framework.")


def render(deck, ctx, tier):
    # index/passive (and any factor) funds get no per-scheme analysis page (Principal
    # 2026-07-28, permanent): an index fund's Sell/Hold call is a portfolio-construction
    # decision, not a performance finding -- there's no vs-benchmark alpha/down-capture
    # battery to show, and giving it a full scorecard page implies an analysis that was
    # never run (the underlying data is already None post the 2026-07-28 data fix).
    funds = [f for f in ctx["funds"] if f.get("verdict") != "Hold" and f.get("category") != "passive"]
    for i, f in enumerate(funds):
        _card(deck, f, tier, i)
    return len(funds)
