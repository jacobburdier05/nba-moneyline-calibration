"""
Two figures for the conference abstract.

Figure 1 shows the same 6,840 games under every vig-removal rule, so the
only thing that changes from row to row is the rule. Figure 2 compares the
power of this test with the power of a typical 74-game bucket.

Nothing here is computed fresh. Both figures read numbers the pipeline
already wrote to results/, so they can't drift from the paper.

Run after equivalence_and_fixed_sample.py and primary_analysis.py.
Writes figures/abstract_fig1_rules.(png|pdf) and
figures/abstract_fig2_power.(png|pdf) at 300 dpi.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(exist_ok=True)

# Palette: validated with the dataviz six-check script (light mode, all pass).
BLUE = "#2a78d6"     # the rule fixed in advance / this test
ORANGE = "#eb6834"   # no vig removed / the 74-game bucket
GRAY = "#8d8c87"     # the other rules
INK = "#0b0b0b"
INK2 = "#52514e"
RULE = "#d9d8d4"     # zero line and reference lines
SURFACE = "#ffffff"

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "text.color": INK,
    "axes.labelcolor": INK2,
    "axes.edgecolor": RULE,
    "xtick.color": INK2,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})

Z = norm.ppf(0.975)


def fmt_p(p):
    return "p < .001" if p < 0.001 else f"p = {p:.3f}".replace("0.", ".")


# Figure 1: one sample, every rule
fx = json.load(open(RES / "equivalence_fixed_sample.json"))["fixed_sample_normalization"]
by = {r["rule"]: r for r in fx}
rows = [
    ("Proportional (set in advance)", by["Proportional (primary)"], BLUE),
    ("Equal margin  =  Shin (1993)", by["Additive, equal margin"], GRAY),
    ("Constant odds ratio", by["Constant odds ratio"], GRAY),
    ("Power", by["Power"], GRAY),
    ("No vig removed (raw prices)", by["None, raw probabilities"], ORANGE),
]
# Shin and equal margin must agree exactly for a two-outcome book.
assert abs(by["Shin (1993)"]["gap_pp"] - by["Additive, equal margin"]["gap_pp"]) < 1e-9
n = by["Proportional (primary)"]["n"]

fig, ax = plt.subplots(figsize=(6.5, 2.9))
ys = np.arange(len(rows))[::-1]
for y, (label, r, col) in zip(ys, rows):
    g, se = r["gap_pp"], r["se_pp"]
    lo, hi = g - Z * se, g + Z * se
    ax.plot([lo, hi], [y, y], color=col, lw=2, solid_capstyle="round", zorder=2)
    ax.plot(g, y, "o", ms=8, color=col, mec=SURFACE, mew=2, zorder=3)
    tr = ax.get_yaxis_transform()
    ax.text(1.10, y, f"{g:+.2f}", transform=tr, va="center", ha="right", fontsize=9,
            color=INK, fontweight="bold" if col == BLUE else "normal")
    ax.text(1.13, y, fmt_p(r["p_value"]), transform=tr, va="center", ha="left", fontsize=9, color=INK2)
ax.axvline(0, color=INK2, lw=1, zorder=1)
ax.set_yticks(ys)
ax.set_yticklabels([r[0] for r in rows])
ax.tick_params(axis="y", length=0)
ax.set_xlim(-3.6, 2.1)
ax.set_xticks([-3, -2, -1, 0, 1, 2])
ax.set_xticklabels(["-3", "-2", "-1", "0", "+1", "+2"])
ax.set_xlabel("Calibration gap, percentage points (dot = estimate, line = 95 percent CI)")
ax.grid(axis="x", color=RULE, lw=0.6, zorder=0)
ax.spines["left"].set_visible(False)
trh = ax.get_yaxis_transform()
ax.text(1.10, len(rows) - 0.45, "Gap", transform=trh, ha="right", fontsize=8, color=INK2)
ax.text(1.13, len(rows) - 0.45, "Two-sided", transform=trh, ha="left", fontsize=8, color=INK2)
ax.set_ylim(-0.6, len(rows) - 0.2)
fig.subplots_adjust(left=0.33, right=0.80, top=0.80, bottom=0.18)
fig.text(0.015, 0.955, f"Same {n:,} games. Change only the vig rule and the sign flips.",
         ha="left", va="top", fontsize=10.5, fontweight="bold")
fig.text(0.015, 0.885, "Favorites above .70 vig-free probability, NBA regular season, 2007-08 to March 2020",
         ha="left", va="top", fontsize=8.5, color=INK2)
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"abstract_fig1_rules.{ext}", dpi=300)
plt.close(fig)

# Figure 2: power, this test versus a 74-game bucket
prim = json.load(open(RES / "primary_results.json"))
pw = json.load(open(RES / "power_analysis.json"))
se_main = pw["se_pp"]
ill = prim["design"]["illustrative_power"]
n74, p74 = ill["n"], ill["assumed_probability"]
se_74 = np.sqrt(p74 * (1 - p74) / n74) * 100
be = prim["design"]["breakeven_pp_primary"]
mde = pw["mde_pp"]


def power(d, se):
    return norm.cdf(-Z - d / se) + 1 - norm.cdf(Z - d / se)


# Both curves must reproduce the numbers quoted in the paper.
assert abs(power(be, se_74) * 100 - ill["power_pct"]) < 1e-6
assert abs(power(mde, se_main) - 0.80) < 1e-6

d = np.linspace(0, 4, 401)
fig, ax = plt.subplots(figsize=(6.5, 2.9))
ax.axhline(80, color=RULE, lw=1, zorder=1)
ax.plot([be, be], [0, 100], color=INK2, lw=1, zorder=1)
ax.plot(d, power(d, se_main) * 100, color=BLUE, lw=2, label=f"This test ({prim['primary']['n']:,} games)", zorder=3)
ax.plot(d, power(d, se_74) * 100, color=ORANGE, lw=2, label=f"A {n74}-game bucket near .{int(p74*100)}", zorder=3)
ax.plot(be, power(be, se_74) * 100, "o", ms=8, color=ORANGE, mec=SURFACE, mew=2, zorder=4)
ax.plot(be, power(be, se_main) * 100, "o", ms=8, color=BLUE, mec=SURFACE, mew=2, zorder=4)
ax.plot(mde, 80, "o", ms=8, color=BLUE, mec=SURFACE, mew=2, zorder=4)
ax.annotate(f"{power(be, se_74)*100:.0f} percent", (be, power(be, se_74) * 100),
            xytext=(8, 8), textcoords="offset points", fontsize=9, color=INK, va="bottom")
ax.annotate("over 99.9 percent", (be, power(be, se_main) * 100),
            xytext=(8, -10), textcoords="offset points", fontsize=9, color=INK)
ax.annotate(f"80 percent at {mde:.2f} points", (mde, 80),
            xytext=(8, -12), textcoords="offset points", fontsize=9, color=INK)
ax.text(be - 0.04, 50, "A bettor's break-even\nabout 3 points", ha="right", va="center",
        fontsize=8.5, color=INK2)
ax.set_xlim(0, 4)
ax.set_ylim(0, 105)
ax.set_yticks([0, 20, 40, 60, 80, 100])
ax.set_xlabel("True gap between win rate and price, percentage points")
ax.set_ylabel("Power (percent)")
ax.grid(axis="y", color=RULE, lw=0.6, zorder=0)
ax.text(0.72, 52, "This test", ha="right", va="center", fontsize=9, color=INK)
ax.text(2.0, 10.5, "74-game bucket", ha="center", va="bottom", fontsize=9, color=INK)
fig.legend(loc="upper right", bbox_to_anchor=(0.985, 0.905), ncol=2, frameon=False,
           fontsize=8.5, handlelength=1.6, columnspacing=1.2)
fig.subplots_adjust(left=0.11, right=0.97, top=0.80, bottom=0.18)
fig.text(0.015, 0.955, "Same question, very different chances of seeing an answer.",
         ha="left", va="top", fontsize=10.5, fontweight="bold")
fig.text(0.015, 0.885, "Power of a two-sided test at alpha = .05",
         ha="left", va="top", fontsize=8.5, color=INK2)
for ext in ("png", "pdf"):
    fig.savefig(FIG / f"abstract_fig2_power.{ext}", dpi=300)
plt.close(fig)

print("wrote figures/abstract_fig1_rules.(png|pdf) and figures/abstract_fig2_power.(png|pdf)")
