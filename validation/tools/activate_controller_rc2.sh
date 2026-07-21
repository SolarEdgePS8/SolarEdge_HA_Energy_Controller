#!/usr/bin/env bash
set -eu

MODE="${1:---observe}"
MONITOR_SECONDS="${MONITOR_SECONDS:-600}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-10}"
CONFIG_ROOT="${CONFIG_ROOT:-/config}"
SHARE_ROOT="${SHARE_ROOT:-/share}"
API_URL="${HA_API_URL:-http://supervisor/core/api}"
STAMP="$(date -u '+%Y%m%dT%H%M%SZ')"
LOG_FILE="$SHARE_ROOT/se_controller_activation_${STAMP}.log"
JSON_FILE="$SHARE_ROOT/se_controller_activation_${STAMP}.json"
RUNTIME_REPORT="$SHARE_ROOT/se_controller_activation_runtime_${STAMP}.json"

log() {
  printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*" | tee -a "$LOG_FILE"
}

fail() {
  log "FEHLER: $*"
  exit 2
}

usage() {
  cat <<'EOF'
Aufruf:

  Nur prüfen, nichts einschalten:
    bash /share/activate_controller_rc2.sh --observe

  Kontrolliert aktivieren und 10 Minuten überwachen:
    bash /share/activate_controller_rc2.sh --activate

Optionale Dauer:
    MONITOR_SECONDS=900 bash /share/activate_controller_rc2.sh --activate
EOF
}

case "$MODE" in
  --observe|--activate) ;;
  *) usage; exit 2 ;;
esac

command -v python3 >/dev/null 2>&1 || fail "python3 fehlt"
command -v ha >/dev/null 2>&1 || fail "ha CLI fehlt"
[ -n "${SUPERVISOR_TOKEN:-}" ] || fail "SUPERVISOR_TOKEN fehlt"
[ -f "$CONFIG_ROOT/se_controller_runtime_checker.py" ] || \
  fail "Runtime-Checker fehlt: $CONFIG_ROOT/se_controller_runtime_checker.py"
[ -f "$CONFIG_ROOT/.se_controller_runtime_manifest.json" ] || \
  fail "Runtime-Manifest fehlt"

: >"$LOG_FILE"

log "SolarEdge HA Energy Controller RC2 – kontrollierte Aktivierung"
log "Modus: $MODE"
log "Überwachungsdauer: ${MONITOR_SECONDS}s"
log "Intervall: ${INTERVAL_SECONDS}s"

api_python() {
  python3 - "$API_URL" "$@" <<'PY'
from __future__ import annotations
import json
import os
import sys
import urllib.request

api = sys.argv[1].rstrip("/")
command = sys.argv[2]
token = os.environ["SUPERVISOR_TOKEN"]

def request(path: str, method: str = "GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        api + path,
        method=method,
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        raw = response.read()
        return json.loads(raw.decode("utf-8")) if raw else None

if command == "master":
    state = sys.argv[3]
    request(
        f"/services/input_boolean/turn_{state}",
        "POST",
        {"entity_id": "input_boolean.se_netzdienlich_enabled"},
    )
    print(f"MASTER={state.upper()}")

elif command == "state":
    entity_id = sys.argv[3]
    item = request("/states/" + entity_id)
    print(item.get("state", ""))

elif command == "snapshot":
    states = request("/states") or []
    index = {
        item.get("entity_id"): item
        for item in states
        if isinstance(item, dict) and item.get("entity_id")
    }

    entities = [
        "input_boolean.se_netzdienlich_enabled",
        "input_boolean.se_nf_site_config_confirmed",
        "sensor.se_nf_config_check",
        "sensor.se_nf_sanity_check",
        "binary_sensor.se_nf_controller_write_enabled",
        "binary_sensor.se_nf_risk_flag",
        "sensor.se_nf_start_gate_reason",
        "sensor.se_nf_active_control_label",
        "sensor.se_nf_desired_target",
        "sensor.se_nf_charge_limit_actual",
        "sensor.se_nf_writer_mode",
        "sensor.se_nf_writer_last_decision",
        "input_text.se_nf_charge_limit_entity",
        "input_text.se_nf_discharge_limit_entity",
        "input_text.se_nf_command_mode_entity",
        "input_text.se_nf_storage_control_mode_entity",
        "input_text.se_discharge_limit_writer_last_reason",
        "input_text.se_storage_control_writer_last_reason",
        "input_text.se_storage_command_mode_writer_last_reason",
        "input_select.se_nf_optimization_mode",
        "input_select.se_nf_session_state",
        "sensor.se_nf_battery_soe",
        "sensor.se_nf_remaining_pv_today",
        "sensor.se_nf_pv_forecast_tomorrow",
        "binary_sensor.se_nf_evopt_grid_charge_request",
        "binary_sensor.se_nf_evopt_discharge_lock_request",
    ]

    result = {}
    for entity_id in entities:
        item = index.get(entity_id)
        result[entity_id] = None if item is None else {
            "state": item.get("state"),
            "attributes": item.get("attributes") or {},
            "last_changed": item.get("last_changed"),
            "last_updated": item.get("last_updated"),
        }

    for helper in (
        "input_text.se_nf_charge_limit_entity",
        "input_text.se_nf_discharge_limit_entity",
        "input_text.se_nf_command_mode_entity",
        "input_text.se_nf_storage_control_mode_entity",
    ):
        item = index.get(helper)
        target = str(item.get("state", "")).strip() if item else ""
        if target and target not in {"unknown", "unavailable", "none", "None"}:
            target_item = index.get(target)
            result[f"mapped::{helper}"] = {
                "target": target,
                "state": None if target_item is None else target_item.get("state"),
                "attributes": {} if target_item is None else target_item.get("attributes") or {},
            }

    print(json.dumps(result, ensure_ascii=False))
PY
}

master_off() {
  api_python master off >>"$LOG_FILE" 2>&1 || true
}

INTERRUPTED=0
trap 'INTERRUPTED=1; log "Abbruch erkannt – Controller-Master wird ausgeschaltet."; master_off; exit 130' INT TERM HUP

log "Home-Assistant-Konfiguration prüfen."
ha core check 2>&1 | tee -a "$LOG_FILE"

log "Runtime-Prüfung bei ausgeschaltetem Master."
python3 "$CONFIG_ROOT/se_controller_runtime_checker.py" \
  --expect-master-off \
  --report "$RUNTIME_REPORT" 2>&1 | tee -a "$LOG_FILE"

log "Ausgangszustand erfassen."
BEFORE_JSON="$(api_python snapshot)"
printf '%s\n' "$BEFORE_JSON" >"$JSON_FILE.before"

python3 - "$BEFORE_JSON" <<'PY' | tee -a "$LOG_FILE"
import json
import sys

data = json.loads(sys.argv[1])
def state(entity):
    item = data.get(entity)
    return None if item is None else item.get("state")

checks = {
    "Master AUS": state("input_boolean.se_netzdienlich_enabled") == "off",
    "Site-Konfiguration bestätigt": state("input_boolean.se_nf_site_config_confirmed") == "on",
    "Config Check OK": state("sensor.se_nf_config_check") == "ok",
    "Sanity Check OK": state("sensor.se_nf_sanity_check") == "ok",
    "Writer gesperrt": state("binary_sensor.se_nf_controller_write_enabled") == "off",
    "Risk Flag AUS": state("binary_sensor.se_nf_risk_flag") == "off",
}
for name, passed in checks.items():
    print(f"[{'OK' if passed else 'FEHLER'}] {name}")
if not all(checks.values()):
    raise SystemExit(2)

print("[INFO] Modus:", state("input_select.se_nf_optimization_mode"))
print("[INFO] Session:", state("input_select.se_nf_session_state"))
print("[INFO] Ziel Charge-Limit:", state("sensor.se_nf_desired_target"))
print("[INFO] Ist Charge-Limit:", state("sensor.se_nf_charge_limit_actual"))
print("[INFO] Start-Gate:", state("sensor.se_nf_start_gate_reason"))
PY

if [ "$MODE" = "--observe" ]; then
  log "OBSERVE=PASS"
  log "Controller-Master bleibt AUS."
  log "Für die Aktivierung:"
  log "bash /share/activate_controller_rc2.sh --activate"
  exit 0
fi

log "Controller-Master wird eingeschaltet."
api_python master on 2>&1 | tee -a "$LOG_FILE"
sleep 8

START_TS="$(date +%s)"
END_TS="$((START_TS + MONITOR_SECONDS))"
FAIL_COUNT=0
SAMPLES=0

python3 - "$API_URL" "$END_TS" "$INTERVAL_SECONDS" "$JSON_FILE" <<'PY' 2>&1 | tee -a "$LOG_FILE"
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

api = sys.argv[1].rstrip("/")
end_ts = int(sys.argv[2])
interval = int(sys.argv[3])
report_path = Path(sys.argv[4])
token = os.environ["SUPERVISOR_TOKEN"]

def get_states():
    req = urllib.request.Request(
        api + "/states",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {
        item["entity_id"]: item
        for item in data
        if isinstance(item, dict) and item.get("entity_id")
    }

def service(domain, action, entity_id):
    payload = json.dumps({"entity_id": entity_id}).encode("utf-8")
    req = urllib.request.Request(
        api + f"/services/{domain}/{action}",
        method="POST",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        response.read()

def state(index, entity_id):
    item = index.get(entity_id)
    return None if item is None else item.get("state")

def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

samples = []
consecutive_failures = 0
previous = {}

while int(time.time()) < end_ts:
    now = time.time()
    try:
        index = get_states()
        desired = number(state(index, "sensor.se_nf_desired_target"))
        actual = number(state(index, "sensor.se_nf_charge_limit_actual"))
        start_reason = str(state(index, "sensor.se_nf_start_gate_reason") or "")
        writer_mode = state(index, "sensor.se_nf_writer_mode")
        writer_decision = state(index, "sensor.se_nf_writer_last_decision")

        critical = []
        if state(index, "input_boolean.se_netzdienlich_enabled") != "on":
            critical.append("master_not_on")
        if state(index, "input_boolean.se_nf_site_config_confirmed") != "on":
            critical.append("site_config_not_confirmed")
        if state(index, "sensor.se_nf_config_check") != "ok":
            critical.append("config_check_not_ok")
        if state(index, "sensor.se_nf_sanity_check") != "ok":
            critical.append("sanity_check_not_ok")
        if state(index, "binary_sensor.se_nf_controller_write_enabled") != "on":
            critical.append("writer_not_enabled")
        if state(index, "binary_sensor.se_nf_risk_flag") != "off":
            critical.append("risk_flag_on")
        if desired is None or not 0 <= desired <= 5000:
            critical.append("desired_target_invalid")
        if actual is None or not 0 <= actual <= 5000:
            critical.append("charge_limit_actual_invalid")
        if len(start_reason) > 255:
            critical.append("start_gate_too_long")

        mapped = {}
        for helper in (
            "input_text.se_nf_charge_limit_entity",
            "input_text.se_nf_discharge_limit_entity",
            "input_text.se_nf_command_mode_entity",
            "input_text.se_nf_storage_control_mode_entity",
        ):
            target = str(state(index, helper) or "").strip()
            target_state = state(index, target) if target else None
            mapped[helper] = {"target": target, "state": target_state}

        sample = {
            "timestamp": now,
            "critical": critical,
            "master": state(index, "input_boolean.se_netzdienlich_enabled"),
            "write_enabled": state(index, "binary_sensor.se_nf_controller_write_enabled"),
            "config": state(index, "sensor.se_nf_config_check"),
            "sanity": state(index, "sensor.se_nf_sanity_check"),
            "risk": state(index, "binary_sensor.se_nf_risk_flag"),
            "mode": state(index, "input_select.se_nf_optimization_mode"),
            "session": state(index, "input_select.se_nf_session_state"),
            "desired_target": desired,
            "charge_limit_actual": actual,
            "writer_mode": writer_mode,
            "writer_decision": writer_decision,
            "start_gate": start_reason,
            "battery_soe": state(index, "sensor.se_nf_battery_soe"),
            "remaining_pv_today": state(index, "sensor.se_nf_remaining_pv_today"),
            "mapped_targets": mapped,
            "discharge_reason": state(index, "input_text.se_discharge_limit_writer_last_reason"),
            "storage_control_reason": state(index, "input_text.se_storage_control_writer_last_reason"),
            "command_mode_reason": state(index, "input_text.se_storage_command_mode_writer_last_reason"),
        }
        samples.append(sample)

        summary = (
            f"[SAMPLE] master={sample['master']} write={sample['write_enabled']} "
            f"cfg={sample['config']} sanity={sample['sanity']} risk={sample['risk']} "
            f"mode={sample['mode']} session={sample['session']} "
            f"target={desired} actual={actual} writer={writer_mode} "
            f"errors={','.join(critical) if critical else '-'}"
        )
        print(summary, flush=True)

        if critical:
            consecutive_failures += 1
        else:
            consecutive_failures = 0

        if consecutive_failures >= 2:
            service("input_boolean", "turn_off", "input_boolean.se_netzdienlich_enabled")
            report_path.write_text(
                json.dumps(
                    {
                        "pass": False,
                        "reason": "two_consecutive_critical_samples",
                        "master_forced_off": True,
                        "samples": samples,
                    },
                    indent=2,
                    ensure_ascii=False,
                ) + "\n",
                encoding="utf-8",
            )
            print("[FEHLER] Zwei kritische Messungen in Folge. Master wurde ausgeschaltet.", flush=True)
            raise SystemExit(2)

    except Exception as exc:
        consecutive_failures += 1
        samples.append({
            "timestamp": now,
            "critical": ["snapshot_error"],
            "error": str(exc),
        })
        print(f"[FEHLER] Snapshot: {exc}", flush=True)
        if consecutive_failures >= 2:
            try:
                service("input_boolean", "turn_off", "input_boolean.se_netzdienlich_enabled")
            except Exception:
                pass
            report_path.write_text(
                json.dumps(
                    {
                        "pass": False,
                        "reason": "two_consecutive_snapshot_errors",
                        "master_forced_off": True,
                        "samples": samples,
                    },
                    indent=2,
                    ensure_ascii=False,
                ) + "\n",
                encoding="utf-8",
            )
            raise SystemExit(2)

    time.sleep(interval)

report_path.write_text(
    json.dumps(
        {
            "pass": True,
            "master_left_on": True,
            "sample_count": len(samples),
            "samples": samples,
        },
        indent=2,
        ensure_ascii=False,
    ) + "\n",
    encoding="utf-8",
)
print(f"[OK] Überwachung bestanden: {len(samples)} Messungen.", flush=True)
PY

log "Abschließende Runtime-Prüfung."
python3 "$CONFIG_ROOT/se_controller_runtime_checker.py" \
  --report "$RUNTIME_REPORT" 2>&1 | tee -a "$LOG_FILE"

FINAL_MASTER="$(api_python state input_boolean.se_netzdienlich_enabled)"
FINAL_WRITE="$(api_python state binary_sensor.se_nf_controller_write_enabled)"

if [ "$FINAL_MASTER" != "on" ] || [ "$FINAL_WRITE" != "on" ]; then
  master_off
  fail "Abschlusszustand ungültig: Master=$FINAL_MASTER Writer=$FINAL_WRITE"
fi

log "ACTIVATION=PASS"
log "Controller-Master: AN"
log "Writer-Freigabe: AN"
log "Überwachungsbericht: $JSON_FILE"
log "Laufzeitbericht: $RUNTIME_REPORT"
log "Log: $LOG_FILE"
