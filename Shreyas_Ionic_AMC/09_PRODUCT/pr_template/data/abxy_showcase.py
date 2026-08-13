# -*- coding: utf-8 -*-
"""abxy_showcase.py — the ABXY Family SHOWCASE context: the house demo book rendered
against a deliberately AGGRESSIVE Investment Policy Statement, for the Product Approval
Committee / CEO product review (2026-08-03).

Why a separate module rather than editing azby_family.py: azby_family is the schema
reference every future client data file is copied from, and other builds/tests read it.
This wraps its ctx and overrides only two things:

  1. `is_demo = True`. azby_family does NOT set the flag, so the demo book has been
     rendering WITHOUT the "illustrative synthetic" disclaimers every module already
     supports (cover prints "[ILLUSTRATIVE, synthetic demo client; not a real
     portfolio]" only when the flag is on). A committee showcase built on fabricated
     holdings must be labelled as such on every page it can be — that is the whole
     point of the flag, and leaving it off would be the more dangerous default.
  2. An AGGRESSIVE IPS. The stock IPS is already tiered "Aggressive" but sits at a
     78% equity target with an 8% single-name cap; this one pushes to an 85% equity
     target, 55% mid-and-small ceiling, 10% single-name and 30% single-AMC caps, an
     18% foreign target and a 10-year horizon, so the IPS-fit engine is exercised
     against a genuinely high-risk mandate rather than a moderate one.

Nothing else is touched: the same holdings, the same scored calls, the same frozen
scoring contract. Aggressive here describes the CLIENT'S MANDATE, never a loosening
of our own scoring or QA standards.
"""
import copy

from data.azby_family import build_ctx as _base_build_ctx

# The aggressive mandate. Shapes match the IPS v2 schema exactly (ips_summary.py reads
# min/target/max 3-tuples for alloc_bands and gold/silver, 2-tuples for the mcap and
# credit bands, bare floats for the caps) — a shape change here silently breaks that page.
_AGGRESSIVE_IPS = {
    # short on purpose: ips_summary renders this into a narrow pill, and a longer string
    # wraps and clips there (seen as "AGGRESSIVE (GROWTH-" / "MAXIMISING)"). The fuller
    # description of the mandate belongs in `objective`, which has a real line to itself.
    "risk_tier": "Aggressive",
    # kept short deliberately: ips_summary.py gives the objective a single 0.42in line, and a
    # longer string overflows into the parameter table beneath it (caught by both geometry gates).
    "objective": "Maximise long-term compounding; accepts deep drawdowns for a higher terminal value.",
    "horizon_yrs": 10,
    "alloc_bands": {"Equity": (72, 85, 92), "Hybrid/Debt": (0, 8, 18),
                    "Alternatives/Gold": (0, 5, 12), "Cash": (0, 2, 8)},
    "single_name_cap_pct": 10.0,
    "single_amc_cap_pct": 30.0,
    "locked_in_cap_pct": 15.0,
    "cash_cap_pct": 8.0,
    "equity_mcap_bands": {"Large": (40, 65), "Mid & Small": (35, 55)},
    "thematic_sectoral_cap_pct": 25.0,
    "unlisted_equity_cap_pct": 5.0,
    "foreign_target_pct": 18.0,
    "international_equity_cap_pct": 30.0,
    "fi_credit_bands": {"AAA": (60, 80), "AA+ / AA / AA-": (15, 30), "Below AA-": (0, 10)},
    "mod_duration_cap_yrs": 3.0,
    "gold_band_pct": (0, 5, 12),
    "silver_band_pct": (0, 3, 6),
    "constraints": [
        "Single stock capped at 10% of the book; single AMC at 30%",
        "Min 18% of equity in foreign/global by target — diversification, not return-chasing",
        "Mid-and-small permitted to 55% of the equity sleeve",
        "No unrated credit, no F&O, no leverage — risk is taken in equity beta, never in structure",
        "No drawdown-triggered de-risking: the mandate is explicitly ride-through",
    ],
}


def build_ctx():
    ctx = copy.deepcopy(_base_build_ctx())

    # 1. honest labelling for a fabricated book (see module docstring)
    ctx["is_demo"] = True

    # 2. the aggressive mandate, merged over the base IPS so any key the base carries
    #    that this dict does not (on_file, and anything added to the schema later)
    #    survives instead of being dropped.
    ctx["ips"] = {**ctx.get("ips", {}), **_AGGRESSIVE_IPS}
    ctx["ips"]["on_file"] = True

    # client block reflects the mandate the deck is being reviewed against
    c = ctx["client"]
    c["name"] = "ABXY Family"
    c["profile"] = "Aggressive (growth-maximising)"
    c["horizon"] = "10-year horizon"

    # the house view's foreign gap is quoted against the IPS foreign target, so it has to
    # move with it (base assumed a 15% target; this mandate asks for 18%). Everything else
    # in alloc_gap is a house call, not an IPS-derived number, and stays as-is.
    hv = ctx.get("house_view", {}).get("alloc_gap")
    if isinstance(hv, dict) and "Foreign" in hv:
        hv["Foreign"] = hv["Foreign"] - 3.0

    return ctx
