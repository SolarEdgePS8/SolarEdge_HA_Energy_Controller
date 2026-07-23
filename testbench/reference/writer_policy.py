"""Independent safety model for the single SolarEdge charge-limit writer.

This module is test-only.  It does not parse the production YAML and does not
import Home Assistant.  The tests use it as an independent statement of the
required safety behaviour.
"""

from __future__ import annotations

from dataclasses import dataclass


EVOPT_MODE = "EVOpt optimiert"
HOLDCHARGE = "holdcharge"


@dataclass(frozen=True)
class WriterSnapshot:
    mode: str = EVOPT_MODE
    target_w: float = 5000.0
    current_w: float = 0.0
    controller_write_enabled: bool = True
    entity_available: bool = True
    target_plausible: bool = True
    target_is_risk: bool = False
    session_stable_s: int = 9999
    target_stable_s: int = 9999
    evopt_action_stable_s: int = 9999
    raw_action: str = "normal"
    stable_action: str = "normal"
    charge_block_on: bool = False
    emergency_open: bool = False
    cooldown_ok: bool = True
    lock_active: bool = False
    minimum_delta_w: float = 100.0


@dataclass(frozen=True)
class WriterResult:
    should_write: bool
    reason: str
    restrictive_evopt: bool


def restrictive_evopt(snapshot: WriterSnapshot) -> bool:
    """Return True when EVOpt clearly requests that charging stays blocked."""

    return snapshot.mode == EVOPT_MODE and (
        snapshot.raw_action == HOLDCHARGE
        or snapshot.stable_action == HOLDCHARGE
        or snapshot.charge_block_on
    )


def decide(snapshot: WriterSnapshot) -> WriterResult:
    """Evaluate the required writer safety policy for one complete snapshot."""

    restrictive = restrictive_evopt(snapshot)

    if not snapshot.controller_write_enabled:
        return WriterResult(False, "controller_write_disabled", restrictive)
    if not snapshot.entity_available:
        return WriterResult(False, "target_entity_unavailable", restrictive)
    if not 0 <= snapshot.target_w <= 5000:
        return WriterResult(False, "invalid_target", restrictive)
    if not 0 <= snapshot.current_w <= 5000:
        return WriterResult(False, "invalid_current_value", restrictive)
    if abs(snapshot.target_w - snapshot.current_w) < snapshot.minimum_delta_w:
        return WriterResult(False, "below_minimum_delta", restrictive)

    # Closing is always the safest transition and must remain immediate.
    if snapshot.target_w <= 50 and snapshot.current_w > 50:
        return WriterResult(True, "restrictive_close_immediate", restrictive)

    # This is the invariant that the real 2026-07-23 log proved was missing.
    if snapshot.target_w >= 4750 and restrictive:
        return WriterResult(False, "evopt_restrictive_hard_block", restrictive)

    if snapshot.target_w >= 4750:
        if not snapshot.target_plausible:
            return WriterResult(False, "open_not_plausible", restrictive)
        if snapshot.target_is_risk and snapshot.session_stable_s < 90:
            return WriterResult(False, "risk_session_not_stable", restrictive)
        if snapshot.emergency_open:
            return WriterResult(True, "emergency_open_without_evopt_block", restrictive)
        if snapshot.target_stable_s < 90:
            return WriterResult(False, "target_not_stable_90s", restrictive)
        if snapshot.mode == EVOPT_MODE and snapshot.evopt_action_stable_s < 1200:
            return WriterResult(False, "evopt_action_not_stable_20min", restrictive)
        if snapshot.lock_active:
            return WriterResult(False, "write_lock_active", restrictive)
        if not snapshot.cooldown_ok:
            return WriterResult(False, "cooldown_active", restrictive)
        return WriterResult(True, "permissive_open_ready", restrictive)

    if snapshot.lock_active:
        return WriterResult(False, "write_lock_active", restrictive)
    if not snapshot.cooldown_ok:
        return WriterResult(False, "cooldown_active", restrictive)
    return WriterResult(True, "normal_write_ready", restrictive)
