from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parents[1]
EVOPT_PACKAGE = ROOT / "package" / "se_controller_50_mode_evopt.yaml"


def charge_block_section() -> str:
    text = EVOPT_PACKAGE.read_text(encoding="utf-8")
    start = text.index("      - name: SE NF EVOpt Charge Block Request\n")
    end = text.index("      - name: SE NF EVOpt Differs From Legacy\n", start)
    return text[start:end]


def test_holdcharge_still_blocks_immediately() -> None:
    section = charge_block_section()
    assert "states('sensor.se_nf_evopt_action_raw') == 'holdcharge'" in section
    assert "delay_on:" not in section


def test_charge_release_requires_twenty_stable_minutes() -> None:
    section = charge_block_section()
    assert "delay_off:\n            seconds: 1200" in section
    assert "seconds: 180" not in section


def test_only_the_evopt_charge_block_contract_is_addressed() -> None:
    section = charge_block_section()
    assert "number.set_value" not in section
    assert "service:" not in section
