# Deep Testbench und GitHub Codespaces

## Ziel

Der Deep Testbench prüft den SolarEdge HA Energy Controller außerhalb einer realen Anlage. Er bildet die Betriebslogik der Referenzinstallation mit neutralen Testdaten nach und ergänzt die bestehenden Release-, Installer- und Paritätstests.

Die Testumgebung verbindet fünf Ebenen:

1. statische Architektur- und Datenschutzprüfungen;
2. ein unabhängiges Python-Referenzmodell;
3. feste Tag-/Nacht-/PV-/SoC-/Forecast-Szenarien;
4. Property- und Fake-Time-Zustandsmaschinentests;
5. einen Home-Assistant-Container-Smoke-Test und das tatsächliche Release-ZIP.

Es wird niemals eine Verbindung zur produktiven SolarEdge- oder Home-Assistant-Instanz hergestellt.

## Warum Codespaces?

Die Datei `.devcontainer/devcontainer.json` legt Python, Docker, ShellCheck, YAML-Unterstützung und VS-Code-Erweiterungen fest. Dadurch verwenden Codespaces und lokale Dev-Container dieselbe Werkzeugbasis. GitHub Actions führt dieselben Einstiegsskripte aus.

## Codespace öffnen

1. Repository öffnen.
2. **Code → Codespaces → Create codespace on main** wählen.
3. Warten, bis `postCreateCommand` abgeschlossen ist.
4. Im Terminal ausführen:

```bash
bash scripts/run_deep_tests.sh all
```

Für den Home-Assistant-Container-Smoke-Test:

```bash
bash scripts/run_ha_smoke.sh
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

## Testdaten

Die Datei `tests/fixtures/controller_scenarios.yaml` enthält feste, künstliche Szenarien für:

- Eigenverbrauch maximieren;
- Netzdienlich laden;
- Akku schonen;
- EVOpt optimiert;
- Master aus, Site nicht bestätigt, Config-/Sanity-Fehler und Risk Flag;
- Tag, Nacht, Ladefenster, niedrigen SoC und erreichtes Ziel;
- EVOpt `normal`, `holdcharge`, `hold`, `charge`, `discharge`;
- EVOpt-Startup-Hold und vollständigen Legacy-Fallback;
- Writer-Stabilität, Cooldown und identische Sollwerte.

Alle Werte sind synthetisch. Die verwendete neutrale Referenzkapazität von `24.25 kWh` dient nur dazu, das Verhalten der geprüften Referenzinstallation nachzubilden; sie ist kein allgemeiner Standardwert.

## Referenzmodell

`testbench/reference/controller_model.py` ist absichtlich unabhängig von Home Assistant und den Jinja-Templates. Das Modell definiert:

- Safety-Gates;
- die vier Modusanforderungen;
- EVOpt-Hold und 20-Minuten-Fallback;
- restriktive und permissive Übergänge;
- 90 Sekunden Stabilität vor einer Öffnung;
- 180 Sekunden Writer-Cooldown;
- 180 Sekunden `holdcharge`-Latch;
- Mindestdifferenz und doppelte Writes;
- Fake-Time-Sequenzen und Write-Protokolle.

Das Modell ersetzt nicht die Produktivlogik. Es dient als unabhängige Sollinstanz für Tests und macht Abweichungen sichtbar.

## Property-Tests

Hypothesis erzeugt Kombinationen aus:

```text
4 Modi
SoC 0…100 %
Kapazität 0.1…100 kWh
PV und Verbrauch 0…30 kW
Prognose 0…150 kWh
EVOpt-Aktionen und Health-Zustände
Tag- und Nachtzeiten
0- und 5000-W-Ausgangszuständen
```

Zusätzlich werden ungültige Werte bis außerhalb der zulässigen Bereiche erzeugt. Globale Invarianten:

```text
0 <= Ziel <= 5000 W
Master/Site/Config/Sanity/Risk-Gate aus => kein Write
identischer Sollwert => kein Write
restriktiv => sofort
permissiv => erst nach Stabilität und Cooldown
keine NaN-/Inf-Ausgabe
keine Exception bei ungültigen Messwerten
```

## Fake-Time-Tests

`ControllerSequence` bewegt Zeit ohne reales Warten. Geprüft werden unter anderem:

- kein `0 → 5000 → 0` beim EVOpt-Startup;
- Fallback erst nach 1200 Sekunden EVOpt-Ausfall;
- zusätzliche 90 Sekunden Stabilität vor permissiver Öffnung;
- `holdcharge` bleibt 180 Sekunden gelatcht;
- restriktives Schließen ignoriert Cooldown;
- Tages-/Fensterende erzeugt genau einen Schließvorgang.

## Fake evcc

Der Server `testbench/fake_evcc/app.py` stellt `/api/state` bereit und kann während eines Tests umgeschaltet werden:

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
```

Beispiel:

```bash
python -m testbench.fake_evcc.app --port 7070 --scenario holdcharge
curl http://127.0.0.1:7070/api/state
curl -X POST http://127.0.0.1:7070/__scenario/normal
```

## Home-Assistant-Smoke-Test

`scripts/run_ha_smoke.sh`:

1. erstellt eine temporäre neutrale HA-Konfiguration;
2. installiert die echten Projektdateien mit dem portablen Installer;
3. führt `check_config` mit dem gepinnten Home-Assistant-Image `2026.7.3` aus;
4. startet denselben Stand als Container;
5. wartet auf die HTTP-Bereitschaft;
6. prüft auf fatale Konfigurations- und Watchdog-Setupfehler;
7. speichert Installer-, Check- und HA-Logs als Artefakte.

Dieser Test prüft Startbarkeit und Installation, aber keine reale SolarEdge-Modbus-Kommunikation. Firmware-, Register- und Geräteeffekte bleiben Bestandteil der kontrollierten Hardware-Abnahme.

## GitHub Actions

`.github/workflows/deep-testbench.yml` enthält getrennte Jobs:

```text
static-architecture
model-matrix-property-state
fake-evcc-api
home-assistant-2026.7.3-smoke
release-installer-rollback
deep-release-gate
```

Der abschließende Gate-Job wird nur grün, wenn alle vorherigen Stufen erfolgreich sind.

## Artefakte

Je nach Job werden hochgeladen:

```text
readonly_audit.txt
ruff.txt
*-junit.xml
scenario_report.json
coverage.xml
coverage-html/
installer.log
check-config.log
home-assistant.log
report.json
Release-ZIP und SHA256
```

## Branch Protection

Für `main` sollten mindestens diese Checks verpflichtend werden:

```text
Validate SolarEdge HA Energy Controller / validate
Deep SolarEdge Controller Testbench / static-architecture
Deep SolarEdge Controller Testbench / model-matrix-property-state
Deep SolarEdge Controller Testbench / fake-evcc-api
Deep SolarEdge Controller Testbench / home-assistant-2026.7.3-smoke
Deep SolarEdge Controller Testbench / release-installer-rollback
Deep SolarEdge Controller Testbench / deep-release-gate
```

Die Einstellung erfolgt unter **Settings → Branches → Branch protection rules**. Force-Pushes sollten blockiert bleiben.

## Grenzen

Der Deep Testbench kann nicht beweisen, dass jede SolarEdge-Firmware Register identisch behandelt. Nicht simuliert werden:

- physische Modbus-Latenz und Paketverlust;
- gerätespezifische Flash-Persistenz;
- Wechselrichter-/Batterie-Firmwareabweichungen;
- reale Messwertverzögerungen anderer Integrationen;
- Netz- und Hardwareausfälle außerhalb der definierten Fehlerbilder.

Dafür bleibt der dokumentierte Hardware-Abnahmetest erforderlich.
