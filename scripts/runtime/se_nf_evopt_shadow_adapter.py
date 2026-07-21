#!/usr/bin/env python3
"""SE-NF EVOpt shadow adapter.

Read-only adapter for Home Assistant command_line sensor.
Fetches evcc/EVOpt state, validates the current optimizer plan, and emits a
small JSON object. It never calls Home Assistant services and never writes to
SolarEdge.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from statistics import median
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

TOOL_VERSION = "1.1.0"
VALID_ACTIONS = {"holdcharge", "normal", "charge", "hold"}
ACTION_THRESHOLD_W = 100.0
HARD_SLOT_MAX_AGE_MIN = 120.0


def parse_time(value: Any) -> datetime | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (TypeError, ValueError):
        return None


def fnum(value: Any, default: float | None = 0.0) -> float | None:
    try:
        number = float(value)
        if not math.isfinite(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def bval(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def avg_power_w(energy_wh: float, duration_s: float) -> float:
    return energy_wh * 3600.0 / duration_s if duration_s > 0 else 0.0


def fetch_json(url: str, timeout: float = 15.0) -> tuple[Any, float]:
    started = time.monotonic()
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "se-nf-evopt-shadow/1.0"})
    with urlopen(request, timeout=timeout) as response:
        if not 200 <= response.status < 300:
            raise RuntimeError(f"HTTP {response.status}")
        payload = json.load(response)
    return payload, (time.monotonic() - started) * 1000.0


def read_json_file(path: str | None) -> Any:
    if not path:
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def path_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "str"
    if isinstance(value, list):
        return "list"
    if isinstance(value, dict):
        return "dict"
    return type(value).__name__


def schema_fingerprint(req: dict[str, Any], res: dict[str, Any], details: dict[str, Any], rb: dict[str, Any], sb: dict[str, Any]) -> str:
    ts = req.get("time_series") if isinstance(req.get("time_series"), dict) else {}
    payload = {
        "req_keys": sorted(req.keys()),
        "res_keys": sorted(res.keys()),
        "details_keys": sorted(details.keys()),
        "time_series_keys": sorted(ts.keys()),
        "battery_req_keys": sorted(rb.keys()),
        "battery_res_keys": sorted(sb.keys()),
        "req_types": {k: path_type(req.get(k)) for k in sorted(req)},
        "res_types": {k: path_type(res.get(k)) for k in sorted(res)},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def first_power_event(values: list[float], durations: list[float], timestamps: list[str], threshold_w: float = 100.0) -> str | None:
    for index, energy in enumerate(values):
        if index < len(durations) and avg_power_w(energy, durations[index]) > threshold_w:
            return timestamps[index] if index < len(timestamps) else None
    return None


def select_battery_index(details_batteries: list[Any], req_batteries: list[Any], res_batteries: list[Any], title: str, name: str) -> tuple[int | None, str]:
    candidates: list[int] = []
    for index, item in enumerate(details_batteries):
        if not isinstance(item, dict):
            continue
        title_match = bool(title) and str(item.get("title", "")).strip() == title
        name_match = bool(name) and str(item.get("name", "")).strip() == name
        if title_match or name_match:
            candidates.append(index)
    if len(candidates) == 1:
        return candidates[0], "identity_match"
    if len(candidates) > 1:
        return None, "identity_ambiguous"
    if len(details_batteries) == len(req_batteries) == len(res_batteries) == 1:
        return 0, "single_battery_fallback"
    return None, "not_found"


def select_device(devices: list[Any], title: str, name: str, capacity_kwh: float | None) -> tuple[dict[str, Any] | None, str]:
    exact: list[dict[str, Any]] = []
    for item in devices:
        if not isinstance(item, dict):
            continue
        if (title and str(item.get("title", "")).strip() == title) or (name and str(item.get("name", "")).strip() == name):
            exact.append(item)
    if len(exact) == 1:
        return exact[0], "identity_match"
    if len(exact) > 1 and capacity_kwh is not None:
        narrowed = [x for x in exact if abs((fnum(x.get("capacity"), -999.0) or -999.0) - capacity_kwh) <= 0.25]
        if len(narrowed) == 1:
            return narrowed[0], "identity_capacity_match"
        return None, "identity_ambiguous"
    if len(devices) == 1 and isinstance(devices[0], dict):
        return devices[0], "single_battery_fallback"
    return None, "not_found"


def current_slot_index(timestamps: list[str], durations: list[float], now: datetime) -> int | None:
    parsed = [parse_time(item) for item in timestamps]
    for index, start in enumerate(parsed):
        if start is None or index >= len(durations):
            continue
        end_ts = start.timestamp() + durations[index]
        if start.timestamp() - 2 <= now.timestamp() < end_ts + 2:
            return index
    return None


def derive_action_from_slot(
    suggestion: dict[str, Any],
    charge_w: float,
    discharge_w: float,
    import_w: float,
    export_w: float,
    threshold_w: float = ACTION_THRESHOLD_W,
) -> tuple[str, str]:
    """Return the EVOpt action and the source used to derive it.

    evcc 0.312 may omit battery.devices[].suggestion.action even though the
    optimizer plan is complete. In that case the current optimizer slot is the
    authoritative fallback:

    - planned grid charging -> charge
    - planned PV charging -> normal
    - planned battery discharge -> holdcharge
    - planned export while battery stays idle -> holdcharge
    - planned grid import while battery stays idle -> hold
    - otherwise -> normal

    Simultaneous contradictory flows are rejected as unknown so Home Assistant
    falls back safely instead of guessing.
    """
    explicit = str(suggestion.get("action") or "").strip().lower()
    if explicit in VALID_ACTIONS:
        return explicit, "suggestion"

    charge_active = charge_w > threshold_w
    discharge_active = discharge_w > threshold_w
    import_active = import_w > threshold_w
    export_active = export_w > threshold_w

    if charge_active and discharge_active:
        return "unknown", "slot_conflict_charge_discharge"
    if import_active and export_active:
        return "unknown", "slot_conflict_import_export"

    if charge_active:
        if import_active:
            return "charge", "slot_grid_charge"
        return "normal", "slot_pv_charge"

    if discharge_active:
        return "holdcharge", "slot_discharge"

    if export_active:
        return "holdcharge", "slot_export"

    if import_active:
        return "hold", "slot_grid_import_hold"

    return "normal", "slot_neutral"


def action_matches_slot(
    action: str,
    charge_w: float,
    discharge_w: float,
    import_w: float,
    export_w: float,
    threshold_w: float = ACTION_THRESHOLD_W,
) -> bool:
    """Validate that the selected action can reproduce the optimizer slot."""
    if action == "holdcharge":
        # Charging is blocked, while discharge and export are explicitly
        # allowed. The old implementation incorrectly required discharge=0.
        return charge_w < threshold_w
    if action == "hold":
        # Discharge is blocked; PV charging may still happen. Grid charging
        # belongs to the dedicated `charge` action.
        return (
            discharge_w < threshold_w
            and not (charge_w > threshold_w and import_w > threshold_w)
        )
    if action == "charge":
        # `charge` is the only action that deliberately enables grid charging.
        return charge_w > threshold_w and import_w > threshold_w
    if action == "normal":
        return True
    return False


def evaluate_freshness(
    age_min: float | None,
    max_age_min: float,
    current_slot_present: bool,
) -> tuple[bool, bool, bool, float]:
    """Evaluate update age without discarding an active optimizer slot.

    A current slot remains usable for a bounded grace period even when the full
    optimizer result was not regenerated inside the normal freshness window.
    The hard 120-minute limit prevents using an indefinitely stale plan.
    """
    normal_limit = max(max_age_min, 1.0)
    hard_limit = max(normal_limit, HARD_SLOT_MAX_AGE_MIN)
    fresh_by_update = (
        age_min is not None and -1.0 <= age_min <= normal_limit
    )
    slot_freshness_override = bool(
        age_min is not None
        and current_slot_present
        and -1.0 <= age_min <= hard_limit
        and not fresh_by_update
    )
    fresh = fresh_by_update or slot_freshness_override
    return fresh, fresh_by_update, slot_freshness_override, hard_limit


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str))
    return 0


def error_payload(message: str, evcc_url: str, response_ms: float | None = None) -> dict[str, Any]:
    return {
        "adapter_status": "error",
        "tool_version": TOOL_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "evcc_url": evcc_url,
        "evcc_reachable": False,
        "response_ms": round(response_ms, 1) if response_ms is not None else None,
        "data_healthy": False,
        "active_ready_raw": False,
        "health_reason": message[:240],
        "solver_status": "unavailable",
        "action_raw": "unavailable",
        "plan_consistent": False,
        "action_plan_consistent": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only EVOpt shadow adapter")
    parser.add_argument("--evcc-url", default="http://example.invalid:7070")
    parser.add_argument("--battery-title", default="SolarEdge Akku")
    parser.add_argument("--battery-name", default="")
    parser.add_argument("--max-age-min", type=float, default=25.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    parser.add_argument("--state-file")
    parser.add_argument("--evopt-file")
    parser.add_argument("--devices-file")
    parser.add_argument("--forecast-file")
    parser.add_argument("--evaluation-time", help="ISO time override for offline tests")
    args = parser.parse_args()

    evcc_url = str(args.evcc_url).strip().rstrip("/")
    if evcc_url.lower() in {"", "unknown", "unavailable", "none"}:
        evcc_url = "http://example.invalid:7070"
    battery_title = str(args.battery_title).strip()
    if battery_title.lower() in {"", "unknown", "unavailable", "none"}:
        battery_title = "SolarEdge Akku"
    battery_name = str(args.battery_name).strip()
    if battery_name.lower() in {"unknown", "unavailable", "none"}:
        battery_name = ""

    response_ms: float | None = None
    try:
        full_state = read_json_file(args.state_file)
        if full_state is None and not args.evopt_file:
            full_state, response_ms = fetch_json(evcc_url + "/api/state", args.timeout)
        if full_state is not None:
            if not isinstance(full_state, dict):
                raise RuntimeError("evcc /api/state liefert kein JSON-Objekt")
            evopt = full_state.get("evopt") or {}
            battery_root = full_state.get("battery") or {}
            devices = battery_root.get("devices") or []
            forecast = battery_root.get("forecast") or {}
            live_pv_w = fnum(full_state.get("pvPower"), None)
            live_home_w = fnum(full_state.get("homePower"), None)
            grid_root = full_state.get("grid") or {}
            live_grid_w = fnum(grid_root.get("power") if isinstance(grid_root, dict) else None, None)
            live_battery_w = fnum(battery_root.get("power") if isinstance(battery_root, dict) else None, None)
            evcc_version = full_state.get("version")
            tariff_grid = fnum(full_state.get("tariffGrid"), None)
            tariff_feedin = fnum(full_state.get("tariffFeedIn"), None)
        else:
            evopt = read_json_file(args.evopt_file) or {}
            devices = read_json_file(args.devices_file) or []
            forecast = read_json_file(args.forecast_file) or {}
            live_pv_w = live_home_w = live_grid_w = live_battery_w = None
            evcc_version = None
            tariff_grid = tariff_feedin = None
    except Exception as exc:
        return emit(error_payload(f"fetch_error: {exc}", evcc_url, response_ms))

    try:
        if not isinstance(evopt, dict):
            raise RuntimeError("evopt ist kein JSON-Objekt")
        req = evopt.get("req") if isinstance(evopt.get("req"), dict) else {}
        res = evopt.get("res") if isinstance(evopt.get("res"), dict) else {}
        details = evopt.get("details") if isinstance(evopt.get("details"), dict) else {}
        series = req.get("time_series") if isinstance(req.get("time_series"), dict) else {}

        timestamps = [str(x) for x in (details.get("timestamp") or [])]
        durations = [fnum(x, 0.0) or 0.0 for x in (series.get("dt") or [])]
        pv = [fnum(x, 0.0) or 0.0 for x in (series.get("ft") or [])]
        load = [fnum(x, 0.0) or 0.0 for x in (series.get("gt") or [])]
        feedin_prices = [fnum(x, 0.0) or 0.0 for x in (series.get("p_E") or [])]
        grid_prices = [fnum(x, 0.0) or 0.0 for x in (series.get("p_N") or [])]
        grid_export = [fnum(x, 0.0) or 0.0 for x in (res.get("grid_export") or [])]
        grid_import = [fnum(x, 0.0) or 0.0 for x in (res.get("grid_import") or [])]
        flow_direction = list(res.get("flow_direction") or [])

        req_batteries = list(req.get("batteries") or [])
        res_batteries = list(res.get("batteries") or [])
        detail_batteries = list(details.get("batteryDetails") or [])
        battery_index, battery_selection = select_battery_index(
            detail_batteries, req_batteries, res_batteries, battery_title, battery_name
        )
        if battery_index is None:
            raise RuntimeError(f"battery_{battery_selection}")
        if battery_index >= len(req_batteries) or battery_index >= len(res_batteries):
            raise RuntimeError("battery_index_out_of_range")
        rb = req_batteries[battery_index]
        sb = res_batteries[battery_index]
        if not isinstance(rb, dict) or not isinstance(sb, dict):
            raise RuntimeError("battery_plan_not_object")

        detail_battery = detail_batteries[battery_index] if battery_index < len(detail_batteries) and isinstance(detail_batteries[battery_index], dict) else {}
        selected_title = str(detail_battery.get("title") or battery_title)
        selected_name = str(detail_battery.get("name") or battery_name)

        charge = [fnum(x, 0.0) or 0.0 for x in (sb.get("charging_power") or [])]
        discharge = [fnum(x, 0.0) or 0.0 for x in (sb.get("discharging_power") or [])]
        soc_wh = [fnum(x, 0.0) or 0.0 for x in (sb.get("state_of_charge") or [])]

        arrays = {
            "timestamp": timestamps,
            "dt": durations,
            "ft": pv,
            "gt": load,
            "p_E": feedin_prices,
            "p_N": grid_prices,
            "charging": charge,
            "discharging": discharge,
            "soc": soc_wh,
            "grid_export": grid_export,
            "grid_import": grid_import,
            "flow_direction": flow_direction,
        }
        lengths = {key: len(value) for key, value in arrays.items()}
        slot_count = len(durations)
        arrays_equal = slot_count > 0 and all(length == slot_count for length in lengths.values())

        capacity_wh = fnum(rb.get("s_capacity"), 0.0) or 0.0
        s_initial = fnum(rb.get("s_initial"), 0.0) or 0.0
        s_min = fnum(rb.get("s_min"), 0.0) or 0.0
        s_max = fnum(rb.get("s_max"), 0.0) or 0.0
        c_max_w = fnum(rb.get("c_max"), 0.0) or 0.0
        d_max_w = fnum(rb.get("d_max"), 0.0) or 0.0
        eta_c = fnum(req.get("eta_c"), 1.0) or 1.0
        eta_d = fnum(req.get("eta_d"), 1.0) or 1.0

        balance_errors: list[float] = []
        soc_errors: list[float] = []
        timestamp_errors: list[float] = []
        power_limit_errors: list[float] = []
        parsed_times = [parse_time(x) for x in timestamps]
        previous = s_initial
        if arrays_equal:
            for index in range(slot_count):
                balance_errors.append(pv[index] + grid_import[index] + discharge[index] - load[index] - grid_export[index] - charge[index])
                expected_soc = previous + eta_c * charge[index] - (discharge[index] / eta_d if eta_d > 0 else 0.0)
                soc_errors.append(soc_wh[index] - expected_soc)
                previous = soc_wh[index]
                charge_allowed = c_max_w * durations[index] / 3600.0 if durations[index] > 0 else 0.0
                discharge_allowed = d_max_w * durations[index] / 3600.0 if durations[index] > 0 else 0.0
                power_limit_errors.extend([max(charge[index] - charge_allowed, 0.0), max(discharge[index] - discharge_allowed, 0.0)])
            for index in range(slot_count - 1):
                if parsed_times[index] is None or parsed_times[index + 1] is None:
                    timestamp_errors.append(math.inf)
                else:
                    timestamp_errors.append((parsed_times[index + 1] - parsed_times[index]).total_seconds() - durations[index])

        max_balance_error = max((abs(x) for x in balance_errors), default=math.inf)
        max_soc_error = max((abs(x) for x in soc_errors), default=math.inf)
        max_time_error = max((abs(x) for x in timestamp_errors), default=0.0 if slot_count == 1 else math.inf)
        max_power_limit_error = max(power_limit_errors, default=math.inf)
        cadence_s = median(durations[1:]) if slot_count > 1 else (durations[0] if durations else 0.0)

        now = parse_time(args.evaluation_time) if args.evaluation_time else datetime.now(timezone.utc)
        if now is None:
            now = datetime.now(timezone.utc)
        current_index = current_slot_index(timestamps, durations, now)
        current_slot_present = current_index is not None

        current: dict[str, Any] = {
            "slot_index": current_index,
            "slot_start": None,
            "slot_end": None,
            "slot_duration_s": None,
            "slot_pv_wh": None,
            "slot_load_wh": None,
            "slot_charge_wh": None,
            "slot_discharge_wh": None,
            "slot_grid_import_wh": None,
            "slot_grid_export_wh": None,
            "slot_pv_w": None,
            "slot_load_w": None,
            "slot_charge_w": None,
            "slot_discharge_w": None,
            "slot_grid_import_w": None,
            "slot_grid_export_w": None,
            "slot_soc_pct": None,
            "slot_grid_price_eur_kwh": None,
            "slot_feedin_price_eur_kwh": None,
        }
        if current_index is not None and arrays_equal:
            index = current_index
            duration = durations[index]
            start = parsed_times[index]
            current.update({
                "slot_start": timestamps[index],
                "slot_end": datetime.fromtimestamp(start.timestamp() + duration, tz=start.tzinfo).isoformat() if start else None,
                "slot_duration_s": round(duration, 1),
                "slot_pv_wh": round(pv[index], 3),
                "slot_load_wh": round(load[index], 3),
                "slot_charge_wh": round(charge[index], 3),
                "slot_discharge_wh": round(discharge[index], 3),
                "slot_grid_import_wh": round(grid_import[index], 3),
                "slot_grid_export_wh": round(grid_export[index], 3),
                "slot_pv_w": round(avg_power_w(pv[index], duration), 1),
                "slot_load_w": round(avg_power_w(load[index], duration), 1),
                "slot_charge_w": round(avg_power_w(charge[index], duration), 1),
                "slot_discharge_w": round(avg_power_w(discharge[index], duration), 1),
                "slot_grid_import_w": round(avg_power_w(grid_import[index], duration), 1),
                "slot_grid_export_w": round(avg_power_w(grid_export[index], duration), 1),
                "slot_soc_pct": round(100.0 * soc_wh[index] / capacity_wh, 3) if capacity_wh > 0 else None,
                "slot_grid_price_eur_kwh": round(grid_prices[index] * 1000.0, 6),
                "slot_feedin_price_eur_kwh": round(feedin_prices[index] * 1000.0, 6),
            })

        plan_consistent = bool(
            arrays_equal
            and 180 <= slot_count <= 193
            and 0 < cadence_s <= 901
            and max_balance_error <= 2.0
            and max_soc_error <= 2.0
            and max_time_error <= 1.0
            and max_power_limit_error <= 2.0
            and 0 <= s_min <= s_initial <= s_max <= capacity_wh
            and current_slot_present
        )

        device, device_selection = select_device(
            devices if isinstance(devices, list) else [],
            selected_title,
            selected_name,
            capacity_wh / 1000.0 if capacity_wh else None,
        )
        suggestion = (
            device.get("suggestion")
            if isinstance(device, dict) and isinstance(device.get("suggestion"), dict)
            else {}
        )
        actionable = bval(suggestion.get("actionable"))
        controllable = bval(device.get("controllable")) if isinstance(device, dict) else False
        battery_soc = fnum(device.get("soc"), None) if isinstance(device, dict) else None
        battery_capacity_kwh = fnum(device.get("capacity"), None) if isinstance(device, dict) else None

        charge_w = fnum(current.get("slot_charge_w"), 0.0) or 0.0
        discharge_w = fnum(current.get("slot_discharge_w"), 0.0) or 0.0
        export_w = fnum(current.get("slot_grid_export_w"), 0.0) or 0.0
        import_w = fnum(current.get("slot_grid_import_w"), 0.0) or 0.0

        if current_slot_present:
            action, action_source = derive_action_from_slot(
                suggestion,
                charge_w,
                discharge_w,
                import_w,
                export_w,
            )
            action_plan_consistent = action_matches_slot(
                action,
                charge_w,
                discharge_w,
                import_w,
                export_w,
            )
        else:
            explicit = str(suggestion.get("action") or "").strip().lower()
            action = explicit if explicit in VALID_ACTIONS else "unknown"
            action_source = (
                "suggestion_without_current_slot"
                if explicit in VALID_ACTIONS
                else "none"
            )
            action_plan_consistent = False

        updated = parse_time(evopt.get("updated"))
        age_min = (
            (now - updated.astimezone(timezone.utc)).total_seconds() / 60.0
            if updated
            else None
        )
        fresh, fresh_by_update, slot_freshness_override, hard_stale_limit_min = evaluate_freshness(
            age_min,
            args.max_age_min,
            current_slot_present,
        )
        solver_status = str(res.get("status") or "unknown")
        schema = schema_fingerprint(req, res, details, rb, sb)

        highest_index = max(range(slot_count), key=lambda i: soc_wh[i]) if arrays_equal and slot_count else None
        lowest_index = min(range(slot_count), key=lambda i: soc_wh[i]) if arrays_equal and slot_count else None
        forecast_highest = forecast.get("highest") if isinstance(forecast, dict) and isinstance(forecast.get("highest"), dict) else {}
        forecast_lowest = forecast.get("lowest") if isinstance(forecast, dict) and isinstance(forecast.get("lowest"), dict) else {}

        action_valid = action in VALID_ACTIONS
        soc_plausible = battery_soc is not None and 0.0 <= battery_soc <= 100.0
        capacity_plausible = battery_capacity_kwh is not None and 1.0 <= battery_capacity_kwh <= 100.0
        identity_consistent = device is not None and device_selection not in {"not_found", "identity_ambiguous"}
        core_gates = {
            "solver_optimal": solver_status.lower() == "optimal",
            "updated_parseable": updated is not None,
            "fresh": fresh,
            "battery_found": identity_consistent,
            "controllable": controllable,
            "action_valid": action_valid,
            "soc_plausible": soc_plausible,
            "capacity_plausible": capacity_plausible,
            "plan_consistent": plan_consistent,
        }
        failed = [key for key, value in core_gates.items() if not value]
        data_healthy = not failed
        active_ready_raw = data_healthy and action_plan_consistent
        if failed:
            health_reason = "failed_checks:" + ",".join(failed)
        elif not action_plan_consistent:
            health_reason = "failed_checks:action_plan_consistent"
        elif slot_freshness_override:
            health_reason = "ok:current_slot_valid_stale_update"
        else:
            health_reason = "ok"

        payload: dict[str, Any] = {
            "adapter_status": "ok",
            "tool_version": TOOL_VERSION,
            "created_at": now.isoformat(),
            "evcc_url": evcc_url,
            "evcc_reachable": True,
            "response_ms": round(response_ms, 1) if response_ms is not None else None,
            "evcc_version": evcc_version,
            "data_healthy": data_healthy,
            "active_ready_raw": active_ready_raw,
            "health_reason": health_reason,
            "solver_status": solver_status,
            "updated": updated.isoformat() if updated else "",
            "age_min": round(age_min, 3) if age_min is not None else None,
            "fresh": fresh,
            "fresh_by_update": fresh_by_update,
            "current_slot_valid": current_slot_present,
            "slot_freshness_override": slot_freshness_override,
            "hard_stale_limit_min": hard_stale_limit_min,
            "schema_fingerprint": schema,
            "battery_index": battery_index,
            "battery_selection": battery_selection,
            "device_selection": device_selection,
            "battery_title": selected_title,
            "battery_name": selected_name,
            "battery_controllable": controllable,
            "battery_actionable": actionable,
            "battery_soc_pct": round(battery_soc, 3) if battery_soc is not None else None,
            "battery_capacity_kwh": round(battery_capacity_kwh, 3) if battery_capacity_kwh is not None else None,
            "battery_plan_initial_soc_pct": round(100.0 * s_initial / capacity_wh, 3) if capacity_wh > 0 else None,
            "battery_plan_min_soc_pct": round(100.0 * s_min / capacity_wh, 3) if capacity_wh > 0 else None,
            "battery_plan_max_soc_pct": round(100.0 * s_max / capacity_wh, 3) if capacity_wh > 0 else None,
            "action_raw": action,
            "action_source": action_source,
            "action_inference_reason": action_source,
            "suggested_charge": fnum(suggestion.get("charge"), None),
            "suggested_discharge": fnum(suggestion.get("discharge"), None),
            "action_plan_consistent": action_plan_consistent,
            "plan_consistent": plan_consistent,
            "slot_count": slot_count,
            "horizon_hours": round(sum(durations) / 3600.0, 3) if durations else None,
            "cadence_s": round(cadence_s, 3) if durations else None,
            "max_balance_error_wh": round(max_balance_error, 6) if math.isfinite(max_balance_error) else None,
            "max_soc_recurrence_error_wh": round(max_soc_error, 6) if math.isfinite(max_soc_error) else None,
            "max_timestamp_error_s": round(max_time_error, 3) if math.isfinite(max_time_error) else None,
            "max_power_limit_error_wh": round(max_power_limit_error, 6) if math.isfinite(max_power_limit_error) else None,
            "first_charge_time": first_power_event(charge, durations, timestamps),
            "first_discharge_time": first_power_event(discharge, durations, timestamps),
            "first_grid_import_time": first_power_event(grid_import, durations, timestamps),
            "first_grid_export_time": first_power_event(grid_export, durations, timestamps),
            "plan_highest_soc_pct": round(100.0 * soc_wh[highest_index] / capacity_wh, 3) if highest_index is not None and capacity_wh > 0 else None,
            "plan_highest_soc_time": timestamps[highest_index] if highest_index is not None else None,
            "plan_lowest_soc_pct": round(100.0 * soc_wh[lowest_index] / capacity_wh, 3) if lowest_index is not None and capacity_wh > 0 else None,
            "plan_lowest_soc_time": timestamps[lowest_index] if lowest_index is not None else None,
            "forecast_highest_soc_pct": round(fnum(forecast_highest.get("soc"), 0.0) or 0.0, 3) if forecast_highest else None,
            "forecast_highest_time": forecast_highest.get("time") if forecast_highest else None,
            "forecast_lowest_soc_pct": round(fnum(forecast_lowest.get("soc"), 0.0) or 0.0, 3) if forecast_lowest else None,
            "forecast_lowest_time": forecast_lowest.get("time") if forecast_lowest else None,
            "live_pv_w": live_pv_w,
            "live_home_w": live_home_w,
            "live_grid_w": live_grid_w,
            "live_battery_w": live_battery_w,
            "tariff_grid_eur_kwh": tariff_grid,
            "tariff_feedin_eur_kwh": tariff_feedin,
        }
        payload.update(current)
        return emit(payload)
    except Exception as exc:
        return emit(error_payload(f"parse_error: {exc}", evcc_url, response_ms))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
    except Exception as exc:  # defensive: command_line sensor must always receive JSON
        emit(error_payload(f"fatal_error: {exc}", "unknown"))
        raise SystemExit(0)
