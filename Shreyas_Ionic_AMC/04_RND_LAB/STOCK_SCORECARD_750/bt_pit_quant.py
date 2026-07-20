"""
bt_pit_quant.py  v2 (2026-07-20) - POINT-IN-TIME, NO-LOOKAHEAD backtest of the STOCK_SCORECARD quant score.
Tests: hold top-10 by score (equal weight) and bottom-10, quarterly rebalanced, vs Nifty 500 TRI proxy.

v2 FIX (red-team, Nikhil, ADVERSARIAL_REVIEWS.md 2026-07-20): v1 read mc_fundamentals_parsed.parquet,
which caps at available_date 2023-06-29 and silently dropped ~20% of the N500 (concentrated in
quality compounders), skewing the universe toward the PSU/cyclical cohort that led 2022-24 and
invalidating the "no edge" read. v2 uses the firm's mandated annual PIT panels
(ratios_pit ROE/ROCE, yearly_balance_sheet_pit D/E, yearly_profit_loss_pit revenue/EPS/interest),
per-symbol-latest-available (not a single cross-sectional year cutoff). N500 coverage now ~430-455.

QUANT-ONLY: the analyst layer (growth estimate, reverse-DCF, Sell/Hold override, Ionic forward
adjustment) is present-day judgment and CANNOT be reconstructed historically, so it is excluded.
Ranking signal = final_3y_adj (the 3Y fundamentals-led composite after gates/penalty/boost).

NO-LOOKAHEAD discipline: universe = N500 members as-of the rebalance month (survivorship-safe);
fundamentals = latest annual whose available_date (90-day conservative lag) <= rebalance date,
per symbol; price pillars from prices <= date; ownership from shareholding available <= date;
regime tilt NEUTRALIZED (historical regime unknown); ENTRY LAGGED +1 session; benchmark same dates.
Documented data-driven deviations from the live engine: Value uses PE only (no clean PIT book-value
-per-share or FCF line) -> renorm(0.25 -PE univ, 0.35 -PE sector); sector-neutral Quality + sector
Value bucket use a static current sector map (sectors rarely change).
WINDOW: annual PIT fundamentals refresh through FY2023 (available to Nov-2023) and prices start
Jul-2021, so the faithful clean window is ~Dec-2021 to Sep-2024 (~11 quarters). Fundamentals for
2024 rebalances are FY2023 (<=~15m old): stale, not lookahead. A clean 5y needs the PIT panel
extended past FY2023 + earlier prices (data project).
Outputs -> results/PIT_SCORE_BACKTEST_20260720/: nav.csv, metrics.json, baskets.csv, nav_chart.png.
"""
import os, json
os.environ["PYTHONIOENCODING"] = "utf-8"
import numpy as np, pandas as pd

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
EP = os.path.join(ROOT, "datasets", "earnings_pit")
OUT = os.path.join(ROOT, r"Shreyas_Ionic_AMC\04_RND_LAB\STOCK_SCORECARD_750\results\PIT_SCORE_BACKTEST_20260720")
os.makedirs(OUT, exist_ok=True)
RF = 0.065
FIN = {"financial services", "finance", "banking", "banks", "nbfc", "insurance"}
W3 = dict(quality=20, growth=20, value=18, stage=14, sector=11, own=9, accum=8)


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
    # dedupe to one row per (sym, yr) - panels carry standalone/consolidated dupes; keep latest-filed
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
    # gates
    red = (((df["de"] > 2.5) | (df["intcov"] < 1.5)) & (~df["is_fin"]))
    amb = (((df["de"] > 1.5) | (df["intcov"] < 3)) & (~df["is_fin"]) & (~red))
    df["final"] = df["composite_3y"].copy()
    df.loc[red, "final"] = df.loc[red, "final"].clip(upper=40)
    df.loc[amb, "final"] = df.loc[amb, "final"] * 0.85
    fl = (((df["de"] > 2.5) & (~df["is_fin"])).astype(int) + (df["intcov"] < 1.5).astype(int)
          + (df["g1"] < 0).astype(int) + ((df["g3"] - df["g1"]) > 15).astype(int))
    df["penalty"] = -np.minimum(10, 2.0 ** fl - 1)
    df["boost"] = np.where((fl == 0) & (df["quality"] > 60) & (df["value"] > 60), 3, 0)
    df["final"] = (df["final"] + df["penalty"] + df["boost"]).clip(0, 100)
    return df[["sym", "sector", "final", "composite_3y", "quality", "growth", "value", "stage"]].dropna(subset=["final"])


def next_session(pxm, t):
    fut = pxm.index[pxm.index > t]
    return fut[0] if len(fut) else None


def basket_ret(pxm, syms, e0, e1):
    if e0 is None or e1 is None:
        return np.nan, 0
    rs = []
    for s in syms:
        if s in pxm.columns:
            a = pxm.at[e0, s] if e0 in pxm.index else np.nan
            b = pxm.at[e1, s] if e1 in pxm.index else np.nan
            if pd.notna(a) and pd.notna(b) and a > 0:
                rs.append(b / a - 1)
    return (np.mean(rs) if rs else np.nan), len(rs)


def run(start="2021-12-31", end="2024-09-30", lag=1, verbose=True):
    fund, mem, sh, sect, pxm, vol, idx = load()
    qends = pd.date_range(start, end, freq="QE")
    rdates = [pxm.index[pxm.index <= q][-1] for q in qends if len(pxm.index[pxm.index <= q])]
    recs, baskets, univ_syms = [], [], []
    for i, t in enumerate(rdates[:-1]):
        sc = score_asof(t, fund, mem, sh, sect, pxm, vol)
        if sc is None or len(sc) < 30:
            if verbose: print(t.date(), "skip")
            continue
        sc = sc.sort_values("final")
        bot = list(sc.head(10)["sym"]); top = list(sc.tail(10)["sym"])
        e0 = next_session(pxm, t) if lag else t
        e1 = next_session(pxm, rdates[i + 1]) if lag else rdates[i + 1]
        rt, nt = basket_ret(pxm, top, e0, e1); rb, nb = basket_ret(pxm, bot, e0, e1)
        rew, _ = basket_ret(pxm, list(sc["sym"]), e0, e1)
        univ_syms.append((list(sc["sym"]), e0, e1))
        if e0 in idx.index and e1 in idx.index:
            bpx = idx.at[e1, "close"] / idx.at[e0, "close"] - 1
            dy = pd.to_numeric(idx.loc[e0:e1, "div_yield"], errors="coerce").mean() / 100
            rbench = bpx + dy * (e1 - e0).days / 365
        else:
            rbench = np.nan
        recs.append(dict(rebal=t.date(), entry=e0.date(), exit=e1.date(), n_uni=len(sc),
                         top_ret=rt, bot_ret=rb, bench_ret=rbench, ew_ret=rew,
                         ls_ret=(rt - rb) if pd.notna(rt) and pd.notna(rb) else np.nan,
                         top_vs_ew=(rt - rew) if pd.notna(rt) and pd.notna(rew) else np.nan, n_top=nt, n_bot=nb))
        baskets.append(dict(rebal=t.date(), top=";".join(top), bottom=";".join(bot)))
        if verbose:
            print(f"{t.date()} uni={len(sc):3d} top={rt:+.3f} bot={rb:+.3f} bench={rbench:+.3f} ew={rew:+.3f} L-S={rt-rb:+.3f}")
    return pd.DataFrame(recs), pd.DataFrame(baskets), idx, univ_syms, pxm


def placebo(pxm, univ_syms, ndraw=2000, seed=7):
    rng = np.random.default_rng(seed); out = []
    for _ in range(ndraw):
        rets = []
        for syms, e0, e1 in univ_syms:
            r, _n = basket_ret(pxm, list(rng.choice(syms, size=min(10, len(syms)), replace=False)), e0, e1)
            rets.append(r)
        rets = [x for x in rets if pd.notna(x)]
        if rets:
            out.append(np.cumprod([1 + x for x in rets])[-1] ** (4 / len(rets)) - 1)
    return np.array(out)


def metrics(R):
    def stats(col):
        r = R[col].dropna().values
        if len(r) < 2:
            return {}
        nav = np.cumprod(1 + r); yrs = R.shape[0] / 4.0
        cagr = nav[-1] ** (1 / yrs) - 1; vol = np.std(r, ddof=1) * np.sqrt(4)
        sharpe = (np.mean(r) * 4 - RF) / vol if vol > 0 else np.nan
        dd = np.min(nav / np.maximum.accumulate(nav) - 1)
        return dict(total_ret=round(float(nav[-1] - 1) * 100, 1), cagr_pct=round(cagr * 100, 1),
                    vol_pct=round(vol * 100, 1), sharpe=round(float(sharpe), 2),
                    maxdd_pct=round(float(dd) * 100, 1), periods=int(len(r)))
    out = {c: stats(c) for c in ["top_ret", "bot_ret", "bench_ret", "ew_ret", "ls_ret", "top_vs_ew"]}
    out["top_beats_bench_rate"] = round(float((R["top_ret"] > R["bench_ret"]).mean()), 2)
    out["ls_positive_rate"] = round(float((R["ls_ret"] > 0).mean()), 2)
    out["mean_universe"] = int(R["n_uni"].mean()); out["n_quarters"] = int(len(R))
    return out


if __name__ == "__main__":
    R, B, idx, US, PXM = run(lag=1)
    R.to_csv(os.path.join(OUT, "nav.csv"), index=False); B.to_csv(os.path.join(OUT, "baskets.csv"), index=False)
    m = metrics(R)
    topc = np.cumprod(1 + R["top_ret"].dropna().values)[-1] ** (4 / R["top_ret"].dropna().shape[0]) - 1
    rand = placebo(PXM, US)
    m["placebo"] = dict(actual_top_cagr_pct=round(float(topc) * 100, 1),
                        random_median_cagr_pct=round(float(np.median(rand)) * 100, 1),
                        actual_percentile=round(float((rand < topc).mean()) * 100, 0), n_draws=len(rand))
    R0, _, _, _, _ = run(lag=0, verbose=False); m["ls_lag0"] = metrics(R0)["ls_ret"]
    m["_note"] = ("v2 corrected sources. QUANT-ONLY (no analyst layer), regime-neutralized, Dec-2021..Sep-2024. "
                  "L-S = pure selection; top_vs_ew = selection vs equal-weight size effect; placebo pct = vs random 10-name baskets.")
    json.dump(m, open(os.path.join(OUT, "metrics.json"), "w"), indent=1)
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 5))
        for col, lab, c, w, ls in [("top_ret", "Top 10 by score", "#1D4ED8", 2.4, "-"), ("bot_ret", "Bottom 10 by score", "#B91C1C", 2.0, "-"),
                                   ("ew_ret", "Eligible universe (equal-weight)", "#6B7280", 1.6, "-"), ("bench_ret", "Nifty 500 TRI proxy", "#111827", 1.6, "--")]:
            nav = np.insert(np.cumprod(1 + R[col].fillna(0).values), 0, 1.0)
            ax.plot(range(len(nav)), nav, label=lab, linewidth=w, linestyle=ls, color=c)
        ax.set_title("PIT quant-only backtest v2: growth of Rs 1 (Dec-2021 to Sep-2024, quarterly)", fontsize=11)
        ax.set_xlabel("quarter"); ax.set_ylabel("growth of Rs 1"); ax.legend(fontsize=9); ax.grid(alpha=0.25)
        fig.tight_layout(); fig.savefig(os.path.join(OUT, "nav_chart.png"), dpi=130); print("chart saved")
    except Exception as e:
        print("chart skip", repr(e)[:80])
    print("\n=== METRICS v2 (1-day lag) ==="); print(json.dumps(m, indent=1)); print("saved ->", OUT)
