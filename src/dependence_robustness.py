"""
Robustness: does the conclusion survive plausible dependence structures?

The primary test treats games as independent Bernoulli trials conditional
on their own prices. That is the standard framing for a calibration test,
but it is an assumption, and these observations are not obviously
independent:

  within-game      not an issue. One favorite outcome per game, and the two
                   sides are perfectly collinear by construction, so only
                   one is analyzed.
  within-team      each team appears in roughly 1,000 games. A team whose
                   quality is persistently misjudged by the market would
                   correlate its own residuals across the whole sample.
  within-season    roster rules, pace, officiating and market structure are
                   common within a year.
  temporal         injuries and news propagate across nearby games.
  cross-book       a consensus price aggregates books that share
                   information, so pricing errors need not be idiosyncratic.

None of that changes the point estimate. All of it can change the standard
error, and therefore the p-value. This script re-estimates the same
quantities with variance estimators that allow correlation within clusters,
and reports whether the substantive conclusion moves.

Two estimands:

  1. The primary calibration gap, estimated as the mean of
     d_i = y_i - p_i and tested against zero. Under independence its
     standard error is the Poisson-binomial one used in the primary test.
     Here it is re-estimated with cluster-robust and block-bootstrap
     variance.

  2. The logistic calibration regression, with the joint Wald test of
     intercept 0 and slope 1 recomputed under each variance estimator.

Run:  python src/dependence_robustness.py
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
BOOT_REPS = 10_000
SEED = 20260714


def add_dog_team(g):
    """The archive names the two teams; derive the underdog side."""
    dog = np.where(g["fav_team"].to_numpy() == g["team1"].to_numpy(),
                   g["team2"].to_numpy(), g["team1"].to_numpy())
    g = g.copy()
    g["dog_team"] = dog
    return g


def gap_with_cluster_se(d, groups_list, labels):
    """Mean of d, with standard errors under several clusterings.

    Regressing d on a constant gives the mean as the coefficient, so any
    covariance estimator statsmodels supports becomes a standard error on
    the calibration gap directly comparable to the Poisson-binomial one.
    """
    X = np.ones((len(d), 1))
    base = sm.OLS(d, X)

    out = []
    fit = base.fit()
    out.append(("Independent (classical OLS)", float(fit.params[0]),
                float(fit.bse[0]), int(len(d))))

    for groups, label in zip(groups_list, labels):
        if groups.ndim == 1:
            n_clusters = len(np.unique(groups))
        else:
            n_clusters = min(len(np.unique(groups[:, j]))
                             for j in range(groups.shape[1]))
        f = base.fit(cov_type="cluster",
                     cov_kwds={"groups": groups, "use_correction": True,
                               "df_correction": True})
        out.append((label, float(f.params[0]), float(f.bse[0]), n_clusters))
    return out


def block_bootstrap(df, unit_col, reps=BOOT_REPS, seed=SEED):
    """Resample whole clusters with replacement, recompute the gap."""
    rng = np.random.default_rng(seed)
    units = df[unit_col].unique()
    blocks = {u: df.loc[df[unit_col] == u, ["fav_won", "p_vf_fav"]].to_numpy()
              for u in units}
    k = len(units)

    gaps = np.empty(reps)
    for i in range(reps):
        picked = rng.choice(units, size=k, replace=True)
        wins = expected = n = 0.0
        for u in picked:
            b = blocks[u]
            wins += b[:, 0].sum()
            expected += b[:, 1].sum()
            n += len(b)
        gaps[i] = (wins - expected) / n * 100.0
    return {"clusters": int(k), "reps": reps, "seed": seed,
            "ci_low_pp": float(np.percentile(gaps, 2.5)),
            "ci_high_pp": float(np.percentile(gaps, 97.5)),
            "sd_pp": float(gaps.std(ddof=1))}


def calibration_regression(g, groups_list, labels):
    """Logistic calibration regression under several variance estimators."""
    p = g["p_vf_fav"].to_numpy()
    X = sm.add_constant(np.log(p / (1.0 - p)))
    y = g["fav_won"].to_numpy()
    theta0 = np.array([0.0, 1.0])

    rows = []
    variants = [("Independent (classical)", None, None)]
    variants += [(lab, gr, "cluster") for gr, lab in zip(groups_list, labels)]

    for label, groups, kind in variants:
        model = sm.Logit(y, X)
        if kind is None:
            fit = model.fit(disp=False)
        else:
            fit = model.fit(disp=False, cov_type="cluster",
                            cov_kwds={"groups": groups, "use_correction": True,
                                      "df_correction": True})
        diff = fit.params - theta0
        V = np.asarray(fit.cov_params())
        chi2 = float(diff @ np.linalg.inv(V) @ diff)
        rows.append({
            "variance_estimator": label,
            "intercept": float(fit.params[0]),
            "intercept_se": float(fit.bse[0]),
            "slope": float(fit.params[1]),
            "slope_se": float(fit.bse[1]),
            "joint_wald_chi2": chi2,
            "joint_wald_p": float(stats.chi2.sf(chi2, df=2)),
        })
    return rows


def main():
    g = add_dog_team(pd.read_csv(GAMES))
    primary = g.loc[g["p_vf_fav"] > PRIMARY_THRESHOLD].copy()

    # statsmodels needs integer cluster codes, not strings, and the
    # two-way estimator needs a plain integer matrix.
    code = lambda s: pd.factorize(s)[0]
    season = code(primary["season"])
    fav = code(primary["fav_team"])
    dog = code(primary["dog_team"])
    two_way = np.column_stack([season, fav]).astype(int)

    groups_list = [season, fav, dog, two_way]
    labels = ["Clustered by season", "Clustered by favorite team",
              "Clustered by underdog team", "Two-way: season and favorite team"]

    out = {}

    # ------------------------------------------------------------------
    # 1. the primary gap under each variance estimator
    # ------------------------------------------------------------------
    d = (primary["fav_won"].to_numpy() - primary["p_vf_fav"].to_numpy()) * 100.0
    rows = []
    for label, est, se, k in gap_with_cluster_se(d, groups_list, labels):
        z = est / se
        rows.append({"variance_estimator": label, "gap_pp": est, "se_pp": se,
                     "z": float(z), "p_value": float(2 * stats.norm.sf(abs(z))),
                     "clusters": k,
                     "ci_low_pp": est - 1.96 * se, "ci_high_pp": est + 1.96 * se})

    # the Poisson-binomial standard error, for direct comparison
    pv = primary["p_vf_fav"].to_numpy()
    pb_se = float(np.sqrt(np.sum(pv * (1 - pv))) / len(pv) * 100.0)
    rows.insert(1, {"variance_estimator": "Poisson-binomial (primary test)",
                    "gap_pp": float(d.mean()), "se_pp": pb_se,
                    "z": float(d.mean() / pb_se),
                    "p_value": float(2 * stats.norm.sf(abs(d.mean() / pb_se))),
                    "clusters": len(pv),
                    "ci_low_pp": d.mean() - 1.96 * pb_se,
                    "ci_high_pp": d.mean() + 1.96 * pb_se})
    out["gap_by_variance_estimator"] = rows

    # ------------------------------------------------------------------
    # 2. block bootstraps
    # ------------------------------------------------------------------
    out["bootstrap_season"] = block_bootstrap(primary, "season")
    out["bootstrap_favorite_team"] = block_bootstrap(primary, "fav_team")

    # ------------------------------------------------------------------
    # 3. calibration regression under each variance estimator
    # ------------------------------------------------------------------
    gs, gf, gd = code(g["season"]), code(g["fav_team"]), code(g["dog_team"])
    out["calibration_regression"] = calibration_regression(
        g, [gs, gf, gd, np.column_stack([gs, gf]).astype(int)], labels)

    with open(os.path.join(RESULTS_DIR, "dependence_robustness.json"), "w") as f:
        json.dump(out, f, indent=2)
    pd.DataFrame(rows).to_csv(
        os.path.join(RESULTS_DIR, "dependence_robustness.csv"), index=False)

    # ------------------------------------------------------------------
    print("=" * 92)
    print("DEPENDENCE ROBUSTNESS  (primary group: favorites above .70, n = "
          f"{len(primary):,})")
    print("=" * 92)
    print(f"{'Variance estimator':<38}{'Clusters':>9}{'Gap':>8}{'SE':>7}"
          f"{'z':>7}{'p':>8}{'95% CI':>18}")
    for r in rows:
        ci = f"[{r['ci_low_pp']:+.2f}, {r['ci_high_pp']:+.2f}]"
        print(f"{r['variance_estimator']:<38}{r['clusters']:>9}"
              f"{r['gap_pp']:>+8.2f}{r['se_pp']:>7.2f}{r['z']:>7.2f}"
              f"{r['p_value']:>8.3f}{ci:>18}")
    print()
    print("Block bootstraps on the same gap:")
    for key, name in [("bootstrap_season", "by season"),
                      ("bootstrap_favorite_team", "by favorite team")]:
        b = out[key]
        print(f"  {name:<20} {b['clusters']:>3} clusters   "
              f"95% CI [{b['ci_low_pp']:+.2f}, {b['ci_high_pp']:+.2f}] pp")
    print()
    print("LOGISTIC CALIBRATION REGRESSION  (all 15,351 games)")
    print(f"{'Variance estimator':<38}{'Intercept':>11}{'Slope':>9}"
          f"{'Wald chi2':>11}{'p':>8}")
    for r in out["calibration_regression"]:
        print(f"{r['variance_estimator']:<38}{r['intercept']:>11.3f}"
              f"{r['slope']:>9.3f}{r['joint_wald_chi2']:>11.2f}"
              f"{r['joint_wald_p']:>8.3f}")
    print()
    worst = max(rows, key=lambda r: r["se_pp"])
    print(f"Largest standard error: {worst['variance_estimator']} "
          f"({worst['se_pp']:.2f} pp, p = {worst['p_value']:.3f}).")
    rejects = [r for r in rows if r["p_value"] < 0.05]
    print(f"Estimators rejecting calibration at .05: "
          f"{len(rejects)} of {len(rows)}"
          + (" (" + ", ".join(r["variance_estimator"] for r in rejects) + ")"
             if rejects else ""))
    print("=" * 92)


if __name__ == "__main__":
    main()
