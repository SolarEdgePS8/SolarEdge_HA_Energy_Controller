#!/usr/bin/env bash
set -u
LOGDIR="/config/se_write_watchdog"
LINES="${1:-80}"

echo "============================================================"
echo " SolarEdge Write Watchdog Report"
echo " $(date -Iseconds 2>/dev/null || date)"
echo "============================================================"

if [ -f "$LOGDIR/latest.json" ]; then
  echo
  echo "--- Letztes Ereignis ---"
  if command -v jq >/dev/null 2>&1; then
    jq . "$LOGDIR/latest.json"
  else
    cat "$LOGDIR/latest.json"
  fi
else
  echo "Noch kein latest.json vorhanden. Läuft Home Assistant bereits mit dem Watchdog?"
fi

if [ -f "$LOGDIR/writer_scan.json" ]; then
  echo
  echo "--- Statisch gefundene mögliche Schreiber ---"
  if command -v jq >/dev/null 2>&1; then
    jq '{watched_entity,count,candidates:[.candidates[]|{file,classification,has_number_set_value,has_exact_target,has_mapping_helper}]}' "$LOGDIR/writer_scan.json"
  else
    cat "$LOGDIR/writer_scan.json"
  fi
fi

echo
echo "--- Letzte relevante Ereignisse (max. $LINES) ---"
FILES=$(ls -1 "$LOGDIR"/events-*.jsonl 2>/dev/null | tail -n 3 || true)
if [ -n "$FILES" ]; then
  if command -v jq >/dev/null 2>&1; then
    grep -hE '"event": "(write_intent|number_set_value_call|charge_limit_state_change|flapping_detected|evopt_mismatch|evopt_mismatch_cleared|watched_entity_mapping_changed)"' $FILES \
      | tail -n "$LINES" \
      | jq -c '{timestamp,event,target_entity,requested_value,current_value_at_call,old_value,new_value,allowed_writer,duplicate,roundtrip_detected,attributed,source,reasons,reason,intent}'
  else
    grep -hE '"event": "(write_intent|number_set_value_call|charge_limit_state_change|flapping_detected|evopt_mismatch|evopt_mismatch_cleared|watched_entity_mapping_changed)"' $FILES \
      | tail -n "$LINES"
  fi
else
  echo "Keine Ereignisdateien gefunden."
fi

echo
echo "Dateien:"
echo "  $LOGDIR/events-YYYY-MM-DD.jsonl"
echo "  $LOGDIR/writer_scan.json"
echo "  $LOGDIR/report.json (nach Dienst se_write_watchdog.dump_report)"
