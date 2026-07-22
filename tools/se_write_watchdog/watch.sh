#!/usr/bin/env bash
set -u
LOGDIR="/config/se_write_watchdog"
LOGFILE="$LOGDIR/events-$(date +%F).jsonl"

echo "Live-Überwachung: $LOGFILE"
echo "Abbruch mit Strg+C"
mkdir -p "$LOGDIR"
touch "$LOGFILE"

if command -v jq >/dev/null 2>&1; then
  tail -n 0 -F "$LOGFILE" | while IFS= read -r line; do
    printf '%s\n' "$line" | jq -c 'select(.event=="write_intent" or .event=="number_set_value_call" or .event=="charge_limit_state_change" or .event=="flapping_detected" or .event=="evopt_mismatch") | {timestamp,event,target_entity,requested_value,current_value_at_call,old_value,new_value,allowed_writer,duplicate,roundtrip_detected,source,reasons,reason,intent}'
  done
else
  tail -n 0 -F "$LOGFILE"
fi
