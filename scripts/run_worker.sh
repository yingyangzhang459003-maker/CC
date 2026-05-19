#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="$ROOT_DIR:${PYTHONPATH:-}"
mkdir -p logs data

CONFIG_PATH="${RADAR_CONFIG:-config/config.example.yaml}"
LOG_FILE="${RADAR_WORKER_LOG:-logs/worker.log}"

echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] starting Polymarket NVIDIA Event Radar worker with config=$CONFIG_PATH" | tee -a "$LOG_FILE"
python3.11 -m src.main loop --config "$CONFIG_PATH" 2>&1 | tee -a "$LOG_FILE"
