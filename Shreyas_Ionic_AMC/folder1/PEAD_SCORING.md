# PEAD Score — Methodology

The **PEAD Score** grades a single quarterly result on a 0–100 scale for how
"fly-worthy" the print is: a big, clean, durable earnings beat that tends to
*drift* in the weeks after results, rather than routine 15%-type growth. It is
purely fundamental — it uses no price or volume. The trader handles the tape,
entries and exits manually; this score is the durability filter that a raw
growth screener can't give you.

The math below is the single source of truth. It is implemented identically in
`pead_score.py` (Python) and in the tracker web app's JavaScript (`scoreEP`).
If you change one, change the other, or the app and the offline scorer will
disagree.

## Inputs (per company, one reported quarter)

| Field | Meaning |
|---|---|
| `salesYoY`, `salesQoQ` | Sales growth, year-on-year and quarter-on-quarter (%) |
| `opYoY` | Operating profit growth YoY (%) |
| `npYoY`, `npQoQ` | Net profit growth YoY and QoQ (%) |
| `sMar` / `sDec` / `sPrev` | Sales — latest / previous / year-ago quarter (₹ Cr) |
| `opMar` / `opPrev` | Operating profit — latest / year-ago quarter (₹ Cr) |
| `npMar` / `npDec` / `npPrev` | Net profit — latest / previous / year-ago quarter (₹ Cr) |

`clamp(x, 0, 1)` means "cap `x` between 0 and 1". Any missing input simply
contributes nothing to its term.

## The four pillars

### 1. Growth magnitude — max 30
Rewards the *size* of the beat, scaled so only genuinely large numbers earn
full marks (not 15% growth).

```
+ clamp((npYoY  - 25) / 75, 0, 1) * 14     # PAT growth: 25% earns 0, 100% earns full 14
+ clamp((salesYoY - 8) / 22, 0, 1) *  8     # sales growth: 8% earns 0, 30% earns full 8
+ clamp((opYoY  - 15) / 45, 0, 1) *  8     # OP growth: 15% earns 0, 60% earns full 8
```

### 2. Acceleration — max 20
Rewards sequential momentum and the latest quarter breaking above recent levels.

```
+5 if salesQoQ > 0        # top line still rising sequentially
+5 if npQoQ   > 0         # bottom line still rising sequentially
+5 if npMar > npDec       # PAT above the previous quarter (absolute level)
+5 if npMar > npPrev      # PAT above the year-ago quarter (absolute level)
```

### 3. Margin / operating leverage — max 25
Rewards margin expansion and profit growing faster than sales (real leverage).

```
if opMar, sMar, opPrev, sPrev all > 0:
    OPM_latest  = opMar / sMar * 100
    OPM_yearago = opPrev / sPrev * 100
    + clamp((OPM_latest - OPM_yearago) / 4, 0, 1) * 13   # +4 margin pts earns full 13

if opYoY > salesYoY:
    + clamp((opYoY - salesYoY) / 30, 0, 1) * 12          # +30pt gap earns full 12
```

### 4. Quality of beat — start at 25, subtract; floor at 0
Docks points for beats that are low-quality or optically inflated, and raises a
human-readable flag for each.

```
start q = 25
-12  flag "NP up OP down"   if opYoY <= 0 and npYoY > 0     # profit up while operations shrank
else
-8   flag "NP>>OP"          if npYoY > opYoY + 40           # PAT far outrunning OP (other income / tax / one-off tell)
-8   flag "sales down"      if salesYoY < 0 and npYoY > 0   # profit up on falling revenue
-10  flag "low base"        if abs(npMar) < 5               # tiny absolute PAT -> % illusions
-15  flag "loss qtr"        if npMar < 0                    # loss quarter
q = max(q, 0)
```

## Total and grade

```
total = round(growth + acceleration + margin + quality)

grade:  >= 75  A  (Prime)
        >= 60  B  (Strong)
        >= 45  C  (Watch)
        else   D  (Weak)
```

## Important caveat — banks & NBFCs
Financials report an unconventional "operating profit", so the margin and
quality pillars can misfire for them. Treat A/B grades on banks/NBFCs with extra
caution and cross-check the actuals before acting.

## Worked examples (from the sample feed)

- **Bhansali Engg. Poly. — 67, B, clean.** Sales +53%, OP +57%, PAT +43%, all
  three pillars firing together, margins up, no quality flags. The archetype of
  a clean, broad-based beat worth charting.
- **Sangam (India) — 79, A, flag: NP>>OP.** Highest score, but PAT +1825% vastly
  outruns OP +83% — the profit jump is off a tiny year-ago base (₹2.13 Cr), so
  the flag warns you the headline % is an optical artefact.
- **India Cements — 69, B, flag: sales down.** Strong OP and PAT growth but sales
  fell YoY — profit improvement isn't demand-led; flagged accordingly.

## How to read the output
Filter to **mcap > 500 Cr** first (the working universe), sort by score, then
eyeball only the **A/B, flag-clean** names on the chart for a 5%+ gap. Flags
don't disqualify a name automatically — they tell you exactly what to verify
before you trust the print.
