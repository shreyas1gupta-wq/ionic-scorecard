"""B2-CARD: air-pocket leg-buyback overlay on S1 primary. Spec frozen @ 9e82e72 BEFORE run.
Baseline S1 vs overlay: buy back threatened leg at next close when spot crosses a low-OI strike
toward it and the leg trades >=1.10x entry. Bars: adopt iff +1.0 pt/day AND worst-10 +15 AND
SL-day mean improves; kill iff mean < baseline; else park.
"""
import datetime as dt
import json
import sys
import numpy as np, pandas as pd, pyarrow.parquet as pq
from pathlib import Path

ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
sys.path.insert(0, str(ROOT / "intraday_options_strategy" / "buying"))
import chain  # noqa: E402

OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/results/B2_AIRPOCKET_OVERLAY_20260711"
OUT.mkdir(parents=True, exist_ok=True)

spot = chain.load_index()
spot = spot[(spot.index.time >= dt.time(9, 15)) & (spot.index.time <= dt.time(15, 30))]
mapping, exps = chain.build_expiry_index()
spot_dates = pd.Series(spot.index.date, index=spot.index)

def leg_cost(ts):
    return 2.0 if ts.time() < dt.time(9, 30) else 1.0

rows = []
for exp in sorted(exps):
    day = exp
    sd = spot[spot_dates == day]
    if len(sd) < 100:
        continue
    try:
        df = pq.read_table(mapping[exp], columns=["timestamp", "strike", "option_type", "close",
                                                  "open_interest", "trading_day"]).to_pandas()
    except Exception as e:
        print(f"[skip] {exp}: {e}", flush=True); continue
    df = df[df["trading_day"] == str(day)]
    if not len(df):
        continue
    ts = pd.to_datetime(df["timestamp"])
    if getattr(ts.dt, "tz", None) is not None:
        ts = ts.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    df = df.assign(ts=ts)

    s_close = sd["close"]
    ent = s_close[s_close.index.time >= dt.time(9, 20)]
    if not len(ent):
        continue
    t0, sp0 = ent.index[0], ent.iloc[0]
    K = round(sp0 / 50) * 50

    legs = {}
    def ser(k, cp, col="close"):
        key = (float(k), cp, col)
        if key not in legs:
            s = df[(df.strike == float(k)) & (df.option_type == cp)].set_index("ts")[col].sort_index()
            legs[key] = s[~s.index.duplicated(keep="last")]
        return legs[key]

    ce = ser(K, "CE"); pe = ser(K, "PE")
    if t0 not in ce.index or t0 not in pe.index:
        e_ce = ce[ce.index >= t0]; e_pe = pe[pe.index >= t0]
        if not len(e_ce) or not len(e_pe):
            continue
        t0 = max(e_ce.index[0], e_pe.index[0])
    ce0 = ce.get(t0, np.nan); pe0 = pe.get(t0, np.nan)
    if np.isnan(ce0) or np.isnan(pe0):
        continue

    # OI snapshots every 30 min from 09:23, strikes within +-150 of spot at snapshot, 3-bar lag
    snaps = {}
    strikes_all = sorted(df.strike.unique())
    for h, m in [(9, 23), (9, 53), (10, 23), (10, 53), (11, 23), (11, 53), (12, 23),
                 (12, 53), (13, 23), (13, 53), (14, 23), (14, 53), (15, 23)]:
        st = pd.Timestamp(dt.datetime.combine(day, dt.time(h, m)))
        sp_now = s_close[s_close.index <= st]
        if not len(sp_now):
            continue
        spn = sp_now.iloc[-1]
        cand = [k for k in strikes_all if abs(k - spn) <= 150 and k % 50 == 0]
        oi = {}
        lag_t = st - pd.Timedelta(minutes=3)
        for k in cand:
            tot = 0.0
            for cp in ("CE", "PE"):
                s = ser(k, cp, "open_interest")
                s = s[s.index <= lag_t]
                if len(s):
                    tot += s.iloc[-1]
            oi[k] = tot
        if oi:
            med = np.median(list(oi.values()))
            snaps[st] = {k for k, v in oi.items() if v <= med}  # bottom-50% = air pockets

    def latest_snap(t):
        keys = [s for s in snaps if s <= t]
        return snaps[max(keys)] if keys else set()

    # walk both variants
    def run(overlay):
        pnl, det = 0.0, {}
        for cp, e_px, s_leg in [("CE", ce0, ce), ("PE", pe0, pe)]:
            win = s_leg[(s_leg.index > t0) & (s_leg.index.time <= dt.time(15, 25))]
            exit_px, exit_t, reason = (win.iloc[-1], win.index[-1], "settle") if len(win) else (e_px, t0, "none")
            sl_level = 1.30 * e_px
            prev_spot = sp0
            for tt, px in win.items():
                # SL
                if px >= sl_level:
                    after = win[win.index > tt]
                    exit_px, exit_t, reason = (after.iloc[0], after.index[0], "SL") if len(after) else (px, tt, "SL")
                    break
                if overlay and px >= 1.10 * e_px:
                    sp_now = s_close.get(tt, np.nan)
                    if not np.isnan(sp_now):
                        ap = latest_snap(tt)
                        crossed = [k for k in ap if (prev_spot < k <= sp_now) or (sp_now <= k < prev_spot)]
                        toward = any((k >= prev_spot and cp == "CE") or (k <= prev_spot and cp == "PE")
                                     for k in crossed) if crossed else False
                        if toward:
                            after = win[win.index > tt]
                            exit_px, exit_t, reason = (after.iloc[0], after.index[0], "AP") if len(after) else (px, tt, "AP")
                            break
                    prev_spot = s_close.get(tt, prev_spot)
                else:
                    prev_spot = s_close.get(tt, prev_spot)
            pnl += (e_px - exit_px) - leg_cost(t0) - (leg_cost(exit_t) if reason != "settle" else 1.0)
            det[cp] = reason
        return pnl, det

    base, bdet = run(False)
    over, odet = run(True)
    rows.append(dict(day=day, base=base, over=over,
                     base_sl=("SL" in bdet.values()), ap_trig=("AP" in odet.values())))
    if len(rows) % 50 == 0:
        print(f"...{len(rows)} days", flush=True)

r = pd.DataFrame(rows)
r.to_csv(OUT / "b2_days.csv", index=False)

def t_of(x):
    x = np.asarray(x, float)
    return x.mean() / (x.std(ddof=1) / np.sqrt(len(x)))

d_mean = r.over.mean() - r.base.mean()
w10_b = r.nsmallest(10, "base").base.mean()
w10_o = r.nsmallest(10, "over").over.mean()
sl_days = r[r.base_sl]
sl_impr = sl_days.over.mean() - sl_days.base.mean() if len(sl_days) else np.nan

adopt = (d_mean >= 1.0) and (w10_o - w10_b >= 15) and (sl_impr > 0)
kill = d_mean < 0
verdict = "ADOPT-CANDIDATE (shadow v1.1)" if adopt else ("KILL overlay" if kill else "PARK")

lines = [f"days={len(r)} | baseline mean {r.base.mean():+.2f} (t={t_of(r.base):.2f}) | overlay mean {r.over.mean():+.2f} (t={t_of(r.over):.2f})",
         f"delta mean {d_mean:+.2f} pts/day (bar i: >=+1.0)",
         f"worst-10: base {w10_b:.1f} -> overlay {w10_o:.1f} (delta {w10_o - w10_b:+.1f}; bar ii: >=+15)",
         f"SL-hit days n={len(sl_days)}: overlay delta {sl_impr:+.2f} (bar iii: >0)",
         f"AP triggers fired on {r.ap_trig.sum()} days ({r.ap_trig.mean()*100:.0f}%)",
         f"no-SL days overlay drag: {(r[~r.base_sl].over - r[~r.base_sl].base).mean():+.2f} pts/day",
         f"VERDICT: {verdict}"]
txt = "\n".join(lines)
print(txt)
(OUT / "RESULTS_RAW.txt").write_text(txt, encoding="utf-8")

card = {"card": "B2-CARD", "frozen_commit": "9e82e72", "run_ts": dt.datetime.now().isoformat(timespec="seconds"),
        "script": "b2_airpocket_overlay.py", "data": ["NIFTY 1-min option chain incl open_interest (3-bar lag)"],
        "n_obs": int(len(r)), "metrics": {"delta_mean": round(float(d_mean), 2),
        "worst10_delta": round(float(w10_o - w10_b), 1), "sl_day_delta": round(float(sl_impr), 2) if not np.isnan(sl_impr) else None},
        "validation": {"era_split": "see CSV", "bootstrap_ci95": None,
                       "lookahead_ast": "pre-flight run; OI 3-bar lag enforced in construction",
                       "one_day_lag": "n/a intraday"},
        "verdict": verdict, "bars_hit": [], "trials_increment": 1, "token_cost_agents": 0}
(OUT / "RUN_CARD.json").write_text(json.dumps(card, indent=1), encoding="utf-8")
print("RUN_CARD.json written", flush=True)
