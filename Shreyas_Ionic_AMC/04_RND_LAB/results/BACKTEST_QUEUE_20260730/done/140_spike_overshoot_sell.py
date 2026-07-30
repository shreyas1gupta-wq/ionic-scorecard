"""
140_spike_overshoot_sell.py -- Vikram Shah, 2026-07-30.

FULL backtest for the Principal's SPIKE_OVERSHOOT_SELL mandate. Reuses the event list
written by 135_spike_overshoot_measure.py (events_raw.csv) so trigger detection is not
redone; re-touches each event's option chain (needed for forward-looking HIGH/exit prices
that 135 did not compute). Self-contained, argument-free; loops the option chain -> queued.

Delivers: entry-mechanism head-to-head (market-next-bar vs resting sell-limit, Principal's
market-making idea), 4 structures (naked/vertical-near/vertical-far/delta-neutral) with
dynamic 10%/5% margin, exact P&L decomposition (vol-crush vs directional+theta), mean-
reversion & capture probabilities with Wilson CIs, tail (named crisis dates + worst trade),
build/held-out + pre/post-Oct-2024 splits, regime-conditional buckets (ALL reported, with n),
and the frequency-dependent robustness gate (top-decile-exclusion OR cost-stress).

Spec: SPIKE_OVERSHOOT_SELL_20260730/PRE_REGISTRATION.md.
"""
from __future__ import annotations

import datetime as dt
import gc
import sys
import time
import traceback
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/SPIKE_OVERSHOOT_SELL_20260730"
OUT.mkdir(parents=True, exist_ok=True)
LOG: list[str] = []


def log(msg):
    print(msg, flush=True)
    LOG.append(str(msg))


t_start = time.time()
R = 0.065
LOT = 75
COST_PER_LOT_SIDE = 25.0          # Rs25/lot/side/leg, SHARED_CONTEXT authoritative
FUT_RT_COST_PTS = 5.5             # mid of 5.0-6.5pt futures round-trip range
TICK = 0.05
X_VALUES = (2.0, 3.0, 5.0, 8.0)
HOLDS_MIN = (5, 15, 30, 60)       # + same-day close handled separately
MAX_WAIT_MIN = 30                 # resting-limit max wait before DROP (D-031 no-fill=drop)
WING_NEAR, WING_FAR = 150.0, 300.0
CRISIS_DATES = {"2021-11-26", "2022-02-24", "2024-06-04"}


# ---------------------------------------------------------------- vectorized BS (validated)
def bs_price_vec(is_call, S, K, T, r, sigma):
    S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, float), 1e-4)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    put = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return np.where(is_call, call, put)


def bs_delta_vec(is_call, S, K, T, r, sigma):
    S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.maximum(np.asarray(sigma, float), 1e-4)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    return np.where(is_call, norm.cdf(d1), norm.cdf(d1) - 1)


def bs_iv_scalar_arr(price, is_call, S, K, T, r, n_iter=60):
    price = np.asarray(price, float); S = np.asarray(S, float); K = np.asarray(K, float)
    T = np.maximum(np.asarray(T, float), 1e-6)
    sigma = np.full_like(price, 0.20, dtype=float)
    for _ in range(n_iter):
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        vega = S * norm.pdf(d1) * np.sqrt(T)
        model = bs_price_vec(is_call, S, K, T, r, sigma)
        vega_safe = np.where(vega < 1e-8, 1e-8, vega)
        step = np.clip((model - price) / vega_safe, -0.5, 0.5)
        sigma = np.clip(sigma - step, 0.01, 3.0)
    return sigma


def wilson_ci(k, n, z=1.96):
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z ** 2 / n
    center = (p + z ** 2 / (2 * n)) / denom
    half = (z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2))) / denom
    return (center - half, center + half)


# ---------------------------------------------------------------- phase 0: load events + daily regime series
log("[phase0] loading events_raw.csv from 135 + building daily regime series")
ev_path = OUT / "events_raw.csv"
if not ev_path.exists():
    log("FATAL: events_raw.csv not found -- 135 must run first / did not complete.")
    sys.exit(1)
ev_df = pd.read_csv(ev_path, parse_dates=["t0"])
ev_df["day"] = pd.to_datetime(ev_df["day"]).dt.date
ev_df["expiry"] = pd.to_datetime(ev_df["expiry"]).dt.date
log(f"[phase0] {len(ev_df)} events loaded, {ev_df['expiry'].nunique()} distinct expiries")

idx = chain.load_index()
idx = idx[idx.index.time >= dt.time(9, 15)].copy()
idx["day"] = idx.index.date
spot_lookup = idx["close"].to_dict()

# daily close series (session close = last bar of the day) for 20/50DMA + RSI14
daily_close = idx.groupby("day")["close"].last().sort_index()
ma20 = daily_close.rolling(20, min_periods=20).mean().shift(1)   # causal: excludes today
ma50 = daily_close.rolling(50, min_periods=50).mean().shift(1)
delta_d = daily_close.diff()
gain = delta_d.clip(lower=0).rolling(14, min_periods=14).mean()
loss = (-delta_d.clip(upper=0)).rolling(14, min_periods=14).mean()
rs = gain / loss.replace(0, np.nan)
rsi14 = (100 - 100 / (1 + rs)).shift(1)                          # causal: prior day's RSI
prior_close = daily_close.shift(1)

regime_by_day = pd.DataFrame({
    "px_above_20dma": (prior_close > ma20),
    "px_above_50dma": (prior_close > ma50),
    "rsi14": rsi14,
}).reindex(sorted(daily_close.index))
regime_by_day["rsi_bucket"] = pd.cut(regime_by_day["rsi14"], [-1, 30, 70, 101],
                                      labels=["oversold<30", "neutral30-70", "overbought>70"])

ev_df = ev_df.merge(regime_by_day, left_on="day", right_index=True, how="left")

# IV-percentile proxy: trailing-100-prior-events median of iv_pre (built once we compute iv_pre
# below in phase 1 -- placeholder merge happens after phase1 produces per-event iv_pre/iv_obs).

# ---------------------------------------------------------------- phase 1: per-event trade construction
log("[phase1] building trades per event, batched by expiry (memory-safe)")
trades = []
by_exp = ev_df.groupby("expiry")
n_exp_done = 0
n_events_total = len(ev_df)

for exp, sub in by_exp:
    try:
        df = chain.load_expiry(exp)
        wide_close = df.pivot_table(index="t", columns=["option_type", "strike"], values="close")
        wide_high = df.pivot_table(index="t", columns=["option_type", "strike"], values="high")
        wide_vol = df.pivot_table(index="t", columns=["option_type", "strike"], values="volume")
        wide_open = df.pivot_table(index="t", columns=["option_type", "strike"], values="open")
        wide_close_m = wide_close.where(wide_vol > 0)
        wide_open_m = wide_open.where(wide_vol > 0)
        expiry_dt = pd.Timestamp(exp) + pd.Timedelta(hours=15, minutes=30)
        times = wide_close_m.index
        times_arr = times.to_numpy()

        for _, ev in sub.iterrows():
            t0 = ev["t0"]
            if t0 not in times:
                continue
            S0 = ev["S0"]
            pre_win = wide_close_m.loc[(times >= t0 - pd.Timedelta(minutes=10)) & (times < t0)]
            if len(pre_win) < 3:
                continue
            pre_mean = pre_win.mean(skipna=True).dropna()
            obs_row = wide_close_m.loc[t0].dropna()
            common = pre_mean.index.intersection(obs_row.index)
            if len(common) == 0:
                continue
            strikes = common.get_level_values("strike").to_numpy(dtype=float)
            types = common.get_level_values("option_type").to_numpy()
            is_call = (types == "CE")
            T0 = (expiry_dt - t0) / pd.Timedelta(days=365)
            if T0 <= 1e-6:
                continue
            Sarr = np.full(len(strikes), S0)
            Tarr = np.full(len(strikes), T0)
            pre_px = pre_mean.loc[common].to_numpy(dtype=float)
            obs_px = obs_row.loc[common].to_numpy(dtype=float)
            valid = (pre_px > 0.05) & (obs_px > 0.05)
            if valid.sum() == 0:
                continue
            iv_pre_v = bs_iv_scalar_arr(pre_px[valid], is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R)
            iv_obs_v = bs_iv_scalar_arr(obs_px[valid], is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R)
            delta_signed = np.where(is_call[valid], 1, -1) * bs_delta_vec(
                is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R, iv_obs_v)
            delta_signed = np.where(is_call[valid],
                                     bs_delta_vec(is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R, iv_obs_v),
                                     bs_delta_vec(is_call[valid], Sarr[valid], strikes[valid], Tarr[valid], R, iv_obs_v))
            band = (np.abs(delta_signed) >= 0.20) & (np.abs(delta_signed) <= 0.40)
            same_side = np.where(ev["direction"] == "up", is_call[valid], ~is_call[valid])
            cand = band & same_side  # trade the side the move actually went, per Principal's framing
            if cand.sum() == 0:
                continue
            # pick strike closest to 0.30 |delta| among candidates
            cidx = np.where(cand)[0]
            pick = cidx[np.argmin(np.abs(np.abs(delta_signed[cidx]) - 0.30))]

            K = strikes[valid][pick]
            typ = types[valid][pick]
            iv_pre = iv_pre_v[pick]
            iv_obs = iv_obs_v[pick]
            d_obs = delta_signed[pick]
            fair_value_t0 = bs_price_vec(is_call[valid][pick:pick + 1], Sarr[valid][pick:pick + 1],
                                          strikes[valid][pick:pick + 1], Tarr[valid][pick:pick + 1],
                                          R, np.array([iv_pre]))[0]
            excess_t0 = obs_px[valid][pick] - fair_value_t0
            rv30_ann = ev["rv30"] * np.sqrt(375 * 252) if pd.notna(ev["rv30"]) and ev["rv30"] > 0 else np.nan
            iv_rv_ratio = (iv_obs / rv30_ann) if (rv30_ann and rv30_ann > 0) else np.nan

            col = (typ, K)
            if col not in wide_close_m.columns:
                continue

            # ---- forward path for this strike from t0 onward (bounded to day/expiry window)
            fwd_mask = times > t0
            fwd_times = times[fwd_mask]
            if len(fwd_times) == 0:
                continue
            fwd_close = wide_close_m[col].reindex(times).loc[fwd_times]
            fwd_open = wide_open_m[col].reindex(times).loc[fwd_times]
            fwd_high_raw = wide_high[col].reindex(times).loc[fwd_times]  # unmasked: HIGH exists even if vol col NaN elsewhere
            fwd_vol = wide_vol[col].reindex(times).loc[fwd_times]

            # market-next-bar entry: first bar after t0 with volume>0, within 5 bars
            mkt_entry_time, mkt_entry_px = None, np.nan
            for j in range(min(5, len(fwd_times))):
                tt = fwd_times[j]
                if fwd_vol.loc[tt] > 0 and pd.notna(fwd_open.loc[tt]):
                    mkt_entry_time, mkt_entry_px = tt, fwd_open.loc[tt]
                    break

            # resting sell-limit entries per X, with/without haircut
            limit_fills = {}
            wait_times = fwd_times[fwd_times <= t0 + pd.Timedelta(minutes=MAX_WAIT_MIN)]
            for X in X_VALUES:
                limit_px = fair_value_t0 + X
                filled_t, filled_haircut_t = None, None
                for tt in wait_times:
                    if fwd_vol.loc[tt] <= 0 or pd.isna(fwd_high_raw.loc[tt]):
                        continue
                    hi = fwd_high_raw.loc[tt]
                    if filled_t is None and hi >= limit_px:
                        filled_t = tt
                    if filled_haircut_t is None and hi >= limit_px + TICK:
                        filled_haircut_t = tt
                    if filled_t is not None and filled_haircut_t is not None:
                        break
                limit_fills[X] = (filled_t, filled_haircut_t, limit_px)

            def get_exit(entry_time, hold_min):
                """Open of first volume>0 bar at/after entry_time+hold_min (within 5-bar search),
                else NaN (drop for this horizon)."""
                target = entry_time + pd.Timedelta(minutes=hold_min)
                after = fwd_times[fwd_times >= target]
                for j in range(min(5, len(after))):
                    tt = after[j]
                    if fwd_vol.loc[tt] > 0 and pd.notna(fwd_open.loc[tt]):
                        return tt, fwd_open.loc[tt]
                return None, np.nan

            def get_close_exit(entry_time, day):
                """Last volume>0 bar of the trading day."""
                same_day = fwd_times[pd.Series(fwd_times).dt.date.values == day]
                for tt in same_day[::-1]:
                    if fwd_vol.loc[tt] > 0 and pd.notna(fwd_close.loc[tt]):
                        return tt, fwd_close.loc[tt]
                return None, np.nan

            # wing strikes for vertical spreads (further OTM, same type)
            step_dir = 1 if typ == "CE" else -1

            def wing_price(offset, when_t):
                Kw = K + step_dir * offset
                colw = (typ, round(Kw / 50) * 50)
                if colw not in wide_open_m.columns:
                    return np.nan
                try:
                    v = wide_vol[colw].reindex(times).loc[when_t]
                    if v is None or (isinstance(v, float) and pd.isna(v)) or v <= 0:
                        return np.nan
                    return wide_open_m[colw].reindex(times).loc[when_t]
                except Exception:
                    return np.nan

            base_rec = dict(
                event_id=ev["event_id"], day=ev["day"], expiry=exp, dte=ev["dte"], dte_band=ev["dte_band"],
                era=ev["era"], split=ev["split"], trigA=ev["trigA"], trigB=ev["trigB"], z15=ev["z15"],
                rv30=ev["rv30"], direction=ev["direction"], option_type=typ, strike=K, delta_obs=d_obs,
                iv_pre=iv_pre, iv_obs=iv_obs, iv_rv_ratio=iv_rv_ratio, excess_t0=excess_t0, S0=S0,
                px_above_20dma=ev.get("px_above_20dma"), px_above_50dma=ev.get("px_above_50dma"),
                rsi_bucket=ev.get("rsi_bucket"),
            )

            entry_variants = []
            if mkt_entry_time is not None:
                entry_variants.append(("market", np.nan, mkt_entry_time, mkt_entry_px, False))
            for X, (ft, fth, lim) in limit_fills.items():
                if ft is not None:
                    entry_variants.append((f"limit_X{X}", X, ft, lim, False))
                if fth is not None:
                    entry_variants.append((f"limit_X{X}_haircut", X, fth, lim, True))

            for method, Xval, entry_time, entry_px, haircut in entry_variants:
                S_entry = spot_lookup.get(entry_time, np.nan)
                T_entry = (expiry_dt - entry_time) / pd.Timedelta(days=365)
                fv_entry = bs_price_vec(np.array([typ == "CE"]), np.array([S_entry]), np.array([K]),
                                         np.array([max(T_entry, 1e-6)]), R, np.array([iv_pre]))[0] \
                    if pd.notna(S_entry) else np.nan
                excess_entry = entry_px - fv_entry if pd.notna(fv_entry) else np.nan

                for hold in list(HOLDS_MIN) + ["close"]:
                    if hold == "close":
                        exit_time, exit_px = get_close_exit(entry_time, ev["day"])
                    else:
                        exit_time, exit_px = get_exit(entry_time, hold)
                    if exit_time is None or pd.isna(exit_px):
                        continue
                    S_exit = spot_lookup.get(exit_time, np.nan)
                    T_exit = (expiry_dt - exit_time) / pd.Timedelta(days=365)
                    if pd.isna(S_exit) or T_exit <= 0:
                        continue
                    fv_exit = bs_price_vec(np.array([typ == "CE"]), np.array([S_exit]), np.array([K]),
                                            np.array([max(T_exit, 1e-6)]), R, np.array([iv_pre]))[0]
                    excess_exit = exit_px - fv_exit
                    naked_pnl_gross = entry_px - exit_px      # short: sell high, buy back low = profit
                    cost_naked = 2 * COST_PER_LOT_SIDE / LOT
                    naked_pnl_net = naked_pnl_gross - cost_naked
                    vol_crush = excess_entry - excess_exit
                    directional_theta = fv_entry - fv_exit
                    # sanity: vol_crush + directional_theta should equal naked_pnl_gross (exact identity)

                    delta_hedge_pnl = d_obs * (S_exit - S_entry)
                    hedge_cost = FUT_RT_COST_PTS * abs(d_obs)
                    dn_pnl_net = naked_pnl_gross + delta_hedge_pnl - cost_naked - hedge_cost

                    wing_near_entry = wing_price(WING_NEAR, entry_time)
                    wing_near_exit = wing_price(WING_NEAR, exit_time)
                    wing_far_entry = wing_price(WING_FAR, entry_time)
                    wing_far_exit = wing_price(WING_FAR, exit_time)
                    cost_vert = 4 * COST_PER_LOT_SIDE / LOT
                    vert_near_pnl = np.nan
                    if pd.notna(wing_near_entry) and pd.notna(wing_near_exit):
                        vert_near_pnl = (entry_px - wing_near_entry) - (exit_px - wing_near_exit) - cost_vert
                    vert_far_pnl = np.nan
                    if pd.notna(wing_far_entry) and pd.notna(wing_far_exit):
                        vert_far_pnl = (entry_px - wing_far_entry) - (exit_px - wing_far_exit) - cost_vert

                    notional = S_entry * LOT
                    rec = dict(base_rec)
                    rec.update(dict(
                        entry_method=method, X=Xval, haircut=haircut, entry_time=entry_time,
                        entry_px=entry_px, exit_time=exit_time, exit_px=exit_px, hold=str(hold),
                        S_entry=S_entry, S_exit=S_exit,
                        naked_pnl_pts=naked_pnl_net, vol_crush_pts=vol_crush,
                        directional_theta_pts=directional_theta,
                        dn_pnl_pts=dn_pnl_net, vert_near_pnl_pts=vert_near_pnl, vert_far_pnl_pts=vert_far_pnl,
                        margin_naked=0.10 * notional, margin_hedged=0.05 * notional,
                        crisis_day=str(ev["day"]) in CRISIS_DATES,
                    ))
                    trades.append(rec)
        n_exp_done += 1
    except Exception as e:
        log(f"[phase1] expiry {exp} FAILED: {e}")
        log(traceback.format_exc(limit=4))
    finally:
        chain.load_expiry.cache_clear()
        gc.collect()
    if n_exp_done % 25 == 0:
        log(f"[phase1] ...{n_exp_done}/{len(by_exp)} expiries, {len(trades)} trade-rows, "
            f"{time.time()-t_start:.0f}s elapsed")

tr = pd.DataFrame(trades)
tr.to_csv(OUT / "trades_full.csv", index=False)
log(f"[phase1] DONE: {len(tr)} trade-rows from {n_exp_done} expiries, {time.time()-t_start:.0f}s")

if len(tr) == 0:
    (OUT / "SUMMARY.md").write_text("NO TRADES CONSTRUCTED -- see log.\n\n" + "\n".join(LOG), encoding="utf-8")
    sys.exit(0)

# ============================================================== phase 2: aggregate reporting
def rupees(pts):
    return pts * LOT


def summarize(s, label):
    s = s.dropna()
    n = len(s)
    if n == 0:
        return f"{label}: n=0"
    win = (s > 0).mean()
    return (f"{label}: n={n} mean={s.mean():.2f}pt net_Rs={rupees(s.sum()):,.0f} "
            f"win%={win*100:.1f} worst={s.min():.2f}pt best={s.max():.2f}pt")


lines = ["# SPIKE_OVERSHOOT_SELL -- FULL BACKTEST SUMMARY", ""]
lines.append(f"Total trade-rows (all entry-method x holding-period x structure combos): {len(tr)}")
lines.append(f"Distinct events with >=1 constructed trade: {tr['event_id'].nunique()}")
lines.append("")

# ---- headline: entry mechanism head-to-head, primary hold=30min, no haircut, naked structure
lines.append("## HEADLINE 1: entry mechanism head-to-head (naked structure, hold=30min)")
h30 = tr[tr["hold"] == "30"]
mkt30 = h30[h30["entry_method"] == "market"]["naked_pnl_pts"]
lines.append(summarize(mkt30, "market-next-bar"))
n_events_all = ev_df.shape[0]
for X in X_VALUES:
    for hc, tag in [(False, ""), (True, "_haircut")]:
        col = h30[(h30["entry_method"] == f"limit_X{X}{tag}")]
        s = col["naked_pnl_pts"]
        fill_rate = len(col) / n_events_all if n_events_all else np.nan
        lines.append(f"limit X={X}{tag}: fill_rate~{fill_rate*100:.1f}% (of all events) | " +
                     summarize(s, "pnl"))
lines.append("")

# ---- P&L decomposition (naked, hold=30min, market entry)
lines.append("## HEADLINE 2: P&L decomposition -- vol-crush vs directional+theta (naked, mkt entry, hold=30min)")
d = mkt30 if False else h30[h30["entry_method"] == "market"]
vc = d["vol_crush_pts"].dropna()
dth = d["directional_theta_pts"].dropna()
lines.append(f"vol_crush: n={len(vc)} mean={vc.mean():.2f}pt sum_Rs={rupees(vc.sum()):,.0f}")
lines.append(f"directional_theta: n={len(dth)} mean={dth.mean():.2f}pt sum_Rs={rupees(dth.sum()):,.0f}")
tot = d["naked_pnl_pts"].dropna()
lines.append(f"total net (incl costs): n={len(tot)} mean={tot.mean():.2f}pt sum_Rs={rupees(tot.sum()):,.0f}")
lines.append("")

# ---- structures head-to-head (market entry, hold=30min), return on margin
lines.append("## HEADLINE 3: structures (market entry, hold=30min) -- P&L and return-on-margin")
for col, marg, name in [("naked_pnl_pts", "margin_naked", "Naked directional (10% margin)"),
                         ("vert_near_pnl_pts", "margin_hedged", f"Vertical near-wing ({WING_NEAR}pt, 5% margin)"),
                         ("vert_far_pnl_pts", "margin_hedged", f"Vertical far-wing ({WING_FAR}pt, 5% margin)"),
                         ("dn_pnl_pts", "margin_hedged", "Delta-neutral vol trade (5% margin)")]:
    sub = d[[col, marg]].dropna()
    if len(sub) == 0:
        lines.append(f"{name}: n=0")
        continue
    rom = rupees(sub[col]) / sub[marg]
    lines.append(f"{name}: n={len(sub)} mean_pnl={sub[col].mean():.2f}pt sum_Rs={rupees(sub[col].sum()):,.0f} "
                 f"mean_RoM={rom.mean()*100:.2f}% win%={(sub[col]>0).mean()*100:.1f}")
lines.append("")

# ---- probabilities with Wilson CIs
lines.append("## HEADLINE 4: probabilities (naked, mkt entry, hold=30min)")
n_mr = len(vc.dropna())
k_mr = int((vc > 0).sum())
lo, hi = wilson_ci(k_mr, n_mr)
lines.append(f"P(capture excess / vol-crush positive) = {k_mr}/{n_mr} = {k_mr/n_mr*100:.1f}% "
             f"[95% CI {lo*100:.1f}-{hi*100:.1f}%]" if n_mr else "P(capture excess): n=0")
n_dr = len(tot)
k_dr = int((tot > 0).sum())
lo2, hi2 = wilson_ci(k_dr, n_dr)
lines.append(f"P(trade net-positive) = {k_dr}/{n_dr} = {k_dr/n_dr*100:.1f}% "
             f"[95% CI {lo2*100:.1f}-{hi2*100:.1f}%]" if n_dr else "P(trade net-positive): n=0")
lines.append("")

# ---- tail
lines.append("## HEADLINE 5: TAIL -- the whole risk here")
worst = tot.min() if len(tot) else np.nan
avg_win = tot[tot > 0].mean() if (tot > 0).any() else np.nan
lines.append(f"Worst single trade: {worst:.2f}pt = Rs{rupees(worst):,.0f} (naked, 1 lot)")
lines.append(f"Average winning trade: {avg_win:.2f}pt = Rs{rupees(avg_win):,.0f}")
if pd.notna(worst) and pd.notna(avg_win) and avg_win != 0:
    lines.append(f"Worst-loss / average-gain ratio: {abs(worst/avg_win):.1f}x")
for pct in (1, 5, 10, 50, 90, 95, 99):
    lines.append(f"  p{pct}: {tot.quantile(pct/100):.2f}pt")
lines.append("")
lines.append("### Named crisis dates")
for cd in sorted(CRISIS_DATES):
    csub = d[d["day"].astype(str) == cd]
    if len(csub):
        lines.append(f"- {cd}: {len(csub)} trade(s), naked pnl sum={csub['naked_pnl_pts'].sum():.2f}pt "
                     f"(worst {csub['naked_pnl_pts'].min():.2f}pt)")
    else:
        lines.append(f"- {cd}: NO triggering event / no tradeable strike that day")
lines.append("### >2.5-sigma events (severe moves)")
sev = d[d["z15"].abs() >= 2.5]
if len(sev):
    lines.append(f"n={len(sev)} naked pnl mean={sev['naked_pnl_pts'].mean():.2f}pt "
                 f"worst={sev['naked_pnl_pts'].min():.2f}pt win%={(sev['naked_pnl_pts']>0).mean()*100:.1f}")
else:
    lines.append("n=0")
lines.append("")

# ---- splits
lines.append("## HEADLINE 6: splits (build vs held-out 2026; pre/post Oct-2024)")
for key, name in [("split", "build/held-out"), ("era", "pre/post-Oct-2024")]:
    for val in d[key].dropna().unique():
        s = d[d[key] == val]["naked_pnl_pts"]
        lines.append(summarize(s, f"{name}={val}"))
lines.append("")

# ---- regime conditioning (ALL buckets, with n)
lines.append("## HEADLINE 7: regime conditioning (ALL buckets, naked/mkt/hold30, era-consistency check)")
cond_cols = ["trigA", "trigB", "px_above_20dma", "px_above_50dma", "rsi_bucket"]
for c in cond_cols:
    lines.append(f"### {c}")
    for val, grp in d.groupby(c, dropna=False):
        row = [f"n={len(grp)}"]
        s_all = grp["naked_pnl_pts"]
        row.append(f"all={s_all.mean():.2f}pt" if len(s_all) else "all=NA")
        for era in ["pre_Oct2024", "post_Oct2024"]:
            se = grp[grp["era"] == era]["naked_pnl_pts"]
            row.append(f"{era}={se.mean():.2f}pt(n={len(se)})" if len(se) else f"{era}=n=0")
        lines.append(f"  {val}: " + " | ".join(row))
lines.append("")
lines.append("### IV/RV ratio at spike (tertiles)")
if d["iv_rv_ratio"].notna().sum() > 3:
    terts = pd.qcut(d["iv_rv_ratio"], 3, duplicates="drop")
    for val, grp in d.groupby(terts, observed=True):
        lines.append(f"  {val}: n={len(grp)} mean_pnl={grp['naked_pnl_pts'].mean():.2f}pt "
                     f"mean_ratio={grp['iv_rv_ratio'].mean():.2f}")
else:
    lines.append("  insufficient data")
lines.append("")

# ---- robustness gate (frequency-dependent)
lines.append("## HEADLINE 8: robustness gate (frequency-dependent, Principal-corrected)")
n_primary = len(tot)
lines.append(f"n(primary cell, naked/mkt/hold30) = {n_primary}")
if n_primary < 100:
    lines.append("LOW n -> applying TOP-DECILE-EXCLUSION gate")
    srt = tot.sort_values(ascending=False)
    for pct in (0.05, 0.10, 0.20):
        k = max(1, int(len(srt) * pct))
        rest = srt.iloc[k:]
        lines.append(f"  ex-top-{int(pct*100)}%: net_Rs={rupees(rest.sum()):,.0f} "
                     f"(vs headline {rupees(tot.sum()):,.0f}) -> "
                     f"{'PASS' if rest.sum() > 0 else 'FAIL'}")
else:
    lines.append("HIGH n -> applying COST-STRESS gate")
    cost_naked = 2 * COST_PER_LOT_SIDE / LOT
    gross = tot + cost_naked  # add back the 1x cost already netted, to get gross
    for mult in (1.0, 1.5, 2.0, 3.0):
        stressed = gross - cost_naked * mult
        lines.append(f"  {mult}x cost: net_Rs={rupees(stressed.sum()):,.0f} "
                     f"win%={(stressed>0).mean()*100:.1f}")
    # breakeven multiple via simple search
    lo_m, hi_m = 0.5, 20.0
    for _ in range(40):
        mid = (lo_m + hi_m) / 2
        val = (gross - cost_naked * mid).sum()
        if val > 0:
            lo_m = mid
        else:
            hi_m = mid
    lines.append(f"  breakeven cost multiple ~ {lo_m:.2f}x")
lines.append("")

# ---- trials count
n_trials = len(X_VALUES) * 2 * len(HOLDS_MIN + (1,) if False else HOLDS_MIN) * 4  # rough, documented below
lines.append("## Trials logged this mandate")
lines.append(f"Entry variants tested: market + {len(X_VALUES)} X-values x 2 (haircut/no) = "
             f"{1+len(X_VALUES)*2}. Holding periods: {len(HOLDS_MIN)+1}. Structures: 4. "
             f"Conditioning cuts reported: {len(cond_cols)+1}. "
             f"Firm cumulative before this mandate: 466 (see OVERFIT_AUDIT_20260729/TRIALS_LEDGER.csv).")
lines.append("")
lines.append("## Run log tail")
lines.extend(LOG[-50:])

(OUT / "SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")
log(f"[phase2] SUMMARY.md written. Total runtime {time.time()-t_start:.0f}s. 140 complete.")
