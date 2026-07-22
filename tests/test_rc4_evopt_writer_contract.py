from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _text(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _helper_block(text: str, helper: str) -> str:
    match = re.search(
        rf"^  {re.escape(helper)}:\s*$\n(?P<body>(?:^    .*\n)*)",
        text,
        re.M,
    )
    assert match, helper
    return match.group("body")


def test_restart_relevant_helpers_restore_previous_state() -> None:
    core = _text("package/se_controller_00_core.yaml")
    evopt = _text("package/se_controller_50_mode_evopt.yaml")

    assert "initial:" not in _helper_block(core, "se_nf_site_config_confirmed")
    assert "initial:" not in _helper_block(core, "se_netzdienlich_enabled")
    assert "initial:" not in _helper_block(evopt, "se_nf_evopt_shadow_enabled")
    assert "initial:" not in _helper_block(evopt, "se_nf_evopt_base_url")


def test_evopt_startup_handover_is_restrictive_first() -> None:
    evopt = _text("package/se_controller_50_mode_evopt.yaml")

    assert "seconds: 180" in evopt
    assert "fallback_grace_s = 1200" in evopt
    assert "fallback_permissive_ready" in evopt
    assert "held_w | round(0)" in evopt
    assert "selected == 'EVOpt optimiert' and charge_block" in evopt


def test_charge_writer_has_one_write_path_and_delayed_open() -> None:
    writer = _text("package/se_controller_80_charge_writer.yaml")

    assert writer.count("service: number.set_value") == 1
    assert 'for: "00:01:30"' in writer
    assert "target_value_stable_s" in writer
    assert "permissive_open_stable" in writer
    assert "se_charge_limit_write_intent" in writer
    assert "sensor.se_nf_evopt_candidate_target_w" in writer
    assert not re.search(r"sensor\.se_nf_evopt_candidate_target(?!_w)\b", writer)


def test_watchdog_only_enforces_raw_holdcharge_when_evopt_is_active() -> None:
    source = _text("custom_components/se_write_watchdog/__init__.py")
    manifest = json.loads(
        _text("custom_components/se_write_watchdog/manifest.json")
    )

    assert manifest["version"] == "1.0.2"
    assert 'active_control and action_raw == "holdcharge"' in source
    assert "number_set_value_call" in source
    assert "charge_limit_state_change" in source
    assert "roundtrip_detected" in source
