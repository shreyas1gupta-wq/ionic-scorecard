"""
build_exit_trigger.py
======================
Builder-agent implementation of EXIT_TRIGGER_SPEC.md, LEGS 1-3 ONLY.
(Leg 4 -- technical stop/trim, spec section 3.5 -- is present in the spec as of 2026-07-18 but is
explicitly OUT OF SCOPE for this pass per the task brief: "if leg 4 is present when you read it,
note it but do NOT implement it -- build ONLY legs 1-3 in this pass". Confirmed present, not built.)

Owner: quant-head-arjun-rao (E-004). Spec owner: fm-fundamental-sanjay-kulkarni (E-017).
Reads all thresholds from exit_weights_v1.json -- nothing hard-coded here (determinism contract,
same discipline as SCORECARD_BLUEPRINT.md Section 4). Run twice -> byte-identical parquet (checked
at the bottom of this script).

Does NOT touch rel_score_*.parquet / absolute_scorecard.parquet (overlay only, per spec Section 0).
Does NOT pull new data -- every input below is an already-on-disk file cited in the spec's own
data-lineage table.

HISTORICAL-OVERLAY SIMULATION (this is a backtest overlay, not a live process; task-specified,
NOT part of the locked spec, judgment call flagged below):
  entry_date(symbol) = first date at which rel_score_1Y OR rel_score_5Y reaches the top quintile
  (rel_score >= 60, since rel_score = 200*(rank_pct-0.5) in [-100,100] and top quintile is
  rank_pct >= 0.80). If both horizons cross, the EARLIER date is used ("first appearance").
  [MY CALL -- exit_weights_v1.json:entry_screen_judgment_call]
"""
import json
import hashlib
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # ALPHA_RANKER/
PANEL_DIR = ROOT / "rnd" / "panel"
SCORECARD_DIR = ROOT / "rnd" / "scorecard"
WAVE4_DIR = ROOT / "rnd" / "wave4"
RESULTS_DIR = ROOT / "results"

OUT_PARQUET = SCORECARD_DIR / "exit_trigger_flags.parquet"
WEIGHTS_PATH = SCORECARD_DIR / "exit_weights_v1.json"

LOG = []


def log(msg):
    print(msg)
    LOG.append(msg)


def load_weights():
    with open(WEIGHTS_PATH, "r") as f:
        return json.load(f)


def to_dt(s):
    return pd.to_datetime(s).astype("datetime64[ns]")


def build():
    t0 = time.time()
    W = load_weights()

    # ---------------------------------------------------------------
    # 1. LOAD -- base grain = panel_pit.parquet (task-specified grain)
    # ---------------------------------------------------------------
    panel = pd.read_parquet(PANEL_DIR / "panel_pit.parquet",
                             columns=["date", "symbol", "sector",
                                      "fwd_ret_1M_raw", "fwd_ret_1Y_raw"])
    panel["date"] = to_dt(panel["date"])
    log(f"[DATA] panel_pit.parquet rows={len(panel)} "
        f"date range {panel['date'].min().date()}..{panel['date'].max().date()}")
    base_rows = len(panel)

    # 2. stock_valuation_pit.parquet -- PE per name, PIT
    val = pd.read_parquet(PANEL_DIR / "stock_valuation_pit.parquet",
                           columns=["date", "symbol", "PE"])
    val["date"] = to_dt(val["date"])
    log(f"[DATA] stock_valuation_pit.parquet rows={len(val)}")

    # 3. w5bv_stock_percentiles.parquet -- cross-sectional richness percentile
    w5bv = pd.read_parquet(PANEL_DIR / "w5bv_stock_percentiles.parquet",
                            columns=["date", "symbol", "expensive_pctile_PE"])
    w5bv["date"] = to_dt(w5bv["date"])
    log(f"[DATA] w5bv_stock_percentiles.parquet rows={len(w5bv)}")

    # 4. absolute_scorecard.parquet -- PE_current/PE_fair/rerating (horizon-invariant, verified;
    #    take the '1Y' slice as the representative row)
    abs_sc = pd.read_parquet(SCORECARD_DIR / "absolute_scorecard.parquet",
                              columns=["date", "symbol", "horizon", "PE_current", "PE_fair", "rerating"])
    abs_sc["date"] = to_dt(abs_sc["date"])
    abs_sc = abs_sc[abs_sc["horizon"] == "1Y"].drop(columns=["horizon"])
    log(f"[DATA] absolute_scorecard.parquet (1Y slice) rows={len(abs_sc)}")

    # 5. sector_context.parquet -- sec_earn_yoy for the idiosyncratic-vs-macro filter
    secctx = pd.read_parquet(PANEL_DIR / "sector_context.parquet",
                              columns=["date", "sector", "sec_earn_yoy"])
    secctx["date"] = to_dt(secctx["date"])
    log(f"[DATA] sector_context.parquet rows={len(secctx)}")

    # 6. _w6fg2_scored.parquet -- earnings_confirm_v2 / composite_v2_confirmed, PIT via available_date
    #    (already resolved onto the grid date by the upstream builder, per SCORECARD_BLUEPRINT.md; used as-is)
    w6fg2 = pd.read_parquet(WAVE4_DIR / "_w6fg2_scored.parquet",
                             columns=["date", "symbol", "earnings_confirm_v2", "composite_v2_confirmed"])
    w6fg2["date"] = to_dt(w6fg2["date"])
    log(f"[DATA] _w6fg2_scored.parquet rows={len(w6fg2)}")

    # 7/8. rel_score_1Y.parquet / rel_score_5Y.parquet -- entry-thesis trigger + quality_score
    rel1y = pd.read_parquet(SCORECARD_DIR / "rel_score_1Y.parquet",
                             columns=["date", "symbol", "rel_score_1Y", "quality_score"])
    rel1y["date"] = to_dt(rel1y["date"])
    rel5y = pd.read_parquet(SCORECARD_DIR / "rel_score_5Y.parquet",
                             columns=["date", "symbol", "rel_score_5Y"])
    rel5y["date"] = to_dt(rel5y["date"])
    log(f"[DATA] rel_score_1Y.parquet rows={len(rel1y)}, rel_score_5Y.parquet rows={len(rel5y)}")

    # 9/10. forensic score + flags -- LIVE CURRENT-STATE SNAPSHOTS (no date column -- see WEIGHTS note)
    forensic_score = pd.read_parquet(RESULTS_DIR / "universe_forensic_score.parquet",
                                      columns=["symbol", "forensic_risk_score_0_100"])
    forensic_flags = pd.read_parquet(RESULTS_DIR / "universe_forensic_flags.parquet",
                                      columns=["symbol", "flag", "data_status", "badness"])
    log(f"[DATA] universe_forensic_score.parquet rows={len(forensic_score)} (STATIC, no date column)")
    log(f"[DATA] universe_forensic_flags.parquet rows={len(forensic_flags)} (STATIC, no date column)")

    severe_names = W["leg3_forensic_override"]["severe_flag_names"]
    severe = forensic_flags[
        forensic_flags["flag"].isin(severe_names)
        & (forensic_flags["data_status"] == "ok")
        & (forensic_flags["badness"] >= W["leg3_forensic_override"]["severe_flag_badness_min"])
    ]
    has_severe_flag = severe.groupby("symbol").size().gt(0)
    has_severe_flag.name = "has_severe_flag"

    forensic_static = forensic_score.set_index("symbol").join(has_severe_flag, how="left")
    forensic_static["has_severe_flag"] = forensic_static["has_severe_flag"].fillna(False)
    forensic_static["leg3_stageA_static"] = (
        (forensic_static["forensic_risk_score_0_100"] >= W["leg3_forensic_override"]["stage_a_score_threshold"])
        | forensic_static["has_severe_flag"]
    )
    n_static_flagged = int(forensic_static["leg3_stageA_static"].sum())
    log(f"[INFERENCE] forensic Stage-A static tripwire: {n_static_flagged}/{len(forensic_static)} "
        f"names flagged on CURRENT snapshot (score>=70 or severe confirmed flag)")

    # ---------------------------------------------------------------
    # MERGE everything onto the panel_pit grain
    # ---------------------------------------------------------------
    df = panel.merge(val, on=["date", "symbol"], how="left")
    df = df.merge(w5bv, on=["date", "symbol"], how="left")
    df = df.merge(abs_sc, on=["date", "symbol"], how="left")
    df = df.merge(secctx, on=["date", "sector"], how="left")
    df = df.merge(w6fg2, on=["date", "symbol"], how="left")
    df = df.merge(rel1y, on=["date", "symbol"], how="left")
    df = df.merge(rel5y, on=["date", "symbol"], how="left")
    assert len(df) == base_rows, f"merge changed row count: {base_rows} -> {len(df)}"
    log(f"[INFERENCE] merged panel shape={df.shape} (row count preserved: {base_rows})")

    df = df.sort_values(["symbol", "date"]).reset_index(drop=True)

    # ---------------------------------------------------------------
    # own_trailing_pctile(t) -- rolling N-year (8yr default) percentile of PE within the
    # stock's OWN history (spec Section 1.2). Computed on the full stock_valuation_pit series
    # (not restricted to the panel_pit grain) so the trailing window has full history available,
    # then merged onto the panel grain.
    # ---------------------------------------------------------------
    win_years = W["leg1_valuation_ceiling"]["own_trailing_window_years"]
    win_str = f"{int(win_years * 365.25)}D"
    val_pe = val.dropna(subset=["PE"]).sort_values(["symbol", "date"]).copy()

    def _own_pctile(g):
        s = g.set_index("date")["PE"]
        return s.rolling(win_str, min_periods=1).apply(
            lambda a: (a <= a[-1]).mean() if len(a) else np.nan, raw=True
        ).values

    log(f"[INFERENCE] computing own_trailing_pctile (rolling {win_years}yr window) over "
        f"{val_pe['symbol'].nunique()} symbols, {len(val_pe)} rows ...")
    t_roll0 = time.time()
    parts = []
    for sym, g in val_pe.groupby("symbol", sort=False):
        vals = _own_pctile(g)
        parts.append(pd.DataFrame({"symbol": sym, "date": g["date"].values, "own_trailing_pctile": vals}))
    own_pctile_df = pd.concat(parts, ignore_index=True)
    log(f"[INFERENCE] own_trailing_pctile computed in {time.time()-t_roll0:.1f}s")

    df = df.merge(own_pctile_df, on=["date", "symbol"], how="left")
    assert len(df) == base_rows

    # ---------------------------------------------------------------
    # ENTRY-DATE SIMULATION (historical-overlay judgment call, see module docstring)
    # ---------------------------------------------------------------
    thr = W["entry_screen_judgment_call"]["rel_score_top_quintile_threshold"]
    e1 = df.loc[df["rel_score_1Y"] >= thr].groupby("symbol")["date"].min().rename("entry_1Y")
    e5 = df.loc[df["rel_score_5Y"] >= thr].groupby("symbol")["date"].min().rename("entry_5Y")
    entry = pd.concat([e1, e5], axis=1)
    entry["entry_date"] = entry[["entry_1Y", "entry_5Y"]].min(axis=1)
    entry["entry_source"] = np.select(
        [entry["entry_date"] == entry["entry_1Y"], entry["entry_date"] == entry["entry_5Y"]],
        ["rel_score_1Y", "rel_score_5Y"], default="UNKNOWN")
    n_with_entry = entry["entry_date"].notna().sum()
    log(f"[INFERENCE] entry_date simulated for {n_with_entry}/{entry.shape[0]} symbols "
        f"that ever reached rel_score>={thr} top-quintile (1Y or 5Y)")

    df = df.merge(entry[["entry_date", "entry_source"]], on="symbol", how="left")
    assert len(df) == base_rows

    # entry-time snapshot values (PE, rerating, earnings_confirm_v2, composite_v2_confirmed, quality_score)
    at_entry = df.loc[df["date"] == df["entry_date"],
                       ["symbol", "PE", "rerating", "earnings_confirm_v2",
                        "composite_v2_confirmed", "quality_score"]].drop_duplicates(subset=["symbol"])
    at_entry = at_entry.rename(columns={
        "PE": "PE_entry", "rerating": "rerating_entry",
        "earnings_confirm_v2": "earnings_confirm_v2_entry",
        "composite_v2_confirmed": "composite_v2_confirmed_entry",
        "quality_score": "quality_score_entry",
    })
    df = df.merge(at_entry, on="symbol", how="left")
    assert len(df) == base_rows

    # entry_thesis_type
    rr_thr = W["entry_thesis_type"]["rerating_at_entry_threshold"]
    conditions = [
        df["rerating_entry"].isna(),
        df["rerating_entry"] > rr_thr,
    ]
    choices = ["UNKNOWN", "VALUE_GROWTH"]
    df["entry_thesis_type"] = np.select(conditions, choices, default="MOMENTUM")
    # not-yet-entered rows: no thesis assigned yet
    not_yet_entered = df["entry_date"].isna() | (df["date"] < df["entry_date"])
    df.loc[not_yet_entered, "entry_thesis_type"] = "UNKNOWN"
    held = ~not_yet_entered  # date >= entry_date, i.e. currently "held" in the simulation

    n_vg = ((df["entry_thesis_type"] == "VALUE_GROWTH") & held).sum()
    n_mo = ((df["entry_thesis_type"] == "MOMENTUM") & held).sum()
    n_unk_held = ((df["entry_thesis_type"] == "UNKNOWN") & held).sum()
    log(f"[INFERENCE] post-entry rows: held={held.sum()}, thesis breakdown "
        f"VALUE_GROWTH={n_vg}, MOMENTUM={n_mo}, UNKNOWN(no rerating at entry)={n_unk_held}")

    # ---------------------------------------------------------------
    # LEG 1 -- valuation-ceiling exit (Jain-style), spec Section 1.3
    # ---------------------------------------------------------------
    L1 = W["leg1_valuation_ceiling"]
    richness_vs_entry = df["PE"] / df["PE_entry"]
    richness_cross_sec = df["expensive_pctile_PE"]
    richness_vs_fair = df["PE_current"] / df["PE_fair"]

    cond_a = df["entry_thesis_type"] == "VALUE_GROWTH"
    cond_b = (
        (richness_vs_entry >= L1["round_trip_ratio_min"])
        | (df["own_trailing_pctile"] >= L1["own_trailing_pctile_min"])
        | (richness_cross_sec >= L1["cross_sectional_pctile_min"])
    )
    cond_c = richness_vs_fair >= L1["richness_vs_fair_min"]
    df["leg1_valuation_ceiling"] = (cond_a & cond_b & cond_c & held).fillna(False)

    # ---------------------------------------------------------------
    # LEG 2 -- fundamental-deterioration exit (Fisher-style), spec Section 2.4
    # ---------------------------------------------------------------
    L2 = W["leg2_fundamental_deterioration"]
    growth_decel = (
        (df["earnings_confirm_v2_entry"] == 1)
        & (df["earnings_confirm_v2"] == 0)
        & (df["composite_v2_confirmed"] < df["composite_v2_confirmed_entry"])
    )
    entry_decile = np.clip(np.ceil(df["quality_score_entry"] * 10), 1, 10)
    current_decile = np.clip(np.ceil(df["quality_score"] * 10), 1, 10)
    quality_drop = current_decile < (entry_decile - L2["quality_drop_deciles_min"])
    idiosyncratic = df["sec_earn_yoy"] >= 0
    df["leg2_fundamental_deterioration"] = (
        growth_decel & quality_drop & idiosyncratic & held
    ).fillna(False)

    # ---------------------------------------------------------------
    # LEG 3 -- forensic override, Stage A tripwire only (spec Section 3.2)
    # STATIC current-snapshot data (no PIT history on disk) -> applied ONLY to each symbol's
    # LAST date in the panel to avoid lookahead. See exit_weights_v1.json note.
    # ---------------------------------------------------------------
    last_date_per_symbol = df.groupby("symbol")["date"].transform("max")
    is_last_date = df["date"] == last_date_per_symbol
    df = df.merge(
        forensic_static[["leg3_stageA_static"]].rename_axis("symbol").reset_index(),
        on="symbol", how="left"
    )
    assert len(df) == base_rows
    df["leg3_stageA_static"] = df["leg3_stageA_static"].fillna(False)
    df["leg3_forensic_veto"] = (df["leg3_stageA_static"] & is_last_date & held).fillna(False)
    df["leg3_requires_analyst_confirmation"] = df["leg3_forensic_veto"]  # never auto-confirmed in this build

    # ---------------------------------------------------------------
    # any_leg_fired + composite_exit_flag (legs 1-3 combination only, per spec Section 4,
    # with the forensic "confirmed override" branch never reachable since Stage B needs a human)
    # ---------------------------------------------------------------
    df["any_leg_fired"] = (
        df["leg1_valuation_ceiling"] | df["leg2_fundamental_deterioration"] | df["leg3_forensic_veto"]
    )

    conds = [
        df["leg3_forensic_veto"],
        df["leg1_valuation_ceiling"] & df["leg2_fundamental_deterioration"],
        df["leg1_valuation_ceiling"],
        df["leg2_fundamental_deterioration"],
    ]
    choices = ["WATCH", "EXIT_NOW", "TRIM", "TRIM"]
    # NOTE: leg3_forensic_veto here is the STAGE-A TRIPWIRE, not a confirmed hard veto -- it maps
    # to WATCH (per spec: "WATCH if leg3_pending_confirmation==TRUE, Stage A only, Stage B pending"),
    # NOT EXIT_NOW. EXIT_NOW is reserved for a genuinely confirmed override, which never happens here.
    df["composite_exit_flag"] = np.select(conds, choices, default="NONE")

    def _notes(row):
        bits = []
        if row["leg1_valuation_ceiling"]:
            bits.append("leg1:valuation-ceiling")
        if row["leg2_fundamental_deterioration"]:
            bits.append("leg2:fundamental-deterioration")
        if row["leg3_forensic_veto"]:
            bits.append("leg3:STAGE-A-TRIPWIRE-ONLY(requires analyst filing-read confirmation before acting)")
        return "; ".join(bits) if bits else ""

    df["notes"] = df.apply(_notes, axis=1)

    # ---------------------------------------------------------------
    # FINAL OUTPUT COLUMNS
    # ---------------------------------------------------------------
    out_cols = [
        "date", "symbol", "entry_thesis_type", "entry_date",
        "leg1_valuation_ceiling", "leg2_fundamental_deterioration",
        "leg3_forensic_veto", "leg3_requires_analyst_confirmation",
        "any_leg_fired", "composite_exit_flag", "notes",
    ]
    out = df[out_cols].sort_values(["symbol", "date"]).reset_index(drop=True)

    log(f"[INFERENCE] final output shape={out.shape}")
    log(f"[INFERENCE] incidence -- leg1 fired rows: {int(df['leg1_valuation_ceiling'].sum())}")
    log(f"[INFERENCE] incidence -- leg2 fired rows: {int(df['leg2_fundamental_deterioration'].sum())}")
    log(f"[INFERENCE] incidence -- leg3 fired rows (Stage-A, last-date-only): {int(df['leg3_forensic_veto'].sum())}")
    log(f"[INFERENCE] incidence -- any_leg_fired rows: {int(df['any_leg_fired'].sum())}")
    log(f"[INFERENCE] held (post-entry) rows total: {int(held.sum())} / {base_rows}")

    return out, df, held, log_str_join()


def log_str_join():
    return "\n".join(LOG)


def sha256_of_parquet(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    out, df_full, held, _ = build()
    out.to_parquet(OUT_PARQUET, index=False)
    log(f"[DATA] wrote {OUT_PARQUET} rows={len(out)}")

    # ---- determinism check: rebuild and compare ----
    log("[CHECK] re-running build for determinism check (byte-identical parquet required) ...")
    LOG.clear()
    out2, _, _, _ = build()
    tmp_path = OUT_PARQUET.with_name("exit_trigger_flags_run2_tmp.parquet")
    out2.to_parquet(tmp_path, index=False)
    h1 = sha256_of_parquet(OUT_PARQUET)
    h2 = sha256_of_parquet(tmp_path)
    identical = h1 == h2
    print(f"[CHECK] run1 sha256={h1}")
    print(f"[CHECK] run2 sha256={h2}")
    print(f"[CHECK] DETERMINISM: {'PASS -- byte-identical' if identical else 'FAIL -- outputs differ'}")
    tmp_path.unlink()

    # dump full log to disk for the report step
    with open(SCORECARD_DIR / "_build_exit_trigger_log.txt", "w") as f:
        f.write(log_str_join())
        f.write(f"\n\n[CHECK] run1 sha256={h1}\n[CHECK] run2 sha256={h2}\n"
                f"[CHECK] DETERMINISM: {'PASS' if identical else 'FAIL'}\n")

    return out, df_full, held, identical


if __name__ == "__main__":
    main()
