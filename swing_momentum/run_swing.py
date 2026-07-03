"""Track 2 core backtest: regime-gated momentum-LEADERSHIP swing on the
survivorship-safe Nifty500 panel 2005-2025 (close-based).

Engine: weekly rebalance to top-N leaders (Minervini trend-template pass, ranked
by relative strength), equal-weight, REGIME-GATED (no new exposure when the
market regime is RED), weekly trailing stop, transaction costs. No lookahead:
weights from info <= t applied to t->t+1 returns.

Tests the core thesis: does regime-gated leadership momentum deliver high CAGR /
controlled drawdown on Indian equities? Reports IS/OOS, per-year, and the
critical regime-ON vs always-ON comparison.
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

P = Path(__file__).resolve().parent / "processed"
COST_BPS = 30          # round-trip per name turnover (brokerage+STT+slippage), bps
TOP_N = 20
STOP = 0.15            # weekly-close trailing stop from peak (tighter → cut DD)
RF = 0.06

close_long = pd.read_parquet(P / "eq_close.parquet")
mem = pd.read_parquet(P / "membership.parquet")
close = close_long.pivot_table(index="date", columns="symbol", values="close").sort_index()
close = close[~close.index.duplicated()]
close = close.ffill(limit=10)   # bridge non-trading-day gaps so rolling SMAs aren't all-NaN
print(f"panel {close.shape}", flush=True)

# --- survivorship: delisting dates → realize a loss when a held name delists ---
DELIST_LOSS = -0.50
try:
    dl = pd.read_excel(Path(__file__).resolve().parents[1] /
                       "Nifty500_Delisted_2005_2025.xlsx", sheet_name="Sheet1")
    dl = dl.rename(columns={dl.columns[0]: "date"})
    dl["date"] = pd.to_datetime(dl["date"], errors="coerce")
    dl = dl.dropna(subset=["date"]).set_index("date")
    delist_date = {}
    for s in dl.columns:
        col = pd.to_numeric(dl[s], errors="coerce").dropna()
        if len(col):
            delist_date[str(s).upper()] = col.index.max()
    print(f"delisted register: {len(delist_date)} names with delist dates")
except Exception as e:
    delist_date = {}
    print(f"delist load failed ({str(e)[:80]}) — survivorship loss disabled")

# point-in-time membership mask (monthly snapshots ffilled to daily)
mem["month"] = pd.to_datetime(mem["month"])
mwide = (mem.assign(v=True).pivot_table(index="month", columns="symbol", values="v",
         aggfunc="any").reindex(columns=close.columns))
memmask = mwide.reindex(close.index, method="ffill").fillna(False).astype(bool)

# --- indicators (lookback-only) ---
sma50 = close.rolling(50, min_periods=40).mean()
sma150 = close.rolling(150, min_periods=120).mean()
sma200 = close.rolling(200, min_periods=150).mean()
hi52 = close.rolling(252, min_periods=180).max()
lo52 = close.rolling(252, min_periods=180).min()
ret6 = close / close.shift(126) - 1
ret12 = close / close.shift(252) - 1
rising200 = sma200 > sma200.shift(21)

trend_ok = ((close > sma150) & (sma150 > sma200) & rising200 & (close > sma50)
            & (sma50 > sma150) & (close >= 1.25 * lo52) & (close >= 0.75 * hi52))
# liquidity/quality proxy: price floor (drop penny names) — full ADV gate pending volume data
elig = trend_ok & memmask & ret12.notna() & (close >= 20)

# relative strength score (blend), ranked cross-sectionally among eligible
rs = (0.6 * ret12 + 0.4 * ret6)
rs_elig = rs.where(elig)
rs_rank = rs_elig.rank(axis=1, pct=True)   # 0..1 within eligible each day

# --- regime: clean Nifty 50 index (yfinance) + breadth ---
nif = pd.read_csv(Path(__file__).resolve().parents[1] /
                  "intraday_options_strategy/datasets/raw/nifty50_daily.csv",
                  parse_dates=["Date"]).set_index("Date")["Close"].sort_index()
nif = nif[~nif.index.duplicated()].reindex(close.index).ffill()
nif_sma200 = nif.rolling(200, min_periods=200).mean()
nif_sma50 = nif.rolling(50, min_periods=50).mean()
breadth = (close > sma200).where(memmask).mean(axis=1)   # % above 200DMA
# tighter regime to cut drawdown: index above BOTH 200 & 50 DMA AND healthy breadth
regime_green = (nif > nif_sma200) & (nif > nif_sma50) & (breadth > 0.40)
regime_green = regime_green.fillna(False)

# --- diagnostics: eligibility + regime by year ---
elig_cnt = elig.sum(axis=1)
diag = pd.DataFrame({"elig": elig_cnt, "green": regime_green.astype(int),
                     "breadth": breadth}).groupby(close.index.year).mean()
print("\nyear-diagnostics (avg eligible names / regime-green frac / breadth):")
print(diag.round(2).to_string())

# --- weekly rebalance backtest ---
rebal = close.index[::5]                                 # ~weekly
fwd = close.shift(-5) / close - 1                        # next-week return per name (t->t+5)


def run(use_regime: bool):
    eq = [1.0]; dates = [close.index[0]]; held = {}; turn_hist = []
    held_peak = {}
    for t in rebal:
        if t not in rs_rank.index:
            continue
        green = bool(regime_green.get(t, False)) if use_regime else True
        # selection
        if green:
            row = rs_rank.loc[t].dropna()
            picks = list(row.sort_values(ascending=False).head(TOP_N).index)
        else:
            picks = []
        # weekly trailing stop on currently held names (close-based)
        newheld = {}
        for s in picks:
            newheld[s] = held.get(s, close.at[t, s] if s in close.columns else np.nan)
        # peak track + stop
        keep = {}
        for s, entry in newheld.items():
            px = close.at[t, s] if s in close.columns else np.nan
            pk = max(held_peak.get(s, entry), px)
            if px >= pk * (1 - STOP):
                keep[s] = entry; held_peak[s] = pk
        picks = list(keep.keys())
        # portfolio next-week return (equal weight); realize delisting losses (survivorship)
        if picks:
            rr = fwd.loc[t, picks].replace([np.inf, -np.inf], np.nan)
            vals = []
            for s in picks:
                v = rr.get(s, np.nan)
                if np.isnan(v):
                    dd = delist_date.get(s)
                    if dd is not None and t <= dd <= t + pd.Timedelta(days=12):
                        v = DELIST_LOSS          # held into delisting → realize loss
                    else:
                        continue                 # genuine no-data (panel end) → drop
                vals.append(v)
            port = float(np.mean(vals)) if vals else 0.0
        else:
            port = 0.0
        # turnover cost
        prev = set(held.keys()); cur = set(picks)
        turn = len(prev.symmetric_difference(cur)) / max(TOP_N, 1)
        cost = turn * (COST_BPS / 1e4)
        turn_hist.append(turn)
        eq.append(eq[-1] * (1 + port - cost))
        dates.append(t)
        held = {s: keep.get(s) for s in picks}
    e = pd.Series(eq[1:], index=pd.DatetimeIndex(dates[1:]))
    return e, np.mean(turn_hist)


def stats(e, label):
    r = e.pct_change().dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cagr = e.iloc[-1] ** (1 / yrs) - 1
    vol = r.std() * np.sqrt(52)
    sharpe = (r.mean() * 52 - RF) / vol if vol > 0 else 0
    peak = e.cummax(); mdd = ((peak - e) / peak).max()
    calmar = cagr / mdd if mdd > 0 else 0
    print(f"{label:22} CAGR {cagr:+7.1%}  vol {vol:5.1%}  Sharpe {sharpe:5.2f}  "
          f"MaxDD {mdd:5.1%}  Calmar {calmar:4.2f}")
    return dict(cagr=cagr, mdd=mdd, sharpe=sharpe, calmar=calmar)


print(f"\n=== Regime-gated leadership momentum (Top{TOP_N}, stop {STOP:.0%}, "
      f"cost {COST_BPS}bps, weekly) ===")
eg, tg = run(use_regime=True)
ea, ta = run(use_regime=False)
n_is = int(len(eg) * 0.70)
stats(eg, "REGIME-GATED (full)")
stats(eg.iloc[:n_is] / eg.iloc[0], "  IS (2005-~2019)")
stats(eg.iloc[n_is:] / eg.iloc[n_is], "  OOS (~2019-2025)")
stats(ea, "ALWAYS-ON (no regime)")
print(f"\nregime cuts drawdown: gated MaxDD vs always-on — the core hypothesis.")
print(f"avg weekly turnover: gated {tg:.0%}, always {ta:.0%}")
# per-year
yr = eg.groupby(eg.index.year).apply(lambda s: s.iloc[-1] / s.iloc[0] - 1)
print("\nper-year (regime-gated):")
print(yr.apply(lambda x: f"{x:+.0%}").to_string())
eg.to_csv(Path(__file__).resolve().parent / "processed" / "equity_regime.csv")
