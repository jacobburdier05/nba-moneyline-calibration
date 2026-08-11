# Data

## Files

| File | Rows | Description |
|---|---|---|
| `raw/nba_moneylines.csv` | 15,490 | Matchup-level table. The analysis file. Carries `teamML.team1`, `oppML.team1`, `outcomeGame.team1`, `slugSeason`. This is upstream `new_nba_ytd_matchup.csv` reduced to the ten columns this analysis reads, which takes it from 28 MB to 1.2 MB. No values were altered. |
| `raw/nba_adv_crosscheck.csv` | 32,985 | Team-game-level extraction from the same source repository, including playoffs. Used only as an independent cross-check of moneylines and outcomes. This is upstream `nba_adv_complete.csv` reduced to the eight columns the check uses (`newGameID`, `slugSeason`, `slugTeam`, `teamML`, `oppML`, `isWin`, `typeSeason`, `dateGame`), which takes it from 20 MB to 2.4 MB. No values were altered. |
| `processed/games.csv` | 15,351 | Built by `src/build_dataset.py`. One row per game after exclusions, with raw and vig-free probabilities, the favorite side, payouts, and the per-game break-even requirement. |

`processed/games.csv` is generated. Delete it and re-run `src/build_dataset.py`
to rebuild.

## Provenance

Consensus moneylines and final scores originate from the
sportsbookreviewsonline.com NBA odds archive and reach this repository
through the public data repository accompanying:

> Dotan, G. (2020). *Beating the book: A machine learning approach to
> identifying an edge in NBA betting markets* (Master's thesis, UCLA).
> https://github.com/guydotan/ucla-thesis

Files were retrieved unmodified. No cleaning, imputation, or correction was
applied to `raw/`.

## Known properties of the source

- One moneyline per side per game. The archive does not document whether
  the quote is an opening or closing line, and does not identify the book.
- Regular season only. The source pipeline had already dropped playoff
  games before publishing this table.
- One game is missing a moneyline. This matches the source thesis's own
  description and is excluded.
- 138 pick'em games carry identical prices on both sides. Neither side is
  a favorite, so they are excluded.

## Column reference for `processed/games.csv`

| Column | Meaning |
|---|---|
| `season` | NBA season, e.g. `2015-16` |
| `date` | game date |
| `ml1`, `ml2` | American moneylines, team1 and team2 |
| `team1_won` | 1 if team1 won |
| `p_raw_1`, `p_raw_2` | raw, vig-inclusive implied probabilities |
| `overround` | raw probability sum minus one |
| `p_vf_1`, `p_vf_2` | vig-free probabilities, proportional normalization |
| `fav_team`, `fav_ml`, `dog_ml` | favorite side and both quoted prices |
| `p_raw_fav`, `p_vf_fav` | favorite's raw and vig-free probability |
| `fav_won` | 1 if the favorite won |
| `fav_payout`, `dog_payout` | net profit per unit staked if that side wins |
| `breakeven_pp` | percentage points the favorite must beat its vig-free probability by, for a flat bet at the quoted price to break even |


## Verifying the column subsets

Both files in `raw/` are column subsets of larger upstream originals, kept
small so the repository clones quickly. To confirm nothing was altered:

```bash
python src/fetch_source_data.py
```

That downloads the complete originals from `guydotan/ucla-thesis`, prints a
SHA-256 for each, and compares every retained column row by row. Expected
output: `VERIFIED: the local subsets match upstream exactly.`

Reference hashes at time of assembly:

| Upstream file | SHA-256 |
|---|---|
| `new_nba_ytd_matchup.csv` | `6968fa3e472e425725b135b55a9a502170ad1c02154c4205ab266f6be700edf3` |
| `nba_adv_complete.csv` | `4958bcd335fd4c45e20e5980ae7146e0e4eff74c19444acd9576ea564d3c7944` |
