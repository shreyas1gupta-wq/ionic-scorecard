"""
qfra2_history_rebuild.py
=========================
Rebuilds the QFRA 2.0 "8-year recommendation history" tables so they are
followable across every half-year period. Fixes two defects the Principal
named in the rendering used by mr_x_framework/src/qfra2_deck_v4.py (the
hand-built `HIST` dict feeding the "8-year track record" slides):

DEFECT 1 -- SLOT CHURN.
    The deck's "Pick 1" / "Pick 2" columns are just that period's QFRA
    rank-1 / rank-2, not a persistent fund identity. When a held fund's
    rank flips (because the OTHER slot's occupant changed), the held fund
    visually jumps columns even though nothing happened to it.

    Concrete example found in the source data: JM Large Cap Fund-Reg(G) is
    continuously held in "Large Cap" from 2020-H2 through 2024-H2, but it
    is rank-2 ("Pick 2") through 2021-H2 and rank-1 ("Pick 1") from
    2022-H1 onward -- purely because Nippon India Large Cap (the OTHER
    pick) rolled off and ICICI Pru Bluechip took its place that period.
    qfra2_deck_v4.py's hardcoded HIST dict (~line 334) reproduces exactly
    this jump.

    FIX: assign each fund a STABLE SLOT (slot1 / slot2) that it keeps for
    as long as it is continuously held in that category. A replacement
    fund inherits the DEPARTING fund's slot; a continuing fund never
    moves slots, regardless of how the model's own rank ordering falls
    that period. See build_stable_slots().

DEFECT 2 -- MISSING PERIODS.
    qfra2_deck_v4.py's HIST dict is hand-curated to show only rows where
    something changed (its own in-slide caption: "each row = a change"),
    so whole held stretches vanish -- e.g. its "Small Cap" entry jumps
    2018-H1 -> 2021-H1 -> 2025-H1 and never shows the periods held
    unchanged in between.

    FIX: emit every half-year period present in the source, 2018-H1
    through the latest period in the data, carrying the held pair
    forward, with an explicit changed_flag / note so the eye can still
    find real changes. See build_stable_slots() + render_markdown().

SOURCE OF TRUTH (read-only -- this script only ever reads it):
    QFRA2_recommendation_history.csv, one row per (period, category,
    rank), rank in {1, 2}. Verified 2026-08-04 via validate_source():
    every one of the 8 categories has all 17 periods x 2 ranks present,
    no nulls, no rank-1==rank-2 dupes.

    [DATA] The source ALREADY carries every period explicitly -- there is
    NO gap to infer-and-carry-forward at the data level. The "missing
    periods" defect is 100% a rendering artifact in qfra2_deck_v4.py's
    hand-curated HIST dict, not a hole in the data. This script's "carry
    forward" is therefore a RESHAPE of fully-present rows into stable
    slots, not an INFERENCE filling a gap.

    If a future re-run of this script ever finds a genuine gap (a
    (period, category) group without exactly 2 ranks), validate_source()
    raises loudly rather than silently filling it with an assumed
    holding -- this script never fabricates a period that isn't in the
    source.

OUTPUTS (written under --out-dir; fully deterministic from the read-only
    source with no state carried between runs, so re-running is always
    safe -- it just overwrites these two files):
    QFRA2_history_rebuilt.csv
        one row per (category, period). Required schema (deliverable):
        category, period, slot1_fund, slot2_fund, changed_flag
        Additive convenience columns (same data, not new information):
        slot1_changed, slot2_changed, note, slot1_fund_short,
        slot2_fund_short
    QFRA2_history_rebuilt.md
        human-readable per-category tables, changed slot(s) bolded on
        changed rows, plus a summary table of period / hidden / swap
        counts per category.

CONSTRAINTS HONOURED:
    - Never fabricates a holding or a date -- every slot1_fund/slot2_fund
      value is copied verbatim from a real source row; the only transform
      is WHICH COLUMN (slot1 vs slot2) it is placed in, decided by the
      continuity rule above. The *_short columns are a deterministic,
      reversible suffix-strip of that exact same string (see
      make_short_name()), never a re-identification -- the canonical
      value is always slot1_fund/slot2_fund, not the short form.
    - [DATA] tags on anything read straight from the source; [INFERENCE]
      tags on anything derived (slot assignment, changed_flag, the
      naive-vs-stable swap counts). No [OPINION] in this script's output
      -- the slide-fit recommendation is a judgment call and lives in the
      accompanying report, not here.
    - No import of 04_RND_LAB/lib/guards.py: that module's schema helpers
      are scoped to the stock/options dual-schema landmine (HF 1-min vs
      bhavcopy daily). This CSV is a different domain (MF recommendation
      history, columns period/category/rank/fund/source) with no
      overlapping schema risk, so this script carries its own
      validate_source() guard instead of forcing an irrelevant import.

Python: C:\\Users\\Shreyas.1Gupta\\AppData\\Local\\Python\\bin\\python.exe
Usage:
    python qfra2_history_rebuild.py [--source PATH] [--out-dir PATH]
"""

import argparse
import re
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Read-only source. Never written to by this script.
DEFAULT_SOURCE = Path(
    r"C:\Users\Shreyas.1Gupta\Downloads\Mf_qfra2-20260529T103217Z-3-001"
    r"\Mf_qfra2\mr_x_framework\outputs\recommendations"
    r"\QFRA2_recommendation_history.csv"
)

# .../Shreyas_Ionic_AMC/09_PRODUCT/scripts/qfra2_history_rebuild.py
#   parents[0] = scripts, parents[1] = 09_PRODUCT, parents[2] = Shreyas_Ionic_AMC
# Derived relative to this file (not hardcoded to one worktree) so the
# script keeps working if the repo is checked out into a different
# worktree path.
_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = _REPO_ROOT / "03_RESEARCH_DESK" / "qfra2_pac_prep"

REQUIRED_COLS = {"period", "category", "rank", "fund", "source"}
PERIOD_RE = re.compile(r"^(\d{4})-H([12])$")


# ---------------------------------------------------------------------------
# Period ordering
# ---------------------------------------------------------------------------

def period_key(period: str):
    """Sortable (year, half) key for strings like '2018-H1'. Raises on any
    period string that doesn't match the expected H1/H2 half-year format --
    we do not guess at a malformed period."""
    m = PERIOD_RE.match(str(period))
    if not m:
        raise ValueError(f"Unrecognised period format: {period!r} (expected 'YYYY-H1' or 'YYYY-H2')")
    return (int(m.group(1)), int(m.group(2)))


# ---------------------------------------------------------------------------
# Guard: validate the source before touching it
# ---------------------------------------------------------------------------

def validate_source(df: pd.DataFrame) -> None:
    """Fails loudly (AssertionError, full detail, real traceback) on any
    shape the rest of this script is not prepared to handle honestly.
    Nothing here is caught/swallowed -- per firm protocol, failures are
    reported verbatim, not papered over."""
    missing = REQUIRED_COLS - set(df.columns)
    if missing:
        raise AssertionError(f"Source CSV missing required columns: {sorted(missing)}")

    null_counts = df[["period", "category", "rank", "fund"]].isnull().sum()
    if null_counts.any():
        raise AssertionError(f"Source CSV has nulls in key columns:\n{null_counts[null_counts > 0]}")

    bad_rank = df.loc[~df["rank"].isin([1, 2])]
    if len(bad_rank):
        raise AssertionError(f"Source CSV has rank values other than {{1,2}}:\n{bad_rank}")

    counts = df.groupby(["period", "category"]).size()
    bad_counts = counts[counts != 2]
    if len(bad_counts):
        # This WOULD be a genuine data gap (not a rendering artifact) --
        # refuse to silently carry-forward or fabricate a holding for it.
        raise AssertionError(
            "Source CSV has (period, category) groups without exactly 2 "
            "ranks -- this is a genuine data gap, not a rendering "
            "artifact. Refusing to invent a holding. Offending groups:\n"
            f"{bad_counts}"
        )

    piv = df.pivot_table(index=["period", "category"], columns="rank", values="fund", aggfunc="first")
    same = piv[1] == piv[2]
    if same.any():
        raise AssertionError(f"Source CSV has rank-1 fund == rank-2 fund in the same period/category:\n{piv[same]}")

    # Every period string must parse; raises via period_key() if not.
    for p in df["period"].unique():
        period_key(p)


# ---------------------------------------------------------------------------
# "Before" metric: naive rank-as-slot churn (what the deck effectively does)
# ---------------------------------------------------------------------------

def naive_swap_events(df: pd.DataFrame, period_order):
    """Count continuing-fund slot swaps under the NAIVE scheme where
    slot == that period's own rank (rank1 -> column1, rank2 -> column2,
    always). This reproduces the deck's defect quantitatively: a fund
    held in both period t and t+1 whose rank differs between the two is
    counted as one swap event. This is the [INFERENCE] "before" baseline
    the task asks to compare against."""
    events = []
    by_cat = {}
    for cat, g in df.groupby("category", sort=False):
        piv = g.pivot(index="period", columns="rank", values="fund").reindex(period_order)
        prev_pair, prev_p, count = None, None, 0
        for p in period_order:
            r1, r2 = piv.loc[p, 1], piv.loc[p, 2]
            if prev_pair is not None:
                prev1, prev2 = prev_pair
                cur_pair = {r1, r2}
                for fund in ({prev1, prev2} & cur_pair):
                    prev_rank = 1 if fund == prev1 else 2
                    cur_rank = 1 if fund == r1 else 2
                    if prev_rank != cur_rank:
                        events.append(dict(category=cat, fund=fund, from_period=prev_p, to_period=p,
                                            from_rank=prev_rank, to_rank=cur_rank))
                        count += 1
            prev_pair, prev_p = (r1, r2), p
        by_cat[cat] = count
    return events, by_cat


# ---------------------------------------------------------------------------
# The fix: stable slot assignment
# ---------------------------------------------------------------------------

def build_stable_slots(df: pd.DataFrame, period_order) -> pd.DataFrame:
    """Defect-1 + defect-2 fix in one pass: walk each category's periods
    in order, keep slot1/slot2 pinned to fund IDENTITY rather than that
    period's rank, and emit every period (not just changed ones).

    Rule per period, given the current pair of funds {r1, r2} and the
    previous slot occupants (old1 in slot1, old2 in slot2):
      - both old1 and old2 still present  -> HELD. Slots unchanged,
        regardless of which one is rank-1 vs rank-2 this period. This is
        the exact fix for defect 1.
      - only old1 present   -> slot1 stays old1; slot2 takes the other
        (replacement inherits the departing fund's slot: slot2).
      - only old2 present   -> slot2 stays old2; slot1 takes the other.
      - neither present (full turnover, both replaced at once) -> no
        continuity to anchor to; slot1/slot2 default to this period's
        own rank1/rank2 as a deterministic, documented tie-break
        ([INFERENCE]: an arbitrary but stable and disclosed choice, not a
        fabricated holding -- both funds ARE real source rows for this
        period, only the column choice is a tie-break).
      - first period seen for a category -> initialise slot1=rank1,
        slot2=rank2 (nothing to be continuous with yet).
    """
    rows = []
    for cat, g in df.groupby("category", sort=False):
        piv = g.pivot(index="period", columns="rank", values="fund").reindex(period_order)
        slot1 = slot2 = None
        for p in period_order:
            r1, r2 = piv.loc[p, 1], piv.loc[p, 2]
            cur_pair = {r1, r2}
            if slot1 is None:
                slot1, slot2 = r1, r2
                s1_ch, s2_ch, note = True, True, "start"
            else:
                old1, old2 = slot1, slot2
                old1_in, old2_in = old1 in cur_pair, old2 in cur_pair
                if old1_in and old2_in:
                    s1_ch, s2_ch, note = False, False, "held"
                elif old1_in:
                    slot2 = next(iter(cur_pair - {old1}))
                    s1_ch, s2_ch, note = False, True, "slot2 replaced"
                elif old2_in:
                    slot1 = next(iter(cur_pair - {old2}))
                    s1_ch, s2_ch, note = True, False, "slot1 replaced"
                else:
                    slot1, slot2 = r1, r2
                    s1_ch, s2_ch, note = True, True, "both replaced (full turnover)"
            rows.append(dict(
                category=cat, period=p, slot1_fund=slot1, slot2_fund=slot2,
                changed_flag=bool(s1_ch or s2_ch), slot1_changed=bool(s1_ch),
                slot2_changed=bool(s2_ch), note=note,
            ))
    return pd.DataFrame(rows)


def verify_zero_stable_swaps(stable_df: pd.DataFrame, period_order):
    """Independent re-derivation from the OUTPUT (not the construction
    state) that no continuing fund ever changes slot column. This is the
    "after" count the task asks for -- computed the same way as
    naive_swap_events() but reading slot1_fund/slot2_fund instead of raw
    rank, so it is a genuine check, not a restatement of the algorithm's
    own bookkeeping."""
    events = []
    by_cat = {}
    for cat, g in stable_df.groupby("category", sort=False):
        idx = g.set_index("period").reindex(period_order)
        prev_pair, prev_p, count = None, None, 0
        for p in period_order:
            s1, s2 = idx.loc[p, "slot1_fund"], idx.loc[p, "slot2_fund"]
            if prev_pair is not None:
                p1, p2 = prev_pair
                cur_pair = {s1, s2}
                for fund in ({p1, p2} & cur_pair):
                    prev_slot = 1 if fund == p1 else 2
                    cur_slot = 1 if fund == s1 else 2
                    if prev_slot != cur_slot:
                        events.append(dict(category=cat, fund=fund, from_period=prev_p, to_period=p))
                        count += 1
            prev_pair, prev_p = (s1, s2), p
        by_cat[cat] = count
    return events, by_cat


# ---------------------------------------------------------------------------
# Display-only short names (additive; canonical value stays the full string)
# ---------------------------------------------------------------------------

_SHORT_PATTERNS = [
    r"\s*-\s*Growth Option\s*-\s*Direct Plan\s*$",
    r"\s*-\s*Growth Option\s*$",
    r"\s*\(Direct\)\s*$",
    r"\s*-\s*Direct\s*$",
    r"-Reg\(G\)\s*$",
    r"\(G\)\s*$",
    r"\s*-\s*Growth\s*$",
]


def make_short_name(name: str) -> str:
    """Deterministic, reversible-in-spirit suffix strip for slide-width
    display (e.g. 'Nippon India Large Cap Fund(G)' -> 'Nippon India Large
    Cap'). Anchored at end-of-string throughout, so it never touches a
    distinguishing mid/trailing token such as 'Series II' vs 'Series VII'
    (Sundaram Value Fund Series II/VII both survive untouched). This is a
    DISPLAY transform only -- the CSV's slot1_fund/slot2_fund columns are
    always the untouched source string; *_short is an additive column."""
    s = str(name).strip()
    changed = True
    while changed:
        changed = False
        for pat in _SHORT_PATTERNS:
            new_s = re.sub(pat, "", s, flags=re.IGNORECASE).strip()
            if new_s != s:
                s = new_s
                changed = True
    s = re.sub(r"\s+Fund$", "", s, flags=re.IGNORECASE).strip()
    return s


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_markdown(stable_df, cat_order, period_order, naive_by_cat, stable_by_cat, source_path, out_path):
    lines = []
    lines.append("# QFRA 2.0 -- 8-Year Recommendation History (rebuilt)")
    lines.append("")
    lines.append(f"Generated by `09_PRODUCT/scripts/qfra2_history_rebuild.py`. Source (read-only): "
                 f"`{source_path}`")
    lines.append("")
    lines.append("Two fixes vs the prior `qfra2_deck_v4.py` HIST-dict rendering:")
    lines.append("")
    lines.append("1. **Stable slots** -- Slot 1 / Slot 2 track fund IDENTITY, not that period's QFRA "
                 "rank. A held fund never changes column; a replacement always lands in the "
                 "departing fund's column.")
    lines.append("2. **Every period shown** -- all periods present in the source "
                 f"({period_order[0]} .. {period_order[-1]}), held or changed, with an explicit "
                 "status marker.")
    lines.append("")
    lines.append("Legend: `.` = held (no change from the prior period) &nbsp;&nbsp; **bold** = the "
                 "fund occupying that slot changed this period &nbsp;&nbsp; START = first period on "
                 "record for that category (nothing prior to compare against).")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Periods | Changed (shown pre-fix) | Held (hidden pre-fix) | "
                 "Continuing-fund slot-swaps: BEFORE (naive rank-as-slot) | "
                 "AFTER (stable slots) |")
    lines.append("|---|---|---|---|---|---|")
    for cat in cat_order:
        g = stable_df[stable_df["category"] == cat]
        n_per = len(g)
        n_changed = int(g["changed_flag"].sum())
        n_held = n_per - n_changed
        lines.append(f"| {cat} | {n_per} | {n_changed} | {n_held} | {naive_by_cat.get(cat, 0)} | "
                     f"{stable_by_cat.get(cat, 0)} |")
    total_naive = sum(naive_by_cat.values())
    total_stable = sum(stable_by_cat.values())
    lines.append(f"| **TOTAL** | {len(period_order) * len(cat_order)} | "
                 f"{int(stable_df['changed_flag'].sum())} | "
                 f"{len(stable_df) - int(stable_df['changed_flag'].sum())} | "
                 f"**{total_naive}** | **{total_stable}** |")
    lines.append("")

    for cat in cat_order:
        g = stable_df[stable_df["category"] == cat].copy()
        g["_ord"] = g["period"].map({p: i for i, p in enumerate(period_order)})
        g = g.sort_values("_ord")
        lines.append(f"## {cat}")
        lines.append("")
        lines.append("| Period | Slot 1 | Slot 2 | Status |")
        lines.append("|---|---|---|---|")
        for _, row in g.iterrows():
            s1 = f"**{row['slot1_fund_short']}**" if row["slot1_changed"] else row["slot1_fund_short"]
            s2 = f"**{row['slot2_fund_short']}**" if row["slot2_changed"] else row["slot2_fund_short"]
            if row["note"] == "start":
                status = "START"
            elif row["changed_flag"]:
                status = "CHANGED"
            else:
                status = "."
            lines.append(f"| {row['period']} | {s1} | {s2} | {status} |")
        lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Rebuild the QFRA 2.0 8-year recommendation history tables "
                                              "(stable slots, no missing periods).")
    ap.add_argument("--source", default=str(DEFAULT_SOURCE), help="Path to QFRA2_recommendation_history.csv (read-only)")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory to write the rebuilt CSV+MD into")
    args = ap.parse_args()

    source_path = Path(args.source)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[qfra2_history_rebuild] reading (read-only) {source_path}")
    df = pd.read_csv(source_path)
    validate_source(df)

    period_order = sorted(df["period"].unique(), key=period_key)
    cat_order = list(df["category"].unique())  # preserve source's first-seen category order
    print(f"[qfra2_history_rebuild] {len(cat_order)} categories x {len(period_order)} periods "
          f"({period_order[0]} .. {period_order[-1]}), {len(df)} source rows -- "
          f"every (period,category) has exactly 2 ranks, no gaps to infer.")

    naive_events, naive_by_cat = naive_swap_events(df, period_order)
    stable_df = build_stable_slots(df, period_order)
    stable_events, stable_by_cat = verify_zero_stable_swaps(stable_df, period_order)

    if stable_events:
        # Should be impossible by construction; if this ever fires it means
        # build_stable_slots() has a bug -- fail loudly, do not ship silently.
        raise AssertionError(
            f"BUG: stable-slot construction still produced {len(stable_events)} continuing-fund "
            f"slot swaps -- must be zero by construction. Events: {stable_events}"
        )

    stable_df["slot1_fund_short"] = stable_df["slot1_fund"].map(make_short_name)
    stable_df["slot2_fund_short"] = stable_df["slot2_fund"].map(make_short_name)

    ord_map = {p: i for i, p in enumerate(period_order)}
    cat_ord_map = {c: i for i, c in enumerate(cat_order)}
    stable_df["_pord"] = stable_df["period"].map(ord_map)
    stable_df["_cord"] = stable_df["category"].map(cat_ord_map)
    stable_df = stable_df.sort_values(["_cord", "_pord"]).drop(columns=["_pord", "_cord"]).reset_index(drop=True)

    out_csv = out_dir / "QFRA2_history_rebuilt.csv"
    cols = ["category", "period", "slot1_fund", "slot2_fund", "changed_flag",
            "slot1_changed", "slot2_changed", "note", "slot1_fund_short", "slot2_fund_short"]
    stable_df[cols].to_csv(out_csv, index=False)
    print(f"[qfra2_history_rebuild] wrote {out_csv} ({len(stable_df)} rows)")

    out_md = out_dir / "QFRA2_history_rebuilt.md"
    render_markdown(stable_df, cat_order, period_order, naive_by_cat, stable_by_cat, source_path, out_md)
    print(f"[qfra2_history_rebuild] wrote {out_md}")

    maxlen = stable_df[["slot1_fund", "slot2_fund"]].apply(lambda c: c.str.len()).max().max()
    maxlen_short = stable_df[["slot1_fund_short", "slot2_fund_short"]].apply(lambda c: c.str.len()).max().max()

    print()
    header = f"{'category':<22} {'periods':>7} {'changed':>7} {'held(hidden)':>12} {'naive_swaps':>11} {'stable_swaps':>12}"
    print(header)
    total_changed = 0
    for cat in cat_order:
        g = stable_df[stable_df["category"] == cat]
        n_per = len(g)
        n_changed = int(g["changed_flag"].sum())
        n_held = n_per - n_changed
        total_changed += n_changed
        print(f"{cat:<22} {n_per:>7} {n_changed:>7} {n_held:>12} {naive_by_cat.get(cat, 0):>11} {stable_by_cat.get(cat, 0):>12}")
    print()
    print(f"TOTAL rows written: {len(stable_df)}  (previously shown pre-fix: {total_changed}, "
          f"previously hidden pre-fix: {len(stable_df) - total_changed})")
    print(f"TOTAL continuing-fund slot swaps -- BEFORE (naive rank-as-slot): {sum(naive_by_cat.values())}")
    print(f"TOTAL continuing-fund slot swaps -- AFTER  (stable slots):       {sum(stable_by_cat.values())}  (must be 0)")
    print(f"Longest fund name string: {maxlen} chars full / {maxlen_short} chars shortened")

    assert sum(stable_by_cat.values()) == 0, "stable slot swap count must be zero -- see assertion above"


if __name__ == "__main__":
    main()
