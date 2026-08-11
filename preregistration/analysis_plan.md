# Frozen Analysis Plan

**Study:** Are NBA Consensus Moneylines Calibrated? A Pre-Specified Test for
Favorite Bias in 15,351 Games
**Author:** Jacob Burdier
**Plan status:** confirmatory analyses fixed before outcome data were examined

> **Provenance note.** This file is the analysis plan as specified in the
> paper and as implemented in `src/`. It was transcribed into this
> repository in August 2026 when the repository was assembled. It is not
> itself a timestamped record of when the plan was frozen. See
> `docs/pre_specification.md` for an honest account of what evidence does
> and does not exist for the freeze date, and for the wording the paper
> should use.

---

## 1. Research question

Are consensus NBA moneylines calibrated? That is, do favorites win at the
rate their vig-free implied probabilities state?

The question is a calibration question about prices, not a claim about the
mechanism that sets them. Following Newall and Cortis (2021):

- **Favorite bias** means bettors overpay for favorites, so favorites win
  *less* often than their implied probability states.
- **Longshot bias** is the reverse, and is the classic horse-racing
  pattern.

This study tests for favorite bias.

## 2. Primary confirmatory hypothesis

One hypothesis, fixed in advance.

> **H0:** Among games where the favorite's vig-free implied probability
> exceeds .70, favorites win at exactly their implied rate.
> **H1:** They do not.

Two-sided, alpha = .05. This is the only confirmatory test. Everything else
is secondary or exploratory.

**Why .70.** The threshold is set above the coin-flip region where implied
and observed rates are mechanically close, and low enough to retain a large
group. It is fixed before analysis and is not tuned to the data.

## 3. Probability construction

1. Convert American moneyline odds to raw implied probabilities:
   - negative odds: `p = |odds| / (|odds| + 100)`
   - positive odds: `p = 100 / (odds + 100)`
2. Remove the bookmaker margin by **proportional normalization**: divide
   each side's raw probability by the sum of the two, so the pair sums to
   one.
3. The **favorite** is the side with the higher vig-free probability.
4. Raw probabilities are retained for the sensitivity analysis in 7.

Proportional normalization is one assumption among several. Shin-type
methods are named as future work, not run here.

## 4. Test statistic

Implied probabilities differ game by game, so the number of favorite wins
is **Poisson-binomial**, not binomial. Under the null:

```
expected = sum_i p_i
variance = sum_i p_i (1 - p_i)
z        = (observed - expected) / sqrt(variance)
```

Two-sided normal p-value. This construction replaces the fixed-probability
bucket tests common in the literature, which assume every game in a bucket
carries the same probability.

## 5. The smallest effect worth detecting

A calibration gap matters to a bettor only if it exceeds the share of the
bookmaker margin carried by the favorite side of the price:

```
break-even requirement (pp) = (p_raw_favorite - p_vigfree_favorite) x 100
```

computed game by game and averaged over the group. This is the economic
anchor. The design is judged against it, not against an arbitrary effect
size.

The minimum detectable effect at 80 percent power uses the same
heterogeneous per-game variance as the test:

```
MDE (pp) = (z_{1-alpha/2} + z_{power}) x sqrt(sum p_i(1-p_i)) / n x 100
```

The design is adequate if MDE < break-even requirement, so that any
economically exploitable bias would be detected.

## 6. Secondary analyses (pre-specified)

1. **Logistic calibration regression.** Regress the favorite win indicator
   on the log-odds of the vig-free implied probability. Perfect
   calibration implies intercept 0 and slope 1. Joint Wald test, 2 df.
2. **Fixed probability buckets.** Five buckets: (.50,.60], (.60,.70],
   (.70,.75], (.75,.80], (.80,1.00]. Each tested with the Poisson-binomial
   statistic. **Holm** step-down correction across the five.
3. **Flat-stake returns.** One unit per bet at quoted prices, for all
   favorites, all underdogs, and favorites above .70, with 95 percent
   intervals.

## 7. Sensitivity and methodological caution

Repeat the primary test against **raw**, vig-inclusive implied
probabilities. Under proportional vig removal, any gap this produces is the
bookmaker margin rather than bettor behavior. Report both so readers can
see what the normalization assumption is doing. This is included because
several bucket-test designs in circulation skip vig removal entirely.

## 8. Exploratory analyses (added at review, labeled as such)

These were **not** part of the confirmatory plan and are reported as
exploratory:

- season-by-season gaps with a Cochran Q heterogeneity test
- the extreme tail above .90 vig-free implied probability
- a season-blocked bootstrap, 10,000 replications, seed 20260714

## 9. Data and exclusions

**Source.** Consensus moneylines and outcomes for NBA regular season games,
2007-08 through 2019-20, originally published by sportsbookreviewsonline.com
and distributed in the public repository accompanying Dotan's UCLA master's
thesis.

**Exclusions, fixed in advance:**

1. games with a missing moneyline on either side
2. pick'em games, where the two sides carry identical prices and neither
   side is a favorite

**Verification before analysis.** The moneylines and outcomes are validated
against an independent extraction shipped in the same source repository,
and season game counts are checked against the true NBA schedule including
the 2011-12 lockout, the cancelled 2012-13 game, and the March 2020
suspension. See `src/verify_data.py`.

## 10. What would falsify the paper's conclusion

The conclusion is that favorite mispricing was too small to exploit. It
would be overturned by:

- a primary-test gap exceeding the break-even requirement in the
  hypothesized direction, at p < .05
- a calibration slope reliably different from 1 in the joint Wald test
- a bucket surviving Holm correction with a gap above break-even
- flat-stake returns on any pre-specified group reliably above zero

None of these outcomes was observed. The null result is reported as the
finding, not buried.

## 11. Deviations from this plan

Any deviation must be listed here. As of the analysis run recorded in
`results/`:

- The exploratory analyses in section 8 were added after the confirmatory
  analyses were run, at review, and are labeled exploratory throughout.
- No confirmatory analysis was added, removed, or altered after the data
  were examined.

---

## References

Newall, P. W. S., & Cortis, D. (2021). Are sports bettors biased toward
longshots, favorites, or both? A literature review. *Risks, 9*(1), 22.

Dotan, G. (2020). *Beating the book: A machine learning approach to
identifying an edge in NBA betting markets* (Master's thesis, UCLA).
https://github.com/guydotan/ucla-thesis
