"""Regime-selection edge study for intraday Nifty premium selling.

QUESTION
--------
We calibrated real NSE option data and found ATM implied vol ~ India VIX
(multiplier m ~ 1.0-1.2 for short DTE). So an intraday option SELLER only
profits when REALIZED intraday vol comes in BELOW implied (~VIX). This script
asks the only question that then matters:

    Can day-type features KNOWN AT 09:20 predict the low-realized-vol
    ("range") days, creating a tradeable premium-selling edge?

METHOD (no-lookahead throughout)
--------------------------------
For each trading day over the 09:20 -> 15:00 premium-selling window we compute:
  (a) close-to-close 1-min realized vol, annualized on intraday minutes;
  (b) the absolute open(09:20)->close(15:00) move in %;
  (c) the max intraday excursion (high/low) from the 09:20 price.

We turn VIX into an implied expected |move| over the same window:
  daily_sigma  = VIX/100 / sqrt(252)
  window_sigma = daily_sigma * sqrt(window_hours / 6.25)         # time-scale
  E[|move|]    = window_sigma * sqrt(2/pi) * spot                # half-normal

and define the per-day SELLER PnL PROXY:
  seller_pnl_proxy = implied_expected_move - realized_abs_move   (Rs. points)
  (positive  -> realized came in below implied -> seller wins)

A normalized version (in % of spot) makes buckets comparable across regimes.

The 09:20 SELECTION features come from features.horizon.day_features() (gap,
ORB5 width, VIX level, VIX 5d change, prior-day range, bias) plus an
expiry-vs-non-expiry flag. We:
  3. correlate each feature with the proxy and bucket the proxy by feature;
  4. greedily build the BEST 09:20 feature rule on the IN-SAMPLE half only
     (pre 2022-12-16) and report whether it lifts the seller win-rate above
     the unconditional base rate IN-SAMPLE *and* OUT-OF-SAMPLE (post) -- the
     honest overfit check;
  5. save per-day metrics to results/realized_vol_study.csv and print a
     summary + one-paragraph verdict.

Outcome (realized vol) is what we PREDICT; selection uses 09:20 data only.
Console is cp1252 -> ASCII only ("Rs.", "->").
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import PROCESSED_DIR, RANDOM_SEED, RESULTS_DIR, TRADING_DAYS_PER_YEAR  # noqa: E402
from features.horizon import day_features  # noqa: E402
from strategies.sleeves import all_expiry_days  # noqa: E402

np.random.seed(RANDOM_SEED)

# ---- window definition (the premium-selling window) ------------------------
WIN_START = dt.time(9, 20)
WIN_END = dt.time(15, 0)
WINDOW_HOURS = (15 * 60 + 0 - (9 * 60 + 20)) / 60.0     # 5.6667 hours
FULL_SESSION_HOURS = 6.25                               # 09:15 -> 15:30
MIN_WINDOW_BARS = 200                                   # skip half/short days
OOS_SPLIT = pd.Timestamp("2022-12-16")                  # IS = pre, OOS = post

ANNUALIZE_BARS_PER_YR = TRADING_DAYS_PER_YEAR * FULL_SESSION_HOURS * 60  # 1-min


# ---------------------------------------------------------------------------
# 1. Per-day intraday realized-vol proxies + 2. VIX-implied expected move
# ---------------------------------------------------------------------------
def per_day_metrics(nifty: pd.DataFrame, dayf: pd.DataFrame,
                    expiry_days: set) -> pd.DataFrame:
    """One row per day with realized-vol proxies and the seller PnL proxy."""
    idx_t = nifty.index.time
    in_win = (idx_t >= WIN_START) & (idx_t <= WIN_END)
    win = nifty[in_win]
    day = win.index.normalize()

    rows = []
    for d, sub in win.groupby(day):
        if len(sub) < MIN_WINDOW_BARS:
            continue
        close = sub["close"].to_numpy(dtype=float)
        spot0 = float(sub["open"].iloc[0])              # 09:20 open = entry spot
        if spot0 <= 0:
            continue

        # (a) close-to-close 1-min realized vol, annualized
        rets = np.diff(np.log(close))
        rv_ann = float(np.std(rets, ddof=0) * np.sqrt(ANNUALIZE_BARS_PER_YR))

        # (b) absolute open->close move over the window
        close_last = float(sub["close"].iloc[-1])
        abs_move_pts = abs(close_last - spot0)
        abs_move_pct = abs_move_pts / spot0

        # (c) max intraday excursion from the 09:20 price (worst adverse swing)
        hi = float(sub["high"].max())
        lo = float(sub["low"].min())
        max_exc_pts = max(hi - spot0, spot0 - lo)
        max_exc_pct = max_exc_pts / spot0

        # --- VIX-implied expected |move| over the window (half-normal) ------
        vix = float(dayf["vix_open"].get(d, np.nan))
        if not np.isfinite(vix) or vix <= 0:
            continue
        daily_sigma = vix / 100.0 / np.sqrt(TRADING_DAYS_PER_YEAR)        # frac
        window_sigma = daily_sigma * np.sqrt(WINDOW_HOURS / FULL_SESSION_HOURS)
        exp_move_pct = window_sigma * np.sqrt(2.0 / np.pi)               # E|.|/S
        exp_move_pts = exp_move_pct * spot0

        # --- seller PnL proxy: implied expected move - realized move --------
        # absolute (points) and normalized (% of spot, for cross-regime buckets)
        proxy_pts = exp_move_pts - abs_move_pts
        proxy_pct = exp_move_pct - abs_move_pct

        rows.append({
            "day": d,
            "spot_open": spot0,
            "rv_annual": rv_ann,
            "abs_move_pct": abs_move_pct,
            "abs_move_pts": abs_move_pts,
            "max_exc_pct": max_exc_pct,
            "max_exc_pts": max_exc_pts,
            "vix_open": vix,
            "exp_move_pct": exp_move_pct,
            "exp_move_pts": exp_move_pts,
            "seller_proxy_pts": proxy_pts,
            "seller_proxy_pct": proxy_pct,
            "seller_win": int(proxy_pct > 0),
            "is_expiry": int(d in expiry_days),
            # 09:20 selection features (no-lookahead)
            "gap_pct": float(dayf["gap_pct"].get(d, np.nan)),
            "orb5_width": float(dayf["orb5_width"].get(d, np.nan)),
            "vix_5d_chg": float(dayf["vix_5d_chg"].get(d, np.nan)),
            "prev_day_range": float(dayf["prev_day_range"].get(d, np.nan)),
            "bias": float(dayf["bias"].get(d, np.nan)),
        })

    df = pd.DataFrame(rows).set_index("day").sort_index()
    df["abs_gap_pct"] = df["gap_pct"].abs()
    df["seg"] = np.where(df.index < OOS_SPLIT, "IS", "OOS")
    return df


# ---------------------------------------------------------------------------
# 3. Correlations + feature buckets
# ---------------------------------------------------------------------------
SELECTION_FEATURES = [
    "abs_gap_pct", "orb5_width", "vix_open", "vix_5d_chg",
    "prev_day_range", "bias",
]


def correlations(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for f in SELECTION_FEATURES:
        s = df[[f, "seller_proxy_pct"]].dropna()
        if len(s) < 30:
            continue
        pear = s[f].corr(s["seller_proxy_pct"], method="pearson")
        spear = s[f].corr(s["seller_proxy_pct"], method="spearman")
        rows.append({"feature": f, "pearson": pear, "spearman": spear,
                     "n": len(s)})
    return pd.DataFrame(rows)


def bucket_table(df: pd.DataFrame) -> pd.DataFrame:
    """Mean seller proxy + hit-rate per feature bucket (per spec)."""
    base_wr = df["seller_win"].mean()
    base_proxy = df["seller_proxy_pct"].mean()
    rows = [{"feature": "<UNCONDITIONAL>", "bucket": "all", "n": len(df),
             "mean_proxy_pct": base_proxy, "mean_proxy_pts":
             df["seller_proxy_pts"].mean(), "win_rate": base_wr}]

    def add(feature, label, mask):
        sub = df[mask]
        if not len(sub):
            return
        rows.append({"feature": feature, "bucket": label, "n": len(sub),
                     "mean_proxy_pct": sub["seller_proxy_pct"].mean(),
                     "mean_proxy_pts": sub["seller_proxy_pts"].mean(),
                     "win_rate": sub["seller_win"].mean()})

    # gap small/large at the median |gap|
    gmed = df["abs_gap_pct"].median()
    add("abs_gap", f"small (<= {gmed:.4f})", df["abs_gap_pct"] <= gmed)
    add("abs_gap", f"large (>  {gmed:.4f})", df["abs_gap_pct"] > gmed)

    # ORB5 width low/high quartile (the spec explicitly asks for quartiles)
    qlo, qhi = df["orb5_width"].quantile([0.25, 0.75])
    add("orb5_width", f"low Q1 (<= {qlo:.4f})", df["orb5_width"] <= qlo)
    add("orb5_width", f"high Q4 (> {qhi:.4f})", df["orb5_width"] > qhi)

    # VIX level terciles
    v1, v2 = df["vix_open"].quantile([1 / 3, 2 / 3])
    add("vix_open", f"low (<= {v1:.2f})", df["vix_open"] <= v1)
    add("vix_open", f"mid ({v1:.2f}-{v2:.2f}]",
        (df["vix_open"] > v1) & (df["vix_open"] <= v2))
    add("vix_open", f"high (> {v2:.2f})", df["vix_open"] > v2)

    # expiry vs non-expiry
    add("expiry", "expiry day", df["is_expiry"] == 1)
    add("expiry", "non-expiry", df["is_expiry"] == 0)

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# 4. Greedy "best rule" learned IN-SAMPLE, evaluated IS vs OOS (overfit check)
# ---------------------------------------------------------------------------
def candidate_conditions(is_df: pd.DataFrame) -> dict:
    """Threshold conditions, with directions/cutoffs fitted ON IS ONLY.

    Each value is a boolean Series over the FULL df (passed in via .reindex
    later); here we just store (feature, op, threshold) fitted on IS.
    """
    cands = {}
    # gap: small gap -> calmer day expected
    cands["gap_small"] = ("abs_gap_pct", "<=", is_df["abs_gap_pct"].median())
    # ORB5 width: tight opening range -> range day
    cands["orb5_tight"] = ("orb5_width", "<=", is_df["orb5_width"].median())
    # VIX level: try both low and high (IV is rich when VIX high)
    cands["vix_low"] = ("vix_open", "<=", is_df["vix_open"].median())
    cands["vix_high"] = ("vix_open", ">", is_df["vix_open"].median())
    # VIX 5d change: falling VIX -> mean-reverting / calming
    cands["vix_falling"] = ("vix_5d_chg", "<=", 0.0)
    # prior-day range: small prior range -> low-vol persistence
    cands["prevrange_small"] = ("prev_day_range", "<=",
                                is_df["prev_day_range"].median())
    return cands


def apply_cond(df: pd.DataFrame, cond) -> pd.Series:
    feat, op, thr = cond
    col = df[feat]
    if op == "<=":
        return col <= thr
    return col > thr


def wr(df: pd.DataFrame, mask: pd.Series) -> tuple[float, int]:
    sub = df[mask]
    return (float(sub["seller_win"].mean()) if len(sub) else np.nan, len(sub))


def greedy_best_rule(df: pd.DataFrame, cands: dict, is_df: pd.DataFrame,
                     min_frac: float = 0.10, max_terms: int = 3):
    """Greedily add AND-conditions to maximize IS win-rate, keeping >= min_frac
    of IS days selected. Returns (chosen list, IS metrics, full-mask fn)."""
    n_is = len(is_df)
    chosen = []
    cur_mask_is = pd.Series(True, index=is_df.index)
    best_wr = is_df["seller_win"].mean()
    remaining = dict(cands)

    for _ in range(max_terms):
        best_add, best_add_wr, best_add_mask = None, best_wr, None
        for name, cond in remaining.items():
            m = cur_mask_is & apply_cond(is_df, cond)
            if m.sum() < max(30, min_frac * n_is):
                continue
            w = is_df[m]["seller_win"].mean()
            if w > best_add_wr:
                best_add, best_add_wr, best_add_mask = name, w, m
        if best_add is None:
            break
        chosen.append((best_add, remaining.pop(best_add)))
        cur_mask_is = best_add_mask
        best_wr = best_add_wr

    def full_mask(frame: pd.DataFrame) -> pd.Series:
        m = pd.Series(True, index=frame.index)
        for _, cond in chosen:
            m &= apply_cond(frame, cond)
        return m

    return chosen, full_mask


# ---------------------------------------------------------------------------
def main() -> None:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("Loading data ...")
    nifty = pd.read_parquet(PROCESSED_DIR / "nifty_1min.parquet")
    vix_raw = pd.read_parquet(PROCESSED_DIR / "vix_1min.parquet")["vix"]
    # vix_1min has a slightly different row count than nifty; day_features
    # groups VIX by the NIFTY index, so align it onto the nifty bars first
    # (forward-fill the last known VIX print -- no lookahead).
    vix_bars = vix_raw.reindex(nifty.index).ffill().bfill()

    trading_days = pd.DatetimeIndex(nifty.index.normalize().unique())
    expiry_days = all_expiry_days(trading_days)
    dayf = day_features(nifty, vix_bars)

    print(f"Computing per-day metrics over {WIN_START}-{WIN_END} "
          f"window ({WINDOW_HOURS:.2f}h) ...")
    df = per_day_metrics(nifty, dayf, expiry_days)
    df = df.dropna(subset=["seller_proxy_pct"])
    print(f"  usable days: {len(df)}  "
          f"(IS={int((df.seg=='IS').sum())}, OOS={int((df.seg=='OOS').sum())})")

    # save per-day CSV
    out_csv = RESULTS_DIR / "realized_vol_study.csv"
    df.reset_index().to_csv(out_csv, index=False)

    # ---- sanity: is the m=1 (VIX-priced) seller a coin flip? ---------------
    base_wr = df["seller_win"].mean()
    print("\n" + "=" * 72)
    print("SANITY: realized vs VIX-implied expected move (m = 1.0, seller PoV)")
    print("=" * 72)
    print(f"  mean realized abs move  : {df['abs_move_pct'].mean()*100:6.3f}% "
          f"of spot")
    print(f"  mean VIX-implied E|move|: {df['exp_move_pct'].mean()*100:6.3f}% "
          f"of spot")
    print(f"  ratio realized/implied  : "
          f"{df['abs_move_pct'].mean()/df['exp_move_pct'].mean():6.3f}")
    print(f"  mean realized 1-min vol : {df['rv_annual'].mean()*100:6.2f}% ann")
    print(f"  mean VIX (open)         : {df['vix_open'].mean():6.2f}")
    print(f"  UNCONDITIONAL seller win-rate (proxy>0) : {base_wr:6.3f}")
    print(f"  mean seller proxy       : {df['seller_proxy_pct'].mean()*100:+.3f}"
          f"% of spot  ({df['seller_proxy_pts'].mean():+.1f} pts)")

    # ---- 3a. correlations --------------------------------------------------
    print("\n" + "=" * 72)
    print("3a. CORRELATION of 09:20 features vs seller PnL proxy (% of spot)")
    print("    positive corr => higher feature -> seller wins more")
    print("=" * 72)
    corr = correlations(df)
    print(corr.round(4).to_string(index=False))

    # ---- 3b. feature buckets ----------------------------------------------
    print("\n" + "=" * 72)
    print("3b. SELLER PROXY by 09:20 feature bucket (full sample)")
    print("    mean_proxy_pct = avg (implied - realized) in % of spot")
    print("    win_rate       = fraction of days seller wins (proxy>0)")
    print("=" * 72)
    bt = bucket_table(df)
    show = bt.copy()
    show["mean_proxy_pct"] = (show["mean_proxy_pct"] * 100).round(3)
    show["mean_proxy_pts"] = show["mean_proxy_pts"].round(1)
    show["win_rate"] = show["win_rate"].round(3)
    print(show.to_string(index=False))

    # ---- 4. best rule learned IS, evaluated IS vs OOS ---------------------
    is_df = df[df["seg"] == "IS"]
    oos_df = df[df["seg"] == "OOS"]
    cands = candidate_conditions(is_df)
    chosen, full_mask = greedy_best_rule(df, cands, is_df)

    print("\n" + "=" * 72)
    print("4. BEST 09:20 SELECTION RULE (greedily fit on IN-SAMPLE only)")
    print("=" * 72)
    if not chosen:
        print("  No feature condition raised IS win-rate above base. "
              "No selectable edge.")
        rule_str = "(none)"
    else:
        rule_str = " AND ".join(
            f"{c[0]}" for c in chosen)
        print("  Rule:", rule_str)
        for name, cond in chosen:
            f, op, thr = cond
            print(f"    - {name}:  {f} {op} {thr:.5f}")

    is_mask = full_mask(is_df)
    oos_mask = full_mask(oos_df)
    is_sel_wr, is_n = wr(is_df, is_mask)
    oos_sel_wr, oos_n = wr(oos_df, oos_mask)
    is_base = is_df["seller_win"].mean()
    oos_base = oos_df["seller_win"].mean()

    print("\n  Seller win-rate: selected days vs unconditional base")
    print(f"  {'segment':<6} {'base_wr':>8} {'sel_wr':>8} {'lift':>8} "
          f"{'sel_n':>7} {'sel_frac':>9} {'avg_proxy_pct':>14}")
    for seg, sub, mask, base in [("IS", is_df, is_mask, is_base),
                                 ("OOS", oos_df, oos_mask, oos_base)]:
        selw, n = wr(sub, mask)
        frac = n / len(sub) if len(sub) else np.nan
        avgp = sub[mask]["seller_proxy_pct"].mean() * 100 if n else np.nan
        lift = selw - base if np.isfinite(selw) else np.nan
        print(f"  {seg:<6} {base:8.3f} {selw:8.3f} {lift:+8.3f} {n:7d} "
              f"{frac:9.3f} {avgp:+14.3f}")

    # ---- 5. verdict --------------------------------------------------------
    is_lift = (is_sel_wr - is_base) if np.isfinite(is_sel_wr) else np.nan
    oos_lift = (oos_sel_wr - oos_base) if np.isfinite(oos_sel_wr) else np.nan
    holds_oos = (np.isfinite(oos_lift) and oos_lift >= 0.02
                 and oos_sel_wr > 0.50)
    decays = (np.isfinite(is_lift) and np.isfinite(oos_lift)
              and is_lift > 0.02 and oos_lift < 0.5 * is_lift)

    print("\n" + "=" * 72)
    print("VERDICT")
    print("=" * 72)
    parts = []
    parts.append(
        f"On {len(df)} trading days (2015-2026), pricing options at m=1 "
        f"(ATM IV = VIX, per our NSE calibration), the intraday "
        f"premium-seller's unconditional win-rate over the 09:20->15:00 "
        f"window is {base_wr:.1%}, with a mean edge of "
        f"{df['seller_proxy_pct'].mean()*100:+.3f}% of spot "
        f"({df['seller_proxy_pts'].mean():+.0f} pts) per day before costs.")
    if not chosen:
        parts.append(
            "No 09:20 day-type feature (gap, ORB5 width, VIX level/change, "
            "prior-day range, bias, expiry) lifted the in-sample win-rate "
            "above this base, so REGIME SELECTION does NOT create a "
            "premium-selling edge here.")
    else:
        parts.append(
            f"The best in-sample rule [{rule_str}] lifted the seller win-rate "
            f"from {is_base:.1%} to {is_sel_wr:.1%} IS (+{is_lift:.1%}), but "
            f"OUT-OF-SAMPLE it went {oos_base:.1%} -> {oos_sel_wr:.1%} "
            f"({oos_lift:+.1%}).")
        if holds_oos and not decays:
            parts.append(
                "The lift PERSISTS out-of-sample, so there is a modest but "
                "real regime-selection edge -- though it must still clear "
                "transaction costs and the IV multiplier before it is "
                "tradeable.")
        elif decays or not holds_oos:
            parts.append(
                "The lift LARGELY DISAPPEARS out-of-sample, the hallmark of "
                "an overfit predictor. Regime selection on these 09:20 "
                "features does NOT create a robust, tradeable "
                "premium-selling edge.")
    verdict = " ".join(parts)
    # wrap to ~78 cols for readability
    import textwrap
    print("\n".join(textwrap.wrap(verdict, 78)))

    print(f"\nsaved per-day metrics -> {out_csv}")


if __name__ == "__main__":
    main()
