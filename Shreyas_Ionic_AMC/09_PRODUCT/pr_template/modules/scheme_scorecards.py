# -*- coding: utf-8 -*-
"""Annexure, per-scheme scorecards (F4): one slide per non-Hold fund with the full QFRA/SENTINEL
metric battery, firing flags, exit narrative vs exemplar, and an 'Our read' bias commentary.
Returns the count.

Principal correction 2026-07-25: the drawdown curve (and its _synth_nav reconstruction) is
removed; an 'Our read' commentary paragraph per scheme takes its place, built from
verdict/flags/structural_reason and the metric battery."""
from slidekit import INK, SLATE, SANS, SERIF, ML, UW, RX


_SEVERE = {"CLOSET_INDEX", "NEG_ALPHA", "DEEP_DD", "CAPACITY"}
_FLAB = {"CLOSET_INDEX": "CLOSET-IDX", "NEG_ALPHA": "NEG ALPHA", "DOWN_CAP_HI": "DOWN-CAP",
         "WEAK_CONSIST": "WEAK 3Y", "MANDATE_RIGIDITY": "MANDATE", "REG_PLAN_DRAG": "REG DRAG",
         "DEEP_DD": "DEEP DD", "CAPACITY": "CAPACITY", "OVER_ALLOC": "OVER-ALLOC"}
_FLAG_READ = {"CLOSET_INDEX": "closet indexing", "NEG_ALPHA": "negative net alpha",
              "DOWN_CAP_HI": "high down-capture", "WEAK_CONSIST": "weak 3-yr consistency",
              "MANDATE_RIGIDITY": "mandate rigidity", "REG_PLAN_DRAG": "Regular-plan cost drag",
              "DEEP_DD": "deep drawdown", "CAPACITY": "capacity strain",
              "OVER_ALLOC": "over-allocation"}


def _scrub(t):
    """House style: no em-dashes in client-facing strings, even when the data carries them."""
    return (t or "").replace(", ", ", ").replace(", ", ", ").strip()


def _flags(deck, s, x, y, flags):
    fx = x
    for fl in flags[:5]:
        deck.pill(s, fx, y, _FLAB.get(fl, fl[:10]), w=1.05,
                  kind="Sell" if fl in _SEVERE else "Trim")
        fx += 1.18


def _our_read(f, simple):
    """Bias + why, per scheme, from verdict/flags/structural_reason/metrics."""
    v = f["verdict"]
    dc, uc = f["down_capture"], f["up_capture"]
    a, w1, dd = f["alpha_ann"], f["worst_1y"], f["max_dd"]
    flags = [_FLAG_READ.get(x, x.lower().replace("_", " ")) for x in (f.get("flags") or [])]
    if simple:
        base = {"Exit": (f"Our read: come out of this fund. It has lost to its benchmark "
                         f"({a:+.1f}% a year) and fell {abs(dd):.1f}% at its worst."),
                "Switch": (f"Our read: move to a stronger fund in the same category. This one takes "
                           f"{dc:.0f}% of the market's falls but only {uc:.0f}% of its rises."),
                "Redeem-to-Direct": ("Our read: keep the fund, switch to its Direct plan. Same fund, "
                                     "lower yearly cost."),
                "Trim": (f"Our read: reduce. Its worst year was {w1:+.1f}% and it falls almost as "
                         f"much as the market itself.")}
        t = base.get(v, f"Our read: {v}.")
        if flags:
            t += " Warning signs: " + ", ".join(flags) + "."
        return t
    lead = {"Exit": (f"Our read is Exit. The case for staying is gone: net alpha runs {a:+.1f}% p.a., "
                     f"down-capture is {dc:.0f}% against {uc:.0f}% up-capture, and the worst year "
                     f"printed {w1:+.1f}%."),
            "Switch": (f"Our read is Switch. QFRA {f['qfra']}/100 ({f['merit']}) sits below the "
                       f"category exemplar: {uc:.0f}% up-capture does not pay for {dc:.0f}% "
                       f"down-capture, and net alpha runs {a:+.1f}% p.a."),
            "Redeem-to-Direct": (f"Our read is Redeem-to-Direct. The scheme itself passes "
                                 f"({a:+.1f}% net alpha p.a., {dc:.0f}% down-capture); the Regular "
                                 f"plan is the defect, so we move the same exposure to Direct "
                                 f"rather than exit."),
            "Trim": (f"Our read is Trim. Down-capture of {dc:.0f}% with a {w1:+.1f}% worst year is "
                     f"not enough cushion for the current allocation; the position stays, smaller.")}
    t = lead.get(v, (f"Our read is {v}. Net alpha {a:+.1f}% p.a., down-capture {dc:.0f}%, "
                     f"worst year {w1:+.1f}%."))
    if flags:
        t += " SENTINEL flags firing: " + ", ".join(flags) + "."
    t += f" Max drawdown on record: {dd:.1f}%."
    return t


def _card(deck, f, tier, idx):
    reg = tier.get("register", "std")
    s = deck.content(5, "Annexure", "Scheme scorecard", f["name"])
    deck.pill(s, RX - 1.7, 1.72, f["verdict"], w=1.7, kind=f["verdict"])

    deck.kpi_strip(s, [
        (f"{f['qfra']}", "QFRA / 100"),
        (f["merit"], "MERIT grade"),
        (f"{f['up_capture']:.0f}%", "Up-capture"),
        (f"{f['down_capture']:.0f}%", "Down-capture"),
        (f"{f['hit3y']:.0f}%", "3Y hit-rate"),
        (f"{f['alpha_ann']:+.1f}%", "Net alpha p.a."),
    ], y=1.95)

    metrics = (f"r²  {f['r2']:.2f}      ·      Info ratio  {f['info_ratio']:.2f}      ·      "
               f"Max DD  {f['max_dd']:.1f}%      ·      Worst 1-yr  {f['worst_1y']:.1f}%      ·      "
               f"Sortino  {f['sortino']:.2f}      ·      Calmar  {f['calmar']:.2f}      ·      "
               f"TER  {f['ter']:.2f}%")
    deck.txt(s, ML, 3.02, UW, 0.24, [(metrics, SANS, 9, INK, False)])
    _flags(deck, s, ML, 3.38, f.get("flags") or [])

    narr = _scrub(f.get("structural_reason"))
    if f.get("exemplar") and f["exemplar"] != "-":
        narr = (narr + " ").strip() + f"  Measured against exemplar: {f['exemplar']}."
    kind = "warn" if f["verdict"] in ("Exit", "Switch") else "human"
    deck.callout(s, ML, 3.9, 5.35, 2.4, "Why we act", narr or "Rationale on file.", kind)
    deck.callout(s, ML + 5.55, 3.9, UW - 5.55, 2.4, "Our read",
                 _our_read(f, reg == "simple"), "note")

    deck.source(s, "Direct-plan NAV vs total-return benchmark, point-in-time. QFRA 2.0 / SENTINEL.")


def render(deck, ctx, tier):
    funds = [f for f in ctx["funds"] if f.get("verdict") != "Hold"]
    for i, f in enumerate(funds):
        _card(deck, f, tier, i)
    return len(funds)
