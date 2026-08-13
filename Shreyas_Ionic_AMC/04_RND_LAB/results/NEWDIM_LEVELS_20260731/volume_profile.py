"""DIMENSION 1 -- Volume Profile / Market Profile.
DATA SOURCE + LIMITS (stated up front, per the mandate):
  NIFTY spot 1-min has NO usable volume (col is 0, per SHARED_CONTEXT). No 1-min NIFTY futures
  volume series exists in DATA_CATALOG either. So the profile is built from the OPTION CHAIN's
  own traded volume (ce_vol+pe_vol summed across ALL strikes of the FRONT-WEEK expiry, in each
  15-min bucket) as a proxy for underlying trading activity -- reused from
  INDICATOR_MINE_20260730/chain_features_15min.parquet via chain_front.py's corrected front-week
  selection (avoids re-touching the raw 1-min chain -- RAM-safe by construction).
  LIMITS, stated explicitly:
    (a) Coverage is 2021-05-07..2026-05-29 only (the option-chain era), NOT the full 2015-2026
        spot history the price-level study used -- five years, not eleven.
    (b) Resolution is 15-MIN buckets (one spot_ref price + volume figure per bucket, ~25/day),
        not tick-level -- this is a coarse market profile, not the tick-by-tick TPO construction
        a real Level-2 feed would give. A "single print" / true TPO count is NOT attempted here
        for that reason -- the bucket resolution cannot resolve it honestly.
    (c) Volume is OPTIONS activity (all strikes), not underlying share/futures volume -- it is a
        proxy for "how much the market was transacting attention on NIFTY that bucket", not a
        literal count of NIFTY shares/contracts traded at that price.
Profile per day: bin spot_ref into ATR-scaled price bins (bin = ATR14_prior/10, floor 5pts, so
bin width is comparable across the 2021 (~15k) to 2026 (~26k) price range), sum total_vol per
bin. POC = bin with max volume. Value area (70%) = bins added by volume-descending order until
70% of the day's total volume is covered; VAH/VAL = max/min price among included bins (a
simplified value-area algorithm, not the strict POC-outward-contiguous-expansion definition --
disclosed, not hidden).
NAKED POC: a POC is "naked" from the day after it is set until the first future day whose
[low,high] range crosses it; only currently-untouched POCs are offered as levels for day D
(built from the state as of D's open, no lookahead).
Signals fed into touch_engine (REUSED VERBATIM from PRICE_LEVELS_20260730 -- same touch
mechanics, same ATR-scaled pathsafe exits, same cost model) -- REJECT and BREAK-AND-HOLD on
POC / VAH / VAL / NAKED_POC.
"""
import sys
import numpy as np
import pandas as pd

OUT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\NEWDIM_LEVELS_20260731"
PL = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PRICE_LEVELS_20260730"
sys.path.insert(0, PL)
from touch_engine import build_day_arrays, simulate_all, add_costs  # noqa: E402


def build_daily_profile(front, daily):
    """Returns DataFrame date -> poc, vah, val (that day's OWN profile, to be used as a level
    the FOLLOWING day only)."""
    f = front.dropna(subset=["spot_ref"]).copy()
    f = f.merge(daily[["atr14_prior"]], left_on="date", right_index=True, how="left")
    f["bin_size"] = (f["atr14_prior"] / 10).clip(lower=5.0)
    f["price_bin"] = (f["spot_ref"] / f["bin_size"]).round() * f["bin_size"]

    rows = []
    for date, g in f.groupby("date"):
        vp = g.groupby("price_bin")["total_vol"].sum().sort_values(ascending=False)
        if vp.empty or vp.sum() <= 0:
            continue
        poc = vp.index[0]
        cum = vp.cumsum()
        total = vp.sum()
        n_included = int((cum < 0.70 * total).sum()) + 1
        included_bins = vp.index[:n_included]
        vah = included_bins.max()
        val = included_bins.min()
        rows.append(dict(date=date, poc=poc, vah=vah, val=val))
    return pd.DataFrame(rows).set_index("date").sort_index()


def build_naked_poc_levels(profile, daily, horizon=20):
    """For each day D, the set of POCs (from days < D) not yet touched by any day's [low,high]
    in (poc_day, D). Built forward, so day D's level set uses only information through D-1's
    close (no lookahead). horizon caps how many days back a POC is still tracked (compute
    discipline; untouched-beyond-horizon POCs are dropped, stated as a limit)."""
    dates = sorted(profile.index)
    lows = daily["low"]
    highs = daily["high"]
    pending = []  # list of (poc_price, set_date)
    rows = []
    for d in dates:
        # today's trade uses the set BEFORE today's own range can touch anything
        for poc_price, set_date in pending:
            rows.append(dict(date=d, level_price=poc_price, anchor=poc_price, set_date=set_date))
        # now resolve today's touches (remove from pending) and age out beyond horizon
        if d in lows.index:
            lo, hi = lows.loc[d], highs.loc[d]
            pending = [(p, sd) for (p, sd) in pending if not (lo <= p <= hi)]
        pending = [(p, sd) for (p, sd) in pending if (d - sd).days <= horizon * 1.5]
        if d in profile.index:
            pending.append((profile.loc[d, "poc"], d))
    return pd.DataFrame(rows)


def main():
    front = pd.read_parquet(f"{OUT}/chain_front_15min.parquet")
    daily = pd.read_parquet(f"{OUT}/daily.parquet")
    bars = pd.read_parquet(f"{OUT}/bars_1min.parquet")

    profile = build_daily_profile(front, daily)
    profile.to_parquet(f"{OUT}/volprofile_daily.parquet")
    print("profile days", len(profile))

    # ---- levels for POC/VAH/VAL: D-1's profile value used on day D (shift by construction:
    # profile.index already IS the day the profile was FORMED; we join it to the NEXT trading
    # day explicitly) ----
    prof_dates = sorted(profile.index)
    next_day = {prof_dates[i]: prof_dates[i + 1] for i in range(len(prof_dates) - 1)}
    lvl_rows = []
    for d in prof_dates:
        nd = next_day.get(d)
        if nd is None:
            continue
        poc, vah, val = profile.loc[d, ["poc", "vah", "val"]]
        for name, price in [("POC", poc), ("VAH", vah), ("VAL", val)]:
            lvl_rows.append(dict(date=nd, system="VOLPROFILE", level_name=name,
                                  level_price=float(price), anchor=float(poc), priority=False))
    levels_pvv = pd.DataFrame(lvl_rows)

    naked = build_naked_poc_levels(profile, daily, horizon=20)
    naked["system"] = "VOLPROFILE"
    naked["level_name"] = "NAKED_POC"
    naked["priority"] = False
    levels_naked = naked[["date", "system", "level_name", "level_price", "anchor", "priority"]]

    levels = pd.concat([levels_pvv, levels_naked], ignore_index=True)
    levels.to_parquet(f"{OUT}/volprofile_levels.parquet")
    print("levels", levels.shape)
    print(levels.groupby("level_name").size())

    day_arrays = build_day_arrays(bars)
    atr_by_date = daily["atr14_prior"].to_dict()
    trades = simulate_all(levels, day_arrays, atr_by_date)
    trades = add_costs(trades)
    trades.to_parquet(f"{OUT}/volprofile_trades.parquet")
    print("trades", trades.shape)
    print(trades.groupby(["level_name", "hypothesis", "exit_cfg"])["net_pess"].agg(["count", "mean"]))


if __name__ == "__main__":
    main()
