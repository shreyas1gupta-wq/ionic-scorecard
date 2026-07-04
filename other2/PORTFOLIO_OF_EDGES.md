# PORTFOLIO OF EDGES — cross-market / cross-asset architecture
Built 2026-06-16. Strategic layer above all three tracks. Read with RESUME_TOMORROW.md.

## THE THESIS (why this is worth it)
Stacking N truly-uncorrelated edges of equal Sharpe on the SAME capital lifts
portfolio Sharpe ~√N (3 uncorrelated Sharpe-1.5 sleeves → ~2.6; 5 → ~3.4) and cuts
drawdown — the one real free lunch. Same capital, sequential/parallel deployment,
lower effective risk, higher compounding. This is the goal.

## THE HONEST TRAP (must not get this wrong)
**Geography is NOT diversification.** US and Indian equities are positively correlated
(~0.4–0.7) and correlations → ~1 in risk-off crises (exactly when you need
diversification). Buying US stocks AND Indian stocks = mostly the same equity-beta bet.
**Real uncorrelation comes from two axes, not geography:**
1. **Edge TYPE** — momentum (directional) vs short-vol (carry/mean-reversion) vs
   fragility/long-gamma (convexity) vs trend-following vs carry. These have
   structurally different return drivers → genuinely low correlation, even crisis-robust
   (short-vol and long-gamma are literally opposite-signed).
2. **Asset CLASS** — equities vs commodities (gold, crude, metals) vs bonds vs FX vs
   volatility. Gold/managed-futures are the classic equity diversifiers (crisis alpha).
**Design rule:** diversify across EDGE TYPE and ASSET CLASS first; geography (US/India)
second. A US momentum sleeve + Indian momentum sleeve is ~1 edge; a momentum sleeve +
a short-vol sleeve + a commodity-trend sleeve is ~3 edges.

## TIMEZONE = genuine capital efficiency (a real win)
- Indian session 09:15–15:30 IST; US session 19:00–01:30 IST (post-DST ~18:30).
- They DON'T overlap → the SAME capital can run an Indian intraday sleeve by day and a
  US intraday/overnight sleeve by night. Sequential reuse of capital = true efficiency,
  not just diversification. (Settlement/margin timing must be managed across brokers.)

## ACCESS MATRIX (tradeable from India, 2026)
| Venue | Instruments | Notes / constraints |
|---|---|---|
| **Kite / Zerodha** | Indian equities, index & stock F&O, MCX commodity futures (gold, silver, crude, natgas, copper, zinc), currency F&O | Full intraday + derivatives. Our 0DTE short-vol + Indian swing live here. |
| **INDmoney** (LRS) | US stocks + US ETFs (equity SPY/QQQ, **commodity GLD/SLV/USO/DBC**, bond TLT, sector, intl) | Indian-resident US investing via RBI LRS. Fractional shares. |
| Access GAPS | **No easy US OPTIONS for retail Indians**; no cheap US intraday leverage; US day-trade culture/PDT differs | → the short-VOL edge stays INDIAN (Nifty/BankNifty/Sensex). US/INDmoney = mostly SWING/positional equities+ETFs. |
| Frictions | **LRS $250k/yr/person cap; TCS on remittance (20% above ₹7L, refundable/adjustable); US 25% dividend withholding; Indian cap-gains on foreign assets (no LTCG benefit pre-24m); USD/INR FX risk; brokerage/forex spread** | Tax & FX drag is REAL — model net-of-all-in. US sleeve must clear a higher hurdle. |

## THE EDGE × ASSET × MARKET GRID (where each sleeve lives)
| Sleeve (edge type) | Asset / market | Venue | Status |
|---|---|---|---|
| 0DTE/DTE1 short-vol (carry) | Nifty/BankNifty/Sensex options | Kite | ✅ validated (Track1) |
| Momentum leadership swing (directional) | Indian stocks | Kite | Track2 (planned) |
| Momentum leadership swing (directional) | US stocks + sector ETFs | INDmoney | Track2 extension |
| Commodity TREND/momentum (different driver) | MCX futures + US commodity ETFs (GLD/USO/DBC) | Kite/INDmoney | NEW — true diversifier |
| Fragility / long-gamma (convexity) | Indian options (H3) | Kite | Track3 H3 — hedges the short-vol |
| Participant-state/flow (forced flows) | Indian F&O | Kite | Track3 H1/H2 |
| Cross-asset trend-following (crisis alpha) | gold/bonds/commodity ETFs | INDmoney | NEW — managed-futures style |

## CAPITAL ALLOCATION (reuse what we built)
Use the `intraday_options_strategy\portfolio\allocator.py` framework (vol-parity +
rolling-Sharpe kill-switch + 0.25-Kelly cap + drawdown governor), generalised to all
sleeves across markets. Allocate by RISK (vol target), not rupees; cap any sleeve;
size the US sleeves NET of LRS/tax/FX drag; respect the ≤₹10Cr capacity ceiling per
capacity-limited sleeve.

## RISKS specific to going multi-market
- Crisis correlation spike (equity sleeves converge) → why we need the vol/commodity/
  short-gamma legs that are crisis-robust.
- FX (USD/INR) overlay on all US holdings — decide hedged vs unhedged (unhedged adds
  INR-depreciation tailwind historically but is a separate bet).
- Operational: 2+ brokers, 2 timezones, 2 tax regimes, reconciliation, funding latency
  (LRS remittance takes days — can't move capital US↔India intraday).
- LRS cap limits US capital scale — fine given our ≤₹10Cr small-capacity philosophy.

## ACTION ITEMS (fold into track plans)
- [ ] Track2 swing PLAN: expand universe to (a) Indian stocks, (b) US stocks+ETFs via
      INDmoney, (c) commodity ETFs/MCX — same leadership/momentum engine, per-market
      data + cost/tax/FX model. Add a commodity-TREND sleeve (different driver).
- [ ] Build a cross-asset PORTFOLIO allocator (generalise allocator.py) over ALL sleeves;
      measure realised cross-sleeve correlations (target avg |rho| < 0.3) and crisis-
      regime correlation; report portfolio Sharpe/DD vs best single sleeve.
- [ ] Data: US EOD (stocks+ETFs), MCX commodity history, USD/INR — for backtest.
- [ ] Net-of-friction model for US sleeves (LRS TCS, withholding, cap-gains, FX, brokerage).

## BOTTOM LINE
Multi-market is right — but the diversification must come from EDGE-TYPE and
ASSET-CLASS variety (momentum + short-vol + commodity-trend + long-gamma), with
geography as a secondary breadth boost. The short-vol edge stays Indian (no US retail
options); US/INDmoney is the SWING/positional + commodity/bond diversifier. Allocate by
risk, model US frictions honestly, and the same ≤₹10Cr capital runs more, lower-risk,
higher-compounding edges across the Indian day and the US night.
