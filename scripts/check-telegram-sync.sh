#!/usr/bin/env bash
set -euo pipefail

# Lightweight sync check for NERV <-> Telegram flow
# Passes if gateway is running and telegram bridge appears healthy.

status_txt=$(openclaw status 2>/dev/null || true)
if [[ -z "${status_txt}" ]]; then
  echo "FAIL: openclaw status unavailable"
  exit 1
fi

if ! echo "${status_txt}" | grep -qi "gateway"; then
  echo "FAIL: cannot confirm gateway status"
  exit 2
fi

if ! echo "${status_txt}" | grep -Eqi "telegram|@.*bot"; then
  echo "WARN: telegram line not found in status output"
  echo "Manual check needed"
  exit 3
fi

echo "OK: status output includes gateway + telegram indicators"
