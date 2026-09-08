# -*- coding: utf-8 -*-
"""What the recommended exits actually cost in tax, from the lot file where there is one.

WHY THIS IS ITS OWN FILE. The tax on an exit is not one rate applied to one gain. It is a
different rate on each SLICE of the same holding, and which slice a unit falls into depends on
when that unit was bought, which a holdings statement does not say and a lot statement does. The
build used to charge a flat 12.5% to everything with a cost basis and print "less STCG 0.0L" - a
positive claim that no short-term gain arises - on a book whose own supplied lot file showed
Rs 89.5 lakh of short-term units, two of them in schemes on the sell list.

THE THREE SLICES, and why each is treated the way it is:

  LTCG units          Held past the long-term line for their asset class. Equity and equity-
                      oriented funds: 12.5% above the per-holder Rs 1.25 lakh exemption. Gold,
                      international and debt units bought BEFORE 1 April 2023: 12.5%, no
                      indexation.
  STCG units          Equity and equity-oriented: 20%. Everything else short-term is taxed at the
                      holder's own slab, which this desk does not know, so it is disclosed in
                      rupees and NOT given a number.
  Other-income units  Debt units bought ON OR AFTER 1 April 2023. These lost capital-gains
                      treatment entirely: the whole gain is added to income and taxed at slab,
                      however long they have been held. Disclosed, never estimated.

NOTHING HERE IS A TAX OPINION, and nothing is invented: a slice with no lot data produces no
number and says so. An estimate that is silently wrong is worse than a gap that is visible.
"""
import re

import pandas as pd

# The columns as the platform writes them. Matched case- and space-insensitively so a re-export
# with a renamed header does not silently produce a book with no short-term gain in it.
_COLS = {
    "invested": ("invested value", "invested"),
    "current": ("current value",),
    "ltcg_val": ("current value of ltcg units",),
    "stcg_val": ("current value of stcg units",),
    "other_val": ("current value of other income units",),
    "gf_val": ("current value of grandfathered units",),
    "mv_2018": ("market value as on 31st jan 2018",),
}
LTCG_EXEMPT_PER_HOLDER = 125000.0     # Sec 112A, per person per year
EQUITY_LTCG = 0.125
EQUITY_STCG = 0.20
NON_EQUITY_LTCG = 0.125               # no indexation, from 23 July 2024


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s or "").lower())


def _num(v):
    try:
        f = float(v)
        return 0.0 if f != f else f
    except (TypeError, ValueError):
        return 0.0


def load_lots(path):
    """scheme key -> the slices, summed over every folio and every family member.

    SUMMED OVER EVERY FOLIO. A scheme held in three folios whose cost was read from two of them
    prices the exit against two thirds of what was actually paid, and the whole error lands on
    the gain. On this book that was SBI Small Cap: Rs 6.11 lakh of cost against Rs 29.5 lakh of
    value, where the lot file carries Rs 17.06 lakh.
    """
    if not path:
        return {}
    df = pd.read_csv(path)
    low = {re.sub(r"\s+", " ", str(c)).strip().lower(): c for c in df.columns}

    def col(key):
        for want in _COLS[key]:
            for k, orig in low.items():
                if k.startswith(want):
                    return orig
        return None

    name_col = next((low[k] for k in low if k in ("scheme", "name", "scheme name")), None)
    if name_col is None:
        return {}
    mem_col = next((low[k] for k in low if k in ("member", "holder", "investor")), None)
    colmap = {k: col(k) for k in _COLS}
    out = {}
    for r in df.itertuples(index=False):
        d = dict(zip(df.columns, r))
        k = _norm(d.get(name_col))
        if not k:
            continue
        rec = out.setdefault(k, {"scheme": str(d.get(name_col)).strip(), "members": set(),
                                 "invested": 0.0, "current": 0.0, "ltcg_val": 0.0,
                                 "stcg_val": 0.0, "other_val": 0.0, "gf_val": 0.0,
                                 "mv_2018": 0.0, "folios": 0})
        if mem_col:
            rec["members"].add(str(d.get(mem_col)).strip())
        rec["folios"] += 1
        for key, c in colmap.items():
            if c is not None:
                rec[key] += _num(d.get(c))
    return out


def _match(lots, name):
    """Exact on the normalised scheme name, then a containment test in one direction.

    NO SIMILARITY SCORING. A fund matched to the wrong scheme by edit distance produces a tax
    number that is confidently wrong and cannot be spotted on the page. Where two lot rows could
    both claim a name, none is returned and the holding falls back to the statement's own cost.
    """
    k = _norm(name)
    if not k:
        return None
    if k in lots:
        return lots[k]
    hits = [v for kk, v in lots.items() if (kk in k or k in kk) and min(len(kk), len(k)) >= 12]
    return hits[0] if len(hits) == 1 else None


def is_equity_oriented(asset_class, sub_category, name):
    a = str(asset_class or "").strip().lower()
    sub = str(sub_category or "")
    nm = str(name or "").lower()
    if a == "equity":
        return True
    if any(w in sub for w in ("Aggressive Hybrid", "Equity Savings", "Arbitrage",
                              "Balanced Advantage", "Dynamic Asset Allocation",
                              "Multi Asset")):
        return True
    if any(w in nm for w in ("arbitrage", "equity savings", "balanced advantage")):
        return True
    return False


def price(row, lots):
    """One holding's exit, priced. Never raises, never guesses a missing slice.

    Keys: value, gain_known, ltcg_gain, ltcg_tax, stcg_tax, slab_value, character, basis, note.
    slab_value is money whose tax this desk cannot compute, carried through so the page can say
    so in rupees instead of printing a zero.
    """
    val = _num(row.get("value_inr"))
    name = row.get("name")
    eq = is_equity_oriented(row.get("asset_class"),
                            row.get("risk_sub") or row.get("sub_category"), name)
    nm = str(name or "").lower()
    out = {"value": val, "gain_known": False, "ltcg_gain": 0.0, "ltcg_tax": 0.0,
           "stcg_tax": 0.0, "slab_value": 0.0, "character": "", "basis": "statement",
           "note": ""}

    # Instruments that produce no capital gain at all. Charging one a capital-gains rate states a
    # treatment that does not exist for it.
    if any(w in nm for w in ("fixed deposit", "bank fd", "deposit", "savings a/c",
                             "savings account", "bank balance")):
        out["character"] = "No gain; interest at slab"
        out["slab_value"] = val
        return out
    if "ppf" in nm or "provident fund" in nm:
        out["character"] = "Tax-free on exit"
        return out
    if "senior citizen" in nm or "scss" in nm:
        out["character"] = "No gain; interest at slab"
        out["slab_value"] = val
        return out
    if "ulip" in nm:
        out["character"] = "Per the policy terms"
        return out

    rec = _match(lots, name)
    if rec is None:
        inv = _num(row.get("cost_inr"))
        if inv <= 0 or val <= 0 or inv >= val:
            out["character"] = ("Equity: 12.5% long, 20% short"
                                if eq else "Debt: 12.5% or SLAB") + ", no cost on file"
            return out
        gain = val - inv
        out["gain_known"] = True
        out["ltcg_gain"] = gain
        out["ltcg_tax"] = gain * (EQUITY_LTCG if eq else NON_EQUITY_LTCG)
        # SHORT ENOUGH FOR THE COLUMN IT LANDS IN. The long form wrapped to three lines in a
        # table row sized for two and the rows overlapped each other on the page.
        out["character"] = ("Equity 12.5%, no holding period" if eq else
                            "Debt 12.5%, no purchase date")
        out["note"] = "no lot detail"
        return out

    # THE GAIN IS APPORTIONED ACROSS THE SLICES BY VALUE. The lot file gives cost for the whole
    # scheme and value per slice; assigning the whole gain to one slice would price the exit at
    # whichever rate that slice happens to carry.
    cur = rec["current"] or val
    inv = rec["invested"]
    out["basis"] = "lot file"
    if cur <= 0 or inv <= 0:
        out["character"] = "Cost on file is nil"
        return out
    gain_rate = max(0.0, 1.0 - inv / cur)          # gain as a share of value
    scale = (val / cur) if cur else 1.0            # the deck's value against the lot file's
    L = rec["ltcg_val"] * scale
    S = rec["stcg_val"] * scale
    O = rec["other_val"] * scale
    out["gain_known"] = True
    parts = []
    if eq:
        out["ltcg_gain"] = L * gain_rate
        out["ltcg_tax"] = out["ltcg_gain"] * EQUITY_LTCG
        out["stcg_tax"] = S * gain_rate * EQUITY_STCG
        if L > 0:
            parts.append("LTCG 12.5%")
        if S > 0:
            parts.append("STCG 20%")
    else:
        out["ltcg_gain"] = L * gain_rate
        out["ltcg_tax"] = out["ltcg_gain"] * NON_EQUITY_LTCG
        # Short-term on anything but equity is slab, and so is every post-April-2023 debt unit.
        out["slab_value"] = S + O
        if L > 0:
            parts.append("LTCG 12.5%")
        if S > 0:
            parts.append("short-term at SLAB")
        if O > 0:
            parts.append("bought after Apr-2023, SLAB")
    out["character"] = " . ".join(parts) if parts else "No taxable slice"
    if rec["folios"] > 1:
        out["note"] = "%d folios" % rec["folios"]
    return out
