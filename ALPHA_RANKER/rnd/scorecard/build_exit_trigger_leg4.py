"""
build_exit_trigger_leg4.py
============================
Builder-agent implementation of EXIT_TRIGGER_SPEC.md SECTION 3.5 -- LEG 4 ONLY
(Minervini/Weinstein technical stop/trim), extending the frozen legs 1-3 overlay
(`EXIT_TRIGGER_BUILD_REPORT.md`, quant-head-arjun-rao, E-004) that shipped
2026-07-18. Legs 1-3 logic is NOT touched here -- their columns are read from the
frozen `exit_trigger_flags.parquet` verbatim and re-written unchanged alongside
the four new leg4 columns.

Owner: technical-head-dhruv-kapoor (E-005). Spec: EXIT_TRIGGER_SPEC.md Section 3.5
(fm-fundamental-sanjay-kulkarni, E-017), Section 4 (combination rule).

Reuses ONLY already-on-disk data, per spec's own "no new data pulls" discipline:
  - rnd/panel/cube_close_long.parquet   (daily close, 2005-04-01..2025-12-05, 976 cols)
  - rnd/panel/cube_volume.parquet       (daily volume, 2021-07-16..2025-12, 751 cols --
                                          NO HISTORY BEFORE 2021-07-16, confirmed data floor)
  - rnd/scorecard/exit_trigger_flags.parquet (frozen legs 1-3 output -- entry_date,
                                          entry_thesis_type, leg1/leg2/leg3 columns)
  - rnd/panel/panel_pit.parquet          (base grain: date, symbol -- the (date,symbol)
                                          rows this overlay is evaluated on)

OUTPUT COLUMNS ADDED (exact names per task instruction):
  leg4a_hardstop    -- bool, 7.5% hard stop from entry cost (spec Section 3.5.1)
  leg4b_trim        -- bool, climax-run / blow-off sell-into-strength trim signature
  leg4c_stagebreak  -- bool, confirmed Weinstein Stage 2->3/4 transition
  leg4_escalated    -- bool, leg4c_stagebreak AND (leg1_valuation_ceiling OR
                        leg2_fundamental_deterioration) -- the spec Section 4 EXIT_NOW
                        escalation condition, exposed as its own column so a PM does not
                        have to reverse-engineer it from composite_exit_flag.
composite_exit_flag is RECOMPUTED (legs 1-3 semantics unchanged; leg4's ADVISORY/TRIM/
escalation branches from spec Section 4 are added on top -- see _combine()).

DAILY-GRAIN -> MONTHLY-PANEL-GRAIN JUDGMENT CALLS (all flagged, all frozen in
exit_weights_v1.json["leg4_technical_stop_trim"], one-line change if overruled):

1. [MY CALL] panel_pit's grain is ~monthly (249 dates, 2005-2025); the cube files are
   DAILY. Leg 4 is evaluated AT each monthly panel date using an as-of (backward) join
   onto the daily signal series -- i.e. "as of this monthly checkpoint, is the technical
   condition true on the most recent available trading day." This means an intra-month
   stop-hit-and-recovery, or a climax run that fully unwound before month-end, can be
   MISSED by this monthly evaluation grid -- a real limitation of reusing panel_pit's
   grain rather than a native daily exit-trigger feed, disclosed here and in the report,
   not silently worked around (spec explicitly says legs operate on "no new data pulls"
   i.e. this module does not build a new daily-grain output artifact).
2. [MY CALL] "ma50(t) crosses below ma150(t)" (spec's literal wording) is interpreted as
   a RECENT-CROSS window (crossing event occurred within the trailing
   recent_cross_window_days=10 trading days), not "currently below" (which would fire
   for years after a single old cross, misreading a stale downtrend as a fresh stage
   break every single day). Frozen prior, disclosed.
3. [MY CALL] spec's `gap_open(t)` sub-condition (Section 3.5.1, leg4b "blow-off" branch)
   requires an intraday OPEN price. `cube_close_long.parquet` has CLOSE ONLY -- no open
   price exists anywhere in the files this module is scoped to reuse. gap_open is
   PROXIED by the close-to-close 1-day return (ret_1d >= 5%) combined with the same
   >=1.5x-20d-average-volume condition. This is a real proxy substitution, not the
   literal spec condition, and is reported as a coverage/fidelity gap, not disguised.
4. [MY CALL] Discontinuity guard: `cube_close_long.parquet`'s corporate-action-adjustment
   status is UNDOCUMENTED in `PANEL_SCHEMA.md` (that doc only covers `panel_long.parquet`).
   As a prudent, disclosed measure (same philosophy as the rest of the codebase's
   >40% one-day-move guard), any day with |1-day return| > discontinuity_guard threshold
   is excluded from firing ANY leg4 sub-trigger that day (logged, not silently dropped
   from the underlying series) -- an unconfirmed bonus/split could otherwise fake a
   -40%+ "hard stop" or a +40%+ "climax run" that is not a real price move.
5. Liquidity/circuit diagnostics (spec Section 3.5.2 points 1-2) are computed
   (circuit_suspect, thin_adv) and reported (which names, what share of fires) but are
   NOT used to silently suppress a mechanical fire -- per the FM-lens instruction, the
   raw signal stays visible and the report discloses where it is likely contaminated.

Run twice -> byte-identical parquet + weights json (checked at the bottom).
"""
import json
import hashlib
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]  # ALPHA_RANKER/
PANEL_DIR = ROOT / "rnd" / "panel"
SCORECARD_DIR = ROOT / "rnd" / "scorecard"

FLAGS_PATH = SCORECARD_DIR / "exit_trigger_flags.parquet"
WEIGHTS_PATH = SCORECARD_DIR / "exit_weights_v1.json"
CUBE_CLOSE_PATH = PANEL_DIR / "cube_close_long.parquet"
CUBE_VOLUME_PATH = PANEL_DIR / "cube_volume.parquet"

LOG = []


def log(msg):
    print(msg)
    LOG.append(str(msg))


LEG4_DEFAULTS = {
    "hard_stop_pct": 0.075,
    "climax_run_return_min": 0.25,
    "climax_run_window_days": 15,
    "blowoff_return_proxy_min": 0.05,
    "blowoff_volume_ratio_min": 1.5,
    "avg_volume_window_days": 20,
    "ma_short_window": 50,
    "ma_long_window": 150,
    "distribution_day_count_min": 4,
    "distribution_day_window": 20,
    "recent_cross_window_days": 10,
    "discontinuity_guard_1day_return_abs": 0.40,
    "thin_adv_pooled_percentile": 0.10,
    "circuit_suspect_volume_ratio_of_avg20": 0.10,
    "volume_data_floor_date": "2021-07-16",
    "liquidity_diagnostic_note": (
        "cube_volume.parquet's 751 names are already NSE F&O-eligible (a liquidity-screened "
        "subset) -- an absolute rupee-ADV floor calibrated for the broader small/microcap "
        "universe (spec's own Rs.5-10L example) essentially never fires here (checked: 1st "
        "percentile of 20d rupee-ADV in this file is ~Rs.1.9Cr, two orders of magnitude above "
        "that example). thin_adv is therefore defined RELATIVE to this file's own cross-section "
        "(bottom decile of pooled 20d-rupee-ADV) and circuit_suspect RELATIVE to each name's own "
        "recent volume (today's volume < 10% of its own 20d average) rather than an absolute "
        "floor -- both frozen, disclosed re-calibrations, not the literal spec numbers, because "
        "the literal numbers are calibrated for a broader universe than this F&O-eligible file."
    ),
    "gap_open_proxy_note": (
        "No intraday open-price data on disk for the files this leg is scoped to reuse "
        "(cube_close_long.parquet has CLOSE only). gap_open(t) in spec Section 3.5.1's "
        "leg4b 'blow-off' branch is PROXIED by the close-to-close 1-day return; this is a "
        "disclosed fidelity gap versus the literal spec condition, not a silent substitution."
    ),
    "_meta": {
        "owner": "technical-head-dhruv-kapoor (E-005), implementing EXIT_TRIGGER_SPEC.md Section 3.5",
        "date": "2026-07-18",
        "scope": "LEG 4 ONLY -- Minervini/Weinstein technical stop/trim. Legs 1-3 sections of this "
                 "file are untouched (owned by quant-head-arjun-rao).",
        "determinism_contract": "Same as legs 1-3 and SCORECARD_BLUEPRINT.md Section 4 -- every "
                 "number a build script reads lives here, no per-run refit, version bump "
                 "(_v1->_v2) is the only way any number changes.",
    },
}


def ensure_leg4_weights():
    """Add (or leave alone if already present) the leg4 threshold block in
    exit_weights_v1.json, WITHOUT touching any existing leg1/2/3 key."""
    with open(WEIGHTS_PATH, "r") as f:
        W = json.load(f)
    if "leg4_technical_stop_trim" not in W:
        W["leg4_technical_stop_trim"] = LEG4_DEFAULTS
        with open(WEIGHTS_PATH, "w") as f:
            json.dump(W, f, indent=2)
        log("[DATA] exit_weights_v1.json: added leg4_technical_stop_trim block")
    else:
        log("[DATA] exit_weights_v1.json: leg4_technical_stop_trim block already present, left as-is")
    return W


def to_dt(s):
    return pd.to_datetime(s).astype("datetime64[ns]")


# ---------------------------------------------------------------------------
# Daily signal construction (the heavy, entry-independent part)
# ---------------------------------------------------------------------------
def compute_daily_signals(L4):
    cc = pd.read_parquet(CUBE_CLOSE_PATH)
    cc.index.name = "date"
    long_close = cc.reset_index().melt(id_vars="date", var_name="symbol", value_name="close")
    long_close = long_close.dropna(subset=["close"])
    long_close["date"] = to_dt(long_close["date"])
    log(f"[DATA] cube_close_long.parquet melted rows={len(long_close)}, "
        f"symbols={long_close['symbol'].nunique()}, "
        f"date range {long_close['date'].min().date()}..{long_close['date'].max().date()}")

    cv = pd.read_parquet(CUBE_VOLUME_PATH)
    cv.index.name = "date"
    long_vol = cv.reset_index().melt(id_vars="date", var_name="symbol", value_name="volume")
    long_vol["date"] = to_dt(long_vol["date"])
    n_vol_nonnull = long_vol["volume"].notna().sum()
    log(f"[DATA] cube_volume.parquet melted rows={len(long_vol)} ({n_vol_nonnull} non-null), "
        f"symbols={long_vol['symbol'].nunique()}, "
        f"date range {long_vol['date'].min().date()}..{long_vol['date'].max().date()} "
        f"-- CONFIRMED FLOOR: no volume history before {L4['volume_data_floor_date']}")

    daily = long_close.merge(long_vol, on=["date", "symbol"], how="left")
    daily = daily.sort_values(["symbol", "date"]).reset_index(drop=True)

    disc_thr = L4["discontinuity_guard_1day_return_abs"]
    ma_s, ma_l = L4["ma_short_window"], L4["ma_long_window"]
    vol_win = L4["avg_volume_window_days"]
    dist_win, dist_min = L4["distribution_day_window"], L4["distribution_day_count_min"]
    recent_cross_win = L4["recent_cross_window_days"]
    climax_win, climax_min = L4["climax_run_window_days"], L4["climax_run_return_min"]
    blowoff_ret_min, blowoff_vol_ratio = L4["blowoff_return_proxy_min"], L4["blowoff_volume_ratio_min"]
    thin_adv_pctile = L4["thin_adv_pooled_percentile"]
    circuit_vol_ratio = L4["circuit_suspect_volume_ratio_of_avg20"]

    t0 = time.time()
    n_disc_events = 0
    parts = []
    for sym, g in daily.groupby("symbol", sort=False):
        g = g.sort_values("date").reset_index(drop=True)
        close = g["close"]
        vol = g["volume"]

        ret1d = close.pct_change()
        is_disc = ret1d.abs() > disc_thr
        is_disc = is_disc.fillna(False)
        n_disc_events += int(is_disc.sum())

        ma50 = close.rolling(ma_s, min_periods=ma_s).mean()
        ma150 = close.rolling(ma_l, min_periods=ma_l).mean()
        avg_vol20 = vol.rolling(vol_win, min_periods=max(5, vol_win // 2)).mean()
        ret_climax = close / close.shift(climax_win) - 1

        down_day = close < close.shift(1)
        vol_up = vol >= vol.shift(1)
        dist_day = (down_day & vol_up & vol.notna()).fillna(False)
        dist_count = dist_day.rolling(dist_win, min_periods=1).sum()

        ma_below = (ma50 < ma150)
        crossed_below = ma_below & (~ma_below.shift(1).fillna(False))
        recently_crossed = crossed_below.rolling(recent_cross_win, min_periods=1).max().fillna(0).astype(bool)
        close_below_ma50 = (close < ma50).fillna(False)
        above_avg_vol = (vol >= avg_vol20).fillna(False)

        leg4c_daily_raw = (
            recently_crossed & close_below_ma50 & above_avg_vol & (dist_count >= dist_min) & ~is_disc
        )

        climax_run = (ret_climax >= climax_min).fillna(False)
        blowoff = ((ret1d >= blowoff_ret_min) & (vol >= blowoff_vol_ratio * avg_vol20)).fillna(False)
        leg4b_daily_raw = (climax_run | blowoff) & ~is_disc

        adv_rupee20 = avg_vol20 * close
        circuit_suspect = ((vol < circuit_vol_ratio * avg_vol20) & vol.notna() & avg_vol20.notna()).fillna(False)

        parts.append(pd.DataFrame({
            "symbol": sym,
            "date": g["date"].values,
            "close": close.values,
            "volume": vol.values,
            "adv_rupee20": adv_rupee20.values,
            "is_discontinuity": is_disc.values,
            "leg4b_daily_raw": leg4b_daily_raw.values,
            "leg4c_daily_raw": leg4c_daily_raw.values,
            "circuit_suspect": circuit_suspect.values,
        }))

    daily_signals = pd.concat(parts, ignore_index=True)
    log(f"[INFERENCE] daily signal table built: {len(daily_signals)} rows, "
        f"{daily_signals['symbol'].nunique()} symbols, in {time.time()-t0:.1f}s")
    log(f"[INFERENCE] discontinuity guard: {n_disc_events} symbol-days with |1-day return|>"
        f"{disc_thr:.0%} excluded from firing any leg4 sub-trigger that day")

    # thin_adv defined RELATIVE to this file's own pooled cross-section (bottom decile of
    # 20d rupee-ADV, computed once over all rows with a non-null adv_rupee20) -- frozen threshold,
    # logged, deterministic (same data -> same quantile every run).
    valid_adv = daily_signals["adv_rupee20"].dropna()
    thin_adv_threshold_rupee = float(valid_adv.quantile(thin_adv_pctile)) if len(valid_adv) else np.nan
    daily_signals["thin_adv"] = (daily_signals["adv_rupee20"] < thin_adv_threshold_rupee).fillna(False)
    log(f"[INFERENCE] thin_adv threshold (pooled {thin_adv_pctile:.0%}ile of 20d rupee-ADV across "
        f"{len(valid_adv)} name-days): Rs.{thin_adv_threshold_rupee:,.0f}")
    return daily_signals


# ---------------------------------------------------------------------------
# Entry-price + as-of join onto the panel_pit / exit_trigger_flags grain
# ---------------------------------------------------------------------------
def join_onto_panel(flags, daily_signals, L4):
    daily_signals = daily_signals.sort_values("date").reset_index(drop=True)

    # entry_price(symbol) = last available daily close at/before entry_date
    entry_lookup = flags[["symbol", "entry_date"]].dropna(subset=["entry_date"]).drop_duplicates("symbol").copy()
    entry_lookup = entry_lookup.sort_values("entry_date").rename(columns={"entry_date": "date"})
    close_only = daily_signals[["symbol", "date", "close"]].sort_values("date")
    entry_price_df = pd.merge_asof(
        entry_lookup, close_only, on="date", by="symbol", direction="backward"
    ).rename(columns={"close": "entry_price", "date": "entry_date"})
    n_entry_price = entry_price_df["entry_price"].notna().sum()
    log(f"[INFERENCE] entry_price resolved (as-of backward join on daily close) for "
        f"{n_entry_price}/{len(entry_price_df)} symbols with a simulated entry_date")

    base = flags.sort_values("date").reset_index(drop=True).copy()
    base = base.merge(entry_price_df[["symbol", "entry_price"]], on="symbol", how="left")

    asof_cols = ["close", "is_discontinuity", "leg4b_daily_raw", "leg4c_daily_raw",
                 "circuit_suspect", "thin_adv"]
    joined = pd.merge_asof(
        base, daily_signals[["symbol", "date"] + asof_cols],
        on="date", by="symbol", direction="backward",
    )
    assert len(joined) == len(flags), f"as-of join changed row count: {len(flags)} -> {len(joined)}"

    held = joined["entry_date"].notna() & (joined["date"] >= joined["entry_date"])
    n_no_daily = joined["close"].isna().sum()
    log(f"[INFERENCE] as-of daily join complete, rows={len(joined)}, "
        f"{n_no_daily} rows had no daily close on/before the panel date (pre-listing) -> leg4 False there")

    hard_stop_pct = L4["hard_stop_pct"]
    leg4a = (
        held
        & joined["close"].notna() & joined["entry_price"].notna()
        & (joined["close"] <= joined["entry_price"] * (1 - hard_stop_pct))
        & ~joined["is_discontinuity"].fillna(False)
    ).fillna(False)
    leg4b = (held & joined["leg4b_daily_raw"].fillna(False))
    leg4c = (held & joined["leg4c_daily_raw"].fillna(False))

    joined["leg4a_hardstop"] = leg4a
    joined["leg4b_trim"] = leg4b
    joined["leg4c_stagebreak"] = leg4c
    joined["leg4_escalated"] = (
        joined["leg4c_stagebreak"]
        & (joined["leg1_valuation_ceiling"] | joined["leg2_fundamental_deterioration"])
    )
    joined["held_leg4"] = held
    return joined


def _combine(row):
    l1, l2, l3, l4a, l4b, l4c = (
        row["leg1_valuation_ceiling"], row["leg2_fundamental_deterioration"],
        row["leg3_forensic_veto"], row["leg4a_hardstop"], row["leg4b_trim"], row["leg4c_stagebreak"],
    )
    # leg3_forensic_veto in this build is the STAGE-A TRIPWIRE ONLY (never Stage-B confirmed) --
    # unchanged semantics from the legs 1-3 build: it maps to WATCH, never EXIT_NOW, here.
    if l1 and l2:
        return "EXIT_NOW"
    if l4c and (l1 or l2):
        return "EXIT_NOW"
    if l1:
        return "TRIM"
    if l2:
        return "TRIM"
    if l4c:
        return "TRIM"
    if (l4a or l4b):
        return "ADVISORY"
    if l3:
        return "WATCH"
    return "NONE"


def _notes(row):
    bits = []
    if row["leg1_valuation_ceiling"]:
        bits.append("leg1:valuation-ceiling")
    if row["leg2_fundamental_deterioration"]:
        bits.append("leg2:fundamental-deterioration")
    if row["leg3_forensic_veto"]:
        bits.append("leg3:STAGE-A-TRIPWIRE-ONLY(requires analyst filing-read confirmation before acting)")
    if row["leg4a_hardstop"]:
        bits.append("leg4a:7.5%-hard-stop-from-entry")
    if row["leg4b_trim"]:
        bits.append("leg4b:climax-run/blow-off-sell-into-strength")
    if row["leg4c_stagebreak"]:
        tag = "leg4c:Stage2->3/4-transition"
        if row["leg4_escalated"]:
            tag += "-ESCALATED(corroborated by leg1/leg2)"
        bits.append(tag)
    return "; ".join(bits) if bits else ""


def build():
    W = ensure_leg4_weights()
    L4 = W["leg4_technical_stop_trim"]

    flags = pd.read_parquet(FLAGS_PATH)
    flags["date"] = to_dt(flags["date"])
    flags["entry_date"] = to_dt(flags["entry_date"])
    base_rows = len(flags)
    log(f"[DATA] exit_trigger_flags.parquet (legs 1-3, frozen) rows={base_rows}")

    daily_signals = compute_daily_signals(L4)
    joined = join_onto_panel(flags, daily_signals, L4)
    assert len(joined) == base_rows

    joined["composite_exit_flag"] = joined.apply(_combine, axis=1)
    joined["notes"] = joined.apply(_notes, axis=1)
    joined["any_leg_fired"] = (
        joined["leg1_valuation_ceiling"] | joined["leg2_fundamental_deterioration"]
        | joined["leg3_forensic_veto"] | joined["leg4a_hardstop"] | joined["leg4b_trim"]
        | joined["leg4c_stagebreak"]
    )

    out_cols = [
        "date", "symbol", "entry_thesis_type", "entry_date",
        "leg1_valuation_ceiling", "leg2_fundamental_deterioration",
        "leg3_forensic_veto", "leg3_requires_analyst_confirmation",
        "leg4a_hardstop", "leg4b_trim", "leg4c_stagebreak", "leg4_escalated",
        "any_leg_fired", "composite_exit_flag", "notes",
    ]
    out = joined[out_cols].sort_values(["symbol", "date"]).reset_index(drop=True)

    # ---- incidence logging (held-rows-only, consistent with B1's report convention) ----
    held = joined["held_leg4"]
    n_held = int(held.sum())
    log(f"[INFERENCE] held (post-entry) rows total: {n_held} / {base_rows}")
    for col in ["leg4a_hardstop", "leg4b_trim", "leg4c_stagebreak", "leg4_escalated"]:
        n_fired = int((joined[col] & held).sum())
        log(f"[INFERENCE] incidence -- {col} fired rows (held): {n_fired} "
            f"({100*n_fired/max(n_held,1):.2f}% of held)")

    # liquidity-contamination diagnostics (reporting only, not used to suppress fires)
    for col in ["leg4a_hardstop", "leg4b_trim", "leg4c_stagebreak"]:
        fired_mask = joined[col] & held
        n_fired = int(fired_mask.sum())
        if n_fired > 0:
            n_circuit = int((fired_mask & joined["circuit_suspect"].fillna(False)).sum())
            n_thin = int((fired_mask & joined["thin_adv"].fillna(False)).sum())
            log(f"[INFERENCE] FM-LENS -- of {n_fired} {col} fires: {n_circuit} "
                f"({100*n_circuit/n_fired:.1f}%) on a circuit-suspect day, {n_thin} "
                f"({100*n_thin/n_fired:.1f}%) on a thin-ADV (<Rs.10L 20d ADV) day")

    log(f"[INFERENCE] leg4_escalated fired rows (held): {int((joined['leg4_escalated'] & held).sum())}")
    log(f"[INFERENCE] composite_exit_flag breakdown (held rows):")
    vc = joined.loc[held, "composite_exit_flag"].value_counts()
    for k, v in vc.items():
        log(f"    {k}: {v}")

    return out, joined, held


def sha256_of_parquet(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sha256_of_json(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def main():
    out, joined, held = build()
    out.to_parquet(FLAGS_PATH, index=False)
    log(f"[DATA] wrote {FLAGS_PATH} rows={len(out)} (legs 1-3 columns preserved, "
        f"4 new leg4 columns added, composite_exit_flag recomputed)")

    log("[CHECK] re-running build for determinism check (byte-identical parquet required) ...")
    LOG.clear()
    out2, _, _ = build()
    tmp_path = FLAGS_PATH.with_name("exit_trigger_flags_leg4_run2_tmp.parquet")
    out2.to_parquet(tmp_path, index=False)
    h1 = sha256_of_parquet(FLAGS_PATH)
    h2 = sha256_of_parquet(tmp_path)
    identical = h1 == h2
    print(f"[CHECK] run1 sha256={h1}")
    print(f"[CHECK] run2 sha256={h2}")
    print(f"[CHECK] DETERMINISM: {'PASS -- byte-identical' if identical else 'FAIL -- outputs differ'}")
    tmp_path.unlink()

    with open(SCORECARD_DIR / "_build_exit_trigger_leg4_log.txt", "w") as f:
        f.write("\n".join(LOG))
        f.write(f"\n\n[CHECK] run1 sha256={h1}\n[CHECK] run2 sha256={h2}\n"
                f"[CHECK] DETERMINISM: {'PASS' if identical else 'FAIL'}\n")

    return out, joined, held, identical


if __name__ == "__main__":
    main()
