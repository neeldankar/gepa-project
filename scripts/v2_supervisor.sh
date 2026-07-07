#!/bin/bash
# Detached, self-resuming supervisor for batch_swap_v2_run.py.
# Survives laptop sleep + Claude-session drops (launched via nohup, reparented to launchd).
# Relaunches the run from its checkpoint if it dies unexpectedly; stops on clean completion
# or the in-script $55 spend tripwire. Waits for full process exit before each relaunch, so
# there is never more than one paying run at a time (no double-spend).
set -u
cd /Users/neeldankar/Desktop/gepa-project || exit 1
export HF_DATASETS_OFFLINE=1

SLOG=logs/batch_swap_v2_supervisor.log
RLOG=logs/batch_swap_v2_run.log
MAX_RESTARTS=40
i=0

ts() { date '+%Y-%m-%d %H:%M:%S'; }
echo "[$(ts)] supervisor start (pid $$)" >> "$SLOG"

while [ "$i" -lt "$MAX_RESTARTS" ]; do
  echo "[$(ts)] launch #$i" >> "$SLOG"
  caffeinate -dims .venv/bin/python scripts/batch_swap_v2_run.py >> "$RLOG" 2>&1
  rc=$?
  echo "[$(ts)] run exited rc=$rc" >> "$SLOG"

  # rc=2 => in-script $55 tripwire (children phase). Do NOT resume.
  if [ "$rc" -eq 2 ]; then
    echo "[$(ts)] SPEND TRIPWIRE — stopping, no resume." >> "$SLOG"; break
  fi
  # clean completion: script returns 0 and prints a DONE line at end of main()
  if [ "$rc" -eq 0 ] && tail -40 "$RLOG" | grep -q "^DONE"; then
    echo "[$(ts)] COMPLETE — all pairs done." >> "$SLOG"; break
  fi
  # rc=1 from a pairing-phase tripwire (sys.exit with message) also means overspend; stop.
  if [ "$rc" -eq 1 ] && tail -20 "$RLOG" | grep -qi "TRIPWIRE"; then
    echo "[$(ts)] pairing tripwire — stopping." >> "$SLOG"; break
  fi
  echo "[$(ts)] unexpected exit — resuming from checkpoint in 15s" >> "$SLOG"
  sleep 15
  i=$((i + 1))
done
echo "[$(ts)] supervisor exit after $i restart(s)" >> "$SLOG"
