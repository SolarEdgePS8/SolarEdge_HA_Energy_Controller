#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

VERSION = "0.1.0-rc.4"
CONFIG_ROOT = Path(os.environ.get("CONFIG_ROOT", "/config"))
MANIFEST = CONFIG_ROOT / ".se_controller_runtime_manifest.json"
SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "").strip()
HA_TOKEN = os.environ.get("HA_TOKEN", "").strip()
TOKEN = SUPERVISOR_TOKEN or HA_TOKEN
DEFAULT_API = "http://supervisor/core/api" if SUPERVISOR_TOKEN else "http://127.0.0.1:8123/api"
API = os.environ.get("HA_API_URL", DEFAULT_API).rstrip("/")


class HomeAssistant:
    def get(self, path: str) -> Any:
        if not TOKEN:
            raise RuntimeError(
                "Kein Home-Assistant-API-Token verfügbar. "
                "HA OS/Supervised: Terminal-Add-on verwenden. "
                "Container/Core: HA_TOKEN und optional HA_API_URL setzen."
            )
        req = urllib.request.Request(
            API + path,
            method="GET",
            headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                raw = response.read()
                return json.loads(raw.decode("utf-8")) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} {path}: {detail}") from exc

    def states(self) -> dict[str, dict[str, Any]]:
        data = self.get("/states") or []
        return {item["entity_id"]: item for item in data if isinstance(item, dict) and item.get("entity_id")}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def configured(value: Any) -> bool:
    return str(value or "").strip() not in {"", "unknown", "unavailable", "none", "None"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-master-off", action="store_true")
    parser.add_argument("--allow-unconfirmed", action="store_true")
    parser.add_argument("--wait-seconds", type=int, default=180)
    parser.add_argument("--report", default="/share/se_controller_runtime_check.json")
    args = parser.parse_args()

    report: dict[str, Any] = {
        "project": "SolarEdge_HA_Energy_Controller",
        "version": VERSION,
        "started_at": time.time(),
        "checks": [],
        "errors": [],
        "warnings": [],
    }

    def check(name: str, passed: bool, detail: Any, *, warning: bool = False) -> None:
        report["checks"].append({"name": name, "passed": bool(passed), "detail": detail, "warning": warning})
        if not passed:
            (report["warnings"] if warning else report["errors"]).append(f"{name}: {detail}")
        print(f"[{'OK' if passed else ('WARN' if warning else 'FEHLER')}] {name}: {detail}")

    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        check("Runtime-Manifest Version", manifest.get("version") == VERSION, manifest.get("version"))
        hash_errors = []
        installed = manifest.get("installed_files") or {}
        for rel, expected in installed.items():
            path = CONFIG_ROOT / rel
            if not path.is_file():
                hash_errors.append({"file": rel, "error": "missing"})
            else:
                actual = sha256(path)
                if actual != expected:
                    hash_errors.append({"file": rel, "expected": expected, "actual": actual})
        check("Installierte Dateien unverändert", not hash_errors, {"checked": len(installed), "errors": hash_errors})

        ha = HomeAssistant()
        states = ha.states()

        required = [
            "input_boolean.se_netzdienlich_enabled",
            "input_boolean.se_nf_site_config_confirmed",
            "sensor.se_nf_config_check",
            "sensor.se_nf_sanity_check",
            "binary_sensor.se_nf_controller_write_enabled",
            "sensor.se_nf_start_gate_reason",
            "sensor.se_nf_desired_target",
            "sensor.se_nf_charge_limit_actual",
        ]
        missing = [entity for entity in required if entity not in states]
        check("Pflichtentitäten vorhanden", not missing, missing or "vollständig")

        if not missing:
            deadline = time.monotonic() + max(0, args.wait_seconds)
            while time.monotonic() < deadline:
                states = ha.states()
                cfg = states.get("sensor.se_nf_config_check", {}).get("state")
                sanity = states.get("sensor.se_nf_sanity_check", {}).get("state")
                confirmed = states.get("input_boolean.se_nf_site_config_confirmed", {}).get("state")
                if cfg == "ok" and sanity == "ok" and (confirmed == "on" or args.allow_unconfirmed):
                    break
                time.sleep(5)

            states = ha.states()
            master = states["input_boolean.se_netzdienlich_enabled"]["state"]
            confirmed = states["input_boolean.se_nf_site_config_confirmed"]["state"]
            cfg = states["sensor.se_nf_config_check"]["state"]
            sanity = states["sensor.se_nf_sanity_check"]["state"]
            write_enabled = states["binary_sensor.se_nf_controller_write_enabled"]["state"]
            start_reason = str(states["sensor.se_nf_start_gate_reason"]["state"])

            if args.expect_master_off:
                check("Controller-Master AUS", master == "off", master)
                check("Writer gesperrt", write_enabled == "off", write_enabled)
            else:
                check("Controller-Master gültig", master in {"on", "off"}, master)
            if not args.allow_unconfirmed:
                check("Standortkonfiguration bestätigt", confirmed == "on", confirmed)
            check("Config Check", cfg == "ok", cfg)
            check("Sanity Check", sanity == "ok", sanity)
            check("Start-Gate-State <=255 Zeichen", len(start_reason) <= 255, len(start_reason))

        mapping_entities = [
            "input_text.se_nf_charge_limit_entity",
            "input_text.se_nf_discharge_limit_entity",
            "input_text.se_nf_command_mode_entity",
            "input_text.se_nf_storage_control_mode_entity",
            "input_text.se_nf_battery_soe_entity",
            "input_text.se_nf_battery_capacity_entity",
            "input_text.se_nf_pv_today_remaining_entity",
            "input_text.se_nf_pv_today_total_entity",
            "input_text.se_nf_pv_tomorrow_entity",
        ]
        mapping_errors = []
        mapping_detail = {}
        for helper in mapping_entities:
            item = states.get(helper)
            if not item:
                mapping_errors.append({"helper": helper, "error": "missing"})
                continue
            target = str(item.get("state", "")).strip()
            mapping_detail[helper] = target
            if configured(target) and target not in states:
                mapping_errors.append({"helper": helper, "target": target, "error": "target_missing"})
        check("Konfigurierte Mapping-Ziele vorhanden", not mapping_errors, mapping_errors or mapping_detail)

        evopt_enabled = states.get("input_boolean.se_nf_evopt_shadow_enabled", {}).get("state") == "on"
        if evopt_enabled:
            adapter = states.get("sensor.se_nf_evopt_adapter_raw")
            check("EVOpt-Adapter vorhanden", adapter is not None, "enabled", warning=True)
            if adapter is not None:
                attrs = adapter.get("attributes") or {}
                check("EVOpt-Datenstatus verfügbar", "data_healthy" in attrs, attrs.get("health_reason"), warning=True)

    except Exception as exc:
        report["errors"].append(str(exc))
        print(f"[FEHLER] {exc}")

    report["finished_at"] = time.time()
    report["pass"] = not report["errors"]
    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"FEHLER={len(report['errors'])} WARNUNGEN={len(report['warnings'])} PASS={report['pass']} Bericht={path}")
    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
