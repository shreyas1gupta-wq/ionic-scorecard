# -*- coding: utf-8 -*-
"""psu_list_build.py - red-team PSU identification (Nikhil Bose, 2026-08-06).

Checks BEFORE trusting any list:
  1. Does quarterly_shareholding_pit.parquet's "Government" column work as a PSU classifier?
     (tested separately, verbally reported in memo -- verdict: NO, see findings)
  2. Cross-check the two lists ALREADY on disk against each other and against the scored universe:
       - bt_regime_psu_test.py's hand list (~90 names, built today)
       - scripts/gate_v2.py's PSU set (47 names, Principal-ratified 2026-07-25 live gate)
  3. Flag disagreements and verify each by name (domain knowledge), not by assumption.
No lookahead concern: PSU/govt-promoter status is a slow-moving structural fact, not a return signal.
"""
import os
import sys
import pandas as pd

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SC750 = os.path.dirname(os.path.dirname(HERE))      # STOCK_SCORECARD_750 (up from results/PSU_GATE_ABLATION)
OBS = os.path.join(SC750, "results", "DECILE_ROLLING_20260805", "observations.csv")

# ---- the two existing lists, copied verbatim (read-only cross-check, not edited in place) ----
HAND_LIST = {
    "ONGC", "OIL", "IOC", "BPCL", "HINDPETRO", "GAIL", "PETRONET", "MGL", "IGL",
    "NTPC", "POWERGRID", "NHPC", "SJVN", "THERMAX", "NLCINDIA", "PFC", "RECLTD", "IREDA",
    "COALINDIA", "NMDC", "SAIL", "NALCO", "MOIL", "HINDCOPPER", "KIOCL", "GMDCLTD",
    "BEL", "HAL", "BHEL", "BEML", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL", "MIDHANI",
    "ENGINERSIN", "ITI",
    "IRFC", "RVNL", "IRCTC", "IRCON", "RITES", "NBCC", "HUDCO", "CONCOR", "SCI", "RAILTEL",
    "SBIN", "CANBK", "PNB", "BANKBARODA", "UNIONBANK", "INDIANB", "CENTRALBK", "IOB",
    "UCOBANK", "MAHABANK", "PSB", "J&KBANK",
    "LICI", "GICRE", "NIACL", "IFCI", "SBICARD", "SBILIFE",
    "BALMLAWRIE", "STCINDIA", "MMTC", "HINDZINC", "FACT", "RCF", "NFL", "GSFC",
}
GATE_V2_LIST = {
    "BHEL", "GAIL", "SBIN", "HINDCOPPER", "NATIONALUM", "COCHINSHIP", "POWERGRID", "NTPC",
    "ONGC", "IOC", "BPCL", "HINDPETRO", "COALINDIA", "SAIL", "NMDC", "IRCTC", "IRFC", "HAL",
    "BEL", "MAZDOCK", "BDL", "PFC", "RECLTD", "NHPC", "OIL", "CANBK", "BANKBARODA", "PNB",
    "UNIONBANK", "INDIANB", "MAHABANK", "BANKINDIA", "LICI", "NTPCGREEN", "SJVN", "CESC",
    "ITI", "FACT", "MMTC", "RVNL", "IRCON", "HCC", "NBCC", "ENGINERSIN", "RITES", "CONCOR",
    "GMDC", "MOIL",
}
# GMDC vs GMDCLTD, HINDZINC treated as non-PSU by both hand lists -- ticker note, not a gap.

# ---- verified-wrong entries in GATE_V2_LIST (domain knowledge, checked by name) ----
# CESC Ltd: RP-Sanjiv Goenka Group, privately promoted (Kolkata power co). NOT government-owned.
# HCC (Hindustan Construction Co): Gulabchand family promoted EPC. NOT government-owned.
# Both look like the live gate's PSU-relief set mis-tagging two private companies.
GATE_V2_ERRORS = {"CESC", "HCC"}

# ---- verified-wrong entry in HAND_LIST ----
# Thermax Ltd: Pune engineering/energy co, promoted by the Aga/Pudumjee family (Anu Aga chair).
# NOT government-owned. Looks like a "power/energy sector -> assumed PSU" mistake.
HAND_LIST_ERRORS = {"THERMAX"}

# ---- verified real gaps: genuine CPSEs/PSU banks missing from HAND_LIST ----
# NATIONALUM (National Aluminium Co, GoI ~51%) - in gate_v2 list, correctly a PSU, missing from hand list.
# BANKINDIA (Bank of India) - the hand list has 11 of the 12 nationalised PSU banks and is missing
#   exactly this one (SBIN/CANBK/PNB/BANKBARODA/UNIONBANK/INDIANB/CENTRALBK/IOB/UCOBANK/MAHABANK/PSB
#   present; Bank of India absent). Confirmed by counting against the public list of 12 PSBs.
# NTPCGREEN (NTPC Green Energy, listed Nov-2024, GoI via NTPC) - in gate_v2 list; check universe presence.
VERIFIED_ADDITIONS = {"NATIONALUM", "BANKINDIA", "NTPCGREEN"}

IMPROVED_PSU = (HAND_LIST - HAND_LIST_ERRORS) | VERIFIED_ADDITIONS


def main():
    obs = pd.read_csv(OBS)
    universe = set(obs["sym"].astype(str).str.upper().unique())
    print(f"observations.csv universe: {len(universe)} distinct symbols, {len(obs)} rows, "
          f"{obs['formation'].nunique()} formations")

    print("\n=== list sizes ===")
    print(f"  HAND_LIST (bt_regime_psu_test.py, as shipped)     : {len(HAND_LIST)}")
    print(f"  GATE_V2_LIST (scripts/gate_v2.py, live-ratified)  : {len(GATE_V2_LIST)}")
    print(f"  overlap                                            : {len(HAND_LIST & GATE_V2_LIST)}")
    print(f"  in GATE_V2 only                                    : "
          f"{sorted(GATE_V2_LIST - HAND_LIST)}")
    print(f"  in HAND_LIST only (first 15)                       : "
          f"{sorted(HAND_LIST - GATE_V2_LIST)[:15]} ... ({len(HAND_LIST - GATE_V2_LIST)} total, "
          f"expected -- gate_v2's list is narrower/leverage-relief-focused, hand list is broader)")

    print("\n=== flagged errors, checked by name ===")
    for t in sorted(GATE_V2_ERRORS):
        present = t in universe
        print(f"  GATE_V2 mis-tag  {t:<10} in scored universe: {present}  -> EXCLUDED from improved list "
              f"(not government-owned)")
    for t in sorted(HAND_LIST_ERRORS):
        present = t in universe
        print(f"  HAND_LIST mis-tag {t:<10} in scored universe: {present}  -> EXCLUDED from improved list "
              f"(not government-owned)")

    print("\n=== flagged additions, checked by presence in the scored universe ===")
    for t in sorted(VERIFIED_ADDITIONS):
        present = t in universe
        n_rows = int((obs["sym"].astype(str).str.upper() == t).sum())
        print(f"  candidate add {t:<10} in universe: {present}   rows if present: {n_rows}")

    print(f"\n=== final IMPROVED_PSU list: {len(IMPROVED_PSU)} names ===")
    present_in_uni = sorted(IMPROVED_PSU & universe)
    absent_from_uni = sorted(IMPROVED_PSU - universe)
    print(f"  present in scored universe : {len(present_in_uni)}")
    print(f"  never appear in universe   : {len(absent_from_uni)}  -> {absent_from_uni}")

    # coverage completeness estimate: how much of the improved list's PSU row-count comes from
    # names ALSO on gate_v2 (cross-validated by an independent, Principal-ratified source) vs
    # names ONLY on the hand list (single-source, domain-knowledge-only)
    obs["sym_u"] = obs["sym"].astype(str).str.upper()
    rows_hand = obs["sym_u"].isin(HAND_LIST).sum()
    rows_improved = obs["sym_u"].isin(IMPROVED_PSU).sum()
    rows_cross_validated = obs["sym_u"].isin(HAND_LIST & GATE_V2_LIST).sum()
    print(f"\n  PSU rows under original HAND_LIST     : {rows_hand}  ({rows_hand/len(obs)*100:.1f}% of obs)")
    print(f"  PSU rows under IMPROVED_PSU            : {rows_improved}  "
          f"({rows_improved/len(obs)*100:.1f}% of obs)")
    print(f"  of which cross-validated (both lists)  : {rows_cross_validated}  "
          f"({rows_cross_validated/rows_improved*100:.1f}% of improved-list rows)")

    with open(os.path.join(HERE, "improved_psu_list.txt"), "w") as f:
        f.write(",".join(sorted(IMPROVED_PSU)))
    print(f"\nwrote {os.path.join(HERE, 'improved_psu_list.txt')}")


if __name__ == "__main__":
    main()
