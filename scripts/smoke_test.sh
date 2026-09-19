#!/usr/bin/env bash
# ClaimSaathi Shell Smoke Test Runner
set -e

BASE_URL="${1:-http://localhost:8000}"

echo "============================================================"
echo " ClaimSaathi Smoke Test -> ${BASE_URL}"
echo "============================================================"

python3 scripts/smoke_test.py "${BASE_URL}" || python scripts/smoke_test.py "${BASE_URL}"
