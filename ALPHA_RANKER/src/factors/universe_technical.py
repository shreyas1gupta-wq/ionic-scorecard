"""Universe-scale (NIFTY-750) TECHNICAL + FLOW-MICRO factor engine.

Scales the pilot logic in factors_technical.py (momentum/trend/mean-reversion) and the
delivery-INDEPENDENT part of factors_flow.py (theme_flow_micro_current: volume expansion,
OBV slope, Amihud illiquidity, turnover-adjusted momentum) to the full universe list in
data/universe/symbols_750.txt.

NO LOOKAHEAD: every factor uses only bars up to and including the latest bar in each
symbol's own parquet (point-in-time at "today"). No hard-cutoff scores -- cross-sectional
percentile (0-100) over the full universe, computed only among symbols with enough history
for that particular factor (pandas .rank(pct=True) skips NaN).

Handles partial universe coverage: data/prices/ is still landing. Missing parquet files are
skipped and counted; symbols with <~252 bars get whatever factors their history supports
(shorter-lookback ones) and are flagged short_history=True rather than dropped or crashed on.
"""
import os
import glob
import numpy as np
import pandas as pd

BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\ALPHA_RANKER"
PRICES = os.path.join(BASE, "data", "prices")
UNIVERSE_FILE = os.path.join(BASE, "data", "universe", "symbols_750.txt")
RES = os.path.join(BASE, "results"); os.makedirs(RES, exist_ok=True)
REP = os.path.join(BASE, "reports"); os.makedirs(REP, exist_ok=True)

SHORT_HISTORY_BARS = 252  # ~1 trading year


def load_universe():
    with open(UNIVERSE_FILE, encoding="utf-8") as fh:
        return [ln.strip() for ln in fh if ln.strip()]


def load_price(tk):
    return pd.read_parquet(os.path.join(PRICES, f"{tk}.parquet")).sort_index()


def rsi(close, n=14):
    d = close.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def slope_norm(y):
    """OLS slope of y vs 0..n-1, normalised by mean(|y|) -> dimensionless %/period trend."""
    y = np.asarray(y, dtype=float)
    if len(y) < 2 or np.all(np.isnan(y)):
        return np.nan
    x = np.arange(len(y))
    b = np.polyfit(x, y, 1)[0]
    denom = np.mean(np.abs(y))
    return b / denom if denom != 0 else np.nan


def factors_for(tk, bench):
    """Point-in-time factors at the latest bar of tk's own price history.
    Every lookback is guarded: only computed if enough bars exist, else NaN
    (never crash, never fabricate a value off insufficient history)."""
    try:
        df = load_price(tk)
    except Exception as e:
        return None, f"load_error: {e}"
    if df.empty or "Close" not in df.columns:
        return None, "empty_or_bad_schema"

    c, v = df["Close"], df["Volume"]
    n = len(c)
    f = {"n_bars": n}

    def need(k):
        return n >= k

    # --- Momentum / trend ---
    f["ret_1m"]    = c.iloc[-1] / c.iloc[-22] - 1 if need(22) else np.nan
    f["ret_3m"]    = c.iloc[-1] / c.iloc[-64] - 1 if need(64) else np.nan
    f["ret_6m_sk"] = c.iloc[-22] / c.iloc[-127] - 1 if need(127) else np.nan
    f["ret_12_1"]  = c.iloc[-22] / c.iloc[-253] - 1 if need(253) else np.nan

    if need(64):
        b = bench.reindex(c.index).ffill()
        if pd.notna(b.iloc[-1]) and pd.notna(b.iloc[-64]) and b.iloc[-64] != 0:
            f["rs_3m"] = (c.iloc[-1] / c.iloc[-64]) / (b.iloc[-1] / b.iloc[-64]) - 1
        else:
            f["rs_3m"] = np.nan
    else:
        f["rs_3m"] = np.nan

    ma20 = c.rolling(20).mean()
    ma50 = c.rolling(50).mean()
    ma200 = c.rolling(200).mean()
    f["dist_50dma"]  = c.iloc[-1] / ma50.iloc[-1] - 1 if need(50) else np.nan
    f["dist_200dma"] = c.iloc[-1] / ma200.iloc[-1] - 1 if need(200) else np.nan
    f["ma_align"] = (float(ma20.iloc[-1] > ma50.iloc[-1] > ma200.iloc[-1]) if need(200) else np.nan)
    win52 = min(n, 252)
    f["prox_52wh"] = c.iloc[-1] / c.iloc[-win52:].max() if need(20) else np.nan

    # --- Mean-reversion / exhaustion ---
    f["rsi14"] = rsi(c).iloc[-1] if need(15) else np.nan
    sd20 = c.rolling(20).std()
    f["boll_pctb"] = ((c.iloc[-1] - ma20.iloc[-1]) / (2 * sd20.iloc[-1])) if need(20) and sd20.iloc[-1] > 0 else np.nan
    f["rev_1w"] = -(c.iloc[-1] / c.iloc[-6] - 1) if need(6) else np.nan

    # --- Flow / microstructure (delivery-INDEPENDENT, current, from OHLCV only) ---
    f["vol_expansion_5_60"] = v.tail(5).mean() / v.tail(60).mean() if need(60) and v.tail(60).mean() > 0 else np.nan

    if need(20):
        obv = (np.sign(c.diff().fillna(0)) * v).cumsum()
        f["obv_slope20"] = slope_norm(obv.tail(20))
    else:
        f["obv_slope20"] = np.nan

    if need(20):
        ret = c.pct_change()
        turnover = c * v
        turn_tail = turnover.tail(20)
        amihud = (ret.abs() / turnover).tail(20).mean() * 1e6
        f["amihud_illiq"] = amihud if turn_tail.min() > 0 else np.nan
    else:
        f["amihud_illiq"] = np.nan

    if need(120):
        turnover = c * v
        t20 = turnover.rolling(20).mean().iloc[-1]
        t120 = turnover.rolling(120).mean().iloc[-1]
        ret21 = c.iloc[-1] / c.iloc[-22] - 1
        f["turnover_adj_mom"] = ret21 / (t20 / t120) if t120 > 0 and t20 > 0 else np.nan
    else:
        f["turnover_adj_mom"] = np.nan

    return f, None


def main():
    universe = load_universe()
    bench = load_price("_NSEI")["Close"]

    rows = {}
    missing = []
    errors = []
    for tk in universe:
        path = os.path.join(PRICES, f"{tk}.parquet")
        if not os.path.exists(path):
            missing.append(tk)
            continue
        f, err = factors_for(tk, bench)
        if f is None:
            errors.append((tk, err))
            continue
        rows[tk] = f

    raw = pd.DataFrame(rows).T
    raw.index.name = "symbol"
    raw["short_history"] = raw["n_bars"] < SHORT_HISTORY_BARS

    MOM = ["ret_1m", "ret_3m", "ret_6m_sk", "ret_12_1", "rs_3m",
           "dist_50dma", "dist_200dma", "ma_align", "prox_52wh"]
    MR = ["rsi14", "boll_pctb", "rev_1w"]
    FLOW = ["vol_expansion_5_60", "obv_slope20", "amihud_illiq", "turnover_adj_mom"]

    num_cols = MOM + MR + FLOW
    num = raw[num_cols].apply(pd.to_numeric, errors="coerce")
    pct = num.rank(pct=True) * 100  # cross-sectional over full universe, NaN skipped per-column

    adj = pct.copy()
    sign = {c: +1 for c in num_cols}
    sign["amihud_illiq"] = -1  # higher illiquidity = worse
    for k, s in sign.items():
        if s == -1:
            adj[k] = 100 - pct[k]
    # non-monotonic mean-reversion factors: extremes penalised (pilot convention)
    adj["rsi14"] = 100 - (num["rsi14"] - 50).abs() / 50 * 100
    adj["boll_pctb"] = 100 - num["boll_pctb"].abs().clip(0, 2) / 2 * 100

    theme_momentum = adj[MOM].mean(axis=1, skipna=True)
    theme_meanrev = adj[MR].mean(axis=1, skipna=True)
    theme_flow_micro = adj[FLOW].mean(axis=1, skipna=True)

    out = raw.copy()
    out["theme_momentum"] = theme_momentum.round(1)
    out["theme_meanrev"] = theme_meanrev.round(1)
    out["theme_flow_micro"] = theme_flow_micro.round(1)
    out = out.sort_values("theme_momentum", ascending=False)

    out_path = os.path.join(RES, "universe_technical_scores.parquet")
    out.reset_index().to_parquet(out_path, index=False)

    # ---------- Report ----------
    n_universe = len(universe)
    n_scored = len(out)
    n_short = int(out["short_history"].sum())
    n_missing = len(missing)
    n_errors = len(errors)

    top10 = out.dropna(subset=["theme_momentum"]).head(10)
    bot10 = out.dropna(subset=["theme_momentum"]).tail(10).iloc[::-1]

    lines = []
    lines.append("# UNI-B: Universe Technical + Flow-Micro Engine\n")
    lines.append(f"Universe file: `data/universe/symbols_750.txt` ({n_universe} symbols)\n")
    lines.append("## Coverage\n")
    lines.append(f"- Scored: {n_scored} / {n_universe}")
    lines.append(f"- Missing price file (data still landing): {n_missing}")
    lines.append(f"- Load/schema errors: {n_errors}")
    lines.append(f"- Short-history (<{SHORT_HISTORY_BARS} bars, flagged short_history=True): {n_short}")
    lines.append("")
    if missing:
        lines.append(f"Missing symbols (first 30 of {n_missing}): {', '.join(missing[:30])}\n")
    if errors:
        lines.append(f"Errors (first 20 of {n_errors}): {errors[:20]}\n")

    lines.append("## Sanity check: top 10 by theme_momentum\n")
    lines.append(top10[["theme_momentum", "theme_meanrev", "theme_flow_micro", "n_bars", "short_history"]].to_markdown())
    lines.append("\n## Sanity check: bottom 10 by theme_momentum\n")
    lines.append(bot10[["theme_momentum", "theme_meanrev", "theme_flow_micro", "n_bars", "short_history"]].to_markdown())
    lines.append(f"\nSaved scores: `{out_path}`\n")
    lines.append("NOTE: percentiles are RELATIVE ranks among currently-scored universe symbols with "
                  "enough history for each factor, NOT calibrated probabilities. Re-run as data/prices/ "
                  "fills to widen coverage.\n")

    report_path = os.path.join(REP, "UNI_B_technical_flow.md")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    print(f"Scored {n_scored}/{n_universe} (missing {n_missing}, errors {n_errors}, short_history {n_short})")
    print(f"Saved: {out_path}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()
