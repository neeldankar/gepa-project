#!/bin/bash
# Stage-1 Phase-2 supervisor: seeds 1-7, max 3 concurrent (16GB RAM, in-memory BM25 load).
# DONE/FAILED markers per seed. NO auto-relaunch on failure. Isolation: each seed writes only
# under stage1_seed<N>/ (verified). Launch: nohup bash run_seeds.sh > logs/supervisor.log 2>&1 &
set -u
cd "$(dirname "$0")"
PY=../hover_probe/.venv/bin/python
MAXC=3
SEEDS="1 2 3 4 5 6 7"
mkdir -p logs markers
echo "=== supervisor start $(date +%F_%H:%M:%S)  MAXC=$MAXC  seeds: $SEEDS ==="
for s in $SEEDS; do
  # throttle: block until fewer than MAXC seed jobs are running
  while [ "$(jobs -rp | wc -l | tr -d ' ')" -ge "$MAXC" ]; do sleep 10; done
  (
    "$PY" -u stage1_run.py --seed "$s" > "logs/seed${s}.log" 2>&1
    rc=$?
    if [ "$rc" -eq 0 ] && [ -f "stage1_seed${s}/run_summary.json" ]; then
      touch "markers/seed${s}.DONE"
      echo "seed $s DONE $(date +%H:%M:%S)"
    else
      echo "rc=$rc $(date +%F_%H:%M:%S)" > "markers/seed${s}.FAILED"
      echo "seed $s FAILED rc=$rc $(date +%H:%M:%S)"
    fi
  ) &
  echo "launched seed $s (pid $!) $(date +%H:%M:%S)"
  sleep 3
done
wait
echo "=== supervisor complete $(date +%F_%H:%M:%S) ==="
touch markers/ALL.DONE
