#!/usr/bin/env bash
set -euo pipefail

echo "[MAGI-V2] Preflight starting..."

MODELS=$(openclaw models list 2>/dev/null || true)
if [[ -z "$MODELS" ]]; then
  echo "FAIL: unable to read model inventory"
  exit 2
fi

echo "$MODELS" | sed -n '1,120p'

if echo "$MODELS" | grep -Eiq '(^|[[:space:]])xai/|grok'; then
  echo "OK: Grok/xAI model appears available in OpenClaw model list"
else
  echo "BLOCKED: No Grok/xAI model currently available in OpenClaw model list"
  echo "Action needed: configure xAI provider credentials (or OpenRouter Grok route), then rescan/list models"
  exit 3
fi

echo "[MAGI-V2] Preflight passed."
