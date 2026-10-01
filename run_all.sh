#!/usr/bin/env bash
# Full replication. Runtime is about six minutes.
#
#   bash run_all.sh
#
# Verification runs first and halts the pipeline if it fails.
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "STEP 1 of 11  verify the data layer"
python src/verify_data.py

echo
echo "STEP 2 of 11  build the analysis dataset"
python src/build_dataset.py

echo
echo "STEP 3 of 11  confirmatory analyses"
python src/primary_analysis.py

echo
echo "STEP 4 of 11  robustness analyses"
python src/robustness.py

echo
echo "STEP 5 of 11  figures"
python src/figures.py

echo
echo "STEP 6 of 11  robustness: vig-removal rules and dependence structures"
python src/normalization_robustness.py
python src/dependence_robustness.py

echo
echo "STEP 7 of 11  power curve"
python src/power_curve.py

echo
echo "STEP 8 of 11  supplement S1: check the Shin equivalence against every game"
python src/shin_equivalence_proof.py

echo
echo "STEP 9 of 11  simulated null for the flat-stake return intervals"
python src/return_simulation.py

echo
echo "STEP 10 of 11  equivalence test and fixed-sample normalization"
python src/equivalence_and_fixed_sample.py

echo
echo "STEP 11 of 11  figures for the conference abstract"
python src/abstract_figures.py

echo
echo "Done. Results in results/, figures in figures/."
