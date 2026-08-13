"""Generate the long-format level table: one row per (date, system, level_name).
All levels are computed from strictly PRIOR-day/prior-week/current-morning-opening-range
information that is known before (or, for opening-range levels, during) the live session --
no lookahead into the day's own close/high/low used to define a level tested that same day,
except opening-range levels which by construction use only the first 15/30/60 minutes and are
tested only on bars AFTER that window closes.

Columns returned: date, system, level_name, level_price, anchor, priority(bool)
`anchor` is the reference point used later to build the random-level placebo (same anchor,
random distance matched to this system's own empirical mean distance).
"""
import numpy as np
import pandas as pd

SATY_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
SATY_PRIORITY = {0.382, 0.618, 1.0}
FIB_RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786]
FIB_EXT = [1.272, 1.618]


def _rows(date, system, name, price, anchor, priority=False, min_bar_idx=0):
    return dict(date=date, system=system, level_name=name, level_price=price,
                anchor=anchor, priority=priority, min_bar_idx=min_bar_idx)


def build_levels(daily: pd.DataFrame) -> pd.DataFrame:
    out = []
    d = daily.reset_index().rename(columns={"index": "date"})
    if "date" not in d.columns:
        d = daily.reset_index()
        d.columns = ["date"] + list(daily.columns)

    for r in d.itertuples(index=False):
        date = r.date
        pc, ph, pl = r.prior_close, r.prior_high, r.prior_low
        atr = r.atr14_prior
        if pd.isna(pc) or pd.isna(atr):
            continue

        # ---------------- 1. SATY ATR LEVELS (anchor = prior close, ladder x ATR14) ----------
        for ratio in SATY_RATIOS:
            pr = ratio in SATY_PRIORITY
            out.append(_rows(date, "SATY", f"{ratio}", pc + ratio * atr, pc, pr))
            out.append(_rows(date, "SATY", f"{ratio}", pc - ratio * atr, pc, pr))

        # ---------------- 2. FIBONACCI, prior DAY range -----------------------------------
        if not (pd.isna(ph) or pd.isna(pl)) and ph > pl:
            rng = ph - pl
            mid = (ph + pl) / 2
            for ratio in FIB_RATIOS:
                out.append(_rows(date, "FIB_DAY", f"{ratio}", pl + ratio * rng, mid))
            for ratio in FIB_EXT:
                out.append(_rows(date, "FIB_DAY", f"{ratio}", ph + (ratio - 1) * rng, mid))
                out.append(_rows(date, "FIB_DAY", f"{ratio}", pl - (ratio - 1) * rng, mid))

        # ---------------- 2b. FIBONACCI, prior WEEK range ---------------------------------
        pwh, pwl = r.prior_wk_high, r.prior_wk_low
        if not (pd.isna(pwh) or pd.isna(pwl)) and pwh > pwl:
            rngw = pwh - pwl
            midw = (pwh + pwl) / 2
            for ratio in FIB_RATIOS:
                out.append(_rows(date, "FIB_WEEK", f"{ratio}", pwl + ratio * rngw, midw))
            for ratio in FIB_EXT:
                out.append(_rows(date, "FIB_WEEK", f"{ratio}", pwh + (ratio - 1) * rngw, midw))
                out.append(_rows(date, "FIB_WEEK", f"{ratio}", pwl - (ratio - 1) * rngw, midw))

        # ---------------- 3. CLASSIC PIVOTS (daily, from prior day HLC) -------------------
        if not (pd.isna(ph) or pd.isna(pl) or pd.isna(pc)):
            H, L, C = ph, pl, pc
            # Floor
            PP = (H + L + C) / 3
            R1f, S1f = 2 * PP - L, 2 * PP - H
            R2f, S2f = PP + (H - L), PP - (H - L)
            R3f, S3f = H + 2 * (PP - L), L - 2 * (H - PP)
            for name, price in [("PP", PP), ("R1", R1f), ("S1", S1f), ("R2", R2f),
                                 ("S2", S2f), ("R3", R3f), ("S3", S3f)]:
                out.append(_rows(date, "PIVOT_FLOOR", name, price, PP))

            # Camarilla
            rngHL = H - L
            camR1, camS1 = C + rngHL * 1.1 / 12, C - rngHL * 1.1 / 12
            camR2, camS2 = C + rngHL * 1.1 / 6, C - rngHL * 1.1 / 6
            camR3, camS3 = C + rngHL * 1.1 / 4, C - rngHL * 1.1 / 4
            camR4, camS4 = C + rngHL * 1.1 / 2, C - rngHL * 1.1 / 2
            for name, price, pr in [("R1", camR1, False), ("S1", camS1, False),
                                     ("R2", camR2, False), ("S2", camS2, False),
                                     ("R3", camR3, True), ("S3", camS3, True),
                                     ("R4", camR4, True), ("S4", camS4, True)]:
                out.append(_rows(date, "PIVOT_CAM", name, price, C, pr))

            # Woodie
            PPw = (H + L + 2 * C) / 4
            R1w, S1w = 2 * PPw - L, 2 * PPw - H
            R2w, S2w = PPw + (H - L), PPw - (H - L)
            for name, price in [("PP", PPw), ("R1", R1w), ("S1", S1w), ("R2", R2w), ("S2", S2w)]:
                out.append(_rows(date, "PIVOT_WOODIE", name, price, PPw))

            # Fibonacci pivot (anchor = PP, offsets = fib ratios x range, distinct from FIB_DAY
            # which anchors off the raw low/high directly)
            for name, price in [("PP", PP), ("R1", PP + 0.382 * rngHL), ("S1", PP - 0.382 * rngHL),
                                 ("R2", PP + 0.618 * rngHL), ("S2", PP - 0.618 * rngHL)]:
                out.append(_rows(date, "PIVOT_FIBPIV", name, price, PP))

        # ---------------- 3b. Weekly floor pivot ------------------------------------------
        pwc = r.prior_wk_close
        if not (pd.isna(pwh) or pd.isna(pwl) or pd.isna(pwc)):
            Hw, Lw, Cw = pwh, pwl, pwc
            PPwk = (Hw + Lw + Cw) / 3
            R1wk, S1wk = 2 * PPwk - Lw, 2 * PPwk - Hw
            for name, price in [("PP", PPwk), ("R1", R1wk), ("S1", S1wk)]:
                out.append(_rows(date, "PIVOT_FLOOR_WK", name, price, PPwk))

        # ---------------- 4. CPR daily + weekly -------------------------------------------
        if not (pd.isna(ph) or pd.isna(pl)):
            PPc = (ph + pl + pc) / 3
            BC = (ph + pl) / 2
            TC = 2 * PPc - BC
            for name, price in [("TC", TC), ("PP", PPc), ("BC", BC)]:
                out.append(_rows(date, "CPR_DAY", name, price, PPc))
        if not (pd.isna(pwh) or pd.isna(pwl)):
            PPcw = (pwh + pwl + pwc) / 3
            BCw = (pwh + pwl) / 2
            TCw = 2 * PPcw - BCw
            for name, price in [("TC", TCw), ("PP", PPcw), ("BC", BCw)]:
                out.append(_rows(date, "CPR_WEEK", name, price, PPcw))

        # ---------------- 5. Opening range levels (tested only on bars AFTER the window) --
        # min_bar_idx = m => touch search starts at the bar the window CLOSES (e.g. OR15's
        # own high/low is only "final" once the 09:15-09:29 window has finished forming; a
        # "touch" of it while the window is still forming is lookahead, not a signal).
        for m in (15, 30, 60):
            oh, ol, om = getattr(r, f"or{m}_h"), getattr(r, f"or{m}_l"), getattr(r, f"or{m}_mid")
            if pd.isna(oh) or pd.isna(ol):
                continue
            for name, price in [("high", oh), ("low", ol), ("mid", om)]:
                out.append(_rows(date, f"OR{m}", name, price, om, min_bar_idx=m))

        # ---------------- 6. Round numbers (nearest 50 / 100 to prior close) -------------
        near50 = round(pc / 50) * 50
        near100 = round(pc / 100) * 100
        out.append(_rows(date, "ROUND50", "near50", near50, pc))
        out.append(_rows(date, "ROUND100", "near100", near100, pc))

        # ---------------- 7. Prior day / prior week levels (calibration family) -----------
        out.append(_rows(date, "PRIORDAY", "high", ph, pc))
        out.append(_rows(date, "PRIORDAY", "low", pl, pc))
        out.append(_rows(date, "PRIORDAY", "close", pc, pc))
        if not pd.isna(pwc):
            out.append(_rows(date, "PRIORWEEK", "high", pwh, pwc))
            out.append(_rows(date, "PRIORWEEK", "low", pwl, pwc))
            out.append(_rows(date, "PRIORWEEK", "close", pwc, pwc))

    lv = pd.DataFrame(out)
    return lv


if __name__ == "__main__":
    OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    lv = build_levels(daily)
    print(lv.shape)
    print(lv.groupby("system").size())
    lv.to_parquet(f"{OUT}/levels_real.parquet")
