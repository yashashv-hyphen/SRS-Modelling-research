#!/usr/bin/env bash
# Regenerate every computed chart in docs/working-paper.html into paper/figures/out/.
# Run from anywhere with the project's Python environment active.
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python}"
for s in sweeps.py data_sweeps_dp.py data_flat_market.py data_volatile_path.py data_fig7.py \
         gen_charts.py gen_main.py gen_crossover_lines.py gen_fig7_corrected.py gen_final_three.py; do
  echo "== $s"; "$PY" "$s"
done
