"""Independent controller reference model used only by the testbench.

The model intentionally does not import Home Assistant or parse the production
Jinja templates.  It expresses safety and transition invariants in ordinary
Python so that tests do not merely repeat the implementation under test.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
import math


class Mode(StrEnum):
    SELF_CONSUMPTION = "Eigenverbrauch maximieren"
    GRID_FRIENDLY = "Netzdienlich laden"
    BATTERY_CARE = "Akku schonen"
    EVOPT = "EVOpt optimiert"


class EvoptAction(StrEnum):
    NORMAL = "normal"
    HOLDCHARGE = "holdcharge"
    CHARGE = "charge"
    DISCHARGE = "discharge"
    HOLD = "hold"
    UNAVAILABLE = "unavailable"


class ControlSource(StrEnum):
    SAFETY = "safety"
    SELF_CONSUMPTION = "self_consumption"
    GRID_FRIENDLY = "grid_friendly"
    BATTERY_CARE = "battery_care"
    EVOPT = "evopt"
    EVOPT_HOLD = "evopt_hold_last_confirmed"
    LEGACY_FALLBACK = "legacy_grid_friendly_fallback"


@dataclass(frozen=True)
class ControllerInput:
    mode: Mode = Mode.GRID_FRIENDLY
    now_minute: int = 12 * 60
    master: bool = True
    site_confirmed: bool = True
    config_ok: bool = True
    sanity_ok: bool = True
    risk: bool = False

    soc_pct: float = 50.0
    battery_capacity_kwh: float = 24.25
    backup_reserve_pct: float = 10.0
    low_soc_floor_pct: float = 25.0
    safety_energy_kwh: float = 1.0
    target_soc_pct: float = 95.0

    pv_power_w: float = 0.0
    home_power_w: float = 500.0
    pv_today_remaining_kwh: float = 0.0
    pv_tomorrow_kwh: float = 0.0

    planned_start_minute: int = 11 * 60 + 45
    latest_finish_minute: int = 14 * 60 + 15
    planning_charge_power_w: float = 5000.0
    required_energy_kwh: float | None = None
    lifetime_target_reached: bool = False

    evopt_healthy: bool = False
    evopt_action: EvoptAction = EvoptAction.UNAVAILABLE
    evopt_unavailable_age_s: int = 0
    evopt_block_latched: bool = False

    current_charge_limit_w: float = 0.0
    candidate_stable_s: int = 9999
    seconds_since_last_write: int = 9999

    open_limit_w: float = 5000.0
    closed_limit_w: float = 0.0
    minimum_write_delta_w: float = 100.0
    permissive_stable_s: int = 90
    cooldown_s: int = 180
    evopt_fallback_grace_s: int = 1200


@dataclass(frozen=True)
class WriteDecision:
    should_write: bool
    requested_w: float
    reason: str


@dataclass(frozen=True)
class ControlDecision:
    target_w: float
    source: ControlSource
    control_reason: str
    write_allowed: bool
    write: WriteDecision


def _finite(value: float | int | None) -> bool:
    return value is not None and math.isfinite(float(value))


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _required_energy(i: ControllerInput) -> float:
    if i.required_energy_kwh is not None:
        return max(float(i.required_energy_kwh), 0.0)
    gap_pct = max(i.target_soc_pct - i.soc_pct, 0.0)
    return max(i.battery_capacity_kwh * gap_pct / 100.0, 0.0)


def _safety_gate(i: ControllerInput) -> tuple[bool, str]:
    if not i.master:
        return False, "master_off"
    if not i.site_confirmed:
        return False, "site_not_confirmed"
    if not i.config_ok:
        return False, "config_not_ok"
    if not i.sanity_ok:
        return False, "sanity_not_ok"
    if i.risk:
        return False, "risk_flag"

    numeric = {
        "soc": i.soc_pct,
        "capacity": i.battery_capacity_kwh,
        "pv_power": i.pv_power_w,
        "home_power": i.home_power_w,
        "forecast_today": i.pv_today_remaining_kwh,
        "forecast_tomorrow": i.pv_tomorrow_kwh,
        "open_limit": i.open_limit_w,
        "closed_limit": i.closed_limit_w,
        "current_limit": i.current_charge_limit_w,
    }
    for name, value in numeric.items():
        if not _finite(value):
            return False, f"invalid_{name}"
    if not 0 <= i.soc_pct <= 100:
        return False, "soc_out_of_range"
    if i.battery_capacity_kwh <= 0:
        return False, "capacity_invalid"
    if i.open_limit_w < i.closed_limit_w or i.closed_limit_w < 0:
        return False, "limit_range_invalid"
    if i.pv_power_w < 0 or i.home_power_w < 0:
        return False, "negative_live_power"
    if i.pv_today_remaining_kwh < 0 or i.pv_tomorrow_kwh < 0:
        return False, "negative_forecast"
    return True, "ok"


def _grid_friendly_target(i: ControllerInput) -> tuple[float, str]:
    need = _required_energy(i)
    if i.soc_pct <= i.low_soc_floor_pct and need > 0.05:
        return i.open_limit_w, "low_soc_floor"
    if i.planned_start_minute <= i.now_minute <= i.latest_finish_minute:
        return i.open_limit_w, "inside_planned_window"
    if i.now_minute < i.planned_start_minute:
        return i.closed_limit_w, "before_planned_window"
    return i.closed_limit_w, "after_planned_window"


def _battery_care_target(i: ControllerInput) -> tuple[float, str]:
    need = _required_energy(i)
    reserve_guard = max(
        i.low_soc_floor_pct,
        i.backup_reserve_pct
        + (i.safety_energy_kwh / i.battery_capacity_kwh * 100.0),
    )
    if i.lifetime_target_reached or need <= 0.05 or i.soc_pct >= i.target_soc_pct:
        return i.closed_limit_w, "care_target_reached"
    if i.soc_pct <= reserve_guard:
        return i.open_limit_w, "care_reserve_guard"
    if i.planned_start_minute <= i.now_minute <= i.latest_finish_minute:
        return i.open_limit_w, "care_window_open"
    return i.closed_limit_w, "care_waiting"


def _mode_target(i: ControllerInput) -> tuple[float, ControlSource, str]:
    if i.mode == Mode.SELF_CONSUMPTION:
        return i.open_limit_w, ControlSource.SELF_CONSUMPTION, "self_consumption_open"
    if i.mode == Mode.GRID_FRIENDLY:
        target, reason = _grid_friendly_target(i)
        return target, ControlSource.GRID_FRIENDLY, reason
    if i.mode == Mode.BATTERY_CARE:
        target, reason = _battery_care_target(i)
        return target, ControlSource.BATTERY_CARE, reason

    if i.evopt_healthy:
        if i.evopt_block_latched or i.evopt_action in {
            EvoptAction.HOLDCHARGE,
            EvoptAction.HOLD,
        }:
            return i.closed_limit_w, ControlSource.EVOPT, "evopt_restrictive"
        if i.evopt_action in {
            EvoptAction.NORMAL,
            EvoptAction.CHARGE,
            EvoptAction.DISCHARGE,
        }:
            return i.open_limit_w, ControlSource.EVOPT, "evopt_permissive"

    if i.evopt_unavailable_age_s < i.evopt_fallback_grace_s:
        held = (
            i.open_limit_w
            if i.current_charge_limit_w
            >= (i.open_limit_w + i.closed_limit_w) / 2.0
            else i.closed_limit_w
        )
        return held, ControlSource.EVOPT_HOLD, "evopt_startup_hold"

    target, reason = _grid_friendly_target(i)
    return target, ControlSource.LEGACY_FALLBACK, f"fallback_{reason}"


def _writer(i: ControllerInput, target_w: float, write_allowed: bool) -> WriteDecision:
    requested = _clamp(target_w, i.closed_limit_w, i.open_limit_w)
    if not write_allowed:
        return WriteDecision(False, requested, "write_gate_closed")

    delta = abs(requested - i.current_charge_limit_w)
    if delta < i.minimum_write_delta_w:
        return WriteDecision(False, requested, "below_minimum_delta")

    # Restrictive transitions must never wait for stability or cooldown.
    if requested < i.current_charge_limit_w:
        return WriteDecision(True, requested, "restrictive_immediate")

    if i.candidate_stable_s < i.permissive_stable_s:
        return WriteDecision(False, requested, "permissive_not_stable")
    if i.seconds_since_last_write < i.cooldown_s:
        return WriteDecision(False, requested, "cooldown_active")
    return WriteDecision(True, requested, "permissive_ready")


def decide(i: ControllerInput) -> ControlDecision:
    """Return one deterministic controller decision for a complete input snapshot."""

    gate, gate_reason = _safety_gate(i)
    if not gate:
        target = _clamp(i.current_charge_limit_w, i.closed_limit_w, i.open_limit_w)
        write = _writer(i, target, False)
        return ControlDecision(
            target_w=target,
            source=ControlSource.SAFETY,
            control_reason=gate_reason,
            write_allowed=False,
            write=write,
        )

    target, source, reason = _mode_target(i)
    target = _clamp(float(target), i.closed_limit_w, i.open_limit_w)
    return ControlDecision(
        target_w=target,
        source=source,
        control_reason=reason,
        write_allowed=True,
        write=_writer(i, target, True),
    )


class ControllerSequence:
    """Small fake-time state machine for writer and EVOpt transition tests."""

    def __init__(self, initial: ControllerInput, *, now_s: int = 0) -> None:
        self.input = initial
        self.now_s = now_s
        self.current_w = initial.current_charge_limit_w
        self.last_write_s = now_s - initial.seconds_since_last_write
        self.candidate_target_w: float | None = None
        self.candidate_since_s = now_s
        self.evopt_block_until_s = now_s if not initial.evopt_block_latched else now_s + 180
        self.writes: list[dict[str, float | int | str]] = []

    def step(self, seconds: int = 0, **changes: object) -> ControlDecision:
        if seconds < 0:
            raise ValueError("fake time cannot move backwards")
        self.now_s += seconds
        next_input = replace(self.input, **changes)

        if next_input.mode == Mode.EVOPT and next_input.evopt_healthy:
            if next_input.evopt_action == EvoptAction.HOLDCHARGE:
                self.evopt_block_until_s = self.now_s + 180
            latched = self.now_s < self.evopt_block_until_s
            next_input = replace(next_input, evopt_block_latched=latched)

        probe = replace(
            next_input,
            current_charge_limit_w=self.current_w,
            candidate_stable_s=999999,
            seconds_since_last_write=max(self.now_s - self.last_write_s, 0),
        )
        raw_target = decide(probe).target_w
        if self.candidate_target_w != raw_target:
            self.candidate_target_w = raw_target
            self.candidate_since_s = self.now_s
        stable_s = self.now_s - self.candidate_since_s

        effective = replace(
            next_input,
            current_charge_limit_w=self.current_w,
            candidate_stable_s=stable_s,
            seconds_since_last_write=max(self.now_s - self.last_write_s, 0),
        )
        decision = decide(effective)
        if decision.write.should_write:
            old = self.current_w
            self.current_w = decision.write.requested_w
            self.last_write_s = self.now_s
            self.writes.append(
                {
                    "at_s": self.now_s,
                    "old_w": old,
                    "new_w": self.current_w,
                    "source": decision.source.value,
                    "reason": decision.write.reason,
                    "control_reason": decision.control_reason,
                }
            )
        self.input = replace(effective, current_charge_limit_w=self.current_w)
        return decision
