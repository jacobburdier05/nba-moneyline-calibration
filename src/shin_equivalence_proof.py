"""
Appendix A: proof that Shin's normalization equals the additive rule for a
two-outcome book, with a numerical check of every step.

The Results section asserts this. A reviewer should not have to take the
assertion on trust, so the algebra is written out here and every line is
verified against the actual sample.

-----------------------------------------------------------------------
THE CLAIM

Let q1, q2 be the raw implied probabilities of the two sides of a game and
P = q1 + q2 > 1 the booksum. Shin (1993) sets

    pi_i = [ sqrt(z^2 + 4(1-z) q_i^2 / P) - z ] / (2(1-z))                (1)

with z chosen so that pi_1 + pi_2 = 1. The additive (equal-margin) rule
sets

    pi_i = q_i - (P - 1)/2                                               (2)

For n = 2 these give the same answer.

-----------------------------------------------------------------------
THE PROOF

Step 1. Invert (1) for z.

Rearrange (1) as 2 pi (1-z) + z = sqrt(z^2 + 4(1-z) q^2 / P) and square:

    4 pi^2 (1-z)^2 + 4 pi (1-z) z + z^2 = z^2 + 4(1-z) q^2 / P

Cancel z^2 and divide by 4(1-z), which is nonzero for z < 1:

    pi^2 (1-z) + pi z = q^2 / P

    pi^2 + z pi (1 - pi) = q^2 / P

so, solving for z,

    z = ( q^2 / P - pi^2 ) / ( pi (1 - pi) )                              (3)

Step 2. Require the two sides to agree.

Shin's z is a single property of the book, so (3) must return the same
value for side 1 and side 2. Because pi_1 + pi_2 = 1 we have 1 - pi_1 =
pi_2 and 1 - pi_2 = pi_1, so both denominators equal pi_1 pi_2 and the
requirement reduces to equal numerators:

    q_1^2 / P - pi_1^2 = q_2^2 / P - pi_2^2

    (q_1^2 - q_2^2) / P = pi_1^2 - pi_2^2

    (q_1 - q_2)(q_1 + q_2) / P = (pi_1 - pi_2)(pi_1 + pi_2)

Now q_1 + q_2 = P by definition and pi_1 + pi_2 = 1 by the constraint, so

    q_1 - q_2 = pi_1 - pi_2                                              (4)

Shin's rule preserves the DIFFERENCE of the raw probabilities.

Step 3. Solve.

Two linear equations pin the pair down uniquely:

    pi_1 + pi_2 = 1        (the constraint)
    pi_1 - pi_2 = q_1 - q_2   (from step 2)

    =>  pi_1 = (1 + q_1 - q_2)/2,   pi_2 = (1 - q_1 + q_2)/2

And the additive rule gives

    q_1 - (P-1)/2 = q_1 - (q_1 + q_2 - 1)/2 = (1 + q_1 - q_2)/2

which is the same expression. The two rules coincide.                 QED

-----------------------------------------------------------------------
WHAT THIS DOES AND DOES NOT MEAN

It does not mean Shin's model and the equal-margin rule are the same idea.
Shin's model is derived from a bookmaker pricing against a share z of
insider money; the equal-margin rule is a mechanical convention with no
behavioral content. They coincide only in the two-outcome case, because
there the sum constraint plus the difference-preserving property leave
exactly one degree of freedom. With three or more outcomes the two rules
separate, and Shin loads more margin onto longshots as intended.

For this paper the practical consequence is narrow and worth stating: a
reviewer who asks "why not test Shin?" should know that Shin was tested,
and that in a two-outcome market it is the additive row of Table 5.

The recovered insider share z is still meaningful and is reported below as
a descriptive quantity.

Run:  python src/shin_equivalence_proof.py
"""

import json
import os

import numpy as np
import pandas as pd

from normalization_robustness import norm_shin, norm_additive

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GAMES = os.path.join(ROOT, "data", "processed", "games.csv")
RESULTS_DIR = os.path.join(ROOT, "results")


def z_from_pi(q, pi, P):
    """Equation (3): recover Shin's z from a normalized probability."""
    return (q ** 2 / P - pi ** 2) / (pi * (1.0 - pi))


def main():
    g = pd.read_csv(GAMES)
    q1 = g["p_raw_1"].to_numpy()
    q2 = g["p_raw_2"].to_numpy()
    P = q1 + q2

    # Restrict to books with a positive margin, where Shin is defined.
    ok = P > 1.0
    q1, q2, P = q1[ok], q2[ok], P[ok]
    n_excluded = int((~ok).sum())

    s1, s2 = norm_shin(q1.copy(), q2.copy())
    a1, a2 = norm_additive(q1.copy(), q2.copy())

    out = {"games_tested": int(len(q1)), "games_excluded_underround": n_excluded}

    # --- step 2: the difference-preserving property, equation (4) --------
    diff_err = np.abs((s1 - s2) - (q1 - q2))
    out["step2_max_abs_error"] = float(diff_err.max())

    # --- step 3: the closed form ----------------------------------------
    closed1 = (1.0 + q1 - q2) / 2.0
    closed_err = np.abs(s1 - closed1)
    out["step3_max_abs_error"] = float(closed_err.max())

    # --- the equivalence itself -----------------------------------------
    equiv_err = np.abs(s1 - a1)
    out["equivalence_max_abs_error"] = float(equiv_err.max())

    # --- z is consistent across the two sides, and lies in (0, 1) -------
    z1 = z_from_pi(q1, s1, P)
    z2 = z_from_pi(q2, s2, P)
    out["z_consistency_max_abs_error"] = float(np.abs(z1 - z2).max())
    out["z_min"] = float(z1.min())
    out["z_max"] = float(z1.max())
    out["z_mean"] = float(z1.mean())
    out["z_in_unit_interval"] = bool(((z1 > 0) & (z1 < 1)).all())

    # --- sum constraint --------------------------------------------------
    out["sum_max_abs_error"] = float(np.abs((s1 + s2) - 1.0).max())

    tol = 1e-12
    out["all_steps_verified"] = bool(
        out["step2_max_abs_error"] < tol
        and out["step3_max_abs_error"] < tol
        and out["equivalence_max_abs_error"] < tol
        and out["z_consistency_max_abs_error"] < 1e-9
        and out["sum_max_abs_error"] < tol
        and out["z_in_unit_interval"])

    with open(os.path.join(RESULTS_DIR, "shin_equivalence.json"), "w") as f:
        json.dump(out, f, indent=2)

    print("=" * 72)
    print("APPENDIX A  Shin equals the additive rule for a two-outcome book")
    print("=" * 72)
    print(f"  games tested                       {out['games_tested']:,}")
    print(f"  excluded, booksum at or below 1    {n_excluded}")
    print()
    print("  Step 2, difference preserved: |(pi1 - pi2) - (q1 - q2)|")
    print(f"    max error                        {out['step2_max_abs_error']:.3e}")
    print("  Step 3, closed form pi1 = (1 + q1 - q2)/2")
    print(f"    max error                        {out['step3_max_abs_error']:.3e}")
    print("  Equivalence, |Shin - additive|")
    print(f"    max error                        {out['equivalence_max_abs_error']:.3e}")
    print("  Sum constraint, |pi1 + pi2 - 1|")
    print(f"    max error                        {out['sum_max_abs_error']:.3e}")
    print()
    print("  Recovered insider share z from equation (3):")
    print(f"    consistent across both sides     max error "
          f"{out['z_consistency_max_abs_error']:.3e}")
    print(f"    range                            {out['z_min']:.4f} to {out['z_max']:.4f}")
    print(f"    mean                             {out['z_mean']:.4f}")
    print(f"    all within (0, 1)                {out['z_in_unit_interval']}")
    print()
    print("  RESULT: " + ("ALL STEPS VERIFIED" if out["all_steps_verified"]
                          else "VERIFICATION FAILED"))
    print("=" * 72)
    return 0 if out["all_steps_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
