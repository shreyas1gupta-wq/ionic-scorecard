"""Build the 3 WS-4 benchmark charts (firm palette, style_chart_axes, direct labels).
Palette validator (node) unavailable on this machine (known gap) -> every mark is
direct-labeled so identity never depends on color alone (the skill's own fallback
for a marginal CVD pair). Fixed categorical order, reused across charts:
  models:  Sonnet=NAVY, Fable=GOLD, Opus=TEAL, Haiku=RUST
  arms:    A=NAVY, B=GOLD, C=TEAL, C2=RUST
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

sys.path.insert(0, r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\scripts")
from docx_style_kit import FIRM_NAVY, FIRM_GOLD, FIRM_TEAL, FIRM_RUST, FIRM_STONE, FIRM_INK, style_chart_axes, source_caption_mpl

from pathlib import Path
OUT = Path(r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\09_PRODUCT\reports\_img_ws4")
OUT.mkdir(parents=True, exist_ok=True)
AS_OF = "2026-07-15"
N = lambda h: f"#{h}"

MCOLOR = {"Sonnet 5": N(FIRM_NAVY), "Fable 5": N(FIRM_GOLD), "Opus 4.8": N(FIRM_TEAL), "Haiku 4.5": N(FIRM_RUST)}

# ============================================================
# CHART 1 -- cost vs accuracy (the headline finding)
# ============================================================
data = {  # model: (cost_usd_20task, defects_of_16)
    "Sonnet 5": (0.148, 15), "Fable 5": (1.492, 15), "Opus 4.8": (2.110, 14), "Haiku 4.5": (0.025, 9),
}
fig, ax = plt.subplots(figsize=(6.6, 4.0), dpi=200)
# explicit per-model label placement (offset points, ha, va) -- hand-tuned to avoid
# the Opus/Fable collision (their costs are close on a log scale) and the Haiku
# label running off the left edge against the axis
label_pos = {
    "Sonnet 5":  {"xytext": (0, 14),  "ha": "center", "va": "bottom"},
    "Fable 5":   {"xytext": (14, 18), "ha": "left",   "va": "bottom"},
    "Opus 4.8":  {"xytext": (14, -26),"ha": "left",   "va": "top"},
    "Haiku 4.5": {"xytext": (55, 10), "ha": "left",   "va": "bottom"},
}
for m, (cost, defects) in data.items():
    ax.scatter(cost, defects, s=120, color=MCOLOR[m], zorder=3, edgecolor="white", linewidth=1.1)
    p = label_pos[m]
    ax.annotate(f"{m}\n{defects}/16 defects, ${cost:.3f}", (cost, defects), textcoords="offset points",
                xytext=p["xytext"], fontsize=8, color=MCOLOR[m], ha=p["ha"], va=p["va"], linespacing=1.4)
ax.set_xscale("log")
ax.set_xlim(0.012, 4.2)
ax.set_xlabel("Battery cost, 20 tasks, USD (log scale, published per-token pricing)")
ax.set_ylabel("Defects found (of 16)")
ax.set_ylim(7.2, 17.3)
ax.set_title("Cost vs. accuracy on the defect-review battery", fontsize=11, fontweight="bold", loc="left")
ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:g}"))
style_chart_axes(ax)
ax.text(0.012, 17.0, "Sonnet ties the top score at ~1/10 Fable's cost, ~1/15 Opus's",
        fontsize=8.3, color=N(FIRM_STONE), style="italic", ha="left", va="top")
source_caption_mpl(fig, "MODEL_GRID/COST_ESTIMATE.txt, ws4_battery/results/xmodel_grade/BATTERY_RESULT.txt", AS_OF, y=-0.06)
fig.tight_layout()
fig.savefig(OUT / "chart1_cost_vs_accuracy.png", bbox_inches="tight")
plt.close(fig)
print("chart 1 done")

# ============================================================
# CHART 2 -- judge self-preference
# ============================================================
models = ["Sonnet 5", "Fable 5", "Opus 4.8", "Haiku 4.5"]
haiku_judged = [8.25, 9.50, 9.25, 9.08]
opus_judged = [8.30, 9.55, 9.75, 8.08]
fig, ax = plt.subplots(figsize=(6.3, 3.4), dpi=200)
x = range(len(models))
w = 0.34
b1 = ax.bar([i - w / 2 for i in x], haiku_judged, width=w, color=N(FIRM_STONE), label="Judged by Haiku 4.5", zorder=3)
b2 = ax.bar([i + w / 2 for i in x], opus_judged, width=w, color=N(FIRM_NAVY), label="Judged by Opus 4.8 (neutral re-grade)", zorder=3)
for i, (h, o) in enumerate(zip(haiku_judged, opus_judged)):
    ax.text(i - w / 2, h + 0.12, f"{h:.2f}", ha="center", fontsize=7.5, color=N(FIRM_STONE))
    ax.text(i + w / 2, o + 0.12, f"{o:.2f}", ha="center", fontsize=7.5, color=N(FIRM_NAVY))
delta_h, delta_o = opus_judged[3] - haiku_judged[3], opus_judged[2] - haiku_judged[2]
ax.annotate(f"{delta_h:+.2f} (self-preference)", xy=(3 + w / 2, opus_judged[3]), xytext=(2.55, 6.9),
            fontsize=7.8, color=N(FIRM_RUST), arrowprops=dict(arrowstyle="->", color=N(FIRM_RUST), lw=0.9))
ax.annotate(f"{delta_o:+.2f} (self-preference)", xy=(2 + w / 2, opus_judged[2]), xytext=(1.15, 10.6),
            fontsize=7.8, color=N(FIRM_RUST), arrowprops=dict(arrowstyle="->", color=N(FIRM_RUST), lw=0.9))
ax.set_xticks(list(x)); ax.set_xticklabels(models, fontsize=9)
ax.set_ylabel("Open-ended quality score (of 10)")
ax.set_ylim(6.5, 10.6)
ax.set_title("Measured LLM-judge self-preference", fontsize=11, fontweight="bold", loc="left")
style_chart_axes(ax)
ax.legend(frameon=False, fontsize=8, loc="upper left")
source_caption_mpl(fig, "MODEL_GRID/GRID_QUALITY_CORRECTED.txt (leave-one-out correction)", AS_OF, y=-0.05)
fig.tight_layout()
fig.savefig(OUT / "chart2_judge_self_preference.png", bbox_inches="tight")
plt.close(fig)
print("chart 2 done")

# ============================================================
# CHART 3 -- primary study: defects found by arm (A/B/C/C2)
# ============================================================
arms = ["A\n(single, no tools)", "B\n(single, + code)", "C\n(firm pipeline)", "C2\n(pipeline, no personas)"]
ACOLOR = [N(FIRM_NAVY), N(FIRM_GOLD), N(FIRM_TEAL), N(FIRM_RUST)]
defects = [15, 16, 14, 14]
fig, ax = plt.subplots(figsize=(6.3, 3.4), dpi=200)
bars = ax.bar(range(4), defects, color=ACOLOR, width=0.55, zorder=3)
for i, d in enumerate(defects):
    ax.text(i, d + 0.25, f"{d}/16", ha="center", fontsize=9.5, fontweight="bold", color=ACOLOR[i])
ax.axhline(16, color=N(FIRM_STONE), lw=1.1, linestyle=(0, (4, 2)), zorder=2)
ax.text(3.5, 16.15, "single-LLM ceiling (arm B, 16/16)", ha="right", fontsize=7.5, color=N(FIRM_STONE), style="italic")
ax.set_xticks(range(4)); ax.set_xticklabels(arms, fontsize=8.3)
ax.set_ylabel("Defects found (of 16)")
ax.set_ylim(0, 18.5)
ax.set_title("Pre-registered study: multi-agent pipeline vs. single model (Opus 4.8)", fontsize=10.5, fontweight="bold", loc="left")
style_chart_axes(ax)
source_caption_mpl(fig, "ws4_battery/results/opus_arms_grade/OPUS_ARMS_RESULT.txt (blind Haiku-4.5 judge)", AS_OF, y=-0.07)
fig.tight_layout()
fig.savefig(OUT / "chart3_primary_study_arms.png", bbox_inches="tight")
plt.close(fig)
print("chart 3 done")
print("all charts ->", OUT)
