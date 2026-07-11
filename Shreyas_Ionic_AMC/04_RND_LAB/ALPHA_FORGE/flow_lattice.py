"""V1 FLOW LATTICE (thesis, frozen @ 5e49c26): pre-registered 144-cell FAMILY over participant-OI.
{FII,DII,Pro,Client} x {futnet, callnet, putnet, call-minus-put} x {rank-level, 1d-flow, 5d-flow} x fwd {1,3,5}d.
Construction LOCKED to B1b (rolling-252 pct-rank, T+1 close entry, q5-q1 spread). Discovery on the LONG
window 2019-2024-06 with BH-FDR(10%); confirmation 2024-07..2026-06 same-sign t>=1.5; then flow-shuffle placebo.
Full denominator logged. No per-cell tuning.
"""
import datetime as dt
import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(53)
ROOT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500")
OUT = ROOT / "Shreyas_Ionic_AMC/04_RND_LAB/ALPHA_FORGE"

poi = pd.read_parquet(ROOT / "Shreyas_Ionic_AMC/05_DATA_OFFICE/data/participant_oi/participant_oi_normalized.parquet")
sp = pd.read_csv(ROOT / "intraday_options_strategy/datasets/raw/kaggle/debashis74017__nifty-50-minute-data/NIFTY 50_minute.csv",
                 parse_dates=["date"]).set_index("date").sort_index()
sp = sp[(sp.index.time >= dt.time(9, 15)) & (sp.index.time <= dt.time(15, 25))]
close = sp["close"].groupby(pd.Series(sp.index.date, index=sp.index)).last()
tdays = sorted(close.index)
pos = {dd: i for i, dd in enumerate(tdays)}

ACTORS = ["FII", "DII", "Pro", "Client"]
def measures(g):
    return {"futnet": g["Future Index Long"] - g["Future Index Short"],
            "callnet": g["Option Index Call Long"] - g["Option Index Call Short"],
            "putnet": g["Option Index Put Long"] - g["Option Index Put Short"],
            "cmp": (g["Option Index Call Long"] - g["Option Index Call Short"])
                   - (g["Option Index Put Long"] - g["Option Index Put Short"])}
TRANSFORMS = {"lvl": lambda s: s, "f1": lambda s: s.diff(), "f5": lambda s: s.diff(5)}
D0, D1 = dt.date(2019, 1, 1), dt.date(2024, 6, 30)   # discovery (long window, power)
C0, C1 = dt.date(2024, 7, 1), dt.date(2026, 6, 30)   # confirmation

rows = []
sigstore = {}
for actor in ACTORS:
    g = poi[poi["Client Type"] == actor].set_index("date").sort_index()
    g.index = pd.to_datetime(g.index).date
    for mname, m in measures(g).items():
        for tname, tf in TRANSFORMS.items():
            raw = tf(m).dropna()
            raw = raw[[d in pos for d in raw.index]]
            rank = raw.rolling(252, min_periods=250).apply(lambda w: (w[-1] > w[:-1]).mean(), raw=True).dropna()
            for k in (1, 3, 5):
                cell = f"{actor}|{mname}|{tname}|k{k}"
                def spread_t(idx_lo, idx_hi):
                    top, bot = [], []
                    for dd, rk in rank.items():
                        if not (idx_lo <= dd <= idx_hi):
                            continue
                        i = pos.get(dd)
                        if i is None or i + 1 + k >= len(tdays):
                            continue
                        e = close[tdays[i + 1]]
                        r = (close[tdays[i + 1 + k]] / e - 1) * 1e4
                        (top if rk >= 0.8 else bot if rk <= 0.2 else []).append(r)
                    if len(top) < 25 or len(bot) < 25:
                        return np.nan, np.nan, 0
                    sp_ = np.mean(top) - np.mean(bot)
                    t = sp_ / np.sqrt(np.var(top, ddof=1)/len(top) + np.var(bot, ddof=1)/len(bot))
                    return sp_ / k, t, len(top) + len(bot)
                s_d, t_d, n_d = spread_t(D0, D1)
                s_c, t_c, n_c = spread_t(C0, C1)
                rows.append(dict(cell=cell, disc_bpsday=s_d, disc_t=t_d, disc_n=n_d,
                                 conf_bpsday=s_c, conf_t=t_c, conf_n=n_c))
    print(f"{actor} done", flush=True)

lat = pd.DataFrame(rows)
import math
lat["p"] = 2 * (1 - pd.Series(np.abs(lat.disc_t)).apply(lambda z: 0.5 * (1 + math.erf(z / np.sqrt(2))) if np.isfinite(z) else np.nan))
lat = lat.sort_values("p")
m_valid = lat.p.notna().sum()
lat["bh_crit"] = [0.10 * (i + 1) / m_valid for i in range(len(lat))]
lat["bh_pass"] = (lat.p <= lat.bh_crit)
# BH step-up: all cells up to the largest passing rank
if lat.bh_pass.any():
    kmax = np.where(lat.bh_pass.values)[0].max()
    lat["bh_pass"] = [i <= kmax for i in range(len(lat))]
lat["confirmed"] = lat.bh_pass & (np.sign(lat.conf_bpsday) == np.sign(lat.disc_bpsday)) & (lat.conf_t.abs() >= 1.5)
lat.to_csv(OUT / "flow_lattice.csv", index=False)
n_bh = int(lat.bh_pass.sum()); n_conf = int(lat.confirmed.sum())
print(f"\nlattice: {len(lat)} cells | BH-FDR(10%) discovery passes: {n_bh} | confirmed on 2024-26: {n_conf}", flush=True)
print(lat[lat.confirmed][["cell", "disc_bpsday", "disc_t", "conf_bpsday", "conf_t"]].to_string(index=False), flush=True)
print("\ntop-10 discovery cells (regardless):", flush=True)
print(lat.head(10)[["cell", "disc_bpsday", "disc_t", "conf_bpsday", "conf_t"]].to_string(index=False), flush=True)
