from __future__ import annotations

from scripts.render_readable_test_result import render


def sample_snapshots() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    values = {
        "Eigenverbrauch maximieren": [5000.0],
        "Netzdienlich laden": [0.0],
        "Akku schonen": [0.0],
        "EVOpt optimiert": [5000.0, 0.0],
    }
    for mode, targets in values.items():
        for slot in range(96):
            target = targets[min(slot // 48, len(targets) - 1)]
            rows.append(
                {
                    "mode": mode,
                    "slot": slot,
                    "time": f"{slot // 4:02d}:{(slot % 4) * 15:02d}",
                    "controller": {"target": target, "actual": target},
                }
            )
    return rows


def sample_summary() -> dict[str, object]:
    return {
        "pass": True,
        "snapshots": 384,
        "snapshots_per_mode": {
            "Eigenverbrauch maximieren": 96,
            "Netzdienlich laden": 96,
            "Akku schonen": 96,
            "EVOpt optimiert": 96,
        },
        "hard_conflict_count": 0,
        "hard_conflicts": [],
        "expected_conflicts": [
            {"type": "discharge_capability_fallback"} for _ in range(4)
        ],
        "unexpected_writers": 0,
        "write_calls": 3,
        "master_after_replay": "off",
        "writes": {
            "Eigenverbrauch maximieren": [{"value": 5000.0}],
            "Netzdienlich laden": [],
            "Akku schonen": [],
            "EVOpt optimiert": [{"value": 5000.0}, {"value": 0.0}],
        },
    }


def test_green_report_contains_plain_language_acceptance_result() -> None:
    report = render(
        sample_summary(),
        sample_snapshots(),
        {
            "initial_soc_pct": 44.0,
            "final_soc_pct": 49.82,
            "actual_pv_kwh": 43.62,
            "actual_load_kwh": 11.96,
        },
    )

    assert "Gesamtergebnis: BESTANDEN" in report
    assert "4 Betriebsarten" in report
    assert "96 simulierte Stunden" in report
    assert "384 Entscheidungen" in report
    assert "echte Schreibbefehle des Single Writers: **3**" in report
    assert "Unerwünschtes `0 ↔ 5000 W`-Flattern: **0**" in report
    assert "EVOpt öffnete und schloss genau einmal" in report
    assert "44.0 %" in report
    assert "49.82 %" in report
    assert "noch nicht berechnet" in report
    assert "4×" in report


def test_failed_report_names_the_concrete_error() -> None:
    summary = sample_summary()
    summary.update(
        {
            "pass": False,
            "hard_conflict_count": 1,
            "hard_conflicts": [
                {
                    "type": "holdcharge_not_closed",
                    "snapshot": {"mode": "EVOpt optimiert", "time": "04:15"},
                }
            ],
        }
    )

    report = render(summary, sample_snapshots(), None)

    assert "Gesamtergebnis: FEHLGESCHLAGEN" in report
    assert "EVOpt verlangte Ladesperre" in report
    assert "EVOpt optimiert, 04:15" in report
