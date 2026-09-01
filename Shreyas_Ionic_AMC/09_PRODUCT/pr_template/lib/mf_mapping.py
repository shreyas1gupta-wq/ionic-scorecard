# -*- coding: utf-8 -*-
"""mf_mapping.py — shared MF/fund identity-resolution helpers, extracted from real
mapping mistakes made on the Client A NDPMS build (2026-08-02). See the
`ionic-wealth-complete` skill's "Client A-build lessons" section for the full
incident writeups; this module is the reusable code side of that lesson set.

HARD RULE (do not violate): this module NEVER auto-accepts a fund match by string
similarity. `resolve_amc()` and `resolve_scheme_rename()` only canonicalize KNOWN,
verified name variants (an AMC's own accepted abbreviation, or a scheme's own
official AMFI rename) — they are lookups against a curated table, not a fuzzy
scorer. A fund with no entry in these tables must be verified by a Sonnet agent,
one fund at a time, with web search, before it is ever matched to a framework's
fund list. "Not found" beats a wrong guess, always.

Two of these were caught the hard way: a naive similarity pass matched "Kotak
Midcap Fund" to "Kotak Multicap Fund" (different category, wrong) and "ICICI
Prudential Liquid Fund" to "ICICI Pru Large & Mid Cap Fund" (liquid vs equity,
nonsensical) before AMC/scheme identity was checked properly.
"""
import re

# ---------------------------------------------------------------------------
# AMC name canonicalization — verified equivalences ONLY (same real AMC, just a
# different house style / abbreviation). Adding an AMC here is a factual claim:
# "these two strings always refer to the same fund house." Verify before adding.
# ---------------------------------------------------------------------------
AMC_ALIASES = {
    "ICICI PRUDENTIAL": "ICICI PRU",
    "ADITYA BIRLA SUN LIFE": "ABSL",
    # QFRA-2's NAV files style this house "Aditya Birla SL"; holdings statements spell it out.
    # Without this row the two never match and the fund silently reads as uncovered.
    # (Safe: "SL" is not a substring of "SUN LIFE", so the two rows cannot collide.)
    "ADITYA BIRLA SL": "ABSL",
    "CANARA ROBECO": "CANARA ROB",
    "MOTILAL OSWAL": "MOTILAL OSWAL",
    "FRANKLIN INDIA": "FRANKLIN",
    "FRANKLIN TEMPLETON": "FRANKLIN",
    # QFRA-1's workbook and QFRA-2's NAV files both abbreviate these; CAS statements do not.
    "NIPPON INDIA": "NIPPON",
    "SUNDARAM": "SUNDARAM",
    "HDFC": "HDFC",
}

# Explicitly known NON-equivalences — AMC name pairs that look similar but are
# DIFFERENT real fund houses. Never auto-match across these, even at a high
# string-similarity score. (Documents the exact trap hit on this build.)
AMC_FALSE_FRIENDS = [
    ("ADITYA BIRLA SUN LIFE", "AXIS"),   # both run a "Flexi Cap Fund" — different AMCs
    ("KOTAK", "QUANT"),
]


def canonical_amc(name):
    """Upper-case + apply known alias collapse. Two funds only share an AMC
    identity if canonical_amc(a) == canonical_amc(b) AND neither pair is in
    AMC_FALSE_FRIENDS."""
    s = name.upper()
    for full, short in AMC_ALIASES.items():
        s = s.replace(full, short)
    return s


def first_word_token(name):
    """First alphabetic token of a fund name, post-canonicalization — a cheap
    AMC-identity gate to run BEFORE any name-similarity comparison, never after."""
    s = canonical_amc(name)
    m = re.search(r"[A-Z]+", s)
    return m.group(0) if m else ""


# ---------------------------------------------------------------------------
# Scheme rename table — real AMFI-registered renames we've had to chase down
# manually. Add an entry here (old_name -> new_name, with a `note` citing the
# source/date verified) the moment a Sonnet+web-search pass confirms one, so
# the NEXT client's holdings match on the first pass instead of after another
# manual audit finds the gap.
# ---------------------------------------------------------------------------
SCHEME_RENAMES = {
    "ICICI Pru Bluechip Fund": {
        "renamed_to": "ICICI Prudential Large Cap Fund",
        "note": "Category-mandated rename (SEBI large-cap naming norms). Verified 2026-08-01.",
    },
    "Kotak Emerging Equity Fund": {
        "renamed_to": "Kotak Midcap Fund",
        "note": "Same AMC, same >=65%-midcap mandate, unchanged. Verified 2026-08-01.",
    },
    "Bandhan Core Equity Fund": {
        "renamed_to": "Bandhan Large & Mid Cap Fund",
        "note": "Formerly IDFC Core Equity Fund pre-Bandhan-acquisition, then renamed again "
                "post-acquisition. Verified 2026-08-01.",
    },
    "DSP Equity Opportunities Fund": {
        "renamed_to": "DSP Large & Mid Cap Fund",
        "note": "Same AMC/scheme, SEBI category-naming rename. Verified 2026-08-01.",
    },
}


def resolve_scheme_rename(name):
    """Return the current name for a fund if it appears in the rename table
    (checked both directions — old name given, or new name given), else the
    input unchanged. This is a lookup, not a guess."""
    for old, info in SCHEME_RENAMES.items():
        if name.strip().lower() == old.strip().lower():
            return info["renamed_to"]
        if name.strip().lower() == info["renamed_to"].strip().lower():
            return info["renamed_to"]
    return name


# ---------------------------------------------------------------------------
# CAS holdings-row sanity checks — catches the exact row-bleed corruption class
# found on this build: POLYCAB's `name` field had an entirely different
# holding's row content (NAM-INDIA's AMC name + ISIN + price/value figures)
# silently concatenated onto the front of it during CAS extraction.
# ---------------------------------------------------------------------------
_ISIN_RE = re.compile(r"\bIN[A-Z0-9]{10}\b")
NAME_LEN_WARN = 80  # a real equity/scheme name is essentially never this long


def validate_holdings_row(row):
    """Return a list of human-readable warnings for a parsed CAS holdings row
    (dict with at least a 'name' key). Empty list = clean. Never raises —
    a bad row must be flagged for the RM, never silently dropped or trusted."""
    warnings = []
    name = str(row.get("name", ""))
    if len(name) > NAME_LEN_WARN:
        warnings.append(
            f"name field is {len(name)} chars (>{NAME_LEN_WARN}) — possible row-bleed "
            f"from CAS extraction, check for concatenated content: {name[:60]}..."
        )
    isins_in_name = _ISIN_RE.findall(name)
    row_isin = str(row.get("isin", "")).strip().upper()
    stray_isins = [i for i in isins_in_name if i != row_isin]
    if stray_isins:
        warnings.append(
            f"name field contains ISIN(s) {stray_isins} that don't match this row's own "
            f"isin field ({row_isin!r}) — likely a different holding's data bled in"
        )
    return warnings


def validate_holdings(rows):
    """Run validate_holdings_row over a full parsed holdings list; return
    {row_index: [warnings]} for any row with issues. Call this immediately
    after CAS parsing, before the data enters data/<client>.py."""
    issues = {}
    for i, row in enumerate(rows):
        w = validate_holdings_row(row)
        if w:
            issues[i] = w
    return issues
