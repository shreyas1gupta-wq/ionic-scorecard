"""POST-HOC robustness check on the best BUILD cell. NOT a pre-registered gate --
labelled as such in SUMMARY.md so it cannot be mistaken for one.

Two controls, both run through the same harness and the same cfg as the winner:
  LAG+1  : every signal timestamp moved to the NEXT trading day, same time-of-day.
           An edge that is really in the trigger should largely disappear; a result that
           survives the shift is a property of "buy an option at 11:00 on some day",
           not of the sweep.
  RANDOM : same count, same time-of-day mix, same direction mix, random trading days.

Writes placebo.json + a line for SUMMARY.md.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT))
import arm1_lib as L                                     # noqa: E402
import opt_pl as H                                       # noqa: E402

SEED = 20260730


def shift_days(sig: pd.DataFrame, sessions: list, k: int = 1) -> pd.DataFrame:
    pos = {d: i for i, d in enumerate(sessions)}
    rows = []
    for t0, dr, tg in zip(pd.to_datetime(sig["t"]), sig["direction"], sig["tag"]):
        i = pos.get(t0.date())
        if i is None or i + k >= len(sessions):
            continue
        nd = sessions[i + k]
        rows.append({"t": pd.Timestamp(nd) + pd.Timedelta(hours=t0.hour, minutes=t0.minute),
                     "direction": int(dr), "tag": f"{tg}_lag{k}"})
    return pd.DataFrame(rows)


def randomize(sig: pd.DataFrame, sessions: list, rng) -> pd.DataFrame:
    tods = [(t.hour, t.minute) for t in pd.to_datetime(sig["t"])]
    dirs = sig["direction"].tolist()
    rows = []
    for (hh, mm), dr in zip(tods, dirs):
        d = sessions[int(rng.integers(0, len(sessions)))]
        rows.append({"t": pd.Timestamp(d) + pd.Timedelta(hours=hh, minutes=mm),
                     "direction": int(dr), "tag": "random"})
    return pd.DataFrame(rows).sort_values("t").reset_index(drop=True)


if __name__ == "__main__":
    bc = json.loads((OUT / "best_config.json").read_text(encoding="utf-8"))
    lab = bc["best_label"]
    trig, dte, off, ex = lab.split("|")
    print(f"best build cell = {lab}")

    cells = dict(L.grid(trig) + L.probe_grid(trig))
    cfg = cells[lab]
    print(f"cfg: dte {cfg.min_dte}-{cfg.max_dte} offset {cfg.strike_offset} "
          f"hold {cfg.max_hold_days}d target {cfg.target_pct} stop {cfg.stop_pct} "
          f"trail {cfg.trail_pct} {cfg.expiry_handling}")

    sigs = L.build_signals()
    base = L.split(sigs[trig], L.BUILD_START, L.BUILD_END)
    sp = H.load_spot()
    sessions = sorted({d for d in sp.index.date})
    sessions_build = [d for d in sessions if L.BUILD_START <= d <= L.BUILD_END]

    need = L.needed_strikes(list(sigs.values()))
    lag1 = shift_days(base, sessions_build, 1)
    rng = np.random.default_rng(SEED)
    rnd = randomize(base, sessions_build, rng)
    # the shifted/random sets need their own strike coverage
    need2 = L.needed_strikes([lag1, rnd])
    for k, v in need2.items():
        need.setdefault(k, set()).update(v)
    L.install_global_store(needed=need, maxsize=70)

    res = {}
    for name, s in [("actual", base), ("lag+1_trading_day", lag1), ("random_days", rnd)]:
        tr = H.run_signals(s, cfg)
        fl = tr[tr.status == "filled"]
        rej = tr.loc[tr.status == "rejected", "reject_reason"].astype(str).value_counts().to_dict()
        m = L.metrics(fl, len(tr), rej, name)
        res[name] = m
        print(f"{name:22s} n={m['filled']:5d} net Rs.{m.get('net_total',float('nan')):+12,.0f} "
              f"gross Rs.{m.get('gross_total',float('nan')):+12,.0f} "
              f"ret/trade {m.get('ret_pct_net_mean',float('nan'))*100:+.2f}% "
              f"t(NW) {m.get('t_nw',float('nan')):+.2f} PF {m.get('pf_net',float('nan')):.2f}")
        fl.to_csv(OUT / f"placebo_{name.replace('+','p')}_trades.csv", index=False)

    (OUT / "placebo.json").write_text(json.dumps({"cell": lab, "results": res},
                                                 indent=1, default=str), encoding="utf-8")
    print("wrote placebo.json")
