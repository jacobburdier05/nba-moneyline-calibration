"""
Optional: re-download the full upstream source files.

The two CSVs in data/raw/ are column subsets of files published in the
repository accompanying Dotan (2020). Only the columns this analysis uses
were kept, so the replication package stays small enough to clone quickly.
No values were altered.

This script downloads the complete originals into data/raw/upstream/ so
anyone can confirm the subsetting changed nothing.

Run:  python src/fetch_source_data.py
"""

import hashlib
import os
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEST = os.path.join(ROOT, "data", "raw", "upstream")

BASE = "https://raw.githubusercontent.com/guydotan/ucla-thesis/master/data/"
FILES = {
    "new_nba_ytd_matchup.csv": ("nba_moneylines.csv",
                                ["slugSeason", "newGameID", "idGame", "slugTeam",
                                 "slugOpp", "slugMatchup", "dateGame",
                                 "outcomeGame.team1", "teamML.team1",
                                 "oppML.team1"]),
    "nba_adv_complete.csv": ("nba_adv_crosscheck.csv",
                             ["newGameID", "slugSeason", "slugTeam", "teamML",
                              "oppML", "isWin", "typeSeason", "dateGame"]),
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    os.makedirs(DEST, exist_ok=True)
    all_ok = True

    for upstream_name, (local_name, cols) in FILES.items():
        url = BASE + upstream_name
        dest = os.path.join(DEST, upstream_name)

        print(f"\n{upstream_name}")
        if os.path.exists(dest):
            print("  already downloaded")
        else:
            print(f"  downloading {url}")
            urllib.request.urlretrieve(url, dest)
        print(f"  sha256 {sha256(dest)}")

        full = pd.read_csv(dest, low_memory=False)
        local = pd.read_csv(os.path.join(ROOT, "data", "raw", local_name),
                            low_memory=False)

        if len(full) != len(local):
            print(f"  ROW COUNT MISMATCH: upstream {len(full)}, local {len(local)}")
            all_ok = False
            continue

        identical = full[cols].reset_index(drop=True).equals(
            local[cols].reset_index(drop=True))
        print(f"  rows {len(full):,}, columns compared {len(cols)}")
        print(f"  subset identical to upstream: {identical}")
        all_ok &= identical

    print("\n" + ("VERIFIED: the local subsets match upstream exactly."
                  if all_ok else "MISMATCH: see above."))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
