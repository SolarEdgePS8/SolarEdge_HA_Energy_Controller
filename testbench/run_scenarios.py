#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import fields
import json
from pathlib import Path
from typing import Any

import yaml

from testbench.reference.controller_model import ControllerInput, EvoptAction, Mode, decide


INPUT_FIELDS = {item.name for item in fields(ControllerInput)}


def build_input(case: dict[str, Any]) -> ControllerInput:
    raw = dict(case.get("input") or {})
    unknown = set(raw) - INPUT_FIELDS
    if unknown:
        raise ValueError(f"{case['id']}: unknown fields {sorted(unknown)}")
    raw["mode"] = Mode(str(case["mode"]))
    if "evopt_action" in raw:
        raw["evopt_action"] = EvoptAction(str(raw["evopt_action"]))
    return ControllerInput(**raw)


def run(path: Path) -> dict[str, Any]:
    scenarios = yaml.safe_load(path.read_text(encoding="utf-8"))["scenarios"]
    results: list[dict[str, Any]] = []
    passed = 0
    for case in scenarios:
        decision = decide(build_input(case))
        expected = case["expect"]
        checks = {
            "target": decision.target_w == float(expected["target_w"]),
            "source": decision.source.value == expected["source"],
            "write": decision.write.should_write is bool(expected["write"]),
        }
        ok = all(checks.values())
        passed += int(ok)
        results.append(
            {
                "id": case["id"],
                "mode": case["mode"],
                "pass": ok,
                "checks": checks,
                "actual": {
                    "target_w": decision.target_w,
                    "source": decision.source.value,
                    "write": decision.write.should_write,
                    "control_reason": decision.control_reason,
                    "write_reason": decision.write.reason,
                },
                "expected": expected,
            }
        )
    return {
        "scenario_file": str(path),
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "pass": passed == len(results),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=Path("tests/fixtures/controller_scenarios.yaml"),
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/scenario_report.json"))
    args = parser.parse_args()
    report = run(args.scenarios)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("total", "passed", "failed", "pass")}, indent=2))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
