# Mapping a holding to its sleeve, band and category

Every wrong number on a client page that was not a wrong call was a wrong mapping.

## The one exact test

`INF` = a mutual-fund unit. `INE` = a company security. India issues them that way, so the share /
scheme split needs no lookup and no judgement.

```python
_share_isin = {i for i in isins if str(i).startswith("INE")}
```

Direct shares are removed from `funds` and added to `equity_rows` with their own published call.
**The pre-split frame still contains them.** Writing it alongside `equity_rows` listed every share
twice - once as the No View the fund score file has for it, once with its real call - which on one
family was 124 duplicated lines and `₹2.43 Cr` of double-counted value in a workbook whose whole
purpose is to reconcile. Export `_G_FUNDS = G[~G.isin.isin(_share_isin)]`, never `G`.

## Never match a fund by name

A scheme's name changes; its ISIN does not.

- HSBC Value Fund **is** the old L&T India Value Fund.
- Today's Kotak Midcap Fund is the old Kotak Emerging Equity, while the *old* Kotak Midcap became
  Kotak Small Cap in 2018.

String similarity gets both of these wrong and gets them wrong confidently. Where a name must be
resolved to a scheme identity and the ISIN is absent, it is a Sonnet agent, one fund at a time, with
a web search and scheme-identity reasoning. "Not found" beats a wrong guess.

## Category is authoritative over name

`parse/tag_risk_liquidity.py` decides the sub-category, and the **statement's category column wins**
over anything readable in the name.

### `sub_for_fund` refuses direct-equity categories

It returns `None` for anything categorised as direct equity. Without that, "STATE BANK OF INDIA"
mapped to "Thematic / Sectoral Fund" through the sector regex - a listed bank filed as a sector
fund, with a sector fund's risk band.

### `sub_for_other`: instrument before issuer

A word like "bank" in a security's name is the **issuer**, not the instrument. "State Bank of India
NCD 2029" and "Bank of Baroda Infrastructure Bond" are a debenture and a bond, and neither is a
deposit. The order is:

```
small savings (PPF / SCSS / EPF / NSC / KVP / Sukanya)
  -> SDL -> T-Bill -> perpetual/AT1/Tier-2 -> savings account
  -> deposit (small-finance/NBFC tested BEFORE scheduled-commercial)
  -> NCD -> bond -> bare "bank" fallback, last
```

### Small savings arrive as their own category

The statements this desk sees simply say `PPF`, `SCSS`, `Fixed deposit`, `ULIP`, `PMS`. Those are
in `CATEGORY_TO_SUB` and never reach the instrument tests, which only run for `direct fixed income`.
Before they were mapped, `₹70 L` of fifteen- and five-year money arrived with **no** risk band, **no**
liquidity band and **no** days-to-cash, and then dropped out of the lock-in test and the liquidity
page entirely - reported as neither locked in nor illiquid, because it was reported as nothing at
all.

A generic category is still refined by the name where the credit differs: `Fixed deposit` +
"small finance banks" is not a scheduled-commercial deposit and must not be banded as one.

### `_by_leaf()` leaf-exact fallback

Closes 18 unmapped SEBI categories where the full string differs but the leaf is exact.

## The risk and liquidity bands

`scores/risk_liquidity_bands.csv`, published centrally. Two **independent** axes:

- **risk** is the worst material driver, never an average
- **liquidity** is the tightest binding constraint, and position size is part of it

`days_to_cash` is the first date the money can be reached **without forfeiting the scheme** - PPF
allows one partial withdrawal a year from year seven (2555), SCSS runs a five-year term (1825).

A holding with no band is reported as unbanded, in rupees, on the coverage page. It is never
silently dropped and never given a default band.

## Gold and silver share one band

The framework's sub-category is `Gold / Silver ETF or FoF` - one band, both metals. A gold ETF's own
sub-category string therefore contains the word "silver", and counting on that word printed an
identical `3.7%` against a Gold row (ALIGNED) and a Silver row (PENDING) on a book holding no silver
at all. A holding the client does not own, reported to them as held.

The row is named for what the band covers: **Gold and silver**, one row, unless the profile carries
a separate silver band.

## Bands are bands, not caps

`cash_cap_pct` and `international_equity_cap_pct` are **tuples**. Cash is 1-3% and international
equity 10-25% in the Aggressive profile. Publishing only the upper bound threw the floor away, and a
book at 0.4% cash against a 1% minimum and 3% international against a 10% minimum were both stamped
ALIGNED - two real breaches reported as compliant, in the direction that never gets questioned.

Rows whose mandate genuinely has no floor (thematic, unlisted, locked-in, single AMC) keep a scalar
cap.

## Asset class vs look-through

Two equity numbers, both true, and a page that prints both must name each:

- the **donut** is the asset class as the statement classifies each holding
- the **strip** looks through every fund to what it actually owns, which is higher wherever a hybrid
  or multi-asset scheme is held

One page printed 62% in its read line under a header saying 66% and named neither basis.

Look-through equity is **gross** (Principal ruling 2026-08-05), disclosed by footnote, never a
per-row flag. The four-segment version (`full_lookthrough_mix`) reconciles to the whole book,
including each fund's own "Others" slice - REITs, InvITs, margin, unclassified - which the old
three-segment strip silently dropped.

## The `\b` trap

Writing Python through a shell heredoc turns `\b` into a literal backspace byte (`0x08`), which
compiles fine and matches nothing. It has bitten this codebase four times. Either use the Edit tool,
or build the pattern as `chr(92) + "b"`. Check with:

```bash
grep -c $'\x08' <file>
```
