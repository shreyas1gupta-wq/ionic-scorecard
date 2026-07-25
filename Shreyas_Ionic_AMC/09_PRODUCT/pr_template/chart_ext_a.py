# -*- coding: utf-8 -*-
"""chart_ext_a.py - Annexure Set A charts for the v9 template (returns quilt, correlation grid,
risk contribution, stress replay, liquidity ladder, income ladder, concentration curve,
seasonality grid, fee compounding). Reuses chart_lib's figure scaffold and palette; every
function returns the saved PNG path. Everything rendered here is synthetic / [ILLUSTRATIVE]."""
import os
import sys

_SCRIPTS = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "scripts"))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)
_OUT = os.path.join(os.path.dirname(__file__), "_charts")
os.makedirs(_OUT, exist_ok=True)
os.environ.setdefault("CHART_OUTDIR", _OUT)  # chart_lib reads this at import time

import numpy as np
import matplotlib as _mpl
_mpl.rcParams["axes.unicode_minus"] = False  # ASCII hyphen (Bahnschrift lacks U+2212)
from matplotlib.patches import Rectangle
from chart_lib import (_fig, _save, INK, SLATE, HAIR, NAVY, NAVYD, NT1, NT2, NT3, GOLD,
                       SELL, SELLBG, HOLD, HOLDBG, PANEL, WHITE)

GOLD_TXT = "#8A6E1B"   # legible gold for annotations on white
RED_SOFT = "#F5B7AF"   # mid tier between SELLBG and SELL
GRN_SOFT = "#BFE3D2"   # mid tier between HOLDBG and HOLD


# ------------------------------------------------------- 1. asset-class returns quilt
def returns_quilt(years, assets, matrix, name, figsize=(12.6, 4.2)):
    """matrix[i][j] = annual return % of asset i in year j. Cells coloured by within-year
    rank: gold = best of the year, then the navy ramp down to lightest = worst."""
    A, Y = len(assets), len(years)
    M = np.asarray(matrix, float)
    fig, ax = _fig(figsize)
    bg = [GOLD, NAVY, NT1, NT2, NT3]
    fg = [INK, WHITE, WHITE, INK, INK]
    for j in range(Y):
        order = np.argsort(-M[:, j])
        rank = np.empty(A, int)
        rank[order] = np.arange(A)
        for i in range(A):
            r = min(int(rank[i]), 4)
            yb = A - 1 - i
            ax.add_patch(Rectangle((j + 0.03, yb + 0.05), 0.94, 0.90,
                                   facecolor=bg[r], edgecolor=WHITE, linewidth=1.4, zorder=2))
            ax.text(j + 0.5, yb + 0.5, f"{M[i, j]:+.0f}", ha="center", va="center",
                    fontsize=10.5, color=fg[r],
                    fontweight="bold" if r == 0 else "normal", zorder=3)
    for i, a in enumerate(assets):
        ax.text(-0.12, A - 1 - i + 0.5, a, ha="right", va="center", fontsize=10.5,
                color=INK, fontweight="bold")
    for j, yr in enumerate(years):
        ax.text(j + 0.5, A + 0.10, str(yr), ha="center", va="bottom", fontsize=9.5,
                color=SLATE, fontweight="bold")
    labs = ["best of the year", "2nd", "3rd", "4th", "worst"]
    xs = [0.0, 2.3, 3.2, 4.1, 5.2]
    for r, (lab, x0) in enumerate(zip(labs, xs)):
        ax.add_patch(Rectangle((x0, -0.72), 0.28, 0.30, facecolor=bg[r],
                               edgecolor=WHITE, linewidth=1, zorder=2))
        ax.text(x0 + 0.36, -0.57, lab, ha="left", va="center", fontsize=8.5, color=SLATE)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(-2.3, Y + 0.1); ax.set_ylim(-0.95, A + 0.6)
    return _save(fig, name)


# ------------------------------------------------------- 2. correlation lower-triangle grid
def corr_heat(labels, M, name, figsize=(6.8, 5.6)):
    """Lower-triangle pairwise-correlation grid. Green tint = low correlation (diversifying),
    navy = moves together. M symmetric with unit diagonal."""
    n = len(labels)
    M = np.asarray(M, float)
    fig, ax = _fig(figsize)

    def _bg(c):
        if c >= 0.85: return NAVYD
        if c >= 0.70: return NAVY
        if c >= 0.55: return NT1
        if c >= 0.40: return NT3
        if c >= 0.25: return PANEL
        return HOLDBG

    for i in range(n):
        yb = n - 1 - i
        for j in range(i + 1):
            if i == j:
                ax.add_patch(Rectangle((j + 0.03, yb + 0.03), 0.94, 0.94, facecolor=PANEL,
                                       edgecolor=WHITE, linewidth=1.2, zorder=2))
                ax.text(j + 0.5, yb + 0.5, "1.00", ha="center", va="center", fontsize=8,
                        color=SLATE, zorder=3)
            else:
                c = float(M[i, j])
                ax.add_patch(Rectangle((j + 0.03, yb + 0.03), 0.94, 0.94, facecolor=_bg(c),
                                       edgecolor=WHITE, linewidth=1.2, zorder=2))
                ax.text(j + 0.5, yb + 0.5, f"{c:.2f}", ha="center", va="center", fontsize=8.6,
                        color=WHITE if c >= 0.55 else INK, zorder=3)
        ax.text(-0.12, yb + 0.5, labels[i], ha="right", va="center", fontsize=9,
                color=INK, fontweight="bold")
    for j in range(n):
        ax.text(j + 0.5, -0.10, labels[j], ha="right", va="top", fontsize=8, color=SLATE,
                rotation=38)
    # legend in the empty upper-right triangle
    leg = [(HOLDBG, "under 0.25 · diversifies"), (NT3, "0.40 to 0.70 · related"),
           (NAVY, "0.70 plus · moves together")]
    for k, (col, lab) in enumerate(leg):
        y0 = n - 0.55 - 0.60 * k
        ax.add_patch(Rectangle((n - 4.35, y0), 0.30, 0.30, facecolor=col,
                               edgecolor=WHITE, linewidth=1, zorder=2))
        ax.text(n - 3.95, y0 + 0.15, lab, ha="left", va="center", fontsize=8, color=SLATE)
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(-1.9, n + 0.1); ax.set_ylim(-1.25, n + 0.05)
    return _save(fig, name)


# ------------------------------------------------------- 3. risk contribution vs capital weight
def risk_vs_weight(labels, cap_w, risk_w, name, figsize=(7.4, 5.0),
                   cap_label="Capital weight", risk_label="Risk contribution"):
    """Paired hbars per name: capital weight (light) vs estimated risk contribution (navy).
    Risk figures printed in gold where risk clearly outruns capital weight."""
    n = len(labels)
    y = np.arange(n)[::-1].astype(float)
    fig, ax = _fig(figsize)
    h = 0.36
    ax.barh(y + h / 2 + 0.02, cap_w, height=h, color=NT3, zorder=3)
    ax.barh(y - h / 2 - 0.02, risk_w, height=h, color=NAVY, zorder=3)
    mx = max(max(cap_w), max(risk_w))
    for yi, cv, rv in zip(y, cap_w, risk_w):
        ax.text(cv + mx * 0.015, yi + h / 2 + 0.02, f"{cv:.1f}%", va="center", ha="left",
                fontsize=8.5, color=SLATE)
        hot = rv >= 1.35 * cv
        ax.text(rv + mx * 0.015, yi - h / 2 - 0.02, f"{rv:.1f}%", va="center", ha="left",
                fontsize=8.5, color=GOLD_TXT if hot else INK, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9.5, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, mx * 1.18); ax.set_ylim(-0.7, n + 0.75)
    ax.add_patch(Rectangle((0, n + 0.12), mx * 0.025, 0.30, facecolor=NAVY, zorder=3))
    ax.text(mx * 0.035, n + 0.27, risk_label, fontsize=8.5, color=INK, va="center")
    ax.add_patch(Rectangle((mx * 0.42, n + 0.12), mx * 0.025, 0.30, facecolor=NT3, zorder=3))
    ax.text(mx * 0.455, n + 0.27, cap_label, fontsize=8.5, color=INK, va="center")
    return _save(fig, name)


# ------------------------------------------------------- 4. stress-scenario replay bars
def scenario_replay(scenarios, today_dd, prop_dd, name, today_label="Today's mix",
                    prop_label="Proposed mix", figsize=(7.8, 4.7)):
    """Two downward bars per scenario: estimated drawdown on today's mix vs the proposed mix,
    with the improvement in points printed above the zero line."""
    x = np.arange(len(scenarios)).astype(float)
    w = 0.34
    fig, ax = _fig(figsize)
    ax.bar(x - w / 2 - 0.02, today_dd, w, color=NT1, zorder=3)
    ax.bar(x + w / 2 + 0.02, prop_dd, w, color=GOLD, zorder=3)
    lo = min(min(today_dd), min(prop_dd))
    for xi, tv, pv in zip(x, today_dd, prop_dd):
        ax.text(xi - w / 2 - 0.02, tv - abs(lo) * 0.025, f"{tv:.0f}%", ha="center", va="top",
                fontsize=9, color=NAVY, fontweight="bold")
        ax.text(xi + w / 2 + 0.02, pv - abs(lo) * 0.025, f"{pv:.0f}%", ha="center", va="top",
                fontsize=9, color=GOLD_TXT, fontweight="bold")
        ax.text(xi, abs(lo) * 0.03, f"{pv - tv:+.0f} pts", ha="center", va="bottom",
                fontsize=8.5, color=HOLD, fontweight="bold")
    ax.axhline(0, color=HAIR, lw=1, zorder=2)
    ax.set_xticks(x); ax.set_xticklabels(scenarios, fontsize=10, color=INK)
    ax.set_yticks([])
    ax.set_xlim(-0.55, len(scenarios) - 0.45)
    ax.set_ylim(lo * 1.22, abs(lo) * 0.30)
    yl = abs(lo) * 0.20
    ax.add_patch(Rectangle((-0.45, yl), 0.09, abs(lo) * 0.055, facecolor=NT1, zorder=3))
    ax.text(-0.33, yl + abs(lo) * 0.028, today_label, fontsize=8.5, color=INK, va="center")
    ax.add_patch(Rectangle((0.62, yl), 0.09, abs(lo) * 0.055, facecolor=GOLD, zorder=3))
    ax.text(0.74, yl + abs(lo) * 0.028, prop_label, fontsize=8.5, color=INK, va="center")
    return _save(fig, name)


# ------------------------------------------------------- 5. liquidity ladder (stacked bar)
def liquidity_ladder(buckets, pcts, name, figsize=(11.4, 1.95)):
    """Single horizontal stacked bar: % of book exitable per days-to-exit bucket."""
    fig, ax = _fig(figsize)
    cols = [NAVY, NT1, NT2, GOLD]
    fgs = [WHITE, WHITE, INK, INK]
    x = 0.0
    for i, (b, p) in enumerate(zip(buckets, pcts)):
        ax.barh(0.15, p, left=x, height=0.60, color=cols[i % 4], edgecolor=WHITE,
                linewidth=1.5, zorder=3)
        if p >= 4.5:
            ax.text(x + p / 2, 0.15, f"{p:.0f}%", ha="center", va="center", fontsize=12,
                    color=fgs[i % 4], fontweight="bold", zorder=4)
        ly = -0.34 if i % 2 == 0 else -0.60
        ax.text(x + p / 2, ly, b, ha="center", va="top", fontsize=9.5, color=SLATE)
        x += p
    ax.set_xlim(0, 100); ax.set_ylim(-1.05, 0.62)
    ax.set_xticks([]); ax.set_yticks([])
    return _save(fig, name)


# ------------------------------------------------------- 6. income ladder (hbar, Rs lakhs)
def income_hbar(labels, values_l, name, figsize=(7.2, 4.8)):
    """Estimated annual dividend income by holding, Rs lakhs, sorted desc; top bar gold."""
    n = len(labels)
    y = np.arange(n)[::-1]
    fig, ax = _fig(figsize)
    cols = [GOLD if i == 0 else NAVY for i in range(n)]
    ax.barh(y, values_l, color=cols, height=0.62, zorder=3)
    mx = max(values_l)
    for yi, v in zip(y, values_l):
        ax.text(v + mx * 0.015, yi, f"Rs {v:.1f} L", va="center", ha="left",
                fontsize=9.5, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=9.5, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, mx * 1.22)
    return _save(fig, name)


# ------------------------------------------------------- 7. concentration (Lorenz-style) curve
def concentration_curve(weights, name, marks=(5, 10, 20), figsize=(7.6, 4.8)):
    """Cumulative share of the equity book vs number of holdings (largest first), against an
    equal-weight diagonal; gold markers at the requested top-N points."""
    w = np.sort(np.asarray(weights, float))[::-1]
    w = w / w.sum() * 100.0
    cum = np.cumsum(w)
    n = len(w)
    x = np.arange(1, n + 1)
    fig, ax = _fig(figsize)
    ax.plot([0, n], [0, 100], color=SLATE, lw=1.1, ls=(0, (4, 3)), zorder=2)
    ax.text(n * 0.62, 48, "equal-weight book", fontsize=8.5, color=SLATE, style="italic",
            rotation=33, ha="center", va="bottom")
    ax.plot(x, cum, color=NAVY, lw=2.4, zorder=3)
    for m in marks:
        if m <= n:
            ax.scatter([m], [cum[m - 1]], s=64, color=GOLD, edgecolor=WHITE,
                       linewidth=1.2, zorder=5)
            ax.annotate(f"top {m}: {cum[m - 1]:.0f}%", (m, cum[m - 1]),
                        textcoords="offset points", xytext=(7, -13), fontsize=9.5,
                        color=GOLD_TXT, fontweight="bold")
    ax.set_xlim(0, n + 1); ax.set_ylim(0, 106)
    ax.set_xlabel("Number of holdings, largest first", fontsize=9.5, color=SLATE)
    ax.set_ylabel("Cumulative share of equity book (%)", fontsize=9.5, color=SLATE)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_xticks([1, 5, 10, 20, 30, n] if n > 30 else [1, 5, 10, n])
    ax.tick_params(labelsize=9)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_visible(True); ax.spines[sp].set_color(HAIR)
    return _save(fig, name)


# ------------------------------------------------------- 8. monthly seasonality grid
def seasonality_heat(row_labels, col_labels, M, name, figsize=(11.4, 3.4)):
    """Years x months grid of monthly returns, diverging colour bins around zero."""
    R, C = len(row_labels), len(col_labels)
    M = np.asarray(M, float)
    fig, ax = _fig(figsize)

    def _bg(v):
        if v <= -4: return SELL
        if v <= -1.5: return RED_SOFT
        if v < 1.5: return PANEL
        if v < 4: return GRN_SOFT
        return HOLD

    for i in range(R):
        yb = R - 1 - i
        for j in range(C):
            v = float(M[i, j])
            ax.add_patch(Rectangle((j + 0.03, yb + 0.05), 0.94, 0.90, facecolor=_bg(v),
                                   edgecolor=WHITE, linewidth=1.2, zorder=2))
            ax.text(j + 0.5, yb + 0.5, f"{v:+.1f}", ha="center", va="center", fontsize=8.6,
                    color=WHITE if (v <= -4 or v >= 4) else INK, zorder=3)
        ax.text(-0.12, yb + 0.5, row_labels[i], ha="right", va="center", fontsize=9.5,
                color=INK, fontweight="bold")
    for j, cl in enumerate(col_labels):
        ax.text(j + 0.5, R + 0.08, cl, ha="center", va="bottom", fontsize=9, color=SLATE,
                fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])
    ax.set_xlim(-1.3, C + 0.1); ax.set_ylim(-0.15, R + 0.55)
    return _save(fig, name)


# ------------------------------------------------------- 9. fee-compounding gap lines
def fee_gap_lines(v0_cr, years, gross_pct, fee_lo, fee_hi, name,
                  lo_label="0.4% all-in", hi_label="1.7% all-in", figsize=(8.8, 4.9)):
    """Two projection lines at the same gross return net of two fee levels; the gap between
    them shaded gold with the terminal rupee difference labelled. Values in Rs crore."""
    t = np.arange(years + 1)
    lo = v0_cr * (1 + (gross_pct - fee_lo) / 100.0) ** t
    hi = v0_cr * (1 + (gross_pct - fee_hi) / 100.0) ** t
    fig, ax = _fig(figsize)
    ax.fill_between(t, hi, lo, color=GOLD, alpha=0.28, zorder=2)
    ax.plot(t, lo, color=NAVY, lw=2.4, zorder=4)
    ax.plot(t, hi, color=NT2, lw=2.0, zorder=3)
    ax.text(years + 0.4, lo[-1], f"Rs {lo[-1]:.1f} Cr\n{lo_label}", fontsize=9.5,
            color=NAVY, fontweight="bold", va="center")
    ax.text(years + 0.4, hi[-1], f"Rs {hi[-1]:.1f} Cr\n{hi_label}", fontsize=9.5,
            color=SLATE, va="center")
    gap = lo[-1] - hi[-1]
    xm = int(years * 0.8)
    ax.text(xm, (lo[xm] + hi[xm]) / 2, f"Rs {gap:.1f} Cr\nthe fee gap", ha="center",
            va="center", fontsize=10.5, color=GOLD_TXT, fontweight="bold", zorder=5)
    ax.set_xlim(-0.3, years + 4.2); ax.set_ylim(0, lo[-1] * 1.14)
    ax.set_xticks([0, 5, 10, 15, years])
    ax.set_yticks([])
    ax.set_xlabel("Years from today", fontsize=9.5, color=SLATE)
    ax.tick_params(labelsize=9)
    ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(HAIR)
    return _save(fig, name)
