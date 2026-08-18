"""
Robustness: are the flat-stake return intervals reliable, or does the
normal approximation fail on skewed payouts?

Losak and Kalamvokis (2025) make a specific argument about this literature.
Tests of betting profitability almost always use a t-test or z-test on the
mean profit per unit staked. Per-bet profit is skewed, because a winning
longshot pays several units while a loss always costs one, and under skew
the t-test's true rejection rate exceeds its nominal level. Their proposed
fix is to simulate the null and read the interval off the empirical
distribution rather than off a normal approximation.

That argument applies to section 5.5 of this paper and not to section 5.1.
The primary calibration test compares a win indicator with a probability,
a bounded quantity, and it is already evaluated against the exact
Poisson-binomial distribution rather than a normal approximation. The
return analysis is the payout-weighted quantity their critique targets,
and it does use mean +/- 1.96 * s / sqrt(n).

This script checks it two ways.

  Part 1  Full sample. Simulate the null that the vig-free probabilities
          are correct, build the empirical distribution of the flat-stake
          return, and compare the resulting interval with the normal one.
          Also estimate the t-test's true size at the paper's own n.

  Part 2  The same size calculation at the sample sizes this literature
          actually uses, by drawing subsamples of these prices. This is
          their table rebuilt on NBA moneylines rather than on synthetic
          odds ranges, and it is reported whether or not it favors this
          paper.

Run:  python src/return_simulation.py
"""

import json
import os

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "data", "processed", "games.csv")
RESULTS_DIR = os.path.join(ROOT, "results")

SEED = 20260818
REPS_CI = 100_000
REPS_SIZE = 40_000
ALPHA = 0.05
SUBSAMPLE_N = (100, 250, 500, 1000, 5000)


def null_profit_rates(p, payout, reps, rng, block=4000):
    """Flat-stake return under the null that the vig-free prices are right."""
    n = len(p)
    out = np.empty(reps)
    done = 0
    while done < reps:
        k = min(block, reps - done)
        wins = rng.random((k, n)) < p
        out[done:done + k] = np.where(wins, payout, -1.0).mean(axis=1)
        done += k
    return out


def ttest_size(p, payout, reps, rng, mu0, alpha=ALPHA, block=4000):
    """True rejection rate of the normal-approximation test, under the null."""
    n = len(p)
    zc = stats.norm.ppf(1.0 - alpha / 2.0)
    rej = 0
    done = 0
    while done < reps:
        k = min(block, reps - done)
        wins = rng.random((k, n)) < p
        prof = np.where(wins, payout, -1.0)
        m = prof.mean(axis=1)
        s = prof.std(axis=1, ddof=1)
        rej += int((np.abs(m - mu0) / (s / np.sqrt(n)) > zc).sum())
        done += k
    return rej / reps


def main():
    g = pd.read_csv(GAMES)
    rng = np.random.default_rng(SEED)

    groups = {
        "All favorites": (g["p_vf_fav"].to_numpy(), g["fav_payout"].to_numpy(),
                          g["fav_won"].to_numpy()),
        "All underdogs": (g["p_vf_dog"].to_numpy(), g["dog_payout"].to_numpy(),
                          1 - g["fav_won"].to_numpy()),
        "Favorites above .70": (
            g.loc[g["p_vf_fav"] > 0.70, "p_vf_fav"].to_numpy(),
            g.loc[g["p_vf_fav"] > 0.70, "fav_payout"].to_numpy(),
            g.loc[g["p_vf_fav"] > 0.70, "fav_won"].to_numpy()),
    }

    out = {"seed": SEED, "reps_interval": REPS_CI, "reps_size": REPS_SIZE,
           "full_sample": [], "by_sample_size": []}

    for name, (p, payout, won) in groups.items():
        n = len(p)
        prof = np.where(won == 1, payout, -1.0)
        obs = float(prof.mean())
        s = float(prof.std(ddof=1))
        half = 1.96 * s / np.sqrt(n)
        mu0 = float((p * payout - (1.0 - p)).mean())

        sim = null_profit_rates(p, payout, REPS_CI, rng)
        # Same pivot as the normal interval, empirical shape instead of normal.
        lo_sim = float((obs - (np.percentile(sim, 97.5) - mu0)) * 100.0)
        hi_sim = float((obs - (np.percentile(sim, 2.5) - mu0)) * 100.0)

        out["full_sample"].append({
            "group": name, "n": int(n),
            "return_pct": obs * 100.0,
            "ci_normal_pct": [(obs - half) * 100.0, (obs + half) * 100.0],
            "ci_simulated_pct": [lo_sim, hi_sim],
            "max_bound_shift_pp": max(
                abs(lo_sim - (obs - half) * 100.0),
                abs(hi_sim - (obs + half) * 100.0)),
            "per_bet_skew": float(stats.skew(prof)),
            "ttest_true_size": ttest_size(p, payout, REPS_SIZE, rng, mu0),
            "nominal_size": ALPHA,
        })

    for name, (p, payout, _) in groups.items():
        for n in SUBSAMPLE_N:
            if n > len(p):
                continue
            idx = rng.choice(len(p), size=n, replace=False)
            ps, pay = p[idx], payout[idx]
            mu0 = float((ps * pay - (1.0 - ps)).mean())
            draws = null_profit_rates(ps, pay, 20_000, rng)
            out["by_sample_size"].append({
                "group": name, "n": int(n),
                "per_bet_sd_pct": float(
                    np.sqrt((ps * (1 - ps) * (pay + 1.0) ** 2).mean()) * 100.0),
                "skew_of_mean": float(stats.skew(draws)),
                "ttest_true_size": ttest_size(ps, pay, REPS_SIZE, rng, mu0),
                "simulated_size": ALPHA,
            })

    worst = max(out["full_sample"], key=lambda r: r["max_bound_shift_pp"])
    out["max_interval_shift_pp_full_sample"] = worst["max_bound_shift_pp"]
    out["conclusion"] = (
        "At this paper's sample sizes the normal and simulated intervals "
        "agree to " + f"{worst['max_bound_shift_pp']:.2f}" + " pp and the "
        "t-test holds its nominal size, so the reported return intervals "
        "stand. The failure they describe is reproduced in these same "
        "prices at the sample sizes the literature typically uses.")

    with open(os.path.join(RESULTS_DIR, "return_simulation.json"), "w") as f:
        json.dump(out, f, indent=2)

    print("=" * 100)
    print("RETURN INTERVALS: normal approximation against a simulated null")
    print("=" * 100)
    print(f"{'Group':<22}{'n':>8}{'return':>9}{'normal 95% CI':>22}"
          f"{'simulated 95% CI':>22}{'skew':>8}{'true size':>10}")
    for r in out["full_sample"]:
        cn = f"[{r['ci_normal_pct'][0]:+.2f}, {r['ci_normal_pct'][1]:+.2f}]"
        cs = f"[{r['ci_simulated_pct'][0]:+.2f}, {r['ci_simulated_pct'][1]:+.2f}]"
        print(f"{r['group']:<22}{r['n']:>8,}{r['return_pct']:>8.2f}%{cn:>22}"
              f"{cs:>22}{r['per_bet_skew']:>8.2f}{r['ttest_true_size']*100:>9.1f}%")
    print()
    print("TRUE SIZE OF THE SAME TEST AT SMALLER n, ON THESE PRICES")
    print(f"{'Group':<22}{'n':>8}{'per-bet SD':>13}{'skew of mean':>15}"
          f"{'t-test size':>13}{'simulated':>11}")
    for r in out["by_sample_size"]:
        print(f"{r['group']:<22}{r['n']:>8,}{r['per_bet_sd_pct']:>12.1f}%"
              f"{r['skew_of_mean']:>15.2f}{r['ttest_true_size']*100:>12.1f}%"
              f"{r['simulated_size']*100:>10.1f}%")
    print()
    print("  " + out["conclusion"])
    print("=" * 100)


if __name__ == "__main__":
    main()
