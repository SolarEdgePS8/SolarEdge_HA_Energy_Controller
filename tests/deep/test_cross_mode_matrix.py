from __future__ import annotations

import itertools
import math

from testbench.reference.controller_model import (
    ControlSource,
    ControllerInput,
    ControllerSequence,
    EvoptAction,
    Mode,
    decide,
)


def test_deterministic_day_night_pv_load_soc_forecast_matrix() -> None:
    """Exercise 9,600 deterministic snapshots across all four modes."""

    total = 0
    for mode, minute, soc, pv, load, forecast in itertools.product(
        list(Mode),
        [2 * 60, 10 * 60, 12 * 60 + 30, 23 * 60],
        [0.0, 10.0, 25.0, 50.0, 95.0, 100.0],
        [0.0, 500.0, 2500.0, 5000.0, 10000.0],
        [0.0, 500.0, 2500.0, 5000.0],
        [0.0, 5.0, 20.0, 50.0],
    ):
        actions = (
            [EvoptAction.NORMAL, EvoptAction.HOLDCHARGE]
            if mode is Mode.EVOPT
            else [EvoptAction.UNAVAILABLE]
        )
        for action in actions:
            decision = decide(
                ControllerInput(
                    mode=mode,
                    now_minute=minute,
                    soc_pct=soc,
                    pv_power_w=pv,
                    home_power_w=load,
                    pv_today_remaining_kwh=forecast,
                    pv_tomorrow_kwh=forecast,
                    evopt_healthy=mode is Mode.EVOPT,
                    evopt_action=action,
                    current_charge_limit_w=0.0,
                    candidate_stable_s=999,
                    seconds_since_last_write=999,
                )
            )
            total += 1
            assert math.isfinite(decision.target_w)
            assert 0.0 <= decision.target_w <= 5000.0
            assert 0.0 <= decision.write.requested_w <= 5000.0
            assert decision.source is not ControlSource.SAFETY
            if action is EvoptAction.HOLDCHARGE:
                assert decision.target_w == 0.0
                assert decision.source is ControlSource.EVOPT

    assert total == 9600


def test_all_four_modes_can_be_switched_in_one_fake_time_sequence() -> None:
    """Switch every public mode without duplicate or unsafe writes."""

    seq = ControllerSequence(
        ControllerInput(
            mode=Mode.SELF_CONSUMPTION,
            now_minute=12 * 60 + 30,
            current_charge_limit_w=0.0,
            candidate_stable_s=0,
            seconds_since_last_write=999,
        )
    )

    # Self consumption: permissive opening only after 90 seconds stability.
    assert not seq.step(0).write.should_write
    assert seq.step(90).write.should_write
    assert seq.current_w == 5000.0

    # Grid friendly before its planned window: restrictive close immediately.
    grid = seq.step(
        1,
        mode=Mode.GRID_FRIENDLY,
        now_minute=10 * 60,
        planned_start_minute=11 * 60 + 45,
        latest_finish_minute=14 * 60 + 15,
    )
    assert grid.source is ControlSource.GRID_FRIENDLY
    assert grid.write.should_write
    assert seq.current_w == 0.0

    # Battery care inside the window: wait for stability and cooldown, then open.
    care = seq.step(
        180,
        mode=Mode.BATTERY_CARE,
        now_minute=12 * 60 + 30,
        soc_pct=50.0,
        target_soc_pct=95.0,
    )
    assert care.source is ControlSource.BATTERY_CARE
    assert not care.write.should_write
    care_open = seq.step(90)
    assert care_open.write.should_write
    assert seq.current_w == 5000.0

    # EVOpt holdcharge: restrictive close is immediate despite fresh write.
    evopt = seq.step(
        1,
        mode=Mode.EVOPT,
        evopt_healthy=True,
        evopt_action=EvoptAction.HOLDCHARGE,
    )
    assert evopt.source is ControlSource.EVOPT
    assert evopt.write.should_write
    assert seq.current_w == 0.0

    assert [entry["new_w"] for entry in seq.writes] == [5000.0, 0.0, 5000.0, 0.0]
