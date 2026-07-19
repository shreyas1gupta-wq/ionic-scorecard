"""
WAVE-4 SECTOR CONTEXT MODULATOR TEST -- Devika Menon (FM Equities), 2026-07-17.

QUESTION (not "is sector a standalone alpha" -- already KILLed, W2S-11 /
IDG-I-15): does sector-level context (trailing momentum, relative valuation
vs own history, earnings-growth aggregate, breadth) IMPROVE the CONVICTION /
WEIGHTING of the ALPHA_RANKER canonical 7-leg stock score -- i.e. is it a
useful CONTEXT MODULATOR even though it has no standalone edge.

DATA (all trailing/causal, no lookahead):
  rnd/panel/stock_valuation_pit.parquet  -- date,symbol,sector,mktcap,EY,net_profit (PIT)
  rnd/panel/cube_close_long.parquet      -- daily close, wide (for trailing mom + 200DMA)
  rnd/panel/panel_long.parquet           -- date,symbol,sector,fwd_ret_1Y_*,regime_*,mktcap_log
  rnd/panel/canonical_7leg_pit_scores.parquet -- stock-level composite score (PIT-safe version)

SECTOR AGGREGATES (cap-weighted, causal):
  sec_mom_12_1   = cap-wtd stock trailing (t-252d -> t-21d) return
  sec_val_pctile = expanding-window (24mo burn-in) percentile of cap-wtd
                   sector EY vs the SECTOR'S OWN history (higher = cheaper
                   vs own history = value tailwind)
  sec_earn_grow  = cap-wtd YoY net_profit growth (winsorized)
  sec_breadth    = % of sector's names with close > trailing 200DMA
  sector_context = equal-weight avg of cross-sectional (date) z-scores of
                   the 4 legs above -- the "sector tailwind/headwind" score.

TESTS (all against panel_long fwd_ret_1Y, resid basis, 1Y horizon -- the
canonical convention CANONICAL_7LEG_1Y.json uses):
  1. Interaction: 7-leg score's per-date IC computed separately within
     TAILWIND (top-tercile sector_context that date) vs HEADWIND
     (bottom-tercile) stock-months.
  2. Incremental value: blended_score = z(7leg) + w*z(sector_context) run
     through harness.evaluate() for w in {0 (baseline), 0.15, 0.30, 0.50},
     same family/panel so IC/decile/Sharpe/DSR/PBO are apples-to-apples.
  3. Intra-sector vs sector-timing decomposition:
     (a) sector-neutral score  = 7leg score minus its OWN sector's mean that date
     (b) sector-only score     = every stock in a sector gets the sector's
         mean 7leg score that date (pure sector-rotation bet, no stock-picking)
     compared against (c) the raw/global baseline from test 2 (w=0).
  HONESTY: drop-one-sector jackknife on the test-2 headline delta, and an
  era-split (first half vs second half of the 249-month sample).

OUTPUTS: rnd/wave4/SECTOR_CONTEXT.md, rnd/cards/W4SEC_*.json
"""
from __future__ import annotations
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

_THIS = Path(__file__).resolve()
RND_DIR = _THIS.parent.parent
ALPHA_DIR = RND_DIR.parent
sys.path.insert(0, str(RND_DIR / "lib"))
sys.path.insert(0, str(RND_DIR))
import harness  # noqa: E402

PANEL_DIR = RND_DIR / "panel"
CARDS_DIR = RND_DIR / "cards"
WAVE4_DIR = RND_DIR / "wave4"
OUT_MD = WAVE4_DIR / "SECTOR_CONTEXT.md"

HORIZON = "1Y"
BASIS = "resid"
FAMILY = "W4SEC"
MIN_NAMES = 20
BURNIN_MONTHS = 24

log_lines = []
def log(s=""):
    print(s)
    log_lines.append(str(s))


# ==========================================================================
# 1. LOAD
# ==========================================================================
val = pd.read_parquet(PANEL_DIR / "stock_valuation_pit.parquet")
val["date"] = pd.to_datetime(val["date"])
cube = pd.read_parquet(PANEL_DIR / "cube_close_long.parquet")
cube.index = pd.to_datetime(cube.index)
cube = cube.sort_index()
panel = pd.read_parquet(PANEL_DIR / "panel_long.parquet")
panel["date"] = pd.to_datetime(panel["date"])
score7 = pd.read_parquet(PANEL_DIR / "canonical_7leg_pit_scores.parquet")
score7["date"] = pd.to_datetime(score7["date"])

log(f"[DATA] stock_valuation_pit: {val.shape}, sectors={val['sector'].nunique()}, dates={val['date'].nunique()}")
log(f"[DATA] cube_close_long: {cube.shape}")
log(f"[DATA] panel_long: {panel.shape}")
log(f"[DATA] canonical_7leg_pit_scores: {score7.shape}")

dates = sorted(val["date"].unique())
date_pos = {d: i for i, d in enumerate(cube.index)}


# ==========================================================================
# 2. TRAILING STOCK-LEVEL MOMENTUM + 200DMA (from cube_close_long, causal)
# ==========================================================================
log_prices = np.log(cube.replace(0, np.nan))
ma200 = cube.rolling(200, min_periods=150).mean()

mom_rows = []
breadth_rows = []
for d in dates:
    if d not in cube.index:
        continue
    i = cube.index.get_loc(d)
    if i < 252:
        continue
    p_t = cube.iloc[i]
    p_t1m = cube.iloc[i - 21]
    p_t12m = cube.iloc[i - 252]
    mom = (p_t1m / p_t12m) - 1.0
    mom_rows.append(pd.Series(mom, name=d))
    ab = (p_t > ma200.iloc[i]).astype(float)
    ab[p_t.isna() | ma200.iloc[i].isna()] = np.nan
    breadth_rows.append(pd.Series(ab, name=d))

mom_df = pd.DataFrame(mom_rows)
breadth_df = pd.DataFrame(breadth_rows)
mom_long = mom_df.stack().rename("mom_12_1").reset_index()
mom_long.columns = ["date", "symbol", "mom_12_1"]
breadth_long = breadth_df.stack().rename("above200").reset_index()
breadth_long.columns = ["date", "symbol", "above200"]
log(f"[DATA] trailing mom computed: {mom_long.shape[0]} obs, {mom_long['date'].nunique()} dates (needs 252d history, so early dates dropped)")


# ==========================================================================
# 3. STOCK-LEVEL YoY EARNINGS GROWTH (from stock_valuation_pit net_profit, PIT)
# ==========================================================================
npf = val.pivot_table(index="date", columns="symbol", values="net_profit")
npf_yoy = (npf / npf.shift(12)) - 1.0
npf_yoy = npf_yoy.clip(-2.0, 5.0)  # winsorize blow-ups (small denominators)
earn_long = npf_yoy.stack().rename("earn_yoy").reset_index()
earn_long.columns = ["date", "symbol", "earn_yoy"]


# ==========================================================================
# 4. SECTOR AGGREGATES (cap-weighted, per date x sector)
# ==========================================================================
base = val[["date", "symbol", "sector", "mktcap", "EY"]].copy()
base = base.merge(mom_long, on=["date", "symbol"], how="left")
base = base.merge(breadth_long, on=["date", "symbol"], how="left")
base = base.merge(earn_long, on=["date", "symbol"], how="left")


def cw_mean(g, col):
    x = g[[col, "mktcap"]].dropna()
    if len(x) < 3 or x["mktcap"].sum() <= 0:
        return np.nan
    return float((x[col] * x["mktcap"]).sum() / x["mktcap"].sum())


def build_sector_panel():
    rows = []
    for (d, s), g in base.groupby(["date", "sector"]):
        n = g["symbol"].nunique()
        if n < 3:
            continue
        sec_mom = cw_mean(g, "mom_12_1")
        sec_ey = cw_mean(g, "EY")
        sec_earn = cw_mean(g, "earn_yoy")
        bd = g["above200"].dropna()
        sec_breadth = float(bd.mean()) if len(bd) >= 3 else np.nan
        rows.append({"date": d, "sector": s, "n_names": n,
                      "sec_mom_12_1": sec_mom, "sec_EY": sec_ey,
                      "sec_earn_yoy": sec_earn, "sec_breadth": sec_breadth})
    return pd.DataFrame(rows)


sec_panel = build_sector_panel()
log(f"[DATA] sector-month panel: {sec_panel.shape[0]} rows, {sec_panel['sector'].nunique()} sectors, {sec_panel['date'].nunique()} dates")

# expanding causal percentile of sec_EY vs the SECTOR'S OWN history (24mo burn-in)
sec_panel = sec_panel.sort_values(["sector", "date"])


def expanding_pctile(s: pd.Series) -> pd.Series:
    out = np.full(len(s), np.nan)
    vals = s.values
    for i in range(len(vals)):
        if i < BURNIN_MONTHS:
            continue
        hist = vals[: i + 1]
        hist_valid = hist[~np.isnan(hist)]
        if len(hist_valid) < BURNIN_MONTHS or np.isnan(vals[i]):
            continue
        out[i] = (hist_valid <= vals[i]).mean()
    return pd.Series(out, index=s.index)


sec_panel["sec_val_pctile"] = sec_panel.groupby("sector")["sec_EY"].transform(expanding_pctile)

# cross-sectional (across sectors, per date) z-scores -> composite sector_context
def cs_z(s):
    mu, sd = s.mean(), s.std(ddof=0)
    if sd == 0 or np.isnan(sd):
        return s * np.nan
    return (s - mu) / sd


sec_panel["z_mom"] = sec_panel.groupby("date")["sec_mom_12_1"].transform(cs_z)
sec_panel["z_val"] = sec_panel.groupby("date")["sec_val_pctile"].transform(cs_z)
sec_panel["z_earn"] = sec_panel.groupby("date")["sec_earn_yoy"].transform(cs_z)
sec_panel["z_breadth"] = sec_panel.groupby("date")["sec_breadth"].transform(cs_z)
sec_panel["sector_context"] = sec_panel[["z_mom", "z_val", "z_earn", "z_breadth"]].mean(axis=1, skipna=True)
n_legs_present = sec_panel[["z_mom", "z_val", "z_earn", "z_breadth"]].notna().sum(axis=1)
sec_panel.loc[n_legs_present < 2, "sector_context"] = np.nan

sec_ctx = sec_panel[["date", "sector", "sector_context", "sec_mom_12_1", "sec_val_pctile",
                      "sec_earn_yoy", "sec_breadth", "n_names"]].dropna(subset=["sector_context"])
log(f"[DATA] sector_context available: {sec_ctx.shape[0]} sector-months (of {sec_panel.shape[0]} raw; burn-in + coverage drop the rest)")

sec_ctx.to_parquet(PANEL_DIR / "sector_context.parquet", index=False)


# ==========================================================================
# 5. MERGE onto stock-level score + panel fwd returns
# ==========================================================================
stock = score7.merge(panel[["date", "symbol", "sector", "mktcap_log", "regime_trend", "regime_vol",
                             "fwd_ret_1Y_resid", "fwd_ret_1Y_raw"]],
                      on=["date", "symbol"], how="inner")
stock = stock.merge(sec_ctx[["date", "sector", "sector_context"]], on=["date", "sector"], how="inner")
log(f"[DATA] stock-level merged panel (score+sector+returns): {stock.shape[0]} rows, {stock['date'].nunique()} dates")

# per-date tercile bucket of sector_context (computed ACROSS SECTORS that date, not across stocks
# -- i.e. bucket is a property of the sector-month, applied to every stock in that sector)
def tercile_bucket(g):
    try:
        return pd.qcut(g["sector_context"], 3, labels=["headwind", "mid", "tailwind"], duplicates="drop")
    except ValueError:
        return pd.Series(["mid"] * len(g), index=g.index)

sec_ctx = sec_ctx.copy()
sec_ctx["bucket"] = sec_ctx.groupby("date", group_keys=False).apply(tercile_bucket)
stock = stock.merge(sec_ctx[["date", "sector", "bucket"]], on=["date", "sector"], how="left")


# ==========================================================================
# TEST 1 -- interaction: does 7leg IC differ tailwind vs headwind sector-months?
# ==========================================================================
def per_date_ic(df, min_n=MIN_NAMES):
    def _ic(g):
        if len(g) < min_n:
            return np.nan
        rho, _ = stats.spearmanr(g["composite_rank_avg"], g["fwd_ret_1Y_resid"])
        return rho
    return df.groupby("date").apply(_ic, include_groups=False).dropna()


ic_tail = per_date_ic(stock[stock["bucket"] == "tailwind"])
ic_head = per_date_ic(stock[stock["bucket"] == "headwind"])
ic_all = per_date_ic(stock)

log("\n=== TEST 1: interaction (7-leg IC by sector regime bucket) ===")
log(f"tailwind sector-months : IC mean={ic_tail.mean():.4f}  n_dates={len(ic_tail)}")
log(f"headwind sector-months : IC mean={ic_head.mean():.4f}  n_dates={len(ic_head)}")
log(f"all (unconditional)    : IC mean={ic_all.mean():.4f}  n_dates={len(ic_all)}")
log(f"delta (tailwind-headwind) = {ic_tail.mean() - ic_head.mean():.4f}")

# jackknife: drop one sector at a time, recompute the delta
sectors = sorted(stock["sector"].dropna().unique())
jk_deltas = []
for s in sectors:
    sub = stock[stock["sector"] != s]
    it = per_date_ic(sub[sub["bucket"] == "tailwind"])
    ih = per_date_ic(sub[sub["bucket"] == "headwind"])
    if len(it) > 5 and len(ih) > 5:
        jk_deltas.append(it.mean() - ih.mean())
jk_deltas = np.array(jk_deltas)
log(f"drop-one-sector jackknife on delta: min={jk_deltas.min():.4f} max={jk_deltas.max():.4f} "
    f"all-same-sign={bool((jk_deltas > 0).all() or (jk_deltas < 0).all())}")

# era split
mid_date = stock["date"].quantile(0.5)
for era_name, era_mask in [("first_half", stock["date"] <= mid_date), ("second_half", stock["date"] > mid_date)]:
    e = stock[era_mask]
    it = per_date_ic(e[e["bucket"] == "tailwind"])
    ih = per_date_ic(e[e["bucket"] == "headwind"])
    log(f"  era={era_name}: IC tailwind={it.mean():.4f} (n={len(it)}), IC headwind={ih.mean():.4f} (n={len(ih)}), "
        f"delta={it.mean() - ih.mean():.4f}")


# ==========================================================================
# TEST 2 -- incremental value via harness.evaluate (same family, same panel)
# ==========================================================================
log("\n=== TEST 2: incremental IC/decile/Sharpe of score + w*sector_context ===")

def cs_z_col(df, col):
    return df.groupby("date")[col].transform(lambda s: (s - s.mean()) / s.std(ddof=0) if s.std(ddof=0) else np.nan)

stock["z_score7"] = cs_z_col(stock, "composite_rank_avg")
stock["z_sector"] = cs_z_col(stock, "sector_context")

results = {}
for w in [0.0, 0.15, 0.30, 0.50, 1.0]:
    stock["blend"] = stock["z_score7"] + w * stock["z_sector"]
    factor = stock.set_index(["date", "symbol"])["blend"]
    fid = f"W4SEC_blend_w{int(w*100):03d}_1Y"
    card = harness.evaluate(factor, horizon=HORIZON, return_basis=BASIS, factor_id=fid,
                             panel=panel, panel_source="real_panel_long", family=FAMILY,
                             min_names_per_date=MIN_NAMES, cards_dir=CARDS_DIR)
    results[w] = card
    log(f"w={w:.2f}: IC_mean={card['ic']['ic_mean']:.4f} IC_ir={card['ic']['ic_ir']:.4f} "
        f"mono={card['deciles']['monotonicity']:.3f} ann_LS_net={card['costs']['net_of_cost_ann_return']:.4f} "
        f"PBO={card['pbo']['pbo']:.3f} verdict={card['verdict']}")

base_ic = results[0.0]["ic"]["ic_mean"]
best_w = max([w for w in results if w > 0], key=lambda w: results[w]["ic"]["ic_mean"])
best_delta = results[best_w]["ic"]["ic_mean"] - base_ic
log(f"\nbest incremental w={best_w}: IC delta vs w=0 baseline = {best_delta:+.4f} "
    f"({'IMPROVES' if best_delta > 0 else 'DOES NOT IMPROVE'})")

# drop-one-sector jackknife on the incremental IC delta at best_w
log("drop-one-sector jackknife on incremental IC delta @ best_w:")
jk2 = []
for s in sectors:
    sub = stock[stock["sector"] != s].copy()
    sub["blend0"] = sub["z_score7"]
    sub["blendW"] = sub["z_score7"] + best_w * sub["z_sector"]
    f0 = sub.set_index(["date", "symbol"])["blend0"]
    fW = sub.set_index(["date", "symbol"])["blendW"]
    c0 = harness.evaluate(f0, horizon=HORIZON, return_basis=BASIS, factor_id=f"jk_tmp0_{s}",
                           panel=panel, panel_source="real_panel_long", family="W4SEC_JK",
                           min_names_per_date=MIN_NAMES, write_card=False)
    cW = harness.evaluate(fW, horizon=HORIZON, return_basis=BASIS, factor_id=f"jk_tmpW_{s}",
                           panel=panel, panel_source="real_panel_long", family="W4SEC_JK",
                           min_names_per_date=MIN_NAMES, write_card=False)
    d = cW["ic"]["ic_mean"] - c0["ic"]["ic_mean"]
    jk2.append((s, d))
jk2_deltas = np.array([d for _, d in jk2])
log(f"  n_sectors_tested={len(jk2_deltas)}, delta range=[{jk2_deltas.min():+.4f}, {jk2_deltas.max():+.4f}], "
    f"all-positive={bool((jk2_deltas > 0).all())}, n_negative={(jk2_deltas <= 0).sum()}")
worst = sorted(jk2, key=lambda x: x[1])[:3]
log(f"  worst 3 sectors when dropped (i.e. delta most reduced by their absence): {worst}")

# era split on incremental delta @ best_w
log("era-split on incremental IC delta @ best_w:")
for era_name, era_mask in [("first_half", stock["date"] <= mid_date), ("second_half", stock["date"] > mid_date)]:
    e = stock[era_mask].copy()
    e["blend0"] = e["z_score7"]
    e["blendW"] = e["z_score7"] + best_w * e["z_sector"]
    f0 = e.set_index(["date", "symbol"])["blend0"]
    fW = e.set_index(["date", "symbol"])["blendW"]
    c0 = harness.evaluate(f0, horizon=HORIZON, return_basis=BASIS, factor_id=f"era_tmp0_{era_name}",
                           panel=panel, panel_source="real_panel_long", family="W4SEC_ERA",
                           min_names_per_date=MIN_NAMES, write_card=False)
    cW = harness.evaluate(fW, horizon=HORIZON, return_basis=BASIS, factor_id=f"era_tmpW_{era_name}",
                           panel=panel, panel_source="real_panel_long", family="W4SEC_ERA",
                           min_names_per_date=MIN_NAMES, write_card=False)
    log(f"  {era_name}: IC base={c0['ic']['ic_mean']:.4f} IC blend={cW['ic']['ic_mean']:.4f} "
        f"delta={cW['ic']['ic_mean'] - c0['ic']['ic_mean']:+.4f}")


# ==========================================================================
# TEST 3 -- intra-sector vs sector-timing decomposition
# ==========================================================================
log("\n=== TEST 3: intra-sector vs sector-timing decomposition ===")
stock["sector_mean_score"] = stock.groupby(["date", "sector"])["z_score7"].transform("mean")
stock["sector_neutral_score"] = stock["z_score7"] - stock["sector_mean_score"]
stock["sector_only_score"] = stock["sector_mean_score"]

f_neutral = stock.set_index(["date", "symbol"])["sector_neutral_score"]
f_sectoronly = stock.set_index(["date", "symbol"])["sector_only_score"]

c_neutral = harness.evaluate(f_neutral, horizon=HORIZON, return_basis=BASIS, factor_id="W4SEC_sector_neutral_1Y",
                              panel=panel, panel_source="real_panel_long", family=FAMILY,
                              min_names_per_date=MIN_NAMES, cards_dir=CARDS_DIR)
c_sectoronly = harness.evaluate(f_sectoronly, horizon=HORIZON, return_basis=BASIS, factor_id="W4SEC_sector_only_1Y",
                                 panel=panel, panel_source="real_panel_long", family=FAMILY,
                                 min_names_per_date=MIN_NAMES, cards_dir=CARDS_DIR)

log(f"global (cross-sector) 7-leg score IC   = {base_ic:.4f}  (w=0 baseline, test 2)")
log(f"sector-NEUTRAL (intra-sector only) IC  = {c_neutral['ic']['ic_mean']:.4f}  "
    f"(delta vs global = {c_neutral['ic']['ic_mean'] - base_ic:+.4f})")
log(f"sector-ONLY (pure sector-rotation) IC  = {c_sectoronly['ic']['ic_mean']:.4f}  "
    f"n_dates={c_sectoronly['ic']['n_ic_dates']}")
log(f"sector-only ann_LS_net={c_sectoronly['costs']['net_of_cost_ann_return']:.4f} "
    f"PBO={c_sectoronly['pbo']['pbo']:.3f} verdict={c_sectoronly['verdict']}")

intra_share = (c_neutral["ic"]["ic_mean"] / base_ic) if base_ic else float("nan")
log(f"intra-sector share of global IC = {intra_share:.3f} "
    f"({'edge is essentially intra-sector' if intra_share > 0.85 else 'sector positioning contributes materially'})")


# ==========================================================================
# WRITE MARKDOWN REPORT
# ==========================================================================
WAVE4_DIR.mkdir(parents=True, exist_ok=True)
md = ["# W4SEC -- Sector Context as a Conviction Modulator (not standalone alpha)",
      "",
      "Devika Menon (FM Equities), 2026-07-17. Tests whether sector-level trailing",
      "context (momentum, relative valuation vs own history, earnings-growth,",
      "breadth) improves the ALPHA_RANKER 7-leg stock score's conviction/weighting.",
      "Standalone sector rotation is ALREADY KILLED (W2S-11, IDG-I-15) -- this is",
      "NOT re-litigating that; it is the context-modulator question only.",
      "",
      "## Data", ]
md += [f"- {l}" for l in log_lines if l.startswith("[DATA]")]
md += ["", "## Full run log", "```", *log_lines, "```"]
OUT_MD.write_text("\n".join(md), encoding="utf-8")
log(f"\n[WRITTEN] {OUT_MD}")
