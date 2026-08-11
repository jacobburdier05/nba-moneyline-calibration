"""
Stage 3: robustness analyses.

These were added at review and are labeled exploratory in the paper. They
were not part of the frozen confirmatory plan.

  * season-by-season calibration gaps, with a Cochran Q heterogeneity test
  * the extreme tail above .90 vig-free implied probability
  * a season-blocked bootstrap of the primary contrast

Run:  python src/robustness.py
"""

import json
import os

import numpy as np
import pandas as pd
from scipy import stats

from primary_analysis import poisson_binomial_test, minimum_detectable_effect

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "data", "processed", "games.csv")
RESULTS_DIR = os.path.join(ROOT, "results")

PRIMARY_THRESHOLD = 0.70
TAIL_THRESHOLD = 0.90
BOOTSTRAP_REPS = 10_000
BOOTSTRAP_SEED = 20260714


def season_blocked_bootstrap(primary, reps=BOOTSTRAP_REPS, seed=BOOTSTRAP_SEED):
    """Resample whole seasons with replacement and recompute the gap.

    Blocking on season is a partial relaxation of the independence
    assumption in the primary test. With only 13 season clusters this is a
    supplementary check, not a precise bound, and the paper says so.
    """
    rng = np.random.default_rng(seed)
    seasons = primary["season"].unique()
    blocks = {s: primary.loc[primary["season"] == s] for s in seasons}
    k = len(seasons)

    gaps = np.empty(reps, dtype=float)
    for i in range(reps):
        picked = rng.choice(seasons, size=k, replace=True)
        wins = 0.0
        expected = 0.0
        n = 0
        for s in picked:
            b = blocks[s]
            wins += b["fav_won"].sum()
            expected += b["p_vf_fav"].sum()
            n += len(b)
        gaps[i] = (wins - expected) / n * 100.0

    return {
        "reps": reps,
        "seed": seed,
        "clusters": int(k),
        "ci_low_pp": float(np.percentile(gaps, 2.5)),
        "ci_high_pp": float(np.percentile(gaps, 97.5)),
        "mean_pp": float(gaps.mean()),
        "sd_pp": float(gaps.std(ddof=1)),
    }


def main():
    g = pd.read_csv(GAMES)
    primary = g.loc[g["p_vf_fav"] > PRIMARY_THRESHOLD].copy()
    out = {}

    # ------------------------------------------------------------------
    # Season-by-season, with a Cochran Q heterogeneity test
    # ------------------------------------------------------------------
    rows = []
    for season, block in primary.groupby("season"):
        r = poisson_binomial_test(block["p_vf_fav"], block["fav_won"])
        r["season"] = season
        rows.append(r)

    # Cochran Q heterogeneity test.
    #
    #   Q = sum_i w_i (y_i - y_bar)^2,   w_i = 1 / var(y_i),
    #   y_bar = sum_i w_i y_i / sum_i w_i,   df = k - 1
    #
    # y_i is the season calibration gap in percentage points and var(y_i)
    # is its Poisson-binomial null variance. This asks whether the season
    # gaps differ from one another by more than sampling noise. It is not
    # a test that the pooled gap is zero; that is the primary test.
    y = np.array([r["gap_pp"] for r in rows], dtype=float)
    var = np.array([r["se_pp"] ** 2 for r in rows], dtype=float)
    w = 1.0 / var
    y_bar = float(np.sum(w * y) / np.sum(w))
    Q = float(np.sum(w * (y - y_bar) ** 2))
    df = len(rows) - 1
    Q_p = float(stats.chi2.sf(Q, df))
    i_squared = float(max(0.0, (Q - df) / Q) * 100.0) if Q > 0 else 0.0

    out["seasons"] = rows
    out["cochran_q"] = {"Q": Q, "df": df, "p_value": Q_p,
                        "pooled_gap_pp": y_bar, "i_squared_pct": i_squared}
    out["season_gap_range_pp"] = [float(min(r["gap_pp"] for r in rows)),
                                  float(max(r["gap_pp"] for r in rows))]
    out["seasons_rejecting_at_05"] = [r["season"] for r in rows
                                      if r["p_value"] < 0.05]
    out["min_season_p"] = float(min(r["p_value"] for r in rows))

    # ------------------------------------------------------------------
    # Extreme tail
    # ------------------------------------------------------------------
    tail = g.loc[g["p_vf_fav"] > TAIL_THRESHOLD]
    out["tail_above_90"] = poisson_binomial_test(tail["p_vf_fav"],
                                                 tail["fav_won"])
    out["tail_above_90"]["mde_pp"] = minimum_detectable_effect(tail["p_vf_fav"])
    out["tail_above_90"]["breakeven_pp"] = float(tail["breakeven_pp"].mean())

    # ------------------------------------------------------------------
    # Season-blocked bootstrap
    # ------------------------------------------------------------------
    out["bootstrap"] = season_blocked_bootstrap(primary)

    with open(os.path.join(RESULTS_DIR, "robustness_results.json"), "w") as f:
        json.dump(out, f, indent=2)

    pd.DataFrame(rows)[["season", "n", "observed_rate_pct", "implied_rate_pct",
                        "gap_pp", "z", "p_value"]].to_csv(
        os.path.join(RESULTS_DIR, "season_results.csv"), index=False)

    # ------------------------------------------------------------------
    print("=" * 68)
    print("SEASON-BY-SEASON  (favorites above .70)")
    print(f"  {'season':<10}{'n':>6}{'obs':>9}{'implied':>10}{'gap':>8}{'z':>7}{'p':>8}")
    for r in rows:
        print(f"  {r['season']:<10}{r['n']:>6}{r['observed_rate_pct']:>8.2f}%"
              f"{r['implied_rate_pct']:>9.2f}%{r['gap_pp']:>+8.2f}"
              f"{r['z']:>7.2f}{r['p_value']:>8.3f}")
    print()
    print(f"  gap range          : {out['season_gap_range_pp'][0]:+.2f} to "
          f"{out['season_gap_range_pp'][1]:+.2f} pp")
    print(f"  smallest season p  : {out['min_season_p']:.3f}")
    print(f"  seasons rejecting  : {out['seasons_rejecting_at_05'] or 'none'}")
    print(f"  pooled gap         : {y_bar:+.2f} pp")
    print(f"  Cochran Q          : {Q:.2f} on {df} df, p = {Q_p:.3f} "
          f"(I-squared {i_squared:.1f}%)")
    print()
    t = out["tail_above_90"]
    print("EXTREME TAIL (vig-free probability above .90)")
    print(f"  n {t['n']}, gap {t['gap_pp']:+.2f} pp, z = {t['z']:.2f}, "
          f"p = {t['p_value']:.3f}")
    print(f"  minimum detectable effect {t['mde_pp']:.2f} pp vs "
          f"break-even {t['breakeven_pp']:.2f} pp")
    print()
    b = out["bootstrap"]
    print(f"SEASON-BLOCKED BOOTSTRAP  ({b['reps']:,} reps, seed {b['seed']}, "
          f"{b['clusters']} clusters)")
    print(f"  95% CI on the gap  : {b['ci_low_pp']:+.2f} to {b['ci_high_pp']:+.2f} pp")
    print("=" * 68)


if __name__ == "__main__":
    main()
