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

---

# Addendum: robustness findings added August 2026

Three analyses were added after an external review asked whether the
conclusion survives (a) dependence between observations, (b) a different
vig-removal rule, and (c) a transparent power calculation. All three are in
`src/` and run as steps 6 and 7 of `run_all.sh`. Two came back clean. One
qualifies a claim in the paper and is recorded here for the same reason the
rest of this file exists.

## 6. Power normalization does not agree with the other four rules

`src/normalization_robustness.py` re-runs the primary test under five
vig-removal rules.

| Rule | n | Gap (pp) | p | Break-even (pp) | Verdict |
|---|---|---|---|---|---|
| None, raw probabilities | 8,014 | -2.50 | <.001 | — | artifact |
| Proportional (primary) | 6,840 | +0.58 | .223 | 3.01 | below |
| Additive, equal margin | 7,120 | -0.60 | .186 | 1.88 | below |
| Shin (1993) | 7,120 | -0.60 | .186 | 1.88 | below |
| Constant odds ratio | 7,202 | -0.74 | .104 | 1.79 | below |
| **Power** | 7,211 | **-1.31** | **.004** | 1.24 | **exceeds** |

Four of five leave the gap below that rule's own break-even requirement and
none of those four is significant. Power normalization produces a gap that
is significant at p = .004 and exceeds its own break-even threshold by 0.07
percentage points, in the direction of betting underdogs.

This does not overturn the paper, but it does bound the claim. The
conclusion is robust to the normalization choice under four of five rules,
not under all of them. Power normalization is also the rule that behaves
least plausibly at extreme prices. Both facts are stated in the manuscript
rather than left in the code.

## 7. Shin's rule and the additive rule are the same thing here

For a two-outcome book, Shin (1993) reduces exactly to the equal-margin
(additive) rule. Verified symbolically to 40 decimal digits, numerically
across 19,139 synthetic books spanning booksums 1.005 to 1.080, and across
all 15,351 games in the sample; agreement is to machine precision
everywhere except the one underround game where Shin is undefined.

Two implementation notes, both of which produced wrong numbers before they
were caught:

- The textbook Shin expression `[sqrt(z^2 + a) - z] / (2(1-z))` suffers
  catastrophic cancellation as z approaches 1. In double precision the root
  finder converged on values whose probabilities summed to 0.98 rather than
  1. Multiplying by the conjugate gives `2q^2 / (P(sqrt(z^2+a) + z))`,
  which is algebraically identical and numerically stable.
- One game in the archive is quoted with a **booksum below one** (+240
  against -200, booksum 0.9608). Shin's model assumes a positive margin and
  has no valid solution there, so that game falls back to proportional. It
  is outside the primary group. It is also independent evidence that this
  series is a composite rather than a single book's quote, since no single
  book would post a negative margin.

## 8. Dependence does not move the primary result

`src/dependence_robustness.py` re-estimates the gap under variance
estimators that allow correlation within seasons and within teams. The
point estimate is +0.58 pp in every specification; only the standard error
changes.

| Variance estimator | Clusters | SE (pp) | p |
|---|---|---|---|
| Poisson-binomial (primary) | — | 0.47 | .223 |
| Independent, classical | — | 0.47 | .218 |
| Clustered by season | 13 | 0.39 | .134 |
| Clustered by favorite team | 32 | 0.53 | .276 |
| Clustered by underdog team | 33 | 0.50 | .246 |
| Two-way, season and favorite team | 13 | 0.48 | .224 |

None rejects calibration. A team-blocked bootstrap over 32 favorite teams
gives a 95 percent interval of -0.52 to +1.57 pp, wider than the
season-blocked -0.19 to +1.26 and still containing zero.

**But the secondary calibration regression is not equally stable.** Its
joint Wald p is .293 with classical errors, .221 clustering on favorite
team, .181 on underdog team, .085 on season, and **.037 two-way on season
and team**, which would reject perfect calibration at .05. Cluster-robust
variance is unreliable when the cluster count is small, and thirteen
seasons is small enough that the estimator is known to understate variance,
so this is weak evidence. It is reported anyway. A reader who prefers that
estimate should treat the calibration slope as unresolved rather than
confirmed.

## 9. The power claim now has a curve behind it

`src/power_curve.py` produces Figure 3 and `results/power_analysis.json`.
The paper previously asserted that biases "in the range commonly claimed,
roughly 1.7 to 5.1 percentage points, would have been detected here with
near certainty." That is now quantified rather than asserted:

| True gap (pp) | Power |
|---|---|
| 1.00 | 55.9% |
| 1.33 (MDE) | 80.0% |
| 1.70 | 94.8% |
| 2.00 | 98.8% |
| 3.01 (break-even) | >99.9% |
| 5.10 | >99.9% |

The standard error is 0.4741 pp, from the heterogeneous per-game null
variance rather than a pooled p(1-p).

## 10. Cochran Q: the statistic was right, the documentation was not

An external reviewer suggested Cochran's Q may be the wrong test for season
heterogeneity, on the grounds that Cochran's Q is a test for related binary
treatments. That conflates two different statistics that share a name. The
meta-analytic Cochran Q heterogeneity statistic used here is the standard
tool for asking whether stratum estimates differ by more than sampling
noise, and it is what `src/robustness.py` computes.

The criticism was still useful, because the paper stated the result without
stating the construction. The manuscript now writes out the formula:
Q is the sum over seasons of w times the squared deviation of the season gap
from the inverse-variance-weighted mean, with w the inverse of the
Poisson-binomial null variance, referred to chi-squared on k-1 degrees of
freedom. No change to the statistic; the corrected value remains Q = 8.37,
p = .756, I-squared 0 percent, as recorded in item 3 above.

---

# Addendum 2: an unsourced claim, removed (August 2026)

## 11. The "1.7 to 5.1 percentage point" literature range had no source

Earlier drafts stated that favorite bias "in the range commonly claimed,
roughly 1.7 to 5.1 percentage points" had been reported in prior work, and
Figure 3 marked both values as the smallest and largest effects in the
cited literature. A reviewer asked where the numbers came from. They came
from nowhere. Both were hard-coded constants with no citation behind them.

Tracing them turned up a substantive problem rather than a clerical one:

- Six of the eight cited papers report **rates of return** or
  **point-spread cover rates**, not win-probability calibration gaps. The
  two quantities are not interchangeable without attaching the odds. At
  this sample's prices a -5.5 percent return corresponds to roughly -1.6
  points of calibration gap and a -23 percent return to roughly -16, so
  the classic literature, honestly converted, spans a far wider range than
  1.7 to 5.1 and points the other way, because it concerns parimutuel
  horse racing rather than a two-outcome book.
- Newall and Cortis (2021), the one literature review in the citation set
  and the obvious place such a range would live, is entirely directional
  and reports no effect magnitudes at all.
- The moneyline branch rests largely on Woodland and Woodland (2001),
  whose conversion method was questioned by Berkowitz, Depken and Gandar
  (2018), and whose authors reported in 2011 that the effect disappears in
  later seasons.
- A coincidence worth noting: 1.7 is numerically almost identical to this
  paper's own largest bucket deviation, +1.73 points in the .75 to .80
  bucket.

**Fix.** The marks were removed rather than re-sourced, because no
defensible replacement exists in those units. Figure 3 now marks only
quantities computed from this sample: the observed +0.58-point gap, the
1.33-point minimum detectable effect, and the 3.01-point break-even
requirement. The Introduction's illustrative power calculation was
re-anchored the same way: a 74-game bucket has about 11 percent power
against this sample's own 3.01-point break-even margin, replacing the
7 percent figure that had been computed against the unsourced 1.7. The
Discussion now argues from power at the break-even threshold, which is
stronger than the claim it replaced and needs no citation. Section 6 of
the manuscript explains the removal in the open.

## 12. The MDE is a normal approximation, and it was checked

The 1.33-point minimum detectable effect is the conventional two-sided
normal-approximation formula, not an exact inversion of the
Poisson-binomial power function. That distinction was not stated.

`src/power_curve.py` now computes the exact version: it builds the exact
Poisson-binomial distribution by discrete Fourier transform of the
characteristic function, finds the exact two-sided rejection region under
the null, and inverts exact power at 80 percent.

| Quantity | Value |
|---|---|
| Exact rejection region | wins <= 5,425 or >= 5,554 |
| Exact size (discreteness, not .05) | .0484 |
| MDE, normal approximation | 1.3281 pp |
| MDE, exact Poisson-binomial | 1.3242 pp |
| Difference | 0.0039 pp |

The approximation is retained in the text because it is the conventional
quantity, and both are now reported in Table 1. The exact mean and
standard deviation of the null distribution also match the analytic
sum(p) and sqrt(sum p(1-p)) to four decimal places, which is an
independent check on the primary test's variance.

## 13. Wording made less absolute

Four phrases overstated what the paper establishes and were changed:

| Was | Now |
|---|---|
| "on verified data" | "on cross-validated archival data" (the 260-game audit was hand-drawn, not probabilistic) |
| "manufacturing most of the gap" | "concentrating much of the estimated gap" (removes a causal claim not established) |
| "a curve-fitting device" | "a flexible transformation without the same direct behavioral or structural interpretation" (methodological rather than pejorative) |
| "adequately powered" | "adequately powered for its pre-specified primary estimand" (power is specification-specific; the power-normalization run has its own MDE and threshold) |

## 14. Plain-language revision of the prose

The manuscript was rewritten in plainer English at the author's request.
No finding, statistic, table value, figure, citation or claim changed. A
script compared every numeric token and every parenthetical citation in
the old and new build sources and found both sets identical.

What changed is word choice. Elevated non-technical diction was replaced
with ordinary words: *conflate* became *mix up*, *impounded* became
*absorb*, *estimand* became *the quantity being estimated*, *materially*
became *heavily*, *durable* became *lasting*, *monetize* became *turn
into profit*, *propagate* became *carry over*, *asymptotics* became
*approximations that fail when clusters are few*, *admissible* became
*possible*, *persuasive* became *convincing*, *legitimate* became *fair*,
*cosmetic* became *matters*, and *collinear* became *mirror images of
each other*. Five long sentences were split.

Technical vocabulary was deliberately left alone. Poisson-binomial,
calibration gap, overround, vig-free, booksum, minimum detectable effect,
cluster-robust variance, Cochran Q, Holm correction, Wilson interval and
the rest are the field's terms of art; replacing them would cost
precision rather than gain clarity.

Measured on the body prose, the Flesch-Kincaid grade level fell from 13.8
to 12.9, Flesch reading ease rose from 36.2 to 41.8, and the share of
words with three or more syllables fell from 19.1 to 16.8 percent. Length
is unchanged at 15 pages plus a 6-page supplement.

**One consequence for item 13 above.** Three of the four replacement
phrasings recorded in that table were themselves reworded in this pass
and no longer appear verbatim in the manuscript. The substance of each
correction stands; only the wording moved.

| Item 13 recorded | Now reads |
|---|---|
| "on cross-validated archival data" | "run on cross-checked archival data" |
| "concentrating much of the estimated gap" | "placing much of the estimated gap" |
| "a flexible transformation without the same direct behavioral or structural interpretation" | "a flexible adjustment with no story about bookmakers or bettors behind it" |
| "adequately powered for its pre-specified primary estimand" | "powered well enough for the comparison it was built to make" |

## 15. Second plain-language pass: sentence structure

Item 14 replaced elevated words with ordinary ones and moved the
Flesch-Kincaid grade from 13.8 to 12.9. That pass left sentence length
untouched, at an average of 22 words with sixty sentences running past
28. Long sentences were doing most of the remaining work against a reader.

Forty-two sentences in the main paper and ten in the supplement were split
into shorter ones. Nothing was deleted and nothing was added except the
connective words a split requires. The word count moved from 3,926 to
3,969.

| Measure, main paper body prose | Original | After item 14 | Now |
|---|---|---|---|
| Average sentence length | 22.4 | 22.2 | 16.8 |
| Words of three or more syllables | 19.1% | 16.8% | 16.9% |
| Flesch-Kincaid grade | 13.8 | 13.0 | 10.8 |
| Flesch reading ease | 36.2 | 41.7 | 47.3 |

The supplement moved from grade 11.8 to 10.2, and reading ease from 50.9
to 54.9.

Line spacing was tightened from 340 to 326 twips so the main paper stays
at 15 pages. The supplement is 7 pages.

As with item 14, a script compared every numeric token and every
parenthetical citation across the old and new build sources and found both
sets identical. Sentences that are lists of numbers were left alone;
breaking them up would have hurt rather than helped.
