from __future__ import annotations

import math

import pytest
from hypothesis import given, settings, strategies as st

from testbench.reference.controller_model import (
    ControllerInput,
    EvoptAction,
    Mode,
    decide,
)


finite = st.floats(min_value=-10000, max_value=100000, allow_nan=False, allow_infinity=False)
valid_power = st.floats(min_value=0, max_value=30000, allow_nan=False, allow_infinity=False)
valid_energy = st.floats(min_value=0, max_value=150, allow_nan=False, allow_infinity=False)
valid_soc = st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False)


@settings(max_examples=500, deadline=None)
@given(
    mode=st.sampled_from(list(Mode)),
    soc=valid_soc,
    capacity=st.floats(min_value=0.1, max_value=100, allow_nan=False, allow_infinity=False),
    pv=valid_power,
    load=valid_power,
    forecast=valid_energy,
    current=st.sampled_from([0.0, 5000.0]),
    action=st.sampled_from(list(EvoptAction)),
    healthy=st.booleans(),
    minute=st.integers(min_value=0, max_value=1439),
)
def test_global_output_invariants(
    mode: Mode,
    soc: float,
    capacity: float,
    pv: float,
    load: float,
    forecast: float,
    current: float,
    action: EvoptAction,
    healthy: bool,
    minute: int,
) -> None:
    decision = decide(
        ControllerInput(
            mode=mode,
            soc_pct=soc,
            battery_capacity_kwh=capacity,
            pv_power_w=pv,
            home_power_w=load,
            pv_today_remaining_kwh=forecast,
            pv_tomorrow_kwh=forecast,
            current_charge_limit_w=current,
            evopt_action=action,
            evopt_healthy=healthy,
            now_minute=minute,
            candidate_stable_s=500,
            seconds_since_last_write=500,
        )
    )
    assert math.isfinite(decision.target_w)
    assert 0 <= decision.target_w <= 5000
    assert 0 <= decision.write.requested_w <= 5000
    if abs(decision.target_w - current) < 100:
        assert not decision.write.should_write


@settings(max_examples=200, deadline=None)
@given(
    mode=st.sampled_from(list(Mode)),
    soc=finite,
    capacity=finite,
    pv=finite,
    load=finite,
    today=finite,
    tomorrow=finite,
)
def test_invalid_or_extreme_inputs_never_raise_and_never_write_when_gate_rejects(
    mode: Mode,
    soc: float,
    capacity: float,
    pv: float,
    load: float,
    today: float,
    tomorrow: float,
) -> None:
    i = ControllerInput(
        mode=mode,
        soc_pct=soc,
        battery_capacity_kwh=capacity,
        pv_power_w=pv,
        home_power_w=load,
        pv_today_remaining_kwh=today,
        pv_tomorrow_kwh=tomorrow,
        current_charge_limit_w=0,
    )
    decision = decide(i)
    assert math.isfinite(decision.target_w)
    if not (
        0 <= soc <= 100
        and capacity > 0
        and pv >= 0
        and load >= 0
        and today >= 0
        and tomorrow >= 0
    ):
        assert not decision.write_allowed
        assert not decision.write.should_write


@pytest.mark.parametrize("field", ["master", "site_confirmed", "config_ok", "sanity_ok"])
def test_each_safety_gate_blocks_writes(field: str) -> None:
    values = {field: False, "current_charge_limit_w": 0, "mode": Mode.SELF_CONSUMPTION}
    decision = decide(ControllerInput(**values))
    assert not decision.write_allowed
    assert not decision.write.should_write


def test_risk_flag_blocks_writes() -> None:
    decision = decide(ControllerInput(mode=Mode.SELF_CONSUMPTION, risk=True))
    assert not decision.write_allowed
    assert not decision.write.should_write


@pytest.mark.parametrize("stable_s,expected", [(89, False), (90, True), (91, True)])
def test_permissive_stability_boundary(stable_s: int, expected: bool) -> None:
    decision = decide(
        ControllerInput(
            mode=Mode.SELF_CONSUMPTION,
            current_charge_limit_w=0,
            candidate_stable_s=stable_s,
            seconds_since_last_write=999,
        )
    )
    assert decision.write.should_write is expected


@pytest.mark.parametrize("cooldown_s,expected", [(179, False), (180, True), (181, True)])
def test_writer_cooldown_boundary(cooldown_s: int, expected: bool) -> None:
    decision = decide(
        ControllerInput(
            mode=Mode.SELF_CONSUMPTION,
            current_charge_limit_w=0,
            candidate_stable_s=999,
            seconds_since_last_write=cooldown_s,
        )
    )
    assert decision.write.should_write is expected


def test_restrictive_transition_is_immediate() -> None:
    decision = decide(
        ControllerInput(
            mode=Mode.EVOPT,
            evopt_healthy=True,
            evopt_action=EvoptAction.HOLDCHARGE,
            current_charge_limit_w=5000,
            candidate_stable_s=0,
            seconds_since_last_write=0,
        )
    )
    assert decision.write.should_write
    assert decision.write.requested_w == 0
    assert decision.write.reason == "restrictive_immediate"
