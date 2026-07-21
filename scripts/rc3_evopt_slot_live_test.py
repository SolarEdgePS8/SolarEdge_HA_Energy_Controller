#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

API = os.environ.get("HA_API_URL", "http://supervisor/core/api").rstrip("/")
TOKEN = os.environ.get("SUPERVISOR_TOKEN", "").strip()


def fetch_states() -> dict[str, dict[str, Any]]:
    if not TOKEN:
        raise RuntimeError("SUPERVISOR_TOKEN fehlt")
    request = urllib.request.Request(
        API + "/states",
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    return {
        item["entity_id"]: item
        for item in data
        if isinstance(item, dict) and item.get("entity_id")
    }


def state(states: dict[str, dict[str, Any]], entity_id: str) -> str:
    return str(states.get(entity_id, {}).get("state", "missing"))


def attributes(states: dict[str, dict[str, Any]], entity_id: str) -> dict[str, Any]:
    value = states.get(entity_id, {}).get("attributes")
    return value if isinstance(value, dict) else {}


def integer(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only RC3 EVOpt live test. Counts real slot-index advances within "
            "one optimizer plan and separates them from solver replans."
        )
    )
    parser.add_argument("--minutes", type=float, default=50.0)
    parser.add_argument("--interval", type=float, default=10.0)
    parser.add_argument("--grace-seconds", type=float, default=180.0)
    parser.add_argument("--minimum-slot-advances", type=int, default=2)
    parser.add_argument(
        "--report",
        default="/share/rc3_evopt_slot_live_test_report.json",
    )
    args = parser.parse_args()

    started = time.monotonic()
    deadline = started + max(1.0, args.minutes * 60.0)
    grace_deadline = started + max(0.0, args.grace_seconds)

    samples: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    slot_advance_events: list[dict[str, Any]] = []
    replan_events: list[dict[str, Any]] = []
    fallback_samples = 0
    api_errors = 0

    previous_plan_updated: str | None = None
    previous_slot_index: int | None = None

    print(
        f"RC3 EVOpt Live-Test: {args.minutes:.1f} min, "
        f"Intervall {args.interval:.1f} s, read-only"
    )

    while time.monotonic() < deadline:
        now_mono = time.monotonic()
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            states = fetch_states()
            raw = attributes(states, "sensor.se_nf_evopt_adapter_raw")
            status_attrs = attributes(states, "sensor.se_nf_evopt_status")

            plan_updated = str(raw.get("updated") or "")
            slot_index = integer(raw.get("slot_index"))

            if (
                previous_plan_updated is not None
                and plan_updated
                and plan_updated != previous_plan_updated
            ):
                event = {
                    "timestamp": timestamp,
                    "previous_plan_updated": previous_plan_updated,
                    "plan_updated": plan_updated,
                    "slot_index": slot_index,
                    "slot_start": raw.get("slot_start"),
                }
                replan_events.append(event)
                print(
                    "\nREPLAN: "
                    f"{previous_plan_updated} -> {plan_updated}, index={slot_index}"
                )

            if (
                previous_plan_updated is not None
                and plan_updated == previous_plan_updated
                and previous_slot_index is not None
                and slot_index is not None
                and slot_index > previous_slot_index
            ):
                event = {
                    "timestamp": timestamp,
                    "plan_updated": plan_updated,
                    "from_index": previous_slot_index,
                    "to_index": slot_index,
                    "slot_start": raw.get("slot_start"),
                    "slot_end": raw.get("slot_end"),
                    "action_raw": raw.get("action_raw"),
                    "action_source": raw.get("action_source"),
                    "suggestion_action": raw.get("suggestion_action"),
                    "slot_action": raw.get("slot_action"),
                    "suggestion_overridden": raw.get("suggestion_overridden"),
                }
                slot_advance_events.append(event)
                print(
                    "\nSLOT-ADVANCE "
                    f"{len(slot_advance_events)}: "
                    f"index {previous_slot_index} -> {slot_index}, "
                    f"start={raw.get('slot_start')}"
                )

            sample = {
                "timestamp": timestamp,
                "master": state(states, "input_boolean.se_netzdienlich_enabled"),
                "site_confirmed": state(states, "input_boolean.se_nf_site_config_confirmed"),
                "evopt_enabled": state(states, "input_boolean.se_nf_evopt_shadow_enabled"),
                "mode": state(states, "input_select.se_nf_optimization_mode"),
                "config": state(states, "sensor.se_nf_config_check"),
                "sanity": state(states, "sensor.se_nf_sanity_check"),
                "status": state(states, "sensor.se_nf_evopt_status"),
                "reason": status_attrs.get("reason"),
                "active_control": state(states, "binary_sensor.se_nf_evopt_active_control"),
                "fallback_active": state(states, "binary_sensor.se_nf_evopt_fallback_active"),
                "fallback_code": state(states, "sensor.se_nf_evopt_fallback_code"),
                "active_label": state(states, "sensor.se_nf_active_control_label"),
                "desired_target": state(states, "sensor.se_nf_desired_target"),
                "actual_target": state(states, "sensor.se_nf_charge_limit_actual"),
                "plan_updated": plan_updated,
                "slot_index": slot_index,
                "slot_start": raw.get("slot_start"),
                "slot_end": raw.get("slot_end"),
                "action_raw": raw.get("action_raw"),
                "action_source": raw.get("action_source"),
                "suggestion_action": raw.get("suggestion_action"),
                "slot_action": raw.get("slot_action"),
                "suggestion_overridden": raw.get("suggestion_overridden"),
                "suggestion_plan_consistent": raw.get("suggestion_plan_consistent"),
                "action_plan_consistent": raw.get("action_plan_consistent"),
                "plan_consistent": raw.get("plan_consistent"),
                "data_healthy": raw.get("data_healthy"),
                "health_reason": raw.get("health_reason"),
            }
            samples.append(sample)

            sample_errors: list[str] = []
            for key, expected in [
                ("master", "on"),
                ("site_confirmed", "on"),
                ("evopt_enabled", "on"),
                ("mode", "EVOpt optimiert"),
                ("config", "ok"),
                ("sanity", "ok"),
            ]:
                if sample[key] != expected:
                    sample_errors.append(
                        f"{key}={sample[key]!r}, erwartet {expected!r}"
                    )

            if now_mono >= grace_deadline:
                if sample["status"] != "healthy":
                    sample_errors.append(f"status={sample['status']!r}")
                if sample["reason"] != "ok":
                    sample_errors.append(f"reason={sample['reason']!r}")
                if sample["active_control"] != "on":
                    sample_errors.append(
                        f"active_control={sample['active_control']!r}"
                    )
                if sample["fallback_active"] == "on":
                    fallback_samples += 1
                    sample_errors.append(
                        "fallback_active=on, "
                        f"code={sample['fallback_code']!r}"
                    )
                for key in (
                    "data_healthy",
                    "suggestion_plan_consistent",
                    "action_plan_consistent",
                    "plan_consistent",
                ):
                    if sample[key] is not True:
                        sample_errors.append(f"{key}={sample[key]!r}")

            if sample_errors:
                event = {
                    "timestamp": timestamp,
                    "plan_updated": plan_updated,
                    "slot_index": slot_index,
                    "errors": sample_errors,
                }
                errors.append(event)
                print("FEHLER:", "; ".join(sample_errors))
            else:
                print(
                    f"{datetime.now().strftime('%H:%M:%S')} "
                    f"status={sample['status']} "
                    f"active={sample['active_control']} "
                    f"index={slot_index} "
                    f"action={sample['action_raw']} "
                    f"soll/ist={sample['desired_target']}/{sample['actual_target']}"
                )

            previous_plan_updated = plan_updated or previous_plan_updated
            previous_slot_index = slot_index

        except Exception as exc:
            api_errors += 1
            errors.append({
                "timestamp": timestamp,
                "errors": [f"API: {exc!r}"],
            })
            print("API-FEHLER:", repr(exc))

        sleep_for = min(
            max(1.0, args.interval),
            max(0.0, deadline - time.monotonic()),
        )
        if sleep_for:
            time.sleep(sleep_for)

    if len(slot_advance_events) < max(1, args.minimum_slot_advances):
        errors.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "errors": [
                f"Nur {len(slot_advance_events)} echte Slot-Index-Fortschaltungen "
                f"beobachtet; mindestens {args.minimum_slot_advances} erforderlich"
            ],
        })

    report = {
        "project": "SolarEdge_HA_Energy_Controller",
        "test": "RC3 EVOpt real slot-index transition live test",
        "read_only": True,
        "duration_minutes": args.minutes,
        "interval_seconds": args.interval,
        "grace_seconds": args.grace_seconds,
        "minimum_slot_advances": args.minimum_slot_advances,
        "samples": len(samples),
        "slot_advance_events": slot_advance_events,
        "slot_advances": len(slot_advance_events),
        "replan_events": replan_events,
        "replans": len(replan_events),
        "fallback_samples_after_grace": fallback_samples,
        "api_errors": api_errors,
        "errors": errors,
        "warnings": warnings,
        "pass": not errors,
        "last_sample": samples[-1] if samples else None,
        "all_samples": samples,
    }

    path = Path(args.report)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print("\n" + json.dumps({
        "samples": report["samples"],
        "slot_advances": report["slot_advances"],
        "replans": report["replans"],
        "fallback_samples_after_grace": fallback_samples,
        "api_errors": api_errors,
        "errors": len(errors),
        "pass": report["pass"],
        "report": str(path),
    }, indent=2, ensure_ascii=False))

    return 0 if report["pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
