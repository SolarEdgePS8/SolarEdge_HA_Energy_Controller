from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "discover_entities.py"
    spec = importlib.util.spec_from_file_location("discover_entities", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scoring_and_safe_env_generation():
    module = load_module()
    states = [
        {
            "entity_id": "number.solaredge_i1_storage_charge_limit",
            "state": "5000",
            "attributes": {
                "friendly_name": "SolarEdge I1 Storage Charge Limit",
                "unit_of_measurement": "W",
                "min": 0,
                "max": 1000000,
            },
        },
        {
            "entity_id": "number.solaredge_i1_storage_discharge_limit",
            "state": "5000",
            "attributes": {
                "friendly_name": "SolarEdge I1 Storage Discharge Limit",
                "unit_of_measurement": "W",
            },
        },
        {
            "entity_id": "sensor.solaredge_i1_b1_state_of_energy",
            "state": "54.2",
            "attributes": {
                "friendly_name": "SolarEdge Battery State of Energy",
                "unit_of_measurement": "%",
                "device_class": "battery",
            },
        },
        {
            "entity_id": "sensor.solaredge_i1_b1_maximum_energy",
            "state": "14.2",
            "attributes": {
                "friendly_name": "SolarEdge Battery Maximum Energy",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
            },
        },
        {
            "entity_id": "sensor.solaredge_i1_ac_power",
            "state": "2300",
            "attributes": {
                "friendly_name": "SolarEdge I1 AC Power",
                "unit_of_measurement": "W",
                "device_class": "power",
            },
        },
        {
            "entity_id": "sensor.house_consumption_power",
            "state": "620",
            "attributes": {
                "friendly_name": "House Consumption Power",
                "unit_of_measurement": "W",
                "device_class": "power",
            },
        },
        {
            "entity_id": "sensor.pv_forecast_today_remaining",
            "state": "6.4",
            "attributes": {
                "friendly_name": "PV Forecast Today Remaining",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
            },
        },
        {
            "entity_id": "sensor.pv_forecast_today_total",
            "state": "12.1",
            "attributes": {
                "friendly_name": "PV Forecast Today Total",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
            },
        },
        {
            "entity_id": "sensor.pv_forecast_tomorrow",
            "state": "14.0",
            "attributes": {
                "friendly_name": "PV Forecast Tomorrow",
                "unit_of_measurement": "kWh",
                "device_class": "energy",
            },
        },
        {
            "entity_id": "weather.home",
            "state": "cloudy",
            "attributes": {"friendly_name": "Weather Home"},
        },
    ]

    categories = module.classify(states)

    assert categories["charge_limit"][0].entity_id == (
        "number.solaredge_i1_storage_charge_limit"
    )
    assert all(
        "discharge" not in item.entity_id
        for item in categories["charge_limit"]
    )
    assert categories["battery_soc"][0].confidence == "high"
    assert categories["pv_power"][0].entity_id == "sensor.solaredge_i1_ac_power"

    env = module.create_env(categories)
    assert "SITE_CONFIG_CONFIRMED=NO" in env
    assert "EVOPT_ENABLED=NO" in env
    assert (
        "CHARGE_LIMIT_ENTITY=number.solaredge_i1_storage_charge_limit" in env
    )
    assert "BATTERY_CAPACITY_KWH=" in env
    assert "SITE_CONFIG_CONFIRMED=YES" not in env


def test_unknown_states_are_reported_but_not_high_confidence():
    module = load_module()
    categories = module.classify(
        [
            {
                "entity_id": "sensor.example_pv_power",
                "state": "unavailable",
                "attributes": {
                    "friendly_name": "PV Power",
                    "unit_of_measurement": "W",
                    "device_class": "power",
                },
            }
        ]
    )
    assert categories["pv_power"]
    assert categories["pv_power"][0].state_available is False
    assert categories["pv_power"][0].confidence != "high"


def test_env_does_not_auto_map_wrong_power_unit():
    module = load_module()
    categories = module.classify(
        [
            {
                "entity_id": "sensor.example_pv_power_kw",
                "state": "2.5",
                "attributes": {
                    "friendly_name": "PV Power",
                    "unit_of_measurement": "kW",
                    "device_class": "power",
                },
            },
            {
                "entity_id": "sensor.example_house_power_kw",
                "state": "0.6",
                "attributes": {
                    "friendly_name": "House Consumption Power",
                    "unit_of_measurement": "kW",
                    "device_class": "power",
                },
            },
        ]
    )
    assert categories["pv_power"]
    env = module.create_env(categories)
    assert "LIVE_PV_POWER_ENTITIES=\n" in env
    assert "LIVE_CONSUMPTION_POWER_ENTITIES=\n" in env
    assert "sensor.example_pv_power_kw" in env  # visible only in comments
