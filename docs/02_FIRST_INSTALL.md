# Erstinstallation – geführter Ablauf

Diese Anleitung gilt für eine Anlage, auf der der SolarEdge HA Energy Controller noch nicht installiert ist. Bestehende Nutzer verwenden [Update](05_UPDATE.md) oder [Migration](06_MIGRATION.md).

## Was der Installer macht – und was nicht

Der Installer:

- kopiert die 18 Controller-Packages und die Runtime-/Diagnosedateien;
- installiert den read-only Write-Watchdog;
- erstellt ein dateibezogenes Backup;
- ergänzt den Watchdog-Konfigurationsblock genau einmal;
- führt die Home-Assistant-Konfigurationsprüfung aus;
- rollt bei einem Fehler automatisch zurück.

Der Installer:

- sucht nicht eigenmächtig die „richtige“ Anlage aus;
- trägt keine bestätigte Standortkonfiguration ein;
- aktiviert weder EVOpt noch den Controller-Master;
- installiert keine Wetter-, Forecast-, evcc- oder Strompreis-Integration;
- überschreibt keine privaten Automationen außerhalb der Projektdateien.

## 1. Voraussetzungen

- vollständiges Home-Assistant-Backup;
- Zugriff auf `/config` und ein Backup-Verzeichnis, bei OS/Supervised `/share`;
- Packages aktiviert:

  ```yaml
  homeassistant:
    packages: !include_dir_named packages
  ```

- SolarEdge-Modbus-Integration verbunden;
- Charge-Limit-Entity vorhanden und noch nicht von einer anderen Automation gesteuert;
- Pflichtdaten oder ein Plan, wie fehlende Sensoren erzeugt werden.

Details: [Voraussetzungen](01_REQUIREMENTS.md).

## 2. Release herunterladen und prüfen

Dateien nach `/share` kopieren:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
```

```bash
cd /share
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
```

Erwartet:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip: OK
```

Bei `FAILED` abbrechen.

## 3. In einen leeren Ordner entpacken

```bash
rm -rf /share/se_controller_release_rc4
mkdir -p /share/se_controller_release_rc4
unzip -q /share/SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip \
  -d /share/se_controller_release_rc4
cd /share/se_controller_release_rc4/SolarEdge_HA_Energy_Controller
```

## 4. Dateien installieren

```bash
bash scripts/install_package.sh
```

Der Installer zeigt am Ende:

- Backup-Pfad;
- Ergebnis der HA-Prüfung;
- Hinweis, dass der Master AUS bleibt;
- nächste Schritte für Mapping, Neustart und Erstprüfung.

Dann:

```bash
ha core restart
```

Andere Installationsarten: [OS, Supervised, Container und Core](09_INSTALLATION_VARIANTS.md).

## 5. Sensoren finden – read-only

Nach dem Neustart:

```bash
python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

Der Assistent liest ausschließlich HA-States. Er ändert nichts in Home Assistant. Die Datei enthält weiterhin:

```dotenv
SITE_CONFIG_CONFIRMED=NO
EVOPT_ENABLED=NO
```

Öffne anschließend:

```text
config/site_config.env
```

und prüfe jeden Vorschlag anhand der [Entity-Mapping-Anleitung](03_ENTITY_MAPPING.md) und der [Sensorquellen](12_SENSOR_SOURCES_AND_EXAMPLES.md).

## 6. Fehlende Sensoren ergänzen

Häufige Fälle:

- SolarEdge liefert Charge-Limit, Batterie-SoE und AC-Leistung direkt;
- Hausverbrauch kommt aus einem Smart Meter oder Power-Flow-Sensor;
- PV-Prognosen kommen aus Forecast.Solar, Solcast oder einem anderen Anbieter;
- „heute verbleibend“ wird aus Tagesprognose minus PV-Ertrag heute gebildet;
- Wetter kommt aus einer `weather.*`-Integration;
- evcc/ha-evcc ist nur für EVOpt beziehungsweise zusätzliche Anzeige nötig;
- Strompreis- und Kostensensoren sind optional und nicht Teil des Pflichtmappings.

Optionale YAML-Bausteine: [`examples/sensors`](../examples/sensors/README.md).

Nach jedem selbst gebauten Sensor:

```bash
ha core check
ha core restart
```

Anschließend Einheit und Aktualisierung in **Entwicklerwerkzeuge → Zustände** prüfen.

## 7. Private Standortkonfiguration bestätigen

Erst wenn alle Pflichtfelder fachlich geprüft sind:

```dotenv
SITE_CONFIG_CONFIRMED=YES
```

EVOpt bleibt zunächst aus, sofern der Optimizer noch nicht vollständig geprüft wurde:

```dotenv
EVOPT_ENABLED=NO
```

Konfiguration anwenden:

```bash
python3 scripts/apply_site_config.py config/site_config.env
```

Das Skript lässt den Controller-Master AUS.

## 8. Erste Prüfungen

```bash
bash scripts/run_first_checks.sh
python3 scripts/check_external_writer_conflicts.py "${CONFIG_ROOT:-/config}"
/config/se_write_watchdog_tools/report.sh 200
```

Erwartet:

```text
PASS=True
sensor.se_nf_config_check=ok
sensor.se_nf_sanity_check=ok
```

Jeder gemeldete fremde Writer muss vor der Aktivierung geklärt werden.

## 9. EVOpt optional aktivieren

Nur für den Modus `EVOpt optimiert`:

```bash
curl -fsS http://EVCC-HOST:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Dann Batterietitel/-name prüfen, `EVOPT_ENABLED=YES` setzen und die Standortkonfiguration erneut anwenden. Die Home-Assistant-Integration `ha-evcc` ist dafür nicht zwingend erforderlich.

## 10. Master einschalten

Erst wenn alle Prüfungen grün sind:

```text
input_boolean.se_netzdienlich_enabled → EIN
```

Danach mindestens beobachten:

```text
sensor.se_nf_active_control_label
sensor.se_nf_desired_target
sensor.se_nf_charge_limit_actual
sensor.se_write_watchdog_status
```

## 11. Rollback

Der aktuelle Backup-Pfad steht in:

```text
/share/se_controller_last_backup.txt
```

Rollback:

```bash
bash scripts/rollback.sh
```

Der Master bleibt auch nach dem Rollback AUS.
