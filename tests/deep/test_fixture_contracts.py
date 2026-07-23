from __future__ import annotations

import csv
import json
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
import yaml

from scripts.export_fixture import export_csv, export_states
from scripts.privacy_scan import scan_paths, self_test

ROOT = Path(__file__).parents[2]
FIXTURES = ROOT / "testbench" / "fixtures"
SCHEMA = ROOT / "testbench" / "schema" / "real_day_fixture.schema.json"
CALIBRATED = FIXTURES / "daily_balance_calibrated_example_15m.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator() -> Draft202012Validator:
    return Draft202012Validator(load(SCHEMA), format_checker=FormatChecker())


def records(fixture: dict) -> list[dict]:
    return [dict(zip(fixture["columns"], row, strict=True)) for row in fixture["rows"]]


def energy(rows: list[dict], role: str) -> float:
    return sum(float(row[role]) for row in rows) * 0.25 / 1000


def test_all_public_15m_fixtures_validate_against_formal_schema() -> None:
    files = sorted(FIXTURES.glob("*_15m.json"))
    assert len(files) >= 2
    check = validator()
    for path in files:
        errors = sorted(check.iter_errors(load(path)), key=lambda item: list(item.path))
        assert not errors, (path, [error.message for error in errors[:10]])


def test_all_public_fixtures_have_complete_monotonic_day_and_matching_totals() -> None:
    role_to_total = {
        "pv_w": "actual_pv_kwh",
        "home_w": "actual_load_kwh",
        "grid_import_w": "actual_grid_import_kwh",
        "grid_export_w": "actual_grid_export_kwh",
        "battery_charge_w": "actual_battery_charge_kwh",
        "battery_discharge_w": "actual_battery_discharge_kwh",
    }
    for path in sorted(FIXTURES.glob("*_15m.json")):
        fixture = load(path)
        rows = records(fixture)
        assert [row["slot"] for row in rows] == list(range(96))
        assert [row["minute"] for row in rows] == list(range(0, 1440, 15))
        assert max(abs(float(row["energy_balance_residual_w"])) for row in rows) <= 20
        for role, total in role_to_total.items():
            assert abs(energy(rows, role) - float(fixture[total])) <= 0.011, (
                path,
                role,
                energy(rows, role),
                fixture[total],
            )


def test_calibrated_fixture_is_explicitly_synthetic_and_uses_only_aggregate_targets() -> None:
    fixture = load(CALIBRATED)
    assert fixture["source_kind"] == "synthetic_profile_calibrated_to_anonymized_daily_energy_totals"
    assert "Synthetic" in fixture["privacy"]
    assert fixture["actual_pv_kwh"] == 25.646
    assert fixture["actual_load_kwh"] == 9.620
    assert fixture["actual_grid_import_kwh"] == 0.177
    assert fixture["actual_grid_export_kwh"] == 17.503
    assert fixture["actual_battery_charge_kwh"] == 2.660
    assert fixture["actual_battery_discharge_kwh"] == 3.960


def test_privacy_scanner_self_test_and_public_fixture_gate() -> None:
    self_test()
    assert scan_paths([FIXTURES]) == []


def test_csv_exporter_discards_source_column_names_and_emits_schema_valid_fixture(
    tmp_path: Path,
) -> None:
    source = load(CALIBRATED)
    source_rows = records(source)
    csv_path = tmp_path / "private-source.csv"
    mapping_path = tmp_path / "private-mapping.yaml"
    output_path = tmp_path / "public-fixture.json"

    source_columns = {
        "timestamp": "local_timestamp",
        "pv_w": "roof_generation_original",
        "home_w": "building_load_original",
        "grid_import_w": "meter_import_original",
        "grid_export_w": "meter_export_original",
        "battery_charge_w": "storage_charge_original",
        "battery_discharge_w": "storage_discharge_original",
        "soc_pct": "storage_soc_original",
        "pv_forecast_total_kwh": "forecast_total_original",
        "pv_forecast_remaining_kwh": "forecast_remaining_original",
        "pv_forecast_tomorrow_kwh": "forecast_tomorrow_original",
        "evopt_action": "optimizer_action_original",
        "evopt_healthy": "optimizer_health_original",
    }
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(source_columns.values()))
        writer.writeheader()
        for row in source_rows:
            writer.writerow(
                {
                    source_columns["timestamp"]: row["time"],
                    **{
                        source_columns[key]: row[key]
                        for key in source_columns
                        if key != "timestamp"
                    },
                }
            )

    mapping = {
        "source": {"timestamp_column": source_columns["timestamp"]},
        "metadata": {
            "name": "exporter_roundtrip_15m",
            "source_date": "2026-07-01",
            "timezone": "Europe/Berlin",
            "cadence_minutes": 15,
            "battery_capacity_kwh": source["battery_capacity_kwh"],
            "battery_efficiency": source["battery_efficiency"],
            "forecast_scale_observed": source["forecast_scale_observed"],
            "forecast_total_kwh": source["forecast_total_kwh"],
            "evopt_timeline_kind": "test_exporter_roundtrip",
        },
        "roles": {key: value for key, value in source_columns.items() if key != "timestamp"},
    }
    mapping_path.write_text(yaml.safe_dump(mapping, sort_keys=False), encoding="utf-8")

    exported = export_csv(csv_path, mapping_path, output_path)
    validator().validate(exported)
    serialized = output_path.read_text(encoding="utf-8")
    for private_column in source_columns.values():
        assert private_column not in serialized
    assert scan_paths([output_path]) == []


def test_states_export_is_marked_local_and_reports_missing_entities(tmp_path: Path) -> None:
    states_path = tmp_path / "states.json"
    mapping_path = tmp_path / "mapping.yaml"
    output_path = tmp_path / "roles.json"
    states_path.write_text(
        json.dumps(
            [
                {
                    "entity_id": "sensor.private_pv",
                    "state": "1234",
                    "attributes": {"unit_of_measurement": "W"},
                }
            ]
        ),
        encoding="utf-8",
    )
    mapping_path.write_text(
        yaml.safe_dump(
            {
                "roles": {
                    "pv_w": "sensor.private_pv",
                    "home_w": "sensor.private_home",
                }
            }
        ),
        encoding="utf-8",
    )
    result = export_states(states_path, mapping_path, output_path)
    assert result["public_fixture"] is False
    assert result["roles"]["pv_w"]["present"] is True
    assert result["roles"]["home_w"]["present"] is False
