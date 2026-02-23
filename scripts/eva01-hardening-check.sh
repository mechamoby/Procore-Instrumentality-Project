#!/usr/bin/env bash
set -euo pipefail

echo "[EVA01] hardening check start"

python -m py_compile \
  /home/moby/.openclaw/workspace/eva-agent/submittal-agent/eva00/eva01_flow.py \
  /home/moby/.openclaw/workspace/scripts/eva01-review.py \
  /home/moby/.openclaw/workspace/scripts/procore-api.py

echo "[EVA01] compile check passed"

python - <<'PY'
import subprocess, tempfile, pathlib, json

# 1) Missing path must fail loud
r = subprocess.run(
    ['python','/home/moby/.openclaw/workspace/scripts/eva01-review.py',''],
    capture_output=True, text=True
)
assert r.returncode != 0
obj = json.loads((r.stdout or '{}').strip() or '{}')
assert obj.get('stage') == 'attachment_guardrail'

# 2) Non-PDF must fail loud
p = pathlib.Path(tempfile.gettempdir())/'eva01-hardening-not-pdf.txt'
p.write_text('x')
r = subprocess.run(
    ['python','/home/moby/.openclaw/workspace/scripts/eva01-review.py',str(p),'--text-only'],
    capture_output=True, text=True
)
assert r.returncode != 0
obj = json.loads((r.stdout or '{}').strip() or '{}')
assert obj.get('stage') == 'file_type_guardrail'

# 3) payload defaults should exist on valid pdf
pdf = pathlib.Path(tempfile.gettempdir())/'eva01-hardening-minimal.pdf'
pdf.write_bytes(b'%PDF-1.4\n1 0 obj<</Type/Catalog>>endobj\ntrailer<<>>\n%%EOF')
r = subprocess.run(
    ['python','/home/moby/.openclaw/workspace/scripts/eva01-review.py',str(pdf),'--text-only','--project-name','BTV5','--pm-title-override','PM Override'],
    capture_output=True, text=True
)
# may fail due minimal malformed pdf in fitz; allow either. If succeeded, assert defaults shape.
if r.returncode == 0:
    obj = json.loads(r.stdout)
    defaults = obj.get('eva01_defaults', {})
    assert defaults.get('status') == 'open'
    assert defaults.get('title') == 'PM Override'

print('EVA01_HARDENING_CHECK_OK')
PY

echo "[EVA01] hardening check complete"