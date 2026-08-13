# -*- coding: utf-8 -*-
"""core_satellite (Portfolio X-ray, core) -- Principal ruling 2026-08-06 (#1): a guidance read of
the book's construction, core vs satellite, NOT an IPS breach test. His words: "it was for broad
direction/idea, keep midcap in core." The category map and the ~70/30 split are both his, and both
explicitly flexible:

  Core      = index, large cap, mid cap, flexi, multi, hybrid, debt, gold
  Satellite = sectoral/thematic, small cap, international, factor/smart-beta, contra

This is a CURRENT-POSITION READ against that guidance -- a plain two-segment bar with the target
shown as a reference tick, plus a breakdown of which holdings actually sit where. It deliberately
does NOT reuse ips_summary.py's Aligned/Gap pill device: there is no pass/fail here, by design.
"""
import os

from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from slidekit import NAVY, GOLD, INK, SLATE, WHITE, SERIF, SANS, ML, UW

_LIB_CS = None          # cached; the path load is done once per build, not per fund


def _load_lib_classify():
    """`lib/core_satellite.py`'s classify(), loaded by absolute path.

    Both that file and this one are called core_satellite.py, so importing by NAME is ambiguous and
    can resolve to this module itself depending on sys.path order. Returns None if the lib is absent,
    and the caller falls back to the local sets."""
    global _LIB_CS
    if _LIB_CS is None:
        import importlib.util
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "lib", "core_satellite.py")
        if not os.path.exists(p):
            return None
        spec = importlib.util.spec_from_file_location("_lib_core_satellite", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _LIB_CS = mod
    return getattr(_LIB_CS, "classify", None)

TARGET_CORE_PCT = 70.0  # Principal's stated target -- "flexible", a guidance marker, not a cap

# Fund-category buckets, exactly as the Principal named them (mirrors lib/mf_sell_score's parallel
# CORE_CATEGORIES/SATELLITE_CATEGORIES -- reconciled 2026-08-06 after that concurrent build found
# this set had no explicit "mid" entry and was landing midcap at Core only via its catch-all
# default, same OUTCOME but a more fragile MECHANISM than an explicit membership check. Fixed here
# to check membership explicitly, same as that file, rather than relying on a silent default).
_CORE_FUND_CATS = {"passive", "index", "large", "largemid", "mid", "flexi", "multi", "multicap",
                   "hybrid", "conservative_hybrid", "debt", "gilt", "debt_short", "overnight",
                   "gold", "elss", "value", "dividend_yield", "focused"}
_SATELLITE_FUND_CATS = {"thematic_mnc", "thematic", "sectoral", "small", "international",
                        "global", "factor", "smart_beta", "momentum_factor", "contra"}
# azby's (and most intake files') generic "equity" category folds large/flexi/multi/small cap into
# one label -- only a name/benchmark keyword tells small cap or a thematic mandate apart from the
# rest of it. [INFERENCE], disclosed on the page: a real client's ACE-matched fund carries its own
# finer category and never needs this heuristic.
_SMALLCAP_KW = ("small cap", "smallcap", "small-cap")
_THEMATIC_KW = ("thematic", "opportunities fund", "digital", "esg fund", "infrastructure fund",
               "psu ", "banking and financial", "consumption fund", "pharma fund", "technology fund")


def _fund_bucket(f):
    cat = (f.get("category") or "").lower()
    name = (f.get("name") or "").lower()
    bench = (f.get("bench_label") or "").lower()
    if cat == "equity":
        if any(k in name for k in _SMALLCAP_KW) or "smallcap" in bench:
            return "Satellite"
        if any(k in name for k in _THEMATIC_KW):
            return "Satellite"
        return "Core"
    # SINGLE SOURCE OF TRUTH. `lib/core_satellite.py` owns the fund-category classification; this
    # module owns only the PRESENTATION and the direct-equity reading (which the lib has no view on,
    # because a stock has no fund category). Two concurrent passes on 2026-08-06 each wrote their own
    # copy of the category sets; they happened to agree, but a duplicated map is a map that drifts,
    # and a deck page silently disagreeing with the sell scoring about what counts as "core" is the
    # exact failure this avoids. The local `_CORE_FUND_CATS` / `_SATELLITE_FUND_CATS` sets are kept
    # ONLY as the fallback for when the lib cannot be imported, never as a second opinion.
    # Loaded by explicit PATH, not by module name. `lib/core_satellite.py` and this file share a
    # basename, so a plain `import core_satellite` resolves by sys.path order -- and since the engine
    # puts both lib/ and modules/ on the path, it can resolve to THIS file and import itself. The
    # path load removes the ambiguity entirely.
    try:
        _lib_classify = _load_lib_classify()
        if _lib_classify is None:
            raise ImportError("lib/core_satellite.py not loadable")
        bucket, _reason = _lib_classify(f)
        return "Core" if bucket == "core" else "Satellite"
    except Exception:
        if cat in _CORE_FUND_CATS:
            return "Core"
        if cat in _SATELLITE_FUND_CATS:
            return "Satellite"
        return "Core"  # a category named by neither set: default Core (the larger, less exotic
                       # bucket) rather than an unexplained Satellite -- disclosed on the page's
                       # source line, never silent


def _equity_bucket(e):
    if "gold" in (e.get("name") or "").lower():
        return "Core"  # the ruling names gold explicitly, regardless of the holding's wrapper
    return "Satellite" if e.get("mcap_band") == "Small" else "Core"  # Large/Mid -> Core


def render(deck, ctx, tier):
    reg = tier.get("register", "std")
    eq = ctx["equity"]; funds = ctx["funds"]

    rows = [(e["name"], "Stock", _equity_bucket(e), e["weight_pct"]) for e in eq]
    rows += [(f["name"], "Fund", _fund_bucket(f), f["weight_pct"]) for f in funds]

    invested = sum(r[3] for r in rows) or 1.0
    core_pct = sum(r[3] for r in rows if r[2] == "Core") / invested * 100.0
    sat_pct = 100.0 - core_pct

    eyebrow = "Portfolio construction"
    title = ("Core and satellite, read against the mandate's own guidance" if reg != "simple"
             else "The steady core, and the smaller bets around it")
    s = deck.content(1, "Portfolio X-ray", eyebrow, title)

    intro = (f"This mandate is built core-satellite: a stable core doing the compounding, smaller "
             f"satellites for higher-risk, higher-return bets. {TARGET_CORE_PCT:.0f}/"
             f"{100-TARGET_CORE_PCT:.0f} is the house's directional guidance for that split, "
             "explicitly flexible, not a limit.")
    deck.txt(s, ML, 1.85, UW, 0.42, [(intro, SERIF, 10.5, INK, False, True)], ls=1.08)

    # ---- bar: current read, target shown as a reference tick, no pass/fail colouring ----
    bx, by, bw, bh = ML, 2.55, UW, 0.42
    core_w_in = bw * core_pct / 100.0
    deck.rect(s, bx, by, max(core_w_in, 0.02), bh, fill=NAVY)
    deck.rect(s, bx + core_w_in, by, max(bw - core_w_in, 0.02), bh, fill=GOLD)
    if core_w_in >= 1.0:
        deck.txt(s, bx + 0.1, by, core_w_in - 0.15, bh, [(f"CORE  {core_pct:.0f}%", SANS, 10, WHITE, True)],
                 anchor=MSO_ANCHOR.MIDDLE)
    if bw - core_w_in >= 1.0:
        deck.txt(s, bx + core_w_in + 0.1, by, bw - core_w_in - 0.15, bh,
                 [(f"SATELLITE  {sat_pct:.0f}%", SANS, 10, WHITE, True)], anchor=MSO_ANCHOR.MIDDLE)
    tick_x = min(max(bx + bw * TARGET_CORE_PCT / 100.0, bx + 0.02), bx + bw - 0.02)
    deck.rect(s, tick_x - 0.009, by - 0.07, 0.018, bh + 0.14, fill=INK)
    deck.txt(s, tick_x - 0.6, by + bh + 0.05, 1.2, 0.2,
             [(f"guidance ~{TARGET_CORE_PCT:.0f}%", SANS, 7.5, SLATE, True, False, 15)], align=PP_ALIGN.CENTER)
    deck.txt(s, bx, by + bh + 0.05, 1.6, 0.2, [(f"today {core_pct:.0f}%", SANS, 7.5, NAVY, True, False, 15)])

    # ---- breakdown: which holdings actually sit where, fixed row budget regardless of count ----
    ty = 3.30
    deck.txt(s, ML, ty, UW, 0.2, [("WHAT SITS WHERE, BY WEIGHT OF THE INVESTED BOOK", SANS, 8.5, SLATE, True, False, 90)])
    ty += 0.30
    half = (UW - 0.3) / 2
    N_SHOW = 5
    end_y = ty
    for i, bucket in enumerate(("Core", "Satellite")):
        sub = sorted([r for r in rows if r[2] == bucket], key=lambda r: -r[3])
        top, n = sub[:N_SHOW], len(sub)
        pct = core_pct if bucket == "Core" else sat_pct
        x0 = ML + i * (half + 0.3)
        deck.txt(s, x0, ty, half, 0.22,
                 [(f"{bucket.upper()} · {n} holding{'s' if n != 1 else ''} · {pct:.0f}%",
                   SANS, 8.5, (NAVY if bucket == "Core" else GOLD), True, False, 15)])
        yy = ty + 0.28
        for name, _kind, _b, w in top:
            deck.txt(s, x0, yy, half - 0.65, 0.22, [(name[:40], SERIF, 9.5, INK, False)])
            deck.txt(s, x0 + half - 0.62, yy, 0.62, 0.22, [(f"{w:.1f}%", SANS, 9.5, SLATE, True)],
                     align=PP_ALIGN.RIGHT)
            yy += 0.255
        if n == 0:
            deck.txt(s, x0, yy, half, 0.22, [("None held today.", SERIF, 9.5, SLATE, False, True)])
            yy += 0.255
        elif n > len(top):
            deck.txt(s, x0, yy, half, 0.22, [(f"+ {n - len(top)} more", SERIF, 8.5, SLATE, True, True)])
            yy += 0.255
        end_y = max(end_y, yy)

    body = ("Guidance, not a test. The split above is a read of where the book sits today against "
            "the mandate's own core-satellite idea -- there is no breach, and the target is "
            "explicitly flexible.") if reg != "simple" else (
            "This just shows how much of your money is in steady, core holdings versus smaller, "
            "higher-risk bets. It is a guide, not a rule you can fail.")
    cy = end_y + 0.12
    ch = deck.callout_h(UW, body, min_h=0.55, max_h=max(0.55, 6.50 - cy))
    deck.callout(s, ML, cy, UW, ch, "How to read this", body, "human")

    demo_tag = " Illustrative synthetic book." if ctx.get("is_demo", False) else ""
    deck.source(s, "Core = index, large cap, mid cap, flexi, multi, hybrid, debt, gold. Satellite = "
                   "sectoral/thematic, small cap, international, factor/smart-beta, contra (house "
                   "guidance, 2026-08-06). % of the invested book (equity + funds); cash is "
                   "outside this split. A generic 'equity'-category fund with no finer category on "
                   "file is placed by name/benchmark keyword -- disclosed, not a scored judgement."
                   f"{demo_tag}")
    return 1
