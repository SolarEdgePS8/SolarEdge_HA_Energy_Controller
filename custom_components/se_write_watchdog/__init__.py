"""SolarEdge charge-limit write watchdog.

This custom integration observes every number.set_value service call targeting the
configured SolarEdge charge-limit entity. It records the Home Assistant context
chain, resolves automation/script/user sources, correlates service calls with
actual state changes, detects rapid round trips, and checks EVOpt consistency.
"""

from __future__ import annotations

import json
import logging
import re
import time
from collections import OrderedDict, deque
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

import voluptuous as vol

from homeassistant.const import (
    ATTR_ENTITY_ID,
    EVENT_CALL_SERVICE,
    EVENT_HOMEASSISTANT_STOP,
    EVENT_STATE_CHANGED,
)
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

DOMAIN = "se_write_watchdog"
STORAGE_VERSION = 1
STORAGE_KEY = DOMAIN

DEFAULT_WATCHED_ENTITY = "number.solaredge_i1_storage_charge_limit"
DEFAULT_MAPPING_HELPER = "input_text.se_nf_charge_limit_entity"
DEFAULT_ALLOWED_WRITERS = ["automation.solaredge_netzdienlich_v2_8_single_writer"]
DEFAULT_INTENT_EVENT = "se_charge_limit_write_intent"

CONF_WATCHED_ENTITY = "watched_entity"
CONF_MAPPING_HELPER = "mapping_helper"
CONF_ALLOWED_WRITERS = "allowed_writers"
CONF_INTENT_EVENT = "intent_event"
CONF_RAPID_WINDOW = "rapid_window_seconds"
CONF_BURST_WINDOW = "burst_window_seconds"
CONF_BURST_COUNT = "burst_change_count"
CONF_FLAP_HOLD = "flap_hold_seconds"
CONF_MISMATCH_GRACE = "mismatch_grace_seconds"
CONF_CORRELATION_WINDOW = "correlation_window_seconds"
CONF_RETENTION_DAYS = "retention_days"
CONF_NOTIFICATIONS = "notifications"

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Optional(CONF_WATCHED_ENTITY, default=DEFAULT_WATCHED_ENTITY): cv.entity_id,
                vol.Optional(CONF_MAPPING_HELPER, default=DEFAULT_MAPPING_HELPER): cv.entity_id,
                vol.Optional(CONF_ALLOWED_WRITERS, default=DEFAULT_ALLOWED_WRITERS): vol.All(
                    cv.ensure_list, [cv.entity_id]
                ),
                vol.Optional(CONF_INTENT_EVENT, default=DEFAULT_INTENT_EVENT): cv.string,
                vol.Optional(CONF_RAPID_WINDOW, default=180): vol.All(
                    vol.Coerce(int), vol.Range(min=30, max=3600)
                ),
                vol.Optional(CONF_BURST_WINDOW, default=600): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=7200)
                ),
                vol.Optional(CONF_BURST_COUNT, default=4): vol.All(
                    vol.Coerce(int), vol.Range(min=2, max=50)
                ),
                vol.Optional(CONF_FLAP_HOLD, default=1800): vol.All(
                    vol.Coerce(int), vol.Range(min=60, max=86400)
                ),
                vol.Optional(CONF_MISMATCH_GRACE, default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=600)
                ),
                vol.Optional(CONF_CORRELATION_WINDOW, default=30): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=300)
                ),
                vol.Optional(CONF_RETENTION_DAYS, default=14): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=365)
                ),
                vol.Optional(CONF_NOTIFICATIONS, default=True): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

RELEVANT_ENTITIES = (
    "sensor.se_nf_desired_target",
    "sensor.se_nf_charge_limit_actual",
    "sensor.se_nf_writer_mode",
    "sensor.se_nf_decision_reason",
    "sensor.se_nf_evopt_action_raw",
    "sensor.se_nf_evopt_action_stable",
    "binary_sensor.se_nf_evopt_charge_block_request",
    "binary_sensor.se_nf_evopt_active_control",
    "sensor.se_nf_evopt_candidate_source",
    "sensor.se_nf_evopt_candidate_target_w",
    "sensor.se_nf_optimization_mode_effective",
    "input_select.se_nf_optimization_mode",
    "input_select.se_nf_session_state",
    "sensor.se_nf_active_control_label",
    "sensor.se_nf_config_check",
    "sensor.se_nf_sanity_check",
    "binary_sensor.se_nf_controller_write_enabled",
    "input_boolean.se_netzdienlich_enabled",
    "input_datetime.se_nf_last_write",
    "input_datetime.se_nf_write_lock_until",
)

COUNTER_KEYS = (
    "write_calls_today",
    "duplicate_write_calls_today",
    "state_changes_today",
    "roundtrips_today",
    "unexpected_write_calls_today",
    "unattributed_state_changes_today",
    "evopt_mismatches_today",
)


def _safe_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _context_value(context: Any, key: str) -> str | None:
    value = getattr(context, key, None)
    if value is None:
        return None
    return str(value)


def _event_origin(event: Event) -> str:
    origin = getattr(event, "origin", None)
    if origin is None:
        return "unknown"
    return getattr(origin, "value", str(origin))


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


class SolarEdgeWriteWatchdog:
    """Runtime watchdog and audit logger."""

    def __init__(self, hass: HomeAssistant, config: dict[str, Any]) -> None:
        self.hass = hass
        self.config = config
        self.configured_entity: str = config[CONF_WATCHED_ENTITY]
        self.mapping_helper: str = config[CONF_MAPPING_HELPER]
        self.allowed_writers: set[str] = set(config[CONF_ALLOWED_WRITERS])
        self.intent_event: str = config[CONF_INTENT_EVENT]
        self.rapid_window: int = config[CONF_RAPID_WINDOW]
        self.burst_window: int = config[CONF_BURST_WINDOW]
        self.burst_count: int = config[CONF_BURST_COUNT]
        self.flap_hold: int = config[CONF_FLAP_HOLD]
        self.mismatch_grace: int = config[CONF_MISMATCH_GRACE]
        self.correlation_window: int = config[CONF_CORRELATION_WINDOW]
        self.retention_days: int = config[CONF_RETENTION_DAYS]
        self.notifications: bool = config[CONF_NOTIFICATIONS]

        self.log_dir = Path(hass.config.path(DOMAIN))
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

        self.contexts: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.pending_intents: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self.recent_write_calls: deque[dict[str, Any]] = deque(maxlen=100)
        self.state_history: deque[tuple[float, str]] = deque(maxlen=200)
        self.recent_records: deque[dict[str, Any]] = deque(maxlen=100)

        self.counters: dict[str, int] = {key: 0 for key in COUNTER_KEYS}
        self.counter_date = datetime.now().date().isoformat()

        self.last_write_call: dict[str, Any] | None = None
        self.last_state_change: dict[str, Any] | None = None
        self.last_unexpected: dict[str, Any] | None = None
        self.last_scan: dict[str, Any] = {"count": 0, "candidates": []}

        self.flap_until = 0.0
        self.flap_reason = ""
        self.mismatch_since = 0.0
        self.mismatch_signature = ""
        self.mismatch_active = False
        self.mismatch_reasons: list[str] = []
        self._mismatch_cancel = None
        self._flap_cancel = None
        self._save_cancel = None
        self._unsubs: list[Any] = []

    @property
    def watched_entity(self) -> str:
        """Return mapped target when valid, otherwise configured fallback."""
        mapped = self.hass.states.get(self.mapping_helper)
        if mapped is not None:
            candidate = mapped.state.strip()
            if candidate.startswith("number.") and candidate not in {
                "unknown",
                "unavailable",
                "none",
                "",
            }:
                return candidate
        return self.configured_entity

    async def async_setup(self) -> None:
        await self.hass.async_add_executor_job(
            partial(self.log_dir.mkdir, parents=True, exist_ok=True)
        )
        stored = await self.store.async_load() or {}
        if stored.get("date") == self.counter_date:
            for key in COUNTER_KEYS:
                self.counters[key] = int(stored.get("counters", {}).get(key, 0))

        self._unsubs.extend(
            [
                self.hass.bus.async_listen("automation_triggered", self._on_automation_triggered),
                self.hass.bus.async_listen("script_started", self._on_script_started),
                self.hass.bus.async_listen(self.intent_event, self._on_intent),
                self.hass.bus.async_listen(EVENT_CALL_SERVICE, self._on_call_service),
                self.hass.bus.async_listen(EVENT_STATE_CHANGED, self._on_state_changed),
                self.hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, self._on_stop),
                async_track_time_change(
                    self.hass, self._on_midnight, hour=0, minute=0, second=5
                ),
            ]
        )

        self.hass.services.async_register(DOMAIN, "reset_counters", self._service_reset)
        self.hass.services.async_register(DOMAIN, "rescan", self._service_rescan)
        self.hass.services.async_register(
            DOMAIN,
            "mark_test",
            self._service_mark_test,
            schema=vol.Schema({vol.Optional("note", default="manual test"): cv.string}),
        )
        self.hass.services.async_register(DOMAIN, "dump_report", self._service_dump_report)

        await self.async_scan_writers()
        self._publish_all()
        await self._write_record(
            {
                "event": "watchdog_started",
                "watched_entity": self.watched_entity,
                "allowed_writers": sorted(self.allowed_writers),
                "config": _jsonable(self.config),
                "snapshot": self._snapshot(),
            }
        )
        await self._cleanup_old_logs()
        _LOGGER.info("SolarEdge Write Watchdog started for %s", self.watched_entity)

    @callback
    def _remember_context(
        self,
        event: Event,
        *,
        source_type: str | None = None,
        source_entity: str | None = None,
        source_name: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        context_id = _context_value(event.context, "id")
        if not context_id:
            return
        old = self.contexts.pop(context_id, {})
        node = {
            **old,
            "context_id": context_id,
            "parent_id": _context_value(event.context, "parent_id"),
            "user_id": _context_value(event.context, "user_id"),
            "time": time.time(),
            "event_type": event.event_type,
            "origin": _event_origin(event),
        }
        if source_type:
            node["source_type"] = source_type
        if source_entity:
            node["source_entity"] = source_entity
        if source_name:
            node["source_name"] = source_name
        if details:
            node["details"] = _jsonable(details)
        self.contexts[context_id] = node
        while len(self.contexts) > 1000:
            self.contexts.popitem(last=False)

    async def _on_automation_triggered(self, event: Event) -> None:
        self._remember_context(
            event,
            source_type="automation",
            source_entity=event.data.get("entity_id"),
            source_name=event.data.get("name"),
            details=event.data,
        )

    async def _on_script_started(self, event: Event) -> None:
        self._remember_context(
            event,
            source_type="script",
            source_entity=event.data.get("entity_id"),
            source_name=event.data.get("name"),
            details=event.data,
        )

    async def _on_intent(self, event: Event) -> None:
        self._remember_context(event, details=event.data)
        context_id = _context_value(event.context, "id")
        if not context_id:
            return
        intent = {
            "time": time.time(),
            "context_id": context_id,
            "parent_id": _context_value(event.context, "parent_id"),
            "user_id": _context_value(event.context, "user_id"),
            "data": _jsonable(event.data),
        }
        self.pending_intents[context_id] = intent
        while len(self.pending_intents) > 200:
            self.pending_intents.popitem(last=False)
        await self._write_record({"event": "write_intent", **intent, "snapshot": self._snapshot()})

    def _extract_entity_ids(self, event: Event) -> set[str]:
        ids: set[str] = set()
        service_data = event.data.get("service_data") or {}
        candidates: list[Any] = [
            service_data.get(ATTR_ENTITY_ID),
            event.data.get(ATTR_ENTITY_ID),
        ]
        for target in (service_data.get("target"), event.data.get("target")):
            if isinstance(target, dict):
                candidates.append(target.get(ATTR_ENTITY_ID))
        for candidate in candidates:
            if isinstance(candidate, str):
                ids.update(part.strip() for part in candidate.split(",") if part.strip())
            elif isinstance(candidate, (list, tuple, set)):
                ids.update(str(part).strip() for part in candidate if str(part).strip())
        return ids

    def _context_chain(self, context_id: str | None, parent_id: str | None) -> list[dict[str, Any]]:
        chain: list[dict[str, Any]] = []
        seen: set[str] = set()
        current = context_id or parent_id
        fallback_parent = parent_id
        for _ in range(10):
            if not current or current in seen:
                break
            seen.add(current)
            node = self.contexts.get(current)
            if node:
                chain.append(dict(node))
                current = node.get("parent_id")
            elif current == context_id and fallback_parent:
                chain.append({"context_id": current, "parent_id": fallback_parent})
                current = fallback_parent
            else:
                break
        return chain

    async def _resolve_source(self, event: Event) -> dict[str, Any]:
        context_id = _context_value(event.context, "id")
        parent_id = _context_value(event.context, "parent_id")
        chain = self._context_chain(context_id, parent_id)
        for node in chain:
            if node.get("source_type") in {"automation", "script"}:
                return {
                    "type": node.get("source_type"),
                    "entity_id": node.get("source_entity"),
                    "name": node.get("source_name"),
                    "context_chain": chain,
                }

        intent = self._find_intent(context_id, parent_id)
        if intent:
            writer = intent.get("data", {}).get("writer")
            if writer:
                return {
                    "type": "intent",
                    "entity_id": writer,
                    "name": writer,
                    "context_chain": chain,
                }

        user_id = _context_value(event.context, "user_id")
        if user_id:
            user_name = user_id
            try:
                user = await self.hass.auth.async_get_user(user_id)
                if user is not None:
                    user_name = user.name
            except Exception:  # pragma: no cover - defensive only
                _LOGGER.debug("Could not resolve Home Assistant user %s", user_id)
            return {
                "type": "user_or_api",
                "entity_id": None,
                "name": user_name,
                "user_id": user_id,
                "context_chain": chain,
            }

        return {
            "type": "integration_or_supervisor",
            "entity_id": None,
            "name": "unresolved local source",
            "context_chain": chain,
        }

    def _find_intent(self, context_id: str | None, parent_id: str | None) -> dict[str, Any] | None:
        now = time.time()
        for candidate in (context_id, parent_id):
            if candidate and candidate in self.pending_intents:
                intent = self.pending_intents[candidate]
                if now - float(intent.get("time", 0)) <= 10:
                    return intent
        for intent in reversed(self.pending_intents.values()):
            if now - float(intent.get("time", 0)) > 5:
                break
            return intent
        return None

    async def _on_call_service(self, event: Event) -> None:
        self._remember_context(event, details=event.data)
        if event.data.get("domain") != "number" or event.data.get("service") != "set_value":
            return
        target = self.watched_entity
        entity_ids = self._extract_entity_ids(event)
        if target not in entity_ids:
            return

        source = await self._resolve_source(event)
        intent = self._find_intent(
            _context_value(event.context, "id"), _context_value(event.context, "parent_id")
        )
        service_data = event.data.get("service_data") or {}
        requested = _safe_float(service_data.get("value"))
        current_state = self.hass.states.get(target)
        current = _safe_float(current_state.state) if current_state else None
        duplicate = (
            requested is not None and current is not None and abs(requested - current) < 1
        )
        source_entity = source.get("entity_id")
        if not source_entity and intent:
            source_entity = intent.get("data", {}).get("writer")
        allowed = source_entity in self.allowed_writers

        self.counters["write_calls_today"] += 1
        if duplicate:
            self.counters["duplicate_write_calls_today"] += 1
        if not allowed:
            self.counters["unexpected_write_calls_today"] += 1

        record = {
            "event": "number_set_value_call",
            "target_entity": target,
            "requested_value": requested,
            "current_value_at_call": current,
            "duplicate": duplicate,
            "allowed_writer": allowed,
            "source": source,
            "intent": intent,
            "context_id": _context_value(event.context, "id"),
            "parent_id": _context_value(event.context, "parent_id"),
            "user_id": _context_value(event.context, "user_id"),
            "origin": _event_origin(event),
            "service_call_id": event.data.get("service_call_id"),
            "snapshot": self._snapshot(),
        }
        self.last_write_call = record
        self.recent_write_calls.append({**record, "time_epoch": time.time()})
        if not allowed:
            self.last_unexpected = record
        await self._write_record(record)
        self._publish_all()
        self._schedule_save()

        self.hass.bus.async_fire("se_write_watchdog_write_observed", _jsonable(record))
        await self._logbook(
            f"number.set_value {requested} W → {target}; Quelle: "
            f"{source_entity or source.get('name')}; erlaubt={allowed}; duplicate={duplicate}"
        )
        if not allowed:
            await self._notify_once(
                "unexpected_writer",
                "Unerwarteter SolarEdge-Schreibzugriff",
                f"Ein nicht freigegebener Aufrufer wollte {requested} W auf {target} schreiben.\n\n"
                f"Quelle: {source_entity or source.get('name')}\n"
                f"Kontext: {_context_value(event.context, 'id')}\n"
                f"Details: /config/{DOMAIN}/events-{self.counter_date}.jsonl",
            )
        await self._evaluate_mismatch()

    async def _on_state_changed(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        if entity_id == self.mapping_helper:
            await self._write_record(
                {
                    "event": "watched_entity_mapping_changed",
                    "new_target": self.watched_entity,
                    "context_id": _context_value(event.context, "id"),
                }
            )
            await self.async_scan_writers()
            self._publish_all()
            return

        if entity_id in RELEVANT_ENTITIES:
            await self._evaluate_mismatch()
            return

        if entity_id != self.watched_entity:
            return

        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if old_state is None or new_state is None or old_state.state == new_state.state:
            return

        now = time.time()
        source = await self._resolve_source(event)
        old_value = _safe_float(old_state.state)
        new_value = _safe_float(new_state.state)
        correlated_call = self._correlate_call(now, new_value)
        if correlated_call:
            source = correlated_call.get("source", source)
        attributable = correlated_call is not None or source.get("entity_id") is not None
        if not attributable:
            self.counters["unattributed_state_changes_today"] += 1

        self.counters["state_changes_today"] += 1
        if not self.state_history:
            self.state_history.append((now - 0.001, old_state.state))
        self.state_history.append((now, new_state.state))
        self._prune_state_history(now)

        roundtrip = False
        if len(self.state_history) >= 3:
            t0, v0 = self.state_history[-3]
            _t1, v1 = self.state_history[-2]
            t2, v2 = self.state_history[-1]
            roundtrip = v0 == v2 and v0 != v1 and (t2 - t0) <= self.rapid_window
        if roundtrip:
            self.counters["roundtrips_today"] += 1
            await self._set_flapping(
                f"Roundtrip {self.state_history[-3][1]}→{self.state_history[-2][1]}→{self.state_history[-1][1]} "
                f"in {self.state_history[-1][0] - self.state_history[-3][0]:.1f}s"
            )
        elif len(self.state_history) - 1 >= self.burst_count:
            await self._set_flapping(
                f"{len(self.state_history) - 1} Zustandswechsel innerhalb {self.burst_window}s"
            )

        record = {
            "event": "charge_limit_state_change",
            "target_entity": entity_id,
            "old_value": old_state.state,
            "new_value": new_state.state,
            "roundtrip_detected": roundtrip,
            "attributed": attributable,
            "source": source,
            "correlated_write_call": correlated_call,
            "context_id": _context_value(event.context, "id"),
            "parent_id": _context_value(event.context, "parent_id"),
            "user_id": _context_value(event.context, "user_id"),
            "origin": _event_origin(event),
            "snapshot": self._snapshot(),
        }
        self.last_state_change = record
        self.recent_records.append(record)
        await self._write_record(record)
        self._publish_all()
        self._schedule_save()
        await self._logbook(
            f"Charge Limit {old_state.state}→{new_state.state} W; Quelle: "
            f"{source.get('entity_id') or source.get('name')}; Roundtrip={roundtrip}"
        )
        if not attributable:
            await self._notify_once(
                "unattributed_change",
                "Nicht zugeordneter SolarEdge-Zustandswechsel",
                f"{entity_id} wechselte von {old_state.state} auf {new_state.state}, "
                "ohne korrelierbaren number.set_value-Aufruf. Prüfe das JSONL-Protokoll.",
            )
        await self._evaluate_mismatch()

    def _correlate_call(self, now: float, new_value: float | None) -> dict[str, Any] | None:
        for record in reversed(self.recent_write_calls):
            age = now - float(record.get("time_epoch", 0))
            if age > self.correlation_window:
                break
            requested = record.get("requested_value")
            if new_value is None or requested is None or abs(float(requested) - new_value) < 1:
                return record
        return None

    def _prune_state_history(self, now: float) -> None:
        while self.state_history and now - self.state_history[0][0] > self.burst_window:
            self.state_history.popleft()

    async def _set_flapping(self, reason: str) -> None:
        self.flap_reason = reason
        self.flap_until = max(self.flap_until, time.time() + self.flap_hold)
        if self._flap_cancel is not None:
            self._flap_cancel()
        self._flap_cancel = async_call_later(self.hass, self.flap_hold + 1, self._clear_flap_callback)
        await self._write_record(
            {"event": "flapping_detected", "reason": reason, "snapshot": self._snapshot()}
        )
        self._publish_all()
        await self._notify_once(
            "flapping",
            "SolarEdge Charge-Limit flattert",
            f"Erkannt: {reason}\n\nDetails: /config/{DOMAIN}/events-{self.counter_date}.jsonl",
        )

    @callback
    def _clear_flap_callback(self, _now: Any) -> None:
        self._flap_cancel = None
        if time.time() >= self.flap_until:
            self.flap_until = 0.0
            self.flap_reason = ""
            self._publish_all()

    async def _evaluate_mismatch(self) -> None:
        action_raw = self._state("sensor.se_nf_evopt_action_raw")
        block = self._state("binary_sensor.se_nf_evopt_charge_block_request") == "on"
        active_control = (
            self._state("binary_sensor.se_nf_evopt_active_control") == "on"
        )
        desired = _safe_float(self._state("sensor.se_nf_desired_target"))
        actual = _safe_float(self._state(self.watched_entity))

        reasons: list[str] = []

        # Die rohe EVCC-Aktion ist während Start, Warm-up oder Fallback nur
        # informativ. Verbindlich ist holdcharge erst, wenn EVOpt aktiv steuert
        # oder der gelatchte Charge-Block bereits gesetzt ist.
        restrictive = block or (
            active_control and action_raw == "holdcharge"
        )
        if restrictive and desired is not None and desired > 100:
            reasons.append("EVOpt holdcharge/Block aktiv, Desired Target ist offen")
        if restrictive and actual is not None and actual > 100:
            reasons.append("EVOpt holdcharge/Block aktiv, SolarEdge Charge Limit ist offen")
        if desired is not None and desired <= 100 and actual is not None and actual >= 1000:
            reasons.append("Desired Target ist 0 W, SolarEdge Charge Limit bleibt >=1000 W")

        signature = " | ".join(sorted(set(reasons)))
        now = time.time()
        if not signature:
            self.mismatch_since = 0.0
            self.mismatch_signature = ""
            self.mismatch_reasons = []
            if self.mismatch_active:
                self.mismatch_active = False
                await self._write_record(
                    {"event": "evopt_mismatch_cleared", "snapshot": self._snapshot()}
                )
                await self._dismiss_notification("se_write_watchdog_evopt_mismatch")
            self._publish_all()
            if self._mismatch_cancel is not None:
                self._mismatch_cancel()
                self._mismatch_cancel = None
            return

        if signature != self.mismatch_signature:
            self.mismatch_signature = signature
            self.mismatch_reasons = reasons
            self.mismatch_since = now
            if self._mismatch_cancel is not None:
                self._mismatch_cancel()
            self._mismatch_cancel = async_call_later(
                self.hass, self.mismatch_grace + 1, self._mismatch_recheck_callback
            )
            self._publish_all()
            return

        if not self.mismatch_active and now - self.mismatch_since >= self.mismatch_grace:
            self.mismatch_active = True
            self.counters["evopt_mismatches_today"] += 1
            record = {
                "event": "evopt_mismatch",
                "reasons": reasons,
                "duration_seconds": round(now - self.mismatch_since, 1),
                "snapshot": self._snapshot(),
            }
            await self._write_record(record)
            self._publish_all()
            self._schedule_save()
            await self._notify_once(
                "evopt_mismatch",
                "EVOpt-/SolarEdge-Steuerung widersprüchlich",
                "\n".join(reasons)
                + f"\n\nDetails: /config/{DOMAIN}/events-{self.counter_date}.jsonl",
            )

    @callback
    def _mismatch_recheck_callback(self, _now: Any) -> None:
        self._mismatch_cancel = None
        self.hass.async_create_task(self._evaluate_mismatch())

    def _state(self, entity_id: str) -> str:
        state = self.hass.states.get(entity_id)
        return state.state if state else "unknown"

    def _snapshot(self) -> dict[str, Any]:
        entities = list(RELEVANT_ENTITIES)
        if self.watched_entity not in entities:
            entities.append(self.watched_entity)
        result: dict[str, Any] = {}
        for entity_id in entities:
            state = self.hass.states.get(entity_id)
            if state is None:
                result[entity_id] = {"state": "missing"}
                continue
            attrs: dict[str, Any] = {}
            for key, value in state.attributes.items():
                if key in {"friendly_name", "icon", "unit_of_measurement"}:
                    continue
                if isinstance(value, (str, int, float, bool)) and len(attrs) < 12:
                    attrs[key] = value
            result[entity_id] = {
                "state": state.state,
                "last_changed": state.last_changed.isoformat(),
                "attributes": attrs,
            }
        return result

    async def _write_record(self, record: dict[str, Any]) -> None:
        full = {
            "timestamp": datetime.now().astimezone().isoformat(),
            "epoch": time.time(),
            **_jsonable(record),
        }
        self.recent_records.append(full)
        await self.hass.async_add_executor_job(self._write_record_sync, full)

    def _write_record_sync(self, record: dict[str, Any]) -> None:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        date = datetime.now().date().isoformat()
        path = self.log_dir / f"events-{date}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        latest = self.log_dir / "latest.json"
        latest.write_text(
            json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    async def async_scan_writers(self) -> None:
        scan = await self.hass.async_add_executor_job(self._scan_writers_sync)
        self.last_scan = scan
        await self._write_record({"event": "static_writer_scan", **scan})
        self._publish_all()

    def _scan_writers_sync(self) -> dict[str, Any]:
        root = Path(self.hass.config.path())
        target = self.watched_entity
        candidates: list[dict[str, Any]] = []
        extensions = {".yaml", ".yml", ".py"}
        excluded = {".storage", ".git", "deps", "tts", "www", DOMAIN}
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in extensions:
                continue
            if any(part in excluded for part in path.parts):
                continue
            lowered = str(path).lower()
            if ".backup" in lowered or "/backup" in lowered or "_backup" in lowered:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            has_number_set = bool(re.search(r"(?:service|action)\s*:\s*number\.set_value", text))
            has_exact = target in text
            has_mapping = "se_nf_charge_limit_entity" in text
            if not has_number_set or not (has_exact or has_mapping):
                continue
            lines = text.splitlines()
            hit_lines: set[int] = set()
            for idx, line in enumerate(lines, start=1):
                if target in line or "se_nf_charge_limit_entity" in line:
                    hit_lines.add(idx)
                if re.search(r"(?:service|action)\s*:\s*number\.set_value", line):
                    hit_lines.add(idx)
            snippets = []
            for line_no in sorted(hit_lines)[:12]:
                start = max(1, line_no - 3)
                end = min(len(lines), line_no + 4)
                snippets.append(
                    {
                        "line": line_no,
                        "snippet": "\n".join(
                            f"{n}: {lines[n-1]}" for n in range(start, end + 1)
                        ),
                    }
                )
            classification = "direct_exact" if has_exact and has_number_set else "mapped_dynamic"
            candidates.append(
                {
                    "file": str(path.relative_to(root)),
                    "classification": classification,
                    "has_number_set_value": has_number_set,
                    "has_exact_target": has_exact,
                    "has_mapping_helper": has_mapping,
                    "hits": snippets,
                }
            )

        candidates.sort(key=lambda item: (item["classification"], item["file"]))
        result = {
            "watched_entity": target,
            "count": len(candidates),
            "candidates": candidates,
        }
        output = self.log_dir / "writer_scan.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    async def _cleanup_old_logs(self) -> None:
        cutoff = time.time() - self.retention_days * 86400
        await self.hass.async_add_executor_job(self._cleanup_old_logs_sync, cutoff)

    def _cleanup_old_logs_sync(self, cutoff: float) -> None:
        if not self.log_dir.exists():
            return
        for path in self.log_dir.glob("events-*.jsonl"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink()
            except OSError:
                pass

    def _status(self) -> tuple[str, str]:
        if self.mismatch_active:
            return "mismatch", "EVOpt-/Ziel-/Ist-Widerspruch"
        if time.time() < self.flap_until:
            return "flapping", self.flap_reason
        if self.last_unexpected:
            return "warning", "Unerwarteter Schreiber wurde erkannt"
        return "ok", "Keine aktuelle Auffälligkeit"

    def _publish_all(self) -> None:
        status, reason = self._status()
        common = {
            "friendly_name": "SE Write Watchdog Status",
            "icon": "mdi:shield-search",
            "reason": reason,
            "watched_entity": self.watched_entity,
            "allowed_writers": sorted(self.allowed_writers),
            "log_file": f"/config/{DOMAIN}/events-{self.counter_date}.jsonl",
            "writer_scan_file": f"/config/{DOMAIN}/writer_scan.json",
        }
        self.hass.states.async_set("sensor.se_write_watchdog_status", status, common)

        for key in COUNTER_KEYS:
            self.hass.states.async_set(
                f"sensor.se_write_watchdog_{key}",
                self.counters[key],
                {
                    "friendly_name": f"SE Write Watchdog {key.replace('_', ' ').title()}",
                    "icon": "mdi:counter",
                },
            )

        last_call = self.last_write_call or {}
        call_source = last_call.get("source", {}) if last_call else {}
        self.hass.states.async_set(
            "sensor.se_write_watchdog_last_writer",
            call_source.get("entity_id") or call_source.get("name") or "none",
            {
                "friendly_name": "SE Write Watchdog Last Writer",
                "icon": "mdi:account-search",
                "requested_value": last_call.get("requested_value"),
                "allowed_writer": last_call.get("allowed_writer"),
                "duplicate": last_call.get("duplicate"),
                "context_id": last_call.get("context_id"),
                "parent_id": last_call.get("parent_id"),
                "source_type": call_source.get("type"),
                "intent": _jsonable(last_call.get("intent")),
            },
        )

        last_change = self.last_state_change or {}
        self.hass.states.async_set(
            "sensor.se_write_watchdog_last_change",
            last_change.get("new_value", "none"),
            {
                "friendly_name": "SE Write Watchdog Last Change",
                "icon": "mdi:swap-horizontal",
                "old_value": last_change.get("old_value"),
                "roundtrip_detected": last_change.get("roundtrip_detected"),
                "attributed": last_change.get("attributed"),
                "source": _jsonable(last_change.get("source")),
                "context_id": last_change.get("context_id"),
            },
        )

        self.hass.states.async_set(
            "binary_sensor.se_write_watchdog_flapping",
            "on" if time.time() < self.flap_until else "off",
            {
                "friendly_name": "SE Write Watchdog Flapping",
                "icon": "mdi:pulse",
                "reason": self.flap_reason,
                "active_until_epoch": self.flap_until or None,
            },
        )
        self.hass.states.async_set(
            "binary_sensor.se_write_watchdog_evopt_mismatch",
            "on" if self.mismatch_active else "off",
            {
                "friendly_name": "SE Write Watchdog EVOpt Mismatch",
                "icon": "mdi:alert-decagram",
                "reasons": self.mismatch_reasons,
                "candidate_since_epoch": self.mismatch_since or None,
                "grace_seconds": self.mismatch_grace,
            },
        )
        unexpected_active = bool(self.last_unexpected)
        self.hass.states.async_set(
            "binary_sensor.se_write_watchdog_unexpected_writer",
            "on" if unexpected_active else "off",
            {
                "friendly_name": "SE Write Watchdog Unexpected Writer",
                "icon": "mdi:account-alert",
                "last_unexpected": _jsonable(self.last_unexpected),
            },
        )
        self.hass.states.async_set(
            "sensor.se_write_watchdog_possible_writers",
            self.last_scan.get("count", 0),
            {
                "friendly_name": "SE Write Watchdog Possible Writers",
                "icon": "mdi:file-search",
                "candidates": [
                    {
                        "file": item.get("file"),
                        "classification": item.get("classification"),
                    }
                    for item in self.last_scan.get("candidates", [])[:30]
                ],
            },
        )

    async def _logbook(self, message: str) -> None:
        try:
            await self.hass.services.async_call(
                "logbook",
                "log",
                {"name": "SE Write Watchdog", "message": message},
                blocking=False,
            )
        except Exception:  # pragma: no cover - optional integration
            _LOGGER.debug("Could not write logbook entry")

    async def _notify_once(self, key: str, title: str, message: str) -> None:
        if not self.notifications:
            return
        notification_id = f"se_write_watchdog_{key}"
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": title,
                "message": message,
                "notification_id": notification_id,
            },
            blocking=False,
        )

    async def _dismiss_notification(self, notification_id: str) -> None:
        try:
            await self.hass.services.async_call(
                "persistent_notification",
                "dismiss",
                {"notification_id": notification_id},
                blocking=False,
            )
        except Exception:
            pass

    @callback
    def _schedule_save(self) -> None:
        if self._save_cancel is not None:
            return
        self._save_cancel = async_call_later(self.hass, 5, self._save_callback)

    @callback
    def _save_callback(self, _now: Any) -> None:
        self._save_cancel = None
        self.hass.async_create_task(self._async_save())

    async def _async_save(self) -> None:
        await self.store.async_save({"date": self.counter_date, "counters": self.counters})

    @callback
    def _on_midnight(self, _now: Any) -> None:
        self.hass.async_create_task(self._async_midnight_reset())

    async def _async_midnight_reset(self) -> None:
        self.counter_date = datetime.now().date().isoformat()
        self.counters = {key: 0 for key in COUNTER_KEYS}
        self.state_history.clear()
        self.last_unexpected = None
        self._publish_all()
        await self._async_save()
        await self._cleanup_old_logs()
        await self._write_record({"event": "daily_reset"})

    async def _service_reset(self, _call: Any) -> None:
        await self._async_midnight_reset()

    async def _service_rescan(self, _call: Any) -> None:
        await self.async_scan_writers()

    async def _service_mark_test(self, call: Any) -> None:
        await self._write_record(
            {"event": "manual_test_marker", "note": call.data.get("note"), "snapshot": self._snapshot()}
        )

    async def _service_dump_report(self, _call: Any) -> None:
        report = {
            "generated": datetime.now().astimezone().isoformat(),
            "status": self._status(),
            "watched_entity": self.watched_entity,
            "allowed_writers": sorted(self.allowed_writers),
            "counters": self.counters,
            "last_write_call": self.last_write_call,
            "last_state_change": self.last_state_change,
            "last_unexpected": self.last_unexpected,
            "flapping": {
                "active": time.time() < self.flap_until,
                "reason": self.flap_reason,
                "until": self.flap_until,
            },
            "mismatch": {
                "active": self.mismatch_active,
                "reasons": self.mismatch_reasons,
                "since": self.mismatch_since,
            },
            "writer_scan": self.last_scan,
            "snapshot": self._snapshot(),
        }
        path = self.log_dir / "report.json"
        await self.hass.async_add_executor_job(
            path.write_text,
            json.dumps(_jsonable(report), ensure_ascii=False, indent=2, sort_keys=True),
            "utf-8",
        )
        await self._write_record({"event": "report_dumped", "path": str(path)})

    async def _on_stop(self, _event: Event) -> None:
        await self._async_save()


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the watchdog from configuration.yaml."""
    watchdog = SolarEdgeWriteWatchdog(hass, config.get(DOMAIN, {}))
    hass.data[DOMAIN] = watchdog
    await watchdog.async_setup()
    return True
