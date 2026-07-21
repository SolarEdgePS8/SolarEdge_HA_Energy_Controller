#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import urllib.request
from pathlib import Path
from typing import Any

API = os.environ.get("HA_API_URL", "http://supervisor/core/api").rstrip("/")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "").strip()

MAPPING_HELPERS = {
    "charge_limit": "input_text.se_nf_charge_limit_entity",
    "discharge_limit": "input_text.se_nf_discharge_limit_entity",
    "command_mode": "input_text.se_nf_command_mode_entity",
    "storage_control": "input_text.se_nf_storage_control_mode_entity",
}
PATTERNS = {
    "charge_limit": re.compile(r"storage_charge_limit|se_nf_charge_limit_entity", re.I),
    "discharge_limit": re.compile(r"storage_discharge_limit|se_nf_discharge_limit_entity", re.I),
    "command_mode": re.compile(r"storage_command_mode|se_nf_command_mode_entity", re.I),
    "storage_control": re.compile(r"storage_control_mode|se_nf_storage_control_mode_entity|se_akku_remote_control", re.I),
}
WRITE_SERVICE = re.compile(
    r"number\.set_value|select\.select_option|switch\.turn_on|switch\.turn_off|modbus\.write_register",
    re.I,
)
EXCLUDED = {".storage", ".git", "backups", "backup", "archive", "custom_components", "www", "ssl"}


def api_states() -> dict[str, dict[str, Any]]:
    if not TOKEN:
        return {}
    req = urllib.request.Request(
        API + "/states",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        data = json.loads(response.read().decode("utf-8"))
    return {item["entity_id"]: item for item in data if item.get("entity_id")}


def configured(value: Any) -> bool:
    return str(value or "").strip() not in {"", "unknown", "unavailable", "none", "None"}


parser = argparse.ArgumentParser()
parser.add_argument("config", nargs="?", default="/config")
args = parser.parse_args()
config = Path(args.config)
project_names = {
    p.name for p in (Path(__file__).resolve().parents[1] / "package").glob("*.yaml")
}
states = api_states()
mapped = {
    target: str(states.get(helper, {}).get("state", "")).strip()
    for target, helper in MAPPING_HELPERS.items()
}

hits = []
ignored = []
for path in config.rglob("*.yaml"):
    if path.name in project_names:
        continue
    try:
        rel = path.relative_to(config)
    except ValueError:
        continue
    if any(part in EXCLUDED for part in rel.parts):
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    for index, line in enumerate(lines):
        targets = [name for name, pattern in PATTERNS.items() if pattern.search(line)]
        if not targets:
            continue
        start = max(0, index - 12)
        end = min(len(lines), index + 13)
        context = "\n".join(lines[start:end])
        if not WRITE_SERVICE.search(context):
            continue
        item = {"file": str(rel), "line": index + 1, "targets": targets}
        blocking = [name for name in targets if configured(mapped.get(name))]
        if blocking:
            item["blocking_targets"] = blocking
            hits.append(item)
        else:
            ignored.append(item)

result = {"mapped_targets": mapped, "conflicts": hits, "ignored_unmapped": ignored, "pass": not hits}
print(json.dumps(result, indent=2, ensure_ascii=False))
raise SystemExit(0 if not hits else 2)
