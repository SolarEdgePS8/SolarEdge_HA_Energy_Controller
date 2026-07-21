#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

API = os.environ.get("HA_API_URL", "http://supervisor/core/api").rstrip("/")
DRY_RUN = os.environ.get("SE_CONTROLLER_DRY_RUN", "") == "1"

TEXT_MAP = {
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

NUMBER_MAP = {
    "BATTERY_CAPACITY_KWH": "input_number.se_nf_battery_capacity_kwh_fallback",
}

BOOLEAN_MAP = {
    "EVOPT_ENABLED": "input_boolean.se_nf_evopt_shadow_enabled",
}


def parse_env(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def call(service: str, payload: dict[str, object], *, tolerate_missing: bool = False) -> None:
    if DRY_RUN:
        print(f"DRY_RUN {service} {json.dumps(payload, ensure_ascii=False)}")
        return
    token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
    if not token:
        raise RuntimeError("SUPERVISOR_TOKEN fehlt")
    request = urllib.request.Request(
        f"{API}/services/{service}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if tolerate_missing and exc.code in {400, 404}:
            print(f"WARN {service}: {detail}")
            return
        raise RuntimeError(f"{service}: HTTP {exc.code}: {detail}") from exc


def set_master_off() -> None:
    call(
        "input_boolean/turn_off",
        {"entity_id": "input_boolean.se_netzdienlich_enabled"},
        tolerate_missing=True,
    )


def set_confirmed(value: bool) -> None:
    service = "input_boolean/turn_on" if value else "input_boolean/turn_off"
    call(
        service,
        {"entity_id": "input_boolean.se_nf_site_config_confirmed"},
        tolerate_missing=not value,
    )


def set_text(entity_id: str, value: str) -> None:
    call("input_text/set_value", {"entity_id": entity_id, "value": value})


def set_number(entity_id: str, value: str) -> None:
    number = float(value.replace(",", "."))
    call("input_number/set_value", {"entity_id": entity_id, "value": number})


def set_boolean(entity_id: str, value: str) -> None:
    enabled = value.strip().upper() in {"YES", "TRUE", "ON", "1"}
    service = "input_boolean/turn_on" if enabled else "input_boolean/turn_off"
    call(service, {"entity_id": entity_id})


parser = argparse.ArgumentParser()
parser.add_argument("env", nargs="?")
parser.add_argument("--master-off-only", action="store_true")
args = parser.parse_args()

set_master_off()
if args.master_off_only:
    print("Controller-Master ist AUS.")
    raise SystemExit(0)

if not args.env:
    raise SystemExit("Pfad zu site_config.env fehlt")

config = parse_env(Path(args.env))
if config.get("SITE_CONFIG_CONFIRMED", "").upper() != "YES":
    raise SystemExit("SITE_CONFIG_CONFIRMED muss YES sein")

set_confirmed(False)

for key, entity_id in TEXT_MAP.items():
    if key in config:
        set_text(entity_id, config[key])

for key, entity_id in NUMBER_MAP.items():
    if key in config and config[key] != "":
        set_number(entity_id, config[key])

for key, entity_id in BOOLEAN_MAP.items():
    if key in config and config[key] != "":
        set_boolean(entity_id, config[key])

set_confirmed(True)
set_master_off()
print("Site-Konfiguration angewendet. Standort bestätigt; Controller-Master bleibt AUS.")
