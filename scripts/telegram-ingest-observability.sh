#!/usr/bin/env bash
set -euo pipefail

LOG_DIR=/tmp/openclaw
LATEST=$(ls -1t "$LOG_DIR"/openclaw-*.log 2>/dev/null | head -n 1 || true)
if [[ -z "${LATEST}" ]]; then
  echo "NO_LOGS: no openclaw logs found in ${LOG_DIR}"
  exit 1
fi

echo "Using log: ${LATEST}"

getfile_errors=$(grep -Ei "telegram|getfile|file too big|downloadAndSaveTelegramFile|media" "$LATEST" | tail -n 50 || true)

if [[ -z "${getfile_errors}" ]]; then
  echo "OK: no recent Telegram ingest/getFile errors detected in last sample"
else
  echo "RECENT_TELEGRAM_INGEST_SIGNALS:"
  echo "${getfile_errors}"
fi
