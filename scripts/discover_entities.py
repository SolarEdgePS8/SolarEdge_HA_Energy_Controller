#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import urllib.request

API = os.environ.get("HA_API_URL", "http://supervisor/core/api").rstrip("/")
token = os.environ.get("SUPERVISOR_TOKEN", "").strip()
if not token:
    raise SystemExit("SUPERVISOR_TOKEN fehlt")

request = urllib.request.Request(
    API + "/states",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=40) as response:
    states = json.loads(response.read().decode("utf-8"))

categories = {
    "charge_limit": [],
    "discharge_limit": [],
    "command_mode": [],
    "storage_control_mode": [],
    "battery_soc": [],
    "pv_power": [],
    "consumption_power": [],
    "pv_forecast": [],
    "weather": [],
}

for item in states:
    entity_id = item.get("entity_id", "")
    attrs = item.get("attributes") or {}
    name = str(attrs.get("friendly_name", ""))
    unit = str(attrs.get("unit_of_measurement", ""))
    haystack = f"{entity_id} {name}".lower()
    record = {
        "entity_id": entity_id,
        "name": name,
        "unit": unit,
        "device_class": attrs.get("device_class"),
        "options": attrs.get("options") if isinstance(attrs.get("options"), list) else None,
    }

    if entity_id.startswith("number.") and re.search(r"charge.*limit|lad.*limit", haystack):
        categories["charge_limit"].append(record)
    if entity_id.startswith("number.") and re.search(r"discharge.*limit|entlad.*limit", haystack):
        categories["discharge_limit"].append(record)
    if entity_id.startswith("select.") and re.search(r"command.*mode|befehls.*modus", haystack):
        categories["command_mode"].append(record)
    if entity_id.startswith("select.") and re.search(r"storage.*control|speicher.*steuer", haystack):
        categories["storage_control_mode"].append(record)
    if entity_id.startswith("sensor.") and (
        attrs.get("device_class") == "battery"
        or re.search(r"state.of.energy|soe|ladestand", haystack)
    ) and unit == "%":
        categories["battery_soc"].append(record)
    if entity_id.startswith("sensor.") and unit in {"W", "kW"} and re.search(r"pv|solar", haystack):
        categories["pv_power"].append(record)
    if entity_id.startswith("sensor.") and unit in {"W", "kW"} and re.search(r"consumption|verbrauch|load", haystack):
        categories["consumption_power"].append(record)
    if entity_id.startswith("sensor.") and unit in {"Wh", "kWh", "MWh"} and re.search(r"forecast|prognose", haystack):
        categories["pv_forecast"].append(record)
    if entity_id.startswith("weather."):
        categories["weather"].append(record)

print(json.dumps(categories, indent=2, ensure_ascii=False))
