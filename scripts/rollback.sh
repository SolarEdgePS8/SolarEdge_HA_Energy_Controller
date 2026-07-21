#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${CONFIG_ROOT:-/config}"
SHARE="${SHARE_ROOT:-/share}"
BACKUP="${1:-$(cat "$SHARE/se_controller_last_backup.txt" 2>/dev/null || true)}"
ACTIONS="$BACKUP/backup_actions.tsv"

# shellcheck source=scripts/lib/ha_environment.sh
. "$ROOT/scripts/lib/ha_environment.sh"

[ -d "$BACKUP" ] || { echo "Backup fehlt: $BACKUP"; exit 2; }
[ -f "$ACTIONS" ] || { echo "Backup-Aktionsliste fehlt: $ACTIONS"; exit 2; }

# Best effort: Vor dem Zurückkopieren keine neuen Writer-Zugriffe zulassen.
if ha_api_token_available || [ "${SE_CONTROLLER_DRY_RUN:-0}" = "1" ]; then
  SE_CONTROLLER_DRY_RUN="${SE_CONTROLLER_DRY_RUN:-0}" \
    python3 "$ROOT/scripts/apply_site_config.py" --master-off-only || true
else
  echo "WARN: Kein HA-API-Token verfügbar; Master konnte beim Rollback nicht per API ausgeschaltet werden."
fi

while IFS="$(printf '\t')" read -r action rel; do
  [ -n "$rel" ] || continue
  dst="$CONFIG/$rel"
  case "$action" in
    RESTORE)
      src="$BACKUP/content/$rel"
      [ -f "$src" ] || { echo "Backup-Datei fehlt: $src"; exit 2; }
      mkdir -p "$(dirname "$dst")"
      cp "$src" "$dst"
      ;;
    REMOVE)
      rm -f "$dst"
      ;;
    *)
      echo "Unbekannte Rollback-Aktion: $action"
      exit 2
      ;;
  esac
done <"$ACTIONS"

run_ha_config_check
echo "Rollback vollständig ausgeführt. Controller-Master bleibt AUS beziehungsweise muss ohne API-Token manuell AUS bleiben."
