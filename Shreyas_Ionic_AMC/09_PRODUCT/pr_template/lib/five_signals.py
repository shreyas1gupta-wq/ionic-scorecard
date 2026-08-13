# -*- coding: utf-8 -*-
"""FIVE SIGNALS -- the seven scorecard pillars clubbed into five client-facing dimensions, each shown
as a traffic-light dot. Replaces the one-line prose commentary on the equity holdings page.
Principal, 2026-08-06 / 07.

SINGLE SOURCE OF TRUTH for the clubbing, the band floors, the words and the colours. The deck module
and the option-comparison sheets all import from here -- three copies of a threshold is three chances
to disagree about what green means.

THE CLUBBING (all 7 pillars represented, none dropped):
    Quality         <- quality_score
    Growth          <- growth_3y_score, the trailing revenue-CAGR percentile. UNCHANGED from the
                       original design (Principal, 2026-08-07: "keep the previous one we had at start")
    Value           <- value_score
    Technical       <- mean(stage_3y_score, accumulation_3y_score)          price/volume evidence
    Sector & Flows  <- mean(ownership_flow_3y_score, sector_macro_3y_score) who else is buying, and
                                                                           is the sector working

BANDS: four even quartiles (floors 75 / 50 / 25), per the Principal -- "25%ile 25%ile 25%ile 25%ile
for each colour". `T4` keeps the earlier tuned floors for comparison; see FLOORS for what each costs.

NO FORWARD DATA REACHES A DOT. Principal, 2026-08-07: the 60:40 EPS-to-revenue weighting he specified
belongs to the Ionic Score's forward ADJUSTMENT (the bonus/penalty points banded <5% / 5-10% / ... ),
NOT to this Growth signal. The signal is the trailing revenue-CAGR percentile it always was. The
forward adjustment lives in `fix_thin_coverage_v3.py`, where it belongs, and reaches the page only
through the Ionic Score column.

I had briefly blended the estimate into the dot at 50/50 and then at 60/40; both were wrong, for two
separate reasons worth recording so they are not repeated:
  * the estimate is expected EPS growth while the pillar is a trailing REVENUE rank -- different
    quantities, and averaging them yields a number that is neither; and
  * it was never what the 60:40 ruling referred to in the first place.
The conviction leg is likewise NOT smeared across the dots: a name-level adjustment applied to all five
would make two holdings with identical ROE show different Quality dots, and would turn the dots into a
restatement of the call rather than the evidence behind it. The call is already on the row, in the pill.

SCORE CAPS: composite scores are clamped to [5, 95] (Principal, 2026-08-07). Pillar percentiles are NOT
capped -- they are ranks, where 100 honestly means "first of 751".

COLUMN-NAME LANDMINE: the ownership pillar is `ownership_flow_3y_score` in the client scoring output
(portfolio_quant.csv) but `ownership_3y_score` in the 750-universe file (full750_scored.csv). Reading
only one name renders "no data" on every real client deck while looking perfect on the universe file
-- a silent gap, not an error. `_ALIASES` reads either.
"""
import csv
import json
import os

# House palette. Every value is EXACTLY a slidekit colour except DOTGREEN2, which is a tint of HOLD
# because the palette has no mid-green and "light greenish" must be unmistakably lighter than the dark
# green beside it.
GREEN, GREENBG = "#1E9E6A", "#E0F2EA"     # HOLD / HOLDBG
NAVY, NAVYBG = "#1B27A3", "#EEEFF7"       # NAVY / TRACK
AMBER, AMBERBG = "#92400E", "#FBEFDC"     # AMBER / AMBERBG
RED, REDBG = "#E0402F", "#FBE3E0"         # SELL / SELLBG
SLATE, SLATEBG = "#6B7280", "#E5E7EB"     # SLATE / HAIR
DOTGREEN2 = "#76C7A6"
YELLOW = "#F2A93C"                        # GOLD

# FIVE columns, FINAL (Principal, 2026-08-07): Quality, Growth, Value, Technical, Sector & Flows --
# in that order, Sector & Flows last. A sixth Cash (FCF-yield) signal was added and then REMOVED on his
# instruction the same day. The measurement that justified it still stands -- best spread of any
# candidate tested (5/11/33/10 on the real book), and it says something no other dot does, since ROE
# can be high while free cash flow is negative. It stays available as `cash_signal()` (and
# `safety_signal()`) for internal/analyst use; it is simply not a client-deck column.
CATS = ("Quality", "Growth", "Value", "Technical", "Sector & Flows")

# --------------------------------------------------------------------------------------------------
# ABSOLUTE-THRESHOLD SIGNALS.
#
# Everything above is a percentile rank. These two are not: they are banded on fixed, published-style
# thresholds, so a green dot means genuinely clean rather than merely cleaner than most of the 750. That
# also means they need no explanatory footnote at all -- which is the direction the page is moving.
#
# They are placed onto the SAME 0-100 band scale (band centre, not a real percentile) so one code path
# bands, colours and words every signal. `occupancy()` therefore counts them as if they were
# percentiles, which is fine for "is this column dead ink" and wrong for anything finer -- do not read
# those two rows as distribution statistics.
#
# CASH -- free-cash-flow yield. Measured on the real 98-holding book it spreads 5 / 11 / 33 / 10, the
#   best of every candidate tested, and it says something no other dot does: ROE can be high while free
#   cash flow is negative (working-capital-hungry growth). It currently sits buried inside Value at 0.20
#   weight, where a strong P/E can mask it entirely.
# SAFETY -- the frozen balance-sheet gate (RED caps the score at 40, AMBER multiplies by 0.85). Today it
#   moves the score but appears NOWHERE on the page, so a client cannot see that a holding is levered.
#   On this book it spreads only 44 / 11 / 4 / 0, so it earns its column as a risk DISCLOSURE, not as a
#   differentiator -- a PSU/infra/realty-heavy book would light it up far more.
# LIQUIDITY was tested and REJECTED: 56 of 59 names in the top band, median turnover 61x the size-tier
#   bar and the thinnest name still 4.8x. On a large/mid book it is 56 identical dots -- dead ink.
_BAND_CENTRE = (87.5, 62.5, 37.5, 12.5)
_FIN_KEYS = ("financial", "bank", "insurance", "nbfc", "capital market", "finance")


def _as_value(band_i):
    return None if band_i is None else _BAND_CENTRE[band_i]


def cash_signal(row):
    """FCF yield, %. Thresholds: >=5 strong, >=2 upper, >=0 lower, negative bottom.

    FINANCIALS ARE EXEMPT, and this is not a nicety. Free cash flow is not interpretable for a lender:
    deposits and borrowings run through operating/financing lines, so an FCF yield for a bank or an NBFC
    is an artefact of the cash-flow format rather than a fact about the business. The first build put
    Bajaj Finance on RED and HDFC Bank and SBI on yellow for Cash -- three meaningless dots that read as
    three real warnings. They return not-scored instead, exactly as the frozen method exempts financials
    from the D/E trigger."""
    if any(k in str(row.get("sector") or "").lower() for k in _FIN_KEYS):
        return None
    fy = _num(row.get("fcf_yield"))
    if fy is None:
        return None
    return _as_value(0 if fy >= 5 else (1 if fy >= 2 else (2 if fy >= 0 else 3)))


def safety_signal(row):
    """Frozen balance-sheet gate as four bands. Financial sectors are EXEMPT from the D/E trigger --
    leverage is their business model, and banding them on it would paint every bank red."""
    de, ic = _num(row.get("debt_equity")), _num(row.get("interest_coverage"))
    if de is None and ic is None:
        return None
    if any(k in str(row.get("sector") or "").lower() for k in _FIN_KEYS):
        de = None                                        # exempt, per the frozen method
    if (de is not None and de > 2.5) or (ic is not None and ic < 1.5):
        return _as_value(3)                              # RED gate
    if (de is not None and de > 1.5) or (ic is not None and ic < 3):
        return _as_value(2)                              # AMBER gate
    if (de is None or de <= 0.5) and (ic is None or ic >= 8):
        return _as_value(0)
    return _as_value(1)

# Traffic-light ramp, best band first. Index-aligned to FLOORS and to every WORDS set.
DOT_COLOURS = (GREEN, DOTGREEN2, YELLOW, RED)
# Chip inks, for the worded-chip rendering the dots replaced. Kept: the annexure may still want words.
CHIP_INKS = ((GREEN, GREENBG), (GREEN, "#FFFFFF"), (AMBER, AMBERBG), (RED, REDBG))

# Band floors, high to low. The last is always 0.
#   Q4  even quartiles, the Principal's choice. Simple to state, and the four bands are equal by
#       construction -- which is also its one cost: exactly half of all cells are below-average by
#       arithmetic, so 28% of HOLD rows show no green dot at all.
#   T4  tuned floors measured earlier: flatter occupancy (28/29/27/16 vs 20/30/31/19) and only 11% of
#       Hold rows with no green. Better on the numbers, harder to explain in one line.
FLOORS = {"Q4": (75, 50, 25, 0), "T4": (67, 45, 22, 0)}
DEFAULT_FLOORS = "Q4"

# Word sets for the legend, best band first. All four are index-aligned to DOT_COLOURS.
WORDS = {
    # Plainest ranked words. "Poor" carries the bottom band without the bluntness of "Bad".
    "plain": ("Strong", "Fair", "Weak", "Poor"),
    # The Principal's own suggestion.
    "blunt": ("Strong", "Okay", "Weak", "Bad"),
    # RELATIVE wording. The one set that needs no explanatory footnote: a percentile dot means "better
    # than most of the universe", and these words say exactly that, so the colour cannot over-claim.
    # Every other set invites the reader to hear an absolute grade -- "Strong" quality sounds like good
    # quality, when it only means top-quartile among the 750, and in an expensive market the greenest
    # Value dot is still expensive.
    "relative": ("Top 25%", "Upper", "Lower", "Bottom 25%"),
    # Neutral magnitude language, no praise or blame in it.
    "level": ("High", "Medium", "Low", "Very low"),
}
DEFAULT_WORDS = "relative"

NO_DATA_WORD = "Not scored"

_ALIASES = {
    "quality": ("quality_score",),
    "growth": ("growth_3y_score",),
    "value": ("value_score",),
    "stage": ("stage_3y_score",),
    "accum": ("accumulation_3y_score",),
    # both spellings seen in the wild -- see the landmine note above
    "ownership": ("ownership_flow_3y_score", "ownership_3y_score"),
    "sector": ("sector_macro_3y_score",),
}

# FROZEN growth-leg thresholds from the Ionic Score's forward adjustment (>=25 / 20-25 / 15-20 / 10-15
# / 5-10 / <5), re-expressed on the 0-100 scale so the analyst's forward figure can sit on the same
# axis as the trailing percentile. Nothing new is invented; these are the model's own bands.
#
# THE TWO LEGS MEASURE DIFFERENT THINGS, and that is a deliberate, Principal-ruled choice rather than an
# oversight: the trailing leg is a percentile rank of REVENUE CAGR, the forward leg is expected EPS
# growth. A company can compound EPS at 20% on 6% revenue through margin or buybacks, and this dot will
# read that as strong growth. That is the intended reading -- "Growth" here is the growth DIMENSION,
# evidenced by where revenue has been and where the desk expects earnings to go, not a single metric.
_FWD_BANDS = ((25.0, 92.0), (20.0, 80.0), (15.0, 65.0), (10.0, 50.0), (5.0, 30.0), (-1e9, 12.0))
# Principal, 2026-08-07: "let's take 60 growth in eps : 40 growth in revenue as final". EPS LEADS.
# Named per-leg rather than as one blend fraction: a single `FWD_BLEND = 0.40` is ambiguous about which
# side the 0.40 belongs to, and the first pass got it backwards (40% on EPS instead of 60%).
EPS_WEIGHT = 0.60         # analyst's expected EPS growth, mapped through _FWD_BANDS
REV_WEIGHT = 0.40         # trailing revenue-CAGR percentile (the frozen growth pillar)
assert abs(EPS_WEIGHT + REV_WEIGHT - 1.0) < 1e-9

# Score caps (Principal, 2026-08-07): no score below 5 or above 95. A 0 or a 100 claims a certainty the
# framework does not have -- there is always a worse company and always a better one, and a name pinned
# at the extreme cannot be distinguished from the next one out. Applied to composite scores, NOT to the
# pillar percentiles, which are ranks and where 100 simply means "first of 751".
SCORE_FLOOR, SCORE_CEIL = 5.0, 95.0


def cap_score(v):
    """Clamp a composite score into [SCORE_FLOOR, SCORE_CEIL]; passes NaN/None through untouched."""
    if v is None or v != v:
        return v
    return min(max(float(v), SCORE_FLOOR), SCORE_CEIL)


def _num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v != v else v          # NaN -> None, so callers test one thing


def _get(row, key):
    for c in _ALIASES[key]:
        if c in row:
            v = _num(row[c])
            if v is not None:
                return v
    return None


def _avg(row, *keys):
    vals = [v for v in (_get(row, k) for k in keys) if v is not None]
    return sum(vals) / len(vals) if vals else None


def fwd_growth_score(row):
    """The analyst's forward growth estimate on the 0-100 pillar scale, or None if not on file."""
    g = _num(row.get("growth_pct"))
    if g is None:
        return None
    for lo, score in _FWD_BANDS:
        if g >= lo:
            return score
    return _FWD_BANDS[-1][1]


def _blend_growth(row):
    """Growth = 60% expected EPS growth (mapped through the frozen bands) + 40% trailing revenue rank.
    Whichever leg exists if the other does not; None if neither does."""
    rev = _get(row, "growth")
    eps = fwd_growth_score(row)
    if eps is None:
        return rev
    if rev is None:
        return eps
    return EPS_WEIGHT * eps + REV_WEIGHT * rev


_COMPOSITE_DIST = None   # {"Technical": [...], "Sector & Flows": [...], "Growth": [...]}, all sorted


def _composite_dist(forward=False):
    """Universe distributions of the two COMPOSITE signals, for re-ranking.

    Why this exists: Quality, Growth and Value are single percentile ranks, so they are uniform and
    cutting at 75/50/25 gives four equal quarters. Technical and Flows & Sector are each the MEAN of two
    percentile ranks -- and the mean of two uniforms is triangular, not uniform. It piles up around 50.
    Measured on the real book, cutting the raw means at 75/50/25 gave 25/29/30/16 rather than four 25s:
    the middle bands fatten and the tails starve, precisely because of those two signals.

    So the composites are re-ranked against the universe's own distribution of the same composite. That
    restores uniformity and makes "a quarter of the universe in each colour" literally true instead of
    approximately true. It changes no pillar weight and no underlying score -- it only fixes the fact
    that an average of two ranks is not itself a rank."""
    # Keyed by `forward`. The distribution MUST be built the same way the values are, or every name is
    # ranked against a quantity that is not its own. That happened: the cache was built with the
    # default forward=True while signals() computed forward=False, and the Growth column came out
    # 267/250/123/104 -- a barbell, the opposite of quartiles -- because trailing-revenue values were
    # being ranked against an EPS-blended distribution.
    global _COMPOSITE_DIST
    if _COMPOSITE_DIST is None:
        _COMPOSITE_DIST = {}
    if forward in _COMPOSITE_DIST:
        return _COMPOSITE_DIST[forward]
    acc = {c: [] for c in CATS}
    for _sym, rec in load_universe().items():
        for cat, v in _raw_signals(rec, forward=forward):
            if v is not None:
                acc[cat].append(v)
    _COMPOSITE_DIST[forward] = {c: sorted(v) for c, v in acc.items()}
    return _COMPOSITE_DIST[forward]


def _pctile_of(value, sorted_vals):
    """Percentile rank of `value` within `sorted_vals`, 0-100. Falls back to the raw value when the
    universe is unavailable -- a slightly mis-banded dot beats no dot."""
    n = len(sorted_vals)
    if value is None or n == 0:
        return value
    lo, hi = 0, n
    while lo < hi:                                        # bisect_left, no import needed
        mid = (lo + hi) // 2
        if sorted_vals[mid] < value:
            lo = mid + 1
        else:
            hi = mid
    return lo / n * 100.0


def signals(row, forward=False, rerank=True):
    """row: any mapping (dict / pandas Series / ctx equity entry) -> [(category, value|None), ...] in
    fixed CATS order. None means genuinely not scored and must render as a hollow ring, never a colour.

    `forward=True` makes the Growth dot 60% the analyst's expected EPS growth and 40% the trailing
    revenue percentile (Principal, 2026-08-07). Read as: mostly where the desk expects earnings to go,
    partly where revenue has actually been. With no EPS estimate on file the trailing rank stands alone
    -- the dot degrades to backward-looking rather than disappearing, which is the right trade for one
    signal of five. See `_FWD_BANDS` for why the EPS leg must be mapped before it can be averaged."""
    raw = dict(_raw_signals(row, forward=forward))
    if not rerank:
        return [(c, raw.get(c)) for c in CATS]
    # RE-RANK EVERY SIGNAL against the universe, not just the obviously-composite ones.
    # The legend labels the bands "Top 25% / Upper / Lower / Bottom 25%", which is only true if each
    # column is uniformly distributed -- and NONE of the five is, because every one is a blend:
    # Quality is the mean of two ranks, Value a weighted mix of four, Growth 60/40 EPS-and-revenue,
    # Technical and Sector & Flows the mean of two each. A blend of ranks is not itself a rank; it
    # clusters mid-scale. Measured before this fix: Value came out 32/32/19/13 and blended Growth
    # 12/37/40/11 instead of four quarters. Re-ranking each signal against the universe's own
    # distribution of that same signal restores the quarters and makes the legend literally true.
    dist = _composite_dist(forward=forward)
    return [(c, _pctile_of(raw.get(c), dist.get(c, []))) for c in CATS]


def _raw_signals(row, forward=True):
    """The five signals BEFORE universe re-ranking. Split out so `_composite_dist()` can build the
    distribution from exactly the same construction `signals()` ranks against -- if these two ever
    diverged, every name would be ranked against a quantity that is not its own."""
    out = {
        "Quality": _get(row, "quality"),
        "Growth": _blend_growth(row) if forward else _get(row, "growth"),
        "Value": _get(row, "value"),
        "Cash": cash_signal(row),          # not in CATS -- kept for internal/analyst use
        "Technical": _avg(row, "stage", "accum"),
        "Sector & Flows": _avg(row, "ownership", "sector"),
        "Safety": safety_signal(row),      # not in CATS -- kept for internal/analyst use
    }
    # CATS is the single place that decides which signals appear and in what order, so adding or
    # dropping a column is a one-line change there rather than an edit in three files.
    return [(c, out.get(c)) for c in CATS]


def band_index(value, floors=DEFAULT_FLOORS):
    """-> 0 (best) .. 3 (worst), or None when not scored."""
    if value is None:
        return None
    for i, lo in enumerate(FLOORS[floors]):
        if value >= lo:
            return i
    return len(FLOORS[floors]) - 1


def word(value, floors=DEFAULT_FLOORS, words=DEFAULT_WORDS):
    i = band_index(value, floors)
    return NO_DATA_WORD if i is None else WORDS[words][i]


def dot(value, floors=DEFAULT_FLOORS):
    """-> fill_hex, or None when not scored (caller draws a hollow grey ring)."""
    i = band_index(value, floors)
    return None if i is None else DOT_COLOURS[i]


def chip(value, floors=DEFAULT_FLOORS, words=DEFAULT_WORDS):
    """-> (label, fg_hex, bg_hex) for the worded-chip rendering."""
    i = band_index(value, floors)
    if i is None:
        return NO_DATA_WORD, SLATE, SLATEBG
    fg, bg = CHIP_INKS[i]
    return WORDS[words][i], fg, bg


def legend(floors=DEFAULT_FLOORS, words=DEFAULT_WORDS):
    """[(word, fill_hex), ...] best to worst. No percentages: the Principal's instruction is that the
    legend stays four words and four colours, nothing else."""
    return [(WORDS[words][i], DOT_COLOURS[i]) for i in range(len(DOT_COLOURS))]


def to_rgb(hex_str):
    """'#1E9E6A' -> pptx RGBColor. Imported lazily so this module stays usable without python-pptx."""
    from pptx.dml.color import RGBColor
    h = hex_str.lstrip("#")
    return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


# --------------------------------------------------------------------------------------------------
# Getting the pillars INTO the deck's context.
#
# The deck data files (data/*.py) carry `ionic_score` but no per-pillar scores -- they were written when
# this page showed one prose line. Without a join, `signals()` returns all-None and the page ships as a
# wall of hollow rings: technically honest, useless, and it would have looked finished. So the pillars
# are joined from the scoring output by symbol at build time. No data file is hand-edited, and a rescore
# flows through automatically.
# --------------------------------------------------------------------------------------------------
_PILLAR_COLS = ("quality_score", "growth_3y_score", "value_score", "stage_3y_score",
                "accumulation_3y_score", "ownership_flow_3y_score", "ownership_3y_score",
                "sector_macro_3y_score",
                # raw inputs for the absolute-threshold signals -- these are NOT pillar scores, but
                # they come from the same scoring output and the Cash/Safety dots are blank without them
                "fcf_yield", "debt_equity", "interest_coverage")
# Client scoring output first: it is the per-client run and its figures are the ones the rest of the
# deck quotes. The 750-universe file is the fallback for a holding scored in the universe sweep but not
# in this client's run.
_SOURCES = (("04_RND_LAB", "STOCK_SCORECARD_750", "results", "portfolio_quant.csv"),
            ("04_RND_LAB", "STOCK_SCORECARD_750", "results", "full750_scored.csv"))
_UNIV = None


def _nifty_root():
    """Walk up to the repo root -- the directory that CONTAINS `Shreyas_Ionic_AMC`.

    This used to match on a directory literally named "NIFTY 500", which is only true on the Principal's
    machine. A fresh `git clone` produces a folder named after the repo (`ionic-scorecard`), so the walk
    found nothing, `load_universe()` returned {}, and every signal dot rendered as a hollow "not scored"
    ring -- on a deck that otherwise built cleanly, with no error anywhere. Caught 2026-08-07 by
    exporting the tracked files to a temp directory and building from there.

    Anchoring on the folder that contains `Shreyas_Ionic_AMC` is the real invariant: it holds under any
    clone name, inside a git worktree, and on the Principal's own tree. The legacy name is kept as a
    fallback for the case where this file is used outside the firm layout."""
    p = os.path.abspath(__file__)
    while True:
        p, tail = os.path.split(p)
        if not tail:
            return None
        cand = os.path.join(p, tail)
        if os.path.isdir(os.path.join(cand, "Shreyas_Ionic_AMC")) or tail == "NIFTY 500":
            return cand


def load_universe():
    """{SYMBOL: {pillar_col: float}} merged across the scoring outputs. Cached; returns {} if none is
    readable, and the caller then renders "not scored" rather than inventing a figure."""
    global _UNIV
    if _UNIV is not None:
        return _UNIV
    _UNIV = {}
    root = _nifty_root()
    if root is None:
        return _UNIV
    for parts in reversed(_SOURCES):                      # weaker source first, stronger overwrites
        path = os.path.join(root, "Shreyas_Ionic_AMC", *parts)
        if not os.path.exists(path):
            continue
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                for rec in csv.DictReader(fh):
                    sym = (rec.get("symbol") or rec.get("Symbol") or "").strip().upper()
                    if not sym:
                        continue
                    got = {c: _num(rec[c]) for c in _PILLAR_COLS
                           if c in rec and _num(rec[c]) is not None}
                    if got:
                        _UNIV.setdefault(sym, {}).update(got)
        except (OSError, csv.Error):
            continue

    # Forward EPS estimates, from the per-name research files. Needed here and not only in the Excel:
    # the blended Growth signal is re-ranked against the UNIVERSE, so the universe rows must carry the
    # same EPS leg the client rows do. Without this the client book would be ranked against a
    # revenue-only distribution while its own values are blended -- comparing two different quantities,
    # which is exactly the failure the re-ranking exists to prevent.
    qual_dir = os.path.join(root, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750", "results")
    try:
        for fn in os.listdir(qual_dir):
            if not (fn.startswith("pf_qual_") and fn.endswith(".json")):
                continue
            sym = fn[len("pf_qual_"):-len(".json")].strip().upper()
            try:
                with open(os.path.join(qual_dir, fn), "r", encoding="utf-8") as fh:
                    v = _num(json.load(fh).get("expected_next_3y_growth_pct"))
            except (OSError, ValueError, TypeError):
                continue
            if v is not None:
                _UNIV.setdefault(sym, {})["growth_pct"] = v
    except OSError:
        pass
    return _UNIV


def enrich(entries):
    """Fill missing pillar fields on ctx equity entries, in place, by symbol. Never overwrites a value a
    data file already states -- a hand-set figure is a deliberate act. Returns (n_matched, n_total) so
    the caller can disclose coverage instead of quietly showing a sparse grid."""
    univ = load_universe()
    matched = 0
    for e in entries:
        sym = str(e.get("symbol") or "").strip().upper()
        src = univ.get(sym)
        if not src:
            continue
        # setdefault on every column, with no short-circuit. An earlier version skipped the whole
        # holding once it found ANY pillar already set, which meant a data file stating one figure by
        # hand silently blocked the Cash and Safety inputs from ever being filled.
        for col, val in src.items():
            e.setdefault(col, val)
        matched += 1
    return matched, len(entries)


def occupancy(rows, floors=DEFAULT_FLOORS, forward=True):
    """(per-band [(word, n, pct)], n_scored, n_not_scored). The number that decides whether a band set
    is usable: a band nothing lands in is decoration, one half the grid lands in says nothing."""
    counts = [0] * len(DOT_COLOURS)
    n_na = 0
    for r in rows:
        for _c, v in signals(r, forward=forward):
            i = band_index(v, floors)
            if i is None:
                n_na += 1
            else:
                counts[i] += 1
    n = sum(counts)
    return ([(WORDS[DEFAULT_WORDS][i], counts[i], (counts[i] / n * 100.0) if n else 0.0)
             for i in range(len(counts))], n, n_na)
