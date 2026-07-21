#!/usr/bin/env python3
"""Finaler kontrollierter Charge-Writer-Rundlauf für RC2.

Der Test verändert ausschließlich:
- input_boolean.se_netzdienlich_enabled
- input_select.se_nf_optimization_mode
- das gemappte SolarEdge-Charge-Limit über den Controller-Writer

Bei einem Fehler wird der ursprüngliche Charge-Limit-Wert direkt wiederhergestellt,
der Master ausgeschaltet und der ursprüngliche Modus zurückgesetzt.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

VERSION = "1.0.0"
MASTER = "input_boolean.se_netzdienlich_enabled"
MODE = "input_select.se_nf_optimization_mode"
WRITE_ENABLED = "binary_sensor.se_nf_controller_write_enabled"
SITE_CONFIRMED = "input_boolean.se_nf_site_config_confirmed"
CONFIG_CHECK = "sensor.se_nf_config_check"
SANITY_CHECK = "sensor.se_nf_sanity_check"
RISK_FLAG = "binary_sensor.se_nf_risk_flag"
DESIRED = "sensor.se_nf_desired_target"
ACTUAL = "sensor.se_nf_charge_limit_actual"
WRITER_MODE = "sensor.se_nf_writer_mode"
WRITER_DECISION = "sensor.se_nf_writer_last_decision"
LAST_WRITE = "input_datetime.se_nf_last_write"
LAST_APPLIED = "input_number.se_nf_last_applied_charge_limit_w"
CHARGE_MAPPING = "input_text.se_nf_charge_limit_entity"
SESSION = "input_select.se_nf_session_state"
ORIGINAL_OPEN_MODE = "Eigenverbrauch maximieren"


class TestFailure(RuntimeError):
    pass


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@dataclass
class HAClient:
    api_url: str
    token: str
    timeout: int = 30

    def request(self, path: str, method: str = "GET", payload: dict[str, Any] | None = None) -> Any:
        body = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.api_url.rstrip("/") + path,
            method=method,
            data=body,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise TestFailure(f"Home-Assistant-API HTTP {exc.code}: {detail}") from exc
        except OSError as exc:
            raise TestFailure(f"Home-Assistant-API nicht erreichbar: {exc}") from exc
        return json.loads(raw.decode("utf-8")) if raw else None

    def states(self) -> dict[str, dict[str, Any]]:
        payload = self.request("/states") or []
        return {
            item["entity_id"]: item
            for item in payload
            if isinstance(item, dict) and item.get("entity_id")
        }

    def state(self, entity_id: str, index: dict[str, dict[str, Any]] | None = None) -> str | None:
        data = index if index is not None else self.states()
        item = data.get(entity_id)
        return None if item is None else str(item.get("state", ""))

    def service(self, domain: str, action: str, payload: dict[str, Any]) -> None:
        self.request(f"/services/{domain}/{action}", "POST", payload)

    def master(self, enabled: bool) -> None:
        self.service("input_boolean", "turn_on" if enabled else "turn_off", {"entity_id": MASTER})

    def select_mode(self, option: str) -> None:
        self.service("input_select", "select_option", {"entity_id": MODE, "option": option})

    def set_number(self, entity_id: str, value: float) -> None:
        self.service("number", "set_value", {"entity_id": entity_id, "value": round(value)})


class Logger:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def __call__(self, message: str) -> None:
        line = f"[{datetime.now().strftime('%H:%M:%S')}] {message}"
        print(line, flush=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")


def snapshot(client: HAClient) -> dict[str, Any]:
    index = client.states()
    entities = [
        MASTER, MODE, WRITE_ENABLED, SITE_CONFIRMED, CONFIG_CHECK, SANITY_CHECK,
        RISK_FLAG, DESIRED, ACTUAL, WRITER_MODE, WRITER_DECISION, LAST_WRITE,
        LAST_APPLIED, CHARGE_MAPPING, SESSION,
    ]
    result: dict[str, Any] = {}
    for entity_id in entities:
        item = index.get(entity_id)
        result[entity_id] = None if item is None else {
            "state": item.get("state"),
            "last_changed": item.get("last_changed"),
            "last_updated": item.get("last_updated"),
            "attributes": item.get("attributes") or {},
        }
    target = (client.state(CHARGE_MAPPING, index) or "").strip()
    result["charge_target_entity"] = target
    target_item = index.get(target) if target else None
    result["charge_target"] = None if target_item is None else {
        "state": target_item.get("state"),
        "last_changed": target_item.get("last_changed"),
        "last_updated": target_item.get("last_updated"),
        "attributes": target_item.get("attributes") or {},
    }
    return result


def s(data: dict[str, Any], entity_id: str) -> str | None:
    item = data.get(entity_id)
    return None if item is None else str(item.get("state", ""))


def wait_for(
    client: HAClient,
    predicate: Callable[[dict[str, Any]], bool],
    timeout: int,
    interval: float,
    label: str,
    log: Logger,
    samples: list[dict[str, Any]],
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    last: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last = snapshot(client)
        sample = {
            "phase": label,
            "time": datetime.now(timezone.utc).isoformat(),
            "master": s(last, MASTER),
            "mode": s(last, MODE),
            "session": s(last, SESSION),
            "write_enabled": s(last, WRITE_ENABLED),
            "config": s(last, CONFIG_CHECK),
            "sanity": s(last, SANITY_CHECK),
            "risk": s(last, RISK_FLAG),
            "desired": num(s(last, DESIRED)),
            "actual": num(s(last, ACTUAL)),
            "writer_mode": s(last, WRITER_MODE),
            "writer_decision": s(last, WRITER_DECISION),
            "last_write": s(last, LAST_WRITE),
            "last_applied": num(s(last, LAST_APPLIED)),
            "charge_target_entity": last.get("charge_target_entity"),
            "charge_target_state": num((last.get("charge_target") or {}).get("state")),
        }
        samples.append(sample)
        log(
            f"{label}: master={sample['master']} mode={sample['mode']} "
            f"session={sample['session']} write={sample['write_enabled']} "
            f"target={sample['desired']} actual={sample['actual']} "
            f"writer={sample['writer_mode']}"
        )
        if predicate(last):
            return last
        time.sleep(interval)
    raise TestFailure(f"Zeitüberschreitung bei: {label}")


def run_command(command: list[str], log: Logger) -> None:
    result = subprocess.run(command, text=True, capture_output=True)
    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            log(line)
    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            log(line)
    if result.returncode != 0:
        raise TestFailure(f"Befehl fehlgeschlagen ({result.returncode}): {' '.join(command)}")


def validate_baseline(data: dict[str, Any]) -> tuple[str, str, float]:
    required = {
        SITE_CONFIRMED: "on",
        CONFIG_CHECK: "ok",
        SANITY_CHECK: "ok",
        RISK_FLAG: "off",
    }
    errors = [f"{entity}={s(data, entity)!r}, erwartet {expected!r}" for entity, expected in required.items() if s(data, entity) != expected]
    target_entity = str(data.get("charge_target_entity") or "").strip()
    if not target_entity.startswith("number."):
        errors.append(f"Charge-Limit-Mapping ungültig: {target_entity!r}")
    desired = num(s(data, DESIRED))
    actual = num(s(data, ACTUAL))
    target_state = num((data.get("charge_target") or {}).get("state"))
    if desired is None or not 0 <= desired <= 50:
        errors.append(f"Ausgangs-Soll muss 0 W sein, ist {desired!r}")
    if actual is None or not 0 <= actual <= 50:
        errors.append(f"Ausgangs-Ist muss 0 W sein, ist {actual!r}")
    if target_state is None or not 0 <= target_state <= 50:
        errors.append(f"Gemappter SolarEdge-Wert muss 0 W sein, ist {target_state!r}")
    original_mode = s(data, MODE)
    if not original_mode or original_mode in {"unknown", "unavailable"}:
        errors.append(f"Ursprünglicher Modus ungültig: {original_mode!r}")
    original_master = s(data, MASTER)
    if original_master not in {"on", "off"}:
        errors.append(f"Masterzustand ungültig: {original_master!r}")
    if errors:
        raise TestFailure("Baseline nicht sicher:\n- " + "\n- ".join(errors))
    assert original_mode is not None and original_master is not None and actual is not None
    return original_mode, original_master, actual


def main() -> int:
    parser = argparse.ArgumentParser(description="Finaler RC2-Charge-Writer-Rundlauf")
    parser.add_argument("--check", action="store_true", help="Nur Voraussetzungen prüfen, nichts verändern")
    parser.add_argument("--run", action="store_true", help="Kontrollierten 0→5000→0-Rundlauf ausführen")
    parser.add_argument("--api-url", default=os.getenv("HA_API_URL", "http://supervisor/core/api"))
    parser.add_argument("--config-root", default=os.getenv("CONFIG_ROOT", "/config"))
    parser.add_argument("--share-root", default=os.getenv("SHARE_ROOT", "/share"))
    parser.add_argument("--open-timeout", type=int, default=90)
    parser.add_argument("--close-timeout", type=int, default=120)
    parser.add_argument("--interval", type=float, default=3.0)
    args = parser.parse_args()
    if args.check == args.run:
        parser.error("Genau eine Option erforderlich: --check oder --run")

    token = os.getenv("SUPERVISOR_TOKEN", "")
    if not token:
        print("FEHLER: SUPERVISOR_TOKEN fehlt", file=sys.stderr)
        return 2

    stamp = utc_stamp()
    share = Path(args.share_root)
    log_path = share / f"se_controller_writer_roundtrip_{stamp}.log"
    report_path = share / f"se_controller_writer_roundtrip_{stamp}.json"
    runtime_path = share / f"se_controller_writer_roundtrip_runtime_{stamp}.json"
    log = Logger(log_path)
    client = HAClient(args.api_url, token)
    samples: list[dict[str, Any]] = []
    original_mode = ""
    original_master = "off"
    baseline_actual = 0.0
    charge_entity = ""
    open_confirmed = False

    report: dict[str, Any] = {
        "version": VERSION,
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "check" if args.check else "run",
        "pass": False,
        "emergency_restore_used": False,
        "samples": samples,
    }

    try:
        log(f"SolarEdge HA Energy Controller RC2 – finaler Writer-Test {VERSION}")
        log("Prüfe Home-Assistant-Konfiguration.")
        run_command(["ha", "core", "check"], log)

        checker = Path(args.config_root) / "se_controller_runtime_checker.py"
        if not checker.is_file():
            raise TestFailure(f"Runtime-Checker fehlt: {checker}")
        run_command([sys.executable, str(checker), "--report", str(runtime_path)], log)

        before = snapshot(client)
        original_mode, original_master, baseline_actual = validate_baseline(before)
        charge_entity = str(before.get("charge_target_entity") or "")
        report.update({
            "original_mode": original_mode,
            "original_master": original_master,
            "baseline_actual_w": baseline_actual,
            "charge_entity": charge_entity,
            "before": before,
        })
        log(
            f"Baseline PASS: Master={original_master}, Modus={original_mode}, "
            f"Charge-Limit={baseline_actual:.0f} W, Ziel={charge_entity}"
        )

        if args.check:
            report["pass"] = True
            report["result"] = "CHECK=PASS; keine Zustände verändert"
            log("CHECK=PASS · Es wurde nichts verändert.")
            return 0

        # Deterministischer Start: erst Master aus und Writer-Gate wirklich gesperrt.
        log("Phase 1: Master AUS und Writer-Sperre bestätigen.")
        client.master(False)
        wait_for(
            client,
            lambda d: s(d, MASTER) == "off" and s(d, WRITE_ENABLED) == "off",
            30, args.interval, "MASTER_OFF", log, samples,
        )

        log(f"Phase 2: Testmodus {ORIGINAL_OPEN_MODE!r} bei gesperrtem Writer setzen.")
        client.select_mode(ORIGINAL_OPEN_MODE)
        wait_for(
            client,
            lambda d: s(d, MODE) == ORIGINAL_OPEN_MODE and s(d, WRITE_ENABLED) == "off",
            30, args.interval, "MODE_PREPARED", log, samples,
        )

        last_write_before = s(snapshot(client), LAST_WRITE)
        log("Phase 3: Master AN – Controller muss 5000 W über den Charge-Writer setzen.")
        client.master(True)
        opened = wait_for(
            client,
            lambda d: (
                s(d, MASTER) == "on"
                and s(d, WRITE_ENABLED) == "on"
                and (num(s(d, DESIRED)) or -1) >= 4750
                and (num(s(d, ACTUAL)) or -1) >= 4750
                and (num((d.get("charge_target") or {}).get("state")) or -1) >= 4750
                and s(d, LAST_WRITE) != last_write_before
            ),
            args.open_timeout, args.interval, "OPEN_WRITE", log, samples,
        )
        open_confirmed = True
        report["open_write"] = opened
        log("OPEN_WRITE=PASS · echter Controller-Write auf 5000 W bestätigt.")

        log(f"Phase 4: Ursprünglichen Modus {original_mode!r} wiederherstellen.")
        client.select_mode(original_mode)
        closed = wait_for(
            client,
            lambda d: (
                s(d, MODE) == original_mode
                and (num(s(d, DESIRED)) is not None and num(s(d, DESIRED)) <= 50)
                and (num(s(d, ACTUAL)) is not None and num(s(d, ACTUAL)) <= 50)
                and (num((d.get("charge_target") or {}).get("state")) is not None and num((d.get("charge_target") or {}).get("state")) <= 50)
            ),
            args.close_timeout, args.interval, "CLOSE_WRITE", log, samples,
        )
        report["close_write"] = closed
        log("CLOSE_WRITE=PASS · echter Controller-Write zurück auf 0 W bestätigt.")

        if original_master == "off":
            log("Phase 5: ursprünglichen Masterzustand AUS wiederherstellen.")
            client.master(False)
            wait_for(
                client,
                lambda d: s(d, MASTER) == "off" and s(d, WRITE_ENABLED) == "off",
                30, args.interval, "RESTORE_MASTER_OFF", log, samples,
            )
        else:
            log("Phase 5: ursprünglicher Masterzustand war AN und bleibt AN.")

        final = snapshot(client)
        final_actual = num(s(final, ACTUAL))
        if s(final, MODE) != original_mode:
            raise TestFailure(f"Abschlussmodus nicht wiederhergestellt: {s(final, MODE)!r}")
        if final_actual is None or final_actual > 50:
            raise TestFailure(f"Abschluss-Charge-Limit nicht sicher geschlossen: {final_actual!r}")
        if s(final, CONFIG_CHECK) != "ok" or s(final, SANITY_CHECK) != "ok" or s(final, RISK_FLAG) != "off":
            raise TestFailure("Abschlussprüfung von Config/Sanity/Risk fehlgeschlagen")
        if s(final, MASTER) != original_master:
            raise TestFailure(f"Master nicht auf Ausgangszustand: {s(final, MASTER)!r} statt {original_master!r}")

        report.update({
            "pass": True,
            "result": "WRITER_ROUNDTRIP=PASS",
            "open_confirmed": open_confirmed,
            "close_confirmed": True,
            "final": final,
            "finished_utc": datetime.now(timezone.utc).isoformat(),
        })
        log("WRITER_ROUNDTRIP=PASS")
        log(f"Ausgangsmodus wiederhergestellt: {original_mode}")
        log(f"Master wiederhergestellt: {original_master.upper()}")
        log("Charge-Limit wiederhergestellt: 0 W")
        return 0

    except Exception as exc:
        log(f"FEHLER: {exc}")
        report["error"] = str(exc)
        report["open_confirmed"] = open_confirmed
        report["emergency_restore_used"] = True
        # Emergency restore: zuerst Writer sperren, dann bekannten Ausgangswert setzen.
        try:
            client.master(False)
            log("Controller-Master aus Sicherheitsgründen AUS.")
        except Exception as restore_exc:
            log(f"WARNUNG: Master konnte nicht ausgeschaltet werden: {restore_exc}")
            report["emergency_master_off_error"] = str(restore_exc)
        try:
            if charge_entity.startswith("number."):
                log(f"Notfall-Rückstellung: {charge_entity} direkt auf {baseline_actual:.0f} W.")
                client.set_number(charge_entity, baseline_actual)
        except Exception as restore_exc:
            log(f"WARNUNG: Direkte Charge-Limit-Rückstellung fehlgeschlagen: {restore_exc}")
            report["emergency_charge_restore_error"] = str(restore_exc)
        try:
            if original_mode:
                client.select_mode(original_mode)
                log(f"Ursprünglicher Modus wiederhergestellt: {original_mode}")
        except Exception as restore_exc:
            log(f"WARNUNG: Modus-Rückstellung fehlgeschlagen: {restore_exc}")
            report["emergency_mode_restore_error"] = str(restore_exc)
        try:
            report["final_after_error"] = snapshot(client)
        except Exception as snap_exc:
            report["final_snapshot_error"] = str(snap_exc)
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        return 2

    finally:
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            log(f"Bericht: {report_path}")
            log(f"Log: {log_path}")
        except Exception as write_exc:
            print(f"FEHLER beim Schreiben des Berichts: {write_exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
