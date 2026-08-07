# -*- coding: utf-8 -*-
"""abl_scorer.py - RED-TEAM ABLATION COPY of bt_pit_quant.py (Nikhil Bose, 2026-08-06).

This is a COPY, not an edit of the live bt_pit_quant.py / FROZEN_METHODOLOGY.md / gate_v2.py /
config.py / final_model.py. Nothing in the live scorer is touched. The only change from
bt_pit_quant.py is that the gate/penalty/boost block in score_asof() now consults a module-level
GATE_CFG dict so each layer can be switched off ONE AT A TIME for TEST 2 (gate ablation). Every
other line -- data loading, pillar construction, weights, universe, no-lookahead discipline -- is
copied verbatim from the live bt_pit_quant.py (Jul-27 15:40 version, the one bt_decile_rolling.py
imports as `B`) so the ablation is measuring the SAME model the Principal's rolling study measured,
minus exactly one mechanism at a time.

GATE_CFG keys (all True = reproduces the live gate exactly = "V0" control):
  red_cap    : RED flag (D/E>2.5 or IntCov<1.5, non-financial) clips composite at 40
  amber_mult : AMBER flag (D/E>1.5 or IntCov<3, non-financial, not RED) multiplies composite by 0.85
  penalty    : -min(10, 2**n_flags - 1) subtracted, n_flags from D/E>2.5, IntCov<1.5, g1<0, (g3-g1)>15
  boost      : +3 when flags==0 and quality>60 and value>60

NOTE: n_flags (feeding `penalty`) is computed independently of the red_cap/amber_mult booleans in
the live code -- switching red_cap off does NOT also silently switch off the D/E>2.5 flag inside
the penalty count. Preserved here on purpose: ablating one mechanism must not accidentally ablate
another that happens to share a threshold.
"""
import os
import json

os.environ["PYTHONIOENCODING"] = "utf-8"
import numpy as np
import pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
EP = os.path.join(ROOT, "datasets", "earnings_pit")
RF = 0.065
FIN = {"financial services", "finance", "banking", "banks", "nbfc", "insurance"}
W3 = dict(quality=20, growth=20, value=18, stage=14, sector=11, own=9, accum=8)

# ---- THE ONLY NEW THING: an ablation switchboard, defaults = full live model ----
GATE_CFG = dict(red_cap=True, amber_mult=True, penalty=True, boost=True)


def winz_pct(s):
    s = pd.to_numeric(s, errors="coerce")
    lo, hi = s.quantile(0.02), s.quantile(0.98)
    return s.clip(lo, hi).rank(pct=True) * 100


def _yr(x):
    d = pd.to_datetime(x, errors="coerce")
    return int(d.year) if pd.notna(d) else np.nan


def load():
    def rd(fn):
        return pd.read_parquet(os.path.join(EP, fn))
    rat = rd("ratios_pit.parquet")[["nse_symbol", "year_end", "available_date", "ROE %", "ROCE %"]].copy()
    bs = rd("yearly_balance_sheet_pit.parquet")[["nse_symbol", "year_end", "available_date", "Borrowings", "Equity Capital", "Reserves"]].copy()
    pl = rd("yearly_profit_loss_pit.parquet")[["nse_symbol", "year_end", "available_date", "Sales", "EPS in Rs", "Interest", "Operating Profit"]].copy()
    for d in (rat, bs, pl):
        d["sym"] = d["nse_symbol"].astype(str).str.upper().str.strip()
        d["yr"] = d["year_end"].map(_yr)
        d["avail"] = pd.to_datetime(d["available_date"], errors="coerce")
    rat = rat.rename(columns={"ROE %": "roe", "ROCE %": "roce"})
    bs = bs.rename(columns={"Borrowings": "borrow", "Equity Capital": "eqcap", "Reserves": "res"})
    pl = pl.rename(columns={"Sales": "sales", "EPS in Rs": "eps", "Interest": "interest", "Operating Profit": "opro"})
    for d in (rat, bs, pl):
        d.sort_values(["sym", "yr", "avail"], inplace=True)
        d.drop_duplicates(subset=["sym", "yr"], keep="last", inplace=True)
    ann = rat[["sym", "yr", "avail", "roe", "roce"]].merge(
        bs[["sym", "yr", "borrow", "eqcap", "res"]], on=["sym", "yr"], how="outer").merge(
        pl[["sym", "yr", "avail", "sales", "eps", "interest", "opro"]], on=["sym", "yr"], how="outer", suffixes=("", "_pl"))
    ann["avail"] = ann["avail"].fillna(ann["avail_pl"])
    ann = ann.dropna(subset=["sym", "yr", "avail"]).sort_values(["sym", "yr"])
    fund = {s: g.set_index("yr") for s, g in ann.groupby("sym")}

    mem = pd.read_excel(os.path.join(ROOT, "NIFTY500_TICKER_2005_2025_Final.xlsx"))
    mem["dt"] = pd.to_datetime(mem["Month-Year"], format="%b%Y", errors="coerce")
    mem["Ticker"] = mem["Ticker"].astype(str).str.upper().str.strip()

    sh = pd.read_parquet(os.path.join(EP, "quarterly_shareholding_pit.parquet"))
    sh["available_date"] = pd.to_datetime(sh["available_date"]); sh["quarter_end"] = pd.to_datetime(sh["quarter_end"])
    sh["sym"] = sh["nse_symbol"].astype(str).str.upper().str.strip()
    sh["fd"] = pd.to_numeric(sh["FIIs"], errors="coerce") + pd.to_numeric(sh["DIIs"], errors="coerce")

    try:
        sm = pd.read_parquet(os.path.join(ROOT, r"ALPHA_RANKER\data\universe\sector_map.parquet"))
        scol = "macro_sector" if "macro_sector" in sm.columns else sm.columns[-1]
        idcol = [c for c in sm.columns if "sym" in c.lower() or "ticker" in c.lower()][0]
        sect = {str(r[idcol]).upper().strip(): str(r[scol]).lower().strip() for _, r in sm.iterrows()}
    except Exception:
        sect = {}

    pdir = os.path.join(ROOT, r"ALPHA_RANKER\data\prices")
    px, vol = {}, {}
    for fn in os.listdir(pdir):
        if not fn.endswith(".parquet"):
            continue
        s = fn[:-8].upper()
        d = pd.read_parquet(os.path.join(pdir, fn), columns=["Adj Close", "Close", "Volume"])
        d.index = pd.to_datetime(d.index); d = d[~d.index.duplicated(keep="last")].sort_index()
        px[s] = d["Adj Close"]; vol[s] = d["Close"] * d["Volume"]
    pxm = pd.DataFrame(px).sort_index()

    idx = pd.read_parquet(os.path.join(ROOT, r"datasets\index_daily\nse_official_all_indices.parquet"),
                          columns=["index_name", "date", "close", "div_yield"])
    idx = idx[idx["index_name"] == "Nifty 500"].copy()
    idx["date"] = pd.to_datetime(idx["date"]); idx = idx.set_index("date").sort_index()
    return fund, mem, sh, sect, pxm, vol, idx


def members_asof(mem, t):
    sub = mem[mem["dt"] <= t]
    if sub.empty:
        return set()
    return set(mem[mem["dt"] == sub["dt"].max()]["Ticker"])


def score_asof(t, fund, mem, sh, sect, pxm, vol):
    uni = members_asof(mem, t)
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
        rec = dict(sym=s, sector=sect.get(s, "unknown"),
                   roe=r0.get("roe"), roce=r0.get("roce"),
                   de=(r0.get("borrow") / eqres) if eqres and eqres > 0 and pd.notna(r0.get("borrow")) else np.nan,
                   g1=((sales0 / sales1 - 1) * 100) if pd.notna(sales0) and pd.notna(sales1) and sales1 > 0 else np.nan,
                   g3=(((sales0 / sales3) ** (1 / 3) - 1) * 100) if pd.notna(sales0) and pd.notna(sales3) and sales3 > 0 else np.nan,
                   pe=(p / r0.get("eps")) if pd.notna(r0.get("eps")) and r0.get("eps") > 0 else np.nan,
                   intcov=(r0.get("opro") / r0.get("interest")) if pd.notna(r0.get("interest")) and r0.get("interest") > 0 else np.nan)
        rec["r12"] = (p / ps.asof(last - pd.Timedelta(days=365)) - 1) if ps.asof(last - pd.Timedelta(days=365)) else np.nan
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
    df["is_fin"] = df["sector"].isin(FIN)
    df["quality"] = pd.concat([winz_pct(df["roe"]), winz_pct(df["roce"])], axis=1).mean(axis=1)
    df["growth"] = winz_pct(df["g3"])
    v_pe_u = winz_pct(-df["pe"]); v_pe_s = df.groupby("sector")["pe"].transform(lambda x: winz_pct(-x))
    df["value"] = v_pe_u * (0.25 / 0.60) + v_pe_s * (0.35 / 0.60)
    df["stage"] = pd.concat([winz_pct(df["r12"]), winz_pct(df["r24"])], axis=1).mean(axis=1)
    df["stage"] = np.where(df["above200"], df["stage"], df["stage"] * 0.5)
    secmean = df.groupby("sector")["r12"].transform("mean")
    df["sector_s"] = winz_pct(secmean)
    df["own"] = winz_pct(df["fd"]); df["accum"] = winz_pct(df["obv"])
    pill = ["quality", "growth", "value", "stage", "sector_s", "own", "accum"]
    W = np.array([W3["quality"], W3["growth"], W3["value"], W3["stage"], W3["sector"], W3["own"], W3["accum"]], float)
    M = df[pill].astype(float).values
    mask = ~np.isnan(M); wsum = (mask * W).sum(1)
    df["composite_3y"] = np.nansum(np.nan_to_num(M) * W, 1) / np.where(wsum == 0, np.nan, wsum)

    # ---- gates: EXACT copy of the live logic, gated behind GATE_CFG for ablation only ----
    red = (((df["de"] > 2.5) | (df["intcov"] < 1.5)) & (~df["is_fin"]))
    amb = (((df["de"] > 1.5) | (df["intcov"] < 3)) & (~df["is_fin"]) & (~red))
    df["final"] = df["composite_3y"].copy()
    if GATE_CFG["red_cap"]:
        df.loc[red, "final"] = df.loc[red, "final"].clip(upper=40)
    if GATE_CFG["amber_mult"]:
        df.loc[amb, "final"] = df.loc[amb, "final"] * 0.85
    fl = (((df["de"] > 2.5) & (~df["is_fin"])).astype(int) + (df["intcov"] < 1.5).astype(int)
          + (df["g1"] < 0).astype(int) + ((df["g3"] - df["g1"]) > 15).astype(int))
    if GATE_CFG["penalty"]:
        df["penalty"] = -np.minimum(10, 2.0 ** fl - 1)
    else:
        df["penalty"] = 0.0
    if GATE_CFG["boost"]:
        df["boost"] = np.where((fl == 0) & (df["quality"] > 60) & (df["value"] > 60), 3, 0)
    else:
        df["boost"] = 0
    df["final"] = (df["final"] + df["penalty"] + df["boost"]).clip(0, 100)
    # kept for diagnostics -- which raw flags fired, regardless of which layers are switched on
    df["red_flag"] = red
    df["amber_flag"] = amb
    df["n_penalty_flags"] = fl
    return df[["sym", "sector", "final", "composite_3y", "quality", "growth", "value", "stage",
               "red_flag", "amber_flag", "n_penalty_flags", "de", "intcov"]].dropna(subset=["final"])


def next_session(pxm, t):
    fut = pxm.index[pxm.index > t]
    return fut[0] if len(fut) else None
