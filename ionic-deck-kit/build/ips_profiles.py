# -*- coding: utf-8 -*-
"""The three client mandates, and the machinery to score a book against one.

An IPS is generated from a SMALL number of inputs: the client's name, their risk profile, and the
holdings. Everything else on the statement below is either a band this desk sets by profile, or a
figure computed from the book. Nothing is typed in per client.

WHERE THE NUMBERS COME FROM, and this matters for sign-off:
  Aggressive  is the desk's own sheet, transcribed. Those bands are agreed.
  Moderate and Conservative are DERIVED, by one stated rule rather than invented per line: as the
  mandate becomes more cautious, the equity band steps down (80-100 / 60-80 / 40-60, the Principal's
  own numbers), and every other limit moves the same direction on the same axis, tightening what
  concentrates risk and widening what holds it back. They are marked as drafts until the desk signs
  them off, and this file is the single place to edit them.

A parameter this desk cannot compute from a holdings statement is reported as not available. It is
never estimated, because an IPS that quietly guesses a credit quality is worse than one that admits
it does not know.
"""

# (low, high) as percentages. None on either side means the side is unbounded.
PROFILES = {
    "Aggressive": {
        "label": "Aggressive",
        "approved": True,
        "drawdown": "Tolerable peak drawdown around 45%, horizon 7 years or more",
        "portfolio": {
            "Equity": (80, 100),
            "Fixed Income": (0, 20),
            "Alternates": (0, 20),
            "Cash and equivalents": (1, 3),
            "Allocation to a single AMC": (None, 25),
            "Locked-in products, over one year": (None, 30),
        },
        "equity": {
            "Core exposure": (56, 80),
            "Satellite exposure": (20, 44),
            "Pooled vehicles": (56, 100),
            "Direct holdings": (0, 20),
            "Large cap": (50, 80),
            "Mid and small cap": (20, 50),
            "Thematic and sectoral": (None, 15),
            "Listed securities": (70, None),
            "Unlisted securities": (None, 30),
            "A single listed security": (None, 15),
            "International equity": (10, 25),
            "A single strategy or scheme": (None, 15),
        },
        "fixed_income": {
            "AAA rated": (70, 100),
            "AA rated": (0, 30),
            "Below AA rated": (0, 0),
            "Modified duration, years": (None, 5),
            "NCDs and structured notes": (None, 5),
        },
        "alternates": {"Gold": (0, 20)},
    },
    "Moderate": {
        "label": "Moderate",
        "approved": False,
        "drawdown": "Tolerable peak drawdown around 25%, horizon 5 to 7 years",
        "portfolio": {
            "Equity": (60, 80),
            "Fixed Income": (20, 40),
            "Alternates": (0, 15),
            "Cash and equivalents": (1, 5),
            "Allocation to a single AMC": (None, 20),
            "Locked-in products, over one year": (None, 20),
        },
        "equity": {
            "Core exposure": (70, 90),
            "Satellite exposure": (10, 30),
            "Pooled vehicles": (70, 100),
            "Direct holdings": (0, 15),
            "Large cap": (60, 85),
            "Mid and small cap": (15, 40),
            "Thematic and sectoral": (None, 10),
            "Listed securities": (85, None),
            "Unlisted securities": (None, 15),
            "A single listed security": (None, 10),
            "International equity": (5, 15),
            "A single strategy or scheme": (None, 12),
        },
        "fixed_income": {
            "AAA rated": (80, 100),
            "AA rated": (0, 20),
            "Below AA rated": (0, 0),
            "Modified duration, years": (None, 4),
            "NCDs and structured notes": (None, 3),
        },
        "alternates": {"Gold": (0, 15)},
    },
    "Conservative": {
        "label": "Conservative",
        "approved": False,
        "drawdown": "Tolerable peak drawdown around 10 to 12%, horizon 3 to 5 years",
        "portfolio": {
            "Equity": (40, 60),
            "Fixed Income": (40, 60),
            "Alternates": (0, 10),
            "Cash and equivalents": (2, 8),
            "Allocation to a single AMC": (None, 15),
            "Locked-in products, over one year": (None, 10),
        },
        "equity": {
            "Core exposure": (80, 100),
            "Satellite exposure": (0, 20),
            "Pooled vehicles": (85, 100),
            "Direct holdings": (0, 10),
            "Large cap": (75, 100),
            "Mid and small cap": (0, 25),
            "Thematic and sectoral": (None, 5),
            "Listed securities": (100, None),
            "Unlisted securities": (None, 0),
            "A single listed security": (None, 5),
            "International equity": (0, 10),
            "A single strategy or scheme": (None, 10),
        },
        "fixed_income": {
            "AAA rated": (90, 100),
            "AA rated": (0, 10),
            "Below AA rated": (0, 0),
            "Modified duration, years": (None, 3),
            "NCDs and structured notes": (None, 0),
        },
        "alternates": {"Gold": (0, 10)},
    },
}

# Core or satellite, by framework sub-category. The desk's own split, transcribed.
# A broad-market or factor index fund is a CORE holding: it is the market, cheaply, not a bet
# beside it. Classing factor as satellite put Rs 129 crore of this book, an ICICI low-volatility
# ETF and a UTI momentum index fund, on the satellite side and read satellite at 56% of the equity
# sleeve against the desk's own 28%. The desk's Core list names cap-based funds and index vehicles
# belong with them; a thematic or sectoral fund is the satellite, because it is a view on one part
# of the market rather than the whole of it.
SATELLITE_SUBS = {
    "Thematic / Sectoral Fund",
    "Unlisted Equity - Late Stage / Pre-IPO", "Unlisted Equity - Mid Stage",
    "Unlisted Equity - Early Stage", "AIF Cat II - Private Equity Fund",
    "AIF Cat I - Venture Capital Fund", "AIF Cat III - Long Only Listed Equity",
    "AIF Cat III - Public Equity Fund", "AIF Cat III - Long / Short / Absolute Return",
    "PMS - Discretionary Listed Equity", "Credit Risk Fund",
    "AIF Cat II - Structured / Mezzanine / Venture Debt",
    "AIF Cat II - Performing / Senior Secured Credit",
    "NCD - AA and below / unrated / market-linked", "Perpetual / AT1 / Tier 2",
    "Bonds - AAA / AA+ private issuer", "Market Linked Debenture / Structured Note",
    "AIF Cat II - Real Estate - Yield / Lease", "AIF Cat II - Real Estate - Development",
}
# Held directly by the client rather than through a pooled vehicle.
DIRECT_SUBS_PREFIX = ("Direct Equity", "Unlisted Equity", "G-Sec", "SDL", "Bonds", "NCD",
                      "Perpetual", "Fixed Deposit", "T-Bill", "REIT", "InvIT",
                      "Bank Balance", "Market Linked Debenture", "Sovereign Gold Bond")
UNLISTED_PREFIX = ("Unlisted Equity", "AIF Cat I", "AIF Cat II")
LARGE_CAP_SUBS = {"Direct Equity - Large Cap", "Large Cap Fund",
                  "Index Fund / ETF - Broad Market", "Factor / Smart Beta Fund"}
MIDSMALL_SUBS = {"Direct Equity - Mid Cap", "Direct Equity - Small Cap",
                 "Direct Equity - Micro Cap", "Direct Equity - Recent IPO",
                 "Mid Cap Fund", "Small Cap Fund"}
INTERNATIONAL_SUBS = {"International Fund / FoF"}
THEMATIC_SUBS = {"Thematic / Sectoral Fund"}
# Sovereign and sovereign-owned paper is AAA by construction, and so is a fund that holds only
# those. The debt-fund categories below are here because SEBI fixes their credit floor: a Banking
# and PSU fund must hold 80% in bank, PSU and PFI paper, a Corporate Bond fund 80% in AA+ and above,
# a Money Market fund only instruments under a year. Leaving them out put AAA at 42% on a book whose
# fixed income is almost entirely investment grade, against the desk's own 95%.
AAA_SUBS = {"G-Sec - Short (residual under 5 years)", "G-Sec - Medium (residual 5 to 15 years)",
            "G-Sec - Long (residual over 15 years)", "SDL", "T-Bill",
            "Bonds - AAA PSU / sovereign-owned", "Bonds - AAA / AA+ private issuer",
            "Target Maturity Index Fund (G-Sec / SDL / PSU)", "Gilt Fund / Constant Maturity Gilt",
            "Overnight Fund", "Liquid Fund", "Bank Balance / Savings / Current Account",
            "Fixed Deposit - scheduled commercial or PSU bank, callable",
            "Money Market / Ultra Short / Low Duration", "Short Duration / Banking & PSU Debt",
            "Corporate Bond Fund", "Dynamic Bond Fund"}
# Cash and equivalents is NOT the whole Priority 1 bucket. Priority 1 is where the desk would draw
# cash from first and includes short-duration and corporate-bond funds; cash proper is same-day or
# next-day money. Using Priority 1 put cash at 13% of a book holding 0.3% in liquid funds.
CASH_SUBS = {"Overnight Fund", "Liquid Fund", "Bank Balance / Savings / Current Account",
             "Money Market / Ultra Short / Low Duration", "Arbitrage Fund", "T-Bill"}
BELOW_AA_SUBS = {"NCD - AA and below / unrated / market-linked", "Credit Risk Fund"}

NOT_AVAILABLE = "not available from a holdings statement"


def band_text(lo, hi, unit="%"):
    if lo is None and hi is None:
        return "no limit"
    if lo is None:
        return "max %g%s" % (hi, unit)
    if hi is None:
        return "min %g%s" % (lo, unit)
    if lo == hi:
        return "%g%s" % (lo, unit)
    return "%g%s to %g%s" % (lo, unit, hi, unit)


def fit(cur, lo, hi):
    """Inside, Below or Above. None where the figure could not be computed."""
    if cur is None:
        return None
    if lo is not None and cur < lo - 1e-9:
        return "Below"
    if hi is not None and cur > hi + 1e-9:
        return "Above"
    return "Inside"
