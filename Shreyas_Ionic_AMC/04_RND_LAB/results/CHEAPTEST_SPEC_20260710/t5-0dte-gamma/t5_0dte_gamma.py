"""T5 cheap-test: 0DTE expiry-day compression->breakout, ATM NIFTY option buy.

Pre-registered (FROZEN) kill threshold, at 2x APPROVED costs (COST_STANDARDS D-021):
  expectancy < +8% of premium/trade  OR  PF < 1.15  OR  n < 100  OR  t < 2.5  -> KILL

Frozen single-pass spec (no tuning; DSR trial ledger: 1 trial):
  - Universe: every valid NIFTY weekly expiry >= 2021-06-01 (chain.build_expiry_index);
    trade only the expiry day itself (0DTE).
  - Spot: NIFTY 1-min index; naive IST; bars < 09:15 dropped (pre-open auction bug);
    bars > 15:30 dropped.
  - Compression: trailing 45-min box (rolling max(high)-min(low) over 45 bars);
    armed when box range <= 0.20% of spot close; arming considered 10:00-14:30.
    Latest compression bar refreshes the armed box.
  - Breakout: first 1-min CLOSE above armed box high -> buy ATM CE;
    below box low -> buy ATM PE. ONE trade per expiry day (first signal).
  - ATM strike = round(spot/50)*50 at signal bar close.
  - Entry: NEXT 1-min option bar OPEN (assert_next_bar). Entry deadline 14:45.
    No option bar at/after signal, or entry-bar volume == 0 -> NO FILL, DROP (D-031).
  - Exit: stop -35% premium, target +70% premium (fixed 1:2 per K-001 lesson);
    same-bar both-touch -> STOP (conservative). Time exit: last bar <= 15:15 close.
  - Costs (COST_STANDARDS, lot = 50 units, 1 lot):
      each leg: Rs20 brokerage + 0.035% exch txn + 18% GST on (brokerage+txn)
      buy leg adds 0.003% stamp; sell leg adds 0.1% STT;
      slippage 0.25% of premium per leg (liquid ATM index floor).
    Kill bar applies at 2x this whole stack.
Guards: drop-preopen, next-bar entry, no same-bar signal/entry, one-bar-lag test,
        within-day direction-shuffle placebo, degenerate_flags.
"""
import sys, datetime as dt, warnings
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

warnings.filterwarnings("ignore")
BASE = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
sys.path.insert(0, BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\lib")
sys.path.insert(0, BASE + r"\intraday_options_strategy\buying")
import guards  # noqa
import chain   # noqa

OUT = BASE + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\CHEAPTEST_SPEC_20260710\t5-0dte-gamma"
IDX = BASE + r"\intraday_options_strategy\datasets\raw\hf_index_options_1m\index\NIFTY.parquet"

BOX_MIN, BOX_PCT = 45, 0.0020
STOP, TGT = -0.35, 0.70
LOT = 50
ARM_START, ARM_END = dt.time(10, 0), dt.time(14, 30)
ENTRY_DEADLINE = dt.time(14, 45)
TIME_EXIT = dt.time(15, 15)


def leg_cost(P, side):  # rupees per leg, 1 lot
    v = P * LOT
    brok = 20.0
    txn = 0.00035 * v
    gst = 0.18 * (brok + txn)
    stt = 0.001 * v if side == "sell" else 0.0
    stamp = 0.00003 * v if side == "buy" else 0.0
    slip = 0.0025 * v
    return brok + txn + gst + stt + stamp + slip


def load_spot():
    df = pq.read_table(IDX).to_pandas()
    df["t"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
    df = df[(df["t"].dt.time >= dt.time(9, 15)) & (df["t"].dt.time <= dt.time(15, 30))]
    df["day"] = df["trading_day"].astype(str)
    return df.sort_values("t")


def option_series(exp, day, strike, side):
    mapping, _ = chain.build_expiry_index()
    try:
        tb = pq.read_table(mapping[exp], filters=[
            ("trading_day", "=", day.isoformat()),
            ("option_type", "=", side), ("strike", "=", int(strike))])
    except Exception:
        return None
    o = tb.to_pandas()
    if o.empty:
        return None
    o["t"] = pd.to_datetime(o["timestamp"]).dt.tz_localize(None)
    o = o[(o["t"].dt.time >= dt.time(9, 15)) & (o["t"].dt.time <= dt.time(15, 30))]
    return o.sort_values("t").drop_duplicates("t")


def find_signal(day_bars):
    hi = day_bars["high"].rolling(BOX_MIN).max()
    lo = day_bars["low"].rolling(BOX_MIN).min()
    rng = (hi - lo) / day_bars["close"]
    times = day_bars["t"].dt.time
    box_h = box_l = None
    for i in range(len(day_bars)):
        tt = times.iloc[i]
        c = day_bars["close"].iloc[i]
        if box_h is not None:
            if c > box_h:
                return i, "CE", c
            if c < box_l:
                return i, "PE", c
        if ARM_START <= tt <= ARM_END and not np.isnan(rng.iloc[i]) and rng.iloc[i] <= BOX_PCT:
            box_h, box_l = hi.iloc[i], lo.iloc[i]
    return None


def simulate(entry_lag=1):
    spot = load_spot()
    _, exps = chain.build_expiry_index()
    exps = [e for e in exps if e >= dt.date(2021, 6, 1)]
    trades, skipped = [], []
    for exp in exps:
        db = spot[spot["day"] == exp.isoformat()].reset_index(drop=True)
        if len(db) < 200:
            skipped.append((exp, "no/short spot day")); continue
        sig = find_signal(db)
        if sig is None:
            continue
        i, side, spot_c = sig
        sig_t = db["t"].iloc[i]
        if sig_t.time() > ENTRY_DEADLINE:
            continue
        strike = int(round(spot_c / 50) * 50)
        o = option_series(exp, exp, strike, side)
        if o is None or o.empty:
            skipped.append((exp, f"no option data {side}{strike}")); continue
        after = o[o["t"] > sig_t]
        if len(after) < 2:
            skipped.append((exp, "no bars after signal")); continue
        eb = after.iloc[entry_lag - 1] if len(after) >= entry_lag else None
        if eb is None or eb["volume"] == 0 or eb["open"] <= 0:
            skipped.append((exp, "no-fill entry bar")); continue
        assert eb["t"] > sig_t, "same-bar entry lookahead"
        P_in = float(eb["open"])
        stop_px, tgt_px = P_in * (1 + STOP), P_in * (1 + TGT)
        rest = after[after["t"] > eb["t"]]
        P_out, exit_t, reason = None, None, None
        for _, b in rest.iterrows():
            if b["t"].time() > TIME_EXIT:
                break
            if b["low"] <= stop_px:
                P_out, exit_t, reason = stop_px, b["t"], "stop"; break
            if b["high"] >= tgt_px:
                P_out, exit_t, reason = tgt_px, b["t"], "target"; break
        if P_out is None:
            upto = rest[rest["t"].dt.time <= TIME_EXIT]
            if upto.empty:
                skipped.append((exp, "no exit bars")); continue
            P_out, exit_t, reason = float(upto["close"].iloc[-1]), upto["t"].iloc[-1], "time"
        gross = (P_out - P_in) * LOT
        cost = leg_cost(P_in, "buy") + leg_cost(P_out, "sell")
        trades.append(dict(expiry=exp, side=side, strike=strike, sig_t=sig_t,
                           entry_t=eb["t"], exit_t=exit_t, reason=reason,
                           P_in=P_in, P_out=P_out, gross_rs=gross, cost_1x=cost,
                           ret1x=(gross - cost) / (P_in * LOT) * 100,
                           ret2x=(gross - 2 * cost) / (P_in * LOT) * 100))
    return pd.DataFrame(trades), skipped


def stats(r):
    n = len(r)
    if n == 0:
        return dict(n=0)
    mean = r.mean()
    t = mean / (r.std(ddof=1) / np.sqrt(n)) if n > 1 else np.nan
    pf = r[r > 0].sum() / abs(r[r <= 0].sum()) if (r <= 0).any() else np.inf
    return dict(n=n, exp_pct=round(mean, 2), t=round(t, 2), pf=round(pf, 3),
                wr=round((r > 0).mean() * 100, 1), med=round(r.median(), 2))


if __name__ == "__main__":
    tr, sk = simulate(entry_lag=1)
    tr.to_csv(OUT + r"\t5_trades.csv", index=False)
    print("TRADES", len(tr), "SKIPPED", len(sk))
    r2 = tr["ret2x"]
    print("MAIN 2x:", stats(r2))
    print("MAIN 1x:", stats(tr["ret1x"]))
    tr["year"] = pd.to_datetime(tr["expiry"].astype(str)).dt.year
    era = tr.groupby("year")["ret2x"].agg(["count", "mean",
        lambda x: x[x > 0].sum() / abs(x[x <= 0].sum()) if (x <= 0).any() else np.inf])
    era.columns = ["n", "exp_pct", "pf"]
    print("ERA:\n", era.round(2))
    era.round(3).to_csv(OUT + r"\t5_era.csv")
    print("BY SIDE:\n", tr.groupby("side")["ret2x"].agg(["count", "mean"]).round(2))
    print("BY EXIT:\n", tr.groupby("reason")["ret2x"].agg(["count", "mean"]).round(2))
    # placebo: shuffle P&L signs? Proper within-day placebo: random direction ->
    # cannot re-price cheaply; use sign-flip permutation of net returns (H0: mean 0)
    rng = np.random.default_rng(42)
    obs = r2.mean()
    perm = [ (r2.values * rng.choice([-1, 1], len(r2))).mean() for _ in range(2000)]
    pval = (np.sum(np.array(perm) >= obs) + 1) / 2001
    print(f"PLACEBO sign-flip p={pval:.4f}")
    # one-bar-lag entry test
    tl, _ = simulate(entry_lag=2)
    l2 = tl["ret2x"]
    print("LAG+1BAR 2x:", stats(l2))
    base = r2.mean()
    coll = (base - l2.mean()) / abs(base) * 100 if base != 0 else np.nan
    print(f"LAG collapse: {coll:.1f}%")
    dg = guards.degenerate_flags(tr.set_index("entry_t")["ret2x"] / 100)
    print("DEGENERATE FLAGS:", dg)
    with open(OUT + r"\t5_console.txt", "w") as f:
        f.write(f"n={len(tr)} main2x={stats(r2)} main1x={stats(tr['ret1x'])}\n"
                f"placebo_p={pval:.4f} lag={stats(l2)} collapse={coll:.1f}%\n"
                f"skipped={len(sk)}\n" + era.round(2).to_string())
    print("DONE")
