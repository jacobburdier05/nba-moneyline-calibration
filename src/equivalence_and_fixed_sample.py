"""
Two revisions a reviewer asked for, and one derivation the paper was
skipping.

1. EQUIVALENCE. The paper's primary test asks whether the calibration gap
   is exactly zero. Most of its conclusion is about something else:
   whether the gap is smaller than an amount a bettor could use. Those are
   different hypotheses, and a minimum detectable effect is not an answer
   to the second one. An 80 percent MDE of 1.33 points does not mean every
   effect below 1.33 has been ruled out. This runs the test that does
   match the claim: two one-sided tests against the break-even margin,
   evaluated exactly on the Poisson-binomial rather than by normal
   approximation.

2. FIXED SAMPLE. Table 5 in the main paper changes two things at once.
   Each vig-removal rule produces its own probabilities, so each rule also
   selects a different set of games above the .70 threshold: 6,840 under
   proportional, 7,211 under power. Differences across rows therefore mix
   the rule's effect with a change in sample composition. This holds the
   sample fixed at the 6,840 games the pre-specified proportional rule
   selects, and applies every rule to exactly those games.

3. BREAK-EVEN, DERIVED. The paper compares a mean calibration gap against
   a mean margin share. That is a shortcut. Expected return on a unit
   stake on favorite i is p_i / r_i - 1, where r_i is the raw implied
   probability, so the portfolio breaks even when the gap is weighted by
   1 / r_i, not weighted equally. This computes the exact uniform shift
   that zeroes expected return, and reports how far the equal-weighted
   shortcut is off. It also asks what happens if the gap is concentrated
   in the shortest or longest prices rather than spread evenly.

Run:  python src/equivalence_and_fixed_sample.py
"""

import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "data", "processed", "games.csv")
RESULTS_DIR = os.path.join(ROOT, "results")

from normalization_robustness import (norm_proportional, norm_additive,
                                      norm_power, norm_shin, norm_odds_ratio)
from power_curve import poisson_binomial_pmf

THRESHOLD = 0.70
ALPHA = 0.05

RULES = [("Proportional (primary)", norm_proportional),
         ("Additive, equal margin", norm_additive),
         ("Shin (1993)", norm_shin),
         ("Constant odds ratio", norm_odds_ratio),
         ("Power", norm_power)]


def gap_test(won, p):
    """Poisson-binomial test of the calibration gap, in percentage points."""
    gap = float((won - p).mean() * 100.0)
    se = float(np.sqrt(np.sum(p * (1.0 - p))) / len(p) * 100.0)
    z = gap / se
    return {"n": int(len(p)), "gap_pp": gap, "se_pp": se, "z": z,
            "p_value": float(2 * stats.norm.sf(abs(z)))}


def exact_tail(p_shifted, k, side):
    """Exact Poisson-binomial tail probability for an observed count k.

    Each tail is summed directly from the pmf. Taking the upper tail as
    1 - cdf[k-1] loses all precision when the cdf is within rounding
    distance of one, and returned a small negative number the first time
    this was run.
    """
    pmf = poisson_binomial_pmf(np.clip(p_shifted, 1e-12, 1 - 1e-12))
    return float(pmf[:k + 1].sum()) if side == "le" else float(pmf[k:].sum())


def main():
    g = pd.read_csv(GAMES)
    out = {}

    # ------------------------------------------------------------------
    # 3. break-even, derived rather than approximated
    # ------------------------------------------------------------------
    primary = g.loc[g["p_vf_fav"] > THRESHOLD].copy()
    q = primary["p_vf_fav"].to_numpy()          # vig-free
    r = primary["p_raw_fav"].to_numpy()         # raw, so payout = (1-r)/r
    won = primary["fav_won"].to_numpy().astype(float)

    equal_weight = float((r - q).mean() * 100.0)
    exact_uniform = float((1.0 - np.mean(q / r)) / np.mean(1.0 / r) * 100.0)

    # what if the gap is not spread evenly? put it all in one decile
    order = np.argsort(r)
    lo_idx = order[: len(order) // 10]           # longest prices in group
    hi_idx = order[-len(order) // 10 :]          # shortest prices
    def concentrated(idx):
        w = np.zeros(len(r)); w[idx] = 1.0
        # solve mean((q + d*w)/r) = 1  for d
        return float((1.0 - np.mean(q / r)) / np.mean(w / r) * 100.0)

    out["breakeven"] = {
        "equal_weighted_mean_pp": equal_weight,
        "exact_uniform_shift_pp": exact_uniform,
        "shortcut_error_pp": abs(equal_weight - exact_uniform),
        "if_all_gap_in_shortest_decile_pp": concentrated(hi_idx),
        "if_all_gap_in_longest_decile_pp": concentrated(lo_idx),
        "note": ("Expected return on a unit stake is p/r - 1, so the "
                 "portfolio breaks even on a 1/r-weighted gap. The paper "
                 "quotes the equal-weighted mean."),
    }

    # ------------------------------------------------------------------
    # 1. equivalence: two one-sided tests against the break-even margin
    # ------------------------------------------------------------------
    margin = exact_uniform / 100.0
    k = int(won.sum())
    # H0 upper: true gap = +margin. Evidence against it is a low count.
    p_upper = exact_tail(q + margin, k, "le")
    # H0 lower: true gap = -margin. Evidence against it is a high count.
    p_lower = exact_tail(q - margin, k, "ge")
    tost_p = max(p_upper, p_lower)

    se_pp = float(np.sqrt(np.sum(q * (1 - q))) / len(q) * 100.0)
    gap_pp = float((won - q).mean() * 100.0)
    ci = (gap_pp - 1.96 * se_pp, gap_pp + 1.96 * se_pp)
    ci90 = (gap_pp - 1.645 * se_pp, gap_pp + 1.645 * se_pp)

    out["equivalence"] = {
        "margin_pp": exact_uniform,
        "observed_gap_pp": gap_pp,
        "favorite_wins": k,
        "p_upper_exact": p_upper,
        "p_lower_exact": p_lower,
        "tost_p_exact": tost_p,
        "equivalence_established_at_05": bool(tost_p < ALPHA),
        "ci95_pp": list(ci),
        "ci90_pp": list(ci90),
        "team_bootstrap_ci95_upper_pp": 1.57,
        "interpretation": (
            "Rejecting both one-sided nulls means the gap is smaller in "
            "absolute value than the break-even margin, at the stated "
            "level. This is the hypothesis the paper's conclusion actually "
            "relies on."),
    }

    # ------------------------------------------------------------------
    # 2. every rule on the SAME 6,840 games
    # ------------------------------------------------------------------
    q1_all = g["p_raw_1"].to_numpy()
    q2_all = g["p_raw_2"].to_numpy()
    fav_is_1 = (g["p_vf_1"].to_numpy() >= g["p_vf_2"].to_numpy())
    keep = (g["p_vf_fav"].to_numpy() > THRESHOLD)      # the pre-specified sample
    won_all = g["fav_won"].to_numpy().astype(float)

    rows = []
    for name, fn in RULES:
        a, b = fn(q1_all.copy(), q2_all.copy())
        p_fav = np.where(fav_is_1, a, b)
        raw_fav = np.where(fav_is_1, q1_all, q2_all)
        pf, rf, wf = p_fav[keep], raw_fav[keep], won_all[keep]
        res = gap_test(wf, pf)
        be = float((rf - pf).mean() * 100.0)
        res.update({"rule": name, "breakeven_pp": be,
                    "exceeds_breakeven": bool(abs(res["gap_pp"]) > be)})
        rows.append(res)

    # the no-normalization case, same fixed sample
    raw_fav = np.where(fav_is_1, q1_all, q2_all)[keep]
    res = gap_test(won_all[keep], raw_fav)
    res.update({"rule": "None, raw probabilities", "breakeven_pp": None,
                "exceeds_breakeven": None})
    rows.insert(0, res)
    out["fixed_sample_normalization"] = rows

    with open(os.path.join(RESULTS_DIR, "equivalence_fixed_sample.json"), "w") as f:
        json.dump(out, f, indent=2)

    # ------------------------------------------------------------------
    print("=" * 88)
    print("BREAK-EVEN, DERIVED RATHER THAN APPROXIMATED")
    print("=" * 88)
    b = out["breakeven"]
    print(f"  equal-weighted mean margin share (what the paper quotes)  "
          f"{b['equal_weighted_mean_pp']:.4f} pp")
    print(f"  exact uniform shift that zeroes expected return           "
          f"{b['exact_uniform_shift_pp']:.4f} pp")
    print(f"  error in the shortcut                                     "
          f"{b['shortcut_error_pp']:.4f} pp")
    print(f"  if the whole gap sat in the shortest-priced decile        "
          f"{b['if_all_gap_in_shortest_decile_pp']:.2f} pp")
    print(f"  if the whole gap sat in the longest-priced decile         "
          f"{b['if_all_gap_in_longest_decile_pp']:.2f} pp")
    print()
    print("=" * 88)
    print("EQUIVALENCE TEST  (two one-sided, exact Poisson-binomial)")
    print("=" * 88)
    e = out["equivalence"]
    print(f"  equivalence margin        +/- {e['margin_pp']:.2f} pp")
    print(f"  observed gap              {e['observed_gap_pp']:+.2f} pp "
          f"({e['favorite_wins']:,} favorite wins)")
    print(f"  p, gap is below +margin   {e['p_upper_exact']:.3e}")
    print(f"  p, gap is above -margin   {e['p_lower_exact']:.3e}")
    print(f"  TOST p                    {e['tost_p_exact']:.3e}")
    print(f"  equivalence at .05        {e['equivalence_established_at_05']}")
    print(f"  95% CI                    [{e['ci95_pp'][0]:+.2f}, {e['ci95_pp'][1]:+.2f}] pp")
    print()
    print("=" * 88)
    print(f"EVERY RULE ON THE SAME {int(keep.sum()):,} GAMES")
    print("=" * 88)
    print(f"{'Rule':<26}{'n':>7}{'Gap':>8}{'z':>8}{'p':>9}{'Break-even':>12}{'Verdict':>10}")
    for r_ in rows:
        be = "—" if r_["breakeven_pp"] is None else f"{r_['breakeven_pp']:.2f}"
        v = "artifact" if r_["exceeds_breakeven"] is None else (
            "exceeds" if r_["exceeds_breakeven"] else "below")
        pv = "<.001" if r_["p_value"] < 0.001 else f"{r_['p_value']:.3f}"
        print(f"{r_['rule']:<26}{r_['n']:>7,}{r_['gap_pp']:>+8.2f}{r_['z']:>8.2f}"
              f"{pv:>9}{be:>12}{v:>10}")
    print("=" * 88)


if __name__ == "__main__":
    main()
