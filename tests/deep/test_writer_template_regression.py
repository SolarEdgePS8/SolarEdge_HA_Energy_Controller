from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, StrictUndefined
import yaml


ROOT = Path(__file__).parents[2]
WRITER = ROOT / "package" / "se_controller_80_charge_writer.yaml"


def variables() -> dict[str, str]:
    document = yaml.safe_load(WRITER.read_text(encoding="utf-8"))
    return document["automation"][0]["action"][1]["variables"]


def render_bool(template: str, *, state_map: dict[str, str], context: dict[str, object]) -> bool:
    env = Environment(undefined=StrictUndefined, autoescape=False)

    def states(entity: str) -> str:
        return state_map.get(entity, "unknown")

    def is_state(entity: str, expected: str) -> bool:
        return states(entity) == expected

    rendered = env.from_string(template).render(states=states, is_state=is_state, **context).strip()
    assert rendered in {"True", "False"}, rendered
    return rendered == "True"


def test_exact_live_state_cannot_reach_write_allowed() -> None:
    templates = variables()
    state_map = {
        "sensor.se_nf_optimization_mode_effective": "EVOpt optimiert",
        "sensor.se_nf_evopt_action_raw": "holdcharge",
        "sensor.se_nf_evopt_action_stable": "holdcharge",
        "binary_sensor.se_nf_evopt_charge_block_request": "on",
        "number.test_storage_charge_limit": "0",
    }

    restrictive = render_bool(
        templates["evopt_restrictive_active"],
        state_map=state_map,
        context={},
    )
    assert restrictive

    release_ready = render_bool(
        templates["evopt_release_ready"],
        state_map=state_map,
        context={
            "evopt_restrictive_active": restrictive,
            "emergency_open": True,
            "evopt_action_stable_s": 9999,
        },
    )
    assert not release_ready

    permissive = render_bool(
        templates["permissive_open_stable"],
        state_map=state_map,
        context={
            "emergency_open": True,
            "evopt_restrictive_active": restrictive,
            "target_value_stable_s": 90,
            "evopt_release_ready": release_ready,
        },
    )
    assert not permissive

    priority = render_bool(
        templates["priority_open_write"],
        state_map=state_map,
        context={
            "target_w": 5000,
            "target_open_allowed": True,
            "permissive_open_stable": permissive,
        },
    )
    assert not priority

    allowed = render_bool(
        templates["write_allowed"],
        state_map=state_map,
        context={
            "controller_write_enabled": True,
            "entity": "number.test_storage_charge_limit",
            "target_w": 5000,
            "current_w": 0,
            "delta_w": 5000,
            "min_delta_w": 100,
            "safety_close_write": False,
            "priority_open_write": priority,
            "normal_write_window_ok": True,
            "target_open_allowed": True,
            "permissive_open_stable": permissive,
        },
    )
    assert not allowed


def test_emergency_open_without_restrictive_evopt_signal_remains_possible() -> None:
    templates = variables()
    state_map = {
        "sensor.se_nf_optimization_mode_effective": "EVOpt optimiert",
        "sensor.se_nf_evopt_action_raw": "normal",
        "sensor.se_nf_evopt_action_stable": "normal",
        "binary_sensor.se_nf_evopt_charge_block_request": "off",
    }

    restrictive = render_bool(
        templates["evopt_restrictive_active"],
        state_map=state_map,
        context={},
    )
    assert not restrictive

    release_ready = render_bool(
        templates["evopt_release_ready"],
        state_map=state_map,
        context={
            "evopt_restrictive_active": restrictive,
            "emergency_open": True,
            "evopt_action_stable_s": 0,
        },
    )
    assert release_ready


def test_zero_write_is_still_independent_of_the_opening_guard() -> None:
    templates = variables()
    state_map: dict[str, str] = {}

    close = render_bool(
        templates["safety_close_write"],
        state_map=state_map,
        context={"target_w": 0, "current_w": 5000},
    )
    assert close
