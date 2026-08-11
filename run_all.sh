#!/usr/bin/env bash
# Full replication. Runtime is about one minute.
#
#   bash run_all.sh
#
# Verification runs first and halts the pipeline if it fails.
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "STEP 1 of 5  verify the data layer"
python src/verify_data.py

echo
echo "STEP 2 of 5  build the analysis dataset"
python src/build_dataset.py

echo
echo "STEP 3 of 5  confirmatory analyses"
python src/primary_analysis.py

echo
echo "STEP 4 of 5  robustness analyses"
python src/robustness.py

echo
echo "STEP 5 of 5  figures"
python src/figures.py

echo
echo "Done. Results in results/, figures in figures/."
