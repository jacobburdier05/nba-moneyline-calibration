#!/usr/bin/env bash
# Full replication. Runtime is about three minutes.
#
#   bash run_all.sh
#
# Verification runs first and halts the pipeline if it fails.
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "STEP 1 of 7  verify the data layer"
python src/verify_data.py

echo
echo "STEP 2 of 7  build the analysis dataset"
python src/build_dataset.py

echo
echo "STEP 3 of 7  confirmatory analyses"
python src/primary_analysis.py

echo
echo "STEP 4 of 7  robustness analyses"
python src/robustness.py

echo
echo "STEP 5 of 7  figures"
python src/figures.py

echo
echo "STEP 6 of 7  robustness: vig-removal rules and dependence structures"
python src/normalization_robustness.py
python src/dependence_robustness.py

echo
echo "STEP 7 of 7  power curve"
python src/power_curve.py

echo
echo "Done. Results in results/, figures in figures/."
