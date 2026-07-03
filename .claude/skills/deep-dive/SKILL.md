---
name: deep-dive
description: Fundamental forensic deep-dive on a stock via the sector analyst desk. Use for /deep-dive <stock>, "analyze this company fundamentally".
---
# /deep-dive — analyst desk (RP-09)
1. Route by sector to the right analyst agent (meera/karan/sneha/rohan/priya; ananya if cross-sector) — ONE agent, not a panel (token discipline).
2. They run ANALYST_CHECKLISTS forensic list on PIT data (screener_deep, ratios_pit, shareholding_changes — paths in DATA_CATALOG; judge only on available_date knowledge).
3. Output memo: verdict, 3 strongest bear points, forensic flags, catalysts + dates, what evidence would change the view. File to `03_RESEARCH_DESK/memos/` if decision-relevant.
