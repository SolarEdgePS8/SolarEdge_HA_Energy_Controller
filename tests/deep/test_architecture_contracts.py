from __future__ import annotations

import re
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[2]
PACKAGE = ROOT / "package"


def _text(name: str) -> str:
    return (PACKAGE / name).read_text(encoding="utf-8")


def test_exactly_18_controller_packages_exist() -> None:
    files = sorted(PACKAGE.glob("se_controller_*.yaml"))
    assert len(files) == 18, [p.name for p in files]


def test_all_package_yaml_is_parseable_without_duplicate_top_level_failure() -> None:
    for path in PACKAGE.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict), path


def test_modes_do_not_write_directly_to_solaredge() -> None:
    for pattern in ("20_mode", "30_mode", "40_mode", "50_mode"):
        matches = list(PACKAGE.glob(f"se_controller_{pattern}*.yaml"))
        assert matches, pattern
        for path in matches:
            text = path.read_text(encoding="utf-8")
            assert "number.set_value" not in text, path
            assert "select.select_option" not in text, path


def test_single_charge_writer_and_required_gates() -> None:
    writers = []
    for path in PACKAGE.glob("*.yaml"):
        text = path.read_text(encoding="utf-8")
        if "service: number.set_value" in text and "se_nf_charge_limit_entity" in text:
            writers.append(path.name)
    assert writers == ["se_controller_80_charge_writer.yaml"]
    text = _text("se_controller_80_charge_writer.yaml")
    for required in (
        "binary_sensor.se_nf_controller_write_enabled",
        "sensor.se_nf_desired_target",
        "target_value_stable_s",
        "permissive_open_stable",
        "se_charge_limit_write_intent",
    ):
        assert required in text


def test_evopt_transition_constants_are_present() -> None:
    text = _text("se_controller_50_mode_evopt.yaml")
    assert "seconds: 180" in text
    assert "fallback_grace_s = 1200" in text
    assert "held_w | round(0)" in text
    assert "sensor.se_nf_evopt_candidate_target_w" in text


def test_writer_uses_90_second_permissive_trigger() -> None:
    text = _text("se_controller_80_charge_writer.yaml")
    assert 'for: "00:01:30"' in text
    assert text.count("service: number.set_value") == 1


def test_no_private_ipv4_addresses_in_public_runtime_files() -> None:
    private = re.compile(
        r"\b(?:10(?:\.\d{1,3}){3}|192\.168(?:\.\d{1,3}){2}|"
        r"172\.(?:1[6-9]|2\d|3[01])(?:\.\d{1,3}){2})\b"
    )
    roots = [PACKAGE, ROOT / "scripts", ROOT / "custom_components", ROOT / "testbench"]
    violations: list[str] = []
    for base in roots:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".sh", ".yaml", ".yml", ".json"}:
                if private.search(path.read_text(encoding="utf-8", errors="replace")):
                    violations.append(str(path.relative_to(ROOT)))
    assert not violations
