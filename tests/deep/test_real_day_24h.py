from __future__ import annotations

from collections import Counter
from pathlib import Path

from testbench.day_replay import MODES, load_fixture, replay_all

FIXTURE = Path(__file__).parents[2] / "testbench" / "fixtures" / "real_day_2026-07-21_15m.json"


def test_fixture_is_complete_balanced_and_anonymized() -> None:
    fixture = load_fixture(FIXTURE)
    assert fixture["slots"] == 96
    assert fixture["cadence_minutes"] == 15
    assert fixture["actual_pv_kwh"] == 43.62
    assert fixture["actual_load_kwh"] == 11.96
    assert fixture["actual_grid_import_kwh"] == 0.07
    assert fixture["actual_grid_export_kwh"] == 29.87
    assert fixture["actual_battery_charge_kwh"] == 6.22
    assert fixture["actual_battery_discharge_kwh"] == 4.27
    assert max(abs(row["energy_balance_residual_w"]) for row in fixture["records"]) <= 20
    serialized = FIXTURE.read_text(encoding="utf-8").lower()
    for forbidden in ("192.168.", "access_token", "refresh_token", "serial_number", "tutnix"):
        assert forbidden not in serialized


def test_all_four_modes_complete_real_day_without_hard_conflicts() -> None:
    report = replay_all(load_fixture(FIXTURE))
    assert report["pass"] is True
    assert report["modes"] == [mode.value for mode in MODES]
    assert report["total_snapshots"] == 4 * 96
    assert report["hard_conflict_count"] == 0
    for result in report["results"]:
        assert result["slots"] == 96
        assert result["pass"] is True
        assert result["hard_conflicts"] == []
        assert result["write_count"] <= (16 if result["mode"] == "EVOpt optimiert" else 8)


def test_evopt_real_day_exercises_actions_outage_fallback_and_recovery() -> None:
    fixture = load_fixture(FIXTURE)
    action_counts = Counter(row["evopt_action"] for row in fixture["records"])
    for action in ("normal", "holdcharge", "charge", "discharge", "hold", "unavailable"):
        assert action_counts[action] > 0

    report = replay_all(fixture)
    evopt = next(result for result in report["results"] if result["mode"] == "EVOpt optimiert")
    sources = evopt["source_counts"]
    assert sources.get("evopt", 0) > 0
    assert sources.get("evopt_hold_last_confirmed", 0) > 0
    assert sources.get("legacy_grid_friendly_fallback", 0) > 0
    reasons = evopt["reason_counts"]
    assert reasons.get("evopt_restrictive", 0) > 0
    assert reasons.get("evopt_permissive", 0) > 0
    assert any(reason.startswith("fallback_") for reason in reasons)


def test_no_duplicate_or_unclassified_roundtrip_writes() -> None:
    report = replay_all(load_fixture(FIXTURE))
    for result in report["results"]:
        writes = result["writes"]
        assert all(write["old_w"] != write["new_w"] for write in writes)
        assert len({write["at_s"] for write in writes}) == len(writes)
        assert not any(item["type"] == "roundtrip_30m" for item in result["hard_conflicts"])
