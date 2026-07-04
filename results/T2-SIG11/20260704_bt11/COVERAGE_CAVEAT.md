# COVERAGE CAVEAT (post-run forensics, 2026-07-04)
BT-11 ran on the HF daily panel. Forensics (results/factor_replication/20260704_data_forensics/) established the panel's
cross-sectional completeness degrades pre-2018 (N200 full-history coverage 57.6% in 2006 -> 83.5% in 2018; N500 likely lower).
IMPACT: BT-11's 2016-2018 slices select from a survivor-lean subset — a KNOWN BOUNDED BIAS, not fabrication (prices+adjustments verified clean).
BEFORE any early-era BT-11 number is certified or quoted: re-run 2016-2018 slices on the combined Master+Delisted close panel
(`_combined_master_delisted_close.parquet`, cached in the forensics dir). Post-2018 slices are sound as-is.
— filed by main desk per Arjun's blast-radius call

## UPGRADE (forensics round-2, same day)
The bias direction is now known: OPTIMISTIC (survivor-holed panel omits later-losers). BT-11 pre-2018 slices are
inflated, not just thin. DO NOT certify/quote early-era BT-11 numbers until re-run on the union panel
(_combined_master_delisted_close.parquet). Candidate additional input: swing_momentum/processed/eq_close.parquet +
membership.parquet (the survivorship-safe pair behind MULTIBAGGER_STUDY).
