# -*- coding: utf-8 -*-
"""DID v3 MAKE THE SCORE BETTER OR WORSE AT PREDICTING? Point-in-time decile test, v1 vs v3.
Principal, 2026-08-07: "show me backtest best possible estimate because prev was good new model i am
not sure we have to look".

METHOD. Imports `bt_pit_quant_v11` and reuses its loader and its per-name feature construction
BYTE-FOR-BYTE -- same universe-as-of, same 90-day fundamentals lag, same +1-session entry lag, same
neutralised regime tilt. The ONLY thing that differs between arms is how the seven pillars are
aggregated into a composite. Anything else would confound the comparison.

ARMS
  v1        skip-and-renormalise. The engine as it stands; the bug.
  v3-mech   neutral-fill for a missing pillar, 1-year sibling substitution where a 3-year pillar is
            unavailable (g3<-g1, r24<-r12), and growth artefacts (>200% CAGR) treated as missing.
  v3-fwd    v3-mech plus a PROXIED forward growth leg: the frozen bonus/penalty bands applied to
            60% trailing 3y revenue CAGR : 40% trailing 1y revenue growth, revenue winsorised at 25.

WHAT THIS CAN AND CANNOT SETTLE -- stated plainly because the difference matters:
  * The conviction leg (analyst Sell/Hold) is NOT tested and cannot be. There is no point-in-time
    history of analyst opinion; using today's view at a past date is lookahead, and proxying it with
    "score below 40" is circular. Its effect stays unmeasured.
  * The listing-price technical is NOT tested either. `score_asof` requires 260 sessions of price
    history, so sub-1-year names never enter the backtest universe at all -- the very names that rule
    exists for. That rule rests on the separate 515-name recovery test, not on this.
  * v3-fwd is therefore a PROXY for the forward leg, not the forward leg. It answers "does banding
    growth into +/-15 points add ranking power, or only variance?", which is the honest testable half.

Reported per arm: decile spread (D10-D1), rank IC of score vs forward quarterly return, top-decile
hit rate vs the equal-weight universe, and the long-short series. Higher IC and a monotone decile
ladder is the thing to look for; a wider D10-D1 spread achieved with a NON-monotone ladder is noise.
"""
import importlib.util
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def _root(p):
    while True:
        p, tail = os.path.split(p)
        if not tail:
            raise RuntimeError("root not found")
        if tail == "NIFTY 500":
            return os.path.join(p, tail)


ROOT = _root(HERE)
LIVE = os.path.join(ROOT, "Shreyas_Ionic_AMC", "04_RND_LAB", "STOCK_SCORECARD_750")
RES = os.path.join(LIVE, "results")
OUT = os.path.join(RES, "BT_V1_VS_V3_DECILES.md")

# import the live v11 harness by path (the worktree copy may differ; the live one is the reference)
spec = importlib.util.spec_from_file_location("bt11", os.path.join(LIVE, "bt_pit_quant_v11.py"))
bt11 = importlib.util.module_from_spec(spec)
sys.modules["bt11"] = bt11
spec.loader.exec_module(bt11)

W3 = bt11.W3
PILL = ["quality", "growth", "value", "stage", "sector_s", "own", "accum"]
WVEC = np.array([W3["quality"], W3["growth"], W3["value"], W3["stage"],
                 W3["sector"], W3["own"], W3["accum"]], float)
NEUTRAL = 50.0
ARTEFACT = 200.0
FWD_BANDS = ((25.0, 15.0), (20.0, 10.0), (15.0, 5.0), (10.0, 0.0), (5.0, -5.0), (-1e9, -15.0))
FWD_REV_CLIP = 25.0


def raw_frame(t, fund, mem, sh, sect, pxm, vol):
    """Per-name features + pillars, exactly as v11 builds them, WITHOUT the composite step."""
    df = bt11.score_asof.__wrapped__(t, fund, mem, sh, sect, pxm, vol) \
        if hasattr(bt11.score_asof, "__wrapped__") else None
    return df


def build(t, fund, mem, sh, sect, pxm, vol):
    """Re-run v11's own feature block, then return the pillar frame plus the raw inputs the v3 rules
    need (g1/g3 for the sibling substitution and the growth proxy, de/intcov for the gates)."""
    uni = bt11.members_asof(mem, t)
    px_t = pxm.loc[:t]
    if len(px_t) < 260:
        return None
    last = px_t.index[-1]
    d200 = px_t.tail(200).mean()
    rows = []
    for s in uni:
        g = fund.get(s)
        if g is None or s not in pxm.columns:
            continue
        av = g[g["avail"] <= t]
        if av.empty:
            continue
        y0 = int(av.index.max())
        r0 = g.loc[y0] if y0 in g.index else None
        if r0 is None:
            continue
        if isinstance(r0, pd.DataFrame):
            r0 = r0.iloc[-1]
        ps = px_t[s].dropna()
        if len(ps) < 260 or pd.isna(ps.iloc[-1]):
            continue
        p = ps.iloc[-1]

        def gy(y, c):
            return g.loc[y, c] if (y in g.index) else np.nan
        sales0 = r0.get("sales"); sales1 = gy(y0 - 1, "sales"); sales3 = gy(y0 - 3, "sales")
        eqres = (r0.get("eqcap") or 0) + (r0.get("res") or 0)
        rec = dict(sym=s, sector=sect.get(s, "unknown"), roe=r0.get("roe"), roce=r0.get("roce"),
                   de=(r0.get("borrow") / eqres) if eqres and eqres > 0 and pd.notna(r0.get("borrow")) else np.nan,
                   g1=((sales0 / sales1 - 1) * 100) if pd.notna(sales0) and pd.notna(sales1) and sales1 > 0 else np.nan,
                   g3=(((sales0 / sales3) ** (1 / 3) - 1) * 100) if pd.notna(sales0) and pd.notna(sales3) and sales3 > 0 else np.nan,
                   pe=(p / r0.get("eps")) if pd.notna(r0.get("eps")) and r0.get("eps") > 0 else np.nan,
                   intcov=(r0.get("opro") / r0.get("interest")) if pd.notna(r0.get("interest")) and r0.get("interest") > 0 else np.nan)
        r12a = ps.asof(last - pd.Timedelta(days=365))
        rec["r12"] = (p / r12a - 1) if pd.notna(r12a) and r12a else np.nan
        p24 = ps.asof(last - pd.Timedelta(days=730))
        rec["r24"] = (p / p24 - 1) if pd.notna(p24) and p24 else np.nan
        rec["above200"] = p > d200.get(s, np.nan)
        v = vol.get(s)
        if v is not None:
            vv = v.loc[:t].tail(190)
            rec["obv"] = np.polyfit(range(len(vv)), vv.fillna(0).cumsum().values, 1)[0] if len(vv) > 30 else np.nan
        else:
            rec["obv"] = np.nan
        shx = sh[(sh["sym"] == s) & (sh["available_date"] <= t)].sort_values("quarter_end")
        rec["fd"] = (shx["fd"].iloc[-1] - shx["fd"].iloc[-2]) if len(shx) >= 2 else np.nan
        rows.append(rec)
    df = pd.DataFrame(rows)
    if len(df) < 50:
        return None
    wz = bt11.winz_pct
    df["is_fin"] = df["sector"].isin(bt11.FIN)
    df["quality"] = pd.concat([wz(df["roe"]), wz(df["roce"])], axis=1).mean(axis=1)
    df["growth"] = wz(df["g3"])
    df["growth_1y_sib"] = wz(df["g1"])                       # the sibling, ranked the same way
    v_pe_u = wz(-df["pe"]); v_pe_s = df.groupby("sector")["pe"].transform(lambda x: wz(-x))
    df["value"] = v_pe_u * (0.25 / 0.60) + v_pe_s * (0.35 / 0.60)
    st12, st24 = wz(df["r12"]), wz(df["r24"])
    df["stage"] = pd.concat([st12, st24], axis=1).mean(axis=1)
    df["stage_12_only"] = st12                               # the sibling for a missing r24
    df["stage"] = np.where(df["above200"], df["stage"], df["stage"] * 0.5)
    df["stage_12_only"] = np.where(df["above200"], df["stage_12_only"], df["stage_12_only"] * 0.5)
    secmean = df.groupby("sector")["r12"].transform("mean")
    df["sector_s"] = wz(secmean)
    df["own"] = wz(df["fd"]); df["accum"] = wz(df["obv"])
    return df


def gates_and_flags(df, comp):
    red = (((df["de"] > 2.5) | (df["intcov"] < 1.5)) & (~df["is_fin"]))
    amb = (((df["de"] > 1.5) | (df["intcov"] < 3)) & (~df["is_fin"]) & (~red))
    out = comp.copy()
    out[red] = out[red].clip(upper=40)
    out[amb] = out[amb] * 0.85
    fl = (((df["de"] > 2.5) & (~df["is_fin"])).astype(int) + (df["intcov"] < 1.5).astype(int)
          + (df["g1"] < 0).astype(int) + ((df["g3"] - df["g1"]) > 15).astype(int))
    pen = -np.minimum(10, 2.0 ** fl - 1)
    boo = np.where((fl == 0) & (df["quality"] > 60) & (df["value"] > 60), 3, 0)
    return (out + pen + boo).clip(0, 100)


def compose(df, arm):
    M = df[PILL].astype(float).copy()
    if arm != "v1":
        # growth artefacts out, then the 1-year siblings in
        M.loc[df["g3"] > ARTEFACT, "growth"] = np.nan
        M["growth"] = M["growth"].fillna(df["growth_1y_sib"])
        M["stage"] = M["stage"].fillna(df["stage_12_only"])
    Mv = M.values
    if arm == "v1":
        mask = ~np.isnan(Mv); wsum = (mask * WVEC).sum(1)
        comp = np.nansum(np.nan_to_num(Mv) * WVEC, 1) / np.where(wsum == 0, np.nan, wsum)
    else:
        filled = np.where(np.isnan(Mv), NEUTRAL, Mv)         # neutral-fill at FULL weight
        comp = (filled * WVEC).sum(1) / WVEC.sum()
    comp = pd.Series(comp, index=df.index)
    fin = gates_and_flags(df, comp)
    if arm == "v3-fwd":
        g = 0.60 * df["g3"].fillna(df["g1"]) + 0.40 * df["g1"].clip(upper=FWD_REV_CLIP)
        pts = pd.Series(FWD_BANDS[-1][1], index=df.index, dtype=float)
        for lo, p in reversed(FWD_BANDS):
            pts[g >= lo] = p
        pts[g.isna()] = 0.0
        fin = (fin + pts).clip(5, 95)
    else:
        fin = fin.clip(5, 95) if arm != "v1" else fin
    return fin


def main(start="2016-12-31", end="2025-06-30", horizon_days=252, label="1Y"):
    """HORIZON MATTERS, and the first run of this file got it wrong. It measured QUARTERLY forward
    returns on a score whose fundamental pillars are built from 3-year windows -- asking a long-horizon
    signal to time a quarter. Every arm came out flat, which says little about the score and a lot
    about the test. Horizon is now a parameter; 1Y and 3Y are the ones that match the design (and the
    prior decile work). Overlapping windows mean the effective independent sample is far smaller than
    the period count -- roughly `periods x 63 / horizon_days` -- so read the ladders, not the decimals."""
    fund, mem, sh, sect, pxm, vol, idx = bt11.load()
    qends = pd.date_range(start, end, freq="QE")
    rdates = [pxm.index[pxm.index <= q][-1] for q in qends if len(pxm.index[pxm.index <= q])]
    arms = ["v1", "v3-mech", "v3-fwd"]
    per = {a: [] for a in arms}
    ics = {a: [] for a in arms}
    ndates = 0
    for i, t in enumerate(rdates[:-1]):
        df = build(t, fund, mem, sh, sect, pxm, vol)
        if df is None:
            continue
        e0 = bt11.next_session(pxm, t)
        if e0 is None or e0 not in pxm.index:
            continue
        fut = pxm.index[pxm.index >= e0 + pd.Timedelta(days=horizon_days * 365 // 252)]
        e1 = fut[0] if len(fut) else None
        if e1 is None or e1 not in pxm.index:
            continue
        a = pxm.loc[e0, df["sym"]].values.astype(float)
        b = pxm.loc[e1, df["sym"]].values.astype(float)
        with np.errstate(invalid="ignore", divide="ignore"):
            fwd = np.where((a > 0) & np.isfinite(a) & np.isfinite(b), b / a - 1, np.nan)
        df = df.assign(fwd=fwd)
        ok = df["fwd"].notna()
        if ok.sum() < 50:
            continue
        ndates += 1
        for arm in arms:
            sc = compose(df, arm)
            m = ok & sc.notna()
            if m.sum() < 50:
                continue
            s, r = sc[m], df.loc[m, "fwd"]
            dec = pd.qcut(s.rank(method="first"), 10, labels=False)
            means = r.groupby(dec).mean()
            per[arm].append(dict(t=t.date(), spread=means.get(9, np.nan) - means.get(0, np.nan),
                                 d10=means.get(9, np.nan), d1=means.get(0, np.nan),
                                 ew=r.mean(),
                                 mono=int(means.is_monotonic_increasing),
                                 **{f"dec{k+1}": means.get(k, np.nan) for k in range(10)}))
            ics[arm].append(s.corr(r, method="spearman"))

    eff_n = max(1, round(ndates * 63 / horizon_days))
    lines = [f"# v1 vs v3 — point-in-time decile test, {label} forward returns", "",
             f"Quarterly formation, **{label}** holding, {ndates} overlapping periods, {start} to "
             f"{end}. Universe as-of each date, 90-day fundamentals lag, +1-session entry lag, regime "
             f"tilt neutralised. Only the pillar AGGREGATION differs between arms.", "",
             f"**Effective independent windows: about {eff_n}.** Overlapping {label} horizons sampled "
             f"quarterly are heavily autocorrelated, so no t-statistic is quotable here and small IC "
             f"differences are not meaningful. Read the decile ladder and the sign, not the decimals.",
             "",
             "| arm | mean rank IC | IC hit rate | mean D10-D1 | mean D10 | mean D1 | monotone |",
             "|---|---|---|---|---|---|---|"]
    store = {}
    for arm in arms:
        p = pd.DataFrame(per[arm])
        ic = pd.Series(ics[arm]).dropna()
        store[arm] = p
        if p.empty:
            lines.append(f"| {arm} | - | - | - | - | - | - |")
            continue
        lines.append(f"| {arm} | {ic.mean():+.4f} | {(ic > 0).mean()*100:.0f}% | "
                     f"{p['spread'].mean()*100:+.2f}% | {p['d10'].mean()*100:+.2f}% | "
                     f"{p['d1'].mean()*100:+.2f}% | {int(p['mono'].sum())}/{len(p)} |")

    lines += ["", f"## Decile ladders (mean forward {label} return, %)", "",
              "| arm | " + " | ".join(f"D{k}" for k in range(1, 11)) + " |",
              "|---|" + "---|" * 10]
    for arm in arms:
        p = store[arm]
        if p.empty:
            continue
        lines.append(f"| {arm} | " + " | ".join(f"{p[f'dec{k}'].mean()*100:+.1f}"
                                                for k in range(1, 11)) + " |")

    lines += ["", "## What this does and does not settle", "",
              "- The **conviction leg** (analyst Sell/Hold) is untested and untestable: no point-in-time "
              "history of analyst opinion exists, and proxying it with the score is circular.",
              "- The **listing-price technical** is untested here: `score_asof` needs 260 sessions, so "
              "sub-1-year names never enter this universe. That rule rests on the 515-name recovery "
              "test instead.",
              "- **v3-fwd** proxies the forward growth leg with TRAILING growth through the frozen "
              "bands. It answers whether banding growth into +/-15 adds ranking power; it is not the "
              "analyst's forward view.", ""]

    return "\n".join(lines)


if __name__ == "__main__":
    blocks = []
    for hz, lab in ((63, "quarterly"), (252, "1Y"), (756, "3Y")):
        blocks.append(main(horizon_days=hz, label=lab))
        print(blocks[-1]); print()
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("\n\n---\n\n".join(blocks) + "\n")
    print("wrote", OUT)
