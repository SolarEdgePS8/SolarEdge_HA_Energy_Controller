# Tests und Release-Gates

## Ziel

Ein Release darf nur veröffentlicht werden, wenn Code, YAML, Installer, Rollback, Testumgebung und Release-Artefakt gemeinsam geprüft wurden. Für produktive Freigabe bleibt zusätzlich ein kontrollierter Live-Test erforderlich.

## Was ein grüner Test bedeutet

Jede GitHub-Teststufe erklärt:

1. Was wurde geprüft?
2. Was bedeutet das Ergebnis?
3. Was ist als Nächstes zu tun?

Ein grünes GitHub-Ergebnis bedeutet, dass alle definierten statischen, modellierten und Home-Assistant-basierten Prüfungen bestanden wurden. Es bedeutet nicht automatisch, dass jede reale SolarEdge-Firmware oder Modbus-Verbindung identisch reagiert.

## Read-only Release Gate

```bash
python3 audit/readonly_audit.py . --release-gate
```

Es prüft unter anderem:

- 18 Package-YAML-Dateien;
- YAML- und Python-Syntax;
- keine privaten oder verbotenen Projektdateien;
- keine doppelten Helper oder Automation-IDs;
- vollständiges Site-Mapping;
- zentrale Writer-Gates;
- RC4-EVOpt-/Writer-Verträge;
- Watchdog-Version und Fehlalarm-Gate;
- SHA256-Parität aller 18 YAML-Dateien zur versionierten Referenz.

## Pytest und Pflichtregressionen

```bash
pytest -q -p no:cacheprovider
```

Enthalten sind unter anderem:

- Live-Paritätstest für alle 18 Package-Dateien;
- Persistenztest der Restart-Helper;
- vorgelagerter 180-Sekunden-Charge-Block-Vertrag;
- 20-Minuten-Stabilität vor einer normalen EVOpt-Freigabe;
- zusätzliche 90 Sekunden stabiler finaler Sollwert;
- genau ein Charge-Limit-Schreibpfad;
- korrekte Candidate-Entity;
- Watchdog-Fehlalarm-Gate;
- unabhängiges Writer-Sicherheitsmodell;
- direkte Auswertung der produktiven Jinja-Ausdrücke.

## Exakter Live-Fehler als blockierende Regression

Der am 23.07.2026 beobachtete Fehlerzustand ist als Pflichtfall hinterlegt:

```text
Modus = EVOpt optimiert
Ziel = 5000 W
raw = holdcharge
stable = holdcharge
charge_block = on
emergency_open = true
```

Erwartet wird zwingend:

```text
evopt_restrictive_active = true
evopt_release_ready = false
permissive_open_stable = false
priority_open_write = false
write_allowed = false
```

Ein Teststand, der daraus einen permissiven Write ableitet, kann das Deep Release Gate nicht bestehen.

## Deep Testbench

Der mehrstufige Workflow prüft:

| Stufe | Inhalt |
|---|---|
| Codespaces | reproduzierbare Komplettumgebung |
| Static | Syntax, Architektur, Datenschutz, Single Writer |
| Model | feste Szenarien, Property-Tests und unabhängige Writer-Policy |
| Fake evcc | normale und fehlerhafte API-Antworten |
| HA 2026.6.3 | Konfiguration und Runtime-Start |
| HA 2026.7.3 | Konfiguration und Runtime-Start |
| Stable Preview | nicht blockierende Kompatibilitätsvorschau mit sichtbarer Warnung bei internem Fehler |
| 96-Stunden-Replay | vier Modi, 384 Entscheidungen und produktive Automation |
| Release/Rollback | ZIP, Prüfsumme, Installation und Rücknahme |
| Deep Gate | alle verpflichtenden Stufen zusammen |

Bei Pull Requests listet der Replay-Job produktive Abweichungen zu `main` auf und prüft anschließend genau den geänderten PR-Code. Eine beabsichtigte Package-Änderung wird nicht mehr vor dem Replay pauschal abgelehnt.

## Installer- und Rollbacksimulation

GitHub Actions simuliert eine neue Installation in temporären Verzeichnissen:

```text
18 Package-Dateien
5 Runtime-/Audit-Dateien
3 Watchdog-Dateien
2 Watchdog-Tools
28 Hash-Einträge im Runtime-Manifest
```

Geprüft werden:

- Konfigurationsblock genau einmal ergänzt;
- Hash aller installierten Projektdateien korrekt;
- bestehende Installation ohne Token bricht vor Änderungen ab;
- manueller Rollback entfernt neue Dateien und stellt `configuration.yaml` wieder her;
- fehlgeschlagener HA-Check löst automatischen vollständigen Rollback aus.

## Release-Build

```bash
bash scripts/build_release.sh dist 0.1.0-rc.4
```

Der Workflow prüft:

- äußere `.sha256`-Datei;
- ZIP-Integrität;
- internes Release-Manifest;
- internen `SHA256SUMS`-Satz;
- Quellcommit;
- Watchdog, Dokumentation und Live-Paritätsmanifest im ZIP.

## Verifizierter GitHub-Stand des korrigierten Writers

```text
4 Betriebsarten
96 simulierte Stunden
384 Entscheidungen
3 notwendige Writer-Aufrufe
0 nicht erlaubte Writer
0 harte Steuerungsfehler
0 unerwünschte 0↔5000-W-Roundtrips
Controller-Master am Ende: off
```

Alle verpflichtenden Deep-Teststufen sowie normale CI und verständlicher Bericht waren grün.

## Live-Nachweis

Der frühere kurze Nachweis mit zunächst `POST_FIX_WRITE_CALLS=0` war nicht ausreichend und wurde später durch zwei echte Writes widerlegt. Die korrigierte Analyse steht in:

```text
docs/16_EVOPT_NIGHT_FLAPPING_LIVE_FIX.md
```

Ein neuer Release oder Abschluss des Issues erfolgt erst nach Installation des korrigierten Stands und einem ausreichend langen Watchdog-Live-Test ohne unerwünschten `5000 → 0`-Roundtrip.
