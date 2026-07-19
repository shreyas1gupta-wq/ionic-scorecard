"""
Money-first scoreboard v2 — Dr. Sameer Bhat (Overfit & Sensitivity Analyst), 2026-07-17.

Non-destructive fix pass over pragmatic_score.py per CONSOLIDATION.md
"HARNESS FIXES NEEDED" (items 2, 3, 4). Reads the SAME rnd/cards/*.json,
writes to a SEPARATE rnd/scoreboard_v2.csv — the v1 scorer and scoreboard.csv
are untouched, no card is overwritten or lost.

FIXES APPLIED (each documented so the fix itself is auditable):

  (a) DSR PER-FAMILY trial count (was GLOBAL, ~318 trials -> crushed every
      card's DSR toward 0 via the expected-max-Sharpe deflator, in the WRONG
      direction — a strong single-family result was being punished for
      trials run on unrelated families). Recomputed from stored (sr_hat,
      skew, kurtosis, n_obs) via the new harness.dsr_from_stats() using
      trials_counter.json's by_family count for that card's own family.
      [INFERENCE]: "family" = the hypothesis id (H0xx / W2_* group) as
      already stamped on the card by evaluate() — this is the honest
      "how many times did we re-test THIS idea" count, not a perfect
      independent-hypothesis count (some families share underlying data
      e.g. W2_ma sweeps 14 MA-length variants = 14 correlated trials, not
      14 independent ones — still deflates far less violently than 318,
      and still MORE conservative than treating it as 1 trial).

  (b) SIGNED IC_IR — verdict() in lib/harness.py kills on raw ic_ir < 0.20,
      which auto-kills any factor whose ECONOMICALLY EXPECTED direction is
      negative (low-vol, idio-vol, size, accruals, standalone-beta, mean-
      reversion, forensic-penalty: "high raw factor value -> LOW forward
      return" is the whole point of these hypotheses). Expected sign is
      pulled from backlog.json's hypothesis "sign" field (keyed by the H0xx
      family already on the card), with a keyword override for wave-2/
      scout families not in backlog.json whose names make the expected
      direction unambiguous (e.g. "lowvol", "idio_vol", "size"). Where sign
      is genuinely unknown (backlog "context"/"na"/"+/-", or an unmatched
      family), signed_ic_ir falls back to abs(ic_ir) and the row is flagged
      sign_source=UNKNOWN — [INFERENCE], flagged not guessed silently.

  (c) HORIZON-AWARE ANNUALIZATION — evaluate() multiplies mean(ls_ret_raw)
      by a hardcoded periods_per_year=12 regardless of horizon. That's
      correct for 1M (label IS a 1-month return). For 1Y it inflates the
      true annual return 12x (the label is already a 1-year return); for
      5Y it inflates 60x (label is a 5-year cumulative return, needs /5,
      not *12). Recovered mean(ls_ret_raw) = card_ann_return_LS / 12
      (inverting the original bug), then re-annualized by /HORIZON_YEARS.
      Cost drag is untouched — turnover is measured per MONTHLY rebalance
      regardless of label horizon, so *12 is correct there (rebalance
      cadence is monthly for all horizons per RESEARCH_PROTOCOL S1).

HARD GATES UNCHANGED (per CONSOLIDATION item 6 — these work, keep them):
  lag_test_delta > 0.25 (lookahead) or |placebo_ic| > 0.02 (leakage) -> FAIL_GATE.
"""
import json
import math
import os
import sys
import glob

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
import harness  # noqa: E402  (adds dsr_from_stats, _expected_max_sharpe)

C = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR = os.path.join(C, "cards")
TRIALS_PATH = os.path.join(C, "trials_counter.json")
BACKLOG_PATH = os.path.join(C, "backlog.json")

HORIZON_YEARS = {"1M": 1.0 / 12.0, "1Y": 1.0, "5Y": 5.0}

# families/keywords whose ECONOMICALLY EXPECTED direction is NEGATIVE
# (raw factor UP -> forward return DOWN is the hypothesis itself).
# Used only as a fallback when the family isn't an H0xx id found in
# backlog.json with an explicit sign. Matched case-insensitively as a
# substring of factor_id or family.
NEGATIVE_KEYWORDS = [
    "lowvol", "low_vol", "idio_vol", "idiovol", "downside_beta", "semidev",
    "accrual", "size", "marketcap_tilt", "mean_revers", "meanrev",
    "forensic_penalty", "beta_standalone", "assetgrowth", "asset_growth",
    "share_issuance", "netissuance", "bab", "betting_against_beta",
    "max_lottery", "lottery", "peg_", "reverse_dcf",
]


def g(d, *path, default=np.nan):
    for p in path:
        if isinstance(d, dict) and p in d:
            d = d[p]
        else:
            return default
    return d if d is not None else default


def load_sign_map():
    """family (H0xx) -> +1/-1/0(unknown), from backlog.json's 'sign' field."""
    m = {}
    try:
        bl = json.load(open(BACKLOG_PATH, encoding="utf-8"))
        for h in bl.get("hypotheses", []):
            s = h.get("sign")
            m[h.get("id")] = {"+": 1, "-": -1}.get(s, 0)  # context/na/+/- -> unknown
    except Exception:
        pass
    return m


def expected_sign(family: str, factor_id: str, sign_map: dict) -> tuple:
    """Returns (sign, source). sign in {1, -1, 0}; 0 = unknown -> caller
    falls back to abs(ic_ir)."""
    if family in sign_map and sign_map[family] != 0:
        return sign_map[family], f"backlog:{family}"
    low = f"{family or ''}_{factor_id or ''}".lower()
    for kw in NEGATIVE_KEYWORDS:
        if kw in low:
            return -1, f"keyword:{kw}"
    if family in sign_map and sign_map[family] == 0:
        return 0, f"backlog_ambiguous:{family}"
    return 1, "default_unconfirmed"


def recompute_dsr_per_family(card: dict, family_trials: dict) -> dict:
    dsr_block = card.get("dsr", {}) or {}
    if not isinstance(dsr_block, dict):
        # Defensive (2026-07-17, Manoj Pillai): a handful of on-disk
        # "*_SUMMARY.json" cards reuse the key "dsr" for an unrelated
        # p-value-like float from a different schema (not a harness.evaluate()
        # card at all — those always write dsr as a dict). Treat as missing
        # rather than crash; this card was already going to score as
        # all-NaN via g()'s isinstance-guarded lookups elsewhere in this file.
        dsr_block = {}
    sr_hat = dsr_block.get("sr_hat")
    skew = dsr_block.get("skew")
    kurt = dsr_block.get("kurtosis")
    n_obs = dsr_block.get("n_obs")
    fam = card.get("family") or "unknown"
    n_trials_fam = family_trials.get(fam, dsr_block.get("n_trials"))
    if sr_hat is None or n_obs is None or (isinstance(sr_hat, float) and math.isnan(sr_hat)):
        return {"dsr": np.nan, "n_trials_family": n_trials_fam, "n_trials_global": dsr_block.get("n_trials")}
    out = harness.dsr_from_stats(sr_hat, skew or 0.0, kurt if kurt is not None else 3.0, int(n_obs), int(n_trials_fam))
    out["n_trials_family"] = n_trials_fam
    out["n_trials_global"] = dsr_block.get("n_trials")
    return out


def horizon_aware_annualization(card: dict, horizon: str, sign: int = 1) -> dict:
    """sign flips the long/short legs for factors with a NEGATIVE expected
    direction (e.g. size, low-vol): the harness's decile spread is always
    top-decile-of-raw-factor MINUS bottom-decile, with no notion of which
    side is economically "long". For these factors the tradeable LS return
    is the NEGATIVE of the stored spread (go long the bottom decile). Left
    un-flipped (sign=0, unknown direction) the v1 sign is kept as-is and
    the row should be read as informational only, not a trade recipe."""
    ann_old = g(card, "long_short", "ann_return_LS", default=np.nan)
    cost_drag = g(card, "costs", "ann_cost_drag", default=0.0)
    if not np.isfinite(ann_old):
        return {"gross_ann_v2": np.nan, "net_ann_v2": np.nan}
    mean_ls_period = ann_old / 12.0                       # invert the old *12
    hy = HORIZON_YEARS.get(horizon, 1.0)
    flip = sign if sign in (1, -1) else 1
    gross_v2 = (mean_ls_period / hy) * flip
    net_v2 = gross_v2 - (cost_drag if np.isfinite(cost_drag) else 0.0)
    return {"gross_ann_v2": gross_v2, "net_ann_v2": net_v2}


def main():
    trials = json.load(open(TRIALS_PATH, encoding="utf-8"))
    family_trials = trials.get("by_family", {})
    sign_map = load_sign_map()

    rows = []
    for fp in glob.glob(os.path.join(CARDS_DIR, "*.json")):
        d = json.load(open(fp, encoding="utf-8"))
        fid = g(d, "factor_id")
        status = g(d, "status", default="OK")
        if status not in ("OK", None):
            rows.append({"id": fid, "horizon": g(d, "horizon"), "status": status})
            continue

        family = g(d, "family")
        horizon = g(d, "horizon")
        ic_ir = g(d, "ic", "ic_ir")
        ic_mean = g(d, "ic", "ic_mean")
        mono = g(d, "deciles", "monotonicity")
        hit = g(d, "long_short", "hit_rate")
        turn = g(d, "turnover", "avg_top_decile_turnover")
        lag = g(d, "lag_test", "lag_test_delta")
        plac = abs(g(d, "placebo", "placebo_ic", default=0) or 0)

        sign, sign_src = expected_sign(family, fid, sign_map)
        if sign == 0:
            signed_ic_ir = abs(ic_ir) if np.isfinite(ic_ir) else np.nan
        else:
            signed_ic_ir = ic_ir * sign if np.isfinite(ic_ir) else np.nan

        dsr_v2 = recompute_dsr_per_family(d, family_trials)
        ann_v2 = horizon_aware_annualization(d, horizon, sign=sign)

        gate_fail = (lag is not None and np.isfinite(lag) and lag > 0.25) or (plac > 0.02)

        rows.append({
            "id": fid, "family": family, "horizon": horizon, "basis": g(d, "return_basis"),
            "ic_ir_raw": ic_ir, "sign": sign, "sign_source": sign_src, "signed_ic_ir": signed_ic_ir,
            "ic_mean": ic_mean, "mono": mono, "hit": hit,
            "gross_LS_v1": g(d, "long_short", "ann_return_LS"),
            "gross_LS_v2": ann_v2["gross_ann_v2"], "net_LS_v2": ann_v2["net_ann_v2"],
            "turnover": turn,
            "dsr_v1_global": g(d, "dsr", "dsr"), "n_trials_global": g(d, "dsr", "n_trials"),
            "dsr_v2_perfamily": dsr_v2.get("dsr"), "n_trials_family": dsr_v2.get("n_trials_family"),
            "pbo": g(d, "pbo", "pbo"),
            "lag": lag, "placebo": plac, "gate_fail": "LOOKAHEAD/PLACEBO" if gate_fail else "",
            "status": "OK",
        })

    df = pd.DataFrame(rows)
    ok = df[df["status"] == "OK"].copy()

    def verdict_v2(r):
        if r["gate_fail"]:
            return "FAIL_GATE"
        sic = r["signed_ic_ir"]
        if not np.isfinite(sic):
            return "WEAK"
        if sic > 0.3 and (pd.isna(r["mono"]) or abs(r["mono"]) > 0.5) and r["net_LS_v2"] > 0:
            return "PROMOTE*"
        if sic > 0.2 and r["net_LS_v2"] > 0:
            return "CANDIDATE"
        return "WEAK"

    ok["verdict_v2"] = ok.apply(verdict_v2, axis=1)
    ok = ok.sort_values(["horizon", "signed_ic_ir"], ascending=[True, False])
    out_path = os.path.join(C, "scoreboard_v2.csv")
    ok.to_csv(out_path, index=False)

    pd.set_option("display.width", 240)
    pd.set_option("display.max_rows", 80)
    print(f"cards: {len(df)}  OK: {len(ok)}  FAIL_GATE: {int((ok.verdict_v2=='FAIL_GATE').sum())}  "
          f"PROMOTE*: {int((ok.verdict_v2=='PROMOTE*').sum())}  CANDIDATE: {int((ok.verdict_v2=='CANDIDATE').sum())}")
    show = ["id", "family", "horizon", "sign", "sign_source", "ic_ir_raw", "signed_ic_ir",
            "mono", "net_LS_v2", "dsr_v1_global", "dsr_v2_perfamily", "n_trials_family", "verdict_v2"]
    print("\n=== PROMOTE* + CANDIDATE (v2) ===")
    print(ok[ok.verdict_v2.isin(["PROMOTE*", "CANDIDATE"])][show].round(3).to_string(index=False))
    print(f"\nwritten: {out_path}")


if __name__ == "__main__":
    main()
