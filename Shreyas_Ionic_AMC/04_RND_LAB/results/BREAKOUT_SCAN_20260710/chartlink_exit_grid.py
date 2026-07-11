"""
EXIT-RULE GRID on the Chartlink realistic Rs.1Cr portfolio sim
==============================================================
Same engine as chartlink_realistic.py (actual Chartlink signals, daily MTM,
full costs, 10% entries, next-day-open entry), but sweeping:

  INITIAL SL (checked intraday vs low):
    - FIX10   : fixed -10% from entry
    - ATR1    : entry - 1.0 x ATR14(signal day)
    - ATR15   : entry - 1.5 x ATR14
    - ATR2    : entry - 2.0 x ATR14
    - SWING   : recent swing low (10-bar lowest low) - 1% buffer

  TRAILING EXIT (checked at close; exit at close if close < level):
    - NONE    : no trail (time exit only)
    - DMA20   : close < 20-SMA
    - KCU15   : close < EMA20 + 1.5xATR (Keltner upper, very tight)
    - KCU10   : close < EMA20 + 1.0xATR (Keltner upper)
    - KCMID   : close < EMA20 (Keltner mid)
    - KCL10   : close < EMA20 - 1.0xATR (Keltner lower)
    - KCL15   : close < EMA20 - 1.5xATR (Keltner lower, loose)

  Max hold 30 trading days in all cases (time exit at close).
  Trail only active from day 2 onward (entry day itself exempt).

35 combos. Output: grid CSV + ranked table.
"""
import os, warnings
import numpy as np, pandas as pd

warnings.filterwarnings("ignore")
os.environ["PYTHONIOENCODING"] = "utf-8"

SIG_CSV = r"C:\Users\Shreyas.1Gupta\Downloads\Backtest D_2026_3 (1).csv"
OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\BREAKOUT_SCAN_20260710"
PRICE_CACHE = os.path.join(OUT, "chartlink_prices.parquet")

INIT_CAP = 10_000_000
MAX_ENTRY_PCT = 0.10
DRIFT_MAX = 0.20
DRIFT_TRIM_TO = 0.15
BUY_COST = 0.00152
SELL_COST = 0.00137
SLIP = 0.0015
MIN_TICKET = 50_000
STALE_LIMIT = 10
MAX_HOLD = 30

# ---------------- Load signals + panel ----------------
sig = pd.read_csv(SIG_CSV)
sig["Date"] = pd.to_datetime(sig["Date"], format="%d-%m-%Y")
sig = sig.sort_values("Date").reset_index(drop=True)

panel = pd.read_parquet(PRICE_CACHE)
panel["date"] = pd.to_datetime(panel["date"])
print(f"Panel: {len(panel):,} rows, {panel['symbol'].nunique()} symbols")

# ---------------- Indicators per symbol ----------------
print("Computing ATR14 / SMA20 / EMA20 / swing lows...")
ind_frames = []
for s, g in panel.groupby("symbol"):
    g = g.sort_values("date").reset_index(drop=True)
    hi, lo, cl = g["high"], g["low"], g["close"]
    prev_cl = cl.shift(1)
    tr = pd.concat([hi - lo, (hi - prev_cl).abs(), (lo - prev_cl).abs()], axis=1).max(axis=1)
    g["atr14"] = tr.ewm(alpha=1/14, min_periods=5).mean()
    g["sma20"] = cl.rolling(20, min_periods=5).mean()
    g["ema20"] = cl.ewm(span=20, min_periods=5).mean()
    g["swing_low10"] = lo.rolling(10, min_periods=3).min()
    ind_frames.append(g)
panel_i = pd.concat(ind_frames, ignore_index=True)

# bar lookup: sym -> date -> (o,h,l,c,atr,sma20,ema20,swing)
sym_bars = {}
for s, g in panel_i.groupby("symbol"):
    sym_bars[s] = dict(zip(
        pd.DatetimeIndex(g["date"]),
        zip(g["open"], g["high"], g["low"], g["close"],
            g["atr14"], g["sma20"], g["ema20"], g["swing_low10"])
    ))

cal_start = pd.Timestamp("2025-11-15")
date_counts = panel_i.groupby("date")["symbol"].nunique()
calendar = sorted(d for d in panel_i["date"].unique()
                  if pd.Timestamp(d) >= cal_start and date_counts.get(d, 0) >= 20)
calendar = [pd.Timestamp(d) for d in calendar]
print(f"{len(sym_bars)} symbols, {len(calendar)} trading days")

# entry mapping (same as before) + signal-day indicator snapshot
entries_by_day = {}
for _, r in sig.iterrows():
    s, sd = r["Symbol"], r["Date"]
    if s not in sym_bars:
        continue
    later = [d for d in calendar if d > sd and d in sym_bars[s]]
    if not later or (later[0] - sd).days > 5:
        continue
    # signal-day bar (for ATR / swing at signal time; fall back to entry-day values)
    sig_bar = sym_bars[s].get(pd.Timestamp(sd))
    entries_by_day.setdefault(later[0], []).append((s, sig_bar))
n_map = sum(len(v) for v in entries_by_day.values())
print(f"Mapped {n_map}/{len(sig)} signals")

# ---------------- SL / trail level functions ----------------
def initial_sl(mode, entry_px, sig_bar, entry_bar):
    """Return SL price. sig_bar/entry_bar = (o,h,l,c,atr,sma,ema,swing)."""
    ref = sig_bar if sig_bar is not None and not np.isnan(sig_bar[4]) else entry_bar
    atr = ref[4] if ref is not None else np.nan
    swing = ref[7] if ref is not None else np.nan
    if mode == "FIX10":
        return entry_px * 0.90
    if mode == "ATR1":
        return entry_px - 1.0 * atr if atr == atr else entry_px * 0.90
    if mode == "ATR15":
        return entry_px - 1.5 * atr if atr == atr else entry_px * 0.90
    if mode == "ATR2":
        return entry_px - 2.0 * atr if atr == atr else entry_px * 0.90
    if mode == "SWING":
        if swing == swing and swing < entry_px:
            return swing * 0.99
        return entry_px * 0.90
    return entry_px * 0.90

def trail_level(mode, bar):
    """Return trail level from today's bar, or None."""
    o, h, l, c, atr, sma, ema, swing = bar
    if mode == "NONE":
        return None
    if mode == "DMA20":
        return sma if sma == sma else None
    if atr != atr or ema != ema:
        return None
    if mode == "KCU15":
        return ema + 1.5 * atr
    if mode == "KCU10":
        return ema + 1.0 * atr
    if mode == "KCMID":
        return ema
    if mode == "KCL10":
        return ema - 1.0 * atr
    if mode == "KCL15":
        return ema - 1.5 * atr
    return None

# ---------------- Simulation ----------------
def run_sim(sl_mode, trail_mode):
    cash = float(INIT_CAP)
    positions = {}
    nav_hist = []
    costs_paid = 0.0
    exits = {"SL": 0, "TRAIL": 0, "TIME": 0, "STALE": 0, "FINAL": 0}
    wins = losses = 0
    win_pnl = loss_pnl = 0.0
    hold_sum = 0
    n_entries = 0

    def sell(s, px, d, reason):
        nonlocal cash, costs_paid, wins, losses, win_pnl, loss_pnl, hold_sum
        p = positions[s]
        gross = p["shares"] * px
        fees = gross * SELL_COST
        cash += gross - fees
        costs_paid += fees
        pnl = (px - p["entry_px"]) * p["shares"] - fees
        if pnl > 0:
            wins += 1; win_pnl += pnl
        else:
            losses += 1; loss_pnl += abs(pnl)
        hold_sum += p["days_held"]
        exits[reason] += 1
        del positions[s]

    prev_nav = float(INIT_CAP)

    for d in calendar:
        for s, sig_bar in entries_by_day.get(d, []):
            if s in positions:
                continue
            bar = sym_bars.get(s, {}).get(d)
            if bar is None or not (bar[0] > 0):
                continue
            buy_px = bar[0] * (1 + SLIP)
            budget = min(MAX_ENTRY_PCT * prev_nav, cash)
            if budget < MIN_TICKET:
                continue
            shares = int(budget / (buy_px * (1 + BUY_COST)))
            if shares <= 0:
                continue
            gross = shares * buy_px
            fees = gross * BUY_COST
            cash -= gross + fees
            costs_paid += fees
            sl_px = initial_sl(sl_mode, buy_px, sig_bar, bar)
            positions[s] = {"shares": shares, "entry_px": buy_px, "sl_px": sl_px,
                            "days_held": 0, "stale": 0, "last_close": buy_px}
            n_entries += 1

        for s in list(positions.keys()):
            p = positions[s]
            bar = sym_bars.get(s, {}).get(d)
            if bar is None:
                p["stale"] += 1
                if p["stale"] > STALE_LIMIT:
                    sell(s, p["last_close"] * (1 - SLIP), d, "STALE")
                continue
            p["stale"] = 0
            o, h, l, c = bar[0], bar[1], bar[2], bar[3]
            if l <= p["sl_px"]:
                fill = min(o, p["sl_px"]) * (1 - SLIP)
                sell(s, fill, d, "SL")
                continue
            p["last_close"] = c
            p["days_held"] += 1
            # trail check at close (from day 2 onward)
            if p["days_held"] >= 2:
                tl = trail_level(trail_mode, bar)
                if tl is not None and c < tl:
                    sell(s, c * (1 - SLIP), d, "TRAIL")
                    continue
            if p["days_held"] >= MAX_HOLD:
                sell(s, c * (1 - SLIP), d, "TIME")

        pos_val = sum(p["shares"] * p["last_close"] for p in positions.values())
        nav = cash + pos_val
        for s in list(positions.keys()):
            p = positions[s]
            val = p["shares"] * p["last_close"]
            if val > DRIFT_MAX * nav:
                target = DRIFT_TRIM_TO * nav
                excess = int((val - target) / p["last_close"])
                if excess > 0:
                    gross = excess * p["last_close"] * (1 - SLIP)
                    fees = gross * SELL_COST
                    cash += gross - fees
                    costs_paid += fees
                    p["shares"] -= excess
        pos_val = sum(p["shares"] * p["last_close"] for p in positions.values())
        nav = cash + pos_val
        nav_hist.append(nav)
        prev_nav = nav

    for s in list(positions.keys()):
        sell(s, positions[s]["last_close"] * (1 - SLIP), calendar[-1], "FINAL")

    nav_arr = np.array(nav_hist + [cash])
    final_nav = cash
    total_ret = final_nav / INIT_CAP - 1
    peak = np.maximum.accumulate(nav_arr)
    max_dd = ((nav_arr / peak) - 1).min()
    rets = np.diff(nav_arr) / nav_arr[:-1]
    sharpe = rets.mean() / rets.std() * np.sqrt(252) if rets.std() > 0 else 0
    n_exits = wins + losses
    pf = win_pnl / loss_pnl if loss_pnl > 0 else 99

    return {
        "sl": sl_mode, "trail": trail_mode,
        "final_nav_L": round(final_nav / 1e5, 1),
        "ret_pct": round(total_ret * 100, 2),
        "max_dd_pct": round(max_dd * 100, 2),
        "sharpe": round(sharpe, 2),
        "win_pct": round(wins / n_exits * 100, 1) if n_exits else 0,
        "pf": round(pf, 2),
        "entries": n_entries,
        "sl_exits": exits["SL"], "trail_exits": exits["TRAIL"],
        "time_exits": exits["TIME"], "avg_hold": round(hold_sum / n_exits, 1) if n_exits else 0,
        "calmar_ratio": round(abs(total_ret / max_dd), 2) if max_dd < 0 else 99,
    }

SL_MODES = ["FIX10", "ATR1", "ATR15", "ATR2", "SWING"]
TRAIL_MODES = ["NONE", "DMA20", "KCU15", "KCU10", "KCMID", "KCL10", "KCL15"]

print(f"\nRunning {len(SL_MODES) * len(TRAIL_MODES)} combos...")
rows = []
for tm in TRAIL_MODES:
    for sm in SL_MODES:
        r = run_sim(sm, tm)
        rows.append(r)
        print(f"  {sm:<6} x {tm:<6}: ret {r['ret_pct']:>7.2f}%  DD {r['max_dd_pct']:>7.2f}%  "
              f"Sharpe {r['sharpe']:>5.2f}  win {r['win_pct']:>5.1f}%  PF {r['pf']:>5.2f}  "
              f"hold {r['avg_hold']:>4.1f}d  exits SL/TR/TIME {r['sl_exits']}/{r['trail_exits']}/{r['time_exits']}")

grid = pd.DataFrame(rows)
grid = grid.sort_values("ret_pct", ascending=False).reset_index(drop=True)
grid.to_csv(os.path.join(OUT, "chartlink_exit_grid.csv"), index=False)

print("\n" + "=" * 100)
print("TOP 12 BY RETURN")
print(grid.head(12).to_string(index=False))
print("\nBOTTOM 5")
print(grid.tail(5).to_string(index=False))
print("\nBASELINE (FIX10 x NONE) for reference:")
print(grid[(grid['sl']=='FIX10') & (grid['trail']=='NONE')].to_string(index=False))
print(f"\nSaved: chartlink_exit_grid.csv")
