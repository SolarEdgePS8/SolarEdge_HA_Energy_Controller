#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

API = os.environ.get("HA_API_URL", "http://supervisor/core/api").rstrip("/")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "").strip()

HELPERS = {
    "CHARGE_LIMIT_ENTITY": "input_text.se_nf_charge_limit_entity",
    "DISCHARGE_LIMIT_ENTITY": "input_text.se_nf_discharge_limit_entity",
    "COMMAND_MODE_ENTITY": "input_text.se_nf_command_mode_entity",
    "COMMAND_MODE_GRID_OPTION": "input_text.se_nf_command_mode_grid_option",
    "COMMAND_MODE_DEFAULT_OPTION": "input_text.se_nf_command_mode_default_option",
    "STORAGE_CONTROL_MODE_ENTITY": "input_text.se_nf_storage_control_mode_entity",
    "STORAGE_CONTROL_REMOTE_OPTION": "input_text.se_nf_storage_control_remote_option",
    "BACKUP_RESERVE_ENTITY": "input_text.se_nf_backup_reserve_entity",
    "BATTERY_SOC_ENTITY": "input_text.se_nf_battery_soe_entity",
    "BATTERY_CAPACITY_ENTITY": "input_text.se_nf_battery_capacity_entity",
    "PV_FORECAST_TODAY_REMAINING_ENTITY": "input_text.se_nf_pv_today_remaining_entity",
    "PV_FORECAST_TODAY_TOTAL_ENTITY": "input_text.se_nf_pv_today_total_entity",
    "PV_FORECAST_TOMORROW_ENTITY": "input_text.se_nf_pv_tomorrow_entity",
    "PV_FORECAST_DAY_AFTER_TOMORROW_ENTITY": "input_text.se_nf_pv_overmorgen_entity",
    "LIVE_PV_POWER_ENTITIES": "input_text.se_nf_live_pv_power_entities",
    "LIVE_CONSUMPTION_POWER_ENTITIES": "input_text.se_nf_live_consumption_power_entities",
    "WEATHER_ENTITY": "input_text.se_nf_weather_entity",
    "PV_YIELD_TODAY_ENTITY": "input_text.se_nf_pv_actual_today_entity",
    "CONSUMPTION_TODAY_ENTITY": "input_text.se_nf_daily_consumption_entity",
    "PV_LIFETIME_ENTITY": "input_text.se_nf_pv_actual_meter_source_entity",
    "FORECAST_NOW_ENTITY": "input_text.se_nf_forecast_now_entity",
    "EVOPT_BASE_URL": "input_text.se_nf_evopt_base_url",
    "EVOPT_BATTERY_TITLE": "input_text.se_nf_evopt_battery_title",
    "EVOPT_BATTERY_NAME": "input_text.se_nf_evopt_battery_name",
    "EVOPT_BATTERY_MODE_ENTITY": "input_text.se_nf_evcc_battery_mode_entity",
    "EXTERNAL_EV_CHARGING_ENTITY": "input_text.se_nf_external_ev_charging_entity",
    "EXTERNAL_DISCHARGE_LOCK_ENTITY": "input_text.se_nf_external_discharge_lock_entity",
    "EXTERNAL_PEAK_LOCK_ENTITY": "input_text.se_nf_external_peak_lock_entity",
}
REQUIRED = {
    "CHARGE_LIMIT_ENTITY",
    "BATTERY_SOC_ENTITY",
    "PV_FORECAST_TODAY_REMAINING_ENTITY",
    "PV_FORECAST_TODAY_TOTAL_ENTITY",
    "PV_FORECAST_TOMORROW_ENTITY",
    "LIVE_PV_POWER_ENTITIES",
    "LIVE_CONSUMPTION_POWER_ENTITIES",
}


def states() -> dict[str, dict[str, Any]]:
    if not TOKEN:
        raise RuntimeError("SUPERVISOR_TOKEN fehlt")
    req = urllib.request.Request(
        API + "/states",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {item["entity_id"]: item for item in data if item.get("entity_id")}


def valid(value: Any) -> bool:
    return str(value or "").strip() not in {"", "unknown", "unavailable", "none", "None"}


def choose_option(entity: dict[str, Any] | None, pattern: str) -> str:
    options = (entity or {}).get("attributes", {}).get("options") or []
    regex = re.compile(pattern, re.I)
    for option in options:
        if regex.search(str(option)):
            return str(option)
    return ""


parser = argparse.ArgumentParser()
parser.add_argument("output")
parser.add_argument("--safe-coexistence", action="store_true", default=True)
args = parser.parse_args()
index = states()
values = {key: str(index.get(helper, {}).get("state", "")).strip() for key, helper in HELPERS.items()}

# Known SolarEdge candidates are used only when the corresponding entity exists.
candidates = {
    "DISCHARGE_LIMIT_ENTITY": "number.solaredge_i1_storage_discharge_limit",
    "COMMAND_MODE_ENTITY": "select.solaredge_i1_storage_command_mode",
    "STORAGE_CONTROL_MODE_ENTITY": "select.solaredge_i1_storage_control_mode",
}
for key, entity_id in candidates.items():
    if not valid(values.get(key)) and entity_id in index:
        values[key] = entity_id

# Preserve coexistence: command/storage ownership remains with existing local automations.
# Candidate values are documented but not activated automatically.
candidate_command = values.get("COMMAND_MODE_ENTITY", "")
candidate_control = values.get("STORAGE_CONTROL_MODE_ENTITY", "")
if args.safe_coexistence:
    values["COMMAND_MODE_ENTITY"] = ""
    values["COMMAND_MODE_GRID_OPTION"] = ""
    values["COMMAND_MODE_DEFAULT_OPTION"] = ""
    values["STORAGE_CONTROL_MODE_ENTITY"] = ""
    values["STORAGE_CONTROL_REMOTE_OPTION"] = ""
else:
    if valid(candidate_command):
        values["COMMAND_MODE_GRID_OPTION"] = choose_option(index.get(candidate_command), r"charge from solar power and grid")
        values["COMMAND_MODE_DEFAULT_OPTION"] = choose_option(index.get(candidate_command), r"maximize self consumption")
    if valid(candidate_control):
        values["STORAGE_CONTROL_REMOTE_OPTION"] = choose_option(index.get(candidate_control), r"remote control|remote|extern")

capacity = index.get("input_number.se_nf_battery_capacity_kwh_fallback", {}).get("state")
try:
    cap = float(str(capacity).replace(",", "."))
except Exception:
    cap = 0.0
if cap <= 0:
    cap_entity = values.get("BATTERY_CAPACITY_ENTITY", "")
    try:
        cap = float(index.get(cap_entity, {}).get("state", 0))
        if cap > 100:
            cap /= 1000.0
    except Exception:
        cap = 0.0
if cap <= 0:
    cap = 14.55
values["BATTERY_CAPACITY_KWH"] = f"{cap:.3f}".rstrip("0").rstrip(".")

values["EVOPT_ENABLED"] = "YES" if index.get("input_boolean.se_nf_evopt_shadow_enabled", {}).get("state") == "on" else "NO"
values.setdefault("EVOPT_BATTERY_TITLE", "SolarEdge Akku")
values["SITE_CONFIG_CONFIRMED"] = "YES"

missing = []
for key in REQUIRED:
    value = values.get(key, "")
    if not valid(value):
        missing.append(key)
        continue
    if key in {"LIVE_PV_POWER_ENTITIES", "LIVE_CONSUMPTION_POWER_ENTITIES"}:
        candidates_list = [item.strip() for item in value.split(",") if item.strip()]
        if not any(item in index for item in candidates_list):
            missing.append(key)
    elif value not in index:
        missing.append(key)
if missing:
    raise SystemExit("Pflicht-Mappings fehlen oder Ziel-Entities existieren nicht: " + ", ".join(sorted(missing)))

order = [
    "SITE_CONFIG_CONFIRMED",
    "CHARGE_LIMIT_ENTITY", "BATTERY_SOC_ENTITY", "BATTERY_CAPACITY_KWH",
    "PV_FORECAST_TODAY_REMAINING_ENTITY", "PV_FORECAST_TODAY_TOTAL_ENTITY",
    "PV_FORECAST_TOMORROW_ENTITY", "LIVE_PV_POWER_ENTITIES",
    "LIVE_CONSUMPTION_POWER_ENTITIES", "DISCHARGE_LIMIT_ENTITY",
    "COMMAND_MODE_ENTITY", "COMMAND_MODE_GRID_OPTION", "COMMAND_MODE_DEFAULT_OPTION",
    "STORAGE_CONTROL_MODE_ENTITY", "STORAGE_CONTROL_REMOTE_OPTION",
    "BACKUP_RESERVE_ENTITY", "BATTERY_CAPACITY_ENTITY",
    "PV_FORECAST_DAY_AFTER_TOMORROW_ENTITY", "WEATHER_ENTITY",
    "PV_YIELD_TODAY_ENTITY", "CONSUMPTION_TODAY_ENTITY",
    "PV_LIFETIME_ENTITY", "FORECAST_NOW_ENTITY",
    "EVOPT_ENABLED", "EVOPT_BASE_URL", "EVOPT_BATTERY_TITLE",
    "EVOPT_BATTERY_NAME", "EVOPT_BATTERY_MODE_ENTITY",
    "EXTERNAL_EV_CHARGING_ENTITY", "EXTERNAL_DISCHARGE_LOCK_ENTITY",
    "EXTERNAL_PEAK_LOCK_ENTITY",
]
path = Path(args.output)
path.parent.mkdir(parents=True, exist_ok=True)
lines = [
    "# PRIVATE – automatisch aus der Referenzinstallation erzeugt",
    "# Nicht veröffentlichen.",
    "# Command- und Storage-Control-Mapping bleiben absichtlich leer,",
    "# solange bestehende lokale Automationen diese Ziele besitzen.",
    f"# COMMAND_MODE_CANDIDATE={candidate_command}",
    f"# STORAGE_CONTROL_MODE_CANDIDATE={candidate_control}",
]
for key in order:
    lines.append(f"{key}={values.get(key, '')}")
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(path)
