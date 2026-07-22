"""Test-only deterministic 24h replay. Never connects to real hardware."""

from __future__ import annotations

import asyncio
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from homeassistant.const import EVENT_CALL_SERVICE, EVENT_HOMEASSISTANT_STARTED, EVENT_TIME_CHANGED
from homeassistant.core import Event, HomeAssistant
from homeassistant.util import dt as dt_util

DOMAIN = "se_test_replay"
_LOGGER = logging.getLogger(__name__)
MODES = ("Eigenverbrauch maximieren", "Netzdienlich laden", "Akku schonen", "EVOpt optimiert")
TARGET = "number.test_storage_charge_limit"
FINGERPRINT = "9e512ccd98ecf53647904f8b8384104796eb89c869fa0c6cfee1a25a40cc86bc"
TZ = ZoneInfo("Europe/Berlin")
UTC = ZoneInfo("UTC")


def _safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe(v) for v in value]
    return str(value)


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _entities(data: dict[str, Any]) -> set[str]:
    values = [(data.get("service_data") or {}).get("entity_id"), (data.get("target") or {}).get("entity_id")]
    result: set[str] = set()
    for value in values:
        if isinstance(value, str):
            result.update(v.strip() for v in value.split(",") if v.strip())
        elif isinstance(value, (list, tuple, set)):
            result.update(str(v).strip() for v in value if str(v).strip())
    return result


class Runner:
    def __init__(self, hass: HomeAssistant, fixture: dict[str, Any], output: Path) -> None:
        self.hass, self.fixture, self.output = hass, fixture, output
        self.output.mkdir(parents=True, exist_ok=True)
        self.now = datetime(2031, 7, 21, tzinfo=TZ)
        self.mode: str | None = None
        self.slot: int | None = None
        self.phase = "startup"
        self.events: list[dict[str, Any]] = []
        self.snapshots: list[dict[str, Any]] = []
        self.intents: list[dict[str, Any]] = []
        self.calls: list[dict[str, Any]] = []
        self.changes: list[dict[str, Any]] = []
        self.hard: list[dict[str, Any]] = []
        self.expected: list[dict[str, Any]] = []
        self.unsub: list[Any] = []
        self.old_now, self.old_utcnow = dt_util.now, dt_util.utcnow

    def clock_now(self, zone: ZoneInfo | None = None) -> datetime:
        return self.now if zone is None else self.now.astimezone(zone)

    def clock_utcnow(self) -> datetime:
        return self.now.astimezone(UTC)

    def base(self, kind: str, event: Event[Any]) -> dict[str, Any]:
        ctx = event.context
        return {
            "event": kind,
            "simulated_at": self.now.isoformat(),
            "mode": self.mode,
            "slot": self.slot,
            "phase": self.phase,
            "context": {"id": ctx.id, "parent_id": ctx.parent_id, "user_id": ctx.user_id},
        }

    def listen(self) -> None:
        async def intent(event: Event[Any]) -> None:
            row = self.base("write_intent", event) | {"data": _safe(dict(event.data))}
            self.intents.append(row)
            self.events.append(row)

        async def service(event: Event[Any]) -> None:
            data = dict(event.data)
            entities = _entities(data)
            if TARGET not in entities:
                return
            row = self.base("call_service", event) | {
                "domain": data.get("domain"),
                "service": data.get("service"),
                "entities": sorted(entities),
                "data": _safe(data.get("service_data") or {}),
            }
            self.calls.append(row)
            self.events.append(row)

        async def changed(event: Event[Any]) -> None:
            if event.data.get("entity_id") != TARGET:
                return
            old, new = event.data.get("old_state"), event.data.get("new_state")
            row = self.base("state_changed", event) | {
                "old": getattr(old, "state", None),
                "new": getattr(new, "state", None),
            }
            if row["old"] != row["new"]:
                self.changes.append(row)
            self.events.append(row)

        async def automation(event: Event[Any]) -> None:
            entity = str(event.data.get("entity_id", ""))
            if "se_nf" in entity or "solaredge" in entity:
                self.events.append(self.base("automation_triggered", event) | {"data": _safe(dict(event.data))})

        self.unsub = [
            self.hass.bus.async_listen("se_charge_limit_write_intent", intent),
            self.hass.bus.async_listen(EVENT_CALL_SERVICE, service),
            self.hass.bus.async_listen("state_changed", changed),
            self.hass.bus.async_listen("automation_triggered", automation),
        ]

    async def settle(self) -> None:
        for _ in range(4):
            await asyncio.sleep(0)
        await asyncio.sleep(0.01)

    async def clock(self, value: datetime) -> None:
        self.now = value
        self.hass.bus.async_fire(EVENT_TIME_CHANGED, {"now": value.astimezone(UTC)})
        await self.settle()

    async def svc(self, domain: str, service: str, entity: str, **data: Any) -> None:
        await self.hass.services.async_call(domain, service, {"entity_id": entity, **data}, blocking=True)
        await self.settle()

    def state(self, entity: str) -> str:
        value = self.hass.states.get(entity)
        return value.state if value else "missing"

    async def wait_ready(self) -> None:
        required = (TARGET, "sensor.se_nf_desired_target", "sensor.se_nf_config_check", "sensor.se_nf_sanity_check")
        for _ in range(240):
            if all(self.hass.states.get(entity) for entity in required):
                return
            await asyncio.sleep(0.25)
        raise RuntimeError(f"missing replay entities: {[e for e in required if not self.hass.states.get(e)]}")

    async def configure(self) -> None:
        self.phase = "configure"
        await self.svc("input_boolean", "turn_off", "input_boolean.se_netzdienlich_enabled")
        mappings = {
            "input_text.se_nf_charge_limit_entity": TARGET,
            "input_text.se_nf_battery_soe_entity": "sensor.test_battery_soc",
            "input_text.se_nf_battery_capacity_entity": "sensor.test_battery_capacity",
            "input_text.se_nf_pv_today_remaining_entity": "sensor.test_pv_remaining",
            "input_text.se_nf_pv_today_total_entity": "sensor.test_pv_total",
            "input_text.se_nf_pv_tomorrow_entity": "sensor.test_pv_tomorrow",
            "input_text.se_nf_live_pv_power_entities": "sensor.test_pv_power",
            "input_text.se_nf_live_consumption_power_entities": "sensor.test_home_power",
        }
        for entity, value in mappings.items():
            await self.svc("input_text", "set_value", entity, value=value)
        numbers = {
            "input_number.se_nf_closed_charge_limit_w": 0,
            "input_number.se_nf_open_charge_limit_w": 5000,
            "input_number.se_nf_battery_capacity_kwh_fallback": 24.3,
            "input_number.se_nf_write_cooldown_s": 180,
            "input_number.se_nf_write_lock_s": 60,
            "input_number.se_nf_write_min_delta_w": 100,
            "input_number.se_nf_min_start_hour": 11.75,
            "input_number.se_nf_latest_finish_hour": 14.25,
            "input_number.se_nf_lifetime_min_start_hour": 14.25,
            "input_number.se_nf_lifetime_latest_finish_hour": 16,
        }
        for entity, value in numbers.items():
            if self.hass.states.get(entity):
                await self.svc("input_number", "set_value", entity, value=value)
        for entity in ("input_boolean.se_nf_site_config_confirmed", "input_boolean.se_nf_evopt_shadow_enabled", "input_boolean.se_netzdienlich_debug", "input_boolean.se_netzdienlich_enabled"):
            await self.svc("input_boolean", "turn_on", entity)
        await self.clock(self.now + timedelta(minutes=5))

    def evopt(self, row: dict[str, Any]) -> None:
        healthy = bool(row["evopt_healthy"])
        action = str(row["evopt_action"] if healthy else "unavailable")
        attrs = {
            "evcc_reachable": healthy,
            "plan_consistent": healthy,
            "action_plan_consistent": healthy,
            "data_healthy": healthy,
            "health_reason": "ok" if healthy else "test_outage",
            "solver_status": "optimal" if healthy else "unavailable",
            "updated": self.now.isoformat(),
            "age_min": 0 if healthy else 30,
            "schema_fingerprint": FINGERPRINT,
            "battery_controllable": True,
            "battery_actionable": True,
            "battery_soc_pct": row["soc_pct"],
            "battery_capacity_kwh": self.fixture["battery_capacity_kwh"],
            "action_raw": action,
            "action_source": "synthetic_replay",
            "suggestion_action": action,
            "suggestion_plan_consistent": healthy,
            "suggestion_overridden": False,
            "slot_action": action,
            "suggested_charge": 5000 if action == "charge" else 0,
            "suggested_discharge": 5000 if action == "discharge" else 0,
            "slot_index": row["slot"],
            "slot_start": self.now.isoformat(),
            "slot_duration_s": 900,
            "slot_pv_w": row["pv_w"],
            "slot_load_w": row["home_w"],
            "slot_charge_w": row["battery_charge_w"],
            "slot_discharge_w": row["battery_discharge_w"],
            "slot_grid_import_w": row["grid_import_w"],
            "slot_grid_export_w": row["grid_export_w"],
            "slot_soc_pct": row["soc_pct"],
            "cadence_s": 900,
            "max_balance_error_wh": abs(row["energy_balance_residual_w"]) / 4,
            "max_soc_recurrence_error_wh": 0,
            "max_timestamp_error_s": 0,
            "max_power_limit_error_wh": 0,
        }
        self.hass.states.async_set("sensor.se_nf_evopt_adapter_raw", "ok" if healthy else "error", attrs)

    async def measurements(self, row: dict[str, Any]) -> None:
        values = {
            "input_number.se_replay_battery_soc": row["soc_pct"],
            "input_number.se_replay_battery_capacity": self.fixture["battery_capacity_kwh"],
            "input_number.se_replay_pv_power": row["pv_w"],
            "input_number.se_replay_home_power": row["home_w"],
            "input_number.se_replay_pv_remaining": row["pv_forecast_remaining_kwh"],
            "input_number.se_replay_pv_total": row["pv_forecast_total_kwh"],
            "input_number.se_replay_pv_tomorrow": row["pv_forecast_tomorrow_kwh"],
        }
        for entity, value in values.items():
            await self.svc("input_number", "set_value", entity, value=value)
        self.evopt(row)
        await self.settle()

    async def prepare_day(self, mode: str, day: datetime) -> None:
        self.phase, self.mode, self.slot = "reset", None, None
        await self.svc("input_boolean", "turn_off", "input_boolean.se_netzdienlich_enabled")
        await self.svc("input_number", "set_value", "input_number.se_replay_charge_limit_backing", value=0)
        await self.svc("input_select", "select_option", "input_select.se_nf_session_state", option="closed")
        await self.svc("input_boolean", "turn_off", "input_boolean.se_nf_lifetime_target_reached")
        await self.clock(day)
        await self.svc("input_datetime", "set_datetime", "input_datetime.se_nf_session_planned_start", datetime=(day + timedelta(hours=11, minutes=45)).strftime("%Y-%m-%d %H:%M:%S"))
        await self.svc("input_select", "select_option", "input_select.se_nf_optimization_mode", option=mode)
        await self.svc("input_boolean", "turn_on", "input_boolean.se_netzdienlich_enabled")
        self.mode = mode
        await self.clock(day + timedelta(minutes=5))

    def snapshot(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "slot": self.slot,
            "time": row["time"],
            "simulated_at": self.now.isoformat(),
            "inputs": {"pv_w": row["pv_w"], "home_w": row["home_w"], "soc_pct": row["soc_pct"], "forecast_remaining_kwh": row["pv_forecast_remaining_kwh"], "evopt_action": row["evopt_action"], "evopt_healthy": row["evopt_healthy"]},
            "controller": {key: self.state(entity) for key, entity in {
                "effective_mode": "sensor.se_nf_optimization_mode_effective",
                "session": "input_select.se_nf_session_state",
                "control": "sensor.se_nf_active_control_label",
                "target": "sensor.se_nf_desired_target",
                "actual": TARGET,
                "reason": "sensor.se_nf_decision_reason",
                "writer_mode": "sensor.se_nf_writer_mode",
                "config": "sensor.se_nf_config_check",
                "sanity": "sensor.se_nf_sanity_check",
                "risk": "binary_sensor.se_nf_risk_flag",
                "planned_start": "input_datetime.se_nf_session_planned_start",
                "need_kwh": "sensor.se_nf_needed_energy",
            }.items()},
            "evopt": {key: self.state(entity) for key, entity in {
                "raw": "sensor.se_nf_evopt_action_raw",
                "stable": "sensor.se_nf_evopt_action_stable",
                "status": "sensor.se_nf_evopt_status",
                "active": "binary_sensor.se_nf_evopt_active_control",
                "block": "binary_sensor.se_nf_evopt_charge_block_request",
                "fallback": "binary_sensor.se_nf_evopt_fallback_active",
                "fallback_code": "sensor.se_nf_evopt_fallback_code",
                "source": "sensor.se_nf_evopt_candidate_source",
                "candidate": "sensor.se_nf_evopt_candidate_target_w",
            }.items()},
        }

    def validate(self, snap: dict[str, Any]) -> None:
        ctrl = snap["controller"]
        for key in ("target", "actual"):
            value = _float(ctrl[key])
            if value is None or not 0 <= value <= 5000:
                self.hard.append({"type": "invalid_limit", "field": key, "snapshot": snap})
        if ctrl["config"] != "ok" or ctrl["sanity"] != "ok" or ctrl["risk"] == "on":
            self.hard.append({"type": "safety_state", "snapshot": snap})
        if self.mode == "EVOpt optimiert" and snap["inputs"]["evopt_action"] == "holdcharge" and (_float(ctrl["actual"]) or 0) > 50:
            self.hard.append({"type": "holdcharge_not_closed", "snapshot": snap})
        if self.mode == "EVOpt optimiert" and snap["inputs"]["evopt_action"] == "discharge" and snap["evopt"]["active"] != "on":
            self.expected.append({"type": "discharge_capability_fallback", "slot": self.slot, "time": snap["time"]})

    def analyse_writes(self) -> dict[str, Any]:
        by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in self.intents:
            if row["mode"] in MODES:
                data = row["data"]
                by_mode[row["mode"]].append({"at": row["simulated_at"], "slot": row["slot"], "value": _float(data.get("requested_value")), "source": data.get("evopt_candidate_source"), "reason": data.get("decision_reason")})
        for mode, writes in by_mode.items():
            for a, b, c in zip(writes, writes[1:], writes[2:]):
                if a["value"] == c["value"] != b["value"] and datetime.fromisoformat(c["at"]) - datetime.fromisoformat(a["at"]) <= timedelta(minutes=30):
                    item = {"mode": mode, "first": a, "middle": b, "last": c}
                    if mode == "EVOpt optimiert" and "legacy" in {a["source"], b["source"], c["source"]}:
                        self.expected.append({"type": "roundtrip", "classification": "expected_fallback_recovery", **item})
                    else:
                        self.hard.append({"type": "roundtrip", "classification": "unexpected_flapping", **item})
        return {mode: by_mode.get(mode, []) for mode in MODES}

    async def run(self) -> None:
        self.listen()
        dt_util.now, dt_util.utcnow = self.clock_now, self.clock_utcnow
        summary: dict[str, Any]
        try:
            await self.wait_ready()
            await self.configure()
            for index, mode in enumerate(MODES):
                day = datetime(2031, 7, 21 + index, tzinfo=TZ)
                await self.prepare_day(mode, day)
                for row in self.fixture["records"]:
                    self.phase, self.slot = "slot", int(row["slot"])
                    start = day + timedelta(minutes=int(row["minute"]))
                    await self.clock(start)
                    await self.measurements(row)
                    for seconds in (60, 120, 180, 300):
                        await self.clock(start + timedelta(seconds=seconds))
                    snap = self.snapshot(row)
                    self.snapshots.append(snap)
                    self.validate(snap)
            self.phase, self.mode, self.slot = "shutdown", None, None
            await self.svc("input_boolean", "turn_off", "input_boolean.se_netzdienlich_enabled")
            writes = self.analyse_writes()
            counts = Counter(row["mode"] for row in self.snapshots)
            if counts != Counter({mode: 96 for mode in MODES}):
                self.hard.append({"type": "incomplete_modes", "counts": dict(counts)})
            unexpected = max(len(self.calls) - len(self.intents), 0)
            if unexpected:
                self.hard.append({"type": "unexpected_writer", "count": unexpected})
            if self.state("input_boolean.se_netzdienlich_enabled") != "off":
                self.hard.append({"type": "master_not_off"})
            summary = {"schema_version": 1, "pass": not self.hard, "fixture": self.fixture["name"], "source_date": self.fixture["source_date"], "modes": list(MODES), "snapshots": len(self.snapshots), "snapshots_per_mode": dict(counts), "write_intents": len(self.intents), "write_calls": len(self.calls), "actual_changes": len(self.changes), "unexpected_writers": unexpected, "hard_conflict_count": len(self.hard), "expected_conflict_count": len(self.expected), "hard_conflicts": self.hard, "expected_conflicts": self.expected, "writes": writes, "master_after_replay": self.state("input_boolean.se_netzdienlich_enabled"), "real_hardware_connected": False, "writer_target": TARGET}
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("24h replay failed")
            summary = {"schema_version": 1, "pass": False, "error": f"{type(exc).__name__}: {exc}", "snapshots": len(self.snapshots), "hard_conflicts": self.hard, "expected_conflicts": self.expected, "real_hardware_connected": False}
        finally:
            for name, rows in (("snapshots.jsonl", self.snapshots), ("events.jsonl", self.events), ("write_intents.jsonl", self.intents), ("actual_changes.jsonl", self.changes)):
                with (self.output / name).open("w", encoding="utf-8") as handle:
                    for row in rows:
                        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
            (self.output / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            dt_util.now, dt_util.utcnow = self.old_now, self.old_utcnow
            for callback in self.unsub:
                callback()
        _LOGGER.warning("SE_24H_REPLAY_DONE|pass=%s|snapshots=%s|hard=%s|expected=%s|writes=%s|master=%s", str(summary.get("pass", False)).lower(), summary.get("snapshots", 0), summary.get("hard_conflict_count", len(summary.get("hard_conflicts", []))), summary.get("expected_conflict_count", len(summary.get("expected_conflicts", []))), summary.get("write_intents", len(self.intents)), summary.get("master_after_replay", "unknown"))


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    settings = config.get(DOMAIN, {}) or {}
    fixture = json.loads(Path(str(settings.get("fixture", "/config/testbench/real_day_2026-07-21_15m.json"))).read_text(encoding="utf-8"))
    if "records" not in fixture:
        fixture["records"] = [dict(zip(fixture["columns"], row, strict=True)) for row in fixture["rows"]]
    output = Path(str(settings.get("output_dir", "/config/se_24h_results")))

    async def started(_: Event[Any]) -> None:
        hass.async_create_task(Runner(hass, fixture, output).run(), "SolarEdge 24h replay")

    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, started)
    return True
