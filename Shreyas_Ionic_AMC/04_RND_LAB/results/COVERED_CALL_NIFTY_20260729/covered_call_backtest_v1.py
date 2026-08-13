"""
First-pass (illustrative, NOT Gate-4 certified) MONTHLY covered-call backtest on NIFTY,
using official NSE F&O index bhavcopy (fo_bhavcopy_hist, 2016-2026) for option closes
+ real NIFTY 50 index daily for the underlying leg. Avoids expiry-day SETTLE_PR landmine
(#9) by always exiting the day BEFORE expiry using CLOSE, gated on CONTRACTS>0.
"""
import glob
import numpy as np
import pandas as pd

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
OUT = r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\73e27829-a3d9-4873-9e54-0077b9710f47\scratchpad"

LOT = 75
SWEEP_FRAC = 0.50
SIGMA_K = 1.0
STRIKE_STEP = 50

def option_costs(premium_pts, lots, side_is_sell):
    notional = premium_pts * LOT * lots
    brokerage = 20.0
    stt = 0.001 * notional if side_is_sell else 0.0
    exch = 0.00035 * notional
    sebi = notional * 10 / 1e7
    gst = 0.18 * (brokerage + exch + sebi)
    stamp = 0.00003 * notional if not side_is_sell else 0.0
    slippage = 0.0025 * notional
    return brokerage + stt + exch + sebi + gst + stamp + slippage

def rsi(series, n=14):
    d = series.diff()
    up = d.clip(lower=0).rolling(n).mean()
    dn = (-d.clip(upper=0)).rolling(n).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)

def main():
    # ---- options panel ----
    frames = []
    for yr in range(2016, 2027):
        p = f"{ROOT}/Shreyas_Ionic_AMC/05_DATA_OFFICE/data/fo_bhavcopy_hist/fo_idx_{yr}.parquet"
        try:
            d = pd.read_parquet(p, columns=["INSTRUMENT","SYMBOL","EXPIRY_DT","STRIKE_PR",
                                             "OPTION_TYP","CLOSE","SETTLE_PR","CONTRACTS","TIMESTAMP"])
        except FileNotFoundError:
            continue
        d = d[(d["SYMBOL"]=="NIFTY") & (d["INSTRUMENT"]=="OPTIDX") & (d["OPTION_TYP"]=="CE")]
        frames.append(d)
    opt = pd.concat(frames, ignore_index=True)
    opt["expiry"] = pd.to_datetime(opt["EXPIRY_DT"], format="%d-%b-%Y").dt.date
    opt["tday"] = pd.to_datetime(opt["TIMESTAMP"], format="%d-%b-%Y").dt.date
    opt["strike"] = opt["STRIKE_PR"].astype(float)
    print(f"[opt] rows={len(opt):,} expiries={opt['expiry'].nunique()} range {opt['tday'].min()}..{opt['tday'].max()}")

    # ---- spot / index ----
    n50 = pd.read_parquet(f"{ROOT}/datasets/index_daily/nifty50.parquet")
    n50["timestamp"] = pd.to_datetime(n50["timestamp"], utc=False)
    if n50["timestamp"].dt.tz is None:
        n50["timestamp"] = n50["timestamp"].dt.tz_localize("Asia/Kolkata")
    n50["date"] = n50["timestamp"].dt.tz_convert("Asia/Kolkata").dt.date
    daily = n50.set_index("date")["close"].sort_index().to_frame("close")
    daily.index = pd.to_datetime(daily.index)
    daily["ret"] = daily["close"].pct_change()
    daily["rv20"] = daily["ret"].rolling(20).std() * np.sqrt(252)
    daily["sma20"] = daily["close"].rolling(20).mean()
    daily["sma50"] = daily["close"].rolling(50).mean()
    daily["rsi14"] = rsi(daily["close"], 14)
    trading_days = daily.index

    # ---- monthly expiries = last expiry-per-calendar-month present in the CE panel ----
    by_month = {}
    for e in sorted(opt["expiry"].unique()):
        by_month.setdefault((e.year, e.month), []).append(e)
    monthly = sorted(max(v) for v in by_month.values())
    print(f"[monthly] {len(monthly)} monthly expiries {monthly[0]}..{monthly[-1]}")

    def next_td_after(d):
        d = pd.Timestamp(d)
        a = trading_days[trading_days > d]
        return a[0] if len(a) else None

    def last_td_before(d):
        d = pd.Timestamp(d)
        b = trading_days[trading_days < d]
        return b[-1] if len(b) else None

    def lookup(expiry, strike, tday, tries=(0, 50, -50, 100, -100)):
        for off in tries:
            k = strike + off
            row = opt[(opt["expiry"]==expiry) & (opt["strike"]==k) & (opt["tday"]==tday) & (opt["CONTRACTS"]>0)]
            if len(row):
                return float(row["CLOSE"].iloc[0]), k
        return None, None

    rows = []
    for i in range(len(monthly)-1):
        prev_exp, this_exp = monthly[i], monthly[i+1]
        entry_day = next_td_after(prev_exp)
        exit_day = last_td_before(this_exp)
        if entry_day is None or exit_day is None or entry_day >= exit_day:
            continue
        if entry_day not in daily.index or exit_day not in daily.index:
            continue
        spot_entry = daily.loc[entry_day, "close"]
        spot_exit = daily.loc[exit_day, "close"]
        rv20 = daily.loc[entry_day, "rv20"]
        rsi14 = daily.loc[entry_day, "rsi14"]
        sma20 = daily.loc[entry_day, "sma20"]
        sma50 = daily.loc[entry_day, "sma50"]
        if pd.isna(rv20) or pd.isna(rsi14) or pd.isna(sma20) or pd.isna(sma50):
            continue

        monthly_sigma_pct = rv20 * np.sqrt(21/252)
        target = round(spot_entry * (1 + SIGMA_K*monthly_sigma_pct) / STRIKE_STEP) * STRIKE_STEP

        strong_uptrend = (spot_entry > sma20 > sma50) and (50 <= rsi14 <= 70)
        oversold = rsi14 <= 30
        overlay_signal = not (strong_uptrend or oversold)   # True = overlay says WRITE this cycle (v1: SMA-stack+mid-RSI skip)
        overbought = rsi14 >= 70
        overlay_v2_signal = not (overbought or oversold)     # v2: skip BOTH RSI tails, write only in neutral 30-70 band

        rec = dict(cycle=i, entry_day=entry_day.date(), exit_day=exit_day.date(), this_exp=this_exp,
                   dte=(this_exp - entry_day.date()).days,
                   spot_entry=spot_entry, spot_exit=spot_exit, rv20=rv20, rsi14=rsi14,
                   monthly_sigma_pct=monthly_sigma_pct, target_strike=target,
                   overlay_signal=overlay_signal, overlay_v2_signal=overlay_v2_signal,
                   regime=("uptrend_skip" if strong_uptrend else
                           "oversold_skip" if oversold else "normal"))

        # ALWAYS attempt the real-data lookup (independent of the overlay decision) so both
        # the "always write" and "overlay" variants can be simulated off the SAME fetched data.
        prem_entry, k1 = lookup(this_exp, target, entry_day.date())
        prem_exit, k2 = lookup(this_exp, target, exit_day.date())
        if prem_entry is None or prem_exit is None:
            rec["note"] = "no-liquid-print"
            rec["data_ok"] = False
        else:
            rec["data_ok"] = True
            rec["strike_used"] = k1
            gross_rs = (prem_entry - prem_exit) * LOT
            cost_sell = option_costs(prem_entry, 1, True)
            cost_buy = option_costs(prem_exit, 1, False) if prem_exit > 0.05 else 0.0
            net_rs = gross_rs - cost_sell - cost_buy
            rec.update(prem_entry=prem_entry, prem_exit=prem_exit, net_pnl_rs=net_rs,
                       itm_at_exit=bool(spot_exit > k1))
        rows.append(rec)

    df = pd.DataFrame(rows)
    df.to_csv(f"{OUT}/cc_bhav_cycles.csv", index=False)
    print(f"cycles total={len(df)} avg_dte={df['dte'].mean():.1f}")
    print(f"data_ok={df['data_ok'].sum()}  no-liquid-print={(~df['data_ok']).sum()}")
    print(f"overlay says WRITE={df['overlay_signal'].sum()}  SKIP={(~df['overlay_signal']).sum()}")
    print(df["regime"].value_counts())

    def simulate(df, mode):
        units = LOT
        cash = 0.0
        out = []
        for _, r in df.iterrows():
            if mode == "always":
                gate = True
            elif mode == "v1":
                gate = bool(r["overlay_signal"])
            elif mode == "v2":
                gate = bool(r["overlay_v2_signal"])
            execute = bool(r["data_ok"]) and gate
            pnl = 0.0
            if execute:
                lots_now = max(1, int(units // LOT))
                pnl = r["net_pnl_rs"] * lots_now
                cash += pnl
                sweep = SWEEP_FRAC * max(pnl, 0)
                units += sweep / r["spot_exit"]
                cash -= sweep
            out.append(dict(cycle=r["cycle"], nav=units*r["spot_exit"]+cash, units=units, cash=cash,
                             option_pnl=pnl, executed=execute))
        return pd.DataFrame(out)

    dfv = df.dropna(subset=["spot_exit"]).reset_index(drop=True)
    nav_ov = simulate(dfv, "v1")
    nav_aw = simulate(dfv, "always")
    nav_v2 = simulate(dfv, "v2")

    spot0, spotN = dfv["spot_entry"].iloc[0], dfv["spot_exit"].iloc[-1]
    bh0, bhN = LOT*spot0, LOT*spotN
    years = (pd.Timestamp(dfv["exit_day"].iloc[-1]) - pd.Timestamp(dfv["entry_day"].iloc[0])).days/365.25

    def c(nav0, navN): return (navN/nav0)**(1/years)-1

    print(f"window {dfv['entry_day'].iloc[0]} -> {dfv['exit_day'].iloc[-1]}  ({years:.2f}y)")
    print(f"Buy&Hold:      NAVn={bhN:,.0f}  CAGR={c(bh0,bhN)*100:.2f}%")
    print(f"AlwaysWrite:   NAVn={nav_aw['nav'].iloc[-1]:,.0f}  CAGR={c(bh0,nav_aw['nav'].iloc[-1])*100:.2f}%  units_end={nav_aw['units'].iloc[-1]:.1f}")
    print(f"Overlay v1:    NAVn={nav_ov['nav'].iloc[-1]:,.0f}  CAGR={c(bh0,nav_ov['nav'].iloc[-1])*100:.2f}%  units_end={nav_ov['units'].iloc[-1]:.1f}")
    print(f"Overlay v2:    NAVn={nav_v2['nav'].iloc[-1]:,.0f}  CAGR={c(bh0,nav_v2['nav'].iloc[-1])*100:.2f}%  units_end={nav_v2['units'].iloc[-1]:.1f}")
    print(f"cum option P&L always={nav_aw['option_pnl'].sum():,.0f}  v1={nav_ov['option_pnl'].sum():,.0f}  v2={nav_v2['option_pnl'].sum():,.0f}")
    itm_col = dfv["itm_at_exit"].fillna(False).astype(bool)
    for name, navdf in [("always", nav_aw), ("v1", nav_ov), ("v2", nav_v2)]:
        ex = navdf["executed"]
        print(f"ITM-at-exit [{name}] = {itm_col[ex].sum()}/{ex.sum()}  ({100*itm_col[ex].sum()/max(ex.sum(),1):.1f}%)")
    bh_path = LOT*dfv["spot_exit"].values
    def maxdd(path):
        peak = np.maximum.accumulate(path)
        return ((path-peak)/peak).min()
    print(f"maxDD(cycle-level) buyhold={maxdd(bh_path)*100:.1f}%  always={maxdd(nav_aw['nav'].values)*100:.1f}%  v1={maxdd(nav_ov['nav'].values)*100:.1f}%  v2={maxdd(nav_v2['nav'].values)*100:.1f}%")

    nav_ov.to_csv(f"{OUT}/nav_overlay_v1.csv", index=False)
    nav_aw.to_csv(f"{OUT}/nav_always.csv", index=False)
    nav_v2.to_csv(f"{OUT}/nav_overlay_v2.csv", index=False)

if __name__ == "__main__":
    main()
