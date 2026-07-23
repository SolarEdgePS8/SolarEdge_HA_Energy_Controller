#!/usr/bin/env python3
"""Local allowlist exporter for Home Assistant state snapshots and CSV histories.

Nothing is uploaded. The mapping file is the only allowlist: source columns or
entity IDs that are not mapped to a public role are discarded.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

import yaml

PUBLIC_COLUMNS = [
    "slot",
    "time",
    "minute",
    "pv_w",
    "home_w",
    "grid_import_w",
    "grid_export_w",
    "battery_charge_w",
    "battery_discharge_w",
    "soc_pct",
    "pv_actual_cumulative_kwh",
    "pv_forecast_total_kwh",
    "pv_forecast_remaining_kwh",
    "pv_forecast_tomorrow_kwh",
    "evopt_action",
    "evopt_healthy",
    "energy_balance_residual_w",
]
POWER_ROLES = {
    "pv_w",
    "home_w",
    "grid_import_w",
    "grid_export_w",
    "battery_charge_w",
    "battery_discharge_w",
}
REQUIRED_ROLES = POWER_ROLES | {
    "soc_pct",
    "pv_forecast_remaining_kwh",
    "pv_forecast_tomorrow_kwh",
}
ACTIONS = {"normal", "holdcharge", "charge", "discharge", "hold", "unavailable"}


def parse_number(value: Any) -> float:
    if value is None:
        raise ValueError("missing numeric value")
    text = str(value).strip().replace("\u00a0", "").replace(" ", "")
    if not text:
        raise ValueError("empty numeric value")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    return float(text)


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "on", "healthy"}:
        return True
    if text in {"0", "false", "no", "off", "unavailable"}:
        return False
    raise ValueError(f"invalid boolean: {value!r}")


def read_mapping(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("mapping must be a YAML object")
    roles = data.get("roles")
    if not isinstance(roles, dict):
        raise ValueError("mapping.roles must be an object")
    return data


def detect_dialect(path: Path) -> csv.Dialect:
    sample = path.read_text(encoding="utf-8-sig", errors="replace")[:8192]
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        return csv.excel


def parse_timestamp(value: str, timezone_name: str) -> tuple[str, int]:
    del timezone_name
    text = value.strip()
    if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", text):
        hour, minute = map(int, text.split(":"))
        return text, hour * 60 + minute
    parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return parsed.strftime("%H:%M"), parsed.hour * 60 + parsed.minute


def _column(row: dict[str, str], roles: dict[str, Any], role: str, default: Any = None) -> Any:
    source = roles.get(role)
    if source is None:
        return default
    if source not in row:
        raise ValueError(f"mapped CSV column missing for role {role}: {source}")
    return row[source]


def export_csv(input_path: Path, mapping_path: Path, output_path: Path) -> dict[str, Any]:
    mapping = read_mapping(mapping_path)
    roles = mapping["roles"]
    missing = sorted(REQUIRED_ROLES - set(roles))
    if missing:
        raise ValueError(f"required roles missing from mapping: {missing}")

    source = mapping.get("source", {}) or {}
    metadata = mapping.get("metadata", {}) or {}
    timestamp_column = str(source.get("timestamp_column", "timestamp"))
    timezone_name = str(metadata.get("timezone", "Europe/Berlin"))
    cadence = int(metadata.get("cadence_minutes", 15))
    if cadence != 15:
        raise ValueError("public 24h fixtures currently require 15-minute cadence")

    dialect = detect_dialect(input_path)
    with input_path.open("r", encoding="utf-8-sig", newline="") as handle:
        raw_rows = list(csv.DictReader(handle, dialect=dialect))
    if len(raw_rows) != 96:
        raise ValueError(f"CSV must contain exactly 96 data rows, got {len(raw_rows)}")

    normalized: list[dict[str, Any]] = []
    for raw in raw_rows:
        if timestamp_column not in raw:
            raise ValueError(f"timestamp column missing: {timestamp_column}")
        time_text, minute = parse_timestamp(str(raw[timestamp_column]), timezone_name)
        item: dict[str, Any] = {"time": time_text, "minute": minute}
        for role in POWER_ROLES | {
            "soc_pct",
            "pv_forecast_remaining_kwh",
            "pv_forecast_tomorrow_kwh",
        }:
            item[role] = parse_number(_column(raw, roles, role))
        forecast_total_raw = _column(
            raw,
            roles,
            "pv_forecast_total_kwh",
            metadata.get("forecast_total_kwh", item["pv_forecast_remaining_kwh"]),
        )
        item["pv_forecast_total_kwh"] = parse_number(forecast_total_raw)
        action = str(_column(raw, roles, "evopt_action", "normal")).strip().lower()
        if action not in ACTIONS:
            raise ValueError(f"unsupported EVOpt action: {action}")
        item["evopt_action"] = action
        item["evopt_healthy"] = parse_bool(_column(raw, roles, "evopt_healthy", True))
        normalized.append(item)

    normalized.sort(key=lambda row: row["minute"])
    expected = list(range(0, 1440, 15))
    actual = [int(row["minute"]) for row in normalized]
    if actual != expected:
        raise ValueError("timestamps must form one complete monotonic 15-minute day")

    cumulative_pv = 0.0
    rows: list[list[Any]] = []
    for slot, item in enumerate(normalized):
        cumulative_pv += item["pv_w"] * 0.25 / 1000
        residual = (
            item["pv_w"]
            + item["grid_import_w"]
            + item["battery_discharge_w"]
            - item["home_w"]
            - item["grid_export_w"]
            - item["battery_charge_w"]
        )
        if abs(residual) > float(metadata.get("max_balance_residual_w", 20)):
            raise ValueError(f"slot {slot} energy balance residual too high: {residual:.3f} W")
        rows.append(
            [
                slot,
                item["time"],
                item["minute"],
                round(item["pv_w"], 3),
                round(item["home_w"], 3),
                round(item["grid_import_w"], 3),
                round(item["grid_export_w"], 3),
                round(item["battery_charge_w"], 3),
                round(item["battery_discharge_w"], 3),
                round(item["soc_pct"], 3),
                round(cumulative_pv, 3),
                round(item["pv_forecast_total_kwh"], 3),
                round(item["pv_forecast_remaining_kwh"], 3),
                round(item["pv_forecast_tomorrow_kwh"], 3),
                item["evopt_action"],
                item["evopt_healthy"],
                round(residual, 3),
            ]
        )

    def energy(role: str) -> float:
        return round(sum(float(item[role]) for item in normalized) * 0.25 / 1000, 3)

    output = {
        "schema_version": 1,
        "name": str(metadata.get("name", "local_allowlist_export_15m")),
        "source_date": str(metadata.get("source_date", "2000-01-01")),
        "timezone": timezone_name,
        "cadence_minutes": 15,
        "slots": 96,
        "battery_capacity_kwh": parse_number(metadata.get("battery_capacity_kwh", 10)),
        "battery_efficiency": parse_number(metadata.get("battery_efficiency", 0.95)),
        "initial_soc_pct": round(float(normalized[0]["soc_pct"]), 3),
        "final_soc_pct": round(float(normalized[-1]["soc_pct"]), 3),
        "actual_pv_kwh": energy("pv_w"),
        "actual_load_kwh": energy("home_w"),
        "actual_grid_import_kwh": energy("grid_import_w"),
        "actual_grid_export_kwh": energy("grid_export_w"),
        "actual_battery_charge_kwh": energy("battery_charge_w"),
        "actual_battery_discharge_kwh": energy("battery_discharge_w"),
        "forecast_scale_observed": parse_number(metadata.get("forecast_scale_observed", 1)),
        "forecast_total_kwh": round(float(normalized[0]["pv_forecast_total_kwh"]), 3),
        "evopt_timeline_kind": str(metadata.get("evopt_timeline_kind", "local_allowlist_export")),
        "source_kind": "locally_exported_allowlisted_roles",
        "privacy": (
            "Generated locally from an explicit allowlist. Source column names, "
            "entity IDs, addresses, tokens and account data are not included."
        ),
        "columns": PUBLIC_COLUMNS,
        "rows": rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    return output


def export_states(input_path: Path, mapping_path: Path, output_path: Path) -> dict[str, Any]:
    mapping = read_mapping(mapping_path)
    roles = mapping["roles"]
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Home Assistant states JSON must be a list")
    states = {str(item.get("entity_id")): item for item in payload if isinstance(item, dict)}
    result: dict[str, Any] = {
        "public_fixture": False,
        "purpose": "local mapping validation only",
        "roles": {},
    }
    for role, entity_id in roles.items():
        if role in {"evopt_action", "evopt_healthy"}:
            continue
        item = states.get(str(entity_id))
        result["roles"][role] = {
            "configured": str(entity_id),
            "present": item is not None,
            "state": None if item is None else item.get("state"),
            "unit": None if item is None else (item.get("attributes") or {}).get("unit_of_measurement"),
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    csv_parser = sub.add_parser("csv", help="export one complete 96-row CSV day")
    csv_parser.add_argument("--input", required=True, type=Path)
    csv_parser.add_argument("--mapping", required=True, type=Path)
    csv_parser.add_argument("--output", required=True, type=Path)

    states_parser = sub.add_parser("states", help="validate a local HA /api/states JSON snapshot")
    states_parser.add_argument("--input", required=True, type=Path)
    states_parser.add_argument("--mapping", required=True, type=Path)
    states_parser.add_argument("--output", required=True, type=Path)

    args = parser.parse_args()
    try:
        if args.command == "csv":
            result = export_csv(args.input, args.mapping, args.output)
            print(json.dumps({"pass": True, "output": str(args.output), "slots": result["slots"], "name": result["name"]}, ensure_ascii=False))
        else:
            result = export_states(args.input, args.mapping, args.output)
            print(json.dumps({"pass": all(item["present"] for item in result["roles"].values()), "output": str(args.output), "roles": len(result["roles"])}, ensure_ascii=False))
    except (OSError, ValueError, json.JSONDecodeError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
