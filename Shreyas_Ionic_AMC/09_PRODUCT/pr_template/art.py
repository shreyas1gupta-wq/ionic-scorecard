# -*- coding: utf-8 -*-
"""art.py — generative brand art for the cover and section dividers. Abstract
'compounding curves' in the house palette (matplotlib), so the full-bleed navy pages
read designed instead of empty, without stock photography."""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_charts")
os.makedirs(OUT, exist_ok=True)
NAVYD, NAVY, NT1, NT2, GOLD = "#10197A", "#1B27A3", "#4A57C4", "#8C95DE", "#F2A93C"


def flow_art(name, w=5.3, h=7.4, seed=11, gold=True, alpha=1.0, transparent=False):
    """Layered rising curves. gold=True adds the single gold 'client journey' line.
    transparent=True renders line-work only (for divider backgrounds)."""
    rng = np.random.default_rng(seed)
    fig = plt.figure(figsize=(w, h), dpi=220)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off")
    ax.set_xlim(0, 1); ax.set_ylim(0, 1)
    if transparent:
        fig.patch.set_alpha(0)
    else:
        fig.patch.set_facecolor(NAVYD)
        ax.set_facecolor(NAVYD)
    x = np.linspace(0, 1, 480)
    n = 26
    for i in range(n):
        base = i / (n - 1)
        amp = 0.035 + 0.05 * rng.random()
        ph = rng.random() * 6.283
        f = 0.8 + 1.5 * rng.random()
        y = 0.05 + 0.90 * base + amp * np.sin(6.283 * (f * x + ph)) * (0.35 + 0.65 * x)
        t = i / (n - 1)
        col = NT2 if t > 0.66 else (NT1 if t > 0.33 else NAVY)
        ax.plot(x, y, color=col, lw=1.1, alpha=(0.14 + 0.30 * t) * alpha)
    if gold:
        yg = 0.10 + 0.72 * x + 0.05 * np.sin(6.283 * (1.15 * x + 0.35)) * (0.3 + 0.7 * x)
        ax.plot(x, yg, color=GOLD, lw=2.2, alpha=0.95 * alpha)
        ax.scatter([0.985], [yg[-4]], s=40, color=GOLD, zorder=5)
    p = os.path.join(OUT, name + ".png")
    fig.savefig(p, transparent=transparent,
                facecolor=(fig.get_facecolor() if not transparent else "none"))
    plt.close(fig)
    return p
