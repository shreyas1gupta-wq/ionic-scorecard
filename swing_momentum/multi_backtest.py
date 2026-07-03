"""Multi-strategy EQUITY swing/positional backtest harness (Indian daily data).

Loads the HF daily parquet (IST-date fixed), builds a point-in-time LIQUIDITY universe,
and backtests a battery of long-only cross-sectional strategies with realistic costs.
Build (<=2021-12-31) vs forward (2022-01 -> 2026-01). Reports CAGR/Sharpe/MaxDD/turnover
+ a strategy correlation matrix. Split-adjustment caveat handled by winsorizing daily rets.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
DAY = ROOT / "swing_momentum/data/hf_stock_minute/day/train-00000.parquet"
SPLIT = dt.date(2021, 12, 31)                 # build/forward boundary
COST_RT = 0.004                               # 0.4% round-trip (STT+brokerage+slippage, mid/small)
RET_CLIP = 0.25                               # winsorize daily ret (neutralize unadjusted splits)
TOP_N = 30                                    # portfolio size
LIQ_N = 500                                   # liquid universe size
MIN_PRICE = 20.0


def load_wide():
    print("[load] reading daily parquet...")
    df = pq.read_table(DAY).to_pandas()
    df["date"] = pd.to_datetime(df["timestamp"]).dt.tz_convert("Asia/Kolkata").dt.normalize().dt.tz_localize(None)
    df = df[df["close"] > 0]
    C = df.pivot_table("close", "date", "symbol")
    V = df.pivot_table("volume", "date", "symbol")
    C = C.sort_index()
    V = V.reindex(C.index)
    print(f"[load] close matrix {C.shape[0]} days x {C.shape[1]} symbols, {C.index.min().date()}..{C.index.max().date()}")
    return C, V


def diagnostics(C):
    r = C.pct_change()
    big = (r.abs() > 0.40).sum().sum()
    tot = r.notna().sum().sum()
    print(f"[diag] daily |ret|>40% = {big:,} of {tot:,} ({big/tot:.2%}) -> "
          f"{'UNADJUSTED (splits present); winsorizing' if big/tot > 0.001 else 'looks adjusted'}")


def liquid_universe(C, V, reb_dates):
    """For each rebalance date, the top-LIQ_N symbols by trailing 60d median turnover."""
    turn = (C * V).rolling(60, min_periods=30).median()
    uni = {}
    for d in reb_dates:
        row = turn.loc[:d].iloc[-1] if d in turn.index else turn.loc[:d].iloc[-1]
        elig = row.dropna()
        px = C.loc[:d].iloc[-1]
        elig = elig[(px.reindex(elig.index) >= MIN_PRICE)]
        uni[d] = set(elig.sort_values(ascending=False).head(LIQ_N).index)
    return uni


def rebalance_dates(C, every=21):
    idx = C.index
    return list(idx[252::every])          # start after 1y history, every ~month


# ---- strategy signal functions: return a Series (symbol->score) at date d; higher=better ----
def sig_mom_6_1(C, d):
    px = C.loc[:d]
    return px.iloc[-1] / px.iloc[-126] - 1 if len(px) > 126 else None, px.iloc[-1] / px.iloc[-21] - 1


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
            return -r.std()          # higher score = lower vol
        return f

    def hi52(C, d):
        px = C.loc[:d].iloc[-252:]
        return px.iloc[-1] / px.max()

    def revers(win):
        def f(C, d):
            px = C.loc[:d]
            return -(px.iloc[-1] / px.iloc[-1 - win] - 1)   # short-term losers score high
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


def backtest(C, V, sig_fn, reb_dates, uni, regime=None):
    """Long-only equal-weight top-N, rebalance monthly. Returns daily net return series."""
    rets = C.pct_change().clip(-RET_CLIP, RET_CLIP)
    daily = pd.Series(0.0, index=C.index)
    prev_holds = set()
    hold_by_day = {}
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
        # regime gate: if regime series says risk-off at d, go cash
        if regime is not None and d in regime.index and not regime.loc[d]:
            holds = set()
        end = reb_dates[i + 1] if i + 1 < len(reb_dates) else C.index[-1]
        seg = rets.loc[d:end].iloc[1:]
        if holds:
            port = seg[list(holds)].mean(axis=1)
        else:
            port = pd.Series(0.0, index=seg.index)
        # turnover cost applied on first day of segment
        turn = len(holds.symmetric_difference(prev_holds)) / max(len(holds | prev_holds), 1)
        if len(port):
            port.iloc[0] -= turn * COST_RT
        daily.loc[port.index] = port.values
        prev_holds = holds
    return daily.fillna(0.0)


def market_regime(C):
    """Equal-weight liquid-market proxy > its 200DMA = risk-on."""
    r = C.pct_change().clip(-RET_CLIP, RET_CLIP)
    mkt = (1 + r.mean(axis=1)).cumprod()
    ma200 = mkt.rolling(200, min_periods=100).mean()
    return mkt > ma200


def metrics(daily, label):
    b = daily[daily.index.date <= SPLIT]; f = daily[daily.index.date > SPLIT]

    def m(x):
        x = x[x != 0] if (x != 0).any() else x
        xx = daily.loc[x.index] if False else x
        r = daily.reindex(x.index).fillna(0) if False else x
        if len(x) < 30 or x.std() == 0:
            return (0, 0, 0)
        eq = (1 + x).cumprod()
        sharpe = x.mean() / x.std() * np.sqrt(252)
        cagr = eq.iloc[-1] ** (252 / len(x)) - 1
        dd = (eq / eq.cummax() - 1).min()
        return (sharpe, cagr, dd)
    # use full daily series (0 on cash days) for build/forward windows
    bd = daily[daily.index.date <= SPLIT]; fd = daily[daily.index.date > SPLIT]
    sb, cb, ddb = m(bd); sf, cf, ddf = m(fd)
    print(f"  {label:12s}: BUILD Sharpe {sb:5.2f} CAGR {cb:+6.1%} DD {ddb:5.0%} | "
          f"FWD Sharpe {sf:5.2f} CAGR {cf:+6.1%} DD {ddf:5.0%}")
    return bd, fd


if __name__ == "__main__":
    C, V = load_wide()
    diagnostics(C)
    reb = rebalance_dates(C, every=21)
    print(f"[reb] {len(reb)} monthly rebalances {reb[0].date()}..{reb[-1].date()}")
    uni = liquid_universe(C, V, reb)
    regime = market_regime(C)
    sigs = make_signals()

    print("\n=== STRATEGY BATTERY (long-only top-30, monthly, 0.4% round-trip cost) ===")
    series = {}
    for name, fn in sigs.items():
        d = backtest(C, V, fn, reb, uni)
        metrics(d, name)
        series[name] = d
    # momentum + regime overlay
    dmr = backtest(C, V, sigs["mom_6_1"], reb, uni, regime=regime)
    metrics(dmr, "mom6+regime")
    series["mom6+regime"] = dmr

    # correlation of strategy daily returns (build)
    M = pd.DataFrame({k: v for k, v in series.items()})
    Mb = M[M.index.date <= SPLIT]
    print("\n=== correlation of daily returns (build) ===")
    print(Mb.corr().round(2).to_string())
    M.to_parquet(ROOT / "swing_momentum/multi_backtest_daily.parquet")
    print(f"\nsaved daily returns -> swing_momentum/multi_backtest_daily.parquet")
