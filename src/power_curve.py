"""
Figure 3: the power curve, and a transparent statement of the power math.

The paper's null result only means something if the design could have
detected a deviation worth caring about. That argument currently rests on
two numbers in the text, a 1.33 point minimum detectable effect and a 3.01
point break-even requirement. This script exposes the whole curve behind
them so a reader can check the claim without opening the code.

The math, in full.

Let p_i be the vig-free implied probability of game i in the primary group,
n the number of games, and delta the true calibration gap in percentage
points. Under the null the number of favorite wins is Poisson-binomial, so
the gap estimator d = (sum y_i - sum p_i) / n has standard error

    SE = sqrt( sum_i p_i (1 - p_i) ) / n

expressed in percentage points by multiplying by 100. For a two-sided test
at level alpha, power against a true gap delta is

    power(delta) = Phi( -z_{1-alpha/2} - delta/SE )
                 + 1 - Phi(  z_{1-alpha/2} - delta/SE )

and the minimum detectable effect at target power 1-beta solves
power(MDE) = 1-beta, which for the normal approximation is

    MDE = ( z_{1-alpha/2} + z_{1-beta} ) * SE

The variance is the heterogeneous per-game one, not a single pooled
p(1-p), so the curve reflects the actual price distribution in the sample.

Run:  python src/power_curve.py
"""

import json
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
RESULTS_DIR = os.path.join(ROOT, "results")

PRIMARY_THRESHOLD = 0.70
ALPHA = 0.05
TARGET_POWER = 0.80

INK = "#1a1a1a"
ACCENT = "#1f4e79"
MUTED = "#8a8a8a"
FLAG = "#c0392b"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": INK, "axes.labelcolor": INK, "text.color": INK,
    "xtick.color": INK, "ytick.color": INK,
    "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 300,
})


def se_pp(p):
    p = np.asarray(p, dtype=float)
    return float(np.sqrt(np.sum(p * (1.0 - p))) / len(p) * 100.0)


def power_at(delta_pp, se, alpha=ALPHA):
    z = stats.norm.ppf(1.0 - alpha / 2.0)
    lam = np.asarray(delta_pp, dtype=float) / se
    return stats.norm.sf(z - lam) + stats.norm.cdf(-z - lam)


def main():
    g = pd.read_csv(GAMES)
    primary = g.loc[g["p_vf_fav"] > PRIMARY_THRESHOLD]
    p = primary["p_vf_fav"].to_numpy()

    se = se_pp(p)
    z_a = stats.norm.ppf(1.0 - ALPHA / 2.0)
    z_b = stats.norm.ppf(TARGET_POWER)
    mde = (z_a + z_b) * se
    breakeven = float(primary["breakeven_pp"].mean())
    observed = float((primary["fav_won"].to_numpy() - p).mean() * 100.0)

    # (x, label, colour, text offset in points, ha, va) -- offsets are set
    # by hand because the marks sit close together on the shoulder of the
    # curve and automatic placement overlaps them
    marks = [
        (mde, f"MDE {mde:.2f}", ACCENT, (-7, -6), "right", "top"),
        (1.7, "1.7 smallest claimed", MUTED, (9, 2), "left", "center"),
        (breakeven, f"break-even {breakeven:.2f}", FLAG, (0, -13), "center", "top"),
        (5.1, "5.1 largest claimed", MUTED, (0, -13), "center", "top"),
    ]

    table = {
        "primary_n": int(len(p)),
        "alpha": ALPHA,
        "target_power": TARGET_POWER,
        "null_model": "Poisson-binomial, heterogeneous per-game variance",
        "se_pp": se,
        "z_alpha": float(z_a),
        "z_beta": float(z_b),
        "mde_pp": float(mde),
        "breakeven_pp": breakeven,
        "observed_gap_pp": observed,
        "power_at": {f"{d:.2f}": float(power_at(d, se))
                     for d in [0.5, 1.0, mde, 1.7, 2.0, 3.0, breakeven,
                               4.0, 5.0, 5.1, 6.0]},
    }
    with open(os.path.join(RESULTS_DIR, "power_analysis.json"), "w") as f:
        json.dump(table, f, indent=2)

    # ------------------------------------------------------------------
    xs = np.linspace(0, 6, 601)
    ys = power_at(xs, se) * 100.0

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.axhline(80, color=MUTED, linestyle=(0, (4, 3)), linewidth=1, zorder=1)
    ax.text(0.06, 81.5, "80% power", ha="left", va="bottom",
            fontsize=7.5, color=MUTED)

    ax.plot(xs, ys, color=ACCENT, linewidth=1.8, zorder=3)

    for x, label, colour, offset, ha, va in marks:
        ax.axvline(x, color=colour, linewidth=0.9,
                   linestyle=(0, (2, 2)), zorder=2, alpha=0.85)
        y = power_at(x, se) * 100.0
        ax.plot([x], [y], "o", color=colour, markersize=4.5,
                markeredgecolor="white", markeredgewidth=0.6, zorder=4)
        ax.annotate(f"{label}\n{y:.0f}%", xy=(x, y), xytext=offset,
                    textcoords="offset points", fontsize=7, color=colour,
                    va=va, ha=ha)

    ax.set_xlim(0, 6)
    ax.set_ylim(0, 104)
    ax.set_xlabel("True calibration gap (percentage points)")
    ax.set_ylabel("Power to detect it (%)")
    ax.set_title("Figure 3. Power of the primary test against a true gap",
                 loc="left", fontsize=10, pad=10)
    ax.grid(axis="y", color="#e8e8e8", linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    fig.text(0.0, -0.05,
             f"Two-sided test at alpha = {ALPHA}, n = {len(p):,} favorites "
             f"above .70 vig-free implied probability. Standard error "
             f"{se:.3f} pp from the heterogeneous per-game null variance. "
             f"Observed gap {observed:+.2f} pp.",
             fontsize=6.5, color=MUTED, ha="left", wrap=True)

    os.makedirs(FIG_DIR, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(FIG_DIR, f"figure3_power.{ext}"),
                    bbox_inches="tight", dpi=300)
    plt.close(fig)

    # ------------------------------------------------------------------
    print("=" * 68)
    print("POWER ANALYSIS  (primary group)")
    print("=" * 68)
    print(f"  n                        {len(p):,}")
    print(f"  alpha                    {ALPHA}")
    print(f"  target power             {TARGET_POWER}")
    print(f"  null model               Poisson-binomial, per-game variance")
    print(f"  standard error           {se:.4f} pp")
    print(f"  z_alpha, z_beta          {z_a:.4f}, {z_b:.4f}")
    print(f"  MDE = (z_a + z_b) * SE   {mde:.4f} pp")
    print(f"  break-even requirement   {breakeven:.4f} pp")
    print(f"  observed gap             {observed:+.4f} pp")
    print()
    print("  Power against a true gap of:")
    for d in [1.0, mde, 1.7, 2.0, 3.0, breakeven, 4.0, 5.0, 5.1]:
        print(f"    {d:>5.2f} pp   {power_at(d, se) * 100:>6.1f}%")
    print()
    print("  wrote figures/figure3_power.png and .pdf")
    print("=" * 68)


if __name__ == "__main__":
    main()
