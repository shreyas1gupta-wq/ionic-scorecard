# 03 — Oversight Cascade (global → national → sector → stock)

The cascade is the "top-down sanity and regime" layer that sits over the bottom-up factor score. It answers: *is the wind at this stock's back or in its face, right now, at this horizon?* It **gates or shifts** the composite score and **forces a written justification** whenever an analyst/agent overrides a cascade signal (per brief Q13 — it is not a rigid gate, but overriding it must be argued).

## Four levels
### L-G — Global
Inputs (public, scrapable): US 10Y yield & curve, DXY, Fed stance/dot-plot, global risk-on/off (S&P/VIX, EM equity flows), crude (Brent/WTI), **gold & silver + gold/silver ratio**, industrial metals, global PMIs, China growth/credit impulse, shipping/freight, geopolitics/conflict/tariff headlines.
Effect: sets the *risk-appetite backdrop* and the commodity-cost axis. Risk-off global → down-weight high-beta/expensive-growth, up-weight quality/low-vol; expensive commodities → sector-specific (good for producers, bad for consumers of that input).

### L-N — National (India)
Inputs: RBI repo & stance, system liquidity, **credit growth**, 10Y G-sec & spreads, INR, CPI/WPI, IIP, GDP nowcast, **FII/DII net flows**, fiscal/budget, GST collections, PMI, election/policy calendar.
Effect: sets the domestic **regime tuple** (see `02` Step 4). The credit/rate axis is what flips red-flag severity (a leveraged/pledged name is fine in easy credit, lethal in a credit scare).

### L-S — Sector
Inputs: sector index relative strength & breadth, input-cost cycle (e.g. crude→paints/aviation, steel→autos, API→pharma), pricing power/demand cycle, regulatory pipeline (RBI/SEBI/IRDAI/USFDA/tariffs), capex cycle position, channel/volume data, competitive intensity/disruption (the **AI-vs-IT-services** structural axis).
Effect: sector **tailwind/headwind** score. A sector headwind can cap all names in that sector at a reduced score band unless the stock has an idiosyncratic offset (argued in writing).

### L-Stock (handoff to bottom-up)
The bottom-up factor/theme score from `02`. The cascade modifies it; it does not replace it.

## How the cascade modifies the score
```
tailwind_S = f(sector RS, input-cost cycle, regulatory, demand cycle)   ∈ [-1, +1]
macro_beta_i = stock's sensitivity to the active global/national axes      # estimated
cascade_shift_i = α · tailwind_S + β · (macro_beta_i · risk_appetite)
composite'_i = composite_i + cascade_shift_i · scale[horizon]
# gate:
if sector headwind severe AND horizon in {1M,1Y}:
     composite'_i = min(composite'_i, HEADWIND_CAP) unless override_with_reason
```
- `scale[horizon]`: cascade matters **most at 1M–1Y** (regime/flow timing) and **least at 5Y** (a great compounder rides through cycles — but a *structural* headwind like disruption still bites at 5Y, so the disruption axis is exempt from the low-5Y-scaling).
- Every gate/cap that an agent overrides writes `{who, what, why}` into `overrides[]`.

## Structural vs cyclical headwind (critical distinction)
- **Cyclical** headwind (input cost high, demand soft) → temporary, mean-reverts; scale down its 5Y weight.
- **Structural** headwind (technology obsolescence, permanent regulatory shift, TAM shrinking) → permanent; it **dominates the 5Y score** and can veto a "quality" name (the brief's "quality with structural change is bad" — e.g. AI compressing IT-services value, or generic pricing collapse). The cascade must classify which one it is and route accordingly.

## Tailwind detection (the upside mirror)
Same machinery, positive: formalization/penetration themes, policy tailwind (PLI, capex, defence indigenization), input-cost tailwind, credit up-cycle for financiers, structural TAM growth. A durable structural tailwind is a large positive at 5Y.

## Guidance & anticipation feed (into the cascade + catalyst theme)
- **Management guidance** (guidance credibility, tone shift vs prior quarters, capex language, promise-vs-delivery tracking) — see `08` §Concall rubric — feeds the sector demand read and the stock catalyst/forensic themes.
- **Earnings anticipation** (estimate-revision breadth, historical beat/miss, pre-results positioning, IV where F&O exists) feeds the 1M catalyst theme specifically.

## Regime → red-flag coupling (one-line reminder)
The National credit/rate axis and the market-valuation axis set the `regime_mult` in the forensic overlay (`02` Step 6). This is the mechanism behind "a pledge is benign in one regime and suicidal in another."

## Data owners
See `09_DATA_LAYER.md` §Macro for exact sources (RBI/FRED/MOSPI/NSE flows/Stooq). The **macro-strategist agent** (`10`) owns this layer and produces a dated `regime_state.json` each run.
