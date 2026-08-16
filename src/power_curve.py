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

That MDE formula is the conventional two-sided normal approximation, not an
exact inversion of the Poisson-binomial power function. The two are not
guaranteed to agree, so this script computes the exact version as well: it
builds the exact Poisson-binomial distribution by DFT of the characteristic
function, finds the exact two-sided critical region under the null, and
inverts exact power for the 80 percent MDE. The paper reports both.

None of the marks on the figure comes from outside this dataset. An earlier
draft marked "1.7" and "5.1" as the smallest and largest effects claimed in
prior work. Those two numbers could not be traced to any cited source: of
the eight papers cited, six report rates of return or point-spread cover
rates rather than win-probability calibration gaps, and the one literature
review in the citation set (Newall & Cortis 2021) reports no effect
magnitudes at all. They were removed rather than re-sourced.

Run:  python src/power_curve.py
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize, stats

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


def poisson_binomial_pmf(probs, chunk=400):
    """Exact Poisson-binomial pmf via DFT of the characteristic function.

    Uses the conjugate symmetry of the characteristic function so only half
    the frequencies are evaluated, and chunks the outer product so memory
    stays bounded at n in the thousands.
    """
    m = len(probs)
    N = m + 1
    l = np.arange(N // 2 + 1)
    z = np.exp(2j * np.pi * l / N)
    half = np.zeros(len(l), dtype=complex)
    for s0 in range(0, len(l), chunk):
        e0 = min(s0 + chunk, len(l))
        half[s0:e0] = np.log(1 - probs + np.outer(z[s0:e0], probs)).sum(axis=1)
    half = np.exp(half)
    cf = np.empty(N, dtype=complex)
    cf[:len(l)] = half
    tail = np.conj(half[1:][::-1])
    cf[N - len(l) + 1:] = tail[:N - len(l)]
    return np.clip(np.real(np.fft.fft(cf)) / N, 0.0, None)


def exact_critical_region(probs, alpha=ALPHA):
    """Two-sided exact rejection region for the count of favorite wins."""
    pmf = poisson_binomial_pmf(probs)
    cdf = np.cumsum(pmf)
    k = np.arange(len(pmf))
    lo = int(k[np.searchsorted(cdf, alpha / 2.0)])
    hi = int(k[np.searchsorted(cdf, 1.0 - alpha / 2.0)])
    size = float(cdf[lo - 1] + (1.0 - cdf[hi]))
    return lo, hi, size


def exact_power_at(delta_pp, probs, lo, hi):
    """Exact power against a uniform shift of delta_pp in every game."""
    q = np.clip(probs + delta_pp / 100.0, 1e-12, 1.0 - 1e-12)
    cdf = np.cumsum(poisson_binomial_pmf(q))
    return float(cdf[lo - 1] + (1.0 - cdf[hi]))


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

    # Every mark is computed from this sample. Offsets are set by hand
    # because the marks sit close together on the shoulder of the curve.
    marks = [
        (observed, f"observed gap {observed:+.2f}", MUTED, (9, -2), "left", "top"),
        (mde, f"MDE {mde:.2f}", ACCENT, (-8, -4), "right", "top"),
        (breakeven, f"break-even {breakeven:.2f}", FLAG, (0, -13), "center", "top"),
    ]

    # exact Poisson-binomial inversion, to check the normal approximation
    lo, hi, exact_size = exact_critical_region(p)
    mde_exact = float(optimize.brentq(
        lambda d: exact_power_at(d, p, lo, hi) - TARGET_POWER, 0.5, 3.0,
        xtol=1e-4))

    table = {
        "primary_n": int(len(p)),
        "mde_pp_exact_poisson_binomial": mde_exact,
        "mde_approximation_error_pp": abs(mde_exact - float(mde)),
        "exact_critical_region": {"reject_at_or_below": lo - 1,
                                  "reject_at_or_above": hi + 1,
                                  "exact_size": exact_size},
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
        # power approaches but never equals 1, so anything that rounds to
        # 100 is labeled as a bound rather than as an exact value
        shown = ">99.9%" if y > 99.9 else f"{y:.0f}%"
        ax.annotate(f"{label}\n{shown}", xy=(x, y), xytext=offset,
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
             f"All three marks are computed from this sample. The 80% MDE "
             f"shown is the normal approximation, {mde:.4f} pp; the exact "
             f"Poisson-binomial inversion gives {mde_exact:.4f} pp.",
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
    print(f"  MDE, normal approx       {mde:.4f} pp")
    print(f"  MDE, exact Poisson-binom {mde_exact:.4f} pp  "
          f"(difference {abs(mde_exact - mde):.4f} pp)")
    print(f"  exact critical region    reject if wins <= {lo - 1} or >= {hi + 1}, "
          f"size {exact_size:.5f}")
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
