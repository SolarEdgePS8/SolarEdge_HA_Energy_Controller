#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${CONFIG_ROOT:-/config}"
SHARE="${SHARE_ROOT:-/share}"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
BACKUP="$SHARE/se_controller_backup_$STAMP"
ACTIONS="$BACKUP/backup_actions.tsv"
RUNTIME_MANIFEST=".se_controller_runtime_manifest.json"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

rollback_now() {
  code=$?
  trap - ERR
  log "Installation fehlgeschlagen. Automatischer Rollback."
  bash "$ROOT/scripts/rollback.sh" "$BACKUP" || true
  exit "$code"
}

mkdir -p "$BACKUP/content" "$CONFIG/packages"
: >"$ACTIONS"
trap rollback_now ERR

SE_CONTROLLER_DRY_RUN="${SE_CONTROLLER_DRY_RUN:-0}" \
  python3 "$ROOT/scripts/apply_site_config.py" --master-off-only

copy_with_backup() {
  src="$1"; dst="$2"; rel="$3"
  mkdir -p "$(dirname "$dst")" "$BACKUP/content/$(dirname "$rel")"
  if [ -f "$dst" ]; then
    cp "$dst" "$BACKUP/content/$rel"
    printf 'RESTORE\t%s\n' "$rel" >>"$ACTIONS"
  else
    printf 'REMOVE\t%s\n' "$rel" >>"$ACTIONS"
  fi
  cp "$src" "$dst"
}

for src in "$ROOT"/package/*.yaml; do
  name="$(basename "$src")"
  copy_with_backup "$src" "$CONFIG/packages/$name" "packages/$name"
done

for src in "$ROOT"/scripts/runtime/*.py "$ROOT"/audit/runtime/*.py; do
  [ -f "$src" ] || continue
  name="$(basename "$src")"
  copy_with_backup "$src" "$CONFIG/$name" "$name"
  chmod +x "$CONFIG/$name"
done

# Runtime-Manifest selbst ist ebenfalls rollbackfähig.
if [ -f "$CONFIG/$RUNTIME_MANIFEST" ]; then
  cp "$CONFIG/$RUNTIME_MANIFEST" "$BACKUP/content/$RUNTIME_MANIFEST"
  printf 'RESTORE\t%s\n' "$RUNTIME_MANIFEST" >>"$ACTIONS"
else
  printf 'REMOVE\t%s\n' "$RUNTIME_MANIFEST" >>"$ACTIONS"
fi

python3 - "$ROOT" "$CONFIG/$RUNTIME_MANIFEST" <<'PY'
from pathlib import Path
import hashlib
import json
import sys

root = Path(sys.argv[1])
target = Path(sys.argv[2])
installed = {}
for path in sorted((root / "package").glob("*.yaml")):
    installed[f"packages/{path.name}"] = hashlib.sha256(path.read_bytes()).hexdigest()
for directory in (root / "scripts" / "runtime", root / "audit" / "runtime"):
    for path in sorted(directory.glob("*.py")):
        installed[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()

version = "0.1.0-rc.3"
source_commit = None
release_manifest = root / "validation" / "release_manifest.json"
if release_manifest.is_file():
    release_data = json.loads(release_manifest.read_text(encoding="utf-8"))
    version = str(release_data.get("version") or version)
    source_commit = release_data.get("source_commit")

target.write_text(json.dumps({
    "project": "SolarEdge_HA_Energy_Controller",
    "version": version,
    "source_commit": source_commit,
    "installed_files": installed,
}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
PY

printf '%s\n' "$BACKUP" >"$SHARE/se_controller_last_backup.txt"

ha core check

trap - ERR
log "Installationsdateien und HA-Konfiguration geprüft."
log "Backup: $BACKUP"
log "Controller-Master bleibt AUS."
