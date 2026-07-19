"""
H1 dealer-gamma/GEX cheap-test — pre-registered spec per
Shreyas_Ionic_AMC/04_RND_LAB/ideas/20260703_dealer_gamma_gex.md

Steps:
 1. Load NIFTY OI surface (402 sparse snapshot dates), join spot (nifty50.parquet).
 2. Back-solve IV per strike/expiry/date from option premium (Black-Scholes, European),
    cap IV<=100% per firm Lessons Learned (INFY IV=133% blowup landmine).
 3. Compute BS gamma per row -> net GEX per trade_date under BOTH candidate sign
    conventions (US-standard call-long/put-short vs India-both-short).
 4. Quintile-bucket dates by GEX (per convention). Compare next-day NIFTY realized
    range across buckets (Mann-Whitney extreme-quintile spread + bootstrap CI).
 5. Join S-04 short-strangle per-trade P&L (asof-backward on entry date) to the
    active GEX bucket at entry; compare P&L by bucket.
 6. Placebo: shuffle bucket labels across dates, rebuild the extreme-quintile spread
    null distribution (2000 draws), compare observed spread's percentile.

No model fitting / no optimization — descriptive bucket comparison only, per spec.
PIT note: GEX at trade_date uses only that date's own OI snapshot (no future OI).
Strangle join is asof-BACKWARD (most recent GEX snapshot at/before entry) - PIT safe.
Quintile cut points use the full 402-date sample distribution (descriptive
characterization only, NOT a live daily gate - the one-pager itself gates that
build-out behind denser OI data, kill criterion #4). No live trades are generated
by this script.
"""
import sys
import numpy as np
import pandas as pd
from scipy.stats import norm, mannwhitneyu

RNG = np.random.default_rng(42)
R = 0.065  # flat India risk-free proxy (free parameter, documented)
IV_CAP = 1.00  # firm landmine: IV<=100% sanity cap

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OI_PATH = ROOT + r"\datasets\derived\nifty_oi_surface.parquet"
SPOT_PATH = ROOT + r"\datasets\index_daily\nifty50.parquet"
STRANGLE_PATH = ROOT + r"\FINAL_STRATEGY_FORWARD_CHECK\04_Short_Strangle\strangle_trades.csv"
OUT_DIR = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\BROAD_RESEARCH_2036"


def bs_price(S, K, T, sigma, r, opt_type):
    sigma = np.maximum(sigma, 1e-6)
    T = np.maximum(T, 1e-6)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    if opt_type == "CE":
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    else:
        return K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)


def bs_vega(S, K, T, sigma, r):
    sigma = np.maximum(sigma, 1e-6)
    T = np.maximum(T, 1e-6)
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return S * norm.pdf(d1) * np.sqrt(T)


def implied_vol_vec(price, S, K, T, r, is_call, tol=1e-4, n_newton=50, n_bisect=60):
    """Fully vectorized IV solve: Newton-Raphson first, bisection fallback for stragglers.
    Returns array of IV (NaN where unsolvable / price below intrinsic)."""
    price = np.asarray(price, dtype=float)
    S = np.asarray(S, dtype=float)
    K = np.asarray(K, dtype=float)
    T = np.asarray(T, dtype=float)
    is_call = np.asarray(is_call, dtype=bool)

    intrinsic = np.where(is_call, np.maximum(S - K, 0.0), np.maximum(K - S, 0.0))
    valid = price > intrinsic + 1e-6

    def price_vec(sig):
        d1 = (np.log(S / K) + (r + 0.5 * sig**2) * T) / (sig * np.sqrt(T))
        d2 = d1 - sig * np.sqrt(T)
        call_p = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        put_p = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
        return np.where(is_call, call_p, put_p)

    def vega_vec(sig):
        d1 = (np.log(S / K) + (r + 0.5 * sig**2) * T) / (sig * np.sqrt(T))
        return S * norm.pdf(d1) * np.sqrt(T)

    sigma = np.full_like(price, 0.25)
    for _ in range(n_newton):
        p = price_vec(sigma)
        v = vega_vec(sigma)
        diff = p - price
        step = np.where(v > 1e-8, diff / np.where(v > 1e-8, v, 1.0), 0.0)
        sigma = np.clip(sigma - step, 0.001, 5.0)

    resid = np.abs(price_vec(sigma) - price)
    needs_bisect = valid & (resid > tol)

    lo = np.full_like(price, 0.001)
    hi = np.full_like(price, 5.0)
    plo = price_vec(lo) - price
    phi = price_vec(hi) - price
    bracket_ok = (plo * phi <= 0)
    for _ in range(n_bisect):
        mid = (lo + hi) / 2
        pm = price_vec(mid) - price
        go_hi = (plo * pm) < 0
        hi = np.where(needs_bisect & go_hi, mid, hi)
        lo = np.where(needs_bisect & ~go_hi, mid, lo)
        plo = np.where(needs_bisect & ~go_hi, pm, plo)
    bisect_sigma = (lo + hi) / 2
    sigma = np.where(needs_bisect & bracket_ok, bisect_sigma, sigma)

    out = np.where(valid & (bracket_ok | ~needs_bisect), sigma, np.nan)
    return out


def bs_gamma(S, K, T, sigma):
    sigma = np.maximum(sigma, 1e-6)
    T = np.maximum(T, 1e-6)
    d1 = (np.log(S / K) + (R + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return norm.pdf(d1) / (S * sigma * np.sqrt(T))


def bootstrap_ci(a, b, n=2000, stat=np.mean):
    diffs = np.empty(n)
    for i in range(n):
        sa = RNG.choice(a, size=len(a), replace=True)
        sb = RNG.choice(b, size=len(b), replace=True)
        diffs[i] = stat(sb) - stat(sa)
    return np.percentile(diffs, [2.5, 97.5]), diffs


def main():
    log = []

    def say(*a):
        s = " ".join(str(x) for x in a)
        print(s)
        log.append(s)

    oi = pd.read_parquet(OI_PATH)
    spot = pd.read_parquet(SPOT_PATH)
    # NOTE: these are IST-local 00:00 wall-clock stamps (not HF 18:30-UTC bars) -
    # tz_convert(None) would WRONGLY shift to the previous UTC day (the L1 landmine,
    # verified empirically: tz_convert(None) on '2016-01-04T00:00:00+05:30' -> '2016-01-03
    # 18:30'). Use tz_localize(None) to strip the tz label while keeping the IST wall date.
    spot["date"] = pd.to_datetime(spot["timestamp"]).dt.tz_localize(None).dt.normalize()
    spot = spot.sort_values("date").reset_index(drop=True)
    spot["prev_close"] = spot["close"].shift(1)
    spot["next_range_pct"] = (spot["high"].shift(-1) - spot["low"].shift(-1)) / spot["close"]
    spot_small = spot[["date", "close", "next_range_pct"]].rename(columns={"close": "spot_close"})

    say("[DATA] OI surface rows:", len(oi), "distinct trade_dates:", oi["trade_date"].nunique())

    oi = oi.merge(spot_small, left_on="trade_date", right_on="date", how="left")
    n_before = oi["trade_date"].nunique()
    oi = oi.dropna(subset=["spot_close"])
    n_after = oi["trade_date"].nunique()
    say(f"[DATA] spot join: {n_after}/{n_before} trade_dates matched to nifty50.parquet (expect ~400/402 per prior scan)")

    # drop same-day-expiry rows (gamma ill-defined / near-infinite at T->0) and non-positive OI
    oi = oi[(oi["dte"] > 0) & (oi["oi"] > 0) & (oi["close"] > 0)].copy()
    oi["T"] = oi["dte"] / 365.0
    say("[DATA] rows after dte>0 & oi>0 & close>0 filter:", len(oi))

    # IV back-solve (fully vectorized Newton-Raphson + bisection fallback)
    say("[COMPUTE] back-solving IV via vectorized Newton-Raphson/bisection...")
    S_arr = oi["spot_close"].to_numpy()
    K_arr = oi["strike"].to_numpy()
    T_arr = oi["T"].to_numpy()
    px_arr = oi["close"].to_numpy()
    is_call = (oi["option_type"].to_numpy() == "CE")
    oi["iv"] = implied_vol_vec(px_arr, S_arr, K_arr, T_arr, R, is_call)
    n_solved = oi["iv"].notna().sum()
    say(f"[COMPUTE] IV solved for {n_solved}/{len(oi)} rows ({n_solved/len(oi):.1%})")

    # firm landmine: IV<=100% sanity cap -> drop rows above cap (don't silently clip into the feature)
    n_over_cap = (oi["iv"] > IV_CAP).sum()
    oi = oi[(oi["iv"].notna()) & (oi["iv"] <= IV_CAP) & (oi["iv"] >= 0.02)].copy()
    say(f"[DATA] dropped {n_over_cap} rows with IV>{IV_CAP:.0%} sanity cap; usable rows: {len(oi)}")

    oi["gamma"] = bs_gamma(oi["spot_close"].to_numpy(), oi["strike"].to_numpy(), oi["T"].to_numpy(), oi["iv"].to_numpy())
    oi["gamma_oi"] = oi["gamma"] * oi["oi"]

    # per trade_date: sum call gamma*OI and put gamma*OI (scale by S^2 per spec; contract
    # multiplier omitted deliberately - a constant per-date scalar that does not affect
    # sign or within/cross-date rank ordering, documented simplification for a sign/rank test)
    g = oi.groupby(["trade_date", "option_type"])["gamma_oi"].sum().unstack(fill_value=0.0)
    g = g.rename(columns={"CE": "call_g", "PE": "put_g"})
    day = g.reset_index().merge(spot_small.rename(columns={"date": "trade_date"}), on="trade_date", how="left")
    day["S2"] = day["spot_close"] ** 2

    # Convention A (US-standard: dealers net long calls / short puts)
    day["gex_A"] = (day["call_g"] - day["put_g"]) * day["S2"]
    # Convention B (India-retail-short-both: dealers net short calls AND short puts)
    day["gex_B"] = -(day["call_g"] + day["put_g"]) * day["S2"]

    day = day.dropna(subset=["next_range_pct"]).sort_values("trade_date").reset_index(drop=True)
    say(f"[DATA] final day-level sample n={len(day)} (dates with usable GEX + next-day range)")

    results = {}
    for conv in ["gex_A", "gex_B"]:
        day[f"{conv}_q"] = pd.qcut(day[conv], 5, labels=False, duplicates="drop")
        q_stats = day.groupby(f"{conv}_q")[["next_range_pct", conv]].agg(["mean", "median", "count"])
        say(f"\n=== Convention {conv} — quintile stats (0=most negative/extreme-short-gamma bucket after sort) ===")
        say(q_stats.to_string())

        qlo = day[day[f"{conv}_q"] == 0]["next_range_pct"].to_numpy()
        qhi = day[day[f"{conv}_q"] == 4]["next_range_pct"].to_numpy()
        # theory: most-negative-GEX quintile (q0, since qcut sorts ascending on raw signed
        # value and gex_B is always negative-signed for B, ranking is by magnitude of
        # negativity for B and by sign for A) -> HIGHER realized range than most-positive (q4)
        mean_lo, mean_hi = qlo.mean(), qhi.mean()
        spread = mean_lo - mean_hi  # expect >0 if theory holds (q0=short-gamma=higher range)
        try:
            u_stat, p_mw = mannwhitneyu(qlo, qhi, alternative="two-sided")
        except ValueError:
            u_stat, p_mw = np.nan, np.nan
        ci, _ = bootstrap_ci(qhi, qlo)  # sb-sa = lo-hi mean diff distribution (b=lo,a=hi consistent with spread sign)
        say(f"q0(most-neg-GEX) mean next-day range={mean_lo:.4%} n={len(qlo)} | "
            f"q4(most-pos-GEX) mean={mean_hi:.4%} n={len(qhi)} | spread(q0-q4)={spread:.4%} | "
            f"Mann-Whitney p={p_mw:.4f} | bootstrap 95% CI on spread={ci}")
        results[conv] = dict(mean_lo=mean_lo, mean_hi=mean_hi, spread=spread, p_mw=p_mw, ci=ci.tolist(),
                              n_lo=len(qlo), n_hi=len(qhi))

    # ---- S-04 strangle P&L join ----
    strg = pd.read_csv(STRANGLE_PATH, parse_dates=["entry", "exp"])
    day_sorted = day[["trade_date", "gex_A", "gex_A_q", "gex_B", "gex_B_q"]].sort_values("trade_date")
    strg_sorted = strg.sort_values("entry")
    joined = pd.merge_asof(strg_sorted, day_sorted, left_on="entry", right_on="trade_date", direction="backward")
    n_matched = joined["trade_date"].notna().sum()
    say(f"\n[DATA] strangle trades: {len(strg)}, matched to a prior/contemporaneous GEX snapshot: {n_matched} "
        f"({n_matched/len(strg):.1%}) via asof-backward (PIT-safe)")
    joined_ok = joined.dropna(subset=["gex_A_q"])

    strangle_results = {}
    for conv in ["gex_A_q", "gex_B_q"]:
        pnl_stats = joined_ok.groupby(conv)[["strangle_managed", "strangle_hold"]].agg(["mean", "count"])
        say(f"\n=== S-04 strangle P&L (strangle_managed) by {conv} quintile ===")
        say(pnl_stats.to_string())
        lo = joined_ok[joined_ok[conv] == 0]["strangle_managed"].to_numpy()
        hi = joined_ok[joined_ok[conv] == 4]["strangle_managed"].to_numpy()
        # theory: negative-gamma bucket (q0) -> WORSE strangle P&L than positive-gamma bucket (q4)
        d = lo.mean() - hi.mean()
        try:
            u_stat, p_mw = mannwhitneyu(lo, hi, alternative="two-sided")
        except ValueError:
            p_mw = np.nan
        say(f"q0 mean managed P&L={lo.mean():.4%} n={len(lo)} | q4 mean={hi.mean():.4%} n={len(hi)} | "
            f"diff(q0-q4)={d:.4%} | Mann-Whitney p={p_mw:.4f}")
        strangle_results[conv] = dict(mean_lo=lo.mean(), mean_hi=hi.mean(), diff=d, p_mw=p_mw, n_lo=len(lo), n_hi=len(hi))

    # ---- Placebo: shuffle bucket labels, rebuild null distribution of extreme-quintile spread ----
    say("\n=== Placebo test: shuffle GEX-quintile labels across dates (2000 draws) ===")
    placebo_results = {}
    for conv in ["gex_A_q", "gex_B_q"]:
        obs_spread = results[conv.replace("_q", "")]["spread"]
        labels = day[conv].to_numpy().copy()
        rng_vals = day["next_range_pct"].to_numpy()
        null_spreads = np.empty(2000)
        for i in range(2000):
            shuf = RNG.permutation(labels)
            lo_mask, hi_mask = shuf == 0, shuf == 4
            null_spreads[i] = rng_vals[lo_mask].mean() - rng_vals[hi_mask].mean()
        pct = (null_spreads >= obs_spread).mean() if obs_spread >= 0 else (null_spreads <= obs_spread).mean()
        say(f"{conv}: observed spread={obs_spread:.4%} | placebo null mean={null_spreads.mean():.4%} "
            f"std={null_spreads.std():.4%} | one-sided p (shuffle as/more extreme)={pct:.4f}")
        placebo_results[conv] = dict(obs_spread=obs_spread, null_mean=null_spreads.mean(),
                                      null_std=null_spreads.std(), p_shuffle=pct)

    # dump everything to a text log for the memo
    with open(OUT_DIR + r"\h1_gex_cheaptest_log.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(log))

    say("\n[DONE] log written to", OUT_DIR + r"\h1_gex_cheaptest_log.txt")


if __name__ == "__main__":
    main()
