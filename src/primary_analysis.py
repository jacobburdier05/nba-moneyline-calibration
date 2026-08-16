"""
Stage 2: the pre-specified confirmatory analysis.

Everything in this file was fixed in preregistration/analysis_plan_frozen.md
before any outcome data were examined.

  Primary test        Poisson-binomial test of calibration for favorites
                      with vig-free implied probability above .70
  Secondary 1         logistic calibration regression, joint Wald test of
                      intercept = 0 and slope = 1
  Secondary 2         five fixed probability buckets, Holm correction
  Secondary 3         flat-stake returns with confidence intervals
  Design              minimum detectable effect at 80 percent power, and
                      the break-even requirement implied by quoted prices
  Caution             the same test run against raw (vig-inclusive)
                      probabilities, to quantify the artefact

Run:  python src/primary_analysis.py
"""

import json
import os

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "data", "processed", "games.csv")
RESULTS_DIR = os.path.join(ROOT, "results")

PRIMARY_THRESHOLD = 0.70
ALPHA = 0.05
POWER = 0.80

BUCKETS = [(0.50, 0.60), (0.60, 0.70), (0.70, 0.75), (0.75, 0.80), (0.80, 1.00)]


def poisson_binomial_test(p, y):
    """Two-sided test that outcomes y are Bernoulli draws with per-game
    probabilities p.

    Under the null the number of successes has a Poisson-binomial
    distribution with mean sum(p) and variance sum(p(1-p)). Because the
    implied probability differs game by game, this replaces the
    fixed-probability bucket test common in the literature.
    """
    p = np.asarray(p, dtype=float)
    y = np.asarray(y, dtype=float)

    observed = y.sum()
    expected = p.sum()
    variance = np.sum(p * (1.0 - p))
    se = np.sqrt(variance)

    z = (observed - expected) / se
    pval = 2.0 * stats.norm.sf(abs(z))

    n = len(p)
    return {
        "n": int(n),
        "observed_wins": int(observed),
        "expected_wins": float(expected),
        "observed_rate_pct": float(observed / n * 100.0),
        "implied_rate_pct": float(expected / n * 100.0),
        "gap_pp": float((observed - expected) / n * 100.0),
        "z": float(z),
        "p_value": float(pval),
        "se_pp": float(se / n * 100.0),
    }


def minimum_detectable_effect(p, alpha=ALPHA, power=POWER):
    """Smallest calibration gap, in percentage points, detectable at the
    given two-sided alpha and power, using the heterogeneous per-game
    null variance.
    """
    p = np.asarray(p, dtype=float)
    n = len(p)
    se_pp = np.sqrt(np.sum(p * (1.0 - p))) / n * 100.0
    z_alpha = stats.norm.ppf(1.0 - alpha / 2.0)
    z_beta = stats.norm.ppf(power)
    return float((z_alpha + z_beta) * se_pp)


def achieved_power(p, effect_pp, alpha=ALPHA):
    """Power to detect a calibration gap of `effect_pp` percentage points."""
    p = np.asarray(p, dtype=float)
    n = len(p)
    se_pp = np.sqrt(np.sum(p * (1.0 - p))) / n * 100.0
    z_alpha = stats.norm.ppf(1.0 - alpha / 2.0)
    lam = effect_pp / se_pp
    return float(stats.norm.sf(z_alpha - lam) + stats.norm.cdf(-z_alpha - lam))


def holm(pvals):
    """Holm step-down adjusted p-values, order preserved."""
    pvals = np.asarray(pvals, dtype=float)
    m = len(pvals)
    order = np.argsort(pvals)
    adjusted = np.empty(m, dtype=float)
    running = 0.0
    for rank, idx in enumerate(order):
        val = (m - rank) * pvals[idx]
        running = max(running, val)
        adjusted[idx] = min(running, 1.0)
    return adjusted


def flat_stake_return(payout, won):
    """Mean profit per unit staked, with a normal-approximation 95 percent
    interval on the mean.
    """
    payout = np.asarray(payout, dtype=float)
    won = np.asarray(won, dtype=float)
    profit = np.where(won == 1, payout, -1.0)
    mean = profit.mean()
    se = profit.std(ddof=1) / np.sqrt(len(profit))
    return {
        "n": int(len(profit)),
        "return_pct": float(mean * 100.0),
        "ci_low_pct": float((mean - 1.96 * se) * 100.0),
        "ci_high_pct": float((mean + 1.96 * se) * 100.0),
    }


def main():
    g = pd.read_csv(GAMES)
    out = {}

    # ------------------------------------------------------------------
    # Design: the economic bar and the minimum detectable effect
    # ------------------------------------------------------------------
    primary = g.loc[g["p_vf_fav"] > PRIMARY_THRESHOLD].copy()
    tail = g.loc[g["p_vf_fav"] > 0.90].copy()

    out["design"] = {
        "primary_threshold": PRIMARY_THRESHOLD,
        "alpha": ALPHA,
        "power": POWER,
        "breakeven_pp_primary": float(primary["breakeven_pp"].mean()),
        "breakeven_pp_primary_p10": float(primary["breakeven_pp"].quantile(0.10)),
        "breakeven_pp_primary_p90": float(primary["breakeven_pp"].quantile(0.90)),
        "breakeven_pp_all_favorites": float(g["breakeven_pp"].mean()),
        "breakeven_pp_tail": float(tail["breakeven_pp"].mean()),
        "mde_pp_primary": minimum_detectable_effect(primary["p_vf_fav"]),
        "mde_pp_tail": minimum_detectable_effect(tail["p_vf_fav"]),
    }

    # The illustrative power figure quoted in the Introduction: a narrow
    # bucket of 74 favorites, the kind of slice these studies routinely
    # report, tested against a deviation the size of THIS sample's own
    # break-even requirement. An earlier draft tested it against 1.7 pp,
    # described as the smallest effect claimed in prior work; that number
    # could not be traced to any cited source and was removed. Anchoring on
    # the break-even margin keeps the comparison inside this dataset and
    # needs no citation. Stated explicitly so it is reproducible: n = 74
    # games at an assumed win probability of .85.
    n_illustrative, p_illustrative = 74, 0.85
    effect_illustrative = out["design"]["breakeven_pp_primary"]
    out["design"]["illustrative_power"] = {
        "n": n_illustrative,
        "assumed_probability": p_illustrative,
        "effect_pp": effect_illustrative,
        "power_pct": achieved_power(np.full(n_illustrative, p_illustrative),
                                    effect_illustrative) * 100.0,
    }

    # ------------------------------------------------------------------
    # Primary confirmatory test
    # ------------------------------------------------------------------
    out["primary"] = poisson_binomial_test(primary["p_vf_fav"],
                                           primary["fav_won"])
    out["primary"]["share_of_sample_pct"] = float(len(primary) / len(g) * 100.0)

    # ------------------------------------------------------------------
    # Secondary 1: logistic calibration regression
    # ------------------------------------------------------------------
    p = g["p_vf_fav"].to_numpy()
    logit_p = np.log(p / (1.0 - p))
    X = sm.add_constant(logit_p)
    model = sm.Logit(g["fav_won"].to_numpy(), X).fit(disp=False)

    intercept, slope = model.params
    ci = np.asarray(model.conf_int())

    # Joint Wald test of perfect calibration: intercept = 0 and slope = 1.
    # W = (theta - theta0)' V^-1 (theta - theta0), chi-squared with 2 df.
    theta = np.array([intercept, slope])
    theta0 = np.array([0.0, 1.0])
    V = np.asarray(model.cov_params())
    diff = theta - theta0
    wald_chi2 = float(diff @ np.linalg.inv(V) @ diff)
    wald_p = float(stats.chi2.sf(wald_chi2, df=2))

    out["calibration_regression"] = {
        "n": int(len(g)),
        "intercept": float(intercept),
        "intercept_ci": [float(ci[0, 0]), float(ci[0, 1])],
        "slope": float(slope),
        "slope_ci": [float(ci[1, 0]), float(ci[1, 1])],
        "joint_wald_chi2": wald_chi2,
        "joint_wald_df": 2,
        "joint_wald_p": wald_p,
    }

    # ------------------------------------------------------------------
    # Secondary 2: pre-specified buckets, Holm corrected
    # ------------------------------------------------------------------
    rows = []
    for lo, hi in BUCKETS:
        sel = g.loc[(g["p_vf_fav"] > lo) & (g["p_vf_fav"] <= hi)]
        r = poisson_binomial_test(sel["p_vf_fav"], sel["fav_won"])
        r["bucket"] = f"({lo:.2f}, {hi:.2f}]"
        rows.append(r)

    adj = holm([r["p_value"] for r in rows])
    for r, a in zip(rows, adj):
        r["holm_p"] = float(a)
    out["buckets"] = rows

    # ------------------------------------------------------------------
    # Secondary 3: flat-stake returns
    # ------------------------------------------------------------------
    out["returns"] = {
        "all_favorites": flat_stake_return(g["fav_payout"], g["fav_won"]),
        "all_underdogs": flat_stake_return(g["dog_payout"], 1 - g["fav_won"]),
        "favorites_above_70": flat_stake_return(primary["fav_payout"],
                                                 primary["fav_won"]),
    }

    bucket_returns = []
    for lo, hi in BUCKETS:
        sel = g.loc[(g["p_vf_fav"] > lo) & (g["p_vf_fav"] <= hi)]
        r = flat_stake_return(sel["fav_payout"], sel["fav_won"])
        r["bucket"] = f"({lo:.2f}, {hi:.2f}]"
        # expected return per unit if prices are exactly calibrated
        r["expected_if_calibrated_pct"] = float(
            ((sel["p_vf_fav"] * sel["fav_payout"]) - (1 - sel["p_vf_fav"])).mean()
            * 100.0)
        bucket_returns.append(r)
    out["returns"]["by_bucket"] = bucket_returns

    # ------------------------------------------------------------------
    # Methodological caution: the same test without removing the vig
    # ------------------------------------------------------------------
    raw_primary = g.loc[g["p_raw_fav"] > PRIMARY_THRESHOLD]
    out["raw_probability_artefact"] = poisson_binomial_test(
        raw_primary["p_raw_fav"], raw_primary["fav_won"])
    out["raw_probability_artefact"]["note"] = (
        "Testing against raw, vig-inclusive implied probabilities. Under "
        "proportional vig removal this gap is the bookmaker margin, not "
        "bettor behavior.")

    # ------------------------------------------------------------------
    with open(os.path.join(RESULTS_DIR, "primary_results.json"), "w") as f:
        json.dump(out, f, indent=2)

    pd.DataFrame(rows)[["bucket", "n", "observed_rate_pct", "implied_rate_pct",
                        "gap_pp", "z", "p_value", "holm_p"]].to_csv(
        os.path.join(RESULTS_DIR, "bucket_results.csv"), index=False)

    # ------------------------------------------------------------------
    d, pr = out["design"], out["primary"]
    print("=" * 68)
    print("DESIGN")
    print(f"  break-even requirement, primary group : {d['breakeven_pp_primary']:.2f} pp "
          f"(p10 {d['breakeven_pp_primary_p10']:.2f}, p90 {d['breakeven_pp_primary_p90']:.2f})")
    print(f"  break-even, all favorites            : {d['breakeven_pp_all_favorites']:.2f} pp")
    print(f"  break-even, tail above .90            : {d['breakeven_pp_tail']:.2f} pp")
    print(f"  minimum detectable effect, primary    : {d['mde_pp_primary']:.2f} pp")
    print(f"  minimum detectable effect, tail       : {d['mde_pp_tail']:.2f} pp")
    ip = d["illustrative_power"]
    print(f"  power, n={ip['n']} at p={ip['assumed_probability']}, vs the "
          f"{ip['effect_pp']:.2f} pp break-even : {ip['power_pct']:.1f}%")
    print()
    print("PRIMARY TEST  (favorites with vig-free probability above .70)")
    print(f"  n                 : {pr['n']} ({pr['share_of_sample_pct']:.1f}% of sample)")
    print(f"  observed wins     : {pr['observed_wins']}")
    print(f"  expected wins     : {pr['expected_wins']:.2f}")
    print(f"  observed rate     : {pr['observed_rate_pct']:.2f}%")
    print(f"  implied rate      : {pr['implied_rate_pct']:.2f}%")
    print(f"  gap               : {pr['gap_pp']:+.2f} pp")
    print(f"  z                 : {pr['z']:.2f}")
    print(f"  p                 : {pr['p_value']:.3f}")
    print()
    cr = out["calibration_regression"]
    print("CALIBRATION REGRESSION")
    print(f"  intercept         : {cr['intercept']:.3f} "
          f"[{cr['intercept_ci'][0]:.3f}, {cr['intercept_ci'][1]:.3f}]")
    print(f"  slope             : {cr['slope']:.3f} "
          f"[{cr['slope_ci'][0]:.3f}, {cr['slope_ci'][1]:.3f}]")
    print(f"  joint Wald chi2   : {cr['joint_wald_chi2']:.2f}, p = {cr['joint_wald_p']:.3f}")
    print()
    print("BUCKETS")
    print(f"  {'bucket':<14}{'n':>6}{'obs':>9}{'implied':>10}{'gap':>8}{'z':>7}{'p':>8}{'holm':>8}")
    for r in rows:
        print(f"  {r['bucket']:<14}{r['n']:>6}{r['observed_rate_pct']:>8.2f}%"
              f"{r['implied_rate_pct']:>9.2f}%{r['gap_pp']:>+8.2f}{r['z']:>7.2f}"
              f"{r['p_value']:>8.3f}{r['holm_p']:>8.3f}")
    print()
    print("RETURNS (flat one-unit stakes at quoted prices)")
    for k in ("all_favorites", "all_underdogs", "favorites_above_70"):
        r = out["returns"][k]
        print(f"  {k:<22}: {r['return_pct']:+.2f}% "
              f"[{r['ci_low_pct']:+.2f}, {r['ci_high_pct']:+.2f}]  n={r['n']}")
    print()
    ra = out["raw_probability_artefact"]
    print("METHODOLOGICAL CAUTION (no vig removal)")
    print(f"  gap {ra['gap_pp']:+.2f} pp, z = {ra['z']:.2f}, p = {ra['p_value']:.2e}")
    print("=" * 68)


if __name__ == "__main__":
    main()
