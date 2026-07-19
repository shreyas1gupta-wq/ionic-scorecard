"""
D1 special-situations cheap-test: buyback-consideration board-meeting intimations.
Event = first public NSE disclosure that a board meeting will be held "to consider
a proposal for buyback of equity shares" (bm_purpose/bm_desc contains 'buyback').

PIT discipline:
  - t0 anchor = bm_timestamp (the actual NSE disclosure system timestamp), NEVER
    bm_date (the future scheduled board-meeting date -- using bm_date would be a
    lookahead bug, since bm_date is announced in ADVANCE of itself and the actual
    board decision/price is not yet public at bm_timestamp).
  - Entry day rule: if disclosure time <= 15:30 IST, event day = same trading day
    (a same-day reaction is theoretically capturable intraday, though not by our
    EOD data -- flagged as an assumption); if disclosure time > 15:30 IST, event
    day = next trading day (over the counter close, cannot react same day).
  - Forward windows measured close-to-close from event day 0.
  - Placebo: for each real event, draw random (non-event) trading days from the
    SAME symbol's own history (excludes +/-15 trading days around ANY real
    buyback event for that symbol) -- matches symbol-specific vol/beta, same
    methodology class as the firm's other same-symbol placebo work.
  - Lag-robustness check: shift entry by +1 extra trading day and re-measure --
    if the effect survives at similar magnitude/sign, it is multi-day drift, not
    a single-day lookahead/jump artifact.

Deterministic: fixed RNG seed, no per-run refit.
"""
import json
import datetime
import numpy as np
import pandas as pd

RNG_SEED = 20260718
N_PLACEBO_PER_EVENT = 10
WINDOWS = [1, 5, 10, 20]
EXCLUSION_HALFWIDTH = 15  # trading days around a real event, excluded from placebo pool

ROOT = r"C:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500"
BM_JSON = ROOT + r"\datasets\nse_earnings_dates\board_meetings_all.json"
PRICE_PARQUET = ROOT + r"\datasets\derived\pit_union_panel_v1\close_panel_price_v11.parquet"
OUT_DIR = ROOT + r"\Shreyas_Ionic_AMC\04_RND_LAB\results\D1_SPECIAL_SITS_CHEAPTEST_20260718"


def parse_dt(s, fmt):
    try:
        return datetime.datetime.strptime(s, fmt)
    except Exception:
        return None


def load_buyback_events():
    with open(BM_JSON, encoding="utf-8") as f:
        d = json.load(f)
    rows = []
    for r in d:
        purpose = (r.get("bm_purpose") or "")
        desc = (r.get("bm_desc") or "")
        text = (purpose + " " + desc).lower()
        if "buyback" in text or "buy back" in text:
            ts = parse_dt(r.get("bm_timestamp"), "%d-%b-%Y %H:%M:%S")
            bmd = parse_dt(r.get("bm_date"), "%d-%b-%Y")
            rows.append({
                "symbol": r.get("bm_symbol"),
                "bm_date": bmd.date() if bmd else None,
                "bm_timestamp": ts,
            })
    df = pd.DataFrame(rows)
    df = df.dropna(subset=["bm_timestamp", "bm_date"])
    # dedupe: one event per (symbol, bm_date) -- keep EARLIEST disclosure timestamp
    df = df.sort_values("bm_timestamp").drop_duplicates(subset=["symbol", "bm_date"], keep="first")
    return df.reset_index(drop=True)


def main():
    events = load_buyback_events()
    print(f"[DATA] Deduped buyback board-meeting-intimation events: {len(events)}, "
          f"symbols: {events['symbol'].nunique()}, "
          f"date range: {events['bm_timestamp'].min()} -> {events['bm_timestamp'].max()}")

    price = pd.read_parquet(PRICE_PARQUET)
    price = price.sort_values(["symbol", "date"]).reset_index(drop=True)
    price_syms = set(price["symbol"].unique())

    matched = events[events["symbol"].isin(price_syms)].copy()
    print(f"[DATA] Events with symbol present in price panel: {len(matched)} / {len(events)}")

    # per-symbol date index arrays for fast searchsorted
    sym_groups = {sym: g.reset_index(drop=True) for sym, g in price.groupby("symbol")}

    def entry_pos(sym, disclosure_ts):
        g = sym_groups.get(sym)
        if g is None or len(g) == 0:
            return None, None
        dates = g["date"].values.astype("datetime64[D]")
        disc_day = np.datetime64(disclosure_ts.date(), "D")
        # trading day index of first date >= disc_day
        pos = int(np.searchsorted(dates, disc_day, side="left"))
        if pos >= len(dates):
            return None, g
        # same-day vs next-day cutoff at 15:30 IST
        if dates[pos] == disc_day and disclosure_ts.time() > datetime.time(15, 30):
            pos += 1
        if pos >= len(dates):
            return None, g
        return pos, g

    records = []
    excluded_windows = {}  # symbol -> list of (start_pos, end_pos) to exclude from placebo pool

    for _, row in matched.iterrows():
        sym = row["symbol"]
        pos, g = entry_pos(sym, row["bm_timestamp"])
        if pos is None:
            continue
        closes = g["close"].values
        n = len(closes)
        if pos == 0 or pos + max(WINDOWS) >= n:
            continue  # need pre-event close + full forward window
        rec = {"symbol": sym, "bm_date": row["bm_date"], "entry_pos": pos,
               "entry_date": g["date"].iloc[pos]}
        c0 = closes[pos]
        for w in WINDOWS:
            rec[f"fwd_{w}d"] = closes[pos + w] / c0 - 1.0
        # anticipation window: return INTO the event (t-5 -> t0), context only
        if pos - 5 >= 0:
            rec["pre_5d"] = closes[pos] / closes[pos - 5] - 1.0
        # lag-robustness: shift entry by +1 extra trading day
        pos1 = pos + 1
        if pos1 + max(WINDOWS) < n:
            c1 = closes[pos1]
            for w in WINDOWS:
                rec[f"lag1_fwd_{w}d"] = closes[pos1 + w] / c1 - 1.0
        records.append(rec)
        excluded_windows.setdefault(sym, []).append(
            (max(0, pos - EXCLUSION_HALFWIDTH), pos + EXCLUSION_HALFWIDTH))

    event_df = pd.DataFrame(records)
    print(f"[DATA] Events with usable price window (pre-event close + forward window all present): {len(event_df)}")
    print(f"[DATA] Distinct symbols in final event sample: {event_df['symbol'].nunique()}")

    # ---- Placebo: same-symbol random non-event dates ----
    rng = np.random.default_rng(RNG_SEED)
    placebo_records = []
    for _, row in event_df.iterrows():
        sym = row["symbol"]
        g = sym_groups[sym]
        n = len(g)
        closes = g["close"].values
        excl = excluded_windows.get(sym, [])
        max_w = max(WINDOWS)
        valid_positions = [p for p in range(5, n - max_w) if not any(a <= p <= b for a, b in excl)]
        if not valid_positions:
            continue
        draws = rng.choice(valid_positions, size=min(N_PLACEBO_PER_EVENT, len(valid_positions)), replace=False)
        for p in draws:
            c0 = closes[p]
            prec = {"symbol": sym}
            for w in WINDOWS:
                prec[f"fwd_{w}d"] = closes[p + w] / c0 - 1.0
            placebo_records.append(prec)

    placebo_df = pd.DataFrame(placebo_records)
    print(f"[DATA] Placebo draws generated: {len(placebo_df)}")

    # ---- Summary stats ----
    from scipy import stats as sstats

    lines = []
    lines.append("# D1 Special-Situations cheap-test: buyback board-meeting intimations")
    lines.append("")
    lines.append(f"Real events (usable): {len(event_df)} | distinct symbols: {event_df['symbol'].nunique()} | "
                 f"placebo draws: {len(placebo_df)}")
    lines.append("")
    lines.append("| window | real mean | real median | real t-stat (vs 0) | placebo mean | "
                 "diff (real-placebo) | Welch t-stat (real vs placebo) | p-value |")
    lines.append("|---|---|---|---|---|---|---|---|")

    summary_rows = []
    for w in WINDOWS:
        col = f"fwd_{w}d"
        real = event_df[col].dropna()
        plac = placebo_df[col].dropna()
        t0, p0 = sstats.ttest_1samp(real, 0.0)
        tdiff, pdiff = sstats.ttest_ind(real, plac, equal_var=False)
        lines.append(f"| +{w}d | {real.mean():.4f} | {real.median():.4f} | {t0:.2f} | "
                     f"{plac.mean():.4f} | {real.mean()-plac.mean():.4f} | {tdiff:.2f} | {pdiff:.4f} |")
        summary_rows.append({"window": w, "real_mean": real.mean(), "real_n": len(real),
                             "placebo_mean": plac.mean(), "placebo_n": len(plac),
                             "diff": real.mean() - plac.mean(), "t_vs_placebo": tdiff, "p_vs_placebo": pdiff})

    lines.append("")
    lines.append("## Anticipation window (t-5 -> t0, context only, NOT tradeable pre-event)")
    pre = event_df["pre_5d"].dropna()
    tpre, ppre = sstats.ttest_1samp(pre, 0.0)
    lines.append(f"pre_5d mean={pre.mean():.4f}, median={pre.median():.4f}, n={len(pre)}, t={tpre:.2f}, p={ppre:.4f}")
    lines.append("")

    lines.append("## Lag-robustness check (entry shifted +1 extra trading day)")
    lines.append("| window | lag1 real mean | lag1 t-stat (vs 0) | lag1 vs placebo diff | lag1 t (vs placebo) | lag1 p |")
    lines.append("|---|---|---|---|---|---|")
    for w in WINDOWS:
        col = f"lag1_fwd_{w}d"
        if col not in event_df.columns:
            continue
        real1 = event_df[col].dropna()
        plac = placebo_df[f"fwd_{w}d"].dropna()
        t1, p1 = sstats.ttest_1samp(real1, 0.0)
        tdiff1, pdiff1 = sstats.ttest_ind(real1, plac, equal_var=False)
        lines.append(f"| +{w}d | {real1.mean():.4f} | {t1:.2f} | {real1.mean()-plac.mean():.4f} | {tdiff1:.2f} | {pdiff1:.4f} |")

    report = "\n".join(lines)
    print("\n" + report)

    with open(OUT_DIR + r"\RESULTS.md", "w", encoding="utf-8") as f:
        f.write(report + "\n")

    event_df.to_csv(OUT_DIR + r"\events_with_returns.csv", index=False)
    placebo_df.to_csv(OUT_DIR + r"\placebo_draws.csv", index=False)
    pd.DataFrame(summary_rows).to_csv(OUT_DIR + r"\summary_by_window.csv", index=False)
    print(f"\nWritten to {OUT_DIR}")


if __name__ == "__main__":
    main()
