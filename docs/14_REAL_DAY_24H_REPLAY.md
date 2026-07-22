# Reproduzierbarer 24-Stunden-Test aus Messdaten

## Ziel

Dieser Test spielt einen vollständigen, anonymisierten Energie-Tag in 15-Minuten-Schritten durch alle vier Betriebsarten des SolarEdge HA Energy Controllers. Dabei werden sowohl das unabhängige Referenzmodell als auch die unveränderten produktiven Home-Assistant-Packages geprüft.

Die Testumgebung verbindet sich niemals mit einer produktiven Home-Assistant-, evcc- oder SolarEdge-Instanz. Das Writer-Ziel ist ausschließlich:

```text
number.test_storage_charge_limit
```

## Messdatensatz

Die Fixture liegt unter:

```text
testbench/fixtures/real_day_2026-07-21_15m.json
```

Sie enthält 96 Viertelstundenwerte mit:

```text
PV-Erzeugung:          43,62 kWh
Hausverbrauch:         11,96 kWh
Netzbezug:              0,07 kWh
Netzeinspeisung:       29,87 kWh
Batterieladung:         6,22 kWh
Batterieentladung:      4,27 kWh
Batteriekapazität:     24,30 kWh
Zeitschritt:           15 Minuten
```

PV, Last, Netz- und Batteriefluss beruhen auf einem gemessenen Tag. Rohdateinamen, private IP-Adressen, Entity-IDs, Seriennummern, Tokens und Kontodaten wurden nicht übernommen.

Der vorhandene evcc-Trace deckt nur einen kurzen Ausschnitt ab. Deshalb ist die EVOpt-Aktionsfolge eine ausdrücklich gekennzeichnete Fehler- und Zustandsinjektion auf den realen Messwerten. Sie umfasst `normal`, `holdcharge`, `charge`, `discharge`, `hold`, einen API-Ausfall sowie Recovery.

## Vier vollständige Tagesläufe

Jeder Modus erhält denselben 24-Stunden-Datensatz:

1. Eigenverbrauch maximieren
2. Netzdienlich laden
3. Akku schonen
4. EVOpt optimiert

Damit entstehen pro Ausführung:

```text
96 Slots × 4 Modi = 384 Controller-Snapshots
```

## Unabhängiges Referenzmodell

```bash
python -m testbench.day_replay \
  --fixture testbench/fixtures/real_day_2026-07-21_15m.json \
  --output-dir artifacts/real-day-24h-model
```

Das Modell prüft unter anderem:

- vollständige und monotone Zeitreihe;
- Energie-Bilanz jedes Slots;
- Wertebereich 0 bis 5000 W;
- Writer-Stabilität und Cooldown;
- doppelte Writes;
- 0→5000→0- und 5000→0→5000-Rundläufe;
- EVOpt-Hold, Fallback und Recovery;
- maximale Writer-Anzahl je Betriebsart.

## Home-Assistant-Runtime-Replay

```bash
bash scripts/run_ha_24h_replay.sh
```

Der Runner:

1. erstellt eine neutrale Home-Assistant-Konfiguration;
2. installiert die 18 produktiven Packages mit dem normalen Installer;
3. führt `check_config` mit Home Assistant 2026.7.3 aus;
4. startet Home Assistant ohne physische Integrationen;
5. injiziert den gemessenen Tag über synthetische Test-Entities;
6. simuliert alle vier Betriebsarten;
7. schaltet den Master nach dem Test wieder aus;
8. wertet Writer, Events, Zustandswechsel und Konflikte aus.

Die vier Modusläufe verwenden aufeinanderfolgende simulierte Kalendertage. Zeit läuft daher niemals rückwärts. Innerhalb jedes Viertelstunden-Slots werden zusätzliche Zeitpunkte erzeugt, damit 60-, 90-, 120- und 180-Sekunden-Gates ohne reales Warten ausgelöst werden.

## Trace und Debugging

Der Runtime-Test erzeugt:

```text
summary.json
snapshots.jsonl
events.jsonl
write_intents.jsonl
actual_changes.jsonl
home-assistant.log
check-config.log
installer.log
```

Jeder Snapshot enthält unter anderem:

- simulierte Zeit und Slot;
- PV-Leistung, Hausverbrauch und Batterie-SoC;
- Prognoserest und EVOpt-Aktion;
- gewählten und effektiven Modus;
- Session-State und aktive Steuerung;
- Soll- und Ist-Charge-Limit;
- Entscheidungsgrund und Writer-Modus;
- Config-, Sanity- und Risk-Status;
- EVOpt-Status, Charge-Block, Fallback-Code, Kandidatenquelle und Kandidatenziel.

## Konfliktklassifizierung

Harte Fehler sind insbesondere:

- weniger oder mehr als 96 Slots je Modus;
- Charge-Limit außerhalb 0 bis 5000 W;
- Config-/Sanity-Fehler oder aktives Risk-Flag;
- `holdcharge` bei weiterhin offenem Charge-Limit;
- unbekannter Writer;
- nicht klassifizierter schneller Roundtrip;
- Controller-Master nach Testende weiterhin an.

Fachlich erwartete Abweichungen werden separat gespeichert und führen nicht automatisch zu einem PASS. Sie müssen im Report begründet sein. Ein Beispiel ist `discharge`: Der aktuelle Charge-Arbiter kann keine Entladeleistung schreiben und muss deshalb auf die dokumentierte vorhandene Steuerungsmöglichkeit zurückfallen.

## Prüfung gegen Main

Der GitHub-Actions-Job heißt:

```text
main-production-real-day-24h
```

Vor dem Replay prüft der Workflow per Git-Diff, dass gegenüber `main` folgende produktive Bereiche unverändert sind:

```text
package/
custom_components/se_write_watchdog/
scripts/install_package.sh
scripts/runtime/
audit/runtime/
```

Der 24-Stunden-Lauf testet somit den tatsächlichen Main-Produktionscode und keine für den Test angepasste Controller-Variante.

## Vergleichbare Projekte

Vor der Umsetzung wurden Testmuster aus EMHASS, OpenEMS, Akkudoktor EOS und evcc untersucht. Es wurde kein fremder Programmcode kopiert. Übernommen wurden nur allgemeine Verfahren:

- feste Uhr und reproduzierbare Simulation;
- Viertelstunden-Horizonte für PV, Last, Preise und SoC;
- explizite Zeitstempel-, Mitternachts- und Tageswechseltests;
- Energie-Bilanz je Zeitintervall;
- getrennte Entscheidungs-, Event- und Konflikttraces.

## Grenzen

Nicht simuliert werden:

- physische Modbus-Latenzen und Paketverlust;
- SolarEdge-Firmware- und Registerabweichungen;
- gerätespezifische Flash-Persistenz;
- reale Messwertverzögerungen externer Integrationen;
- ein vollständiger produktiver EVOpt-Tag;
- Hardware- und Netzfehler außerhalb der injizierten Fehlerbilder.

Diese Punkte bleiben Bestandteil der kontrollierten Hardware-Abnahme.
