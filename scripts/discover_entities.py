#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

DEFAULT_API = (
    "http://supervisor/core/api"
    if os.environ.get("SUPERVISOR_TOKEN", "").strip()
    else "http://127.0.0.1:8123/api"
)

BAD_STATES = {"unknown", "unavailable", "none", ""}
POWER_UNITS = {"W", "kW", "MW"}
ENERGY_UNITS = {"Wh", "kWh", "MWh"}
PERCENT_UNITS = {"%"}
PRICE_UNITS = {"€/kWh", "EUR/kWh", "ct/kWh", "€/MWh", "EUR/MWh"}


@dataclass(frozen=True)
class Candidate:
    entity_id: str
    friendly_name: str
    unit: str
    device_class: str | None
    state_class: str | None
    state_available: bool
    score: int
    confidence: str
    reasons: list[str]
    options: list[str] | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only mapping assistant for SolarEdge HA Energy Controller. "
            "It reads Home Assistant states and never calls a write service."
        )
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("HA_API_URL", DEFAULT_API),
        help="Home Assistant API base URL, including /api",
    )
    parser.add_argument(
        "--states-file",
        type=Path,
        help="Use an exported Home Assistant /api/states JSON file instead of the API.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        help="Write the complete scored candidate report as JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help=(
            "Write a proposed site_config.env. The file always contains "
            "SITE_CONFIG_CONFIRMED=NO and must be reviewed manually."
        ),
    )
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Maximum candidates per category in the terminal summary (default: 5).",
    )
    return parser.parse_args()


def load_states(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.states_file:
        data = json.loads(args.states_file.read_text(encoding="utf-8"))
    else:
        token = (
            os.environ.get("SUPERVISOR_TOKEN", "").strip()
            or os.environ.get("HA_TOKEN", "").strip()
        )
        if not token:
            raise SystemExit(
                "Kein API-Token verfügbar. "
                "HA OS/Supervised: Terminal-/SSH-Add-on verwenden. "
                "Container/Core: HA_TOKEN und HA_API_URL setzen. "
                "Alternativ --states-file verwenden."
            )
        request = urllib.request.Request(
            args.api_url.rstrip("/") + "/states",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=40) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise SystemExit(f"Home-Assistant-API nicht erreichbar: {exc}") from exc

    if not isinstance(data, list):
        raise SystemExit("States-Daten müssen eine JSON-Liste sein.")
    return [item for item in data if isinstance(item, dict)]


def confidence(score: int) -> str:
    if score >= 90:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def record(item: dict[str, Any], score: int, reasons: list[str]) -> Candidate:
    attrs = item.get("attributes") or {}
    state = str(item.get("state", "")).strip().lower()
    options = attrs.get("options")
    return Candidate(
        entity_id=str(item.get("entity_id", "")),
        friendly_name=str(attrs.get("friendly_name", "")),
        unit=str(attrs.get("unit_of_measurement", "")),
        device_class=attrs.get("device_class"),
        state_class=attrs.get("state_class"),
        state_available=state not in BAD_STATES,
        score=score,
        confidence=confidence(score),
        reasons=reasons,
        options=[str(value) for value in options] if isinstance(options, list) else None,
    )


def add_candidate(
    categories: dict[str, list[Candidate]],
    category: str,
    item: dict[str, Any],
    base_score: int,
    reasons: list[str],
) -> None:
    attrs = item.get("attributes") or {}
    state = str(item.get("state", "")).strip().lower()
    score = base_score
    if state not in BAD_STATES:
        score += 5
        reasons = [*reasons, "state currently available"]
    else:
        reasons = [*reasons, f"state currently {state or 'empty'}"]
    if attrs.get("device_class"):
        score += 2
    categories[category].append(record(item, min(score, 100), reasons))


def classify(states: list[dict[str, Any]]) -> dict[str, list[Candidate]]:
    categories: dict[str, list[Candidate]] = {
        "charge_limit": [],
        "discharge_limit": [],
        "backup_reserve": [],
        "command_mode": [],
        "storage_control_mode": [],
        "battery_soc": [],
        "battery_capacity": [],
        "pv_power": [],
        "consumption_power": [],
        "pv_forecast_today_remaining": [],
        "pv_forecast_today_total": [],
        "pv_forecast_tomorrow": [],
        "pv_forecast_day_after_tomorrow": [],
        "forecast_now_power": [],
        "pv_energy_total": [],
        "consumption_energy_total": [],
        "weather": [],
        "evcc_battery_mode": [],
        "electricity_price": [],
    }

    for item in states:
        entity_id = str(item.get("entity_id", ""))
        if "." not in entity_id:
            continue
        domain = entity_id.split(".", 1)[0]
        attrs = item.get("attributes") or {}
        name = str(attrs.get("friendly_name", ""))
        unit = str(attrs.get("unit_of_measurement", ""))
        device_class = str(attrs.get("device_class", ""))
        haystack = f"{entity_id} {name}".lower()
        is_solaredge = "solaredge" in haystack
        is_evcc = "evcc" in haystack

        if (
            domain == "number"
            and re.search(r"storage.*charge.*limit|charge.*limit|lad.*limit", haystack)
            and not re.search(r"discharge|entlad", haystack)
        ):
            score = 70
            reasons = ["number entity", "name indicates charge limit"]
            if unit == "W":
                score += 15
                reasons.append("unit is W")
            if re.search(r"solaredge_.*storage_charge_limit", entity_id):
                score += 15
                reasons.append("SolarEdge Modbus Multi naming pattern")
            add_candidate(categories, "charge_limit", item, score, reasons)

        if domain == "number" and re.search(
            r"storage.*discharge.*limit|discharge.*limit|entlad.*limit", haystack
        ):
            score = 65
            reasons = ["number entity", "name indicates discharge limit"]
            if unit == "W":
                score += 15
                reasons.append("unit is W")
            if re.search(r"solaredge_.*storage_discharge_limit", entity_id):
                score += 15
                reasons.append("SolarEdge Modbus Multi naming pattern")
            add_candidate(categories, "discharge_limit", item, score, reasons)

        if domain == "number" and re.search(r"backup.*reserve|reserve.*backup", haystack):
            score = 65
            reasons = ["number entity", "name indicates backup reserve"]
            if unit == "%":
                score += 15
                reasons.append("unit is %")
            if is_solaredge:
                score += 10
                reasons.append("SolarEdge entity")
            add_candidate(categories, "backup_reserve", item, score, reasons)

        if domain in {"select", "sensor"} and re.search(
            r"storage.*command.*mode|command.*mode|befehls.*modus", haystack
        ):
            score = 55
            reasons = ["name indicates storage command mode"]
            if domain == "select":
                score += 20
                reasons.append("select entity")
            if is_solaredge:
                score += 10
                reasons.append("SolarEdge entity")
            add_candidate(categories, "command_mode", item, score, reasons)

        if domain in {"select", "sensor"} and re.search(
            r"storage.*control.*mode|storage.*control|speicher.*steuer", haystack
        ):
            score = 55
            reasons = ["name indicates storage control mode"]
            if domain == "select":
                score += 20
                reasons.append("select entity")
            if is_solaredge:
                score += 10
                reasons.append("SolarEdge entity")
            add_candidate(categories, "storage_control_mode", item, score, reasons)

        if domain == "sensor" and unit in PERCENT_UNITS and (
            re.search(
                r"state.of.energy|battery.*soc|battery.*soe|ladestand|akku.*stand",
                haystack,
            )
            or device_class == "battery"
        ):
            score = 65
            reasons = [
                "sensor entity",
                "unit is %",
                "name/device class indicates battery state",
            ]
            if re.search(r"solaredge_.*_b\d+_state_of_energy", entity_id):
                score += 25
                reasons.append("SolarEdge Modbus Multi battery SoE naming pattern")
            add_candidate(categories, "battery_soc", item, score, reasons)

        if domain == "sensor" and unit in ENERGY_UNITS and re.search(
            r"maximum.energy|battery.*capacity|batter.*kapazit|usable.*energy",
            haystack,
        ):
            score = 60
            reasons = ["energy sensor", "name indicates battery capacity"]
            if unit == "kWh":
                score += 10
                reasons.append("unit is kWh")
            if re.search(r"solaredge_.*_b\d+_maximum_energy", entity_id):
                score += 25
                reasons.append("SolarEdge Modbus Multi battery capacity naming pattern")
            add_candidate(categories, "battery_capacity", item, score, reasons)

        if (
            domain == "sensor"
            and unit in POWER_UNITS
            and re.search(r"\bpv\b|solar|photovolta", haystack)
            and not re.search(r"forecast|prognose|prediction", haystack)
        ):
            score = 45
            reasons = ["power sensor", "name indicates PV/solar"]
            if unit == "W":
                score += 10
                reasons.append("unit is W")
            if re.search(r"solaredge_.*_ac_power", entity_id):
                score += 25
                reasons.append("SolarEdge inverter AC power naming pattern")
            if "filtered" in haystack:
                score -= 5
                reasons.append("filtered source: verify delay before prioritizing")
            add_candidate(categories, "pv_power", item, score, reasons)

        if domain == "sensor" and unit in POWER_UNITS and re.search(
            r"consumption|house.*power|home.*power|verbrauch|load", haystack
        ):
            score = 50
            reasons = ["power sensor", "name indicates house consumption/load"]
            if unit == "W":
                score += 10
                reasons.append("unit is W")
            add_candidate(categories, "consumption_power", item, score, reasons)

        is_forecast_energy = (
            domain == "sensor"
            and unit in ENERGY_UNITS
            and re.search(r"forecast|prognose|prediction", haystack)
        )
        if is_forecast_energy:
            if re.search(r"remaining|verbleib|rest", haystack) and re.search(
                r"today|heute", haystack
            ):
                add_candidate(
                    categories,
                    "pv_forecast_today_remaining",
                    item,
                    75 if unit == "kWh" else 65,
                    ["forecast energy", "today", "remaining/rest"],
                )
            elif re.search(r"day.after.tomorrow|übermorgen|ubermorgen", haystack):
                add_candidate(
                    categories,
                    "pv_forecast_day_after_tomorrow",
                    item,
                    70 if unit == "kWh" else 60,
                    ["forecast energy", "day after tomorrow"],
                )
            elif re.search(r"tomorrow|morgen", haystack):
                add_candidate(
                    categories,
                    "pv_forecast_tomorrow",
                    item,
                    75 if unit == "kWh" else 65,
                    ["forecast energy", "tomorrow"],
                )
            elif re.search(r"today|heute", haystack):
                add_candidate(
                    categories,
                    "pv_forecast_today_total",
                    item,
                    70 if unit == "kWh" else 60,
                    ["forecast energy", "today total candidate"],
                )

        if domain == "sensor" and unit in POWER_UNITS and re.search(
            r"forecast|prognose|prediction", haystack
        ):
            add_candidate(
                categories,
                "forecast_now_power",
                item,
                60 if unit == "W" else 50,
                ["forecast sensor", "power unit"],
            )

        if domain == "sensor" and unit in ENERGY_UNITS and re.search(
            r"solar.*energy|pv.*energy|generation.*energy|yield|ertrag", haystack
        ):
            score = 45
            reasons = ["energy sensor", "name indicates PV yield/generation"]
            if device_class == "energy":
                score += 10
                reasons.append("device_class energy")
            add_candidate(categories, "pv_energy_total", item, score, reasons)

        if domain == "sensor" and unit in ENERGY_UNITS and re.search(
            r"consumption.*energy|energy.*consumption|verbrauch|imported", haystack
        ):
            score = 45
            reasons = ["energy sensor", "name indicates consumption"]
            if device_class == "energy":
                score += 10
                reasons.append("device_class energy")
            add_candidate(categories, "consumption_energy_total", item, score, reasons)

        if domain == "weather":
            score = 60
            reasons = ["weather entity"]
            if "dwd" in haystack:
                score += 10
                reasons.append("DWD Weather naming hint")
            add_candidate(categories, "weather", item, score, reasons)

        if domain in {"sensor", "select"} and is_evcc and re.search(
            r"battery.*mode|batter.*modus", haystack
        ):
            score = 55
            reasons = ["evcc entity", "name indicates battery mode"]
            if domain == "select":
                score += 10
                reasons.append("select entity")
            add_candidate(categories, "evcc_battery_mode", item, score, reasons)

        if domain == "sensor" and unit in PRICE_UNITS and re.search(
            r"price|preis|tariff|tarif|epex|spot", haystack
        ):
            add_candidate(
                categories,
                "electricity_price",
                item,
                55,
                ["price sensor", f"unit is {unit}"],
            )

    for values in categories.values():
        values.sort(key=lambda value: (-value.score, value.entity_id))
    return categories


def pick(
    categories: dict[str, list[Candidate]],
    category: str,
    minimum: int = 60,
    *,
    units: set[str] | None = None,
) -> str:
    """Return only an available candidate with the exact required unit.

    The report may contain useful conversion candidates in kW, Wh or MWh. The
    generated environment file is deliberately stricter and only fills values
    that already match the controller runtime contract.
    """
    for value in categories.get(category, []):
        if value.score < minimum or not value.state_available:
            continue
        if units is not None and value.unit not in units:
            continue
        return value.entity_id
    return ""


def env_comment(category: str, candidates: list[Candidate], limit: int = 3) -> list[str]:
    if not candidates:
        return [f"# {category}: no candidate found"]
    lines = [f"# {category} candidates:"]
    for value in candidates[:limit]:
        lines.append(
            f"#   {value.confidence:6} score={value.score:3} "
            f"{value.entity_id} [{value.unit or '-'}]"
        )
    return lines


def create_env(categories: dict[str, list[Candidate]]) -> str:
    charge = pick(categories, "charge_limit", 80, units={"W"})
    soc = pick(categories, "battery_soc", 75, units={"%"})
    capacity = pick(categories, "battery_capacity", 75, units={"kWh"})
    pv_power = pick(categories, "pv_power", 60, units={"W"})
    consumption_power = pick(categories, "consumption_power", 60, units={"W"})
    today_remaining = pick(
        categories, "pv_forecast_today_remaining", 70, units={"kWh"}
    )
    today_total = pick(categories, "pv_forecast_today_total", 70, units={"kWh"})
    tomorrow = pick(categories, "pv_forecast_tomorrow", 70, units={"kWh"})

    lines = [
        "# SolarEdge HA Energy Controller – read-only mapping proposal",
        "# Generated locally by scripts/discover_entities.py.",
        "# Review every entity, unit and writer ownership before applying.",
        "# This file is intentionally NOT confirmed and never enables the controller.",
        "",
        "SITE_CONFIG_CONFIRMED=NO",
        "",
        "# Required",
        *env_comment("CHARGE_LIMIT_ENTITY", categories["charge_limit"]),
        f"CHARGE_LIMIT_ENTITY={charge}",
        *env_comment("BATTERY_SOC_ENTITY", categories["battery_soc"]),
        f"BATTERY_SOC_ENTITY={soc}",
        *env_comment("BATTERY_CAPACITY_ENTITY", categories["battery_capacity"]),
        f"BATTERY_CAPACITY_ENTITY={capacity}",
        "# Enter usable total battery capacity manually if no reliable sensor exists.",
        "BATTERY_CAPACITY_KWH=",
        *env_comment(
            "PV_FORECAST_TODAY_REMAINING_ENTITY",
            categories["pv_forecast_today_remaining"],
        ),
        f"PV_FORECAST_TODAY_REMAINING_ENTITY={today_remaining}",
        *env_comment(
            "PV_FORECAST_TODAY_TOTAL_ENTITY",
            categories["pv_forecast_today_total"],
        ),
        f"PV_FORECAST_TODAY_TOTAL_ENTITY={today_total}",
        *env_comment(
            "PV_FORECAST_TOMORROW_ENTITY", categories["pv_forecast_tomorrow"]
        ),
        f"PV_FORECAST_TOMORROW_ENTITY={tomorrow}",
        *env_comment("LIVE_PV_POWER_ENTITIES", categories["pv_power"]),
        f"LIVE_PV_POWER_ENTITIES={pv_power}",
        *env_comment(
            "LIVE_CONSUMPTION_POWER_ENTITIES", categories["consumption_power"]
        ),
        f"LIVE_CONSUMPTION_POWER_ENTITIES={consumption_power}",
        "",
        "# Optional SolarEdge targets – leave empty unless this controller is the only writer.",
        f"DISCHARGE_LIMIT_ENTITY={pick(categories, 'discharge_limit', 80, units={'W'})}",
        "COMMAND_MODE_ENTITY=",
        "COMMAND_MODE_GRID_OPTION=",
        "COMMAND_MODE_DEFAULT_OPTION=",
        "STORAGE_CONTROL_MODE_ENTITY=",
        "STORAGE_CONTROL_REMOTE_OPTION=",
        f"BACKUP_RESERVE_ENTITY={pick(categories, 'backup_reserve', 80, units={'%'})}",
        "",
        "# Optional data sources",
        f"PV_FORECAST_DAY_AFTER_TOMORROW_ENTITY={pick(categories, 'pv_forecast_day_after_tomorrow', 70, units={'kWh'})}",
        f"WEATHER_ENTITY={pick(categories, 'weather', 60)}",
        "PV_YIELD_TODAY_ENTITY=",
        "CONSUMPTION_TODAY_ENTITY=",
        "PV_LIFETIME_ENTITY=",
        f"FORECAST_NOW_ENTITY={pick(categories, 'forecast_now_power', 60, units={'W'})}",
        "",
        "# Optional evcc/EVOpt – disabled until API and battery matching were verified.",
        "EVOPT_ENABLED=NO",
        "EVOPT_BASE_URL=http://EVCC-HOST:7070",
        "EVOPT_BATTERY_TITLE=SolarEdge Akku",
        "EVOPT_BATTERY_NAME=",
        f"EVOPT_BATTERY_MODE_ENTITY={pick(categories, 'evcc_battery_mode', 60)}",
        "",
        "# Optional neutral external signals",
        "EXTERNAL_EV_CHARGING_ENTITY=",
        "EXTERNAL_DISCHARGE_LOCK_ENTITY=",
        "EXTERNAL_PEAK_LOCK_ENTITY=",
        "",
    ]
    return "\n".join(lines)


def print_summary(categories: dict[str, list[Candidate]], top: int) -> None:
    print("SolarEdge HA Energy Controller – read-only mapping candidates")
    print("No Home Assistant service was called. No writer was activated.")
    for category, values in categories.items():
        print(f"\n[{category}]")
        if not values:
            print("  no candidate")
            continue
        for value in values[: max(1, top)]:
            reason = "; ".join(value.reasons)
            print(
                f"  {value.confidence:6} {value.score:3} "
                f"{value.entity_id:58} {value.unit or '-':8} {reason}"
            )


def main() -> int:
    args = parse_args()
    states = load_states(args)
    categories = classify(states)
    print_summary(categories, args.top)

    report = {
        "tool": "SolarEdge HA Energy Controller mapping assistant",
        "read_only": True,
        "states_count": len(states),
        "privacy_note": (
            "The report can contain local entity IDs. Review before sharing publicly."
        ),
        "categories": {
            name: [asdict(candidate) for candidate in values]
            for name, values in categories.items()
        },
    }

    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"\nReport written: {args.report}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(create_env(categories), encoding="utf-8")
        try:
            args.output.chmod(0o600)
        except OSError:
            pass
        print(f"Mapping proposal written: {args.output}")
        print(
            "SITE_CONFIG_CONFIRMED remains NO. "
            "Review manually before apply_site_config.py."
        )

    if not args.report and not args.output:
        print("\nJSON report:")
        print(json.dumps(report, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    sys.exit(main())
