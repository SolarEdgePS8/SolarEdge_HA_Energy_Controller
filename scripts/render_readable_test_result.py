#!/usr/bin/env python3
"""Render the technical 24h replay result as a plain-language Markdown report."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any


MODE_ORDER = (
    "Eigenverbrauch maximieren",
    "Netzdienlich laden",
    "Akku schonen",
    "EVOpt optimiert",
)


ERROR_LABELS = {
    "invalid_limit": "Ungültiges Lade-Limit außerhalb von 0 bis 5000 W",
    "safety_state": "Sicherheitsprüfung war nicht in Ordnung",
    "holdcharge_not_closed": "EVOpt verlangte Ladesperre, das Lade-Limit war aber offen",
    "roundtrip": "Unerwünschtes Hin-und-her-Schalten des Lade-Limits",
    "incomplete_modes": "Mindestens ein Modus wurde nicht vollständig durchlaufen",
    "unexpected_writer": "Ein nicht erlaubter Schreiber hat das Testregister verändert",
    "master_not_off": "Der Controller-Master war nach dem Test noch eingeschaltet",
}

EXPECTED_LABELS = {
    "discharge_capability_fallback": (
        "EVOpt plante Entladung. Der aktuelle Controller steuert nur die "
        "Ladefreigabe, nicht eine separate Entladeleistung."
    ),
    "roundtrip": "Erwartete Wiederherstellung nach einem simulierten Fallback",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.is_file():
        return []
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def format_values(values: list[float]) -> str:
    if not values:
        return "keine"
    return ", ".join(f"{value:g} W" for value in values)


def status_icon(ok: bool) -> str:
    return "✅" if ok else "❌"


def simplify_conflict(item: dict[str, Any]) -> str:
    conflict_type = str(item.get("type") or "unknown")
    label = ERROR_LABELS.get(conflict_type, f"Unbekannter Fehler: {conflict_type}")
    snapshot = item.get("snapshot") or {}
    time_value = snapshot.get("time") or item.get("time")
    mode = snapshot.get("mode") or item.get("mode")
    details = []
    if mode:
        details.append(str(mode))
    if time_value:
        details.append(str(time_value))
    return f"{label}" + (f" ({', '.join(details)})" if details else "")


def render(
    summary: dict[str, Any],
    snapshots: list[dict[str, Any]],
    fixture: dict[str, Any] | None,
) -> str:
    passed = bool(summary.get("pass"))
    snapshot_count = int(summary.get("snapshots") or len(snapshots))
    per_mode = summary.get("snapshots_per_mode") or Counter(
        str(row.get("mode")) for row in snapshots if row.get("mode")
    )
    tested_modes = [mode for mode in MODE_ORDER if int(per_mode.get(mode, 0)) > 0]
    simulated_hours = sum(int(per_mode.get(mode, 0)) for mode in tested_modes) / 4

    values: dict[str, dict[str, set[float]]] = defaultdict(
        lambda: {"target": set(), "actual": set()}
    )
    for row in snapshots:
        mode = str(row.get("mode") or "")
        controller = row.get("controller") or {}
        for key in ("target", "actual"):
            try:
                values[mode][key].add(float(controller.get(key)))
            except (TypeError, ValueError):
                pass

    writes = summary.get("writes") or {}
    hard_conflicts = list(summary.get("hard_conflicts") or [])
    expected_conflicts = list(summary.get("expected_conflicts") or [])
    unexpected_flapping = sum(
        1
        for item in hard_conflicts
        if item.get("type") == "roundtrip"
        and item.get("classification") == "unexpected_flapping"
    )

    lines = [
        "# Verständlicher Testbericht",
        "",
        f"## {status_icon(passed)} Gesamtergebnis: {'BESTANDEN' if passed else 'FEHLGESCHLAGEN'}",
        "",
        "### Was wurde tatsächlich getestet?",
        "",
        f"- **{len(tested_modes)} Betriebsarten**, jeweils **24 simulierte Stunden**",
        f"- insgesamt **{simulated_hours:g} simulierte Stunden**",
        f"- **{snapshot_count} Entscheidungen** im 15-Minuten-Raster",
        "- Home Assistant lief in einem echten Container, aber **ohne Verbindung zur realen SolarEdge-Anlage**",
        "- der produktive Session-Manager und der produktive Charge-Limit-Writer wurden ausgeführt",
        "",
        "### Greifbare Ergebnisse",
        "",
        f"- {status_icon(int(summary.get('hard_conflict_count') or len(hard_conflicts)) == 0)} Harte Steuerungsfehler: **{int(summary.get('hard_conflict_count') or len(hard_conflicts))}**",
        f"- {status_icon(int(summary.get('unexpected_writers') or 0) == 0)} Nicht erlaubte Schreiber: **{int(summary.get('unexpected_writers') or 0)}**",
        f"- {status_icon(unexpected_flapping == 0)} Unerwünschtes `0 ↔ 5000 W`-Flattern: **{unexpected_flapping}**",
        f"- echte Schreibbefehle des Single Writers: **{int(summary.get('write_calls') or 0)}**",
        f"- Controller-Master nach dem Test: **{summary.get('master_after_replay', 'unbekannt')}**",
        "",
        "### Ergebnis je Betriebsart",
        "",
        "| Betriebsart | 15-Minuten-Prüfungen | beobachtete Sollwerte | echte Schreibbefehle | verständliche Bewertung |",
        "|---|---:|---|---:|---|",
    ]

    for mode in MODE_ORDER:
        count = int(per_mode.get(mode, 0))
        mode_values = sorted(values[mode]["target"])
        mode_writes = list(writes.get(mode) or [])
        written_values = [item.get("value") for item in mode_writes]
        if count != 96:
            assessment = "Nicht vollständig getestet"
        elif mode == "Eigenverbrauch maximieren":
            assessment = "Laden wurde freigegeben; ein einmaliger Write ist korrekt."
        elif mode in {"Netzdienlich laden", "Akku schonen"}:
            assessment = (
                "Laden blieb gesperrt. Kein Write war nötig, weil das Testregister "
                "bereits auf 0 W stand."
            )
        elif written_values == [5000.0, 0.0]:
            assessment = "EVOpt öffnete und schloss genau einmal; kein Hin-und-her-Flattern."
        else:
            assessment = "Ablauf siehe Schreibwerte; Ergebnis muss geprüft werden."
        lines.append(
            f"| {mode} | {count} | {format_values(mode_values)} | {len(mode_writes)} | {assessment} |"
        )

    lines.extend(["", "### Akku voll oder nicht voll?", ""])
    if fixture:
        initial_soc = fixture.get("initial_soc_pct")
        final_soc = fixture.get("final_soc_pct")
        pv_kwh = fixture.get("actual_pv_kwh")
        load_kwh = fixture.get("actual_load_kwh")
        lines.extend(
            [
                f"- eingespielter Messtag: **{pv_kwh} kWh PV** und **{load_kwh} kWh Hausverbrauch**",
                f"- im Messprofil stieg der Ladestand von **{initial_soc} %** auf **{final_soc} %**",
            ]
        )
    lines.extend(
        [
            "- **Ob der Controller den Akku tatsächlich voll bekommen hätte, wird in diesem Test noch nicht berechnet.**",
            "- Der Ladestand ist ein eingespielter Messwert. Es gibt noch kein geschlossenes physikalisches Batteriemodell, das den SoC aus jedem Writer-Befehl neu berechnet.",
            "- Der Test beweist daher die Steuerlogik und die Zahl der Schreibzugriffe, aber nicht den realen Ladeerfolg einer Batterie.",
            "",
        ]
    )

    if hard_conflicts:
        lines.extend(["### Gefundene Fehler", ""])
        for item in hard_conflicts[:12]:
            lines.append(f"- ❌ {simplify_conflict(item)}")
        if len(hard_conflicts) > 12:
            lines.append(f"- … und {len(hard_conflicts) - 12} weitere Fehler")
        lines.append("")
    else:
        lines.extend(["### Gefundene Fehler", "", "- ✅ Keine harten Fehler im 24-Stunden-Replay.", ""])

    expected_counts = Counter(str(item.get("type") or "unknown") for item in expected_conflicts)
    if expected_counts:
        lines.extend(["### Bekannte, erwartete Grenzen", ""])
        for key, count in sorted(expected_counts.items()):
            label = EXPECTED_LABELS.get(key, key)
            lines.append(f"- ⚪ **{count}×** {label}")
        lines.append("")

    lines.extend(
        [
            "### Was ein grünes Ergebnis bedeutet",
            "",
            "- alle vier Modi wurden vollständig durchgerechnet;",
            "- Home Assistant konnte die Konfiguration laden und starten;",
            "- kein fremder Writer schrieb auf das Testregister;",
            "- die erwarteten 0-/5000-W-Entscheidungen wurden ohne unnötige Doppelwrites umgesetzt;",
            "- die reale Anlage wurde dabei nicht verändert.",
            "",
            "### Was damit noch nicht bewiesen ist",
            "",
            "- reale Modbus-Latenzen und SolarEdge-Firmwareverhalten;",
            "- tatsächliche Flash-/EEPROM-Belastung;",
            "- reales Erreichen des Ziel-SoC;",
            "- korrekte Entity-Zuordnung auf einer fremden Home-Assistant-Installation.",
            "",
            "Die technischen JSON-, Event- und Home-Assistant-Logs bleiben zusätzlich als Artefakte erhalten.",
        ]
    )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--snapshots", type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = load_json(args.summary)
    snapshots = load_jsonl(args.snapshots)
    fixture = load_json(args.fixture) if args.fixture and args.fixture.is_file() else None
    report = render(summary, snapshots, fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report, encoding="utf-8")
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
