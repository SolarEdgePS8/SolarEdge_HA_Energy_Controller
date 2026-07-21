#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${CONFIG_ROOT:-/config}"

python3 "$ROOT/audit/readonly_audit.py" "$ROOT" --release-gate
ha core check
python3 "$CONFIG/se_controller_runtime_checker.py" \
  --expect-master-off \
  --report "${SHARE_ROOT:-/share}/se_controller_runtime_check.json"

if ! python3 "$ROOT/scripts/check_external_writer_conflicts.py" "$CONFIG"; then
  echo "FEHLER: Externer Writer-Konflikt auf einem aktiv gemappten Controller-Ziel."
  exit 2
fi

echo "Erstprüfungen PASS. Controller-Master bleibt AUS."
