#!/bin/bash
# HoVer necrosis kill-switch — overnight guarded pipeline: Step 1 (run) -> Steps 2-4 (analysis).
# Launch:  caffeinate -dims bash run_step1_full.sh   (backgrounded, tee'd by the launcher)
set -o pipefail
cd "$(dirname "$0")"                      # scratch/hover_probe
SCRATCH_PY=".venv/bin/python"
MAIN_PY="/Users/neeldankar/Desktop/gepa-project/.venv/bin/python"

echo "=================================================================="
echo "NECROSIS STEP 1 pipeline start: $(date)"
echo "=================================================================="

echo ">>> STEP 1: lean mm~300 GEPA run + full capture (scratch venv)"
"$SCRATCH_PY" necrosis_run.py
RC=$?
if [ $RC -ne 0 ]; then
  echo ""
  echo "=================================================================="
  echo "=== STEP 1 FAILED (exit $RC) at $(date) — analysis NOT run, no retry ==="
  echo "=== Fix and resume manually. Do not blind-retry (budget guard).    ==="
  echo "=================================================================="
  exit $RC
fi
echo ">>> STEP 1 OK: $(date)"

echo ""
echo ">>> STEPS 2-4: necrosis analysis on the dumps (main .venv, \$0)"
"$MAIN_PY" necrosis_analysis.py necrosis
RC=$?
if [ $RC -ne 0 ]; then
  echo ""
  echo "=== STEPS 2-4 FAILED (exit $RC) — run completed but analysis errored. ==="
  echo "=== Dumps are safe in necrosis/; re-run necrosis_analysis.py to retry. ==="
  exit $RC
fi

echo ""
echo "=================================================================="
echo "NECROSIS PIPELINE COMPLETE: $(date)"
echo "deliverable: scratch/hover_probe/necrosis_killswitch.md"
echo "=================================================================="
