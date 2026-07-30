"""DIMENSION 3 (range compression->expansion) + DIMENSION 4 (time structure, "build on the
opening window") -- combined into ONE signal family since they answer complementary questions
with the SAME mechanism: does a compressed range breaking out work, and does it work BETTER
inside the opening window specifically (already shown to be the era-stable, real part of the
day per STRUCTURAL_EDGES/OPENING_PATTERNS 2026-07-30 prior art)?

Three DISTINCT compression constructions (deliberately different from the already-tested
OR-width-tercile in OPENING_PATTERNS_20260730, which measured the CURRENT day's own opening
range; these all measure MULTI-DAY compression fixed BEFORE the trade day, a different
information source):
  NR7   -- day D's own range is the narrowest of the trailing 7 days (incl D). Breakout level =
           D's own H/L. Traded on D+1 (signal only known at D's close).
  NR4   -- same, trailing 4 days.
  BOX4  -- the trailing 4-day (D-4..D-1) BALANCE-AREA width, vs ATR, in the bottom decile of its
           trailing 100-day distribution. Breakout level = that 4-day box's H/L. Fully known
           before D's own open (uses D-4..D-1 only) -- traded on D itself.

Each tested as: ANY-TIME-OF-DAY breakout vs FIRST-60-MIN-ONLY breakout (dimension 4's
contribution -- does restricting the breakout window to the opening period help, given the
opening window is the one part of the day with a real, era-stable seasonality effect?).
REJECT (fade the break) and BREAK-AND-HOLD (continuation) both tested, exactly the touch_engine
mechanism, extended here with an explicit scan-window CAP (touch_engine only has a floor).
"""
import sys
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
PL = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
LIB = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\lib"
sys.path.insert(0, PL)
sys.path.insert(0, LIB)
from touch_engine import build_day_arrays, add_costs, EXIT_CFGS, BREAK_CONFIRM_K  # noqa: E402
from pathsafe import simulate_exit  # noqa: E402

OPEN_MIN = 555  # 09:15 in minutes-since-midnight


def build_levels(daily: pd.DataFrame) -> pd.DataFrame:
    dates = daily.index
    rows = []
    # NR7 / NR4: fires day-after (D+1), level = D's own H/L
    for flag_col, name in [("nr7", "NR7"), ("nr4", "NR4")]:
        flagged = daily[daily[flag_col] == True]
        idx = {d: i for i, d in enumerate(dates)}
        for d in flagged.index:
            i = idx[d]
            if i + 1 >= len(dates):
                continue
            nd = dates[i + 1]
            rows.append(dict(date=nd, system=name, level_name=f"{name}_HIGH",
                              level_price=float(daily.loc[d, "high"]), anchor=float(daily.loc[d, "close"])))
            rows.append(dict(date=nd, system=name, level_name=f"{name}_LOW",
                              level_price=float(daily.loc[d, "low"]), anchor=float(daily.loc[d, "close"])))
    # BOX4: fires same day D (fully known before D's open)
    box_flag = daily["box4_pctile_100"] <= 0.10
    for d in daily[box_flag].index:
        ph, pl, pc = daily.loc[d, ["prior4_high", "prior4_low", "prior_close"]]
        if not (np.isfinite(ph) and np.isfinite(pl)):
            continue
        rows.append(dict(date=d, system="BOX4", level_name="BOX4_HIGH",
                          level_price=float(ph), anchor=float(pc)))
        rows.append(dict(date=d, system="BOX4", level_name="BOX4_LOW",
                          level_price=float(pl), anchor=float(pc)))
    return pd.DataFrame(rows)


def simulate_capped(levels: pd.DataFrame, day_arrays: dict, atr_by_date: dict,
                     window_cap_min: int | None) -> pd.DataFrame:
    """touch_engine.simulate_all, extended with an optional UPPER bound on the scan window
    (minutes after 09:15). window_cap_min=None -> any time of day (touch_engine's original
    behaviour); window_cap_min=60 -> only the first 60 minutes of the session."""
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
        scan_start = 0
        scan_end = n if window_cap_min is None else int(np.searchsorted(tmin, OPEN_MIN + window_cap_min, side="left"))
        if scan_end <= scan_start:
            continue

        for r in grp.itertuples(index=False):
            level = r.level_price
            touched = np.where((l[scan_start:scan_end] <= level) & (h[scan_start:scan_end] >= level))[0]
            if len(touched) == 0:
                continue
            i = touched[0] + scan_start
            prior_ref = c[i - 1] if i > 0 else o[i]
            if prior_ref == level:
                continue
            side_below = prior_ref < level
            base = dict(date=date, system=r.system, level_name=r.level_name,
                        window_cap=("any" if window_cap_min is None else f"first{window_cap_min}m"))

            ei = i + 1
            if ei < n:
                entry_price = o[ei]
                direction = -1 if side_below else 1
                exit_bars = pd.DataFrame({"high": h[ei:], "low": l[ei:], "close": c[ei:]})
                if len(exit_bars) >= 3:
                    for cfg_name, cfg in EXIT_CFGS.items():
                        stop, target = cfg["stop_f"] * atr, cfg["target_f"] * atr
                        try:
                            res = simulate_exit(exit_bars, entry_price, direction, stop=stop, target=target)
                        except Exception:
                            continue
                        rows.append(dict(**base, hypothesis="REJECT", exit_cfg=cfg_name, direction=direction,
                                          pnl_pess=res.pnl_pessimistic, pnl_opt=res.pnl_optimistic,
                                          is_ambiguous=res.is_ambiguous, tmin=int(tmin[i])))

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
                    exit_bars = pd.DataFrame({"high": h[ej:], "low": l[ej:], "close": c[ej:]})
                    if len(exit_bars) >= 3:
                        for cfg_name, cfg in EXIT_CFGS.items():
                            stop, target = cfg["stop_f"] * atr, cfg["target_f"] * atr
                            try:
                                res = simulate_exit(exit_bars, entry_price, direction, stop=stop, target=target)
                            except Exception:
                                continue
                            rows.append(dict(**base, hypothesis="BREAK", exit_cfg=cfg_name, direction=direction,
                                              pnl_pess=res.pnl_pessimistic, pnl_opt=res.pnl_optimistic,
                                              is_ambiguous=res.is_ambiguous, tmin=int(tmin[i])))
    return pd.DataFrame(rows)


def main():
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
    day_arrays = build_day_arrays(bars)
    atr_by_date = daily["atr14_prior"].to_dict()

    levels = build_levels(daily)
    levels.to_parquet(f"{OUT}/compression_levels.parquet")
    print("levels", levels.shape)
    print(levels.groupby("level_name").size())

    all_tr = []
    for cap in (None, 60):
        tr = simulate_capped(levels, day_arrays, atr_by_date, cap)
        print(f"cap={cap}: {len(tr)} trade-rows")
        all_tr.append(tr)
    trades = pd.concat(all_tr, ignore_index=True)
    trades = add_costs(trades)
    trades.to_parquet(f"{OUT}/compression_trades.parquet")
    print("total", trades.shape)


if __name__ == "__main__":
    main()
