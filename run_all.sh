#!/usr/bin/env bash
# Full replication. Runtime is about six minutes.
#
#   bash run_all.sh
#
# Verification runs first and halts the pipeline if it fails.
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "STEP 1 of 10  verify the data layer"
python src/verify_data.py

echo
echo "STEP 2 of 10  build the analysis dataset"
python src/build_dataset.py

echo
echo "STEP 3 of 10  confirmatory analyses"
python src/primary_analysis.py

echo
echo "STEP 4 of 10  robustness analyses"
python src/robustness.py

echo
echo "STEP 5 of 10  figures"
python src/figures.py

echo
echo "STEP 6 of 10  robustness: vig-removal rules and dependence structures"
python src/normalization_robustness.py
python src/dependence_robustness.py

echo
echo "STEP 7 of 10  power curve"
python src/power_curve.py

echo
echo "STEP 8 of 10  Appendix A: verify the Shin equivalence proof"
python src/shin_equivalence_proof.py

echo
echo "STEP 9 of 10  simulated null for the flat-stake return intervals"
python src/return_simulation.py

echo
echo "STEP 10 of 10  equivalence test and fixed-sample normalization"
python src/equivalence_and_fixed_sample.py

echo
echo "Done. Results in results/, figures in figures/."
