# Valuation-Regime Hedging & Downside-Play Study — agent book
Date 2026-07-08. Deliverable: `HEDGING_ANALYSIS_REPORT.docx` (Principal, human-format). Reproduce: engine.py → summarize.py → build_report.py.

## Data (verified, cached in data/)
- US: multpl.com monthly S&P500 + real Shiller CAPE 1871–2026, div yield, 10y rate; CBOE VIX daily 1990–2026 (real). stooq/FRED/github blocked by proxy; multpl+CBOE work.
- India: local NIFTY50 daily 2016–2026 + trailing PE/PB/divyield (nse_official_all_indices.parquet), India VIX 2016–2026.
- NO real option chains → all options BS-modeled off VIX/iVIX + put skew (SPX 0.90, NIFTY 0.50 vol-pt/100% mny), settle at realized intrinsic. Entry-IV→realized gap = VRP. Costs DRAFT (8bps+2bps/leg).

## Regimes (25-50-25)
- US = **CAPE**. q25=11.75 q75=21.07. **NOW 41.8 → deep RICH (near 150y high).**
- India = **P/B primary** (CAPE-analog, immune to 2020-21 earnings-collapse artifact that spikes trailing PE to 42). q25=3.37 q75=4.04. **NOW 3.19 → CHEAP.** PE now 21.06 → also CHEAP. Trailing-PE regimes shown as contaminated cross-check.

## Headline findings
- US RICH = strong CONCURRENT return (+10.8%) but weakest FWD-12m (+3.9%) + fattest tail (p10 −20.6%, worst −56%). India (10y growth sample) even RICH stays fwd-positive; CHEAP best fwd (+24%).
- **Best rollover HEDGE = ANNUAL COLLAR** (buy ~5% OTM put, sell 5–10% OTM call). US RICH: maxDD −52%→−15%, CVaR5 −37%→−6%, for ~3–4pp/yr. Tenor: annual ≫ semi ≫ qtr ≫ monthly (monthly pays skew 12×/yr).
- **Best DOWNSIDE PLAY for overvaluation mandate = small 1×2 PUT BACKSPREAD / defined-risk BEAR PUT SPREAD** (convex, near-zero carry). Premium-selling ratios (1×2/2×1) have highest avg expectancy + ~95% win but are SHORT the tail (worst −11%) → rejected on tail-risk grounds. Two opposite "downside" objectives — don't conflate.
- COVID (India entry 19-Feb-2020, iVIX 14, trough −37%): ATM put → hedged to −1.5%; long put +36%; 3:2 ratio +31%. Convexity bought CHEAP pre-spike >> its carry cost.
- Last 2y (no crash): US unhedged +40%, collar +14%, outright plays −20%; backspread1x2 only −1.3% (near-free convexity). Quantifies insurance drag.

## Recommendation NOW
- US (RICH): annual collar core + small 1×2 backspread kicker. Do NOT sell premium as "downside play".
- India (CHEAP): stay long, minimal hedge; escalate to collar programme if P/B > ~4.0.

## Caveats
Full-sample regime thresholds (hindsight for lines only). India 10y = one crash (COVID) → RICH benign in-sample. US pre-1990 IV modeled. Skew/term parametric. Directional conclusions robust; exact bps not.

## V2 BIAS CONTROLS (added 2026-07-08) — HEDGING_ANALYSIS_ADDENDUM_v2.docx
- **Winsorize [2.5,97.5]**: point estimates barely move (medians robust); extreme worst compressed (US FAIR fwd-worst -107%->-35%, RICH -56%->-46%). Raw tail kept via CVaR + raw-worst col. Rankings/conclusions unchanged.
- **Complete-market MEDIAN PE** (true cross-sectional median trailing PE, ~1,100 stocks PIT, annual EPS, 2016-2026; build_median_pe.py): median stock **25.6x now vs NIFTY50 cap-wt 21x** -> typical stock MORE expensive than index. **Regime FLIP: broad market = RICH** (medpe q75=25.0, now 25.6) vs cap-weighted NIFTY50 = CHEAP. Broad RICH shows WEAK fwd (+3.6%) = US-style asymmetry that cap-wt PB regime masked. **Revises v1 'India cheap, stay unhedged' -> large-caps cheap but median/broad market rich, warrants hedging.**
- **Small-cap (Nifty Smallcap 250)**: vol ~20% (vs 13% largecap), drawdowns -29%(RICH)/-53%(FAIR raw) — risk the index hides. RICH = highest concurrent (+30%)/weakest fwd (+5%) boom-bust. Qtrly collar cuts maxDD -29%->-17%. PRACTICAL: no liquid small-cap options in India -> executable hedge = NIFTY index puts (beta/basis risk) / short futures / cut exposure. Play expectancies = tiny sample (2-3 entries), indicative only.
- US breadth/small-cap (Russell 2000, US median PE): DATA GAP (proxy-blocked), noted not done.
- Current 3-lens read: NIFTY50 CHEAP / median-stock RICH / smallcap FAIR-but-high-vol. US = most extreme (CAPE 41.8).
