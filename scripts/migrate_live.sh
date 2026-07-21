#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${CONFIG_ROOT:-/config}"
SHARE="${SHARE_ROOT:-/share}"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
MIGRATION_DIR="$SHARE/se_controller_migration_$STAMP"
ENV_FILE="$MIGRATION_DIR/site_config.env"
REPORT="$MIGRATION_DIR/migration_report.txt"

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$REPORT"; }

wait_for_core() {
  python3 - <<'PY'
import os, time, urllib.request
api = os.environ.get("HA_API_URL", "http://supervisor/core/api").rstrip("/")
token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
deadline = time.monotonic() + 300
while time.monotonic() < deadline:
    try:
        req = urllib.request.Request(api + "/", headers={"Authorization": f"Bearer {token}"})
        with urllib.request.urlopen(req, timeout=10) as response:
            response.read()
        print("Home Assistant API erreichbar.")
        raise SystemExit(0)
    except Exception:
        time.sleep(5)
raise SystemExit("Home Assistant API nach 300 Sekunden nicht erreichbar.")
PY
}

rollback_and_restart() {
  backup="$(cat "$SHARE/se_controller_last_backup.txt" 2>/dev/null || true)"
  log "Fehler erkannt. Rollback: $backup"
  if [ -n "$backup" ]; then
    bash "$ROOT/scripts/rollback.sh" "$backup" || true
    ha core restart || true
  fi
  exit 2
}

mkdir -p "$MIGRATION_DIR"
: >"$REPORT"

log "Controller-Master wird ausgeschaltet."
python3 "$ROOT/scripts/apply_site_config.py" --master-off-only

log "Private Site-Konfiguration wird aus aktuellen Live-Werten erzeugt."
python3 "$ROOT/scripts/export_live_site_config.py" "$ENV_FILE"
chmod 600 "$ENV_FILE"

log "RC2 wird mit vollständigem Backup installiert."
bash "$ROOT/scripts/install_package.sh"

log "Home Assistant wird neu gestartet."
if ! ha core restart; then
  rollback_and_restart
fi
if ! wait_for_core; then
  rollback_and_restart
fi
sleep 20

log "Site-Konfiguration wird angewendet; Master bleibt AUS."
if ! python3 "$ROOT/scripts/apply_site_config.py" "$ENV_FILE"; then
  rollback_and_restart
fi

sleep 30
log "Erstprüfungen starten."
if ! bash "$ROOT/scripts/run_first_checks.sh"; then
  rollback_and_restart
fi

log "MIGRATION=PASS"
log "Controller-Master: AUS"
log "Site-Konfiguration: $ENV_FILE"
log "Backup: $(cat "$SHARE/se_controller_last_backup.txt")"
log "Keine fremde Automation wurde gelöscht oder deaktiviert."
