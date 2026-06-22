#!/usr/bin/env bash
# Build naturebench-base:v3 if missing. Run from repo root:
#   bash scripts/ensure_naturebench_base.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
if docker image inspect naturebench-base:v3 >/dev/null 2>&1; then
  echo "naturebench-base:v3 already present."
  exit 0
fi
echo "Building naturebench-base:v3 from docker/Dockerfile.base ..."
docker build -t naturebench-base:v3 -f "${ROOT}/docker/Dockerfile.base" "${ROOT}/docker"
echo "Done."
