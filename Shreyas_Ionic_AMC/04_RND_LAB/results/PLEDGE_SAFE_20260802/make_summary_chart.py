import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = r"c:\Users\Shreyas.1Gupta\OneDrive - Angel Broking Limited\Desktop\Backup\NIFTY 500\Shreyas_Ionic_AMC\04_RND_LAB\results\PLEDGE_SAFE_20260802"

calm = pd.read_csv(f"{ROOT}/panel_real_mf.csv", parse_dates=["date"]).set_index("date")
calm_h = pd.read_csv(f"{ROOT}/panel_yield_plus_hedge.csv", parse_dates=["date"]).set_index("date")
covid = pd.read_csv(f"{ROOT}/panel_covid_YIELD_ONLY_corrected.csv", parse_dates=["date"]).set_index("date")
covid_h = pd.read_csv(f"{ROOT}/panel_covid_YIELD_PLUS_HEDGE_corrected.csv", parse_dates=["date"]).set_index("date")

INK, BLUE, GREEN, GRID, MUTED, SURF = "#0b0b0b", "#2a78d6", "#15803d", "#e1e0d9", "#898781", "#fcfcfb"


def dd(s):
    return (s - s.cummax()) / s.cummax() * 100


def style(ax, title):
    ax.set_facecolor(SURF)
    ax.set_title(title, fontsize=10.5, color=INK, loc="left", fontweight="bold")
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.tick_params(colors=MUTED, labelsize=8)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.legend(fontsize=8, frameon=False)


fig, axes = plt.subplots(2, 2, figsize=(13, 8), dpi=150)
fig.patch.set_facecolor(SURF)

ax = axes[0, 0]
base = calm["bond"] + calm["mf"]
ax.plot(base.index, base / 1e5, color=MUTED, lw=1.6, label="Bond+MF only (no options)")
ax.plot(calm.index, calm["total"] / 1e5, color=BLUE, lw=1.8, label="+ S1-F yield overlay")
ax.plot(calm_h.index, calm_h["total"] / 1e5, color=GREEN, lw=1.8, label="+ yield & 50% protective put")
style(ax, "Calm period 2021-2026: equity (Rs lakh)")

ax = axes[0, 1]
ax.fill_between(base.index, dd(base), 0, color=MUTED, alpha=0.25, lw=0)
ax.plot(base.index, dd(base), color=MUTED, lw=1.2, label=f"Bond+MF only ({dd(base).min():.1f}%)")
ax.plot(calm.index, dd(calm["total"]), color=BLUE, lw=1.4, label=f"+ yield ({dd(calm['total']).min():.1f}%)")
ax.plot(calm_h.index, dd(calm_h["total"]), color=GREEN, lw=1.4,
        label=f"+ yield & hedge ({dd(calm_h['total']).min():.1f}%)")
style(ax, "Calm period drawdown (%)")

ax = axes[1, 0]
base_c = covid["bond"] + covid["mf"]
ax.plot(base_c.index, base_c / 1e5, color=MUTED, lw=1.6, label="Bond+MF only (no options)")
ax.plot(covid.index, covid["total"] / 1e5, color=BLUE, lw=1.8, label="+ S1-F yield overlay (stress-IV)")
ax.plot(covid_h.index, covid_h["total"] / 1e5, color=GREEN, lw=1.8, label="+ yield & 50% protective put")
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.08)
style(ax, "COVID-era rerun (2020-01..2021-05): equity (Rs lakh)")

ax = axes[1, 1]
ax.fill_between(base_c.index, dd(base_c), 0, color=MUTED, alpha=0.25, lw=0)
ax.plot(base_c.index, dd(base_c), color=MUTED, lw=1.2, label=f"Bond+MF only ({dd(base_c).min():.1f}%)")
ax.plot(covid.index, dd(covid["total"]), color=BLUE, lw=1.4, label=f"+ yield ({dd(covid['total']).min():.1f}%)")
ax.plot(covid_h.index, dd(covid_h["total"]), color=GREEN, lw=1.4,
        label=f"+ yield & hedge ({dd(covid_h['total']).min():.1f}%)")
ax.axvspan(pd.Timestamp("2020-02-19"), pd.Timestamp("2020-04-10"), color="red", alpha=0.08)
style(ax, "COVID-era drawdown (%) [red = actual crash window]")

fig.suptitle("Rs 50L G-sec + Rs 50L equity MF, pledged: yield overlay alone vs. yield + partial hedge",
             fontsize=12, fontweight="bold", color=INK)
fig.tight_layout()
out = f"{ROOT}/SUMMARY_CHART.png"
fig.savefig(out, facecolor=SURF, bbox_inches="tight")
print("saved:", out)
