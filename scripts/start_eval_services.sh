#!/bin/bash
# start_eval_services.sh — Start multiple eval service instances from mapping file.
#
# Usage:
#   bash scripts/start_eval_services.sh eval_env_mapping.json [--log-dir ./logs]
#
# Each environment defined in the mapping gets its own eval_service.py process
# running in the specified conda environment on the specified port.
# Processes run in background; PIDs are saved to <log_dir>/eval_service_pids.txt.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

MAPPING_FILE="${1:?Usage: $0 <eval_env_mapping.json> [--log-dir DIR]}"
LOG_DIR="${3:-${PROJECT_DIR}/eval_logs}"

if [ ! -f "$MAPPING_FILE" ]; then
    echo "ERROR: Mapping file not found: $MAPPING_FILE"
    exit 1
fi

mkdir -p "$LOG_DIR"
PID_FILE="$LOG_DIR/eval_service_pids.txt"
> "$PID_FILE"  # truncate

echo "=== Starting Eval Services from $MAPPING_FILE ==="
echo "Log directory: $LOG_DIR"
echo ""

# Parse environments from JSON using Python (available in conda)
ENV_LIST=$(python3 -c "
import json, sys
m = json.load(open('$MAPPING_FILE'))
for name, cfg in m['environments'].items():
    print(f\"{name} {cfg['conda_env']} {cfg['port']}\")
")

while IFS=' ' read -r ENV_NAME CONDA_ENV PORT; do
    LOG_FILE="$LOG_DIR/eval_service_${ENV_NAME}_${PORT}.log"
    echo "Starting [$ENV_NAME]: conda=$CONDA_ENV port=$PORT log=$LOG_FILE"

    if ! command -v conda >/dev/null 2>&1; then
        echo "ERROR: conda is required to start eval environment '$CONDA_ENV'."
        exit 1
    fi

    nohup conda run -n "$CONDA_ENV" python "$PROJECT_DIR/eval_service.py" --port "$PORT" \
        > "$LOG_FILE" 2>&1 &

    PID=$!
    echo "$ENV_NAME $CONDA_ENV $PORT $PID" >> "$PID_FILE"
    echo "  PID=$PID"

done <<< "$ENV_LIST"

echo ""
echo "Waiting for services to become healthy..."
sleep 3

ALL_OK=true
while IFS=' ' read -r ENV_NAME CONDA_ENV PORT PID; do
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "  [$ENV_NAME] FAILED — process $PID not running. Check $LOG_DIR/eval_service_${ENV_NAME}_${PORT}.log"
        ALL_OK=false
        continue
    fi

    HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/health" 2>/dev/null || echo "000")
    if [ "$HEALTH" = "200" ]; then
        echo "  [$ENV_NAME] OK — port $PORT, PID $PID"
    else
        echo "  [$ENV_NAME] NOT READY — port $PORT, HTTP $HEALTH. Check log."
        ALL_OK=false
    fi
done < "$PID_FILE"

echo ""
if [ "$ALL_OK" = true ]; then
    echo "All eval services started successfully."
else
    echo "WARNING: Some services failed to start. Check logs in $LOG_DIR/"
fi
echo "PID file: $PID_FILE"
echo ""
echo "To stop all services:"
echo "  awk '{print \$4}' $PID_FILE | xargs kill"
