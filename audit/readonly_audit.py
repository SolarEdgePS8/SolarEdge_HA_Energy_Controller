#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("root")
parser.add_argument("--release-gate", action="store_true")
args = parser.parse_args()
root = Path(args.root).resolve()

errors: list[str] = []
warnings: list[str] = []

required = {
    "package/se_controller_00_core.yaml",
    "package/se_controller_05_external_interfaces.yaml",
    "package/se_controller_80_charge_writer.yaml",
    "package/se_controller_82_discharge_writer.yaml",
    "package/se_controller_83_storage_control_writer.yaml",
    "package/se_controller_84_command_mode_writer.yaml",
    "scripts/install_package.sh",
    "scripts/rollback.sh",
    "scripts/apply_site_config.py",
    "config/site_config.env.example",
}
for rel in sorted(required):
    if not (root / rel).is_file():
        errors.append(f"MISSING_REQUIRED {rel}")

for forbidden in [
    "package/se_discharge_policy_block.yaml",
    "package/se_lifetime.yaml",
    "package/se_mode_orchestration.yaml",
    "package/solaredge_helpers.yaml",
]:
    if (root / forbidden).exists():
        errors.append(f"FORBIDDEN_PROJECT_FILE {forbidden}")

for path in root.rglob("*"):
    if "__pycache__" in path.parts or path.suffix == ".pyc":
        errors.append(f"COMPILED_PYTHON {path.relative_to(root)}")

for path in root.rglob("*.py"):
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
    except Exception as exc:
        errors.append(f"PYTHON_SYNTAX {path.relative_to(root)}: {exc}")

package_files = sorted((root / "package").glob("*.yaml"))
package_text = "\n".join(
    path.read_text(encoding="utf-8", errors="replace") for path in package_files
)

try:
    import yaml  # type: ignore
except Exception:
    warnings.append("YAML_PARSER_UNAVAILABLE")
else:
    for path in package_files:
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            errors.append(f"YAML_PARSE {path.name}: {exc}")

banned_patterns = {
    "LOCAL_SOLAREDGE_ENTITY": r"\b(?:number|select|switch|sensor)\.solaredge_i1_[A-Za-z0-9_]+",
    "LOCAL_REMOTE_SWITCH": r"\bswitch\.se_akku_remote_control\b",
    "WARP": r"\b(?:sensor|binary_sensor|select)\.warp_[A-Za-z0-9_]+|\bevcc_warp1\b",
    "ENYAQ": r"\benyaq_[A-Za-z0-9_]+|\bskoda_enyaq\b",
    "SHELLY": r"\bswitch\.shelly[A-Za-z0-9_]+",
    "AKKU_SAVER": r"\b(?:sensor|binary_sensor|input_[a-z]+)\.akku_saver_[A-Za-z0-9_]+|\bse_akku_saver_[A-Za-z0-9_]+",
    "LOCAL_PRICE": r"\b(?:sensor|binary_sensor)\.(?:preisphase|borsenpreis|niedrigster_preis|hochster_preis)[A-Za-z0-9_]*",
    "LOCAL_EVOPT_URL": r"homeassistant\.local|https?://(?:192\.168|10\.|172\.(?:1[6-9]|2[0-9]|3[01])\.)",
}
for name, pattern in banned_patterns.items():
    match = re.search(pattern, package_text, re.I)
    if match:
        errors.append(f"SITE_DEPENDENCY {name}: {match.group(0)}")

for hardcoded in [
    "sensor.pv_prognose_leistung_jetzt_biased_interpoliert",
    "sensor.evcc_forecast_solar",
]:
    if hardcoded in package_text:
        errors.append(f"HARD_CODED_FALLBACK {hardcoded}")

helper_domains = {
    "input_boolean", "input_datetime", "input_number",
    "input_select", "input_text", "counter", "timer",
}
helper_defs: dict[str, list[str]] = defaultdict(list)
automation_ids: list[str] = []

for path in package_files:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    current_domain = None
    for line in lines:
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

for entity_id, files in sorted(helper_defs.items()):
    if len(files) > 1:
        errors.append(f"DUPLICATE_HELPER {entity_id}: {','.join(files)}")

for value, count in Counter(automation_ids).items():
    if count > 1:
        errors.append(f"DUPLICATE_AUTOMATION_ID {value}")

# Every site_config key must be handled by apply_site_config.py.
env_keys = set()
env_path = root / "config/site_config.env.example"
for raw in env_path.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if line and not line.startswith("#") and "=" in line:
        env_keys.add(line.split("=", 1)[0].strip())

apply_path = root / "scripts/apply_site_config.py"
tree = ast.parse(apply_path.read_text(encoding="utf-8"))
handled = {"SITE_CONFIG_CONFIRMED"}
for node in tree.body:
    if isinstance(node, ast.Assign):
        names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        if any(name in {"TEXT_MAP", "NUMBER_MAP", "BOOLEAN_MAP"} for name in names):
            value = ast.literal_eval(node.value)
            handled.update(value.keys())

for key in sorted(env_keys - handled):
    errors.append(f"UNAPPLIED_SITE_CONFIG_KEY {key}")

# Master/write gate checks.
for writer in [
    "se_controller_80_charge_writer.yaml",
    "se_controller_82_discharge_writer.yaml",
    "se_controller_83_storage_control_writer.yaml",
    "se_controller_84_command_mode_writer.yaml",
]:
    text = (root / "package" / writer).read_text(encoding="utf-8")
    if "binary_sensor.se_nf_controller_write_enabled" not in text:
        errors.append(f"WRITER_WITHOUT_GATE {writer}")

# No private config in release tree.
for private in [
    "config/site_config.env",
    "config/private_migration_values.env",
]:
    if (root / private).exists():
        errors.append(f"PRIVATE_FILE {private}")

passed = not errors and (not args.release_gate or not warnings)
report = {
    "errors": errors,
    "warnings": warnings,
    "release_gate": args.release_gate,
    "package_yaml_files": len(package_files),
    "helper_definitions": len(helper_defs),
    "automation_ids": len(automation_ids),
    "pass": passed,
}
print(json.dumps(report, indent=2, ensure_ascii=False))
sys.exit(0 if passed else 2)
