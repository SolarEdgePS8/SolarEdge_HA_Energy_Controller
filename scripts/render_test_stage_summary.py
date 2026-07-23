#!/usr/bin/env python3
"""Write a plain-language explanation for one GitHub Actions test stage."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class Stage:
    title: str
    checks: str
    green: str
    red: str
    next_step: str


STAGES = {
    "quick": Stage(
        "Schnellprüfung der Dateien",
        "YAML, Python, Shell-Skripte, Manifest, Installer und grundlegende Sicherheitsverträge.",
        "Die Dateien sind grundsätzlich lesbar und der Installationsaufbau ist konsistent.",
        "Mindestens eine Datei, Prüfsumme, Installationsregel oder Sicherheitsregel ist fehlerhaft.",
        "Den ersten roten Schritt öffnen; dort stehen Datei, Zeile und konkrete Ursache.",
    ),
    "codespaces": Stage(
        "Komplette Entwicklungsumgebung",
        "Ob der Dev Container startet und darin dieselben Tests reproduzierbar laufen.",
        "Eine fremde Person kann die Testumgebung ohne lokale Sonderkonfiguration starten.",
        "Container-Aufbau oder kompletter Testeinstieg funktioniert nicht reproduzierbar.",
        "Die Logs `up.log`, `post-create.log` und `test.log` im Artefakt prüfen.",
    ),
    "static": Stage(
        "Dateien, Architektur und Datenschutz",
        "Syntax, Privacy-Gate, Fixture-Schema, Single Writer und verbotene Schreibpfade.",
        "Keine offensichtliche Struktur-, Datenschutz- oder Architekturverletzung wurde gefunden.",
        "Eine Datei ist ungültig oder eine zentrale Sicherheitsregel wurde verletzt.",
        "Die erste rote Meldung beheben; ein Release bleibt bis dahin gesperrt.",
    ),
    "model": Stage(
        "Steuerungslogik und Grenzfälle",
        "Feste Szenarien, Zufallstests, Zeitabläufe und den echten EVOpt-Fail-open-Fehler vom 23.07.2026.",
        "Die berechneten Entscheidungen erfüllen die unabhängigen Sicherheitsregeln.",
        "Mindestens eine Situation kann zu einer falschen Ladefreigabe oder einem falschen Write führen.",
        "Den genannten Szenarionamen öffnen und die Eingabewerte mit der erwarteten Entscheidung vergleichen.",
    ),
    "fake-evcc": Stage(
        "evcc-/EVOpt-Schnittstelle",
        "Normale, verspätete, unvollständige und fehlerhafte Antworten eines kontrollierten Testservers.",
        "Der Controller reagiert auf die geprüften evcc-Antworten wie vorgesehen.",
        "Eine bestimmte API-Antwort kann falsch interpretiert werden.",
        "Den fehlgeschlagenen API-Fall und die dazugehörige erwartete Aktion prüfen.",
    ),
    "ha-smoke": Stage(
        "Home Assistant startet mit dem Package",
        "Konfigurationsprüfung und Runtime-Start in der angegebenen Home-Assistant-Version.",
        "Home Assistant akzeptiert die Installation und startet ohne blockierenden Konfigurationsfehler.",
        "Das Package lässt sich in dieser Home-Assistant-Version nicht sauber laden oder starten.",
        "Im HA-Log nach der ersten Meldung mit `ERROR` oder `Invalid config` suchen.",
    ),
    "stable-preview": Stage(
        "Vorschau auf die aktuelle HA-Stable-Version",
        "Smoke-Test und 24-Stunden-Replay gegen das aktuell veröffentlichte Stable-Image.",
        "Auch die aktuelle Stable-Version zeigt im Test keinen neuen Fehler.",
        "Es gibt möglicherweise eine neue HA-Inkompatibilität; dieser Vorschautest blockiert bewusst noch nicht.",
        "Stable-Artefakt prüfen und die Abweichung vor dem nächsten Release bewerten.",
    ),
    "replay": Stage(
        "96-Stunden-Replay aller vier Modi",
        "Vier Betriebsarten mit je 24 simulierten Stunden, echte Produktionsautomation und Test-Schreibziel.",
        "Alle Modi liefen vollständig; keine unerlaubten Writer und kein erkannter harter Steuerungsfehler.",
        "Ein Modus, Writer oder Sicherheitszustand verhielt sich im Replay falsch.",
        "Den verständlichen Bericht zuerst lesen; technische JSON- und HA-Logs nur für die Detailursache öffnen.",
    ),
    "release": Stage(
        "Installation, Release-ZIP und Rollback",
        "Archiv, Prüfsumme, Manifest, portable Installation und vollständige Rücknahme nach Fehlern.",
        "Das erzeugte Paket ist konsistent und lässt sich im Test installieren und zurückrollen.",
        "Release-Datei, Installation oder Rollback ist unvollständig oder inkonsistent.",
        "Keinen Release veröffentlichen; zuerst den ersten roten Installationsschritt beheben.",
    ),
    "gate": Stage(
        "Gesamte Freigabeentscheidung",
        "Ob alle verpflichtenden Deep-Teststufen erfolgreich waren.",
        "Alle Pflichtstufen sind grün. Für produktive Freigabe bleibt zusätzlich der echte Live-Test nötig.",
        "Mindestens eine Pflichtstufe ist rot oder wurde abgebrochen.",
        "In der Ergebnistabelle die rote Stufe öffnen; nichts mergen oder veröffentlichen.",
    ),
}


def effective_status(stage_name: str, status: str, root: Path = Path(".")) -> str:
    """Return the status that a nontechnical reader should actually see."""

    normalized = status.strip().lower()
    if stage_name != "stable-preview" or normalized != "success":
        return normalized

    preview_status = root / "artifacts" / "stable-preview" / "status.json"
    if not preview_status.is_file():
        return "warning"

    try:
        payload = json.loads(preview_status.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "warning"
    return "success" if payload.get("pass") is True else "warning"


def render(stage: Stage, status: str) -> str:
    normalized = status.strip().lower()
    passed = normalized == "success"
    warning = normalized in {"warning", "preview-failed", "nonblocking-failure"}

    if passed:
        icon = "✅"
        result = "BESTANDEN"
        meaning = stage.green
        action = "Keine Aktion nötig; die nächste Teststufe entscheidet weiter."
    elif warning:
        icon = "⚠️"
        result = "WARNUNG – PRÜFEN"
        meaning = stage.red
        action = stage.next_step
    else:
        icon = "❌"
        result = "NICHT BESTANDEN"
        meaning = stage.red
        action = stage.next_step

    return "\n".join(
        [
            f"## {icon} {stage.title}: {result}",
            "",
            "**Was wird hier geprüft?**  ",
            stage.checks,
            "",
            "**Was bedeutet dieses Ergebnis?**  ",
            meaning,
            "",
            "**Was ist jetzt zu tun?**  ",
            action,
            "",
            "> Wichtig: Ein vollständig grüner GitHub-Test ersetzt nicht den kontrollierten Live-Test auf der realen SolarEdge-Anlage.",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    parser.add_argument("--status", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    status = effective_status(args.stage, args.status)
    text = render(STAGES[args.stage], status)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
