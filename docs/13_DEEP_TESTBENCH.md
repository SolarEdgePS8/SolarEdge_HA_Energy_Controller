# Deep Testbench und GitHub Codespaces

## Ziel

Der Deep Testbench prüft den SolarEdge HA Energy Controller außerhalb einer realen Anlage. Er bildet die Betriebslogik der Referenzinstallation mit neutralen Testdaten nach und ergänzt die bestehenden Release-, Installer- und Paritätstests.

Die Testumgebung verbindet sechs Ebenen:

1. statische Architektur-, Syntax- und Datenschutzprüfungen;
2. ein unabhängiges Python-Referenzmodell;
3. feste Tag-/Nacht-/PV-/SoC-/Forecast-Szenarien;
4. Property-, Grenzwert- und Fake-Time-Zustandsmaschinentests;
5. einen umschaltbaren Fake-evcc-Server;
6. einen Home-Assistant-Container-Test sowie das tatsächliche Release-ZIP.

Es wird niemals eine Verbindung zur produktiven SolarEdge- oder Home-Assistant-Instanz hergestellt.

## Warum Codespaces?

Die Datei `.devcontainer/devcontainer.json` legt Python, Docker, ShellCheck, YAML-Unterstützung und VS-Code-Erweiterungen fest. Dadurch verwenden Codespaces und lokale Dev-Container dieselbe Werkzeugbasis. GitHub Actions führt dieselben Einstiegsskripte aus.

## Codespace öffnen

1. Repository oder den Test-Branch öffnen.
2. **Code → Codespaces → Create codespace** wählen.
3. Warten, bis `postCreateCommand` abgeschlossen ist.
4. Im Terminal ausführen:

```bash
bash scripts/run_deep_tests.sh all
```

Für den vollständigen Home-Assistant-Container-Test:

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

Die Datei `tests/fixtures/controller_scenarios.yaml` enthält 29 feste, künstliche Szenarien für:

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

Zusätzlich prüft `tests/deep/test_cross_mode_matrix.py` 9.600 deterministische Snapshots aus:

```text
4 Betriebsarten
× 4 Tageszeiten
× 6 SoC-Stufen
× 5 PV-Leistungsstufen
× 4 Verbrauchsstufen
× 4 Prognosestufen
× EVOpt normal/holdcharge im EVOpt-Modus
```

Eine weitere Sequenz schaltet alle vier Modi nacheinander um und erwartet ausschließlich die kontrollierte synthetische Write-Folge:

```text
5000 W → 0 W → 5000 W → 0 W
```

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
SoC innerhalb und außerhalb 0…100 %
Kapazität innerhalb und außerhalb gültiger Bereiche
PV und Verbrauch bis 30 kW
Prognosen bis 150 kWh und ungültige negative Werte
EVOpt-Aktionen und Health-Zustände
Tag- und Nachtzeiten
0- und 5000-W-Ausgangszuständen
```

Globale Invarianten:

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
- Tages-/Fensterende erzeugt genau einen Schließvorgang;
- Recovery nach EVOpt-Ausfall;
- Moduswechsel während einer laufenden Write-Sequenz.

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
http_404
http_500
timeout
```

Beispiel:

```bash
python -m testbench.fake_evcc.app --port 7070 --scenario holdcharge
curl http://127.0.0.1:7070/api/state
curl -X POST http://127.0.0.1:7070/__scenario/normal
```

## Home-Assistant-Container-Test

`scripts/run_ha_smoke.sh`:

1. erstellt eine temporäre neutrale HA-Konfiguration;
2. installiert die echten Projektdateien mit dem portablen Installer;
3. ergänzt ausschließlich für den Test eine synthetische Runtime-Datei;
4. führt `check_config` mit dem gepinnten Home-Assistant-Image `2026.7.3` aus;
5. startet denselben Stand als Container;
6. mappt Batterie, PV, Verbrauch, Prognose und Charge-Limit auf synthetische Entities;
7. schaltet alle vier Betriebsarten in der echten Home-Assistant-Package-Laufzeit um;
8. prüft `config_check=ok`, `sanity_check=ok` und einen nach dem Test ausgeschalteten Master;
9. speichert Installer-, Check-, Home-Assistant- und Ergebnislogs als Artefakte.

Die synthetische Writer-Entity lautet:

```text
number.test_storage_charge_limit
```

Sie hat keine Verbindung zu Modbus oder realer Hardware.

Der erfolgreiche Referenzlauf vom 22.07.2026 ergab:

| Modus | effektiver Modus | aktive Steuerung | Ziel |
|---|---|---|---:|
| Eigenverbrauch maximieren | Eigenverbrauch maximieren | Eigenverbrauch | 5000 W |
| Netzdienlich laden | Netzdienlich laden | Netzdienliche Planung | 0 W |
| Akku schonen | Akku schonen | Akku schonen | 0 W |
| EVOpt optimiert | EVOpt optimiert | Netzdienlicher Fallback | 0 W |

EVOpt läuft in diesem Container bewusst ohne externe API-Verbindung und muss deshalb sauber auf die netzdienliche Ersatzplanung zurückfallen. Die echte EVOpt-Aktionsmatrix wird separat gegen den Fake-evcc-Server und im Referenzmodell geprüft.

Dieser Test prüft die tatsächliche Home-Assistant-Konfiguration, Entity-Erzeugung, Modusumschaltung und Controller-Arbitration. Er prüft keine reale SolarEdge-Modbus-Kommunikation. Firmware-, Register- und Geräteeffekte bleiben Bestandteil der kontrollierten Hardware-Abnahme.

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

## Verifizierter Teststand

Für den geprüften Pull-Request-Stand waren erfolgreich:

```text
29 / 29 feste Szenarien
9.600 deterministische Vier-Modi-Snapshots
52 Python-Modell-, Property- und Zustandsmaschinentests
98,06 % Line-Coverage des unabhängigen Referenzmodells
alle Fake-evcc-Aktionen und Transportfehler
Home Assistant 2026.7.3 check_config und Runtime-Start
alle vier Modi in der HA-Package-Laufzeit umgeschaltet
Config Check: ok
Sanity Check: ok
Master nach dem Test: aus
Release-ZIP, SHA256 und Manifest: PASS
Deep Release Gate: PASS
```

## Artefakte

Je nach Job werden hochgeladen:

```text
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
- reale EVOpt-Pläne mit der produktiven evcc-Instanz;
- Netz- und Hardwareausfälle außerhalb der definierten Fehlerbilder.

Dafür bleibt der dokumentierte Hardware-Abnahmetest erforderlich.
