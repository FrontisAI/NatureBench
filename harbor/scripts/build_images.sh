#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HARBOR_DIR="$(dirname "$SCRIPT_DIR")"

echo "Building naturebench-base:v3 ..."
docker build \
  -t naturebench-base:v3 \
  "$HARBOR_DIR/images/naturebench-base"

echo "Building naturebench-eval:main ..."
docker build \
  -t naturebench-eval:main \
  "$HARBOR_DIR/images/naturebench-eval-main"

echo "Built naturebench-base:v3 and naturebench-eval:main."
