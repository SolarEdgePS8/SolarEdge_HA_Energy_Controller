from __future__ import annotations

from pathlib import Path
import py_compile

from testbench.patch_ha_24h_component import patch

ROOT = Path(__file__).parents[2]
SOURCE = ROOT / "testbench" / "custom_components" / "se_test_replay" / "__init__.py"
RUNNER = ROOT / "scripts" / "run_ha_24h_replay.sh"


def patched_component(tmp_path: Path) -> str:
    target = tmp_path / "__init__.py"
    target.write_text(SOURCE.read_text(encoding="utf-8"), encoding="utf-8")
    patch(target)
    py_compile.compile(str(target), doraise=True)
    return target.read_text(encoding="utf-8")


def test_configure_keeps_master_off_until_prepare_day(tmp_path: Path) -> None:
    text = patched_component(tmp_path)
    configure = text.split("    async def configure(self) -> None:\n", 1)[1].split(
        "    def evopt(self, row: dict[str, Any]) -> None:\n", 1
    )[0]

    # configure() may turn the master off, but it must never turn it on. The
    # first mode is activated only by prepare_day() after target, timestamps and
    # cooldown state have been reset.
    assert configure.count("input_boolean.se_netzdienlich_enabled") == 1
    assert 'turn_off", "input_boolean.se_netzdienlich_enabled"' in configure
    assert 'turn_on", "input_boolean.se_netzdienlich_enabled"' not in configure


def test_replay_result_files_are_written_off_the_event_loop(tmp_path: Path) -> None:
    text = patched_component(tmp_path)
    assert "def write_results() -> None:" in text
    assert "await asyncio.to_thread(write_results)" in text


def test_fixture_is_loaded_off_the_home_assistant_event_loop(tmp_path: Path) -> None:
    text = patched_component(tmp_path)
    setup = text.split(
        "async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:\n",
        1,
    )[1]
    assert "fixture_text = await asyncio.to_thread(" in setup
    assert "fixture_path.read_text" in setup
    assert "fixture = json.loads(fixture_text)" in setup
    assert ")).read_text(encoding=\"utf-8\"))" not in setup


def test_runtime_runner_rejects_blocking_calls_from_replay_integration() -> None:
    text = RUNNER.read_text(encoding="utf-8")
    assert "Detected blocking call.*se_test_replay" in text


def test_patch_keeps_real_writer_and_session_manager_execution(tmp_path: Path) -> None:
    text = patched_component(tmp_path)
    assert "automation.solaredge_energy_controller_session_manager" in text
    assert "automation.solaredge_energy_controller_charge_limit_writer" in text
    assert "number.test_storage_charge_limit" in text
