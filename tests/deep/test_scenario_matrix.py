from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest
import yaml

from testbench.reference.controller_model import ControllerInput, EvoptAction, Mode, decide


SCENARIO_FILE = Path(__file__).parents[1] / "fixtures" / "controller_scenarios.yaml"
DATA = yaml.safe_load(SCENARIO_FILE.read_text(encoding="utf-8"))["scenarios"]
INPUT_FIELDS = {item.name for item in fields(ControllerInput)}


def _build(case: dict[str, object]) -> ControllerInput:
    raw = dict(case.get("input") or {})
    unknown = set(raw) - INPUT_FIELDS
    assert not unknown, f"unknown ControllerInput fields in {case['id']}: {sorted(unknown)}"
    raw["mode"] = Mode(str(case["mode"]))
    if "evopt_action" in raw:
        raw["evopt_action"] = EvoptAction(str(raw["evopt_action"]))
    return ControllerInput(**raw)


@pytest.mark.parametrize("case", DATA, ids=[str(item["id"]) for item in DATA])
def test_fixed_controller_scenarios(case: dict[str, object]) -> None:
    decision = decide(_build(case))
    expected = case["expect"]
    assert decision.target_w == pytest.approx(float(expected["target_w"]))
    assert decision.source.value == expected["source"]
    assert decision.write.should_write is bool(expected["write"])
    assert 0 <= decision.target_w <= 5000


def test_every_mode_has_multiple_fixed_scenarios() -> None:
    counts = {mode.value: 0 for mode in Mode}
    for case in DATA:
        counts[str(case["mode"])] += 1
    assert all(count >= 4 for count in counts.values()), counts


def test_scenario_ids_are_unique() -> None:
    ids = [str(item["id"]) for item in DATA]
    assert len(ids) == len(set(ids))
