"""Patch the copied test-only HA replay component for accelerated runtime use.

Production packages are never modified. Every replacement is guarded so a
future source change fails visibly instead of silently weakening the test.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def replace_once(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{name}: expected exactly one anchor, found {count}")
    return text.replace(old, new, 1)


def patch(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = text.replace("datetime(2031, 7, 21", "datetime(2026, 7, 21")
    text = replace_once(text, "import logging\n", "import logging\nimport os\n", "os-import")

    text = replace_once(
        text,
        '''    async def clock(self, value: datetime) -> None:
        self.now = value
        self.hass.bus.async_fire(EVENT_TIME_CHANGED, {"now": value.astimezone(UTC)})
        await self.settle()
''',
        '''    async def clock(self, value: datetime) -> None:
        self.now = value

        def write_clock_atomically() -> None:
            target = Path("/config/faketime.txt")
            temporary = target.with_suffix(".tmp")
            temporary.write_text(
                value.strftime("%Y-%m-%d %H:%M:%S") + "\\n",
                encoding="utf-8",
            )
            os.replace(temporary, target)

        await asyncio.to_thread(write_clock_atomically)
        self.hass.bus.async_fire(EVENT_TIME_CHANGED, {"now": value.astimezone(UTC)})
        await self.settle()
''',
        "clock",
    )

    text = replace_once(
        text,
        '''    async def svc(self, domain: str, service: str, entity: str, **data: Any) -> None:
        await self.hass.services.async_call(domain, service, {"entity_id": entity, **data}, blocking=True)
        await self.settle()

    def state(self, entity: str) -> str:
''',
        '''    async def svc(self, domain: str, service: str, entity: str, **data: Any) -> None:
        await self.hass.services.async_call(domain, service, {"entity_id": entity, **data}, blocking=True)
        await self.settle()

    async def trigger_automation(self, entity: str) -> None:
        if self.hass.states.get(entity) is None:
            raise RuntimeError(f"missing production automation: {entity}")
        await self.hass.services.async_call(
            "automation",
            "trigger",
            {"entity_id": entity, "skip_condition": False},
            blocking=True,
        )
        await self.settle()

    async def refresh_controller(self) -> None:
        entities = [
            "sensor.se_controller_eigenverbrauch_next_session_state",
            "sensor.se_controller_netzdienlich_next_session_state",
            "sensor.se_controller_akku_schonen_next_session_state",
            "sensor.se_nf_optimization_mode_effective",
            "sensor.se_nf_desired_target",
            "sensor.se_nf_decision_reason",
            "sensor.se_nf_writer_mode",
            "sensor.se_nf_active_planned_start_timestamp",
            "sensor.se_nf_config_check",
            "sensor.se_nf_sanity_check",
            "binary_sensor.se_nf_controller_write_enabled",
            "binary_sensor.se_nf_write_lock_active",
        ]
        await self.hass.services.async_call(
            "homeassistant",
            "update_entity",
            {"entity_id": entities},
            blocking=True,
        )
        await self.settle()

    def state(self, entity: str) -> str:
''',
        "services",
    )

    text = replace_once(
        text,
        '''    async def configure(self) -> None:
        self.phase = "configure"
        await self.svc("input_boolean", "turn_off", "input_boolean.se_netzdienlich_enabled")
''',
        '''    async def configure(self) -> None:
        self.phase = "configure"
        # Cancel the real writer's 150-second startup delay. Its automation is
        # then re-enabled and invoked normally by the replay.
        writer = "automation.solaredge_energy_controller_charge_limit_writer"
        await self.svc("automation", "turn_off", writer)
        await self.svc("automation", "turn_on", writer)
        await self.svc("input_boolean", "turn_off", "input_boolean.se_netzdienlich_enabled")
''',
        "configure-writer-reset",
    )

    text = replace_once(
        text,
        '''        for entity, value in values.items():
            await self.svc("input_number", "set_value", entity, value=value)
        self.evopt(row)
        await self.settle()
''',
        '''        for entity, value in values.items():
            await self.svc("input_number", "set_value", entity, value=value)
        # Direct state injection is the equivalent of a recorder/history replay.
        # It keeps freshness timestamps aligned with the accelerated OS clock.
        direct = {
            "sensor.test_battery_soc": (row["soc_pct"], "%"),
            "sensor.test_battery_capacity": (self.fixture["battery_capacity_kwh"], "kWh"),
            "sensor.test_pv_power": (row["pv_w"], "W"),
            "sensor.test_home_power": (row["home_w"], "W"),
            "sensor.test_pv_remaining": (row["pv_forecast_remaining_kwh"], "kWh"),
            "sensor.test_pv_total": (row["pv_forecast_total_kwh"], "kWh"),
            "sensor.test_pv_tomorrow": (row["pv_forecast_tomorrow_kwh"], "kWh"),
        }
        for entity, (value, unit) in direct.items():
            self.hass.states.async_set(
                entity,
                str(value),
                {"unit_of_measurement": unit, "source": "se_test_replay"},
            )

        # The real SolarEdge integration reports its current number value on
        # every polling cycle even when the value itself does not change.
        # Re-report the unchanged test target directly to Home Assistant so
        # last_reported stays fresh without creating a number.set_value call.
        target = self.hass.states.get(TARGET)
        if target is None:
            raise RuntimeError(f"missing replay target: {TARGET}")
        self.hass.states.async_set(
            TARGET,
            target.state,
            dict(target.attributes),
        )
        self.evopt(row)
        await self.settle()
''',
        "measurements",
    )

    text = replace_once(
        text,
        '''        await self.clock(day)
        await self.svc("input_datetime", "set_datetime", "input_datetime.se_nf_session_planned_start", datetime=(day + timedelta(hours=11, minutes=45)).strftime("%Y-%m-%d %H:%M:%S"))
''',
        '''        await self.clock(day)
        old_write = (day - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
        await self.svc(
            "input_datetime",
            "set_datetime",
            "input_datetime.se_nf_last_write",
            datetime=old_write,
        )
        await self.svc(
            "input_datetime",
            "set_datetime",
            "input_datetime.se_nf_write_lock_until",
            datetime=old_write,
        )
        await self.svc(
            "input_number",
            "set_value",
            "input_number.se_nf_last_applied_charge_limit_w",
            value=0,
        )
        await self.svc("input_datetime", "set_datetime", "input_datetime.se_nf_session_planned_start", datetime=(day + timedelta(hours=11, minutes=45)).strftime("%Y-%m-%d %H:%M:%S"))
''',
        "prepare-day",
    )

    text = replace_once(
        text,
        '''                "writer_mode": "sensor.se_nf_writer_mode",
                "config": "sensor.se_nf_config_check",
''',
        '''                "writer_mode": "sensor.se_nf_writer_mode",
                "write_enabled": "binary_sensor.se_nf_controller_write_enabled",
                "lock_active": "binary_sensor.se_nf_write_lock_active",
                "config": "sensor.se_nf_config_check",
''',
        "snapshot-writer-state",
    )

    text = replace_once(
        text,
        '''                    await self.clock(start)
                    await self.measurements(row)
                    for seconds in (60, 120, 180, 300):
                        await self.clock(start + timedelta(seconds=seconds))
                    snap = self.snapshot(row)
''',
        '''                    await self.clock(start)
                    await self.measurements(row)
                    await self.refresh_controller()
                    await self.trigger_automation(
                        "automation.solaredge_energy_controller_session_manager"
                    )
                    for seconds in (60, 120, 180, 300):
                        await self.clock(start + timedelta(seconds=seconds))
                        await self.refresh_controller()
                        if seconds in (120, 300):
                            await self.trigger_automation(
                                "automation.solaredge_energy_controller_session_manager"
                            )
                            await self.refresh_controller()
                            await self.trigger_automation(
                                "automation.solaredge_energy_controller_charge_limit_writer"
                            )
                    snap = self.snapshot(row)
''',
        "replay-loop",
    )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("component", type=Path)
    args = parser.parse_args()
    patch(args.component)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
