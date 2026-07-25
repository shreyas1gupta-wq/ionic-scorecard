# -*- coding: utf-8 -*-
"""chart_lib_ext.py — v9 template additions to the Ionic chart engine.
Reuses chart_lib's figure scaffold, palette and save path. 7 new charts for the
fund-evaluation, cost, tax and allocation modules. Every fn returns the PNG path.
"""
import numpy as np
import matplotlib as _mpl
_mpl.rcParams["axes.unicode_minus"] = False  # use ASCII hyphen (Bahnschrift lacks U+2212)
import chart_lib as C
from chart_lib import (_fig, _save, halo, caption_above, chip_legend,
                       INK, SLATE, HAIR, NAVY, NAVYD, NT1, NT2, NT3, GOLD, SELL, SELLBG, HOLD, HOLDBG, PANEL)


# ---------------------------------------------------------------- up/down capture scatter (equity funds)
def capture_scatter(up, down, sizes, colors, labels, name, figsize=(8.6, 5.6)):
    """UP-capture (x) vs DOWN-capture (y). Below the 45deg line = captures more up than down (good).
    Shaded ideal NW zone: up>=100 & down<=100."""
    fig, ax = _fig(figsize)
    up = np.array(up, float); down = np.array(down, float)
    lo = min(60, up.min(), down.min()) - 5; hi = max(120, up.max(), down.max()) + 5
    # ideal zone: up high, down low
    ax.axhspan(lo, 100, xmin=(100-lo)/(hi-lo), xmax=1, color=HOLDBG, alpha=0.5, zorder=0)
    ax.text(hi-2, lo+3, "captures the upside,\nspares the downside", ha="right", va="bottom",
            fontsize=8.5, color=HOLD, style="italic")
    ax.plot([lo, hi], [lo, hi], color=SLATE, lw=1, ls=(0, (4, 3)), zorder=1)
    ax.text(hi-2, hi-2, "symmetric", ha="right", va="top", fontsize=8, color=SLATE, rotation=45)
    ax.axhline(100, color=HAIR, lw=1, zorder=1); ax.axvline(100, color=HAIR, lw=1, zorder=1)
    s = [max(90, v / 1e5 * 3.0) for v in sizes]
    ax.scatter(up, down, s=s, c=colors, alpha=0.85, edgecolors="white", linewidths=1.3, zorder=3)
    for x, y, lab in zip(up, down, labels):
        ax.text(x, y + (hi-lo)*0.02, lab, ha="center", fontsize=8.2, color=INK)
    ax.set_xlabel("Upside capture  (% of benchmark up-moves)", fontsize=10.2, color=SLATE)
    ax.set_ylabel("Downside capture  (% of benchmark down-moves)", fontsize=10.2, color=SLATE)
    ax.set_xlim(lo, hi); ax.set_ylim(hi, lo)  # invert y: lower down-capture = higher on chart
    ax.tick_params(labelsize=9)
    for sp in ("left", "bottom"): ax.spines[sp].set_visible(True); ax.spines[sp].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- drawdown / underwater curve
def drawdown_curve(nav, name, dates=None, figsize=(9.0, 3.4)):
    nav = np.asarray(nav, float); peak = np.maximum.accumulate(nav); dd = (nav / peak - 1.0) * 100
    x = np.arange(len(nav)) if dates is None else dates
    fig, ax = _fig(figsize)
    ax.fill_between(x, dd, 0, color=SELL, alpha=0.28, zorder=2)
    ax.plot(x, dd, color=SELL, lw=1.4, zorder=3)
    i = int(np.argmin(dd))
    ax.scatter([x[i]], [dd[i]], s=70, color=SELL, edgecolor="white", linewidth=1.4, zorder=4)
    ax.annotate(f"max drawdown  {dd[i]:.1f}%", (x[i], dd[i]), textcoords="offset points",
                xytext=(8, -2), fontsize=9.5, color=SELL, fontweight="bold")
    ax.axhline(0, color=HAIR, lw=1)
    ax.set_ylabel("Drawdown from peak (%)", fontsize=9.5, color=SLATE)
    ax.set_ylim(min(dd.min()*1.25, -1), 2); ax.set_xticks([])
    ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- rolling 1Y return band + worst year
def rolling_return_band(nav, name, window=252, figsize=(9.0, 3.8)):
    nav = np.asarray(nav, float)
    if len(nav) <= window + 5:
        fig, ax = _fig(figsize); ax.text(0.5, 0.5, "insufficient history", ha="center", color=SLATE); return _save(fig, name)
    roll = (nav[window:] / nav[:-window] - 1.0) * 100
    x = np.arange(len(roll))
    fig, ax = _fig(figsize)
    ax.axhspan(np.percentile(roll, 10), np.percentile(roll, 90), color=NT3, alpha=0.35, zorder=1)
    ax.plot(x, roll, color=NAVY, lw=1.6, zorder=3)
    ax.axhline(0, color=HAIR, lw=1)
    j = int(np.argmin(roll))
    ax.scatter([x[j]], [roll[j]], s=80, color=GOLD, edgecolor="white", linewidth=1.4, zorder=5)
    ax.annotate(f"worst 1-yr:  {roll[j]:.1f}%", (x[j], roll[j]), textcoords="offset points",
                xytext=(8, -4), fontsize=9.5, color="#8A6E1B", fontweight="bold")
    ax.set_ylabel("Rolling 1-year return (%)", fontsize=9.5, color=SLATE); ax.set_xticks([])
    ax.spines["left"].set_visible(True); ax.spines["left"].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- fee stack (bps)
def fee_stack(rows, name, figsize=(9.4, 4.4)):
    """rows: list of (label, direct_ter_bps, regular_drag_bps, pms_bps). Stacked horizontal bars in bps.
    Direct TER = navy (unavoidable), Regular-plan drag = rust (avoidable), PMS fee = gold."""
    fig, ax = _fig(figsize)
    y = np.arange(len(rows))[::-1]
    for yi, (lab, ter, drag, pms) in zip(y, rows):
        left = 0
        # base segment in NAVY: the primary series is always brand indigo, never periwinkle
        for val, col in ((ter, NAVY), (drag, SELL), (pms, GOLD)):
            if val > 0:
                ax.barh(yi, val, left=left, height=0.6, color=col, alpha=0.92,
                        edgecolor="white", linewidth=1.2, zorder=3)
                left += val
        ax.text(left + 3, yi, f"{left:.0f} bps", va="center", fontsize=9.5, color=INK, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=INK)
    ax.set_xticks([])
    # series key as a caption ABOVE the axes — never a boxed legend inside the data area
    caption_above(ax, "navy = fund TER (direct)   ·   red = Regular-plan drag (avoidable)   ·   gold = PMS / advisory fee")
    ax.set_xlim(0, max(sum(r[1:]) for r in rows) * 1.18)
    return _save(fig, name)


# ---------------------------------------------------------------- plain scheme TER bars (no extras)
def ter_bars(rows, name, avg_bps=None, figsize=(9.4, 4.2)):
    """rows: (label, ter_bps). One clean series: what each scheme charges, house indigo,
    direct value labels, optional blended-average marker. No legend, no fee extras
    (Principal 2026-07-25: the NDPMS deck does not show drag / advisory-fee overlays)."""
    fig, ax = _fig(figsize)
    n = len(rows)
    y = np.arange(n)[::-1]
    vals = [float(r[1]) for r in rows]
    ax.barh(y, vals, height=0.62, color=NAVY, alpha=0.92, zorder=3,
            edgecolor="white", linewidth=1.0)
    for yi, v in zip(y, vals):
        ax.text(v + max(vals) * 0.015, yi, f"{v:.0f} bps", va="center", ha="left",
                fontsize=9.5, color=INK, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels([r[0] for r in rows], fontsize=9.5, color=INK)
    ax.set_xticks([])
    ax.set_ylim(-0.95, n - 0.45)
    if avg_bps:
        ax.axvline(avg_bps, color=GOLD, lw=1.6, ls=(0, (5, 3)), zorder=4)
        ax.text(avg_bps, -0.68, f"  blended {avg_bps:.0f} bps", fontsize=9,
                color="#8A6E1B", fontweight="bold", ha="left", va="center")
    ax.set_xlim(0, max(vals) * 1.18)
    return _save(fig, name)


# ---------------------------------------------------------------- tax bridge (gross -> net)
def tax_bridge(gross, ltcg, stcg, name, figsize=(8.6, 4.0)):
    """Waterfall: gross proceeds -> less LTCG -> less STCG -> net deployable. Amounts in rupees."""
    net = gross - ltcg - stcg
    steps = [("Gross proceeds", gross, NAVY), ("less LTCG", ltcg, SELL),
             ("less STCG", stcg, SELL), ("Net deployable", net, HOLD)]
    fig, ax = _fig(figsize)
    cum = gross
    for i, (lab, val, col) in enumerate(steps):
        if i == 0:
            ax.bar(i, val, 0.6, color=col, zorder=3); cum = val
            top = val
        elif lab.startswith("less"):
            ax.bar(i, val, 0.6, bottom=cum - val, color=col, zorder=3); top = cum; cum -= val
        else:
            ax.bar(i, val, 0.6, color=col, zorder=3); top = val
        ax.text(i, (top if not lab.startswith('less') else cum + val) + gross*0.015,
                f"{val/1e5:.1f}L", ha="center", fontsize=9.5, color=INK, fontweight="bold")
        if i < len(steps) - 1 and lab != "Net deployable":
            ax.plot([i+0.3, i+0.7], [cum, cum], color=HAIR, lw=1)
    ax.set_xticks(range(len(steps))); ax.set_xticklabels([s[0] for s in steps], fontsize=8.8, color=SLATE)
    ax.set_yticks([])
    ax.text(len(steps)-1, net + gross*0.06, f"net after est. tax", ha="center", fontsize=8.5, color=HOLD, style="italic")
    return _save(fig, name)


# ---------------------------------------------------------------- fund quality x allocation quadrant
def quality_alloc_quadrant(gap, quality, sizes, colors, labels, name, figsize=(8.8, 5.8)):
    """X = allocation gap vs house view (under<0<over); Y = fund quality (0-100). 4 prescriptive quadrants."""
    fig, ax = _fig(figsize)
    gap = np.array(gap, float); quality = np.array(quality, float)
    xr = max(abs(gap).max(), 3) * 1.25
    ax.axvline(0, color=SLATE, lw=1, zorder=1); ax.axhline(50, color=SLATE, lw=1, ls=(0, (4, 3)), zorder=1)
    quad = [(-xr*0.98, 96, "UNDER-alloc · HIGH quality\nretain / redeployment target", HOLD, "left"),
            (xr*0.98, 96, "OVER-alloc · HIGH quality\ntrim to target, keep the fund", "#8A6E1B", "right"),
            (-xr*0.98, 6, "UNDER-alloc · LOW quality\nswitch the vehicle", SLATE, "left"),
            (xr*0.98, 6, "OVER-alloc · LOW quality\ntrim, then exit — top priority", SELL, "right")]
    for x, y, t, col, ha in quad:
        ax.text(x, y, t, ha=ha, va="center", fontsize=8.3, color=col, fontweight="bold", alpha=0.9)
    s = [max(120, v / 1e5 * 3.4) for v in sizes]
    ax.scatter(gap, quality, s=s, c=colors, alpha=0.85, edgecolors="white", linewidths=1.4, zorder=3)
    for x, y, lab in zip(gap, quality, labels):
        ax.text(x, y + 3, lab, ha="center", fontsize=8.2, color=INK)
    ax.set_xlabel("under-allocated   <—   Allocation gap vs house view   —>   over-allocated", fontsize=9.6, color=SLATE)
    ax.set_ylabel("Fund quality  (0–100)", fontsize=9.6, color=SLATE)
    ax.set_xlim(-xr, xr); ax.set_ylim(0, 104); ax.tick_params(labelsize=9)
    for sp in ("left", "bottom"): ax.spines[sp].set_visible(True); ax.spines[sp].set_color(HAIR)
    return _save(fig, name)


# ---------------------------------------------------------------- over/under allocation diverging bar
def over_under_bar(cats, gap_pct, name, figsize=(8.8, 4.6)):
    """gap_pct: signed % points vs house-view band (negative = under, positive = over)."""
    fig, ax = _fig(figsize)
    y = np.arange(len(cats))[::-1]
    cols = [SELL if g > 0 else NAVY for g in gap_pct]
    ax.barh(y, gap_pct, height=0.6, color=cols, zorder=3)
    ax.axvline(0, color=INK, lw=1.2, zorder=4)
    for yi, g in zip(y, gap_pct):
        ha = "left" if g >= 0 else "right"
        off = max(abs(np.array(gap_pct)))*0.03
        ax.text(g + (off if g >= 0 else -off), yi, f"{g:+.1f}", va="center", ha=ha, fontsize=9.5,
                color=INK, fontweight="bold")
    ax.set_yticks(y); ax.set_yticklabels(cats, fontsize=10, color=INK); ax.set_xticks([])
    m = max(abs(np.array(gap_pct))) * 1.25
    ax.set_xlim(-m, m)
    ax.text(-m*0.98, len(cats)-0.3, "under-allocated", fontsize=8.5, color=NAVY, style="italic")
    ax.text(m*0.98, len(cats)-0.3, "over-allocated", ha="right", fontsize=8.5, color=SELL, style="italic")
    return _save(fig, name)


if __name__ == "__main__":
    print(capture_scatter([112, 98, 105, 88], [118, 92, 101, 70], [30e5, 25e5, 15e5, 10e5],
          [SELL, HOLD, GOLD, HOLD], ["LIC LargeCap", "Quality Flexi", "Multi Cap", "Index"], "t_capture"))
    rng = np.random.default_rng(3); nav = 100 * np.cumprod(1 + rng.normal(0.0004, 0.011, 900))
    print(drawdown_curve(nav, "t_dd")); print(rolling_return_band(nav, "t_roll"))
    print(fee_stack([("LIC Large Cap (Reg)", 95, 78, 0), ("ICICI Multi-Asset (Reg)", 62, 55, 0),
                     ("Quality Flexi (Dir)", 68, 0, 0), ("PMS wrapper", 0, 0, 120)], "t_fee"))
    print(tax_bridge(74e5, 6.2e5, 1.1e5, "t_taxbridge"))
    print(quality_alloc_quadrant([-4, 6, -2, 8], [78, 32, 60, 18], [20e5, 30e5, 15e5, 8e5],
          [HOLD, SELL, GOLD, SELL], ["Quality Flexi", "LIC LargeCap", "Index", "SmallCap"], "t_quad"))
    print(over_under_bar(["Large", "Mid", "Small", "Foreign", "Gold", "Debt"],
          [8.5, 3.0, -1.5, -12.0, -4.0, 6.0], "t_overunder"))
    print("OK ext charts")
