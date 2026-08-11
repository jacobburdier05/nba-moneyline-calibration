# What the pre-specification claim rests on

Pre-specification is this paper's central methodological contribution. It
is the thing that makes a null result informative rather than empty. It is
therefore also the claim a reviewer will press hardest, and it needs to be
stated with more care than anything else in the paper.

This document is an honest account of what is and is not established.

---

## What the paper currently claims

Section 4:

> The analysis plan was written and frozen before any outcome data were
> examined. It is included with the paper. The plan is self-timestamped
> rather than lodged with an external registry, a distinction discussed in
> the limitations.

Section 7:

> Finally, the analysis plan is self-timestamped; external lodgment would
> make the pre-specification independently verifiable.

The disclosure is honest. That is the right instinct and it should be kept.

## What evidence exists

| Claim | Evidence available |
|---|---|
| The plan's *content* | Strong. Fully recoverable from the paper and reimplemented in `src/`. Everything the plan specifies is executable and every confirmatory number reproduces. |
| The plan's *freeze date* | **None that is independent.** No standalone analysis-plan document with a verifiable creation timestamp has been located. The earliest artifact is the manuscript itself. |

## The correction you need to hear

Posting the plan to OSF Registries **now** does not fix this, and it would
be a mistake to imply that it does.

A registration created in August 2026 carries an August 2026 timestamp. The
analysis was run in July. An external registry timestamp that postdates the
analysis is not evidence of a prospective freeze. Citing it as though it
were would convert an honest limitation into a misleading claim, which is
strictly worse than the current disclosure.

Reviewers in this area know exactly how registry timestamps work. This is
not a detail that survives scrutiny.

## Three options, honestly assessed

### Option 1. Keep the disclosure, strengthen the language (recommended)

Say precisely what is true: the plan was fixed in advance, the record of
that is internal, and the reader is invited to check the harder thing that
*can* be checked, which is that the analysis contains no forking paths.
The paper's design makes this credible without needing a registry: one
named primary contrast, a threshold set on stated reasoning rather than
tuned, a power calculation anchored to an economic quantity computed from
the data's own prices, and exploratory analyses explicitly separated and
labeled.

This costs nothing and is fully defensible.

### Option 2. Post the plan publicly, framed correctly

Post `preregistration/analysis_plan.md` to OSF and describe it as what it
is: a public, immutable posting of the analysis plan, made after the
analysis, so the specification is fixed and inspectable going forward. Do
**not** call it a preregistration of this study. It adds transparency, not
verification.

Worth doing. Just do not overclaim it.

### Option 3. Preregister the *next* study prospectively

This is the one that actually solves the problem, and it solves it
permanently. Register the extension before touching its outcome data:
opening versus closing lines, the post-2020 era, multi-book best-price
execution, or Shin normalization against proportional. Then the
pre-specification claim has a real timestamp behind it, and the paper it
supports is a genuinely preregistered study.

If you write a second paper, this is the single highest-value thing you can
do to it, and it costs one afternoon before you start.

## Replacement text for the Limitations section

Replace the current final sentence with:

> The analysis plan was fixed before outcome data were examined, but the
> record of that freeze is internal to the author's files rather than
> lodged with an external registry, so the timing is not independently
> verifiable. The plan itself is published in full with the replication
> materials, and the design leaves little room for undisclosed flexibility:
> there is one named primary contrast, a threshold and an effect-size floor
> both set from stated reasoning rather than from the outcome data, and
> exploratory analyses reported separately and labeled as such. Readers who
> wish to check the stronger claim can re-run the confirmatory pipeline,
> which reproduces every reported statistic from the raw archive.

This is stronger than the original because it stops apologizing and instead
tells the reader what to verify.

## The 260-game primary source audit

The paper reports a manual audit of 260 games, 20 per season, against the
live sportsbookreviewsonline archive, with all 260 lines and outcomes
matching. That check cannot be automated here, because the primary source
is distributed as per-season spreadsheet downloads rather than a queryable
endpoint.

Two things are needed:

1. **Publish the audit record.** The per-game comparison table from that
   check belongs in `docs/primary_source_audit.csv`. A claim of 260 of 260
   matching with no published record is exactly the kind of assertion a
   reviewer will ask to see. If the working file still exists, add it.
2. **Note what the automated check covers.** `src/verify_data.py` performs
   a full-sample cross-validation of all 30,978 moneylines and 15,490
   outcomes against an independent extraction, with zero mismatches. This
   is broader coverage than the 260-game sample, though it verifies
   internal consistency between two extractions rather than agreement with
   the primary source. Both checks are worth reporting; they answer
   different questions.
