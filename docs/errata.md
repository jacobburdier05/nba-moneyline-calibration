# Errata: differences between the manuscript and this code

Every confirmatory statistic in the paper reproduced exactly from the raw
archive. The differences below are the complete list. Four are small
numeric corrections. One is a claim that needs its supporting artifact.

Corrections are listed in the order they appear in the paper.

---

## 1. Mean overround: 3.80% should be 3.77%

**Paper, Section 3.2:** "The mean overround is 3.80 percent."

**Computed:** 3.77 percent on the analysis sample of 15,351 games.

**Cause.** 3.80 percent is the mean across all 15,489 games carrying a
moneyline, which includes the 138 pick'em games. The sentence sits in
Section 3.2 *after* the exclusions are described, so it should report the
analysis sample.

| Sample | n | Mean overround |
|---|---|---|
| All games with a moneyline | 15,489 | 3.804% |
| Analysis sample, pick'em excluded | 15,351 | 3.774% |

**Fix.** Change to 3.77 percent.

**Downstream.** Section 5.5 says "Losses track the 3.80 percent mean
overround." Change to 3.77 percent. No result changes; the observed
favorite return of -4.06 percent still tracks it.

---

## 2. Flat-stake return on all favorites: -4.07% should be -4.06%

**Paper, Section 5.5:** "-4.07 percent per bet on all favorites."

**Computed:** -4.0645 percent, which rounds to -4.06.

**Fix.** Change to -4.06 percent. The confidence interval (-5.13 to -3.00)
is correct as printed. The underdog figure (-3.91 percent) and the
favorites-above-.70 figure (-2.90 percent) are both correct.

---

## 3. Cochran Q: 8.47 should be 8.37, p .748 should be .756

**Paper, Section 5.4:** "the Cochran Q test finds no heterogeneity across
seasons (Q = 8.47, p = .748)."

**Computed:** Q = 8.37 on 12 df, p = .756, I-squared 0 percent.

**Cause.** A weighting difference in the Q construction. `src/robustness.py`
uses the standard heterogeneity form, documented inline:

```
Q = sum_i w_i (y_i - y_bar)^2,   w_i = 1 / var(y_i),
y_bar = sum_i w_i y_i / sum_i w_i,   df = k - 1
```

with `var(y_i)` the Poisson-binomial null variance of the season gap. Two
nearby alternatives were checked: weighting by observed-rate variance gives
Q = 7.97 (p = .788), and summing squared season z-statistics against zero
gives 9.86 (p = .629), but that last one is a test against zero rather than
a heterogeneity test and should not be used.

**Fix.** Change to Q = 8.37, p = .756. The conclusion is unchanged and
slightly strengthened. Consider adding I-squared = 0 percent, which states
the no-heterogeneity finding more directly than the p-value does.

---

## 4. The 74-game power figure needs its assumption stated

**Paper, Section 1:** "A 74-game group of extreme favorites... has only
about 7 percent power to detect a 1.7 percentage point pricing deviation."

**Reproduced,** but only once the assumed win probability is fixed. Power
depends on it:

| Assumed p | Power vs 1.7 pp |
|---|---|
| .85 | 6.9% |
| .88 | 7.4% |
| .90 | 7.8% |
| .95 | 10.3% |

**Fix.** State the assumption in the sentence: "a 74-game group of
favorites priced near .85 has about 7 percent power." As written, a
reviewer cannot reproduce the number, and an unreproducible figure in the
opening paragraph is a bad first impression. `src/primary_analysis.py`
computes it at p = .85 with the assumption named in code.

---

## 5. The 260-game primary source audit has no published record

**Paper, Section 3.1:** "A 260-game sample, 20 games from each of the 13
seasons, was compared directly against the live primary archive. All 260
moneylines matched exactly on both sides... The verification scripts and a
complete audit record accompany the paper."

**Status:** the audit record is not in this repository, because it was not
available when the repository was assembled.

This is the one item on this list that is not a rounding difference. The
paper asserts that an artifact accompanies it. Until that artifact is
present, the assertion is not supported.

**Fix, in order of preference:**

1. Add the working file as `docs/primary_source_audit.csv` with columns:
   season, date, teams, archive favorite line, archive underdog line,
   dataset favorite line, dataset underdog line, archive result, dataset
   result, match flag. Then the claim is backed.
2. If the working file no longer exists, re-run the check. It is 260 rows.
3. If neither, soften the sentence to describe the automated full-sample
   cross-validation that *is* published here, and drop the claim that an
   audit record accompanies the paper.

Do not leave it as is. See `docs/pre_specification.md`.

---

## Everything that reproduced exactly

For the record, and it is a long list:

**Sample construction.** 15,490 source rows, 1 missing moneyline, 138
pick'em games, 15,351 analysis games, 13 seasons, favorite vig-free
probabilities spanning .502 to .985.

**Primary test.** n = 6,840 (44.6% of the sample), 5,529 observed wins,
5,489.45 expected, 80.83% observed against 80.26% implied, gap +0.58 pp,
z = 1.22, p = .223.

**Design quantities.** Break-even 3.01 pp (10th to 90th percentile 2.35 to
3.72), 2.61 pp across all favorites, 3.02 pp in the tail. Minimum
detectable effect 1.33 pp primary, 2.66 pp tail.

**Calibration regression.** Intercept -0.047 (CI -0.107 to 0.013), slope
1.049 (CI 0.982 to 1.116), joint Wald chi-squared 2.45, p = .293.

**All five buckets.** Every n, observed rate, implied rate, gap, z, and
Holm-adjusted p matches to the printed precision. Largest deviation +1.73
pp in (.75,.80], raw p .091, Holm .457.

**Seasons.** Range -2.82 to +2.52 pp, none rejecting, smallest p = .107.

**Tail above .90.** 756 games, +0.63 pp, p = .506, MDE 2.66 pp against
break-even 3.02 pp.

**Bootstrap.** 95% CI -0.19 to +1.26 pp, 10,000 replications, seed
20260714, 13 clusters. The seed reproduces the published interval exactly.

**Methodological caution.** Raw-probability artifact -2.50 pp, z = -5.90.

**Data verification.** 30,978 of 30,978 moneylines and 15,490 of 15,490
outcomes match an independent extraction. All 13 season game counts match
the true NBA schedule, including 990 in 2011-12, 1,229 in 2012-13, and 971
in 2019-20.

A paper whose entire results section reproduces from raw data on an
independent implementation is in unusually good shape. Fix the five items
above and the numbers are airtight.
