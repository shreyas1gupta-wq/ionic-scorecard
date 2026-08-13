"""Trade simulation for anchored-VWAP band touches. One trade-opportunity per day per
(anchor, sigma, side) -- the FIRST time that day's (time-varying, PIT-safe) band is touched,
scanning buckets in chronological order. Mirrors touch_engine.py's REJECT / BREAK-AND-HOLD
mechanics and pathsafe exits exactly, generalized to a level that changes every 15-min bucket
instead of being fixed for the whole day.
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


def simulate_anchor(bands: pd.DataFrame, day_arrays: dict, atr_by_date: dict, anchor_name: str,
                     sigma: int) -> pd.DataFrame:
    rows = []
    ucol, lcol = f"upper{sigma}_prior", f"lower{sigma}_prior"
    b = bands.dropna(subset=[ucol, lcol]).copy()
    b["tmin"] = b["bucket"].dt.hour * 60 + b["bucket"].dt.minute
    for date, grp in b.groupby("date"):
        day = day_arrays.get(date)
        if day is None:
            continue
        h, l, o, c, tmin = day["h"], day["l"], day["o"], day["c"], day["tmin"]
        n = len(h)
        if n < 10:
            continue
        atr = atr_by_date.get(date, np.nan)
        if not np.isfinite(atr) or atr <= 0:
            continue
        grp = grp.sort_values("bucket")
        touch_upper = None
        touch_lower = None
        for _, r in grp.iterrows():
            win_start, win_end = r["tmin"], r["tmin"] + 15
            i0 = int(np.searchsorted(tmin, win_start, side="left"))
            i1 = int(np.searchsorted(tmin, win_end, side="left"))
            if i0 >= n:
                continue
            i1 = min(i1, n)
            if touch_upper is None:
                hits = np.where(h[i0:i1] >= r[ucol])[0]
                if len(hits):
                    touch_upper = (i0 + hits[0], r[ucol])
            if touch_lower is None:
                hits = np.where(l[i0:i1] <= r[lcol])[0]
                if len(hits):
                    touch_lower = (i0 + hits[0], r[lcol])
            if touch_upper is not None and touch_lower is not None:
                break

        for side, touch in (("UPPER", touch_upper), ("LOWER", touch_lower)):
            if touch is None:
                continue
            i, level = touch
            side_below = (side == "LOWER")  # approached from below (touched lower band from above... )
            base = dict(date=date, anchor=anchor_name, sigma=sigma, side=side)

            # REJECT: fade at next bar open
            ei = i + 1
            if ei < n:
                entry_price = o[ei]
                direction = 1 if side == "LOWER" else -1  # fade: bounce off lower=long, off upper=short
                exit_bars = pd.DataFrame({"high": h[ei:], "low": l[ei:], "close": c[ei:]})
                if len(exit_bars) >= 3:
                    for cfg_name, cfg in EXIT_CFGS.items():
                        stop, target = cfg["stop_f"] * atr, cfg["target_f"] * atr
                        try:
                            res = simulate_exit(exit_bars, entry_price, direction, stop=stop, target=target)
                        except Exception:
                            continue
                        rows.append(dict(**base, hypothesis="REJECT", exit_cfg=cfg_name,
                                          direction=direction, pnl_pess=res.pnl_pessimistic,
                                          pnl_opt=res.pnl_optimistic, is_ambiguous=res.is_ambiguous,
                                          tmin=int(tmin[i])))

            # CONTINUE (BREAK-AND-HOLD): confirm close beyond level+buffer within K bars
            buffer = max(1.0, 0.05 * atr)
            j_end = min(i + BREAK_CONFIRM_K, n - 1)
            confirm_j = None
            for j in range(i, j_end + 1):
                if side == "UPPER" and c[j] > level + buffer:
                    confirm_j = j
                    break
                if side == "LOWER" and c[j] < level - buffer:
                    confirm_j = j
                    break
            if confirm_j is not None:
                ej = confirm_j + 1
                if ej < n:
                    entry_price = o[ej]
                    direction = 1 if side == "UPPER" else -1  # continue through upper=long, through lower=short
                    exit_bars = pd.DataFrame({"high": h[ej:], "low": l[ej:], "close": c[ej:]})
                    if len(exit_bars) >= 3:
                        for cfg_name, cfg in EXIT_CFGS.items():
                            stop, target = cfg["stop_f"] * atr, cfg["target_f"] * atr
                            try:
                                res = simulate_exit(exit_bars, entry_price, direction, stop=stop, target=target)
                            except Exception:
                                continue
                            rows.append(dict(**base, hypothesis="CONTINUE", exit_cfg=cfg_name,
                                              direction=direction, pnl_pess=res.pnl_pessimistic,
                                              pnl_opt=res.pnl_optimistic, is_ambiguous=res.is_ambiguous,
                                              tmin=int(tmin[i])))
    return pd.DataFrame(rows)


def main():
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    day_arrays = build_day_arrays(bars)
    atr_by_date = daily["atr14_prior"].to_dict()

    all_trades = []
    for kind in ("session", "week", "month", "swing"):
        bands = pd.read_parquet(f"{OUT}/vwap_bands_{kind}.parquet")
        for sigma in (1, 2):
            tr = simulate_anchor(bands, day_arrays, atr_by_date, kind, sigma)
            print(f"{kind} sigma={sigma}: {len(tr)} trade-rows")
            all_trades.append(tr)
    trades = pd.concat(all_trades, ignore_index=True)
    trades = add_costs(trades)
    trades.to_parquet(f"{OUT}/vwap_trades.parquet")
    print("total", trades.shape)


if __name__ == "__main__":
    main()
