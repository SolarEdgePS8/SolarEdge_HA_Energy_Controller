"""Replay one anonymized 24-hour measurement day through all controller modes.

The replay is deliberately independent from Home Assistant.  It consumes the same
15-minute fixture that the Home Assistant runtime replay uses and produces a
machine-readable decision trace for every slot and mode.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

from testbench.reference.controller_model import (
    ControllerInput,
    ControllerSequence,
    EvoptAction,
    Mode,
)

MODES = tuple(Mode)
EXPECTED_ACTIONS = {
    EvoptAction.NORMAL,
    EvoptAction.HOLDCHARGE,
    EvoptAction.CHARGE,
    EvoptAction.DISCHARGE,
    EvoptAction.HOLD,
    EvoptAction.UNAVAILABLE,
}


def load_fixture(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records")
    if records is None and isinstance(data.get("columns"), list) and isinstance(data.get("rows"), list):
        records = [dict(zip(data["columns"], row, strict=True)) for row in data["rows"]]
        data["records"] = records
    if not isinstance(records, list) or len(records) != 96:
        raise ValueError("24h fixture must contain exactly 96 records")
    if data.get("cadence_minutes") != 15:
        raise ValueError("24h fixture cadence must be 15 minutes")
    expected_minutes = list(range(0, 24 * 60, 15))
    actual_minutes = [int(row["minute"]) for row in records]
    if actual_minutes != expected_minutes:
        raise ValueError("fixture minutes are not a complete monotonic 15-minute day")
    for row in records:
        for key in (
            "pv_w",
            "home_w",
            "soc_pct",
            "pv_forecast_remaining_kwh",
            "pv_forecast_tomorrow_kwh",
        ):
            if row.get(key) is None:
                raise ValueError(f"missing {key} in slot {row.get('slot')}")
        if abs(float(row.get("energy_balance_residual_w", 0))) > 20:
            raise ValueError(f"energy balance residual too high in slot {row['slot']}")
    return data


def _evopt_action(value: str, healthy: bool) -> EvoptAction:
    if not healthy:
        return EvoptAction.UNAVAILABLE
    try:
        action = EvoptAction(value)
    except ValueError as exc:
        raise ValueError(f"unsupported EVOpt fixture action: {value}") from exc
    if action not in EXPECTED_ACTIONS:
        raise ValueError(f"unsupported EVOpt fixture action: {value}")
    return action


def _classify_roundtrips(writes: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    hard: list[dict[str, Any]] = []
    expected: list[dict[str, Any]] = []
    for first, middle, last in zip(writes, writes[1:], writes[2:]):
        if (
            first["new_w"] == last["new_w"]
            and first["new_w"] != middle["new_w"]
            and last["at_s"] - first["at_s"] <= 1800
        ):
            conflict = {
                "type": "roundtrip_30m",
                "first": first,
                "middle": middle,
                "last": last,
            }
            reasons = {
                str(first.get("control_reason", "")),
                str(middle.get("control_reason", "")),
                str(last.get("control_reason", "")),
            }
            sources = {
                str(first.get("source", "")),
                str(middle.get("source", "")),
                str(last.get("source", "")),
            }
            if any("fallback" in reason or "startup" in reason for reason in reasons) or any(
                "evopt" in source for source in sources
            ):
                conflict["classification"] = "expected_evopt_outage_or_recovery"
                expected.append(conflict)
            else:
                conflict["classification"] = "unexpected_flapping"
                hard.append(conflict)
    return hard, expected


def replay_mode(fixture: dict[str, Any], mode: Mode) -> dict[str, Any]:
    records = fixture["records"]
    initial = ControllerInput(
        mode=mode,
        now_minute=0,
        soc_pct=float(fixture["initial_soc_pct"]),
        battery_capacity_kwh=float(fixture["battery_capacity_kwh"]),
        pv_power_w=float(records[0]["pv_w"]),
        home_power_w=float(records[0]["home_w"]),
        pv_today_remaining_kwh=float(records[0]["pv_forecast_remaining_kwh"]),
        pv_tomorrow_kwh=float(records[0]["pv_forecast_tomorrow_kwh"]),
        planned_start_minute=11 * 60 + 45,
        latest_finish_minute=14 * 60 + 15,
        evopt_healthy=bool(records[0]["evopt_healthy"]),
        evopt_action=_evopt_action(
            str(records[0]["evopt_action"]), bool(records[0]["evopt_healthy"])
        ),
        evopt_unavailable_age_s=0,
        current_charge_limit_w=0,
        candidate_stable_s=0,
        seconds_since_last_write=9999,
    )
    sequence = ControllerSequence(initial)
    unavailable_age_s = 0
    trace: list[dict[str, Any]] = []
    hard_conflicts: list[dict[str, Any]] = []
    expected_conflicts: list[dict[str, Any]] = []
    previous_write_count = 0

    for index, row in enumerate(records):
        healthy = bool(row["evopt_healthy"])
        if healthy:
            unavailable_age_s = 0
        else:
            unavailable_age_s += 15 * 60
        action = _evopt_action(str(row["evopt_action"]), healthy)
        decision = sequence.step(
            0 if index == 0 else 15 * 60,
            mode=mode,
            now_minute=int(row["minute"]),
            soc_pct=float(row["soc_pct"]),
            pv_power_w=float(row["pv_w"]),
            home_power_w=float(row["home_w"]),
            pv_today_remaining_kwh=float(row["pv_forecast_remaining_kwh"]),
            pv_tomorrow_kwh=float(row["pv_forecast_tomorrow_kwh"]),
            evopt_healthy=healthy,
            evopt_action=action,
            evopt_unavailable_age_s=unavailable_age_s,
        )
        new_writes = sequence.writes[previous_write_count:]
        previous_write_count = len(sequence.writes)
        slot = {
            "mode": mode.value,
            "slot": int(row["slot"]),
            "time": row["time"],
            "simulated_second": sequence.now_s,
            "inputs": {
                "pv_w": row["pv_w"],
                "home_w": row["home_w"],
                "soc_pct": row["soc_pct"],
                "forecast_remaining_kwh": row["pv_forecast_remaining_kwh"],
                "forecast_tomorrow_kwh": row["pv_forecast_tomorrow_kwh"],
                "evopt_action": action.value,
                "evopt_healthy": healthy,
                "evopt_unavailable_age_s": unavailable_age_s,
            },
            "decision": {
                "target_w": decision.target_w,
                "source": decision.source.value,
                "control_reason": decision.control_reason,
                "write_allowed": decision.write_allowed,
                "write": asdict(decision.write),
                "actual_w_after": sequence.current_w,
            },
            "writes": new_writes,
        }
        if not 0 <= decision.target_w <= 5000:
            hard_conflicts.append(
                {"type": "target_out_of_range", "slot": row["slot"], "value": decision.target_w}
            )
        if not 0 <= sequence.current_w <= 5000:
            hard_conflicts.append(
                {"type": "actual_out_of_range", "slot": row["slot"], "value": sequence.current_w}
            )
        if new_writes and not decision.write_allowed:
            hard_conflicts.append(
                {"type": "write_with_gate_closed", "slot": row["slot"], "writes": new_writes}
            )
        trace.append(slot)

    seen_times = Counter(int(write["at_s"]) for write in sequence.writes)
    duplicate_times = [at_s for at_s, count in seen_times.items() if count > 1]
    if duplicate_times:
        hard_conflicts.append({"type": "duplicate_writes_same_instant", "times": duplicate_times})

    roundtrip_hard, roundtrip_expected = _classify_roundtrips(sequence.writes)
    hard_conflicts.extend(roundtrip_hard)
    expected_conflicts.extend(roundtrip_expected)

    max_writes = 16 if mode is Mode.EVOPT else 8
    if len(sequence.writes) > max_writes:
        hard_conflicts.append(
            {"type": "excessive_write_count", "writes": len(sequence.writes), "limit": max_writes}
        )

    sources = Counter(slot["decision"]["source"] for slot in trace)
    reasons = Counter(slot["decision"]["control_reason"] for slot in trace)
    return {
        "mode": mode.value,
        "pass": not hard_conflicts,
        "slots": len(trace),
        "write_count": len(sequence.writes),
        "writes": sequence.writes,
        "source_counts": dict(sources),
        "reason_counts": dict(reasons),
        "hard_conflicts": hard_conflicts,
        "expected_conflicts": expected_conflicts,
        "trace": trace,
    }


def replay_all(fixture: dict[str, Any]) -> dict[str, Any]:
    results = [replay_mode(fixture, mode) for mode in MODES]
    return {
        "schema_version": 1,
        "fixture": fixture["name"],
        "source_date": fixture["source_date"],
        "cadence_minutes": fixture["cadence_minutes"],
        "modes": [mode.value for mode in MODES],
        "pass": all(result["pass"] for result in results),
        "total_snapshots": sum(int(result["slots"]) for result in results),
        "total_writes": sum(int(result["write_count"]) for result in results),
        "hard_conflict_count": sum(len(result["hard_conflicts"]) for result in results),
        "expected_conflict_count": sum(len(result["expected_conflicts"]) for result in results),
        "results": results,
    }


def write_outputs(report: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {**report, "results": [{k: v for k, v in r.items() if k != "trace"} for r in report["results"]]}
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with (output_dir / "trace.jsonl").open("w", encoding="utf-8") as handle:
        for result in report["results"]:
            for row in result["trace"]:
                handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    with (output_dir / "conflicts.json").open("w", encoding="utf-8") as handle:
        json.dump(
            {
                result["mode"]: {
                    "hard": result["hard_conflicts"],
                    "expected": result["expected_conflicts"],
                }
                for result in report["results"]
            },
            handle,
            indent=2,
            ensure_ascii=False,
        )
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    fixture = load_fixture(args.fixture)
    report = replay_all(fixture)
    write_outputs(report, args.output_dir)
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
