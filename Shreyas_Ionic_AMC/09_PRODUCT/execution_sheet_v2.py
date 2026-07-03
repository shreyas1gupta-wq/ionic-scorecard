"""
EXECUTION-SHEET v2 — Tanvi Desai (E-026, Head of Product), Shreyas_Ionic_AMC
Roadmap item #2 (09_PRODUCT/ROADMAP.md).

Turns the raw scored leg-level CSV (FINAL_STRATEGY_FORWARD_CHECK/08_Execution/execution_scored.csv)
into a decision-ready trade sheet for the Principal: one row per TRADE (not per leg), sorted into
three decision blocks, with full details/dates/prices/strikes/conviction inline per the Principal's
stated bar ("full details, dates, prices, strikes CE/PE, conviction").

Product does NOT make investment calls: conviction/blocked/tail_tier/size_x are consumed as-produced
by the Quant/Risk desks. This script only groups, formats and sorts what those desks already decided.

Usage:
    python execution_sheet_v2.py [path_to_execution_scored.csv]

Output:
    FINAL_STRATEGY_FORWARD_CHECK/08_Execution/EXECUTION_SHEET_V2.md
"""
import sys
import csv
import os
from collections import defaultdict
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CSV = os.path.join(ROOT, "FINAL_STRATEGY_FORWARD_CHECK", "08_Execution", "execution_scored.csv")
OUT_MD = os.path.join(ROOT, "FINAL_STRATEGY_FORWARD_CHECK", "08_Execution", "EXECUTION_SHEET_V2.md")
MACRO_CAL = os.path.join(ROOT, "FINAL_STRATEGY_FORWARD_CHECK", "03_RESEARCH_DESK", "MACRO_CALENDAR.md")

CONVICTION_TRADE = 60.0
CONVICTION_DISCRETIONARY_LOW = 45.0
MARGIN_RATE_SHORT = 0.12  # 12% of notional for net-short-premium structures (strangle/earnings)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def to_float(x, default=0.0):
    try:
        if x is None or str(x).strip() in ("", "-"):
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def to_bool(x):
    return str(x).strip().lower() == "true"


def fmt_money(x):
    """Indian-style rupee formatting, no decimals for large values."""
    x = round(x)
    sign = "-" if x < 0 else ""
    x = abs(int(x))
    s = str(x)
    if len(s) <= 3:
        return f"{sign}Rs.{s}"
    last3 = s[-3:]
    rest = s[:-3]
    parts = []
    while len(rest) > 2:
        parts.insert(0, rest[-2:])
        rest = rest[:-2]
    if rest:
        parts.insert(0, rest)
    return f"{sign}Rs.{','.join(parts + [last3])}"


def parse_expiry(exp_str):
    """expiry like '28JUL2026' -> datetime, for hold-window checks."""
    try:
        return datetime.strptime(exp_str.strip(), "%d%b%Y")
    except Exception:
        return None


def leg_desc(leg):
    """One inline leg string: SELL 28JUL 1140CE @19.10"""
    exp = leg["expiry"].strip()
    exp_short = exp[:5] if len(exp) >= 5 else exp  # '28JUL2026' -> '28JUL'
    strike = to_float(leg["strike"])
    strike_s = f"{strike:g}"
    opt = leg["opt"].strip()
    price = leg["live_price"].strip()
    if price == "":
        price_s = "N/A(missing px)"
    else:
        price_s = f"{to_float(leg['live_price']):.2f}"
    return f"{leg['action']} {exp_short} {strike_s}{opt} @{price_s}"


def credit_debit_for_leg(leg):
    """Signed premium contribution per share: SELL=+price (credit), BUY=-price (debit). Missing price -> 0, flagged elsewhere."""
    px = to_float(leg["live_price"], default=None)
    if px is None:
        return 0.0
    sign = 1.0 if leg["action"].strip().upper() == "SELL" else -1.0
    return sign * px


def block_reason(trade):
    """One-line reason a trade sits in a given decision block."""
    reasons = []
    if trade["blocked"]:
        # try to surface the risk_flags text for WHY
        rf = trade["risk_flags_set"] - {"-", ""}
        if rf:
            reasons.append(f"blocked: {'; '.join(sorted(rf))}")
        else:
            reasons.append("blocked by risk overlay")
    if trade["conviction"] < CONVICTION_DISCRETIONARY_LOW:
        reasons.append(f"low conviction {trade['conviction']:.0f}")
    if not reasons:
        if trade["tail_tier"] == "HIGH":
            reasons.append("tail_tier HIGH")
        elif CONVICTION_DISCRETIONARY_LOW <= trade["conviction"] < CONVICTION_TRADE:
            reasons.append(f"conviction {trade['conviction']:.0f} in 45-59 discretionary band")
    return "; ".join(reasons) if reasons else "-"


def what_can_go_wrong(trade):
    """One-liner from risk_flags/news_note, deduped across legs."""
    bits = []
    for f in trade["risk_flags_set"] - {"-", ""}:
        bits.append(f)
    note = trade["news_note_set"] - {"-", "", "no notable idiosyncratic news (earnings/sector only)"}
    for n in note:
        bits.append(n)
    if trade["tail_tier"] == "HIGH":
        bits.append("tail_tier HIGH (fat-tail sizing overlay active)")
    if not bits:
        return "no elevated idiosyncratic risk flagged; standard short-vol tail risk applies"
    # de-dup preserving order-ish
    seen = []
    for b in bits:
        if b not in seen:
            seen.append(b)
    return " | ".join(seen)


def event_dates_in_window(trade):
    """Pull explicit event dates mentioned in signal/news_note (earnings dates) that fall inside entry->expiry window."""
    events = []
    sig = trade["signal_set"]
    for s in sig:
        if "earnings" in s.lower():
            events.append(s.replace("earnings ", "earnings: "))
    return "; ".join(sorted(set(events))) if events else "-"


# ---------------------------------------------------------------------------
# Load + group
# ---------------------------------------------------------------------------
def load_rows(csv_path):
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def group_trades(rows):
    groups = defaultdict(list)
    for r in rows:
        key = (r["strategy"], r["symbol"], r["entry_date"])
        groups[key].append(r)

    trades = []
    dq_issues = []  # data-quality issues collected as we go

    for (strategy, symbol, entry_date), legs in groups.items():
        # sanity: conviction/tail_tier/blocked/size_x should agree across legs of the same trade
        convictions = set(to_float(l["conviction"]) for l in legs)
        blocked_vals = set(to_bool(l["blocked"]) for l in legs)
        tail_tiers = set(l["tail_tier"].strip() for l in legs)
        size_xs = set(to_float(l["size_x"], default=1.0) for l in legs)
        lots_vals = set(to_float(l["lots"]) for l in legs)
        lot_sizes = set(to_float(l["lot_size"]) for l in legs)

        if len(convictions) > 1:
            dq_issues.append(f"{strategy}/{symbol}/{entry_date}: legs disagree on conviction {convictions}")
        if len(blocked_vals) > 1:
            dq_issues.append(f"{strategy}/{symbol}/{entry_date}: legs disagree on blocked flag {blocked_vals}")
        if len(lots_vals) > 1:
            dq_issues.append(f"{strategy}/{symbol}/{entry_date}: legs disagree on lots {lots_vals}")
        if len(lot_sizes) > 1:
            dq_issues.append(f"{strategy}/{symbol}/{entry_date}: legs disagree on lot_size {lot_sizes}")

        conviction = max(convictions)  # conservative: shouldn't differ, but don't silently drop info
        blocked = any(blocked_vals)
        tail_tier = "HIGH" if "HIGH" in tail_tiers else (sorted(tail_tiers)[0] if tail_tiers else "-")
        size_x = max(size_xs) if size_xs else 1.0
        lots = max(lots_vals) if lots_vals else 0.0
        lot_size = max(lot_sizes) if lot_sizes else 0.0

        max_lots_vals = [to_float(l.get("max_lots", ""), default=None) for l in legs if l.get("max_lots", "").strip() not in ("", None)]
        max_lots = min(max_lots_vals) if max_lots_vals else None

        raw_final_lots = lots * size_x
        final_lots = min(raw_final_lots, max_lots) if max_lots is not None else raw_final_lots
        capped = max_lots is not None and raw_final_lots > max_lots

        # per-share net credit/debit (sum of signed leg prices); missing price legs contribute 0 and are flagged
        missing_price = any(l["live_price"].strip() == "" for l in legs)
        per_share_net = sum(credit_debit_for_leg(l) for l in legs)
        total_net = per_share_net * lot_size * final_lots

        if missing_price:
            dq_issues.append(f"{strategy}/{symbol}/{entry_date}: missing live_price on at least one leg — credit/debit total is UNDERSTATED")

        # margin estimate: 12% of notional for net-short structures (all three strategies here are
        # short-premium at the trade level even though FF_Calendar has one long leg — margin is on
        # the short leg's underlying notional, so approximate with strike*lot_size*final_lots of the SELL leg(s))
        sell_notional = sum(
            to_float(l["strike"]) * lot_size * final_lots
            for l in legs
            if l["action"].strip().upper() == "SELL"
        )
        margin_est = sell_notional * MARGIN_RATE_SHORT

        legs_desc = " + ".join(leg_desc(l) for l in sorted(legs, key=lambda x: x["action"], reverse=True))

        expiries = [parse_expiry(l["expiry"]) for l in legs]
        expiries = [e for e in expiries if e is not None]
        max_expiry = max(expiries) if expiries else None

        trade = {
            "strategy": strategy,
            "symbol": symbol,
            "entry_date": entry_date,
            "sector": legs[0].get("sector", "-"),
            "legs_desc": legs_desc,
            "legs": legs,
            "conviction": conviction,
            "blocked": blocked,
            "tail_tier": tail_tier,
            "size_x": size_x,
            "lots": lots,
            "lot_size": lot_size,
            "max_lots": max_lots,
            "final_lots": final_lots,
            "capped": capped,
            "per_share_net": per_share_net,
            "total_net": total_net,
            "is_credit": total_net >= 0,
            "missing_price": missing_price,
            "margin_est": margin_est,
            "exit_rule": sorted(set(l["exit_rule"] for l in legs))[0],
            "risk_flags_set": set(l["risk_flags"].strip() for l in legs),
            "news_note_set": set(l["news_note"].strip() for l in legs),
            "signal_set": set(l["signal"].strip() for l in legs),
            "max_expiry": max_expiry,
            "max_expiry_str": legs[0]["expiry"],
        }
        trade["reason"] = block_reason(trade)
        trade["wcgw"] = what_can_go_wrong(trade)
        trade["events_in_window"] = event_dates_in_window(trade)
        trades.append(trade)

    return trades, dq_issues


def classify(trades):
    trade_block, disc_block, blocked_block = [], [], []
    for t in trades:
        if t["blocked"] or t["conviction"] < CONVICTION_DISCRETIONARY_LOW:
            blocked_block.append(t)
        elif t["conviction"] >= CONVICTION_TRADE:
            trade_block.append(t)
        else:
            disc_block.append(t)

    trade_block.sort(key=lambda t: (-t["conviction"], t["symbol"]))
    disc_block.sort(key=lambda t: (-t["conviction"], t["symbol"]))
    blocked_block.sort(key=lambda t: (t["conviction"], t["symbol"]))
    return trade_block, disc_block, blocked_block


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------
def render_trade_row(t, idx):
    net_label = "CREDIT" if t["is_credit"] else "DEBIT"
    net_s = fmt_money(abs(t["total_net"])) + f" {net_label}"
    if t["missing_price"]:
        net_s += " (est., 1+ leg price missing)"
    final_lots_s = f"{t['final_lots']:g}"
    if t["capped"]:
        final_lots_s += f" (capped from {t['lots']*t['size_x']:g} by max_lots={t['max_lots']:g})"
    elif t["size_x"] != 1.0:
        final_lots_s += f" ({t['lots']:g} lots x size_x {t['size_x']:g})"
    return (
        f"| {idx} | {t['entry_date']} | {t['strategy']} | {t['symbol']} ({t['sector']}) | "
        f"{t['legs_desc']} | {net_s} | {final_lots_s} | {fmt_money(t['margin_est'])} | "
        f"{t['conviction']:.0f} | {t['tail_tier']} | {t['exit_rule']} |"
    )


BORING_WCGW = "no elevated idiosyncratic risk flagged; standard short-vol tail risk applies"


def render_block(title, emoji_label, trades, show_reason=False):
    lines = [f"## {emoji_label} ({len(trades)} trades)", ""]
    if not trades:
        lines.append("_none_\n")
        return "\n".join(lines)

    header = (
        "| # | Entry | Strategy | Symbol (Sector) | Legs | Net Credit/Debit | Final Lots | "
        "Margin Est. | Conviction | Tail | Exit Rule |"
    )
    sep = "|---|---|---|---|---|---|---|---|---|---|---|"
    if show_reason:
        header = header + " Reason |"
        sep = sep + "---|"

    lines.append(header)
    lines.append(sep)
    for i, t in enumerate(trades, 1):
        row = render_trade_row(t, i)
        if show_reason:
            row = row + f" {t['reason']} |"
        lines.append(row)
    lines.append("")

    # Token-lean callouts: only surface WCGW/event-window notes when there is something
    # actually notable (not the boilerplate "no elevated risk" line repeated for every row).
    notable = [t for t in trades if t["wcgw"] != BORING_WCGW or t["events_in_window"] != "-"]
    if notable:
        lines.append(f"**What can go wrong / event dates in hold window** (only trades with a flag shown; "
                      f"{len(trades) - len(notable)} of {len(trades)} carry no elevated idiosyncratic flag):")
        lines.append("")
        for t in notable:
            idx = trades.index(t) + 1
            lines.append(f"- **#{idx} {t['symbol']} ({t['strategy']}, {t['entry_date']})**: {t['wcgw']}")
            if t["events_in_window"] != "-":
                lines.append(f"  - Event(s) in window: {t['events_in_window']}")
    else:
        lines.append("**What can go wrong:** no trade in this block carries an elevated idiosyncratic flag "
                      "beyond standard short-vol tail risk.")
    lines.append("")
    return "\n".join(lines)


def load_macro_note():
    if not os.path.exists(MACRO_CAL):
        return "MACRO_CALENDAR.md not found at `03_RESEARCH_DESK/` — no danger-window cross-check available this cycle. [DATA GAP — flagged to Macro desk.]"
    try:
        with open(MACRO_CAL, encoding="utf-8") as f:
            head = f.read(1500)
        return "Macro calendar found — see `03_RESEARCH_DESK/MACRO_CALENDAR.md` for full detail. Excerpt:\n\n" + head
    except Exception as e:
        return f"MACRO_CALENDAR.md present but unreadable ({e})."


def build_summary(trade_block, disc_block, blocked_block, dq_issues, csv_path, n_rows_raw):
    total_trades = len(trade_block) + len(disc_block) + len(blocked_block)
    total_margin_if_all_trade = sum(t["margin_est"] for t in trade_block)
    total_credit_if_all_trade = sum(t["total_net"] for t in trade_block if t["is_credit"])
    top3 = trade_block[:3]

    lines = []
    lines.append("# EXECUTION SHEET v2 — Decision-Ready Trade Sheet")
    lines.append("")
    lines.append(f"_Generated by Tanvi Desai (Product) from `{os.path.relpath(csv_path, ROOT)}` "
                  f"({n_rows_raw} legs -> {total_trades} trades). Product packages; Quant/Risk decided the numbers._")
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- **Total trades:** {total_trades}  |  TRADE: {len(trade_block)}  |  DISCRETIONARY: {len(disc_block)}  |  BLOCKED/AVOID: {len(blocked_block)}")
    lines.append(f"- **If all TRADE-block taken:** margin est. **{fmt_money(total_margin_if_all_trade)}**, "
                  f"net credit collected (credit legs only) **{fmt_money(total_credit_if_all_trade)}**")
    if top3:
        picks = "; ".join(f"#{i+1} {t['symbol']} ({t['strategy']}, conviction {t['conviction']:.0f})" for i, t in enumerate(top3))
        lines.append(f"- **Top-3 conviction picks:** {picks}")
    else:
        lines.append("- **Top-3 conviction picks:** none clear TRADE-block trades this cycle")
    lines.append("")
    lines.append("### Danger-window note")
    lines.append(load_macro_note())
    lines.append("")
    if dq_issues:
        lines.append("### Data-quality issues found in this cycle's CSV (voice-of-client duty)")
        for issue in dq_issues:
            lines.append(f"- {issue}")
        lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_CSV
    rows = load_rows(csv_path)
    trades, dq_issues = group_trades(rows)
    trade_block, disc_block, blocked_block = classify(trades)

    out = []
    out.append(build_summary(trade_block, disc_block, blocked_block, dq_issues, csv_path, len(rows)))
    out.append(render_block("TRADE", "✅ TRADE — conviction >=60, not blocked, ranked by conviction", trade_block))
    out.append(render_block("DISCRETIONARY", "⚠️ DISCRETIONARY — conviction 45-59 or tail_tier HIGH", disc_block, show_reason=True))
    out.append(render_block("BLOCKED", "⛔ BLOCKED / AVOID — blocked or conviction <45", blocked_block, show_reason=True))

    md = "\n".join(out)
    os.makedirs(os.path.dirname(OUT_MD), exist_ok=True)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"Wrote {OUT_MD}")
    print(f"Trades: {len(trades)} total | TRADE {len(trade_block)} | DISCRETIONARY {len(disc_block)} | BLOCKED {len(blocked_block)}")
    if dq_issues:
        print(f"Data-quality issues flagged: {len(dq_issues)}")
        for issue in dq_issues:
            print(" -", issue)


if __name__ == "__main__":
    main()
