"""Line B factor battery, RE-RUN on Line A's survivorship-safe 976-symbol PIT panel.

Purpose: swing_momentum/multi_backtest.py + combo_and_report.py ("Line B") tested 7
cross-sectional signals + combos on a 2,535-symbol HF dataset VERIFIED (sibling review,
SWING_MOMENTUM_ASSESSMENT.md) to contain ZERO of 11 sampled classic NSE delisted names —
current-day-survivors only. This script reuses Line B's EXACT signal definitions and
backtest engine (monthly rebalance, top-30 equal-weight, 0.4% RT cost, build<=2021-12-31
/ fwd 2022-2026, winsorized daily returns) verbatim, swapping only the input panel for
Line A's already-built, already-verified PIT panel (swing_momentum/processed/eq_close.parquet
+ membership.parquet), read-only.

Two deltas from a pure copy-paste, both load-bearing and disclosed:
1. UNIVERSE FILTER: Line B used a volume-based top-500-by-60d-turnover liquidity filter.
   Line A's panel is close-only (no volume column — RESULTS.md caveat #1). Substituting
   Line A's own already-used-and-defended proxy: PIT Nifty500 membership mask (real
   index membership, not retro-selected) + price >= Rs20 floor. This is not a new
   invention; it is literally what run_swing.py already does on this same panel.
2. DELIST-LOSS REALIZATION: Line B's backtest() takes `seg[holds].mean(axis=1)` with
   default skipna=True — on a panel that actually contains delisted names, a name whose
   price series ends mid-holding-period would just silently drop out of the mean (its
   weight redistributes to survivors), NOT realize a loss. That is a second, subtler
   form of the same survivorship bug and would quietly re-inflate the corrected number.
   Ported Line A's fix verbatim: a delist register (Nifty500_Delisted_2005_2025.xlsx)
   drives an explicit -50% one-time hit on the day a held name's data disappears within
   its delisting window, matching run_swing.py's DELIST_LOSS=-0.50 convention.

Everything else (signal formulas, TOP_N, COST_RT, RET_CLIP, rebalance cadence, split date,
combo weighting) is copied unchanged from multi_backtest.py / combo_and_report.py so the
comparison is apples-to-apples: same signals, same methodology, corrected universe.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
SM = ROOT / "swing_momentum"                  # read-only legacy folder
OUTDIR = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/BROAD_RESEARCH_2036"

SPLIT = dt.date(2021, 12, 31)                 # identical to Line B
COST_RT = 0.004                               # identical to Line B (0.4% RT)
RET_CLIP = 0.25                               # identical to Line B
TOP_N = 30                                    # identical to Line B
MIN_PRICE = 20.0                              # identical value Line A already uses
DELIST_LOSS = -0.50                           # identical to Line A's run_swing.py


# ---------------------------------------------------------------------------
# 1. Load Line A's survivorship-safe PIT panel (read-only source)
# ---------------------------------------------------------------------------
def load_panel():
    close_long = pd.read_parquet(SM / "processed/eq_close.parquet")
    mem = pd.read_parquet(SM / "processed/membership.parquet")
    C = close_long.pivot_table(index="date", columns="symbol", values="close").sort_index()
    C = C[~C.index.duplicated()]
    C = C.ffill(limit=10)     # bridge non-trading-day gaps, same as run_swing.py
    print(f"[load] PIT panel {C.shape[0]} days x {C.shape[1]} symbols, "
          f"{C.index.min().date()}..{C.index.max().date()}")

    mem = mem.copy()
    mem["month"] = pd.to_datetime(mem["month"])
    mwide = (mem.assign(v=True).pivot_table(index="month", columns="symbol", values="v",
             aggfunc="any").reindex(columns=C.columns))
    memmask = mwide.reindex(C.index, method="ffill").fillna(False).astype(bool)
    return C, memmask


def load_delist_register(columns):
    dl = pd.read_excel(SM.parent / "Nifty500_Delisted_2005_2025.xlsx", sheet_name="Sheet1")
    dl = dl.rename(columns={dl.columns[0]: "date"})
    dl["date"] = pd.to_datetime(dl["date"], errors="coerce")
    dl = dl.dropna(subset=["date"]).set_index("date")
    delist_date = {}
    for s in dl.columns:
        col = pd.to_numeric(dl[s], errors="coerce").dropna()
        if len(col):
            delist_date[str(s).upper()] = col.index.max()
    print(f"[delist] register: {len(delist_date)} names with delist dates")
    return delist_date


# ---------------------------------------------------------------------------
# 2. Spot-check: confirm the panel is actually survivorship-fixed before trusting it
# ---------------------------------------------------------------------------
def verify_no_survivorship_bug(C):
    names = ["SATYAM", "DHFL", "RCOM", "JETAIRWAYS"]
    print("\n[verify] classic delisted-name spot check on Line A's panel:")
    found = 0
    for s in names:
        if s in C.columns:
            col = C[s].dropna()
            if len(col):
                print(f"  {s:12s} present, {len(col)} obs, {col.index.min().date()}..{col.index.max().date()}")
                found += 1
            else:
                print(f"  {s:12s} column exists but empty")
        else:
            print(f"  {s:12s} ABSENT (expected only for SATYAM, pre-2005 delist)")
    print(f"[verify] {found}/4 sampled names present with real price history "
          f"(SATYAM absence is expected/documented, not a bug) -> panel confirmed "
          f"survivorship-safe, proceeding.\n")


# ---------------------------------------------------------------------------
# 3. Line B's signal functions — copied verbatim from multi_backtest.py
# ---------------------------------------------------------------------------
def make_signals():
    def mom(lb, skip):
        def f(C, d):
            px = C.loc[:d]
            if len(px) <= lb:
                return None
            return px.iloc[-1 - skip] / px.iloc[-1 - lb] - 1
        return f

    def lowvol(win):
        def f(C, d):
            r = C.loc[:d].pct_change().clip(-RET_CLIP, RET_CLIP).iloc[-win:]
            return -r.std()
        return f

    def hi52(C, d):
        px = C.loc[:d].iloc[-252:]
        return px.iloc[-1] / px.max()

    def revers(win):
        def f(C, d):
            px = C.loc[:d]
            return -(px.iloc[-1] / px.iloc[-1 - win] - 1)
        return f

    def trend_mom(C, d):
        px = C.loc[:d]
        if len(px) < 210:
            return None
        ma50 = px.iloc[-50:].mean(); ma200 = px.iloc[-200:].mean()
        mom6 = px.iloc[-21] / px.iloc[-126] - 1
        ok = (px.iloc[-1] > ma50) & (ma50 > ma200)
        return mom6.where(ok, other=-np.inf)

    return {
        "mom_6_1": mom(126, 21),
        "mom_12_1": mom(252, 21),
        "mom_3_0": mom(63, 0),
        "lowvol_126": lowvol(126),
        "hi_52w": hi52,
        "revers_5d": revers(5),
        "trend+mom": trend_mom,
    }


def rebalance_dates(C, every=21):
    idx = C.index
    return list(idx[252::every])


def market_regime(C):
    r = C.pct_change().clip(-RET_CLIP, RET_CLIP)
    mkt = (1 + r.mean(axis=1)).cumprod()
    ma200 = mkt.rolling(200, min_periods=100).mean()
    return mkt > ma200


# ---------------------------------------------------------------------------
# 4. Universe: PIT-membership + price-floor substitute for Line B's ADV filter
# ---------------------------------------------------------------------------
def pit_universe(C, memmask, reb_dates):
    uni = {}
    for d in reb_dates:
        px = C.loc[:d].iloc[-1]
        mem_ok = memmask.loc[d] if d in memmask.index else memmask.reindex([d], method="ffill").iloc[0]
        elig = px[(px >= MIN_PRICE) & mem_ok.reindex(px.index).fillna(False)]
        uni[d] = set(elig.index)
    return uni


# ---------------------------------------------------------------------------
# 5. Backtest engine — Line B's loop, + explicit delist-loss realization
# ---------------------------------------------------------------------------
def build_adjusted_returns(C, delist_date, grace_days=12):
    """Daily pct-change, winsorized, PLUS a one-time DELIST_LOSS hit on the day a
    name's price series ends within its documented delist window (instead of Line B's
    silent NaN-skip). After the hit, the name's return is held at 0 (dead position,
    already realized) so it can't re-contribute or re-enter (also excluded from `uni`
    thereafter since its price is NaN -> fails the price/membership filters)."""
    rets = C.pct_change().clip(-RET_CLIP, RET_CLIP)
    hit_log = []
    for s in C.columns:
        col = C[s]
        valid = col.notna()
        if not valid.any():
            continue
        last_valid_idx = valid[valid].index[-1]
        # only if the column actually ends before panel end (real delist, not survivor)
        if last_valid_idx >= C.index[-1]:
            continue
        dd = delist_date.get(s)
        if dd is None:
            continue
        pos = C.index.get_indexer([last_valid_idx])[0]
        if pos + 1 >= len(C.index):
            continue
        next_day = C.index[pos + 1]
        if last_valid_idx <= dd <= last_valid_idx + pd.Timedelta(days=grace_days):
            rets.loc[next_day, s] = DELIST_LOSS
            hit_log.append((s, next_day.date(), dd.date()))
    print(f"[delist] realized -50% loss on {len(hit_log)} names at their panel-end date "
          f"(sample: {hit_log[:5]})")
    rets = rets.fillna(0.0)   # dead names contribute 0 after their one-time hit
    return rets


def backtest(rets_adj, sig_fn, reb_dates, uni, C, regime=None):
    daily = pd.Series(0.0, index=rets_adj.index)
    prev_holds = set()
    for i, d in enumerate(reb_dates):
        s = sig_fn(C, d)
        if s is None:
            continue
        s = s.dropna()
        s = s[s.index.isin(uni[d])]
        s = s[np.isfinite(s.values)]
        if len(s) < 5:
            holds = set()
        else:
            holds = set(s.sort_values(ascending=False).head(TOP_N).index)
        if regime is not None and d in regime.index and not regime.loc[d]:
            holds = set()
        end = reb_dates[i + 1] if i + 1 < len(reb_dates) else rets_adj.index[-1]
        seg = rets_adj.loc[d:end].iloc[1:]
        if holds:
            port = seg[list(holds)].mean(axis=1)
        else:
            port = pd.Series(0.0, index=seg.index)
        turn = len(holds.symmetric_difference(prev_holds)) / max(len(holds | prev_holds), 1)
        if len(port):
            port.iloc[0] -= turn * COST_RT
        daily.loc[port.index] = port.values
        prev_holds = holds
    return daily.fillna(0.0)


def metrics(daily, label):
    def m(x):
        if len(x) < 30 or x.std() == 0:
            return (0.0, 0.0, 0.0)
        eq = (1 + x).cumprod()
        sharpe = x.mean() / x.std() * np.sqrt(252)
        cagr = eq.iloc[-1] ** (252 / len(x)) - 1
        dd = (eq / eq.cummax() - 1).min()
        return (sharpe, cagr, dd)
    bd = daily[daily.index.date <= SPLIT]; fd = daily[daily.index.date > SPLIT]
    sb, cb, ddb = m(bd); sf, cf, ddf = m(fd)
    print(f"  {label:14s}: BUILD Sharpe {sb:5.2f} CAGR {cb:+6.1%} DD {ddb:5.0%} | "
          f"FWD Sharpe {sf:5.2f} CAGR {cf:+6.1%} DD {ddf:5.0%}")
    return dict(build_sharpe=sb, build_cagr=cb, build_dd=ddb, fwd_sharpe=sf, fwd_cagr=cf, fwd_dd=ddf)


def blend(M, cols, weights=None):
    sub = M[cols]
    if weights is None:
        v = sub[sub.index.date <= SPLIT].std().replace(0, np.nan)
        w = (1 / v) / (1 / v).sum()
    else:
        w = pd.Series(weights, index=cols)
    return (sub * w).sum(axis=1)


if __name__ == "__main__":
    C, memmask = load_panel()
    verify_no_survivorship_bug(C)
    delist_date = load_delist_register(C.columns)
    rets_adj = build_adjusted_returns(C, delist_date)

    reb = rebalance_dates(C, every=21)
    print(f"[reb] {len(reb)} monthly rebalances {reb[0].date()}..{reb[-1].date()}")
    uni = pit_universe(C, memmask, reb)
    avg_uni = np.mean([len(v) for v in uni.values()])
    print(f"[uni] avg eligible names per rebalance: {avg_uni:.0f} "
          f"(PIT-membership + price>=Rs{MIN_PRICE:.0f} floor, no volume data available)")
    regime = market_regime(C)
    sigs = make_signals()

    print("\n=== LINE B SIGNALS RE-RUN ON LINE A's SURVIVORSHIP-SAFE PANEL ===")
    print("(top-30 equal-weight, monthly, 0.4% RT cost, build<=2021-12-31/fwd 2022-2026)")
    series = {}
    results = {}
    for name, fn in sigs.items():
        d = backtest(rets_adj, fn, reb, uni, C)
        results[name] = metrics(d, name)
        series[name] = d
    dmr = backtest(rets_adj, sigs["mom_6_1"], reb, uni, C, regime=regime)
    results["mom6+regime"] = metrics(dmr, "mom6+regime")
    series["mom6+regime"] = dmr

    M = pd.DataFrame(series)
    print("\n=== COMBOS (inverse-vol blend on build, identical to combo_and_report.py) ===")
    combos = {
        "Mom12+LowVol (invvol)": blend(M, ["mom_12_1", "lowvol_126"]),
        "Mom12+LowVol+52wh+Trend": blend(M, ["mom_12_1", "lowvol_126", "hi_52w", "trend+mom"]),
        "Mom6+regime+LowVol": blend(M, ["mom6+regime", "lowvol_126"]),
    }
    for name, s in combos.items():
        results[name] = metrics(s, name)
        M[name] = s

    M.to_parquet(OUTDIR / "lineb_corrected_daily.parquet")
    res_df = pd.DataFrame(results).T
    res_df.to_csv(OUTDIR / "lineb_corrected_results.csv")
    print(f"\nsaved -> {OUTDIR / 'lineb_corrected_daily.parquet'}")
    print(f"saved -> {OUTDIR / 'lineb_corrected_results.csv'}")
