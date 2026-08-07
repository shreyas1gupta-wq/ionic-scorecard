# -*- coding: utf-8 -*-
"""mf_sell_gates.py — Layer-1 hard gates + priority/churn arithmetic from the agreed MF sell
method (09_PRODUCT/MF_SELL_METHOD_SPEC_2026-08-05.md). These are business rules the FM has
already ruled on, not the scoring model: nothing here computes a score or a verdict — only
whether an ALREADY-DECIDED action is allowed to stand, and how urgently it should be worked.

Layer-2's continuous score (the saturating curves) and the discretion band now live in
lib/mf_sell_score.py (built 2026-08-06, FM #17 — "create it and show me best way logically we
cannot backtest"). refine_priority_with_score() below is the one opt-in hook between the two
files: it can only SOFTEN a priority this module already assigned, never manufacture one, so a
caller with no score yet keeps calling assign_priority() alone with zero behaviour change.

Discretion is one-directional throughout: a gate may veto or force an action back to Hold, it
never invents a new action.
"""
import os
import datetime as _dt

APR_1_2023 = _dt.date(2023, 4, 1)


def _parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return _dt.datetime.strptime(str(s), fmt).date()
        except ValueError:
            continue
    return None


def derive_purchase_flags(f, as_of):
    """Graceful degradation (Principal 2026-08-05): purchase dates are case-by-case from the
    holding statement — if present, use them; if absent, proceed without.

    If `purchase_date` parses, it OVERRIDES any hand-set `holding_years` (a real date beats an
    estimate) and yields a real is_stcg / bought_pre_apr_2023. If absent, keeps whatever
    holding_years the caller already carries (may itself be an estimate, unchanged) and returns
    is_stcg from that if possible, but always None for bought_pre_apr_2023 — the debt gate must
    never guess grandfathering from a mere holding-years estimate, only from a real date."""
    pd = _parse_date(f.get("purchase_date"))
    if pd is None:
        hy = f.get("holding_years")
        return {"holding_years": hy, "is_stcg": (hy < 1) if hy is not None else None,
                "bought_pre_apr_2023": None}
    hy = round((as_of - pd).days / 365.25, 2)
    return {"holding_years": hy, "is_stcg": hy < 1, "bought_pre_apr_2023": pd < APR_1_2023}


def is_debt_category(cat):
    cat = str(cat or "").lower()
    return any(k in cat for k in ("debt", "gilt", "duration", "bond", "overnight"))


def apply_debt_grandfather_gate(f, flags):
    """Layer-1 hard gate (FM #21 + Finance Act 2023 grandfathering): a DEBT fund bought before
    1-Apr-2023 is never sold for optimisation or rebalancing. A credit or governance event still
    overrides — signalled by the CALLER having already set `credit_or_governance_event=True` (plus
    a `structural_reason` documenting it) on the fund before this runs; this function only reads
    that flag, never sets it.

    Returns (action, verdict, gate_note). action/verdict pass through unchanged unless the gate
    fires, in which case both are forced to Hold and gate_note explains why — never a silent
    override, per the firm's escalate-rather-than-guess standing rule."""
    action, verdict = f.get("action"), f.get("verdict")
    if not is_debt_category(f.get("category")) or not flags.get("bought_pre_apr_2023"):
        return action, verdict, None
    if action is None or str(action).upper() == "HOLD":
        return action, verdict, None
    if f.get("credit_or_governance_event"):
        return action, verdict, None  # override stands; structural_reason must carry the reason
    return "HOLD", "Hold", (
        "Grandfathered: bought before 1-Apr-2023, so the pre-Finance-Act-2023 debt-fund tax "
        "treatment applies. Not sold for optimisation or rebalancing; a credit or governance "
        "event would still override this.")


def load_restrictions(path=None):
    """Layer-1 gate row 4, first half (FM #18/#23, Principal 2026-08-06): "if he supplies an
    Excel we read it; if not, assume no restriction... do not block on either." Expected columns:
    'ISIN' or 'Scheme Name', 'restriction' (free text), optionally 'note'. No path, or a path
    that doesn't exist yet -> ASSUME NO RESTRICTION (empty map) -- never blocks a build waiting
    for a file that may not arrive this run. Returns {key: {"restriction":..., "note":...}},
    keyed by both ISIN and Scheme Name where available so apply_manual_override_gate() can match
    on whichever key a given fund dict happens to carry."""
    if not path or not os.path.exists(path):
        return {}
    import pandas as pd
    df = pd.read_excel(path)
    key_cols = [c for c in ("ISIN", "Scheme Name") if c in df.columns]
    if not key_cols:
        raise ValueError(f"restrictions file {path!r} has neither an 'ISIN' nor 'Scheme Name' column")
    out = {}
    for _, row in df.iterrows():
        entry = {"restriction": str(row.get("restriction", "")).strip(),
                 "note": str(row.get("note", "")).strip()}
        for c in key_cols:
            key = str(row[c]).strip()
            if key and key.lower() != "nan":
                out[key] = entry
    return out


def check_avoid_list(fund, ask_analyst_fn=None):
    """Layer-1 gate row 4, second half — a DIFFERENT default path than load_restrictions(), per
    the Principal's own words: "for the avoid-list, ask the analyst at runtime, otherwise treat
    as nil." `ask_analyst_fn` is an optional injected callback, (fund_dict) -> True/False/None,
    standing in for "ask the analyst at runtime" — this module never embeds a hardcoded avoid-
    list. No callback (the common case: an automated/background build), a raised exception, or a
    None answer all resolve to NOT on the avoid-list. Never blocks (Principal: "do not block on
    either"). Returns (is_hit: bool, reason: str)."""
    if ask_analyst_fn is None:
        return False, "no analyst callback supplied at build time; treated as nil (#18/#23)"
    try:
        hit = ask_analyst_fn(fund)
    except Exception as ex:
        return False, f"analyst callback raised {ex!r}; treated as nil (#18/#23), never blocking"
    if hit is None:
        return False, "analyst callback returned no answer; treated as nil (#18/#23)"
    return bool(hit), ("analyst-flagged avoid-list hit" if hit else "analyst cleared: not on avoid-list")


def apply_manual_override_gate(f, restrictions, avoid_hit, avoid_reason):
    """Layer-1 gate row 4 ('Manual override / avoid-list hit -> forced action, override reason
    recorded'). `restrictions` is load_restrictions()'s map. A documented restriction forces
    HOLD (we were told to leave this alone); an avoid-list hit forces the opposite, EXIT (we were
    told to get out) -- both recorded, never silent, matching every other gate in this file.
    Runs independently of apply_debt_grandfather_gate: a Principal-supplied restriction or
    avoid-list hit is the same class of override that gate's own docstring already carves out
    for a credit/governance event, so either can still move a grandfathered Hold."""
    isin_key = f.get("isin") or f.get("ISIN")
    scheme_key = f.get("name")
    hit = restrictions.get(isin_key) or restrictions.get(scheme_key)
    if hit:
        note = f"Manual restriction on file: {hit['restriction']}"
        if hit.get("note"):
            note += f" ({hit['note']})"
        return "HOLD", "Hold", note
    if avoid_hit:
        return "EXIT", "Exit", f"Avoid-list: {avoid_reason}"
    return f.get("action"), f.get("verdict"), None


def assign_priority(is_stcg, is_gate_forced):
    """Priority for the churn split (FM #19, #25).
    - A gate-forced action (a documented override on an otherwise-grandfathered holding, or a
      future avoid-list hit) is always HIGH — it is happening regardless of score.
    - STCG always demotes to LOW, and is never suppressed entirely (FM #19's own wording).
    - Everything else defaults to HIGH: the honest placeholder pending the FM's Layer-2 score and
      cut-offs, which this build does not invent (MF_SELL_METHOD_SPEC.md, "Open, and deliberately
      not invented")."""
    if is_gate_forced:
        return "High"
    if is_stcg:
        return "Low"
    return "High"


def refine_priority_with_score(priority, band):
    """Opt-in refinement once lib/mf_sell_score.py has scored a fund (band is its 'sell'/
    'discretion'/'hold'/'no_score'/None). One-directional exactly like that module's own Layer 3:
    can only SOFTEN an existing High priority down to Low when the holistic score turns out to be
    low-urgency (band=='hold') -- it never raises a Low (STCG-demoted or otherwise) back to High,
    and never invents a priority for a fund with none (`priority is None`) or a fund the score
    module didn't reach (`band` is None/'no_score'). Callers with no score simply don't call
    this -- assign_priority()'s own output is unchanged, so nothing already wired through
    apply_to() breaks by this function merely existing."""
    if priority is None or band in (None, "no_score"):
        return priority
    if priority == "High" and band == "hold":
        return "Low"
    return priority


def churn_pct(equity, funds):
    """Total churn = % of portfolio value recommended for sale (FM #3 / #25). Every equity Sell
    or Trim, plus every non-Hold fund action — Switch/Redeem-to-Direct/Exit/Trim all redeem
    units, which is a sale event for tax purposes even when the destination is a reinvestment."""
    eq_churn = sum(e.get("weight_pct") or 0.0 for e in equity if e.get("rec") in ("Sell", "Trim"))
    fund_churn = sum(f.get("weight_pct") or 0.0 for f in funds
                     if str(f.get("action") or "").upper() not in ("HOLD", ""))
    return round(eq_churn + fund_churn, 2)


def apply_to(equity, funds, as_of_str, restrictions=None, ask_analyst_fn=None):
    """Run the full Layer-1 + priority pass over `equity` and `funds` IN PLACE (both lists of
    dicts, mutated by reference so the caller's own list objects end up gated/prioritised too),
    and return the churn summary {"pct": ..., "split_required": bool}. Idempotent: safe to call
    more than once on the same lists (re-derives from source fields each time, never accumulates).

    `restrictions` (load_restrictions()'s map) and `ask_analyst_fn` (check_avoid_list()'s
    callback) are both optional and default to "no restriction" / "nil" per FM #18/#23 -- existing
    callers that pass neither (e.g. data/azby_family.py's `apply_to(eq, funds, AS_OF)`) get
    IDENTICAL behaviour to before this gate existed.

    Call this BEFORE any derived dict (tax/cost/deployment) is built from `funds`, so a
    gate-forced Hold is excluded from proceeds/tax exactly like any other Hold, never sold in one
    place and held in another."""
    restrictions = restrictions or {}
    as_of = _parse_date(as_of_str) or _dt.date.today()
    for f in funds:
        flags = derive_purchase_flags(f, as_of)
        f["holding_years"] = flags["holding_years"]
        f["is_stcg"] = flags["is_stcg"]
        f["bought_pre_apr_2023"] = flags["bought_pre_apr_2023"]
        action, verdict, gate_note = apply_debt_grandfather_gate(f, flags)
        gate_forced = gate_note is None and bool(f.get("credit_or_governance_event")) and \
            is_debt_category(f.get("category")) and flags.get("bought_pre_apr_2023")
        # Manual override / avoid-list gate (FM #18/#23) runs after the debt-grandfather gate so
        # a documented restriction or avoid-list hit can still move a grandfathered Hold, the
        # same override class that gate's own docstring already carves out for a credit/
        # governance event.
        f["action"], f["verdict"] = action, verdict  # stage for apply_manual_override_gate's read
        avoid_hit, avoid_reason = check_avoid_list(f, ask_analyst_fn)
        mo_action, mo_verdict, mo_note = apply_manual_override_gate(f, restrictions, avoid_hit, avoid_reason)
        if mo_note:
            action, verdict, gate_note = mo_action, mo_verdict, mo_note
            gate_forced = True  # an explicit manual override is always a gate-forced action (HIGH priority)
        f["action"], f["verdict"], f["gate_note"] = action, verdict, gate_note
        f["sell_priority"] = (None if str(action).upper() == "HOLD" else
                              assign_priority(flags["is_stcg"], gate_forced))
    for e in equity:
        if e.get("rec") in ("Sell", "Trim"):
            hy = e.get("holding_years")
            is_stcg = (hy < 1) if hy is not None else None
            e["sell_priority"] = assign_priority(is_stcg, False)
        else:
            e["sell_priority"] = None
    pct = churn_pct(equity, funds)
    return {"pct": pct, "split_required": pct > 20.0}


def apply(ctx):
    """Same as apply_to(), but takes/returns a full ctx dict (equity/funds/client.as_of already
    inside it) and stamps ctx["fund_churn"]. Convenience wrapper for callers that already have a
    complete ctx assembled (e.g. a real client's build script)."""
    ctx["fund_churn"] = apply_to(ctx.get("equity", []), ctx.get("funds", []),
                                 ctx.get("client", {}).get("as_of"))
    return ctx
