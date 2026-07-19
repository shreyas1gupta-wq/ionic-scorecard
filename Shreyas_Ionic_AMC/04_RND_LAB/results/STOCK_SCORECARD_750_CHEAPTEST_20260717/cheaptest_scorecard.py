"""
STOCK_SCORECARD_750 — Gate-3 cheap-test (Quality + Value 2-pillar stand-in).
Owner: Arjun Rao (Head of Quant). Date: 2026-07-17.

WHAT THIS IS: the cheapest falsification of "does a Quality+Value composite score
have any real cross-sectional forward-return predictive power on the Nifty-750?"
Tests ONLY 2 of the planned 8 pillars (Quality = ROE+ROCE, Value = P/E cheap=high),
combined as a simple equal average of sector-neutral percentile ranks. This is a
STAND-IN for "the framework", NOT the framework. Pre-registered kill criteria in
ideas/20260717_stock_scorecard_750_forward_return_predictor.md.

DECISION RULE (pre-registered, NOT redesigned here):
  C1 primary  : quintile spread monotonic AND positive (top beats bottom)
  C2 hard gate: real spread must beat a shuffled-score placebo null  -> KILL if not
  C3 power    : do NOT hard-kill on t-stat/DSR alone (small independent-window count)

Landmines handled (see CLAUDE.md / guards.py):
  * PIT: fundamentals filtered available_date <= formation (G.assert_pit)
  * P/E numerator = Close (split-adj, closest to true traded px; matches Task-5);
    forward returns = Adj Close (total-return correct). Residual split noise only
    WEAKENS real signal vs placebo (conservative) -> cannot manufacture a false pos.
  * Overlapping 12M windows -> Newey-West t-stat (lag 11); t-stat is NOT a kill gate.
  * Universe = CURRENT Nifty-750 membership => survivor-biased BASELINE. Placebo
    shuffles within the same survivor set, so the real-vs-placebo gate is unaffected;
    absolute quintile returns are inflated & NOT tradeable. Gate-4 must use PIT
    membership (NIFTY500_TICKER_2005_2025_Final.xlsx).
"""
import os, sys, json, glob, shutil, datetime
os.environ["PYTHONIOENCODING"] = "utf-8"
os.environ["PYTHONUNBUFFERED"] = "1"
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
AR = os.path.join(ROOT, "ALPHA_RANKER", "data")
LIB = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "lib")
OUT = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "results", "STOCK_SCORECARD_750_CHEAPTEST_20260717")
sys.path.insert(0, LIB)
import guards as G  # landmine guards (assert_pit, safe_merge)

SEED = 20260717
N_PLACEBO = 200
N_QUANTILES = 5
NEEDED = ["net profit", "equity capital", "reserves", "borrowings", "borrowing",
          "operating profit", "eps in rs"]

rng = np.random.default_rng(SEED)

# ----------------------------------------------------------------------------- #
# LOAD
# ----------------------------------------------------------------------------- #
def load_universe():
    syms = pd.read_csv(os.path.join(AR, "universe", "symbols_750.txt"),
                       header=None, names=["symbol"])
    sm = pd.read_parquet(os.path.join(AR, "universe", "sector_map.parquet"))
    sm = sm.rename(columns={"macro_sector": "sector"})
    # case-normalise sector (real data has "Consumer durables" vs "Consumer Durables")
    sm["sector"] = sm["sector"].str.strip().str.lower()
    sm = sm.drop_duplicates(subset=["symbol"], keep="first")
    u = G.safe_merge(syms, sm[["symbol", "sector"]], tolerate=0.01, on="symbol", how="left")
    u["sector"] = u["sector"].fillna("__unknown__")
    return u

def load_prices(symbols):
    """symbol -> DataFrame indexed by date with columns close, adj_close."""
    px = {}
    for s in symbols:
        p = os.path.join(AR, "prices", s + ".parquet")
        if not os.path.exists(p):
            continue
        d = pd.read_parquet(p, columns=["Close", "Adj Close"]).sort_index()
        d = d[~d.index.duplicated(keep="last")]
        d.columns = ["close", "adj_close"]
        if len(d):
            px[s] = d
    return px

def load_fundamentals(symbols):
    f = pd.read_parquet(os.path.join(AR, "fundamentals", "MASTER_fundamentals_pit.parquet"),
                        columns=["nse_symbol", "fiscal_year", "metric_norm", "value", "available_date"])
    f = f.rename(columns={"nse_symbol": "symbol"})
    f = f[f["symbol"].isin(symbols) & f["metric_norm"].isin(NEEDED)].copy()
    f["available_date"] = pd.to_datetime(f["available_date"])
    f = f.drop_duplicates(subset=["symbol", "metric_norm", "fiscal_year"], keep="last")
    return f

# ----------------------------------------------------------------------------- #
# RANK UTIL (mirrors Task-2 rank_utils.percentile_rank: sector-neutral + min_group fallback)
# ----------------------------------------------------------------------------- #
def percentile_rank(df, col, group_col="sector", ascending=True, min_group_size=5):
    series = df[col] if ascending else -df[col]
    grp_sizes = df.groupby(group_col)[col].transform("count")
    within = series.groupby(df[group_col]).rank(pct=True) * 100
    universe = series.rank(pct=True) * 100
    return within.where(grp_sizes >= min_group_size, universe)

def price_asof(px, s, dt, col, tol_days):
    if s not in px:
        return np.nan
    ser = px[s][col]
    sub = ser[ser.index <= dt]
    if len(sub) == 0:
        return np.nan
    if (dt - sub.index[-1]).days > tol_days:
        return np.nan
    return float(sub.iloc[-1])

# ----------------------------------------------------------------------------- #
# SCORE BUILD (Quality=ROE+ROCE, Value=P/E) — Task-5 derived-ratio logic, PIT-safe
# ----------------------------------------------------------------------------- #
def build_panel(form_date, fund, uni, px, fwd_months, buy_tol=10, sell_tol=20):
    fd = pd.Timestamp(form_date)
    pit = fund[fund["available_date"] <= fd].copy()
    if pit.empty:
        return pd.DataFrame()
    # explicit lookahead guard: action_date = formation date for every PIT row
    pit_chk = pit.assign(action_date=fd)
    G.assert_pit(pit_chk, avail_col="available_date", act_col="action_date")
    # latest available fiscal_year per (symbol, metric)
    pit = pit.sort_values("fiscal_year").groupby(["symbol", "metric_norm"]).tail(1)
    wide = pit.pivot_table(index="symbol", columns="metric_norm", values="value", aggfunc="last")
    for c in NEEDED:
        if c not in wide.columns:
            wide[c] = np.nan
    # --- Task-5 formulas ---
    wide["equity"] = wide["equity capital"] + wide["reserves"]
    wide.loc[wide["equity"] <= 0, "equity"] = np.nan            # negative equity -> exclude, don't fabricate
    tot_borrow = wide["borrowings"].fillna(wide["borrowing"])
    ce = wide["equity"] + tot_borrow
    ce = ce.where(ce > 0)
    wide["roe"] = wide["net profit"] / wide["equity"]
    wide["roce"] = wide["operating profit"] / ce
    eps = wide["eps in rs"].replace(0, np.nan)
    wide = wide.reset_index()
    # price at formation (Close = split-adj, closest to true traded px)
    wide["px_form_close"] = [price_asof(px, s, fd, "close", buy_tol) for s in wide["symbol"]]
    wide["pe"] = wide["px_form_close"] / eps.values
    wide.loc[wide["pe"] <= 0, "pe"] = np.nan                    # loss-makers excluded from value rank
    # forward return (Adj Close = total-return correct)
    wide["px_buy_adj"] = [price_asof(px, s, fd, "adj_close", buy_tol) for s in wide["symbol"]]
    sell_dt = fd + pd.DateOffset(months=fwd_months)
    wide["px_sell_adj"] = [price_asof(px, s, sell_dt, "adj_close", sell_tol) for s in wide["symbol"]]
    wide["fwd_ret"] = wide["px_sell_adj"] / wide["px_buy_adj"] - 1.0
    # keep only fully-scoreable rows WITH a forward return
    m = wide["roe"].notna() & wide["roce"].notna() & wide["pe"].notna() & wide["fwd_ret"].notna()
    p = wide.loc[m, ["symbol", "roe", "roce", "pe", "fwd_ret"]].copy()
    p = G.safe_merge(p, uni[["symbol", "sector"]], tolerate=0.01, on="symbol", how="left")
    if len(p) < N_QUANTILES * 5:      # need a usable cross-section
        return pd.DataFrame()
    # sector-neutral percentile ranks
    p["q_roe"] = percentile_rank(p, "roe", ascending=True)
    p["q_roce"] = percentile_rank(p, "roce", ascending=True)
    p["quality"] = p[["q_roe", "q_roce"]].mean(axis=1)
    p["value"] = percentile_rank(p, "pe", ascending=False)      # cheap (low PE) -> high score
    p["combined"] = p[["quality", "value"]].mean(axis=1)        # simple equal-weight avg of 2 pillars
    p["form_date"] = fd
    return p

# ----------------------------------------------------------------------------- #
# QUINTILE SPREAD
# ----------------------------------------------------------------------------- #
def quintile_ladder(scores, rets, nq=N_QUANTILES):
    """Return (list of nq mean fwd-returns Q1..Q5, spread=Q5-Q1)."""
    r = pd.qcut(pd.Series(scores).rank(method="first"), nq, labels=False)
    df = pd.DataFrame({"q": r, "ret": np.asarray(rets)})
    means = df.groupby("q")["ret"].mean()
    ladder = [float(means.get(i, np.nan)) for i in range(nq)]
    return ladder, ladder[-1] - ladder[0]

def newey_west_t(x, lag):
    x = np.asarray(x, float); n = len(x)
    if n < 3:
        return float("nan")
    mu = x.mean(); e = x - mu
    var = (e @ e) / n
    for l in range(1, min(lag, n - 1) + 1):
        w = 1 - l / (lag + 1)
        var += 2 * w * (e[l:] @ e[:-l]) / n
    se = np.sqrt(var / n)
    return float(mu / se) if se > 0 else float("nan")

# ============================================================================= #
# RUN
# ============================================================================= #
print("Loading universe / prices / fundamentals ...", flush=True)
uni = load_universe()
symbols = uni["symbol"].tolist()
px = load_prices(symbols)
fund = load_fundamentals(symbols)
print(f"  universe={len(uni)}  priced={len(px)}  fund_rows={len(fund)}  fund_syms={fund['symbol'].nunique()}", flush=True)

DATA_MAX = max(d.index.max() for d in px.values())
DATA_MIN = min(d.index.min() for d in px.values())
print(f"  price span {DATA_MIN.date()} -> {DATA_MAX.date()}", flush=True)

# ---- PRIMARY: monthly rolling 12M ----
form_months = pd.date_range("2021-08-31", "2025-06-30", freq="ME")
print(f"\nPRIMARY 12M: {len(form_months)} monthly formations "
      f"{form_months[0].date()}..{form_months[-1].date()}", flush=True)

panels = {}
per_month = []
for fm in form_months:
    p = build_panel(fm, fund, uni, px, fwd_months=12)
    if p.empty:
        continue
    ladder, spread = quintile_ladder(p["combined"].values, p["fwd_ret"].values)
    med = pd.DataFrame({"q": pd.qcut(p["combined"].rank(method="first"), N_QUANTILES, labels=False),
                        "ret": p["fwd_ret"].values}).groupby("q")["ret"].median()
    med_ladder = [float(med.get(i, np.nan)) for i in range(N_QUANTILES)]
    panels[fm] = p[["combined", "fwd_ret"]].reset_index(drop=True)
    per_month.append(dict(form=str(fm.date()), n=int(len(p)), ladder=ladder, spread=float(spread),
                          med_spread=float(med_ladder[-1] - med_ladder[0])))
    print(f"  {fm.date()}  n={len(p):4d}  Q1..Q5="
          f"{['%.3f'%x for x in ladder]}  spread={spread:+.4f}", flush=True)

spreads = np.array([m["spread"] for m in per_month])
med_spreads = np.array([m["med_spread"] for m in per_month])
ladders = np.array([m["ladder"] for m in per_month])
mean_ladder = ladders.mean(axis=0)
mean_spread = float(spreads.mean())
mean_med_spread = float(med_spreads.mean())
naive_t = float(spreads.mean() / (spreads.std(ddof=1) / np.sqrt(len(spreads))))
nw_t = newey_west_t(spreads, lag=11)
# monotonicity: Spearman between quintile index and mean-ladder return
from scipy.stats import spearmanr
mono_rho, _ = spearmanr(np.arange(N_QUANTILES), mean_ladder)
n_pos_months = int((spreads > 0).sum())

print(f"\n=== PRIMARY 12M AGGREGATE (n_months={len(spreads)}) ===")
print(f"  mean quintile ladder Q1..Q5: {['%.4f'%x for x in mean_ladder]}")
print(f"  mean spread (Q5-Q1)  = {mean_spread:+.4f}  ({mean_spread*100:+.2f}pp, gross)")
print(f"  mean MEDIAN spread   = {mean_med_spread:+.4f}  (outlier-robust)")
print(f"  months spread>0      = {n_pos_months}/{len(spreads)}")
print(f"  monotonicity Spearman(qidx,ret) = {mono_rho:+.3f}")
print(f"  naive t-stat = {naive_t:.2f}   Newey-West(11) t-stat = {nw_t:.2f}")
print(f"  effective independent 12M windows ~ {len(spreads)/12:.1f}")

# ---- PLACEBO (hard gate): shuffle scores within each month ----
print(f"\nPLACEBO: {N_PLACEBO} shuffles (seed {SEED}) ...", flush=True)
null_mean_spreads = np.empty(N_PLACEBO)
for i in range(N_PLACEBO):
    sp = []
    for fm, pan in panels.items():
        shuffled = rng.permutation(pan["combined"].values)
        _, s = quintile_ladder(shuffled, pan["fwd_ret"].values)
        sp.append(s)
    null_mean_spreads[i] = np.mean(sp)
placebo_pctile = float((null_mean_spreads < mean_spread).mean() * 100)
placebo_p_onesided = float((null_mean_spreads >= mean_spread).mean())
print(f"  placebo null mean-spread: mean={null_mean_spreads.mean():+.4f} "
      f"sd={null_mean_spreads.std():.4f} "
      f"[p5={np.percentile(null_mean_spreads,5):+.4f}, p95={np.percentile(null_mean_spreads,95):+.4f}]")
print(f"  REAL mean spread {mean_spread:+.4f} is at placebo percentile {placebo_pctile:.1f} "
      f"(one-sided p={placebo_p_onesided:.4f})")

# ---- SECONDARY: 3Y (36M) context, few overlapping windows ----
print(f"\nSECONDARY 36M CONTEXT (overlapping windows; NOT the primary read):", flush=True)
sec_dates = ["2021-12-31", "2022-06-30", "2022-12-31", "2023-06-30"]
sec_rows = []
sec_panels = {}
for d in sec_dates:
    p = build_panel(d, fund, uni, px, fwd_months=36, sell_tol=20)
    if p.empty:
        print(f"  {d}: no panel"); continue
    ladder, spread = quintile_ladder(p["combined"].values, p["fwd_ret"].values)
    sec_panels[d] = p[["combined", "fwd_ret"]].reset_index(drop=True)
    sec_rows.append(dict(form=d, n=int(len(p)), ladder=ladder, spread=float(spread)))
    print(f"  {d}  n={len(p):4d}  Q1..Q5={['%.3f'%x for x in ladder]}  spread(3Y)={spread:+.4f}")
sec_mean_spread = float(np.mean([r["spread"] for r in sec_rows])) if sec_rows else float("nan")
# placebo for 3Y
sec_placebo_pctile = float("nan")
if sec_panels:
    null3 = np.empty(N_PLACEBO)
    for i in range(N_PLACEBO):
        sp = []
        for d, pan in sec_panels.items():
            shuffled = rng.permutation(pan["combined"].values)
            _, s = quintile_ladder(shuffled, pan["fwd_ret"].values)
            sp.append(s)
        null3[i] = np.mean(sp)
    sec_placebo_pctile = float((null3 < sec_mean_spread).mean() * 100)
    print(f"  3Y mean spread {sec_mean_spread:+.4f} at placebo percentile {sec_placebo_pctile:.1f}")

# ---- concentration / degenerate sanity (no daily curve, so manual) ----
# does dropping the single best fwd_ret in each quintile flip the primary spread sign?
robust_spreads = []
for fm, pan in panels.items():
    q = pd.qcut(pan["combined"].rank(method="first"), N_QUANTILES, labels=False)
    dd = pd.DataFrame({"q": q, "ret": pan["fwd_ret"].values})
    trimmed = dd.groupby("q")["ret"].apply(lambda s: s.sort_values()[:-1].mean() if len(s) > 1 else s.mean())
    robust_spreads.append(float(trimmed.iloc[-1] - trimmed.iloc[0]))
mean_spread_trim1 = float(np.mean(robust_spreads))
print(f"\nCONCENTRATION: mean spread after dropping top-1 return per quintile per month = "
      f"{mean_spread_trim1:+.4f} (sign {'HOLDS' if np.sign(mean_spread_trim1)==np.sign(mean_spread) else 'FLIPS'})")

# ---- REGIME-CONCENTRATION check (my IC-1 lesson: is it edge or regime beta?) ----
fm_dates = pd.to_datetime([m["form"] for m in per_month])
regimes = {
    "A_2021-08..2022-05_pre":   (fm_dates >= "2021-08-01") & (fm_dates <= "2022-05-31"),
    "B_2022-06..2023-09_meltup":(fm_dates >= "2022-06-01") & (fm_dates <= "2023-09-30"),
    "C_2023-10..2025-06_recent":(fm_dates >= "2023-10-01") & (fm_dates <= "2025-06-30"),
}
regime_stats = {}
print("\nREGIME SPLIT (primary 12M spreads):")
for name, mask in regimes.items():
    s = spreads[mask.values if hasattr(mask, 'values') else mask]
    regime_stats[name] = dict(n_months=int(len(s)), mean_spread=float(s.mean()),
                              pct_positive=float((s > 0).mean()*100), min=float(s.min()), max=float(s.max()))
    print(f"  {name:32s} n={len(s):2d}  mean_spread={s.mean():+.4f}  "
          f"pos={100*(s>0).mean():4.0f}%  range[{s.min():+.3f},{s.max():+.3f}]")
# spread with the melt-up regime EXCLUDED
mask_ex = ~regimes["B_2022-06..2023-09_meltup"]
spread_ex_meltup = float(spreads[mask_ex.values if hasattr(mask_ex,'values') else mask_ex].mean())
nw_t_ex = newey_west_t(spreads[mask_ex.values if hasattr(mask_ex,'values') else mask_ex], lag=11)
print(f"  >> mean spread EXCLUDING melt-up regime B = {spread_ex_meltup:+.4f} "
      f"(NW-t={nw_t_ex:.2f})  vs full-sample {mean_spread:+.4f}")

# ============================================================================= #
# SAVE
# ============================================================================= #
config = {
    "test": "STOCK_SCORECARD_750 Gate-3 cheap-test (Quality+Value 2-pillar stand-in)",
    "owner": "Arjun Rao (quant-head)", "date": "2026-07-17", "seed": SEED,
    "pillars_tested": {"quality": "avg(sector-neutral pctile ROE, ROCE)",
                       "value": "sector-neutral pctile of P/E (cheap=high)",
                       "combined": "equal-weight avg(quality, value)"},
    "note": "STAND-IN for the 8-pillar framework, NOT the framework itself.",
    "quantiles": N_QUANTILES, "n_placebo": N_PLACEBO,
    "primary": {"horizon_months": 12, "formation": "month-end 2021-08-31..2025-06-30",
                "sector_neutral": True, "min_group_size": 5,
                "pe_price_col": "Close (split-adj)", "return_col": "Adj Close",
                "costs": "NONE (gross; Gate-3 predictive-power read)"},
    "secondary": {"horizon_months": 36, "formation": sec_dates,
                  "caveat": "windows overlap heavily; context only, not primary stat read"},
    "data_snapshot": {
        "universe_file": "ALPHA_RANKER/data/universe/symbols_750.txt",
        "universe_n": int(len(uni)),
        "priced_symbols": int(len(px)),
        "price_span": [str(DATA_MIN.date()), str(DATA_MAX.date())],
        "fundamentals_file": "ALPHA_RANKER/data/fundamentals/MASTER_fundamentals_pit.parquet",
        "fund_rows_universe_needed_metrics": int(len(fund)),
        "fund_symbols_covered": int(fund["symbol"].nunique()),
        "sector_file": "ALPHA_RANKER/data/universe/sector_map.parquet",
    },
    "known_limitations": [
        "Universe = CURRENT Nifty-750 membership -> survivor-biased BASELINE (absolute "
        "quintile returns inflated, NOT tradeable). Placebo shuffles within same survivor "
        "set so the real-vs-placebo DECISION is unaffected. Gate-4 must use PIT membership.",
        "P/E numerator = Close (split-adj not raw); residual split mis-scaling adds NOISE "
        "to value rank -> conservative (weakens real vs placebo), cannot inflate.",
        "12M windows overlap 11/12 -> naive t inflated; Newey-West(11) reported; t NOT a kill gate.",
        "Gross of costs (Gate-3). Gate-4 must beat cap+turnover-matched random benchmark (D-029).",
        "2 of 8 pillars only; blend/weights/regime-tilt/DCF entirely untested here.",
    ],
}
metrics = {
    "primary_12m": {
        "n_formation_months": int(len(spreads)),
        "mean_quintile_ladder_Q1_Q5": [float(x) for x in mean_ladder],
        "mean_spread_Q5_minus_Q1": mean_spread,
        "mean_spread_pp": mean_spread * 100,
        "mean_median_spread": mean_med_spread,
        "mean_spread_drop_top1_per_quintile": mean_spread_trim1,
        "months_spread_positive": n_pos_months,
        "monotonicity_spearman": float(mono_rho),
        "naive_t": naive_t, "newey_west_t_lag11": nw_t,
        "eff_independent_windows_approx": len(spreads) / 12,
        "placebo_percentile": placebo_pctile,
        "placebo_one_sided_p": placebo_p_onesided,
        "placebo_null_mean": float(null_mean_spreads.mean()),
        "placebo_null_sd": float(null_mean_spreads.std()),
    },
    "secondary_36m": {
        "rows": sec_rows,
        "mean_spread_3y": sec_mean_spread,
        "placebo_percentile": sec_placebo_pctile,
    },
    "regime_split_primary_12m": regime_stats,
    "primary_spread_excluding_meltup": spread_ex_meltup,
    "primary_nw_t_excluding_meltup": nw_t_ex,
    "per_month_primary": per_month,
    "verdict_inputs": {
        "C1_monotonic_and_positive": bool(mono_rho > 0 and mean_spread > 0),
        "C2_beats_placebo_pctile": placebo_pctile,
        "C3_note": "t-stat/DSR not a kill; see writeup",
    },
}
with open(os.path.join(OUT, "config.json"), "w") as fh:
    json.dump(config, fh, indent=2)
with open(os.path.join(OUT, "metrics.json"), "w") as fh:
    json.dump(metrics, fh, indent=2)
print(f"\nSaved config.json + metrics.json to:\n  {OUT}")
print("DONE.")
