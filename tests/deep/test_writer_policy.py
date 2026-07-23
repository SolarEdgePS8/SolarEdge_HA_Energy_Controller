from __future__ import annotations

from dataclasses import replace

from testbench.reference.writer_policy import WriterSnapshot, decide


def test_exact_live_failure_is_blocked_even_during_emergency_open() -> None:
    """2026-07-23: raw/stable holdcharge + block on must never write 5000 W."""

    result = decide(
        WriterSnapshot(
            target_w=5000,
            current_w=0,
            raw_action="holdcharge",
            stable_action="holdcharge",
            charge_block_on=True,
            emergency_open=True,
            target_stable_s=90,
            evopt_action_stable_s=9999,
        )
    )

    assert not result.should_write
    assert result.restrictive_evopt
    assert result.reason == "evopt_restrictive_hard_block"


def test_each_restrictive_evopt_signal_blocks_a_permissive_write() -> None:
    base = WriterSnapshot(target_w=5000, current_w=0, emergency_open=True)

    for snapshot in (
        replace(base, raw_action="holdcharge"),
        replace(base, stable_action="holdcharge"),
        replace(base, charge_block_on=True),
    ):
        result = decide(snapshot)
        assert not result.should_write
        assert result.reason == "evopt_restrictive_hard_block"


def test_restrictive_zero_write_remains_immediate() -> None:
    result = decide(
        WriterSnapshot(
            target_w=0,
            current_w=5000,
            raw_action="holdcharge",
            stable_action="holdcharge",
            charge_block_on=True,
            cooldown_ok=False,
            lock_active=True,
        )
    )

    assert result.should_write
    assert result.reason == "restrictive_close_immediate"


def test_evopt_normal_must_be_stable_for_twenty_minutes() -> None:
    too_early = decide(
        WriterSnapshot(
            target_w=5000,
            current_w=0,
            raw_action="normal",
            stable_action="normal",
            evopt_action_stable_s=1199,
            target_stable_s=9999,
        )
    )
    ready = decide(
        WriterSnapshot(
            target_w=5000,
            current_w=0,
            raw_action="normal",
            stable_action="normal",
            evopt_action_stable_s=1200,
            target_stable_s=90,
        )
    )

    assert not too_early.should_write
    assert too_early.reason == "evopt_action_not_stable_20min"
    assert ready.should_write
    assert ready.reason == "permissive_open_ready"


def test_non_evopt_emergency_open_is_not_accidentally_blocked() -> None:
    result = decide(
        WriterSnapshot(
            mode="Netzdienlich laden",
            target_w=5000,
            current_w=0,
            raw_action="holdcharge",
            stable_action="holdcharge",
            charge_block_on=True,
            emergency_open=True,
        )
    )

    assert result.should_write
    assert not result.restrictive_evopt
    assert result.reason == "emergency_open_without_evopt_block"
