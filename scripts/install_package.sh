#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${CONFIG_ROOT:-/config}"
SHARE="${SHARE_ROOT:-/share}"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
BACKUP="$SHARE/se_controller_backup_$STAMP"
ACTIONS="$BACKUP/backup_actions.tsv"
RUNTIME_MANIFEST=".se_controller_runtime_manifest.json"
CONFIG_FILE="$CONFIG/configuration.yaml"
WATCHDOG_CONFIG="$ROOT/config/se_write_watchdog.yaml.example"

# shellcheck source=scripts/lib/ha_environment.sh
. "$ROOT/scripts/lib/ha_environment.sh"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }

rollback_with_code() {
  code="$1"
  trap - ERR INT TERM
  log "Installation fehlgeschlagen. Automatischer Rollback."
  bash "$ROOT/scripts/rollback.sh" "$BACKUP" || true
  exit "$code"
}

rollback_now() {
  rollback_with_code "$?"
}

[ -f "$CONFIG_FILE" ] || {
  echo "Home-Assistant-Konfiguration fehlt: $CONFIG_FILE" >&2
  exit 2
}
[ -f "$WATCHDOG_CONFIG" ] || {
  echo "Watchdog-Konfiguration fehlt: $WATCHDOG_CONFIG" >&2
  exit 2
}

mkdir -p "$BACKUP/content" "$CONFIG/packages" "$SHARE"
: >"$ACTIONS"
trap rollback_now ERR INT TERM

# Bestehende Installationen dürfen während des Updates nicht schreiben.
ensure_controller_master_off

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

# 18 portable Controller-Packages. Private Anlagenautomationen werden nicht kopiert.
for src in "$ROOT"/package/*.yaml; do
  name="$(basename "$src")"
  copy_with_backup "$src" "$CONFIG/packages/$name" "packages/$name"
done

# Runtime- und Audit-Dateien für Erstprüfung und Laufzeitdiagnose.
for src in "$ROOT"/scripts/runtime/*.py "$ROOT"/audit/runtime/*.py; do
  [ -f "$src" ] || continue
  name="$(basename "$src")"
  copy_with_backup "$src" "$CONFIG/$name" "$name"
  chmod +x "$CONFIG/$name"
done

# Read-only Write-Watchdog. Er erzeugt selbst keine SolarEdge-Schreibbefehle.
for src in "$ROOT"/custom_components/se_write_watchdog/*; do
  [ -f "$src" ] || continue
  name="$(basename "$src")"
  rel="custom_components/se_write_watchdog/$name"
  copy_with_backup "$src" "$CONFIG/$rel" "$rel"
done

# Terminal-Werkzeuge für Bericht und Live-Trace.
for src in "$ROOT"/tools/se_write_watchdog/*.sh; do
  [ -f "$src" ] || continue
  name="$(basename "$src")"
  rel="se_write_watchdog_tools/$name"
  copy_with_backup "$src" "$CONFIG/$rel" "$rel"
  chmod +x "$CONFIG/$rel"
done

# Der Custom Component benötigt genau einen Top-Level-Konfigurationsblock.
# Ein vorhandener Block wird bewusst nicht überschrieben.
if grep -Eq '^se_write_watchdog:[[:space:]]*$' "$CONFIG_FILE"; then
  log "Vorhandener se_write_watchdog:-Block bleibt unverändert."
else
  PATCHED_CONFIG="$BACKUP/configuration.yaml.patched"
  cp "$CONFIG_FILE" "$PATCHED_CONFIG"
  printf '\n# SolarEdge Charge-Limit Audit / Watchdog\n' >>"$PATCHED_CONFIG"
  cat "$WATCHDOG_CONFIG" >>"$PATCHED_CONFIG"
  copy_with_backup "$PATCHED_CONFIG" "$CONFIG_FILE" "configuration.yaml"
  log "Watchdog-Konfiguration in configuration.yaml ergänzt."
fi

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

for path in sorted((root / "custom_components" / "se_write_watchdog").glob("*")):
    if path.is_file():
        installed[f"custom_components/se_write_watchdog/{path.name}"] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

for path in sorted((root / "tools" / "se_write_watchdog").glob("*.sh")):
    installed[f"se_write_watchdog_tools/{path.name}"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()

version = "0.1.0-rc.4"
source_commit = None
release_manifest = root / "validation" / "release_manifest.json"
if release_manifest.is_file():
    release_data = json.loads(release_manifest.read_text(encoding="utf-8"))
    version = str(release_data.get("version") or version)
    source_commit = release_data.get("source_commit")

target.write_text(
    json.dumps(
        {
            "project": "SolarEdge_HA_Energy_Controller",
            "version": version,
            "source_commit": source_commit,
            "installed_files": installed,
        },
        indent=2,
        ensure_ascii=False,
    )
    + "\n",
    encoding="utf-8",
)
PY

printf '%s\n' "$BACKUP" >"$SHARE/se_controller_last_backup.txt"

# Ein Fehler innerhalb einer Shell-Funktion löst nicht in jeder Bash-Konstellation
# zuverlässig den ERR-Trap aus. Deshalb wird die zentrale HA-Prüfung explizit
# ausgewertet und bei Fehlern garantiert zurückgerollt.
if ! run_ha_config_check; then
  rollback_with_code 2
fi

trap - ERR INT TERM
log "Installationsdateien und Home-Assistant-Konfiguration geprüft."
log "Installiert: 18 Package-Dateien, 5 Runtime-/Audit-Dateien, 3 Watchdog-Dateien und 2 Watchdog-Tools."
log "Backup: $BACKUP"
log "Controller-Master bleibt AUS."
