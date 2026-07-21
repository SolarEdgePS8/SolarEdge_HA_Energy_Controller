#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python3 "$ROOT/audit/readonly_audit.py" "$ROOT" --release-gate
if [ -f "$ROOT/validation/release_manifest.json" ]; then
  python3 "$ROOT/audit/manifest_audit.py" "$ROOT"
fi
