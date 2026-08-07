# -*- coding: utf-8 -*-
"""psu_neutral_test.py - TEST 1 (b)+(c): PSU-neutral reweighting + PSU-deleted bound.
Nikhil Bose, red team, 2026-08-06. Independent recomputation from observations.csv -- does NOT
trust bt_regime_psu_test.py's own psu_test.csv output, though it cross-checks against it.

(b) PSU-NEUTRAL: within each formation x decile, reweight PSU vs non-PSU rows so the decile's
    WEIGHTED PSU share equals that formation's universe PSU share. The score can no longer express
    a net PSU over/under-weight inside any decile; whatever spread survives is stock selection
    within-PSU-status, not a PSU tilt. Uses a weighted, continuously-trimmed (5% each side by
    weight-mass) mean so it nests the existing unweighted trimmed-mean statistic exactly when
    weights are uniform (verified below as a sanity check).
(c) PSU-DELETED: drop PSU rows outright, recompute the spread. A bound, not the preferred estimate,
    because deletion also shrinks decile membership and re-ranks everyone else within the decile
    (not what the frozen model would actually do -- named "bound" per the brief, not "the number").

Run for BOTH the original hand list (bt_regime_psu_test.py) and the corrected/expanded list
(psu_list_build.py's IMPROVED_PSU) so the PSU-completeness question does not silently change the
headline.
"""
import os
import numpy as np
import pandas as pd

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
HERE = os.path.dirname(os.path.abspath(__file__))
SC750 = os.path.dirname(os.path.dirname(HERE))
OBS = os.path.join(SC750, "results", "DECILE_ROLLING_20260805", "observations.csv")
OUT = HERE
NDEC = 10

HAND_LIST = {
    "ONGC", "OIL", "IOC", "BPCL", "HINDPETRO", "GAIL", "PETRONET", "MGL", "IGL",
    "NTPC", "POWERGRID", "NHPC", "SJVN", "THERMAX", "NLCINDIA", "PFC", "RECLTD", "IREDA",
    "COALINDIA", "NMDC", "SAIL", "NALCO", "MOIL", "HINDCOPPER", "KIOCL", "GMDCLTD",
    "BEL", "HAL", "BHEL", "BEML", "MAZDOCK", "COCHINSHIP", "GRSE", "BDL", "MIDHANI",
    "ENGINERSIN", "ITI",
    "IRFC", "RVNL", "IRCTC", "IRCON", "RITES", "NBCC", "HUDCO", "CONCOR", "SCI", "RAILTEL",
    "SBIN", "CANBK", "PNB", "BANKBARODA", "UNIONBANK", "INDIANB", "CENTRALBK", "IOB",
    "UCOBANK", "MAHABANK", "PSB", "J&KBANK",
    "LICI", "GICRE", "NIACL", "IFCI", "SBICARD", "SBILIFE",
    "BALMLAWRIE", "STCINDIA", "MMTC", "HINDZINC", "FACT", "RCF", "NFL", "GSFC",
}
IMPROVED_PSU = (HAND_LIST - {"THERMAX"}) | {"NATIONALUM", "BANKINDIA", "NTPCGREEN"}


def trim(x, p=0.05):
    a = np.sort(np.asarray(pd.Series(x).dropna(), dtype=float))
    k = int(len(a) * p)
    core = a[k:len(a) - k] if len(a) > 2 * k else a
    return float(core.mean()) if len(core) else np.nan


def weighted_trim_mean(values, weights, p=0.05):
    """Trim 5% of WEIGHT MASS from each tail (continuous, not row-count), then weighted mean of
    the remainder. Reduces exactly to the unweighted trimmed mean when all weights are equal."""
    v = np.asarray(values, dtype=float)
    w = np.asarray(weights, dtype=float)
    m = ~np.isnan(v)
    v, w = v[m], w[m]
    if len(v) == 0 or w.sum() <= 0:
        return np.nan
    order = np.argsort(v)
    v, w = v[order], w[order].copy()
    total = w.sum()
    lo_cut, hi_cut = p * total, p * total
    i = 0
    while lo_cut > 1e-12 and i < len(w):
        take = min(w[i], lo_cut)
        w[i] -= take
        lo_cut -= take
        i += 1
    j = len(w) - 1
    while hi_cut > 1e-12 and j >= 0:
        take = min(w[j], hi_cut)
        w[j] -= take
        hi_cut -= take
        j -= 1
    if w.sum() <= 0:
        return np.nan
    return float(np.sum(v * w) / np.sum(w))


def sanity_check():
    rng = np.random.default_rng(0)
    x = rng.normal(size=500)
    a = trim(x)
    b = weighted_trim_mean(x, np.ones_like(x))
    assert abs(a - b) < 1e-9, (a, b)
    print(f"sanity check OK: unweighted trim={a:.6f}  weighted(uniform)={b:.6f}")


def psu_neutral_weights(sub, is_psu_col, p_target):
    """Return a weight per row so weighted PSU share of `sub` == p_target. w_non=1 for all
    non-PSU rows; w_psu solved in closed form. Returns (weights, adjustable: bool)."""
    is_psu = sub[is_psu_col].values
    n_psu = int(is_psu.sum())
    n_non = int((~is_psu).sum())
    w = np.ones(len(sub))
    if n_psu == 0 or n_non == 0 or p_target <= 0 or p_target >= 1:
        return w, False   # cannot reach the target composition by reweighting alone
    w_psu = p_target * n_non / (n_psu * (1 - p_target))
    w[is_psu] = w_psu
    return w, True


def run_for_list(d, psu_set, label):
    d = d.copy()
    d["is_psu"] = d["sym"].astype(str).str.upper().isin(psu_set)
    print(f"\n{'='*90}\nPSU LIST: {label}  ({len(psu_set)} names, "
          f"{d['is_psu'].sum()} of {len(d)} obs = {d['is_psu'].mean()*100:.1f}%)")

    # ---------- (c) PSU-deleted bound, pooled ----------
    ex = d[~d["is_psu"]]
    tab_all = d.groupby("dec_final", observed=True)["fwd"].apply(lambda x: trim(x) * 100).round(2)
    tab_ex = ex.groupby("dec_final", observed=True)["fwd"].apply(lambda x: trim(x) * 100).round(2)
    spread_all = tab_all.loc[NDEC] - tab_all.loc[1]
    spread_ex = tab_ex.loc[NDEC] - tab_ex.loc[1]
    print(f"\n(c) PSU-DELETED bound (pooled trim5):")
    print(f"    D10-D1 WITH PSUs    = {spread_all:+.2f}pp   (D1={tab_all.loc[1]:+.2f} D10={tab_all.loc[NDEC]:+.2f})")
    print(f"    D10-D1 PSUs DELETED = {spread_ex:+.2f}pp   (D1={tab_ex.loc[1]:+.2f} D10={tab_ex.loc[NDEC]:+.2f}, n={len(ex)})")

    # per-formation hit rate, PSU-deleted
    per_ex = []
    for f, s2 in ex.groupby("formation"):
        a = s2[s2["dec_final"] == 1]["fwd"]
        b = s2[s2["dec_final"] == NDEC]["fwd"]
        if len(a) and len(b):
            per_ex.append((trim(b) - trim(a)) * 100)
    hit_ex = float(np.mean([x > 0 for x in per_ex]) * 100) if per_ex else np.nan
    print(f"    formations usable: {len(per_ex)}/35   D10>D1 hit rate (ex-PSU) = {hit_ex:.1f}%   "
          f"median spread {np.median(per_ex):+.1f}pp   worst {np.min(per_ex):+.1f}pp")

    # ---------- (b) PSU-NEUTRAL reweighting, per formation x decile ----------
    print(f"\n(b) PSU-NEUTRAL (decile PSU-weight forced = formation universe PSU-weight):")
    rows_pooled_v = {dec: [] for dec in range(1, NDEC + 1)}
    rows_pooled_w = {dec: [] for dec in range(1, NDEC + 1)}
    per_formation_spread = []
    n_unadjustable = 0
    n_decile_formation = 0
    for f, sf in d.groupby("formation"):
        p_target = sf["is_psu"].mean()
        d1w = d10w = np.nan
        for dec, sub in sf.groupby("dec_final", observed=True):
            n_decile_formation += 1
            w, adjustable = psu_neutral_weights(sub, "is_psu", p_target)
            if not adjustable:
                n_unadjustable += 1
            rows_pooled_v[int(dec)].extend(sub["fwd"].values.tolist())
            rows_pooled_w[int(dec)].extend(w.tolist())
            if dec == 1:
                d1w = weighted_trim_mean(sub["fwd"].values, w)
            if dec == NDEC:
                d10w = weighted_trim_mean(sub["fwd"].values, w)
        if pd.notna(d1w) and pd.notna(d10w):
            per_formation_spread.append((d10w - d1w) * 100)
    print(f"    decile x formation cells: {n_decile_formation}   unadjustable (0% or 100% PSU "
          f"already, target unreachable by reweight): {n_unadjustable} "
          f"({n_unadjustable/n_decile_formation*100:.1f}%)")

    tab_neutral = {}
    for dec in range(1, NDEC + 1):
        tab_neutral[dec] = weighted_trim_mean(rows_pooled_v[dec], rows_pooled_w[dec]) * 100
    tab_neutral = pd.Series(tab_neutral)
    spread_neutral_pooled = tab_neutral.loc[NDEC] - tab_neutral.loc[1]
    hit_neutral = float(np.mean([x > 0 for x in per_formation_spread]) * 100)
    print(f"    pooled weighted-trim5 by decile:")
    print("    " + tab_neutral.round(2).to_string().replace("\n", "\n    "))
    print(f"    D10-D1 (pooled weighted trim5)      = {spread_neutral_pooled:+.2f}pp")
    print(f"    D10-D1 (mean of per-formation, n={len(per_formation_spread)}) = "
          f"{np.mean(per_formation_spread):+.2f}pp   median {np.median(per_formation_spread):+.2f}pp   "
          f"worst {np.min(per_formation_spread):+.2f}pp")
    print(f"    D10>D1 hit rate under PSU-neutral    = {hit_neutral:.1f}%  "
          f"({sum(x>0 for x in per_formation_spread)}/{len(per_formation_spread)})")

    # ---------- PSU concentration by decile, for the record ----------
    psu_share = (d.groupby("dec_final", observed=True)["is_psu"].mean() * 100).round(1)
    print(f"\n    PSU share of each decile (%), for reference:")
    print("    " + psu_share.to_string().replace("\n", "\n    "))

    return dict(label=label, n_psu_names=len(psu_set), psu_share_pct=round(float(d["is_psu"].mean()*100), 2),
                spread_with_psu=round(float(spread_all), 2), spread_ex_psu=round(float(spread_ex), 2),
                hit_rate_ex_psu=round(hit_ex, 1),
                spread_neutral_pooled=round(float(spread_neutral_pooled), 2),
                spread_neutral_mean_of_formations=round(float(np.mean(per_formation_spread)), 2),
                spread_neutral_median_of_formations=round(float(np.median(per_formation_spread)), 2),
                spread_neutral_worst_formation=round(float(np.min(per_formation_spread)), 2),
                hit_rate_neutral=round(hit_neutral, 1),
                pct_cells_unadjustable=round(n_unadjustable / n_decile_formation * 100, 1))


def main():
    sanity_check()
    d = pd.read_csv(OBS)
    print(f"loaded observations.csv: {len(d)} rows, {d['formation'].nunique()} formations, "
          f"{d['sym'].nunique()} symbols")

    results = []
    results.append(run_for_list(d, HAND_LIST, "ORIGINAL hand list (bt_regime_psu_test.py, 73 names)"))
    results.append(run_for_list(d, IMPROVED_PSU, "IMPROVED list (Thermax removed; +NATIONALUM +BANKINDIA "
                                                  "+NTPCGREEN; 75 names)"))

    out = pd.DataFrame(results)
    out.to_csv(os.path.join(OUT, "psu_neutral_results.csv"), index=False)
    print(f"\n\nwrote {os.path.join(OUT, 'psu_neutral_results.csv')}")
    print("\n=== SUMMARY TABLE ===")
    print(out[["label", "psu_share_pct", "spread_with_psu", "spread_neutral_pooled",
               "spread_ex_psu", "hit_rate_neutral", "hit_rate_ex_psu",
               "pct_cells_unadjustable"]].to_string(index=False))


if __name__ == "__main__":
    main()
