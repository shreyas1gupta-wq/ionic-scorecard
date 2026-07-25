# -*- coding: utf-8 -*-
"""chart_lib.py — Ionic-styled matplotlib chart engine for the Portfolio Review deck.
Renders publication-quality graphics as high-res transparent PNGs for embedding in python-pptx.
Every function returns the saved PNG path. Private-bank / data-journalism aesthetic:
navy ramp + one gold focal accent, no gridline clutter, direct labels, generous whitespace.
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import FancyBboxPatch
import numpy as np
try:
    import squarify
except Exception:
    squarify = None

# ---- palette (Ionic Wealth by Angel One brand: indigo-blue + orange, green/red calls) ----
NAVYD = "#10197A"; NAVY = "#1B27A3"; NT1 = "#4A57C4"; NT2 = "#8C95DE"; NT3 = "#C9CEF0"
GOLD = "#F2A93C"; INK = "#16233B"; SLATE = "#6B7280"; HAIR = "#E5E7EB"; PANEL = "#F5F6FC"
SELL = "#E0402F"; SELLBG = "#FBE3E0"; HOLD = "#1E9E6A"; HOLDBG = "#E0F2EA"; WHITE = "#FFFFFF"
ORANGE = GOLD
NAVY_RAMP = [NAVY, NT1, NT2, NT3]
NAVY_CMAP = LinearSegmentedColormap.from_list("ionic_navy", ["#FFFFFF", NT3, NT2, NT1, NAVY])

# pick a clean sans available on Windows
for _f in ("Bahnschrift", "Segoe UI", "Corbel", "DejaVu Sans"):
    if any(_f.lower() in f.name.lower() for f in fm.fontManager.ttflist):
        SANS = _f; break
else:
    SANS = "DejaVu Sans"

OUTDIR = os.environ.get("CHART_OUTDIR",
    r"C:\Users\SHREYA~1.1GU\AppData\Local\Temp\claude\c--Users-Shreyas-1Gupta-OneDrive---Angel-Broking-Limited-Desktop-Backup-NIFTY-500\5ec2bf16-8c38-4f40-9e4f-8e07be6545fd\scratchpad\charts")
os.makedirs(OUTDIR, exist_ok=True)


def _rc():
    plt.rcParams.update({
        "font.family": "sans-serif", "font.sans-serif": [SANS, "DejaVu Sans"],
        "text.color": INK, "axes.edgecolor": HAIR, "axes.labelcolor": SLATE,
        "xtick.color": SLATE, "ytick.color": SLATE, "font.size": 12,
        "axes.unicode_minus": False,   # ASCII hyphen (Bahnschrift lacks U+2212)
        "svg.fonttype": "none", "figure.dpi": 240,
    })


def _fig(figsize):
    _rc()
    fig, ax = plt.subplots(figsize=figsize, dpi=240)
    fig.patch.set_alpha(0)
    ax.set_facecolor("none")
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    return fig, ax


def _save(fig, name):
    p = os.path.join(OUTDIR, name + ".png")
    fig.savefig(p, transparent=True, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)
    return p


# ---- house chart-chrome helpers (v7 audit, 2026-07-25) ----------------------------
import matplotlib.patheffects as _pe

def halo(artist, lw=2.4, fg="white"):
    """White stroke behind text so labels survive landing on a filled bar (bar3d's
    defensive pattern, promoted library-wide)."""
    artist.set_path_effects([_pe.withStroke(linewidth=lw, foreground=fg)])
    return artist

def caption_above(ax, text, y=1.05):
    """Series key as a caption line ABOVE the axes. House rule: never ax.legend() —
    a boxed legend inside the data area collides with bar labels (v7 has zero of them)."""
    return ax.text(0, y, text, transform=ax.transAxes, fontsize=8.5, color=SLATE, ha="left")

def chip_legend(ax, items, y=-0.30, x0=0.0, dx=0.24):
    """Manual color-chip + label row below the axes (v7 p.19 'BY CATEGORY' grid),
    for charts with too many categories for inline labels."""
    for i, (col, lab) in enumerate(items):
        ax.add_patch(plt.Rectangle((x0 + i * dx, y), 0.018, 0.10, transform=ax.transAxes,
                                   facecolor=col, edgecolor="white", linewidth=1, clip_on=False))
        ax.text(x0 + i * dx + 0.026, y + 0.05, lab, transform=ax.transAxes,
                fontsize=8.5, color=INK, va="center", clip_on=False)


# ---------------------------------------------------------------- donut
def donut(pairs, name, colors=None, center_top="", center_bot="", figsize=(4.4, 4.4)):
    colors = colors or NAVY_RAMP
    fig, ax = _fig(figsize)
    vals = [v for _, v in pairs]
    wedges, _ = ax.pie(vals, colors=colors[:len(vals)], startangle=90, counterclock=False,
                       wedgeprops=dict(width=0.34, edgecolor="white", linewidth=3))
    # direct labels at wedge midpoints
    for w, (lab, v) in zip(wedges, pairs):
        ang = np.deg2rad((w.theta1 + w.theta2) / 2)
        r = 1.16
        ha = "left" if np.cos(ang) >= 0 else "right"
        ax.text(r*np.cos(ang), r*np.sin(ang), lab, ha=ha, va="center", fontsize=12,
                color=INK, fontweight="bold")
        ax.text(r*np.cos(ang), r*np.sin(ang)-0.13, f"{v:.1f}%", ha=ha, va="center",
                fontsize=11, color=SLATE)
    if center_top:
        ax.text(0, 0.08, center_top, ha="center", va="center", fontsize=17, color=INK, fontweight="bold")
    if center_bot:
        ax.text(0, -0.16, center_bot, ha="center", va="center", fontsize=9, color=SLATE)
    ax.set(aspect="equal"); ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.4, 1.4)
    return _save(fig, name)


# ---------------------------------------------------------------- horizontal bars
def hbar(labels, values, name, highlight=0, fmt="{:.1f}%", figsize=(7.0, 4.2), color=NT3, hcolor=NAVY,
         threshold=None, threshold_label=None):
    """Ranked bars, one hero. threshold: optional guideline value drawn as a gold line with its
    label ON the line (v7 p.21 '25% guideline' grammar) — never a legend."""
    fig, ax = _fig(figsize)
    y = np.arange(len(labels))[::-1]
    cols = [hcolor if i == highlight else color for i in range(len(labels))]
    ax.barh(y, values, color=cols, height=0.62, zorder=3)
    for yi, v in zip(y, values):
        ax.text(v + max(values)*0.015, yi, fmt.format(v), va="center", ha="left",
                fontsize=11, color=INK)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=11, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, max(values)*1.16)
    if threshold is not None:
        ax.axvline(threshold, color=GOLD, lw=1.8, zorder=4)
        ax.set_ylim(-0.6, len(labels) - 0.15)
        halo(ax.text(threshold + max(values)*0.012, len(labels) - 0.42,
                     threshold_label or f"{threshold:g}", fontsize=9, color="#8A6E1B",
                     fontweight="bold", ha="left", zorder=5))
    return _save(fig, name)


# ---------------------------------------------------------------- paired bars (fund vs benchmark)
def paired_bar(labels, a_vals, b_vals, name, a_label="Fund", b_label="Benchmark",
               figsize=(7.6, 4.4), alpha_vals=None):
    fig, ax = _fig(figsize)
    x = np.arange(len(labels)); w = 0.36
    ax.bar(x - w/2, b_vals, w, color=NT3, zorder=3)
    ax.bar(x + w/2, a_vals, w, color=NAVY, zorder=3)
    for xi, (a, b) in enumerate(zip(a_vals, b_vals)):
        ax.text(xi + w/2, a + max(a_vals)*0.02, f"{a:.1f}", ha="center", fontsize=10, color=INK, fontweight="bold")
        ax.text(xi - w/2, b + max(a_vals)*0.02, f"{b:.0f}", ha="center", fontsize=9, color=SLATE)
        if alpha_vals is not None:
            ax.text(xi, max(a, b) + max(a_vals)*0.10, f"+{alpha_vals[xi]:.1f}", ha="center",
                    fontsize=10, color=NT1, fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=10, color=INK)
    ax.set_yticks([]); ax.set_ylim(0, max(a_vals)*1.25)
    return _save(fig, name)


# ---------------------------------------------------------------- waterfall / bridge
def waterfall(steps, name, figsize=(11.0, 4.0), gold_idx=None):
    """steps: list of (label, value, kind) kind in open/flow/close."""
    fig, ax = _fig(figsize)
    cum = 0; x = np.arange(len(steps)); w = 0.62
    for i, (lab, v, kind) in enumerate(steps):
        if kind in ("open", "close"):
            bottom, height = 0, v; cum = v
        else:
            bottom, height = cum - v, v; cum = cum - v
        col = NAVY if kind in ("open", "close") else NT2
        ax.bar(i, height, w, bottom=bottom, color=col, zorder=3)
        cap_h = 0
        if gold_idx is not None and i == gold_idx:
            cap_h = height * 0.045
            ax.bar(i, cap_h, w, bottom=bottom + height, color=GOLD, zorder=4)
        halo(ax.text(i, bottom + height + cap_h + max(1, cum)*0.02, f"{v/1e5:.1f}", ha="center",
                     fontsize=10.5, color=INK, fontweight="bold"))
        if i < len(steps)-1:
            ax.plot([i+w/2, i+1-w/2], [cum, cum], color=HAIR, lw=1, zorder=1)
    ax.set_xticks(x); ax.set_xticklabels([s[0] for s in steps], fontsize=9, color=SLATE)
    ax.set_yticks([])
    return _save(fig, name)


# ---------------------------------------------------------------- dumbbell (current vs target)
def dumbbell(labels, a_vals, b_vals, name, a_label="Today", b_label="Target",
             figsize=(7.4, 4.2), fmt="{:.1f}%"):
    fig, ax = _fig(figsize)
    y = np.arange(len(labels))[::-1]
    for yi, a, b in zip(y, a_vals, b_vals):
        ax.plot([a, b], [yi, yi], color=HAIR, lw=3, zorder=1, solid_capstyle="round")
        ax.scatter([a], [yi], s=120, color=NT3, zorder=3)
        ax.scatter([b], [yi], s=120, color=NAVY, zorder=3)
        ax.text(a, yi+0.28, fmt.format(a), ha="center", fontsize=9, color=SLATE)
        ax.text(b, yi-0.34, fmt.format(b), ha="center", fontsize=9.5, color=NAVY, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=11, color=INK)
    ax.set_xticks([]); ax.set_xlim(-0.5, max(max(a_vals), max(b_vals))*1.15)
    caption_above(ax, f"pale = {a_label}   ·   navy = {b_label}")
    return _save(fig, name)


# ---------------------------------------------------------------- radar / spider
def radar(cats, values, name, values2=None, label1="", label2="", figsize=(4.8, 4.8), color=NAVY):
    _rc()
    n = len(cats); ang = np.linspace(0, 2*np.pi, n, endpoint=False).tolist(); ang += ang[:1]
    fig, ax = plt.subplots(figsize=figsize, dpi=200, subplot_kw=dict(polar=True))
    fig.patch.set_alpha(0); ax.set_facecolor("none")
    def plot(vals, col, fill_alpha=0.18, lw=2):
        v = list(vals) + [vals[0]]
        ax.plot(ang, v, color=col, lw=lw, zorder=3)
        ax.fill(ang, v, color=col, alpha=fill_alpha, zorder=2)
    if values2 is not None:
        plot(values2, NT2, 0.10, 1.5)
    plot(values, color, 0.20, 2.2)
    ax.set_xticks(ang[:-1]); ax.set_xticklabels(cats, fontsize=10, color=INK)
    ax.set_yticks([20, 40, 60, 80]); ax.set_yticklabels(["20", "40", "60", "80"], fontsize=8, color=SLATE)
    ax.set_ylim(0, 100); ax.spines["polar"].set_color(HAIR); ax.grid(color=HAIR, lw=0.8)
    ax.set_theta_offset(np.pi/2); ax.set_theta_direction(-1)
    return _save(fig, name)


# ---------------------------------------------------------------- heatmap
def heatmap(row_labels, col_labels, matrix, name, figsize=(7.6, 4.6), fmt="{:.0f}", vmax=100):
    fig, ax = _fig(figsize)
    M = np.array(matrix, dtype=float)
    ax.imshow(M, cmap=NAVY_CMAP, aspect="auto", vmin=0, vmax=vmax)
    ax.set_xticks(range(len(col_labels))); ax.set_xticklabels(col_labels, fontsize=9, color=INK, rotation=0)
    ax.set_yticks(range(len(row_labels))); ax.set_yticklabels(row_labels, fontsize=9.5, color=INK)
    for i in range(M.shape[0]):
        for j in range(M.shape[1]):
            v = M[i, j]
            tc = "white" if v > vmax*0.55 else INK
            ax.text(j, i, fmt.format(v), ha="center", va="center", fontsize=8.5, color=tc)
    ax.set_xticks(np.arange(-.5, len(col_labels), 1), minor=True)
    ax.set_yticks(np.arange(-.5, len(row_labels), 1), minor=True)
    ax.grid(which="minor", color="white", lw=2); ax.tick_params(which="minor", length=0)
    return _save(fig, name)


# ---------------------------------------------------------------- treemap
def treemap(labels, sizes, name, colors=None, figsize=(11.0, 4.4), value_labels=None):
    fig, ax = _fig(figsize)
    colors = colors or [NAVY_RAMP[i % 4] for i in range(len(sizes))]
    if squarify is None:
        ax.text(0.5, 0.5, "treemap unavailable", ha="center"); return _save(fig, name)
    norm = squarify.normalize_sizes(sizes, 100, 100)
    rects = squarify.squarify(norm, 0, 0, 100, 100)
    for r, lab, col, i in zip(rects, labels, colors, range(len(labels))):
        ax.add_patch(plt.Rectangle((r["x"], r["y"]), r["dx"], r["dy"], facecolor=col,
                                   edgecolor="white", linewidth=2))
        if r["dx"] > 7 and r["dy"] > 7:
            tc = "white" if col in (NAVY, NT1, NAVYD, SELL, HOLD) else INK
            fs = max(6.5, min(11, r["dx"] / 2.2))   # floor: tiny type is worse than no label
            ax.text(r["x"]+r["dx"]/2, r["y"]+r["dy"]/2+ (2 if value_labels else 0), lab,
                    ha="center", va="center", fontsize=fs, color=tc, fontweight="bold")
            if value_labels:
                ax.text(r["x"]+r["dx"]/2, r["y"]+r["dy"]/2-3, value_labels[i], ha="center",
                        va="center", fontsize=8.5, color=tc)
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.invert_yaxis()
    ax.set_xticks([]); ax.set_yticks([])
    return _save(fig, name)


# ---------------------------------------------------------------- histogram / distribution
def histogram(values, name, threshold=40, figsize=(10.6, 4.2), bins=None):
    fig, ax = _fig(figsize)
    bins = bins if bins is not None else list(range(0, 101, 10))
    counts, edges = np.histogram(values, bins=bins)
    centers = (edges[:-1]+edges[1:])/2
    cols = [SELL if c < threshold else NAVY for c in centers]
    # soften: below-threshold in muted terracotta tint, above in navy
    cols = ["#E4B7BD" if c < threshold else NAVY for c in centers]
    ax.axvspan(0, threshold, color=SELLBG, alpha=0.5, zorder=0)
    ax.bar(centers, counts, width=8.4, color=cols, zorder=3)
    for c, n in zip(centers, counts):
        if n: ax.text(c, n+0.2, str(int(n)), ha="center", fontsize=10, color=INK, fontweight="bold")
    ax.axvline(threshold, color=GOLD, lw=2, zorder=4)
    halo(ax.text(threshold+1, max(counts)*0.96, f"Sell below {threshold}",
                 fontsize=9.5, color=INK, fontweight="bold", zorder=5))
    ax.set_xticks(bins); ax.set_xticklabels([str(b) for b in bins], fontsize=9, color=SLATE)
    ax.set_yticks([])
    return _save(fig, name)


# ---------------------------------------------------------------- bubble (weight vs score)
def bubble(x, y, sizes, colors, name, labels=None, threshold=40, figsize=(11.0, 5.2),
           xlabel="Weight (%)", ylabel="Binding Ionic Score"):
    fig, ax = _fig(figsize)
    ax.axhspan(0, threshold, color=SELLBG, alpha=0.4, zorder=0)
    ax.axhline(threshold, color=GOLD, lw=1.6, zorder=2)
    s = [max(60, v/1e5*3) for v in sizes]
    ax.scatter(x, y, s=s, c=colors, alpha=0.85, edgecolors="white", linewidths=1.2, zorder=3)
    if labels:
        for xi, yi, lab, sz in zip(x, y, labels, sizes):
            if sz/1e5 > 12 or xi > 3:  # label the big/important ones
                ax.text(xi, yi+2.2, lab, ha="center", fontsize=8.5, color=INK)
    ax.text(0.4, threshold+1.5, "Sell threshold", fontsize=9, color=INK, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=10, color=SLATE); ax.set_ylabel(ylabel, fontsize=10, color=SLATE)
    ax.set_ylim(0, 100); ax.set_xlim(-0.3, max(x)*1.08)
    ax.tick_params(labelsize=9)
    ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)
    ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- lollipop
def lollipop(labels, values, name, threshold=None, figsize=(7.4, 4.6), highlight=0):
    fig, ax = _fig(figsize)
    y = np.arange(len(labels))[::-1]
    for yi, v, i in zip(y, values, range(len(values))):
        col = GOLD if i == highlight else NAVY
        ax.plot([0, v], [yi, yi], color=NT3, lw=2.4, zorder=2)
        ax.scatter([v], [yi], s=90, color=col, zorder=3)
        ax.text(v+max(values)*0.02, yi, f"{v:.1f}", va="center", fontsize=10, color=INK)
    if threshold is not None:
        ax.axvline(threshold, color=GOLD, lw=1.4, ls=(0,(4,3)))
        ax.set_ylim(-0.6, len(labels) - 0.10)
        halo(ax.text(threshold + max(values)*0.012, len(labels) - 0.38, f"{threshold:g}",
                     fontsize=8.5, color="#8A6E1B", fontweight="bold", ha="left", zorder=5))
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=10.5, color=INK)
    ax.set_xticks([]); ax.set_xlim(0, max(values)*1.15)
    return _save(fig, name)


# ---------------------------------------------------------------- 100% stacked bar
def stacked100(segs, name, figsize=(11.0, 1.5)):
    """segs: list of (label, pct, color). Segments >5% are labeled in-bar; if anything is
    smaller, a chip row below names EVERY segment (v7 never lets a slice go unlabeled)."""
    fig, ax = _fig(figsize)
    left = 0
    for lab, pc, col in segs:
        ax.barh(0, pc, left=left, color=col, height=0.6, edgecolor="white", linewidth=2)
        if pc > 5:
            ax.text(left+pc/2, 0, f"{lab}\n{pc:.1f}%", ha="center", va="center",
                    fontsize=9.5, color=("white" if col in (NAVY, NT1) else INK), fontweight="bold")
        left += pc
    ax.set_xlim(0, 100); ax.set_ylim(-0.5, 0.5); ax.set_xticks([]); ax.set_yticks([])
    if any(pc <= 5 for _, pc, _ in segs):
        chip_legend(ax, [(col, f"{lab}  {pc:.1f}%") for lab, pc, col in segs],
                    y=-0.55, dx=0.20)
    return _save(fig, name)


# ---------------------------------------------------------------- small multiples (pillar bars per holding)
def small_multiples_bars(titles, series, cat_labels, name, ncol=4, figsize=(11.0, 5.2), threshold=40):
    _rc()
    n = len(titles); nrow = int(np.ceil(n/ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=figsize, dpi=200)
    fig.patch.set_alpha(0)
    axes = np.array(axes).reshape(-1)
    for k, ax in enumerate(axes):
        ax.set_facecolor("none")
        for s in ax.spines.values(): s.set_visible(False)
        if k >= n:
            ax.axis("off"); continue
        vals = series[k]
        cols = [SELL if v < threshold else NAVY for v in vals]
        ax.bar(range(len(vals)), vals, color=cols, width=0.7)
        ax.axhline(threshold, color=GOLD, lw=1)
        ax.set_title(titles[k], fontsize=9.5, color=INK, fontweight="bold")
        ax.set_ylim(0, 100); ax.set_xticks(range(len(cat_labels)))
        ax.set_xticklabels(cat_labels, fontsize=6.5, color=SLATE)
        ax.set_yticks([]); ax.tick_params(length=0)
    fig.tight_layout()
    p = os.path.join(OUTDIR, name + ".png")
    fig.savefig(p, transparent=True, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return p


# ---------------------------------------------------------------- efficient frontier (opportunity set)
def efficient_frontier(assets, mu, sigma, corr, marks, name, rf=6.0, figsize=(8.6, 5.4), n=6000):
    """Illustrative opportunity set from long-run capital-market assumptions.
    marks: list of (label, weights, color). Cloud coloured by Sharpe; frontier = upper-left edge."""
    _rc()
    mu = np.array(mu, float); sigma = np.array(sigma, float); corr = np.array(corr, float)
    cov = np.outer(sigma, sigma) * corr; k = len(assets)
    rng = np.random.default_rng(7)
    W = rng.dirichlet(np.ones(k) * 0.5, n)
    rets = W @ mu; vols = np.sqrt(np.einsum("ij,jk,ik->i", W, cov, W)); sh = (rets - rf) / vols
    fig, ax = _fig(figsize)
    cmap = LinearSegmentedColormap.from_list("sh", [NT3, NT1, NAVY, GOLD])
    ax.scatter(vols, rets, c=sh, cmap=cmap, s=9, alpha=0.55, edgecolors="none", zorder=2)
    i = int(np.argmax(sh))
    ax.scatter([vols[i]], [rets[i]], s=150, facecolor=GOLD, edgecolor="white", linewidth=1.6, zorder=5)
    ax.annotate("Max-Sharpe mix", (vols[i], rets[i]), textcoords="offset points", xytext=(9, 7),
                fontsize=9.5, color=INK, fontweight="bold")
    for lab, w, col in marks:
        w = np.array(w, float); w = w / w.sum(); r = float(w @ mu); v = float(np.sqrt(w @ cov @ w))
        ax.scatter([v], [r], s=180, facecolor=col, edgecolor="white", linewidth=2, zorder=6)
        ax.annotate(lab, (v, r), textcoords="offset points", xytext=(11, -3), fontsize=10.5, color=col, fontweight="bold")
    ax.set_xlabel("Risk  (annual volatility, %)", fontsize=10.5, color=SLATE)
    ax.set_ylabel("Expected return  (%)", fontsize=10.5, color=SLATE)
    ax.tick_params(labelsize=9.5)
    ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)
    ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- value map (quality vs valuation)
def value_map(pe, roe, sizes, colors, labels, name, figsize=(8.4, 5.4), label_mask=None):
    """Quality (ROE) vs valuation (P/E) bubble map. label_mask: bool per point — label ONLY
    those (a 47-name book labels every bubble into mush; callers pass top-weights + Sells).
    Quadrant tints + slate medians so the read is instant, v7-style."""
    fig, ax = _fig(figsize)
    pe = np.array(pe, float); roe = np.array(roe, float)
    mpe, mroe = float(np.nanmedian(pe)), float(np.nanmedian(roe))
    # cap the x-axis so one silly-P/E outlier can't squash the whole book into a corner
    cap = float(np.nanpercentile(pe, 92)) * 1.5
    n_clip = int(np.nansum(pe > cap))
    if n_clip == 0:
        cap = float(np.nanmax(pe))
    pe_p = np.minimum(pe, cap)
    xr = float(np.nanmax(pe_p) - np.nanmin(pe_p)) or 1.0
    yr = float(np.nanmax(roe) - np.nanmin(roe)) or 1.0
    x0, x1 = np.nanmin(pe_p) - 0.06 * xr, np.nanmax(pe_p) + 0.08 * xr
    y0, y1 = np.nanmin(roe) - 0.10 * yr, np.nanmax(roe) + 0.14 * yr
    # quadrant tints: the sweet spot (cheap + quality) faint green, the trap faint rust
    ax.add_patch(plt.Rectangle((x0, mroe), mpe - x0, y1 - mroe, color=HOLDBG, alpha=0.45, zorder=0))
    ax.add_patch(plt.Rectangle((mpe, y0), x1 - mpe, mroe - y0, color=SELLBG, alpha=0.32, zorder=0))
    ax.axvline(mpe, color=SLATE, ls=(0, (4, 3)), lw=1.0, alpha=0.7, zorder=1)
    ax.axhline(mroe, color=SLATE, ls=(0, (4, 3)), lw=1.0, alpha=0.7, zorder=1)
    ax.text(mpe, y0 + 0.005 * yr, f" book median {mpe:.0f}x", fontsize=7.5, color=SLATE,
            ha="left", va="bottom")
    ax.text(x1, mroe, f"median ROE {mroe:.0f}%  ", fontsize=7.5, color=SLATE, ha="right", va="bottom")
    if n_clip:
        ax.text(x1 - 0.01 * xr, y1 - 0.05 * yr, f"axis capped at {cap:.0f}x · {n_clip} outlier at the edge",
                fontsize=7, color=SLATE, ha="right", va="top", style="italic")
    s = [max(70, v / 1e5 * 3.2) for v in sizes]
    ax.scatter(pe_p, roe, s=s, c=colors, alpha=0.82, edgecolors="white", linewidths=1.1, zorder=3)
    if label_mask is None:
        label_mask = [sz / 1e5 > 16 for sz in sizes]
    # place Sells first (they must be named), then the rest by size; a label that cannot
    # find a clear spot is dropped — an unreadable pile-up is worse than one missing name
    idx = [i for i, m in enumerate(label_mask) if m]
    idx.sort(key=lambda i: (0 if str(colors[i]).upper() == "#E0402F" else 1, -sizes[i]))
    boxes = []
    def _fits(cx, cy, w, h):
        return not any(abs(cx - bx) < (w + bw) / 2 and abs(cy - by) < (h + bh) / 2
                       for bx, by, bw, bh in boxes)
    for i in idx:
        lab = labels[i]; x, y = float(pe_p[i]), float(roe[i])
        w = max(len(lab), 3) * 0.0115 * xr; h = 0.055 * yr
        for dx, dy in ((0, .050), (0, -.070), (.07, 0), (-.07, 0),
                       (0, .105), (0, -.125), (.09, .05), (-.09, .05)):
            cx, cy = x + dx * xr, y + dy * yr
            if (x0 + w / 2 <= cx <= x1 - w / 2 and y0 + h <= cy <= y1 - h
                    and _fits(cx, cy, w, h)):
                ax.text(cx, cy, lab, ha="center", va="center", fontsize=7.8,
                        color=INK, fontweight="bold", zorder=4)
                boxes.append((cx, cy, w, h))
                break
    q = [("quality, sensibly priced", x0 + 0.02 * xr, y1 - 0.015 * yr, "left"),
         ("quality at a price", x1 - 0.02 * xr, y1 - 0.015 * yr, "right"),
         ("cheap for a reason", x0 + 0.02 * xr, y0 + 0.02 * yr, "left"),
         ("expensive and mediocre", x1 - 0.02 * xr, y0 + 0.02 * yr, "right")]
    for t, x, y, ha in q:
        # upright by design (v7's quadrant captions are upright; Bahnschrift has no
        # italic sub-face anyway, so style="italic" would silently no-op)
        ax.text(x, y, t, fontsize=8, color=SLATE, ha=ha,
                va="top" if y > mroe else "bottom", alpha=0.85, zorder=2)
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
    ax.set_xlabel("Valuation  (P/E, x)", fontsize=10.5, color=SLATE)
    ax.set_ylabel("Quality  (ROE, %)", fontsize=10.5, color=SLATE)
    ax.tick_params(labelsize=9.5)
    ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)
    ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- wealth projection cone (goal planning)
def projection_cone(v0, years, mu, sigma, name, goals=None, figsize=(9.2, 5.2)):
    """Lognormal projection of portfolio value (v0 in rupees). Median + p10-p90 band. goals: list of (year,label,amount)."""
    yrs = np.arange(0, years + 1)
    drift = np.log(1 + mu / 100.0) - 0.5 * (sigma / 100.0) ** 2
    p50 = v0 * (1 + mu / 100.0) ** yrs
    z = 1.2816  # 10th / 90th percentile
    lo = v0 * np.exp(drift * yrs - z * (sigma / 100.0) * np.sqrt(yrs))
    hi = v0 * np.exp(drift * yrs + z * (sigma / 100.0) * np.sqrt(yrs))
    fig, ax = _fig(figsize)
    cr = 1e7
    ax.fill_between(yrs, lo / cr, hi / cr, color=NT2, alpha=0.30, zorder=2, label="10th to 90th percentile")
    ax.plot(yrs, p50 / cr, color=NAVY, lw=2.6, zorder=4)
    ax.plot(yrs, hi / cr, color=NT1, lw=1, zorder=3); ax.plot(yrs, lo / cr, color=NT1, lw=1, zorder=3)
    ax.scatter([0], [v0 / cr], s=90, color=GOLD, edgecolor="white", linewidth=1.5, zorder=6)
    ax.annotate(f"Today  ₹{v0/cr:.2f} Cr", (0, v0/cr), textcoords="offset points", xytext=(6, 10), fontsize=9.5, color=INK, fontweight="bold")
    ax.annotate(f"₹{p50[-1]/cr:.1f} Cr", (yrs[-1], p50[-1]/cr), textcoords="offset points", xytext=(-6, 6), fontsize=10.5, color=NAVY, fontweight="bold", ha="right")
    ax.annotate(f"₹{hi[-1]/cr:.1f} Cr", (yrs[-1], hi[-1]/cr), textcoords="offset points", xytext=(-6, 4), fontsize=9, color=NT1, ha="right")
    if goals:
        for gy, glab, gamt in goals:
            ax.axhline(gamt/cr, color=GOLD, ls=(0, (4, 3)), lw=1.3, zorder=3)
            ax.text(0.3, gamt/cr, glab, fontsize=8.5, color="#8A6E1B", va="bottom")
    ax.set_xlabel("Years from today", fontsize=10.5, color=SLATE)
    ax.set_ylabel("Portfolio value  (₹ Cr)", fontsize=10.5, color=SLATE)
    ax.tick_params(labelsize=9.5); ax.set_xlim(0, years)
    ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)
    ax.spines["bottom"].set_visible(True); ax.spines["bottom"].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- 3D bar chart (professional look)
def bar3d(labels, values, name, colors=None, figsize=(8.6, 5.4), fmt="{:.1f}%", elev=22, azim=-52):
    from mpl_toolkits.mplot3d import Axes3D, proj3d  # noqa
    _rc()
    fig = plt.figure(figsize=figsize, dpi=200); fig.patch.set_alpha(0)
    ax = fig.add_subplot(111, projection="3d"); ax.set_facecolor("none")
    n = len(values); xs = np.arange(n); cols = colors or [NAVY_RAMP[i % 4] for i in range(n)]
    dx = dy = 0.62
    ax.view_init(elev=elev, azim=azim)          # set the view BEFORE projecting label positions
    ax.set_zlim(0, max(values)*1.30)            # headroom so labels sit clear of the tallest bar
    for i, (x, v, c) in enumerate(zip(xs, values, cols)):
        ax.bar3d(x - dx/2, -dy/2, 0, dx, dy, v, color=c, shade=True, edgecolor="white", linewidth=0.6)
    ax.set_xticks(xs); ax.set_xticklabels(labels, fontsize=10, color=INK, rotation=0)
    ax.set_yticks([]); ax.set_zticks([]); ax.tick_params(length=0)
    try: ax.set_box_aspect((max(n * 0.62, 1.8), 1, 0.85))
    except Exception: pass
    fig.canvas.draw()                           # finalize the projection matrix
    for x, v in zip(xs, values):
        # mplot3d paints 3D collections OVER 2D axes-level text, so axes annotations can hide
        # behind bars. Instead: project the bar's four TOP CORNERS to display px, place a
        # FIGURE-level label above the bar's full silhouette (figure text always renders above
        # every axes artist), with a soft white chip so it stays readable over any neighbour bar.
        corners = [(x - dx/2, -dy/2), (x + dx/2, -dy/2), (x - dx/2, dy/2), (x + dx/2, dy/2)]
        pts = []
        for cx, cy in corners:
            x2, y2, _ = proj3d.proj_transform(cx, cy, v, ax.get_proj())
            pts.append(ax.transData.transform((x2, y2)))
        xd = sum(p[0] for p in pts) / 4.0
        yd = max(p[1] for p in pts)
        xf, yf = fig.transFigure.inverted().transform((xd, yd + 9))
        fig.text(xf, yf, fmt.format(v), ha="center", va="bottom",
                 fontsize=10.5, color=INK, fontweight="bold",
                 bbox=dict(facecolor="white", alpha=0.78, edgecolor="none",
                           boxstyle="round,pad=0.28"))
    for pane in (ax.xaxis, ax.yaxis, ax.zaxis):
        pane.pane.set_visible(False); pane.line.set_color((1, 1, 1, 0))
    ax.grid(False)
    try: ax.set_box_aspect((n * 0.5, 1, 1.4))
    except Exception: pass
    p = os.path.join(OUTDIR, name + ".png")
    fig.savefig(p, transparent=True, bbox_inches="tight", pad_inches=0.05); plt.close(fig)
    return p


if __name__ == "__main__":
    # smoke test
    print(donut([("Direct equity", 53.8), ("Mutual funds", 46.2)], "t_donut", [NAVY, NT3],
                center_top="Rs 4.33 Cr", center_bot="TOTAL"))
    print(treemap(["Titan", "Reliance", "Groww", "TCS", "ICICI", "Rest"],
                  [11.2, 11.0, 8.7, 7.5, 6.7, 55], "t_treemap",
                  colors=[HOLD, SELL, HOLD, HOLD, HOLD, NT3]))
    print(radar(["Quality", "Growth 3Y", "Value", "Trend", "Growth 1Y", "Macro"],
                [70, 55, 40, 60, 45, 65], "t_radar"))
    print(bubble([11.2, 11.0, 8.7, 7.5, 6.7], [49, 27, 55, 49, 54],
                 [26e5, 25e5, 20e5, 17e5, 15e5], [HOLD, SELL, HOLD, HOLD, HOLD], "t_bubble",
                 labels=["Titan", "Reliance", "Groww", "TCS", "ICICI"]))
    print(waterfall([("Proceeds", 65.8e5, "open"), ("Low-vol/value", 29.6e5, "flow"),
                     ("Foreign eq", 16.4e5, "flow"), ("Gold/silver", 9.9e5, "flow"),
                     ("Cash", 9.9e5, "close")], "t_waterfall", gold_idx=2))
    print("OK charts in", OUTDIR)
