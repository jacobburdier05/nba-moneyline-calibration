"""
Stage 0: data verification, run before any analysis.

Three independent checks on the data layer.

  Check 1  Moneyline cross-validation. The analysis file
           (nba_moneylines.csv) is a matchup-level table. The same
           source repository also ships nba_adv_complete.csv, a separate
           team-game-level extraction carrying its own teamML / oppML
           columns; nba_adv_crosscheck.csv here is that file with only the
           columns this check needs, so the repository stays small. Every
           moneyline in the analysis file is compared against that
           independent table, game by game and side by side.

  Check 2  Schedule integrity. Season game counts are compared against
           the true NBA regular season schedule, including the three
           irregular years: the 990-game 2011-12 lockout season, the
           1,229-game 2012-13 season (one cancellation, Celtics at Pacers,
           after the Boston Marathon bombing), and the 971 games played in
           2019-20 before the March 2020 suspension.

  Check 3  Outcome integrity. Recorded win/loss outcomes are compared
           against the independent table, and internal consistency is
           checked (exactly one winner per game).

A separate manual audit of 260 games against the live sportsbookreviewsonline
primary source is discussed in docs/pre_specification.md. That check cannot
be automated here because the primary source is distributed as per-season
spreadsheet downloads rather than a queryable endpoint.

Run:  python src/verify_data.py
"""

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW_DIR = os.path.join(ROOT, "data", "raw")
RESULTS_DIR = os.path.join(ROOT, "results")

ANALYSIS_FILE = os.path.join(RAW_DIR, "nba_moneylines.csv")
CROSSCHECK_FILE = os.path.join(RAW_DIR, "nba_adv_crosscheck.csv")

# True NBA regular season game counts.
EXPECTED_SCHEDULE = {
    "2007-08": 1230, "2008-09": 1230, "2009-10": 1230, "2010-11": 1230,
    "2011-12": 990,   # lockout-shortened, 66 games per team
    "2012-13": 1229,  # one game cancelled
    "2013-14": 1230, "2014-15": 1230, "2015-16": 1230, "2016-17": 1230,
    "2017-18": 1230, "2018-19": 1230,
    "2019-20": 971,   # suspended March 2020
}


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    report = {}
    failures = []

    ytd = pd.read_csv(ANALYSIS_FILE)
    adv = pd.read_csv(CROSSCHECK_FILE, low_memory=False)

    # ------------------------------------------------------------------
    # Check 1: moneyline cross-validation against an independent table
    # ------------------------------------------------------------------
    adv_reg = adv.loc[adv["typeSeason"] == "Regular Season"].copy()

    # Key the independent table on (game, team) so each side is checked
    # against the line recorded for that specific team.
    adv_side = (adv_reg[["newGameID", "slugTeam", "teamML"]]
                .drop_duplicates(subset=["newGameID", "slugTeam"])
                .set_index(["newGameID", "slugTeam"])["teamML"])

    checks, mismatches = 0, 0
    mismatch_rows = []
    for col_game, col_team, col_ml, label in [
        ("newGameID", "slugTeam", "teamML.team1", "favorite-side team"),
        ("newGameID", "slugOpp", "oppML.team1", "opponent-side team"),
    ]:
        keys = list(zip(ytd[col_game], ytd[col_team]))
        expected = adv_side.reindex(keys).to_numpy(dtype=float)
        actual = pd.to_numeric(ytd[col_ml], errors="coerce").to_numpy(dtype=float)

        comparable = ~(np.isnan(expected) | np.isnan(actual))
        checks += int(comparable.sum())
        bad = comparable & (expected != actual)
        mismatches += int(bad.sum())
        for i in np.flatnonzero(bad)[:20]:
            mismatch_rows.append({
                "side": label,
                "newGameID": int(ytd[col_game].iloc[i]),
                "team": str(ytd[col_team].iloc[i]),
                "analysis_file": float(actual[i]),
                "crosscheck_file": float(expected[i]),
            })

    report["moneyline_crosscheck"] = {
        "lines_compared": checks,
        "mismatches": mismatches,
        "match_rate_pct": round(100.0 * (checks - mismatches) / checks, 6),
        "examples": mismatch_rows,
    }
    if mismatches:
        failures.append(f"{mismatches} moneyline mismatches")

    # ------------------------------------------------------------------
    # Check 2: schedule integrity
    # ------------------------------------------------------------------
    counts = ytd.groupby("slugSeason").size().to_dict()
    schedule = {}
    for season, expected_n in EXPECTED_SCHEDULE.items():
        got = int(counts.get(season, 0))
        schedule[season] = {"expected": expected_n, "found": got,
                            "ok": got == expected_n}
        if got != expected_n:
            failures.append(f"{season}: expected {expected_n}, found {got}")
    report["schedule"] = schedule
    report["schedule_all_ok"] = all(v["ok"] for v in schedule.values())
    report["total_games"] = int(len(ytd))

    # ------------------------------------------------------------------
    # Check 3: outcome integrity
    # ------------------------------------------------------------------
    outcomes = ytd["outcomeGame.team1"].astype(str).str.upper().str[0]
    valid_outcome = outcomes.isin(["W", "L"])
    report["outcomes"] = {
        "rows": int(len(ytd)),
        "valid_W_or_L": int(valid_outcome.sum()),
        "invalid": int((~valid_outcome).sum()),
    }
    if (~valid_outcome).any():
        failures.append(f"{(~valid_outcome).sum()} invalid outcome codes")

    adv_win = (adv_reg[["newGameID", "slugTeam", "isWin"]]
               .drop_duplicates(subset=["newGameID", "slugTeam"])
               .set_index(["newGameID", "slugTeam"])["isWin"])
    keys = list(zip(ytd["newGameID"], ytd["slugTeam"]))
    expected_win = adv_win.reindex(keys)
    expected_win = expected_win.map(
        lambda v: np.nan if pd.isna(v) else float(bool(v) if not isinstance(v, str)
                                                  else v.strip().upper() in
                                                  ("TRUE", "T", "1", "W"))).to_numpy()
    actual_win = (outcomes == "W").astype(float).to_numpy()
    comparable = ~np.isnan(expected_win)
    outcome_mismatches = int((comparable & (expected_win != actual_win)).sum())
    report["outcome_crosscheck"] = {
        "outcomes_compared": int(comparable.sum()),
        "mismatches": outcome_mismatches,
    }
    if outcome_mismatches:
        failures.append(f"{outcome_mismatches} outcome mismatches")

    # ------------------------------------------------------------------
    # Missing data profile
    # ------------------------------------------------------------------
    ml1 = pd.to_numeric(ytd["teamML.team1"], errors="coerce")
    ml2 = pd.to_numeric(ytd["oppML.team1"], errors="coerce")
    report["missing_moneylines"] = int((ml1.isna() | ml2.isna()).sum())

    report["passed"] = len(failures) == 0
    report["failures"] = failures

    with open(os.path.join(RESULTS_DIR, "verification_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    # ------------------------------------------------------------------
    mc = report["moneyline_crosscheck"]
    print("=" * 68)
    print("DATA VERIFICATION")
    print("=" * 68)
    print(f"Check 1  moneylines cross-validated : {mc['lines_compared']:,}")
    print(f"         mismatches                 : {mc['mismatches']}")
    print(f"         match rate                 : {mc['match_rate_pct']:.4f}%")
    print()
    print("Check 2  schedule integrity")
    for season, v in schedule.items():
        flag = "ok" if v["ok"] else "MISMATCH"
        print(f"         {season}  expected {v['expected']:>4}  "
              f"found {v['found']:>4}   {flag}")
    print(f"         total games                : {report['total_games']:,}")
    print()
    oc = report["outcome_crosscheck"]
    print(f"Check 3  outcomes compared          : {oc['outcomes_compared']:,}")
    print(f"         mismatches                 : {oc['mismatches']}")
    print(f"         invalid outcome codes      : {report['outcomes']['invalid']}")
    print()
    print(f"Missing moneylines in source        : {report['missing_moneylines']}")
    print()
    print("RESULT: " + ("PASSED" if report["passed"] else "FAILED"))
    for f_ in failures:
        print("  - " + f_)
    print("=" * 68)

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
