from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).parents[1]
WRITER = ROOT / "package" / "se_controller_80_charge_writer.yaml"


def writer_text() -> str:
    return WRITER.read_text(encoding="utf-8")


def test_evopt_release_is_rechecked_after_twenty_minutes() -> None:
    text = writer_text()

    assert "entity_id: sensor.se_nf_evopt_action_raw" in text
    assert 'for: "00:20:00"' in text


def test_permissive_evopt_write_requires_stable_raw_action() -> None:
    text = writer_text()

    assert "evopt_action_stable_s:" in text
    assert "evopt_release_ready:" in text
    assert "evopt_action_stable_s | int(0) >= 1200" in text
    assert "target_value_stable_s | int(0) >= 90 and evopt_release_ready" in text


def test_restrictive_close_remains_immediate() -> None:
    text = writer_text()

    assert "safety_close_write:" in text
    assert "target_w | float(0) <= 50 and current_w | float(0) > 50" in text
    assert "safety_close_write\n                    or priority_open_write" in text


def test_single_writer_is_preserved() -> None:
    text = writer_text()

    assert text.count("service: number.set_value") == 1
