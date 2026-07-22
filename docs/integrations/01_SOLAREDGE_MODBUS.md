# SolarEdge Modbus: Quelle der Batterie- und Writer-Entities

## Empfohlene Referenzintegration

Das Projekt ist nicht hart an eine einzige Integration gebunden. Die öffentliche Dokumentation verwendet jedoch [SolarEdge Modbus Multi](https://github.com/WillCodeForCats/solaredge-modbus-multi) als Referenz, weil sie Wechselrichter, Zähler, Batterien und optionale Power-Control-Entities lokal über Modbus/TCP bereitstellt.

Die genauen Entity-IDs hängen ab von:

- Name der Integrationsinstanz;
- Wechselrichterindex (`i1`, `i2`, …);
- Batterieindex (`b1`, `b2`, …);
- unterstützter Firmware und Gerätekonfiguration;
- aktivierten Integrationsoptionen;
- manuellen Entity-Umbenennungen.

Deshalb sind alle Namen in dieser Anleitung Vorschläge und müssen in Home Assistant geprüft werden.

## Typische Entities

```text
number.solaredge_i1_storage_charge_limit
number.solaredge_i1_storage_discharge_limit
number.solaredge_i1_backup_reserve
sensor.solaredge_i1_b1_state_of_energy
sensor.solaredge_i1_b1_maximum_energy
sensor.solaredge_i1_ac_power
```

| Entity-Funktion | Domain/Einheit | Controller-Mapping |
|---|---|---|
| Storage Charge Limit | `number.*`, `W` | `CHARGE_LIMIT_ENTITY` |
| Storage Discharge Limit | `number.*`, `W` | `DISCHARGE_LIMIT_ENTITY` |
| Backup Reserve | `number.*`, `%` | `BACKUP_RESERVE_ENTITY` |
| Battery State of Energy | `sensor.*`, `%` | `BATTERY_SOC_ENTITY` |
| Battery Maximum Energy | `sensor.*`, meist `kWh` | `BATTERY_CAPACITY_ENTITY` |
| Inverter AC Power | `sensor.*`, `W` | möglicher Eintrag in `LIVE_PV_POWER_ENTITIES` |

## Storage Control aktivieren

Die Integration erzeugt die Storage-Control-Entities nur, wenn die entsprechende Option aktiviert und das Gerät unterstützt wird.

In Home Assistant:

```text
Einstellungen → Geräte & Dienste → SolarEdge Modbus Multi → Konfigurieren
```

Danach:

1. Batterieerkennung kontrollieren;
2. Storage Control aktivieren;
3. Wechselrichterdaten neu laden;
4. nach „Storage Charge Limit“ suchen;
5. Domain, Einheit, Min/Max und Verfügbarkeit prüfen.

Storage Charge Limit und Storage Discharge Limit sind in der Referenzintegration nur im Storage-Control-Modus **Remote Control** verfügbar. `0 W` stoppt die jeweilige Richtung; ein größerer Wert ist ein Maximalwert und kein garantierter Leistungsbezug.

## Vorsicht bei Power Control

Die erweiterten Steueroptionen sind in SolarEdge Modbus Multi standardmäßig deaktiviert. Die Integrationsdokumentation weist darauf hin, dass nicht alle Funktionen öffentlich von SolarEdge dokumentiert oder für jede Hardware-/Firmwarekombination freigegeben sind. Änderungen können bestehende Provisionierungs- oder Netzbetreibereinstellungen beeinflussen.

Vor dem Aktivieren:

- Screenshot/Export der bisherigen Einstellungen erstellen;
- nur tatsächlich benötigte Optionen einschalten;
- keine Werte experimentell in schneller Folge ändern;
- nur einen Writer pro Ziel zulassen;
- Controller-Master zunächst AUS lassen;
- Write-Watchdog beobachten.

## Mapping-Assistent

```bash
python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

Hohe Vertrauenswerte werden insbesondere für typische Muster vergeben:

```text
number.solaredge_*_storage_charge_limit
number.solaredge_*_storage_discharge_limit
number.solaredge_*_backup_reserve
sensor.solaredge_*_b*_state_of_energy
sensor.solaredge_*_b*_maximum_energy
sensor.solaredge_*_ac_power
```

Der Assistent aktiviert keine Steuerung. Der Vorschlag muss manuell bestätigt werden.

## Manuelle Prüfung des Charge-Limits

Vor dem Controllerbetrieb:

1. aktuelle Entity öffnen;
2. aktuellen Wert und Einheit notieren;
3. Min-/Max-Bereich prüfen;
4. nur in einem sicheren Anlagenzustand einen einzelnen Testwert setzen;
5. Rückmeldung abwarten;
6. ursprünglichen Wert wiederherstellen;
7. Logbuch auf den verursachenden Benutzer/Service prüfen.

Der Controller selbst verwendet Mindestdifferenz, Cooldown, Stabilisierung und einen zentralen Writer. Diese Mechanismen ersetzen keine korrekte Anlagenkonfiguration.

## Andere SolarEdge-Integrationen

Eine andere Integration kann verwendet werden, wenn sie mindestens bietet:

- zuverlässige lokale oder ausreichend aktuelle Zustände;
- schreibbares Charge-Limit als `number.*` in `W`;
- Batterie-Ladestand in `%`;
- nachvollziehbare Einheiten;
- eindeutige Writer-Eigentümerschaft.

Eine Entity mit ähnlich klingendem Namen ist nicht automatisch semantisch gleich. Besonders `AC Charge Limit` in `kWh` oder `%` ist **nicht** dasselbe wie das Storage Charge Limit in `W`.
