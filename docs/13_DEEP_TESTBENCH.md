# Deep Testbench und GitHub Codespaces

## Ziel

Der Deep Testbench prüft den SolarEdge HA Energy Controller außerhalb einer realen Anlage. Er verwendet neutrale Testdaten, echte Projektdateien und Home-Assistant-Container. Eine Verbindung zur produktiven SolarEdge- oder Home-Assistant-Instanz wird niemals hergestellt.

Die Testumgebung soll zwei Fragen beantworten:

1. Ist der Code technisch und logisch konsistent?
2. Kann ein Fehlerfall zu einem falschen SolarEdge-Schreibzugriff führen?

Sie kann nicht beweisen, dass jede reale Wechselrichter-, Batterie- oder Modbus-Firmware identisch reagiert. Deshalb bleibt nach allen grünen GitHub-Tests eine kontrollierte Live-Abnahme erforderlich.

## Die Testebenen

Die Testumgebung verbindet:

1. YAML-, Python- und Shell-Syntax;
2. Architektur-, Datenschutz- und Single-Writer-Verträge;
3. ein unabhängiges Python-Referenzmodell;
4. feste Szenarien, Grenzwerte und Property-Tests;
5. direkte Auswertung produktiver Jinja-Ausdrücke;
6. einen kontrollierbaren Fake-evcc-Server;
7. Home-Assistant-Smoke-Tests;
8. ein 96-Stunden-Replay aller vier Modi;
9. Release-, Installer- und Rollbackprüfung;
10. Codespaces/Dev-Container als reproduzierbare Komplettumgebung.

## Was der Nutzer bei jedem Test sieht

Jede GitHub-Teststufe schreibt am Ende einen Abschnitt in normaler Sprache:

- **Was wird geprüft?**
- **Was bedeutet Grün?**
- **Was bedeutet Rot oder eine Warnung?**
- **Was muss als Nächstes getan werden?**

Technische Logs und JSON-Dateien bleiben erhalten, sind aber nicht mehr der erste Einstiegspunkt.

Die aktuelle Stable-Vorschau ist bewusst nicht blockierend. Schlägt ihr interner Smoke- oder Replay-Test fehl, wird sie trotzdem nicht fälschlich als grün erklärt, sondern als:

```text
⚠️ WARNUNG – PRÜFEN
```

## Teststufen in GitHub Actions

| Job | Einfache Bedeutung | Blockiert den Merge? |
|---|---|---|
| `codespaces-devcontainer` | Die komplette Testumgebung lässt sich reproduzierbar aufbauen | ja |
| `static-architecture` | Dateien, Datenschutz und Single-Writer-Architektur sind konsistent | ja |
| `model-matrix-property-state` | Steuerungslogik und Grenzfälle erfüllen die unabhängigen Sicherheitsregeln | ja |
| `fake-evcc-api` | Normale und fehlerhafte evcc-Antworten werden richtig behandelt | ja |
| `home-assistant-2026.6.3-smoke` | Das Package lädt und startet in HA 2026.6.3 | ja |
| `home-assistant-2026.7.3-smoke` | Das Package lädt und startet in HA 2026.7.3 | ja |
| `stable-preview-nonblocking` | Vorschau gegen das aktuell veröffentlichte Stable-Image | nein, aber Warnung sichtbar |
| `main-production-real-day-24h` | Vier Modi mit je 24 Stunden und produktiver Automation | ja |
| `release-installer-rollback` | ZIP, Prüfsumme, Installation und Rollback sind konsistent | ja |
| `deep-release-gate` | Alle verpflichtenden Stufen sind erfolgreich | ja |

## Wichtige Korrektur: Produktive PR-Änderungen werden wirklich getestet

Früher verlangte der 96-Stunden-Job vor dem Replay Bytegleichheit mit `main`. Das war für normale Validierung sinnvoll, hatte aber einen entscheidenden Nachteil:

> Sobald ein Pull Request absichtlich eine produktive Package-Datei änderte, brach der Job vor dem Replay ab.

Damit konnte ausgerechnet ein produktiver Fix nicht vollständig vor dem Merge geprüft werden.

Jetzt gilt:

1. Der Test listet verständlich auf, welche produktiven Dateien vom aktuellen `main` abweichen.
2. Anschließend läuft das Replay mit genau dem Code des Pull Requests.
3. Eine produktive Änderung wird nicht mehr pauschal blockiert, sondern tatsächlich geprüft.

Beispiel aus der EVOpt-Korrektur:

```text
Produktive Datei unter Test:
package/se_controller_80_charge_writer.yaml
```

## Pflichtregression für den echten EVOpt-Live-Fehler

Am 23.07.2026 zeigte der reale Write-Watchdog:

```text
Wert=5000 raw=holdcharge stable=holdcharge block=on target_stable_s=90
Wert=0    raw=holdcharge stable=holdcharge block=on target_stable_s=0
```

Einfache Bedeutung: EVOpt verlangte eindeutig eine Ladesperre, aber der Writer öffnete kurzzeitig trotzdem auf `5000 W`. Der Emergency-/Fail-open-Pfad umging den ersten Schutz.

Dieser Fall ist jetzt in drei unabhängigen Ebenen Pflichtbestandteil:

### 1. Unabhängiges Writer-Modell

`testbench/reference/writer_policy.py` beschreibt die Sicherheitsregel ohne Home Assistant und ohne produktive YAML-Datei:

```text
EVOpt aktiv
UND raw=holdcharge ODER stable=holdcharge ODER charge_block=on
UND Ziel=5000 W
=> Write verboten
```

Das gilt auch bei `emergency_open=true`.

### 2. Direkte Auswertung der produktiven Jinja-Logik

`tests/deep/test_writer_template_regression.py` lädt die echte Datei:

```text
package/se_controller_80_charge_writer.yaml
```

Die produktiven Jinja-Ausdrücke werden mit exakt dem Live-Fehlerzustand ausgeführt. Erwartet wird zwingend:

```text
evopt_restrictive_active = true
evopt_release_ready = false
permissive_open_stable = false
priority_open_write = false
write_allowed = false
```

### 3. Vertragstest der Writer-Datei

`tests/test_evopt_writer_release_guard.py` stellt zusätzlich sicher:

- alle drei restriktiven Signale werden berücksichtigt;
- Emergency-/Fail-open kann sie nicht umgehen;
- `0 W` bleibt sofort möglich;
- eine normale Freigabe benötigt 20 Minuten stabile EVOpt-Rohaktion plus 90 Sekunden stabilen finalen Sollwert;
- es existiert weiterhin genau ein `number.set_value`.

## Unabhängiges Controller-Referenzmodell

`testbench/reference/controller_model.py` bleibt unabhängig von Home Assistant und den produktiven Jinja-Templates. Es modelliert unter anderem:

- die vier Betriebsarten;
- Safety-Gates;
- EVOpt-Aktionen und Fallback;
- restriktive und permissive Übergänge;
- Zeitabläufe, Cooldown und Mindestdifferenzen;
- synthetische Write-Protokolle.

Das Modell ersetzt die Produktivlogik nicht. Es dient als unabhängige Sollinstanz. Eine Abweichung zwischen Modell und Produktivcode soll den Test rot machen.

## Fake evcc

`testbench/fake_evcc/app.py` stellt eine kontrollierbare `/api/state` bereit. Geprüft werden unter anderem:

```text
normal
holdcharge
charge
discharge
stale
missing_evopt
multiple_batteries
not_controllable
invalid_json
http_404
http_500
timeout
```

Beispiel für einen lokalen Test:

```bash
python -m testbench.fake_evcc.app --port 7070 --scenario holdcharge
curl http://127.0.0.1:7070/api/state
curl -X POST http://127.0.0.1:7070/__scenario/normal
```

## Home-Assistant-Tests

`scripts/run_ha_smoke.sh`:

1. erstellt eine temporäre neutrale Home-Assistant-Konfiguration;
2. installiert die echten Projektdateien mit dem portablen Installer;
3. verwendet ausschließlich synthetische Test-Entities;
4. führt `check_config` aus;
5. startet Home Assistant im Container;
6. prüft Config, Sanity und den ausgeschalteten Master;
7. speichert Logs und Ergebnisse als Artefakte.

Die synthetische Writer-Entity lautet:

```text
number.test_storage_charge_limit
```

Sie hat keine Verbindung zu Modbus oder realer Hardware.

## 96-Stunden-Replay

`scripts/run_ha_24h_replay.sh` spielt denselben anonymisierten Messtag durch alle vier Betriebsarten:

```text
4 Betriebsarten
× 24 simulierte Stunden
= 96 simulierte Stunden
= 384 Entscheidungen im 15-Minuten-Raster
```

Der produktive Session-Manager und der produktive Charge-Limit-Writer laufen in Home Assistant. Geschrieben wird nur auf das synthetische Testregister.

Der erfolgreich geprüfte EVOpt-Hard-Block-Stand ergab:

```text
3 notwendige Writer-Aufrufe
0 nicht erlaubte Writer
0 harte Steuerungsfehler
0 unerwünschte 0↔5000-W-Roundtrips
Controller-Master am Ende: off
```

Der Test kann zuverlässig sagen:

- ob die Steuerung korrekt geöffnet oder geschlossen hat;
- wie oft geschrieben wurde;
- ob ein fremder Writer geschrieben hat;
- ob ein unnötiger Roundtrip erkannt wurde;
- ob Safety- und Writer-Regeln eingehalten wurden.

Er kann noch nicht beweisen:

- ob eine reale Batterie am Tagesende voll wäre;
- welche reale Modbus-Latenz auftritt;
- wie eine konkrete SolarEdge-Firmware reagiert;
- wie stark EEPROM oder Flash real belastet werden.

## Codespaces

1. Repository oder Pull Request öffnen.
2. **Code → Codespaces → Create codespace** wählen.
3. Warten, bis `postCreateCommand` abgeschlossen ist.
4. Im Terminal ausführen:

```bash
bash scripts/run_deep_tests.sh all
bash scripts/run_ha_smoke.sh
bash scripts/run_ha_24h_replay.sh
```

Für die interaktive Fake-evcc-/Home-Assistant-Umgebung:

```bash
docker compose -f docker/docker-compose.test.yml up --build
```

Ports:

```text
7070  Fake evcc
8123  Home Assistant Testbench
```

## Artefakte

Je nach Job werden unter anderem gespeichert:

```text
TEST_RESULT_READABLE.md
production-files-under-test.txt
readonly_audit.txt
ruff.txt
shellcheck.txt
*-junit.xml
scenario_report.json
coverage.xml
coverage-html/
installer.log
check-config.log
home-assistant.log
results/summary.json
results/write_intents.jsonl
Release-ZIP und SHA256
```

Für normale Nutzer ist `TEST_RESULT_READABLE.md` der erste Einstiegspunkt. Die technischen Dateien dienen der Ursachenanalyse.

## Empfohlene Branch Protection

Für `main` sollten mindestens diese Checks verpflichtend sein:

```text
Validate SolarEdge HA Energy Controller / validate
Verständliche Testergebnisse / Lesbarer YAML- und Installationscheck
Deep SolarEdge Controller Testbench / codespaces-devcontainer
Deep SolarEdge Controller Testbench / static-architecture
Deep SolarEdge Controller Testbench / model-matrix-property-state
Deep SolarEdge Controller Testbench / fake-evcc-api
Deep SolarEdge Controller Testbench / home-assistant-2026.6.3-smoke
Deep SolarEdge Controller Testbench / home-assistant-2026.7.3-smoke
Deep SolarEdge Controller Testbench / main-production-real-day-24h
Deep SolarEdge Controller Testbench / release-installer-rollback
Deep SolarEdge Controller Testbench / deep-release-gate
```

Force-Pushes auf `main` sollten blockiert bleiben.

## Grenzen und Live-Abnahme

Ein vollständig grüner GitHub-Test ist die Voraussetzung für einen Merge. Er ersetzt nicht die reale Abnahme.

Nach Installation auf der Referenzanlage müssen mindestens geprüft werden:

- `ha core check` und First Checks erfolgreich;
- nur der erlaubte Single Writer aktiv;
- keine `5000-W`-Writes bei `raw=holdcharge`, `stable=holdcharge` oder `charge_block=on`;
- keine unerwünschten `5000 → 0`-Roundtrips über einen ausreichend langen Realzeitraum;
- Master bleibt während Installation und Prüfung ausgeschaltet und wird erst nach erfolgreicher Abnahme aktiviert.
