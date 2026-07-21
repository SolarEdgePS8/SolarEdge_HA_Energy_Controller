from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "package"

EXPECTED_PACKAGE_FILES = {
    "se_controller_00_core.yaml",
    "se_controller_05_external_interfaces.yaml",
    "se_controller_10_base_planning.yaml",
    "se_controller_11_weather_planning.yaml",
    "se_controller_12_load_pv_planning.yaml",
    "se_controller_14_data_sources.yaml",
    "se_controller_20_mode_self_consumption.yaml",
    "se_controller_30_mode_grid_friendly.yaml",
    "se_controller_40_mode_battery_care.yaml",
    "se_controller_50_mode_evopt.yaml",
    "se_controller_60_safety.yaml",
    "se_controller_70_arbiter.yaml",
    "se_controller_80_charge_writer.yaml",
    "se_controller_82_discharge_writer.yaml",
    "se_controller_83_storage_control_writer.yaml",
    "se_controller_84_command_mode_writer.yaml",
    "se_controller_90_diagnostics_planning.yaml",
    "se_controller_98_compatibility_automations.yaml",
}

MODES = {
    "Eigenverbrauch maximieren",
    "Netzdienlich laden",
    "Akku schonen",
    "EVOpt optimiert",
}


def package_text() -> str:
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(PACKAGE.glob("*.yaml")))


def test_exact_package_inventory() -> None:
    assert {p.name for p in PACKAGE.glob("*.yaml")} == EXPECTED_PACKAGE_FILES


def test_all_yaml_files_parse() -> None:
    for path in sorted(PACKAGE.glob("*.yaml")):
        assert yaml.safe_load(path.read_text(encoding="utf-8")) is not None


def test_all_four_modes_are_selectable_and_routed() -> None:
    core = (PACKAGE / "se_controller_00_core.yaml").read_text(encoding="utf-8")
    arbiter = (PACKAGE / "se_controller_70_arbiter.yaml").read_text(encoding="utf-8")
    for mode in MODES:
        assert mode in core
        assert mode in arbiter or mode == "Netzdienlich laden"


def test_evopt_has_complete_grid_friendly_fallback() -> None:
    text = (PACKAGE / "se_controller_50_mode_evopt.yaml").read_text(encoding="utf-8")
    assert "fallback_profile: Netzdienlich laden" in text
    assert "binary_sensor.se_nf_evopt_shadow_ready" in text
    assert "binary_sensor.se_nf_evopt_active_control" in text


def test_each_writer_uses_central_gate_and_dynamic_mapping() -> None:
    contracts = {
        "se_controller_80_charge_writer.yaml": "input_text.se_nf_charge_limit_entity",
        "se_controller_82_discharge_writer.yaml": "input_text.se_nf_discharge_limit_entity",
        "se_controller_83_storage_control_writer.yaml": "input_text.se_nf_storage_control_mode_entity",
        "se_controller_84_command_mode_writer.yaml": "input_text.se_nf_command_mode_entity",
    }
    for filename, mapping in contracts.items():
        text = (PACKAGE / filename).read_text(encoding="utf-8")
        assert "binary_sensor.se_nf_controller_write_enabled" in text
        assert mapping in text


def test_no_forbidden_site_dependencies_in_package() -> None:
    text = package_text().lower()
    forbidden = [
        "homeassistant.local",
        "192.168.",
        "switch.se_akku_remote_control",
        "warp_",
        "evcc_warp1",
        "enyaq_",
        "switch.shelly",
        "akku_saver_",
        "preisphase_",
    ]
    for token in forbidden:
        assert token not in text


def test_no_duplicate_helpers_or_automation_ids() -> None:
    helper_domains = {
        "input_boolean", "input_datetime", "input_number", "input_select",
        "input_text", "counter", "timer",
    }
    helper_defs: dict[str, list[str]] = defaultdict(list)
    automation_ids: list[str] = []
    for path in sorted(PACKAGE.glob("*.yaml")):
        current_domain = None
        for line in path.read_text(encoding="utf-8").splitlines():
            top = re.match(r"^([a-z_]+):\s*$", line)
            if top:
                current_domain = top.group(1)
                continue
            if current_domain in helper_domains:
                helper = re.match(r"^  ([A-Za-z0-9_]+):\s*$", line)
                if helper:
                    helper_defs[f"{current_domain}.{helper.group(1)}"].append(path.name)
            auto = re.match(r"^  - id:\s*[\"']?([^\"']+)[\"']?\s*$", line)
            if auto:
                automation_ids.append(auto.group(1).strip())
    assert not {k: v for k, v in helper_defs.items() if len(v) > 1}
    assert not {k: v for k, v in Counter(automation_ids).items() if v > 1}


def test_every_site_config_key_is_supported() -> None:
    env_keys = set()
    for raw in (ROOT / "config/site_config.env.example").read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and "=" in line:
            env_keys.add(line.split("=", 1)[0].strip())

    tree = ast.parse((ROOT / "scripts/apply_site_config.py").read_text(encoding="utf-8"))
    handled = {"SITE_CONFIG_CONFIRMED"}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if any(name in {"TEXT_MAP", "NUMBER_MAP", "BOOLEAN_MAP"} for name in names):
                handled.update(ast.literal_eval(node.value).keys())
    assert env_keys <= handled
