from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[2]
ADAPTER_PATH = ROOT / "scripts" / "runtime" / "se_nf_evopt_shadow_adapter.py"


def load_adapter():
    spec = importlib.util.spec_from_file_location("se_nf_evopt_shadow_adapter", ADAPTER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load_adapter()


def suggestion(action: str) -> dict[str, object]:
    return {"action": action, "actionable": True}


def test_slot_holdcharge_overrides_first_slot_normal_suggestion() -> None:
    result = adapter.select_action(
        suggestion("normal"),
        current_index=0,
        charge_w=0.0,
        discharge_w=310.0,
        import_w=0.0,
        export_w=0.0,
    )

    assert result["slot_action"] == "holdcharge"
    assert result["action"] == "holdcharge"
    assert result["source"] == "slot_restrictive_override_suggestion"
    assert result["suggestion_overridden"] is True


def test_export_slot_also_blocks_permissive_normal_suggestion() -> None:
    result = adapter.select_action(
        suggestion("normal"),
        current_index=0,
        charge_w=0.0,
        discharge_w=0.0,
        import_w=0.0,
        export_w=900.0,
    )

    assert result["slot_action"] == "holdcharge"
    assert result["action"] == "holdcharge"


def test_holdcharge_suggestion_remains_restrictive_during_neutral_slot() -> None:
    result = adapter.select_action(
        suggestion("holdcharge"),
        current_index=0,
        charge_w=0.0,
        discharge_w=0.0,
        import_w=0.0,
        export_w=0.0,
    )

    assert result["slot_action"] == "normal"
    assert result["action"] == "holdcharge"
    assert result["source"] == "suggestion_restrictive_override_slot"


def test_normal_is_released_only_after_both_sources_are_permissive() -> None:
    result = adapter.select_action(
        suggestion("normal"),
        current_index=0,
        charge_w=0.0,
        discharge_w=0.0,
        import_w=0.0,
        export_w=0.0,
    )

    assert result["action"] == "normal"


def test_observed_night_sequence_never_opens_during_source_conflict() -> None:
    effective_actions: list[str] = []

    # Repeated optimizer replans: a fresh first slot carries a permissive
    # suggestion while the validated current slot still plans discharge.
    for _ in range(20):
        effective_actions.append(
            adapter.select_action(
                suggestion("normal"),
                current_index=0,
                charge_w=0.0,
                discharge_w=310.0,
                import_w=0.0,
                export_w=0.0,
            )["action"]
        )

        # Reverse mismatch observed later: suggestion still requests a block,
        # while the newest slot has already become neutral.
        effective_actions.append(
            adapter.select_action(
                suggestion("holdcharge"),
                current_index=1,
                charge_w=0.0,
                discharge_w=0.0,
                import_w=0.0,
                export_w=0.0,
            )["action"]
        )

    assert set(effective_actions) == {"holdcharge"}
    assert all(
        first == second
        for first, second in zip(effective_actions, effective_actions[1:])
    )
