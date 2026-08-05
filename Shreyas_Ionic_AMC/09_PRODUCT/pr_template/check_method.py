# -*- coding: utf-8 -*-
"""check_method.py — QA gate 5: does this client's call sheet obey our own rules?

Gates 1-3 check that the deck LOOKS right and gate 4 checks the data is CURRENT. Nothing checked
that the recommendations obey the method. On 2026-08-05 the Principal asked us to re-look at
Hindustan Copper, and an audit of the shipped Talaulikar book found FIVE quality sells on names our
own model scores as Hold - including L&T at 4.27% of the book. The rule existed in the methodology
document and in the analyst's head; nothing enforced it.

Rules enforced here, with the comment number they come from:

  SELL BAR (Stock Scorecard 750, restated by the Principal 2026-08-05)
    A QUALITY sell needs ionic_score < 40. A score of 40-50 supports a Trim only when the position
    is concentrated (>2.5%). Above 50 is a Hold. A quality call above the bar is permitted ONLY with
    an explicit exceptional override carrying a reason - the asymmetric-override bar already in the
    method ("Sell on a >40 scorer needs a 90% exceptional case").
    Liquidity, directed and structural sells are EXEMPT: they are not quality claims. That is what
    `sell_reason_type` is for, and it is why TMCV at 70.2 and Bajaj Finance at 65.7 are correct.

  CHURN SPLIT (FM #3 / #25, Principal: implement)
    Churn is % of portfolio value recommended for sale. At or below 20% the sell list is one list.
    Above 20% it must be segregated into high and low priority.

  STCG PRIORITY (FM #19)
    A holding sold while in STCG is a LOW priority sell. Only checked where holding_years is
    present - the Principal ruled purchase dates are case-by-case (2026-08-05), so absence is not a
    finding, it is a documented limitation.

  DEBT GRANDFATHERING (FM #21)
    A debt fund bought before 1-Apr-2023 must not be sold for optimisation or rebalancing. A credit
    or governance event overrides, so a structural reason clears the check.

Usage:  python check_method.py <data_module.py>       e.g. data/talaulikar_family.py
Exit 1 on any finding, so it can gate a build.
"""
import importlib.util
import os
import sys

SELL_FLOOR = 40.0          # below this, a quality sell needs no override
TRIM_CEIL = 50.0           # 40-50 supports a Trim, and only when concentrated
CONC_MIN = 2.5             # "concentrated" for the Trim gate, % of portfolio
CHURN_SPLIT = 20.0         # FM #25: above this, segregate priority
NON_QUALITY = {"liquidity", "directed", "structural", "mandate", "consolidation"}


def _load(path):
    spec = importlib.util.spec_from_file_location("clientdata", path)
    m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    spec.loader.exec_module(m)
    return m.build_ctx() if hasattr(m, "build_ctx") else m.ctx()


def check(ctx, verbose=True):
    F = []
    eq = ctx.get("equity") or []
    funds = ctx.get("funds") or []

    # ---- 1. the sell bar -------------------------------------------------------------
    for e in eq:
        rec = str(e.get("rec") or "").strip().lower()
        if rec not in ("sell", "trim"):
            continue
        score = e.get("ionic_score")
        if not score:
            continue                                  # unscored is handled by the No-View rule
        rt = str(e.get("sell_reason_type") or "").strip().lower()
        if rt in NON_QUALITY:
            continue                                  # not a quality claim, bar does not apply
        override = e.get("exceptional_override")
        sym, wt = e.get("symbol") or "?", e.get("weight_pct") or 0.0

        if rec == "sell" and score >= SELL_FLOOR and not override:
            F.append(dict(kind="sell-bar", sym=sym, score=score, wt=wt,
                          msg=f"quality SELL at score {score:.1f} (bar is <{SELL_FLOOR:.0f}) "
                              f"with no exceptional override"))
        elif rec == "trim" and not override:
            if score > TRIM_CEIL:
                F.append(dict(kind="trim-bar", sym=sym, score=score, wt=wt,
                              msg=f"TRIM at score {score:.1f}, above the {TRIM_CEIL:.0f} Hold line"))
            elif wt <= CONC_MIN:
                F.append(dict(kind="trim-conc", sym=sym, score=score, wt=wt,
                              msg=f"TRIM at {wt:.2f}% weight is not a concentration trim "
                                  f"(needs >{CONC_MIN}%)"))

    # ---- 2. churn split --------------------------------------------------------------
    sold = [x for x in (eq + funds)
            if str(x.get("rec") or x.get("action") or "").strip().lower() in ("sell", "trim")]
    churn = sum(x.get("weight_pct") or 0.0 for x in sold)
    if churn > CHURN_SPLIT:
        unprioritised = [x for x in sold if not str(x.get("sell_priority") or "").strip()]
        if unprioritised:
            F.append(dict(kind="churn-split", sym=f"{len(unprioritised)} lines", score=0, wt=churn,
                          msg=f"churn is {churn:.1f}% of the book (>{CHURN_SPLIT:.0f}%), so sells "
                              f"must be split high/low priority; {len(unprioritised)} carry no "
                              f"priority"))

    # ---- 3. STCG priority, only where a holding period is known ----------------------
    for x in eq + funds:
        if str(x.get("rec") or x.get("action") or "").strip().lower() not in ("sell", "trim"):
            continue
        hy = x.get("holding_years")
        if hy is None:
            continue                                  # case-by-case per the Principal; not a finding
        if hy < 1 and str(x.get("sell_priority") or "").lower() != "low":
            F.append(dict(kind="stcg-priority", sym=x.get("symbol") or x.get("name", "?")[:22],
                          score=0, wt=x.get("weight_pct") or 0,
                          msg=f"held {hy}y, so STCG: must be marked a LOW priority sell"))

    # ---- 4. debt grandfathering ------------------------------------------------------
    for f in funds:
        if str(f.get("action") or f.get("verdict") or "").strip().lower() not in ("sell", "trim"):
            continue
        cat = str(f.get("category") or "").lower()
        if "debt" not in cat and "duration" not in cat and "gilt" not in cat and "bond" not in cat:
            continue
        pre = f.get("bought_pre_apr_2023")
        if pre and not f.get("structural_reason"):
            F.append(dict(kind="debt-grandfather", sym=str(f.get("name", "?"))[:26], score=0,
                          wt=f.get("weight_pct") or 0,
                          msg="debt bought before 1-Apr-2023 sold with no structural reason; "
                              "grandfathered treatment is forfeited"))

    if verbose:
        print(f"{len(F)} findings")
        if F:
            by = {}
            for f in F:
                by.setdefault(f["kind"], []).append(f)
            for kind, items in by.items():
                print(f"  [{kind}] x{len(items)}")
                for f in sorted(items, key=lambda z: -z["wt"]):
                    print(f"    {f['sym']:16s} wt={f['wt']:6.2f}%  {f['msg']}")
        print()
        print(f"churn = {churn:.1f}% of book across {len(sold)} lines "
              f"(split required above {CHURN_SPLIT:.0f}%)")
    return F


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: check_method.py <data_module.py>")
    sys.exit(1 if check(_load(sys.argv[1])) else 0)
