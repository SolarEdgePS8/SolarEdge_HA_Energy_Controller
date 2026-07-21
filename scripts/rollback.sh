#!/usr/bin/env bash
set -eu

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONFIG="${CONFIG_ROOT:-/config}"
SHARE="${SHARE_ROOT:-/share}"
BACKUP="${1:-$(cat "$SHARE/se_controller_last_backup.txt" 2>/dev/null || true)}"
ACTIONS="$BACKUP/backup_actions.tsv"

[ -d "$BACKUP" ] || { echo "Backup fehlt: $BACKUP"; exit 2; }
[ -f "$ACTIONS" ] || { echo "Backup-Aktionsliste fehlt: $ACTIONS"; exit 2; }

SE_CONTROLLER_DRY_RUN="${SE_CONTROLLER_DRY_RUN:-0}" \
  python3 "$ROOT/scripts/apply_site_config.py" --master-off-only || true

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

ha core check
echo "Rollback vollständig ausgeführt. Controller-Master bleibt AUS."
