from __future__ import annotations

from testbench.reference.controller_model import (
    ControlSource,
    ControllerInput,
    ControllerSequence,
    EvoptAction,
    Mode,
)


def test_evopt_startup_does_not_create_zero_open_zero_roundtrip() -> None:
    seq = ControllerSequence(
        ControllerInput(
            mode=Mode.EVOPT,
            now_minute=12 * 60 + 30,
            current_charge_limit_w=0,
            evopt_healthy=False,
            evopt_unavailable_age_s=0,
        )
    )
    for age in (0, 30, 60, 300, 1199):
        decision = seq.step(30, evopt_unavailable_age_s=age)
        assert decision.target_w == 0
    seq.step(1, evopt_healthy=True, evopt_action=EvoptAction.HOLDCHARGE)
    assert seq.current_w == 0
    assert seq.writes == []


def test_long_evopt_failure_enters_legacy_only_after_20_minutes_and_90s_stability() -> None:
    seq = ControllerSequence(
        ControllerInput(
            mode=Mode.EVOPT,
            now_minute=12 * 60 + 30,
            current_charge_limit_w=0,
            evopt_healthy=False,
            evopt_unavailable_age_s=1199,
        )
    )
    first = seq.step(1, evopt_unavailable_age_s=1200)
    assert first.source is ControlSource.LEGACY_FALLBACK
    assert not first.write.should_write
    seq.step(89, evopt_unavailable_age_s=1289)
    assert seq.current_w == 0
    final = seq.step(1, evopt_unavailable_age_s=1290)
    assert final.write.should_write
    assert seq.current_w == 5000


def test_holdcharge_latch_survives_raw_normal_for_180_seconds() -> None:
    seq = ControllerSequence(
        ControllerInput(
            mode=Mode.EVOPT,
            current_charge_limit_w=5000,
            evopt_healthy=True,
            evopt_action=EvoptAction.NORMAL,
        )
    )
    close = seq.step(0, evopt_action=EvoptAction.HOLDCHARGE)
    assert close.write.should_write
    assert seq.current_w == 0

    still_latched = seq.step(179, evopt_action=EvoptAction.NORMAL)
    assert still_latched.target_w == 0
    assert seq.current_w == 0

    released_but_not_stable = seq.step(1, evopt_action=EvoptAction.NORMAL)
    assert released_but_not_stable.target_w == 5000
    assert not released_but_not_stable.write.should_write

    seq.step(89, evopt_action=EvoptAction.NORMAL)
    assert seq.current_w == 0
    opened = seq.step(1, evopt_action=EvoptAction.NORMAL)
    assert opened.write.should_write
    assert seq.current_w == 5000


def test_restrictive_change_bypasses_cooldown_but_opening_does_not() -> None:
    seq = ControllerSequence(
        ControllerInput(
            mode=Mode.EVOPT,
            current_charge_limit_w=5000,
            evopt_healthy=True,
            evopt_action=EvoptAction.NORMAL,
            seconds_since_last_write=0,
        )
    )
    close = seq.step(0, evopt_action=EvoptAction.HOLDCHARGE)
    assert close.write.should_write
    assert seq.current_w == 0

    seq.step(180, evopt_action=EvoptAction.NORMAL)
    assert seq.current_w == 0
    seq.step(90, evopt_action=EvoptAction.NORMAL)
    assert seq.current_w == 5000


def test_day_to_night_grid_transition_is_single_restrictive_write() -> None:
    seq = ControllerSequence(
        ControllerInput(
            mode=Mode.GRID_FRIENDLY,
            now_minute=13 * 60,
            current_charge_limit_w=5000,
            planned_start_minute=11 * 60 + 45,
            latest_finish_minute=14 * 60 + 15,
        )
    )
    seq.step(0)
    after = seq.step(2 * 60 * 60, now_minute=15 * 60)
    assert after.write.should_write
    assert seq.current_w == 0
    assert len(seq.writes) == 1
