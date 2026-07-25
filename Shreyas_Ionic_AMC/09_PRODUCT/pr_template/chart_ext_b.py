# -*- coding: utf-8 -*-
"""chart_ext_b.py, annexure set B chart extensions for the v9 template.
Importing `charts` first guarantees the scripts path + CHART_OUTDIR are set before chart_lib loads.
Reuses chart_lib's figure scaffold, palette and save path. Every fn returns the PNG path.
"""
import charts as _CH  # noqa: F401  (side effect: sys.path + CHART_OUTDIR)
import numpy as np
import matplotlib as _mpl
_mpl.rcParams["axes.unicode_minus"] = False  # ASCII hyphen; Bahnschrift lacks U+2212
from chart_lib import (_fig, _save, INK, SLATE, HAIR, NAVY, NT1, NT2, NT3, GOLD,
                       SELL, SELLBG, HOLD, HOLDBG, PANEL)

AMBER = "#92400E"


# ------------------------------------------------ score vs final call (banded scatter, F13)
def score_vs_call(scores, bands, sizes, override, labels, name,
                  band_names=("Sell", "Under review", "Hold"), threshold=40, figsize=(8.8, 5.2)):
    """x = quant score 0-100; bands: 0=Sell, 1=Under review, 2=Hold (final analyst call).
    override: list of None/'up'/'down'; overridden points get a gold ring + symbol label."""
    fig, ax = _fig(figsize)
    ax.axhspan(-0.5, 0.5, color=SELLBG, alpha=0.55, zorder=0)
    ax.axhspan(0.5, 1.5, color=PANEL, alpha=0.9, zorder=0)
    ax.axhspan(1.5, 2.5, color=HOLDBG, alpha=0.55, zorder=0)
    ax.axvline(threshold, color=GOLD, lw=1.6, ls=(0, (4, 3)), zorder=2)
    ax.text(threshold - 1.5, 2.42, f"quant Sell line {threshold}", ha="right", va="top",
            fontsize=8.5, color="#8A6E1B", style="italic")
    bandcol = {0: SELL, 1: GOLD, 2: HOLD}
    # deterministic jitter inside each band so points do not stack
    counts = {}
    offs = [-0.30, -0.15, 0.0, 0.15, 0.30, -0.23, 0.08, 0.23, -0.08]
    n_ov = 0
    for x, b, sz, ov, lab in zip(scores, bands, sizes, override, labels):
        k = counts.get(b, 0); counts[b] = k + 1
        y = b + offs[k % len(offs)]
        s = max(70, sz / 1e5 * 2.6)
        ax.scatter([x], [y], s=s, color=bandcol[b], alpha=0.85,
                   edgecolors="white", linewidths=1.2, zorder=3)
        if ov:
            ax.scatter([x], [y], s=s * 2.6, facecolors="none", edgecolors=GOLD,
                       linewidths=2.0, zorder=4)
            # alternate labels above/below the ring so near neighbours stay legible
            above = (n_ov % 2 == 1); n_ov += 1
            ax.text(x, y + (0.17 if above else -0.17), lab, ha="center",
                    va=("bottom" if above else "top"), fontsize=8, color=INK,
                    fontweight="bold", zorder=5)
    ax.set_yticks([0, 1, 2]); ax.set_yticklabels(band_names, fontsize=10.5, color=INK)
    ax.set_xlabel("Ionic Score  (quant, 0-100)", fontsize=10.2, color=SLATE)
    ax.set_xlim(0, 100); ax.set_ylim(-0.5, 2.5)
    ax.tick_params(labelsize=9)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_visible(True); ax.spines[sp].set_color(HAIR)
    return _save(fig, name)


# ------------------------------------------------ valuation percentile gauge (10y band)
def percentile_gauge(p10, p25, p50, p75, p90, today, name, unit="x",
                     today_note="", figsize=(8.4, 5.0)):
    """Horizontal percentile strips of a valuation range with today's level marked."""
    fig, ax = _fig(figsize)
    ax.axhspan(p10, p25, color=NT3, alpha=0.30, zorder=1)
    ax.axhspan(p25, p75, color=NT2, alpha=0.38, zorder=1)
    ax.axhspan(p75, p90, color=NT3, alpha=0.30, zorder=1)
    for v, lab in ((p10, "p10"), (p25, "p25"), (p75, "p75"), (p90, "p90")):
        ax.axhline(v, color=HAIR, lw=1, zorder=2)
        ax.text(1.005, v, f"{lab} · {v:.0f}{unit}", ha="left", va="center",
                fontsize=9, color=SLATE, transform=ax.get_yaxis_transform())
    ax.axhline(p50, color=NAVY, lw=1.6, ls=(0, (5, 3)), zorder=3)
    ax.text(1.005, p50, f"median · {p50:.0f}{unit}", ha="left", va="center",
            fontsize=9.5, color=NAVY, fontweight="bold", transform=ax.get_yaxis_transform())
    ax.axhline(today, color=GOLD, lw=2.4, zorder=4)
    ax.scatter([0.5], [today], s=170, color=GOLD, edgecolor="white", linewidth=1.8, zorder=5)
    ax.annotate(f"Today  {today:.1f}{unit}" + (f"  ·  {today_note}" if today_note else ""),
                (0.5, today), textcoords="offset points", xytext=(0, 12), ha="center",
                fontsize=11, color=INK, fontweight="bold", zorder=6)
    lo = min(p10, today) * 0.82; hi = max(p90, today) * 1.14
    ax.set_xlim(0, 1); ax.set_ylim(lo, hi); ax.set_xticks([])
    ax.set_ylabel(f"Weighted trailing P/E ({unit})", fontsize=10, color=SLATE)
    ax.tick_params(labelsize=9)
    ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)
    return _save(fig, name)


# ------------------------------------------------ beta lollipop ladder (stems from market = 1.0)
def beta_ladder(labels, betas, name, market=1.0, flag=1.2, book_beta=None, figsize=(7.6, 5.6)):
    fig, ax = _fig(figsize)
    y = np.arange(len(labels))[::-1]
    for yi, b in zip(y, betas):
        col = SELL if b >= flag else NAVY
        ax.plot([market, b], [yi, yi], color=NT3, lw=2.4, zorder=2)
        ax.scatter([b], [yi], s=95, color=col, zorder=3)
        ax.text(b + (0.018 if b >= market else -0.018), yi, f"{b:.2f}",
                va="center", ha=("left" if b >= market else "right"),
                fontsize=9, color=INK)
    ax.axvline(market, color=INK, lw=1.2, zorder=4)
    ax.text(market, len(labels) - 0.25, f"market = {market:.1f}", ha="center",
            fontsize=8.5, color=SLATE, style="italic")
    ax.axvline(flag, color=SELL, lw=1.2, ls=(0, (4, 3)), zorder=2)
    ax.text(flag + 0.008, -0.55, f"high-beta line {flag:.1f}", fontsize=8, color=SELL, style="italic")
    if book_beta is not None:
        ax.axvline(book_beta, color=GOLD, lw=1.6, ls=(0, (4, 3)), zorder=4)
        ax.text(book_beta, len(labels) - 0.95, f"book {book_beta:.2f}", ha="center",
                fontsize=8.5, color="#8A6E1B", fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9.5, color=INK)
    lo = min(min(betas), market) - 0.14; hi = max(max(betas), flag) + 0.14
    ax.set_xlim(lo, hi); ax.set_xticks([])
    return _save(fig, name)


# ------------------------------------------------ revenue geography stacked bars (look-through)
def geo_stack(rows, name, cats=("India", "US", "Europe", "Other"),
              colors=(NAVY, GOLD, NT2, NT3), figsize=(9.0, 5.2)):
    """rows: list of (label, [pct x4]); the LAST row is drawn emphasised (book total)."""
    fig, ax = _fig(figsize)
    y = np.arange(len(rows))[::-1]
    for yi, (lab, vals) in zip(y, rows):
        hgt = 0.72 if yi == y[-1] else 0.58
        left = 0
        for v, col in zip(vals, colors):
            if v <= 0:
                continue
            ax.barh(yi, v, left=left, height=hgt, color=col, edgecolor="white",
                    linewidth=1.2, zorder=3)
            if v >= 9:
                tc = "white" if col in (NAVY, NT1) else INK
                ax.text(left + v / 2, yi, f"{v:.0f}", ha="center", va="center",
                        fontsize=8.5, color=tc, fontweight="bold")
            left += v
    labels = [r[0] for r in rows]
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9.5, color=INK)
    # emphasise the total row label
    ax.get_yticklabels()[-1].set_fontweight("bold")
    ax.set_xlim(0, 100); ax.set_xticks([])
    handles = [_mpl.patches.Patch(facecolor=c, label=l) for c, l in zip(colors, cats)]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 1.10),
              frameon=False, fontsize=9, ncol=4)
    return _save(fig, name)


# ------------------------------------------------ market-cap mix migration (two 100% columns)
def mcap_migration(cats, before, after, name, colors=None, figsize=(7.2, 5.4)):
    """before/after: lists of pcts summing ~100. Connectors between segment boundaries,
    per-segment change labels on the right."""
    colors = colors or [NAVY, NT1, NT2, GOLD]
    fig, ax = _fig(figsize)
    xs = [0.0, 0.85]; w = 0.38
    cum = [0.0, 0.0]
    bounds = [[0.0], [0.0]]
    deltas = []
    for ci, cat in enumerate(cats):
        for k, vals in enumerate((before, after)):
            v = vals[ci]
            if v > 0:
                ax.bar(xs[k], v, w, bottom=cum[k], color=colors[ci % len(colors)],
                       edgecolor="white", linewidth=1.5, zorder=3)
                if v >= 5:
                    tc = "white" if colors[ci % len(colors)] in (NAVY, NT1) else INK
                    ax.text(xs[k], cum[k] + v / 2, f"{v:.1f}", ha="center", va="center",
                            fontsize=9.5, color=tc, fontweight="bold")
            cum[k] += v
            bounds[k].append(cum[k])
        # connector between the tops of this segment
        ax.plot([xs[0] + w / 2, xs[1] - w / 2], [bounds[0][-1], bounds[1][-1]],
                color=HAIR, lw=1.1, zorder=1)
        d = after[ci] - before[ci]
        if abs(d) >= 0.05 and after[ci] + before[ci] > 0:
            deltas.append([cat, d, bounds[1][-1] - max(after[ci], 0.8) / 2])
    # change labels right of the After column, pushed apart so they never collide
    deltas.sort(key=lambda r: r[2])
    for i in range(1, len(deltas)):
        if deltas[i][2] - deltas[i - 1][2] < 6.0:
            deltas[i][2] = deltas[i - 1][2] + 6.0
    for cat, d, yy in deltas:
        ax.annotate(f"{cat}  {d:+.1f} pt", (xs[1] + w / 2 + 0.05, yy), fontsize=9,
                    color=(SELL if d < 0 else HOLD), fontweight="bold", va="center")
    for k, lab in ((0, "Before"), (1, "After the plan")):
        ax.text(xs[k], -6.5, lab, ha="center", fontsize=11, color=INK, fontweight="bold")
    handles = [_mpl.patches.Patch(facecolor=colors[i % len(colors)], label=c)
               for i, c in enumerate(cats)]
    ax.legend(handles=handles, loc="lower center", bbox_to_anchor=(0.5, 1.01),
              frameon=False, fontsize=9, ncol=len(cats))
    ax.set_xlim(-0.45, 1.95); ax.set_ylim(0, 106)
    ax.set_xticks([]); ax.set_yticks([])
    return _save(fig, name)


# ------------------------------------------------ historical drawdown episodes (education)
def drawdown_bars(events, name, figsize=(10.8, 4.4)):
    """events: list of (label, drawdown_pct_negative, recovery_months)."""
    fig, ax = _fig(figsize)
    x = np.arange(len(events))
    for i, (lab, dd, rec) in enumerate(events):
        ax.bar(i, dd, 0.58, color=SELL, alpha=0.85, zorder=3)
        ax.text(i, dd - 2.5, f"{dd:.0f}%", ha="center", va="top", fontsize=11,
                color=SELL, fontweight="bold")
        ax.text(i, 2.5, f"~{rec} months\nto recover", ha="center", va="bottom",
                fontsize=8.5, color=SLATE)
    ax.axhline(0, color=INK, lw=1.2, zorder=4)
    ax.set_xticks(x); ax.set_xticklabels([e[0] for e in events], fontsize=10, color=INK)
    lo = min(e[1] for e in events)
    ax.set_ylim(lo * 1.18, 16); ax.set_yticks([])
    return _save(fig, name)


# ------------------------------------------------ staged deployment paths (lumpsum vs staggered)
def staged_paths(months, paths, name, figsize=(9.0, 5.0)):
    """months: array of month indices. paths: list of (label, series, color).
    Value of Rs 100 committed on day 0 under each entry schedule."""
    fig, ax = _fig(figsize)
    for lab, series, col in paths:
        ax.plot(months, series, color=col, lw=2.2, zorder=3)
        ax.annotate(f"{lab}  Rs {series[-1]:.0f}", (months[-1], series[-1]),
                    textcoords="offset points", xytext=(6, 0), fontsize=9.5,
                    color=col, fontweight="bold", va="center")
    ax.axhline(100, color=HAIR, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(7.6, 100.9, "Rs 100 committed", fontsize=8.5, color=SLATE, style="italic")
    ax.set_xlabel("Months from decision", fontsize=10, color=SLATE)
    ax.set_ylabel("Value of Rs 100 committed", fontsize=10, color=SLATE)
    ax.set_xticks([0, 6, 12, 18, 24]); ax.tick_params(labelsize=9)
    ax.set_xlim(0, months[-1] + 6.5)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_visible(True); ax.spines[sp].set_color(HAIR)
    return _save(fig, name)


# ------------------------------------------------ LTCG unlock timeline (bars + cumulative)
def ltcg_unlock(labels, start_pct, adds, name, figsize=(10.4, 4.4)):
    """adds: % of taxable gain turning long-term in each quarter. A gold cumulative line
    starts at start_pct (already long-term today)."""
    fig, ax = _fig(figsize)
    x = np.arange(len(labels))
    ax.bar(x, adds, 0.58, color=NAVY, zorder=3)
    for xi, v in zip(x, adds):
        ax.text(xi, v + 1.2, f"+{v:.0f}", ha="center", fontsize=9.5, color=INK, fontweight="bold")
    cum = start_pct + np.cumsum(adds)
    ax.plot(np.concatenate(([-0.7], x)), np.concatenate(([start_pct], cum)),
            color=GOLD, lw=2.2, marker="o", markersize=5,
            markeredgecolor="white", zorder=4)
    for xi, c in zip(x, cum):
        ax.text(xi, c + 2.5, f"{c:.0f}%", ha="center", fontsize=8.5, color="#8A6E1B",
                fontweight="bold")
    ax.text(-1.05, start_pct - 6.0, f"already long-term\ntoday: {start_pct:.0f}%",
            ha="left", va="top", fontsize=8.5, color="#8A6E1B")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=9, color=INK)
    ax.set_ylim(0, max(cum.max(), 100) * 1.10); ax.set_yticks([])
    ax.set_xlim(-1.2, len(labels) - 0.4)
    return _save(fig, name)


if __name__ == "__main__":
    print(score_vs_call([24, 58, 45, 67, 33, 51], [2, 0, 1, 2, 0, 2],
                        [80e5, 8e5, 12e5, 30e5, 9e5, 20e5],
                        ["up", "down", None, None, None, None],
                        ["RELIANCE", "POWERINDIA", "ITC", "TITAN", "TATAPOWER", "HDFCBANK"], "tb_svc"))
    print(percentile_gauge(22, 26, 31, 37, 44, 41.0, "tb_gauge", today_note="~84th percentile"))
    print(beta_ladder(["TATASTEEL", "ABB", "LT", "HDFCBANK", "ITC", "SUNPHARMA"],
                      [1.38, 1.24, 1.22, 1.08, 0.74, 0.81], "tb_beta", book_beta=1.04))
    print(geo_stack([("Persistent", [32, 48, 14, 6]), ("Sun Pharma", [45, 32, 13, 10]),
                     ("Reliance", [82, 4, 6, 8]), ("EQUITY BOOK", [88, 5, 4, 3])], "tb_geo"))
    print(mcap_migration(["Large cap", "Mid cap", "Small cap", "Foreign"],
                         [98.2, 1.6, 0.2, 0.0], [94.1, 1.7, 0.2, 4.0], "tb_mig"))
    print(drawdown_bars([("2008", -60, 20), ("2011", -28, 19), ("2013", -15, 7),
                         ("2020", -38, 9), ("2022", -17, 16)], "tb_dd"))
    m = np.arange(25)
    print(staged_paths(m, [("Lumpsum", 100 + m * 0.7, NAVY),
                           ("6-mo staged", 100 + m * 0.8, GOLD),
                           ("12-mo staged", 100 + m * 0.9, NT1)], "tb_paths"))
    print(ltcg_unlock(["Sep 26", "Dec 26", "Mar 27", "Jun 27", "Sep 27", "Dec 27", "Mar 28", "Jun 28"],
                      34, [9, 12, 10, 8, 7, 6, 4, 3], "tb_ltcg"))
    print("OK chart_ext_b")
