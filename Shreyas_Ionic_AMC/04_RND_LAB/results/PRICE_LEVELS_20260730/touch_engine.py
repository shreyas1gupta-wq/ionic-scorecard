"""Touch detection + trade simulation for REJECTION and BREAK-AND-HOLD hypotheses.
Entry ALWAYS at the next 1-min bar's OPEN after the trigger bar closes (no same-bar fill).
Exit ALWAYS via lib/pathsafe.simulate_exit on the real remaining-day bar path (both bounds).
Session-only: every trade is closed out (or timed out) by that day's last bar -- no overnight
carry, consistent with the level systems being anchored per-day/per-week.
"""
import sys
import numpy as np
import pandas as pd

LIB = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib"
sys.path.insert(0, LIB)
from pathsafe import simulate_exit  # noqa: E402

BREAK_CONFIRM_K = 5           # bars allowed after touch to confirm a break-and-hold
EXIT_CFGS = {
    "tight_atr": dict(stop_f=0.30, target_f=0.45),   # RR 1.5
    "wide_atr":  dict(stop_f=0.50, target_f=0.85),   # RR 1.7
}


def build_day_arrays(bars_1min: pd.DataFrame):
    """date -> dict(times, open, high, low, close, tmin) numpy arrays, session order.
    tmin = minutes-since-midnight of each bar, used to enforce OR-window no-lookahead
    (a level anchored on the first 15/30/60 minutes cannot be "touched" validly until
    that window has actually closed)."""
    out = {}
    for date, g in bars_1min.groupby("date"):
        idx = g.index
        out[date] = dict(
            o=g["open"].to_numpy(float), h=g["high"].to_numpy(float),
            l=g["low"].to_numpy(float), c=g["close"].to_numpy(float),
            tmin=(idx.hour * 60 + idx.minute).to_numpy(int),
        )
    return out


def _make_bars_df(day, start_idx):
    return pd.DataFrame({"high": day["h"][start_idx:], "low": day["l"][start_idx:],
                          "close": day["c"][start_idx:]})


def simulate_all(levels: pd.DataFrame, day_arrays: dict, atr_by_date: dict) -> pd.DataFrame:
    """levels: date, system, level_name, level_price, anchor, priority.
    Returns one row per (level-day, hypothesis, exit_cfg) that produced a trade."""
    rows = []
    for date, grp in levels.groupby("date"):
        day = day_arrays.get(date)
        if day is None:
            continue
        h, l, o, c, tmin = day["h"], day["l"], day["o"], day["c"], day["tmin"]
        n = len(h)
        if n < 5:
            continue
        atr = atr_by_date.get(date, np.nan)
        if not np.isfinite(atr) or atr <= 0:
            continue
        run_high = np.maximum.accumulate(h)
        run_low = np.minimum.accumulate(l)

        for r in grp.itertuples(index=False):
            level = r.level_price
            cutoff_min = 555 + int(getattr(r, "min_bar_idx", 0))  # 555 = 09:15 in minutes
            scan_start = int(np.searchsorted(tmin, cutoff_min, side="left"))
            if scan_start >= n:
                continue
            touched_rel = np.where((l[scan_start:] <= level) & (h[scan_start:] >= level))[0]
            if len(touched_rel) == 0:
                continue
            i = touched_rel[0] + scan_start
            prior_ref = c[i - 1] if i > 0 else o[i]
            if prior_ref == level:
                continue
            side_below = prior_ref < level  # approached from below
            atr_consumed = (run_high[i] - run_low[i]) / atr

            base = dict(date=date, system=r.system, level_name=r.level_name,
                        priority=r.priority, atr_consumed=atr_consumed)

            # ---------------- REJECTION: fade at next bar's open ----------------------
            ei = i + 1
            if ei < n:
                entry_price = o[ei]
                direction = -1 if side_below else 1
                exit_bars = _make_bars_df(day, ei)
                if len(exit_bars) >= 3:
                    for cfg_name, cfg in EXIT_CFGS.items():
                        stop = cfg["stop_f"] * atr
                        target = cfg["target_f"] * atr
                        try:
                            res = simulate_exit(exit_bars, entry_price, direction,
                                                 stop=stop, target=target)
                        except Exception:
                            continue
                        rows.append(dict(**base, hypothesis="REJECT", exit_cfg=cfg_name,
                                          direction=direction, entry_price=entry_price,
                                          pnl_pess=res.pnl_pessimistic, pnl_opt=res.pnl_optimistic,
                                          is_ambiguous=res.is_ambiguous, n_bars=res.n_bars))

            # ---------------- BREAK-AND-HOLD: confirm close beyond level+buffer --------
            buffer = max(1.0, 0.05 * atr)
            j_end = min(i + BREAK_CONFIRM_K, n - 1)
            confirm_j = None
            for j in range(i, j_end + 1):
                if side_below and c[j] > level + buffer:
                    confirm_j = j
                    break
                if (not side_below) and c[j] < level - buffer:
                    confirm_j = j
                    break
            if confirm_j is not None:
                ej = confirm_j + 1
                if ej < n:
                    entry_price = o[ej]
                    direction = 1 if side_below else -1
                    exit_bars = _make_bars_df(day, ej)
                    if len(exit_bars) >= 3:
                        for cfg_name, cfg in EXIT_CFGS.items():
                            stop = cfg["stop_f"] * atr
                            target = cfg["target_f"] * atr
                            try:
                                res = simulate_exit(exit_bars, entry_price, direction,
                                                     stop=stop, target=target)
                            except Exception:
                                continue
                            rows.append(dict(**base, hypothesis="BREAK", exit_cfg=cfg_name,
                                              direction=direction, entry_price=entry_price,
                                              pnl_pess=res.pnl_pessimistic,
                                              pnl_opt=res.pnl_optimistic,
                                              is_ambiguous=res.is_ambiguous, n_bars=res.n_bars))
    return pd.DataFrame(rows)


def add_costs(trades: pd.DataFrame) -> pd.DataFrame:
    cost = np.where(trades["date"] < pd.Timestamp("2024-10-01"), 4.47, 5.97) + 0.5
    trades = trades.copy()
    trades["cost"] = cost
    trades["net_pess"] = trades["pnl_pess"] - cost
    trades["net_opt"] = trades["pnl_opt"] - cost
    return trades
