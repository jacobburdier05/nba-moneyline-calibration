"""
Stage 4: publication figures.

  Figure 1  Observed favorite win rates by decile of vig-free implied
            probability, with 95 percent intervals, against the line of
            perfect calibration.
  Figure 2  Flat-stake returns per unit bet on favorites, by implied
            probability bucket, against the expected return if prices are
            calibrated.

Both are written to figures/ at 300 dpi in PNG and PDF.

Run:  python src/figures.py
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "data", "processed", "games.csv")
FIG_DIR = os.path.join(ROOT, "figures")

BUCKETS = [(0.50, 0.60), (0.60, 0.70), (0.70, 0.75), (0.75, 0.80), (0.80, 1.00)]

INK = "#1a1a1a"
ACCENT = "#1f4e79"
MUTED = "#8a8a8a"
SOURCE = ("Source: consensus NBA moneylines, 2007-08 to 2019-20, "
          "15,351 regular season games. Vig removed proportionally.")

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 9,
    "axes.edgecolor": INK,
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": INK,
    "ytick.color": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 300,
})


def wilson(successes, n, z=1.96):
    """Wilson score interval, well behaved at rates near 0 and 1."""
    if n == 0:
        return (np.nan, np.nan)
    phat = successes / n
    denom = 1 + z ** 2 / n
    centre = (phat + z ** 2 / (2 * n)) / denom
    half = z * np.sqrt(phat * (1 - phat) / n + z ** 2 / (4 * n ** 2)) / denom
    return (centre - half, centre + half)


def save(fig, name):
    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"{name}.{ext}"),
                    bbox_inches="tight", dpi=300)
    plt.close(fig)
    print(f"  wrote figures/{name}.png and .pdf")


def figure1_calibration(g):
    """Decile calibration plot."""
    g = g.copy()
    g["decile"] = pd.qcut(g["p_vf_fav"], 10, labels=False, duplicates="drop")

    xs, ys, los, his, ns = [], [], [], [], []
    for d, block in g.groupby("decile"):
        n = len(block)
        wins = block["fav_won"].sum()
        lo, hi = wilson(wins, n)
        xs.append(block["p_vf_fav"].mean() * 100)
        ys.append(wins / n * 100)
        los.append(lo * 100)
        his.append(hi * 100)
        ns.append(n)

    xs, ys = np.array(xs), np.array(ys)
    yerr = np.vstack([ys - np.array(los), np.array(his) - ys])

    fig, ax = plt.subplots(figsize=(5.4, 4.6))
    lim = [48, 100]
    ax.plot(lim, lim, linestyle=(0, (4, 3)), color=MUTED, linewidth=1,
            zorder=1, label="Perfect calibration")
    ax.errorbar(xs, ys, yerr=yerr, fmt="o", color=ACCENT, markersize=5,
                capsize=2.5, elinewidth=1, markeredgecolor="white",
                markeredgewidth=0.6, zorder=3,
                label="Observed win rate, 95% CI")

    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_aspect("equal")
    ax.set_xlabel("Vig-free implied probability (%)")
    ax.set_ylabel("Observed favorite win rate (%)")
    ax.set_title("Figure 1. Calibration by decile of implied probability",
                 loc="left", fontsize=10, pad=10)
    ax.legend(frameon=False, loc="upper left", fontsize=8)
    ax.grid(axis="both", color="#e8e8e8", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    fig.text(0.0, -0.04, SOURCE + f"  Deciles of {len(g):,} games, "
             f"{min(ns):,} to {max(ns):,} games each.",
             fontsize=6.5, color=MUTED, ha="left")
    save(fig, "figure1_calibration")


def figure2_returns(g):
    """Flat-stake returns by bucket against the calibrated expectation."""
    labels, observed, lo, hi, expected = [], [], [], [], []

    for a, b in BUCKETS:
        sel = g.loc[(g["p_vf_fav"] > a) & (g["p_vf_fav"] <= b)]
        profit = np.where(sel["fav_won"] == 1, sel["fav_payout"], -1.0)
        mean = profit.mean() * 100
        se = profit.std(ddof=1) / np.sqrt(len(profit)) * 100
        exp = ((sel["p_vf_fav"] * sel["fav_payout"])
               - (1 - sel["p_vf_fav"])).mean() * 100

        labels.append(f"{a:.2f}–{b:.2f}")
        observed.append(mean)
        lo.append(mean - 1.96 * se)
        hi.append(mean + 1.96 * se)
        expected.append(exp)

    x = np.arange(len(labels))
    observed = np.array(observed)
    yerr = np.vstack([observed - np.array(lo), np.array(hi) - observed])

    fig, ax = plt.subplots(figsize=(6.0, 4.0))
    ax.axhline(0, color=INK, linewidth=0.8, zorder=2)
    ax.errorbar(x, observed, yerr=yerr, fmt="o", color=ACCENT, markersize=6,
                capsize=3, elinewidth=1, markeredgecolor="white",
                markeredgewidth=0.6, zorder=4,
                label="Observed return, 95% CI")
    ax.scatter(x, expected, marker="_", s=340, color="#c0392b", linewidth=1.8,
               zorder=3, label="Expected return if calibrated")

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_xlabel("Vig-free implied probability of the favorite")
    ax.set_ylabel("Return per unit staked (%)")
    ax.set_title("Figure 2. Flat-stake returns on favorites, by price",
                 loc="left", fontsize=10, pad=10)
    ax.legend(frameon=False, loc="lower left", fontsize=8)
    ax.grid(axis="y", color="#e8e8e8", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    fig.text(0.0, -0.06,
             SOURCE + "  Flat one-unit stakes at the quoted price.",
             fontsize=6.5, color=MUTED, ha="left")
    save(fig, "figure2_returns")


def main():
    g = pd.read_csv(GAMES)
    print("Building figures")
    figure1_calibration(g)
    figure2_returns(g)


if __name__ == "__main__":
    main()
