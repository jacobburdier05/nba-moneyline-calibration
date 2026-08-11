"""
Stage 1: build the analysis dataset.

Input  : data/raw/nba_moneylines.csv  (from github.com/guydotan/ucla-thesis)
Output : data/processed/games.csv          (one row per game, analysis-ready)

Applies the exclusions fixed in the frozen analysis plan:
  * games with a missing moneyline on either side
  * pick'em games, where the two sides carry identical moneylines and
    neither side is a favorite

Run:  python src/build_dataset.py
"""

import json
import os

import numpy as np
import pandas as pd

from odds import (american_to_raw_prob, devig_proportional, overround,
                  payout_multiple, breakeven_requirement)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw", "nba_moneylines.csv")
OUT_DIR = os.path.join(ROOT, "data", "processed")
RESULTS_DIR = os.path.join(ROOT, "results")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)

    df = pd.read_csv(RAW)
    n_source = len(df)

    g = pd.DataFrame({
        "season": df["slugSeason"],
        "date": df["dateGame"],
        "team1": df["slugTeam"],
        "team2": df["slugOpp"],
        "ml1": pd.to_numeric(df["teamML.team1"], errors="coerce"),
        "ml2": pd.to_numeric(df["oppML.team1"], errors="coerce"),
        "team1_won": (df["outcomeGame.team1"].astype(str).str.upper()
                      .str[0] == "W").astype(int),
    })

    # --- exclusion 1: missing moneyline on either side ---------------------
    missing_ml = g["ml1"].isna() | g["ml2"].isna() | (g["ml1"] == 0) | (g["ml2"] == 0)
    n_missing = int(missing_ml.sum())
    g = g.loc[~missing_ml].copy()

    # --- probabilities -----------------------------------------------------
    g["p_raw_1"] = american_to_raw_prob(g["ml1"].to_numpy())
    g["p_raw_2"] = american_to_raw_prob(g["ml2"].to_numpy())
    g["overround"] = overround(g["p_raw_1"], g["p_raw_2"])
    g["p_vf_1"], g["p_vf_2"] = devig_proportional(g["p_raw_1"], g["p_raw_2"])

    # --- exclusion 2: pick'em, neither side is a favorite -----------------
    pickem = np.isclose(g["p_vf_1"], g["p_vf_2"])
    n_pickem = int(pickem.sum())
    g = g.loc[~pickem].copy()

    # --- favorite side ----------------------------------------------------
    fav_is_1 = g["p_vf_1"] > g["p_vf_2"]
    g["fav_team"] = np.where(fav_is_1, g["team1"], g["team2"])
    g["fav_ml"] = np.where(fav_is_1, g["ml1"], g["ml2"])
    g["dog_ml"] = np.where(fav_is_1, g["ml2"], g["ml1"])
    g["p_raw_fav"] = np.where(fav_is_1, g["p_raw_1"], g["p_raw_2"])
    g["p_raw_dog"] = np.where(fav_is_1, g["p_raw_2"], g["p_raw_1"])
    g["p_vf_fav"] = np.where(fav_is_1, g["p_vf_1"], g["p_vf_2"])
    g["p_vf_dog"] = np.where(fav_is_1, g["p_vf_2"], g["p_vf_1"])
    g["fav_won"] = np.where(fav_is_1, g["team1_won"], 1 - g["team1_won"]).astype(int)

    # --- economics ---------------------------------------------------------
    g["fav_payout"] = payout_multiple(g["fav_ml"].to_numpy())
    g["dog_payout"] = payout_multiple(g["dog_ml"].to_numpy())
    g["breakeven_pp"] = breakeven_requirement(g["p_raw_fav"], g["p_vf_fav"])

    g = g.reset_index(drop=True)
    out_path = os.path.join(OUT_DIR, "games.csv")
    g.to_csv(out_path, index=False)

    profile = {
        "source_rows": n_source,
        "excluded_missing_moneyline": n_missing,
        "excluded_pickem": n_pickem,
        "analysis_games": int(len(g)),
        "seasons": int(g["season"].nunique()),
        "mean_overround_pct": round(float(g["overround"].mean() * 100), 4),
        "p_vf_fav_min": round(float(g["p_vf_fav"].min()), 4),
        "p_vf_fav_max": round(float(g["p_vf_fav"].max()), 4),
        "games_by_season": {str(k): int(v) for k, v in
                            g["season"].value_counts().sort_index().items()},
    }
    with open(os.path.join(RESULTS_DIR, "dataset_profile.json"), "w") as f:
        json.dump(profile, f, indent=2)

    print(f"source rows                : {n_source}")
    print(f"excluded, missing moneyline: {n_missing}")
    print(f"excluded, pick'em          : {n_pickem}")
    print(f"analysis games             : {len(g)}")
    print(f"seasons                    : {g['season'].nunique()}")
    print(f"mean overround             : {g['overround'].mean() * 100:.2f}%")
    print(f"favorite vig-free range   : {g['p_vf_fav'].min():.3f} to "
          f"{g['p_vf_fav'].max():.3f}")
    print(f"written                    : {out_path}")


if __name__ == "__main__":
    main()
