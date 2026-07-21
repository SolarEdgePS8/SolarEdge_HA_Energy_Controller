from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADAPTER_PATH = ROOT / "scripts/runtime/se_nf_evopt_shadow_adapter.py"

spec = importlib.util.spec_from_file_location("evopt_adapter", ADAPTER_PATH)
assert spec and spec.loader
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def test_stale_suggestion_is_replaced_after_slot_boundary() -> None:
    selected = adapter.select_action(
        {"action": "holdcharge"},
        current_index=1,
        charge_w=5000.0,
        discharge_w=0.0,
        import_w=0.0,
        export_w=0.0,
    )
    assert selected["action"] == "normal"
    assert selected["source"] == "slot_override_suggestion_mismatch"
    assert selected["suggestion_overridden"] is True
    assert adapter.action_matches_slot("normal", 5000.0, 0.0, 0.0, 0.0)


def test_matching_first_slot_suggestion_remains_authoritative() -> None:
    selected = adapter.select_action(
        {"action": "holdcharge"},
        current_index=0,
        charge_w=0.0,
        discharge_w=0.0,
        import_w=0.0,
        export_w=1000.0,
    )
    assert selected["action"] == "holdcharge"
    assert selected["source"] == "suggestion"
    assert selected["suggestion_overridden"] is False


def test_mismatching_first_slot_suggestion_uses_validated_slot() -> None:
    selected = adapter.select_action(
        {"action": "holdcharge"},
        current_index=0,
        charge_w=5000.0,
        discharge_w=0.0,
        import_w=0.0,
        export_w=0.0,
    )
    assert selected["action"] == "normal"
    assert selected["source"] == "slot_override_suggestion_mismatch"
    assert selected["suggestion_plan_consistent"] is False


def test_missing_suggestion_uses_current_slot() -> None:
    selected = adapter.select_action(
        {},
        current_index=2,
        charge_w=0.0,
        discharge_w=0.0,
        import_w=1200.0,
        export_w=0.0,
    )
    assert selected["action"] == "hold"
    assert selected["source"] == "slot_grid_import_hold"


def test_contradictory_slot_remains_blocked() -> None:
    selected = adapter.select_action(
        {},
        current_index=1,
        charge_w=5000.0,
        discharge_w=5000.0,
        import_w=0.0,
        export_w=0.0,
    )
    assert selected["action"] == "unknown"
    assert selected["source"] == "slot_conflict_charge_discharge"
    assert not adapter.action_matches_slot("unknown", 5000.0, 5000.0, 0.0, 0.0)


def test_yaml_keeps_active_control_during_action_stabilization() -> None:
    text = (ROOT / "package/se_controller_50_mode_evopt.yaml").read_text(encoding="utf-8")
    active_block = text.split("- name: SE NF EVOpt Active Control", 1)[1].split(
        "- name: SE NF EVOpt Discharge Lock Request", 1
    )[0]
    state_block = active_block.split("attributes:", 1)[0]
    assert "sensor.se_nf_evopt_action_raw" in state_block
    assert "sensor.se_nf_evopt_action_stable" not in state_block
    assert "restrictive_immediate_permissive_delayed" in active_block


def test_permissive_transitions_are_delayed_without_legacy_fallback() -> None:
    text = (ROOT / "package/se_controller_50_mode_evopt.yaml").read_text(encoding="utf-8")
    assert "se_nf_evopt_charge_block_request" in text
    assert "delay_off:\n          seconds: 60" in text
    assert "se_nf_evopt_grid_charge_request" in text
    assert "delay_on:\n          seconds: 60" in text
    assert "slot_override_suggestion_mismatch" in (
        ROOT / "scripts/runtime/se_nf_evopt_shadow_adapter.py"
    ).read_text(encoding="utf-8")


def test_restrictive_holdcharge_is_immediate_even_before_helper_delay_updates() -> None:
    evopt = (ROOT / "package/se_controller_50_mode_evopt.yaml").read_text(encoding="utf-8")
    writer = (ROOT / "package/se_controller_80_charge_writer.yaml").read_text(encoding="utf-8")
    assert "action_raw == 'holdcharge' or charge_block" in evopt
    assert "sensor.se_nf_evopt_action_raw') != 'holdcharge'" in writer
