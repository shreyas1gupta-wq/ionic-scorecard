# -*- coding: utf-8 -*-
"""mf_sell_score.py — Layer 2 (saturating non-linear score), Layer 3 (discretion band) and
Layer 4 (escalation payload) of the agreed MF sell method
(09_PRODUCT/MF_SELL_METHOD_SPEC_2026-08-05.md, FM #17: "create it and show me best way logically
we cannot backtest"). Layer 1 (hard gates) lives in mf_sell_gates.py and is NOT duplicated here:
this module only scores a holding that already survived Layer 1 — "Gates run before scoring...
a gated holding never receives a score" (spec). score_all() enforces that boundary for you.

WHY EVERY NUMBER BELOW IS A JUDGEMENT, NOT A FIT
--------------------------------------------------
The Principal is right that this cannot be backtested: the AI-analyst/FM discretion layer cannot
be reconstructed historically, and the fund-sell rule has never traded. So every curve shape and
cut-off here is derived from a STATED PRINCIPLE (written next to it below) rather than a fitted
number. Where no house principle exists, the value is a DOCUMENTED DEFAULT — flagged as such,
living in CONFIG, and covered by mf_sell_score_sensitivity.py's sweep (09_PRODUCT/scripts/), which
is the substitute for a backtest: it shows how many Sell/Discretion/Hold calls move when a
parameter is nudged +-20%, so the FM can see which numbers matter before arguing about them.

THE COMBINATION RULE (stated once, because it is the whole design)
--------------------------------------------------------------------
The spec rejects a linear weighted sum at the top level: a good score on one axis can pay for a
disqualifying score on another ("a broken risk profile ... averages out to hold"). A plain
average of five saturating axis-scores would quietly reintroduce exactly that compensation one
level down. So the five scored axes combine by MAX, not sum or mean: the single most concerning
axis decides the raw score. This generalises the spec's own "a floor that becomes a gate" rule
(written for risk-adjusted return alone) to every axis — a bad axis is never diluted by four good
ones. Tax position is deliberately NOT a sixth max-axis: it is not evidence the fund is bad, it is
a cost-of-acting modifier, so it applies as a damping multiplier on the combined result instead
(_tax_multiplier). This mapping of the spec's prose onto one combinator is itself a judgement
call — stated here so the FM can argue with it directly instead of reverse-engineering it from
code.

TWO INTERFACES DELIBERATELY LEFT UNBUILT (separate in-flight workstreams, 2026-08-06)
----------------------------------------------------------------------------------------
- lib.benchmark_returns.get_series(index_key, start_date, end_date) -> list[float] | None
    Periodic (monthly) % returns for one named index. Needed by lib/hybrid_benchmark.py for the
    blended-benchmark performance/down-capture/6m-capture figures this module consumes for
    hybrid funds (_hybrid_perf_gap below). Absence degrades to "axis unavailable" everywhere,
    never a fabricated gap number. THIS IS THE EXACT CONTRACT REQUESTED of that workstream.
- lib.tail_risk.es90(fund, window_years=3) -> {"es90": float|None, "regime_covered": bool,
    "basis": str} | None
    FM #16: a tail-risk axis is fully designed in the spec (common 3y window, ES90, a
    regime-coverage test, a ~2.5x safety factor explicitly "to be validated, not assumed") but is
    NOT wired into the combinator here — CONFIG["TAIL_SAFETY_FACTOR"] is None on purpose, and
    _axis_tail() always reports the axis as unavailable today. The moment lib/tail_risk.py exists
    with an es90() function AND a validated safety factor is set, this file needs no change.
Both are reached through a guarded import so this module runs today with the axis simply absent.
"""
import math
import datetime as _dt

# ============================================================================================
# CONFIG — every tunable the FM can change without reading code. Each has the sentence that
# justifies it. Where no principle supports a specific number, the sentence says so plainly and
# the value is marked a DOCUMENTED DEFAULT rather than dressed up as derived.
# Pass a modified copy (never mutate this dict) to any function's `cfg=` argument — that is how
# mf_sell_score_sensitivity.py runs its +-20% sweep without cross-contaminating runs.
# ============================================================================================
CONFIG = {
    # --- Risk-free / window (Principal ruling #15, 2026-08-06: "yes do it ideal 3y window,
    # risk-free 6.5% unless supplied per run") ---
    "RISK_FREE_RATE": 0.065,        # annualised; every function below accepts a per-call override
    "RAR_WINDOW_YEARS": 3,          # "ideal" window per the same ruling

    # --- Axis: performance vs blended benchmark (sigmoid) ---
    # Midpoint: the spec's own "why not linear" discussion uses "10% behind" as mild and "20%
    # behind" as decisive, without ruling an exact cut. We place score=50 at the middle of that
    # illustrative range. DOCUMENTED DEFAULT, not derived.
    "PERF_GAP_MIDPOINT_PP": 8.0,
    # Steepness: a logistic clears ~99% of its range across ~4.6/k of x either side of the
    # midpoint. Solving so [0pp, 16pp] (midpoint +-8pp) spans that range gives k=4.6/8=0.575; we
    # use a gentler 0.30 so a fund exactly AT benchmark (gap=0) still scores a visible ~9/100
    # rather than a rounding-error 0 — a defensible smoothing choice, not the raw solve.
    # DOCUMENTED DEFAULT.
    "PERF_GAP_STEEPNESS": 0.30,

    # --- Axis: risk-adjusted return (Sortino) — sigmoid with a floor that becomes a gate ---
    # Floor: Sortino <= 0 means the fund is destroying value per unit of downside risk relative
    # to the risk-free rate itself (#15) — sitting in T-bills would have scored better on the
    # fund's OWN downside-risk terms. A principled zero, not an arbitrary cut.
    "SORTINO_FLOOR": 0.0,
    # Comfortable reference: 0.5 Sortino is a common industry rule-of-thumb "acceptable" bar for
    # a diversified fund. This is a market CONVENTION, not a house-derived number.
    # [OPINION] DOCUMENTED DEFAULT — replace with a house view if the FM has one.
    "SORTINO_COMFORTABLE": 0.5,

    # --- Axis: IPS gap — piecewise flat-then-convex ---
    # Inside the client's own IPS band: exactly zero, by construction — the spec's own reason for
    # rejecting a linear term here ("a linear term would penalise a compliant fund").
    # Anchor: spec's own illustration, "1pp outside is minor; 10pp outside is a breach" — one
    # quadratic through (0,0) and (10,100) reproduces BOTH anchors in a single formula (1pp gives
    # 1/100 of the concern of 10pp, i.e. genuinely minor; 10pp saturates as "a breach").
    "IPS_GAP_SATURATE_PP": 10.0,

    # --- Axis: concentration — convex, reproducing house guidance verbatim ---
    # Anchors ARE the house guidance already used on the stock scorecard (5-10% acceptable,
    # >10% a concern, >20% extreme) — not invented. The smooth convex curve BETWEEN those anchors
    # is this module's own interpolation and is the part genuinely open to argument.
    "CONC_CONCERN_PP": 10.0,          # "above 10% a concern"
    "CONC_EXTREME_PP": 20.0,          # "above 20% extreme"
    "CONC_SCORE_AT_CONCERN": 15.0,    # still low at the boundary — consistent with "5-10% acceptable"
    "CONC_SCORE_AT_EXTREME": 70.0,    # decisive but not yet saturated exactly at the extreme boundary
    "CONC_TAIL_SOFTEN_PP": 10.0,      # e-fold distance for the >extreme saturating tail

    # --- Axis: persistent underperformance (FM #9 — "its own term") ---
    # Needs >=2 independent-ish horizons to call something "persistent" by definition (one
    # horizon is a point, not a pattern). Below that: a reported gap, never a fabricated value.
    "PERSISTENCE_MIN_HORIZONS": 2,

    # --- Tax damping (not a max-axis — see module docstring) ---
    # "LTCG mildly reduces… STCG reduces it strongly… never suppressed entirely" (spec, FM #19).
    # Values chosen so LTCG stays close to undamped and STCG is a clearly visible discount while
    # never reaching zero. DOCUMENTED DEFAULTS.
    "TAX_DAMPING_LTCG": 0.92,
    "TAX_DAMPING_STCG": 0.70,
    "TAX_DAMPING_UNKNOWN": 1.00,      # no purchase-date/holding-year data: we don't discount what we don't know
    # "never suppressed entirely" (FM #19), enforced numerically rather than left to chance, only
    # ever applied to a score that was already >=DISCRETION_LOW before damping (see score_fund:
    # damping softens an already-real candidate, it never manufactures one from a low score).
    # NOTE, stated honestly: at today's other two defaults (DISCRETION_LOW=45,
    # TAX_DAMPING_STCG=0.70) the floor cannot actually bind — the lowest a qualifying score can be
    # damped to is 45*0.70=31.5, already above 15. It is a backstop for if TAX_DAMPING_STCG is
    # ever tuned lower, not an active constraint today; test_mf_sell_score.py exercises it under
    # a perturbed config specifically because the default config cannot reach it.
    "TAX_DAMPING_FLOOR": 15.0,

    # --- Layer 3: discretion band edges ---
    # NOT fitted (no backtest exists). Placed so the performance axis's own sigmoid midpoint
    # (score=50, i.e. "a fund exactly at the illustrative half-way gap") sits INSIDE the
    # discretion band rather than on either side of it — the band is meant to catch exactly the
    # ambiguous middle a single-axis midpoint represents. DOCUMENTED DEFAULTS — the single most
    # consequential pair of numbers in this file; see mf_sell_score_sensitivity.py before
    # trusting them operationally.
    "DISCRETION_LOW": 45.0,
    "SELL_THRESHOLD": 70.0,

    # --- Tail axis (FM #16) — left unset ON PURPOSE. Spec: "to be validated, not assumed". Do
    # not set this from this file; it belongs to the workstream validating it. ---
    "TAIL_SAFETY_FACTOR": None,
}

_AXES = ("performance", "risk_adjusted", "ips_gap", "concentration", "persistence", "tail")


# ------------------------------------------------------------------------------------------------
# Curve primitives
# ------------------------------------------------------------------------------------------------
def _sigmoid(x, midpoint, steepness):
    """Logistic, 0..100, RISING as x rises. midpoint is the x at which the curve reads 50."""
    z = -steepness * (x - midpoint)
    try:
        return 100.0 / (1.0 + math.exp(z))
    except OverflowError:
        return 0.0 if z > 0 else 100.0


def _sigmoid_desc(x, midpoint, steepness):
    """Logistic, 0..100, FALLING as x rises — for axes where a bigger raw number means LESS
    concern (Sortino), so callers never have to remember a sign flip."""
    return _sigmoid(-x, -midpoint, steepness)


def _parse_date(s):
    if not s:
        return None
    if isinstance(s, _dt.date):
        return s
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return _dt.datetime.strptime(str(s), fmt).date()
        except ValueError:
            continue
    return None


# ------------------------------------------------------------------------------------------------
# Axis 1 — performance vs blended benchmark
# ------------------------------------------------------------------------------------------------
def _axis_performance(gap_pp, cfg):
    """gap_pp = benchmark_return - fund_return over the scoring window (positive = fund trails).
    None (no benchmark figure at all) -> axis unavailable, never zero (zero would silently claim
    'measured and fine', which is a different, stronger statement than 'not measured yet')."""
    if gap_pp is None:
        return None, "no benchmark-return figure available for this fund yet"
    return round(_sigmoid(gap_pp, cfg["PERF_GAP_MIDPOINT_PP"], cfg["PERF_GAP_STEEPNESS"]), 1), None


def _hybrid_perf_gap(f, ctx, cfg):
    """For a hybrid fund with no pre-computed bench_gap_pp, build one from hybrid_benchmark's
    PER-FUND blended series over the same RAR_WINDOW_YEARS this module uses for risk-adjusted
    return (#15's 'ideal 3y window'), so both axes sit on the same period. Guarded: returns None
    (never a guess) the moment any input is missing, including the pending benchmark_returns
    interface hybrid_benchmark.py itself depends on — see that module's docstring."""
    try:
        from lib import hybrid_benchmark as _hb
    except ImportError:
        return None
    client = (ctx or {}).get("client", {})
    as_of = _parse_date(client.get("as_of"))
    fund_r = f.get("cagr3y")
    if as_of is None or fund_r is None:
        return None
    try:
        # RAR_WINDOW_YEARS must be a whole number of calendar years for date.replace(); guarded
        # (not just documented) so a sensitivity sweep that perturbs it to a fraction degrades to
        # "axis unavailable" instead of crashing the run.
        years = int(round(cfg["RAR_WINDOW_YEARS"]))
        if years < 1:
            return None
        start = as_of.replace(year=as_of.year - years)
        bench_total_r, _, _gap = _hb.blended_return(f, start, as_of)
        if bench_total_r is None:
            return None
        bench_cagr = (1 + bench_total_r / 100.0) ** (1.0 / years) - 1.0
        return round(bench_cagr * 100.0 - fund_r, 2)
    except Exception:
        return None


# ------------------------------------------------------------------------------------------------
# Axis 2 — risk-adjusted return (Sortino), floor-becomes-gate
# ------------------------------------------------------------------------------------------------
def _axis_risk_adjusted(sortino, cfg):
    """Returns (score, floor_breach, gap_reason). Below SORTINO_FLOOR this is no longer a soft
    score — spec: "stops being a score and becomes a disqualification" — so we return the
    maximum axis score AND floor_breach=True, which score_fund() treats as gate-like (forces the
    Sell band regardless of tax damping), matching Layer 1's own gate pattern instead of
    inventing a second mechanism."""
    if sortino is None:
        return None, False, "no Sortino on file for this fund yet (thin NAV history)"
    floor, comfy = cfg["SORTINO_FLOOR"], cfg["SORTINO_COMFORTABLE"]
    if sortino <= floor:
        return 100.0, True, None
    midpoint = (floor + comfy) / 2.0
    half_span = max((comfy - floor) / 2.0, 1e-6)
    # a logistic clears ~99%/~1% of its range at +-4.6/k from the midpoint; floor and comfy sit
    # at +-half_span from the midpoint, so k=4.6/half_span puts floor at ~99 (continuous with the
    # hard-gated branch just above) and comfy at ~1 (reads as "near zero concern").
    steepness = 4.6 / half_span
    return round(_sigmoid_desc(sortino, midpoint, steepness), 1), False, None


# ------------------------------------------------------------------------------------------------
# Axis 3 — IPS gap, attributed only to the fund that is actually the lever
# ------------------------------------------------------------------------------------------------
def _axis_ips_gap(fund, ctx, cfg):
    """Book-level IPS breach, felt only by funds sitting on the breaching side (a debt fund isn't
    'the problem' when the book is over its equity band, even though the whole book breaches).
    #18/#23 pattern applied to IPS too: no IPS on file -> assume no restriction -> axis
    contributes nothing, never a fabricated breach."""
    ips = (ctx or {}).get("ips") or {}
    if not ips.get("on_file"):
        return 0.0, "no IPS on file: assumed no restriction (ruling #18/#23 pattern)"
    band = (ips.get("alloc_bands") or {}).get("Equity")
    if not band:
        return 0.0, "IPS on file has no Equity band"
    lo, _, hi = band
    try:
        from lib import lookthrough
        equity_pct, _, _ = lookthrough.equity_lookthrough_pct(ctx)
    except Exception as ex:
        return None, f"could not compute look-through equity%: {ex!r}"
    if equity_pct > hi:
        gap_pp, breach_side = equity_pct - hi, "over"
    elif equity_pct < lo:
        gap_pp, breach_side = lo - equity_pct, "under"
    else:
        return 0.0, None  # inside band: zero, by construction

    g = fund.get("equity_gross_pct")
    is_equity_oriented = (g is not None and g >= 50.0)
    if breach_side == "over" and not is_equity_oriented:
        return 0.0, "book is over its equity band, but this fund is not the equity-oriented lever"
    if breach_side == "under" and is_equity_oriented:
        return 0.0, "book is under its equity band; trimming an equity-oriented fund would not help"

    anchor = cfg["IPS_GAP_SATURATE_PP"]
    score = 100.0 * min(1.0, gap_pp / anchor) ** 2
    return round(score, 1), None


# ------------------------------------------------------------------------------------------------
# Axis 4 — concentration (scheme OR its AMC, whichever is larger today)
# ------------------------------------------------------------------------------------------------
def _amc_weight_for(f, ctx):
    """AMC-level weight for this fund's canonical AMC — a second real concentration risk (issuer
    concentration across several schemes of one AMC) that the firm already tracks
    (lookthrough.amc_concentration). Reusing the SAME curve on max(scheme%, AMC%) captures it
    without inventing a second threshold."""
    try:
        from lib import lookthrough, mf_mapping
        amc_map = lookthrough.amc_concentration(ctx)
        canon = mf_mapping.canonical_amc(f.get("amc") or "Unknown")
        return amc_map.get(canon, 0.0)
    except Exception:
        return 0.0


def _axis_concentration(pct, cfg):
    if pct is None:
        return None, "no weight_pct on file"
    concern, extreme = cfg["CONC_CONCERN_PP"], cfg["CONC_EXTREME_PP"]
    s_concern, s_extreme = cfg["CONC_SCORE_AT_CONCERN"], cfg["CONC_SCORE_AT_EXTREME"]
    if pct <= concern:
        # convex ramp (0,0)->(concern,s_concern): squared, not linear, so a HALF-of-concern
        # position scores a QUARTER of s_concern — "rising faster than linear", as specified.
        return round(s_concern * (pct / concern) ** 2, 1), None
    if pct <= extreme:
        frac = (pct - concern) / (extreme - concern)
        return round(s_concern + (s_extreme - s_concern) * frac ** 1.5, 1), None
    tail = cfg["CONC_TAIL_SOFTEN_PP"]
    return round(100.0 - (100.0 - s_extreme) * math.exp(-(pct - extreme) / tail), 1), None


# ------------------------------------------------------------------------------------------------
# Axis 5 — persistent underperformance (FM #9)
# ------------------------------------------------------------------------------------------------
def _axis_persistence(fund, cfg):
    """fund['horizon_vs_bench'] = [(label, fund_return_pp, bench_return_pp), ...] — NOT part of
    today's ctx schema; this is what a future ctx-builder needs to populate (from ACE's own
    1Y/3Y/5Y trailing-return columns vs the matching-horizon benchmark figure) for this axis to
    activate on real data. [INFERENCE label required on any real use]: multiple trailing windows
    anchored at ONE as-of date are not genuinely independent non-overlapping periods — weaker
    evidence than true rolling-quarter history, but real and non-fabricated, which is why this is
    gated on >=PERSISTENCE_MIN_HORIZONS rather than treated as a full rolling-window study."""
    pairs = fund.get("horizon_vs_bench")
    if not pairs:
        return None, "no multi-horizon vs-benchmark figures on file to assess persistence"
    usable = [(f_r, b_r) for _, f_r, b_r in pairs if f_r is not None and b_r is not None]
    if len(usable) < cfg["PERSISTENCE_MIN_HORIZONS"]:
        return None, (f"only {len(usable)} horizon(s) on file; need "
                       f"{cfg['PERSISTENCE_MIN_HORIZONS']}+ to call a pattern persistent")
    behind = sum(1 for f_r, b_r in usable if f_r < b_r)
    return round(100.0 * behind / len(usable), 1), None


# ------------------------------------------------------------------------------------------------
# Axis 6 — tail risk (FM #16) — deliberately inert; see module docstring
# ------------------------------------------------------------------------------------------------
def _axis_tail(f, cfg):
    try:
        from lib import tail_risk as _tail
    except ImportError:
        return None, "tail-risk module not yet available (separate workstream, 2026-08-06)"
    if not hasattr(_tail, "es90"):
        return None, "tail-risk module present but es90() not yet implemented"
    try:
        result = _tail.es90(f, window_years=cfg.get("RAR_WINDOW_YEARS", 3))
    except Exception as ex:
        return None, f"tail-risk call failed: {ex!r}"
    if not result or result.get("es90") is None:
        return None, "tail-risk module returned no ES90 for this fund"
    if cfg.get("TAIL_SAFETY_FACTOR") is None:
        return None, "TAIL_SAFETY_FACTOR unset (spec: to be validated, not assumed) — ES90 on file but not scored"
    return None, "tail axis wiring intentionally inert pending FM #16 validation"  # pragma: no cover


# ------------------------------------------------------------------------------------------------
# Tax damping (not a max-axis)
# ------------------------------------------------------------------------------------------------
def _tax_multiplier(f, cfg):
    is_stcg = f.get("is_stcg")
    if is_stcg is None:
        return cfg["TAX_DAMPING_UNKNOWN"], "unknown holding period: no discount applied"
    if is_stcg:
        return cfg["TAX_DAMPING_STCG"], "STCG: strong discount, never to zero (FM #19)"
    return cfg["TAX_DAMPING_LTCG"], "LTCG: mild discount"


# ------------------------------------------------------------------------------------------------
# Layer 2 aggregator
# ------------------------------------------------------------------------------------------------
def score_fund(f, ctx, cfg=None, risk_free_rate=None):
    """Layer 2. Only call this on a holding that already cleared Layer 1 (mf_sell_gates) — use
    score_all() below to get that ordering for free. `risk_free_rate` overrides
    cfg['RISK_FREE_RATE'] for this call only (#15: "unless supplied per run"); accepted here for
    interface symmetry with hybrid_benchmark.py even though today's Sortino/CAGR inputs arrive
    pre-computed upstream.

    Returns a dict: axes (name->score|None), gaps (name->reason, only for None axes),
    driver_axis, raw_score, floor_breach, n_axes_elevated (informational only — see module
    docstring, never fed back into the score), tax_multiplier, tax_basis, final_score, band
    ('sell'|'discretion'|'hold'|'no_score'), band_reason.
    """
    cfg = cfg or CONFIG
    conc_pct = f.get("weight_pct")
    if conc_pct is not None:
        conc_pct = max(conc_pct, _amc_weight_for(f, ctx))

    gap_pp = f.get("bench_gap_pp")
    if gap_pp is None and f.get("category") in ("hybrid", "conservative_hybrid"):
        gap_pp = _hybrid_perf_gap(f, ctx, cfg)
    perf_score, perf_gap = _axis_performance(gap_pp, cfg)
    risk_score, floor_breach, risk_gap = _axis_risk_adjusted(f.get("sortino"), cfg)
    ips_score, ips_gap = _axis_ips_gap(f, ctx, cfg)
    conc_score, conc_gap = _axis_concentration(conc_pct, cfg)
    pers_score, pers_gap = _axis_persistence(f, cfg)
    tail_score, tail_gap = _axis_tail(f, cfg)

    axes = {"performance": perf_score, "risk_adjusted": risk_score, "ips_gap": ips_score,
            "concentration": conc_score, "persistence": pers_score, "tail": tail_score}
    gaps = {k: v for k, v in {"performance": perf_gap, "risk_adjusted": risk_gap,
                               "ips_gap": ips_gap, "concentration": conc_gap,
                               "persistence": pers_gap, "tail": tail_gap}.items() if v}

    available = {k: v for k, v in axes.items() if v is not None}
    if not available:
        return {"axes": axes, "gaps": gaps, "driver_axis": None, "raw_score": None,
                "floor_breach": floor_breach, "n_axes_elevated": 0,
                "tax_multiplier": None, "tax_basis": None, "final_score": None,
                "band": "no_score",
                "band_reason": "every axis is a coverage gap; no score is emitted "
                               "(never a fabricated Hold)"}

    driver_axis = max(available, key=available.get)
    raw_score = available[driver_axis]
    n_elevated = sum(1 for v in available.values() if v >= cfg["DISCRETION_LOW"])

    tax_mult, tax_basis = _tax_multiplier(f, cfg)
    final_score = raw_score * tax_mult
    if raw_score >= cfg["DISCRETION_LOW"] and tax_mult < 1.0:
        # "never suppressed entirely" (FM #19) — a floor that only rescues an ALREADY-elevated
        # score from being damped away; it never lifts a genuinely low score using tax status.
        final_score = max(final_score, cfg["TAX_DAMPING_FLOOR"])
    if floor_breach:
        # a risk-floor breach is a disqualification, not a soft score (see _axis_risk_adjusted) —
        # tax damping softens URGENCY, it does not erase a disqualification.
        final_score = max(final_score, cfg["SELL_THRESHOLD"])

    if final_score >= cfg["SELL_THRESHOLD"]:
        band = "sell"
    elif final_score >= cfg["DISCRETION_LOW"]:
        band = "discretion"
    else:
        band = "hold"

    reason = f"driven by {driver_axis} ({raw_score:.1f}/100)"
    if floor_breach:
        reason += " — risk-floor breach forces the Sell band regardless of tax damping"
    return {"axes": axes, "gaps": gaps, "driver_axis": driver_axis, "raw_score": round(raw_score, 1),
            "floor_breach": floor_breach, "n_axes_elevated": n_elevated,
            "tax_multiplier": tax_mult, "tax_basis": tax_basis,
            "final_score": round(final_score, 1), "band": band, "band_reason": reason}


# ------------------------------------------------------------------------------------------------
# Layer 3 — discretion, enforced one-directionally IN CODE, not just in prose
# ------------------------------------------------------------------------------------------------
_BAND_RANK = {"hold": 0, "discretion": 1, "sell": 2}


def apply_discretion(band, override=None, reason=None):
    """`override` may only move the outcome to a LESS aggressive band than `band` — never more.
    That asymmetry is the whole safety property (task brief); it is enforced here by raising,
    not merely documented. Every override must carry a reason (spec: "every discretionary call
    records its reason"). Returns (effective_band, note)."""
    if override is None:
        return band, None
    if override not in _BAND_RANK:
        raise ValueError(f"unknown override band {override!r}; expected one of {sorted(_BAND_RANK)}")
    if not reason:
        raise ValueError("a discretion override must record a reason (spec, Layer 3)")
    if _BAND_RANK[override] > _BAND_RANK.get(band, 0):
        raise ValueError(
            f"discretion is one-directional: cannot raise {band!r} to {override!r}. "
            "Discretion may veto or soften a sell, never manufacture one (spec, Layer 3).")
    return override, reason


# ------------------------------------------------------------------------------------------------
# Layer 4 — escalation payload (standing rule: situation / our view / counter-view / what settles it)
# ------------------------------------------------------------------------------------------------
def build_escalation(fund, score_result):
    """Writes the question down in the standing-rule shape
    (.claude/skills/ionic-wealth-complete/SKILL.md). Does not decide anything itself."""
    driver = score_result.get("driver_axis")
    driver_val = (score_result.get("axes") or {}).get(driver) or 0.0
    situation = (
        f"{fund.get('name')} ({fund.get('weight_pct', 0):.1f}% of the fund sleeve) scores "
        f"{score_result['final_score']:.0f}/100 on the sell-urgency scale (band: "
        f"{score_result['band']}, driven by {driver}), but its current action on file is "
        f"{fund.get('action') or fund.get('verdict')!r}.")
    our_view = (
        f"The {driver} axis alone reads {driver_val:.0f}/100, which on its own would argue for "
        "review regardless of the other axes (the combinator is a max, by design — see "
        "mf_sell_score.py's module docstring).")
    counter_view = (
        "The existing action reflects the fund-quality framework's own evidence base (QFRA), "
        "built independently and on a longer track record than this score; the sell-urgency "
        "score is new and explicitly unvalidated (no backtest is possible here), and a single "
        "elevated axis is exactly the case Layer 3 says should go to an analyst/FM before it "
        "becomes an action, not a case that should overrule QFRA on its own.")
    what_would_settle_it = (
        "An analyst read against this fund's structural_reason/flags on file, confirming whether "
        "the elevated axis reflects a real deterioration or a stale/thin-data artifact — Sortino "
        "and multi-horizon figures both depend on NAV history that is thin for several funds "
        "firm-wide.")
    return {"situation": situation, "our_view": our_view, "counter_view": counter_view,
            "what_would_settle_it": what_would_settle_it}


# ------------------------------------------------------------------------------------------------
# Convenience: run Layer 2 over every un-gated fund, in place
# ------------------------------------------------------------------------------------------------
def score_all(ctx, cfg=None, risk_free_rate=None):
    """Stamps f['sell_score'] = score_fund(...) onto every fund in ctx['funds'] IN PLACE (mirrors
    mf_sell_gates.apply_to's own convention), skipping any fund Layer 1 already gated
    (f['gate_note'] is not None) — those get f['sell_score']=None, never a score, per the spec.
    Also collects the escalation case where the score disagrees with an existing Hold (band is
    'sell' or 'discretion' but the fund's action on file is still HOLD) — Layer 3's one-
    directional rule means that disagreement is surfaced, never auto-resolved either way.

    Returns {n_scored, n_gated, n_sell, n_discretion, n_hold, n_no_score, escalations}."""
    cfg = cfg or CONFIG
    n_gated = n_sell = n_disc = n_hold = n_noscore = 0
    escalations = []
    funds = ctx.get("funds", [])
    for f in funds:
        if f.get("gate_note"):
            f["sell_score"] = None
            n_gated += 1
            continue
        result = score_fund(f, ctx, cfg, risk_free_rate)
        f["sell_score"] = result
        band = result["band"]
        if band == "sell":
            n_sell += 1
        elif band == "discretion":
            n_disc += 1
        elif band == "hold":
            n_hold += 1
        else:
            n_noscore += 1
        existing = str(f.get("action") or f.get("verdict") or "HOLD").upper()
        if band in ("sell", "discretion") and existing in ("HOLD", ""):
            escalations.append(build_escalation(f, result))
    return {"n_scored": len(funds) - n_gated, "n_gated": n_gated, "n_sell": n_sell,
            "n_discretion": n_disc, "n_hold": n_hold, "n_no_score": n_noscore,
            "escalations": escalations}
