# Erstinstallation

Diese Anleitung gilt für eine Anlage, auf der der SolarEdge HA Energy Controller noch nicht installiert ist. Für bestehende Installationen ausschließlich die [Update-Anleitung](05_UPDATE.md) verwenden.

## 1. Vorbedingungen prüfen

Vor Beginn müssen erfüllt sein:

- vollständiges Home-Assistant-Backup vorhanden;
- Terminal-/SSH-Zugriff auf `/share` und `/config`;
- Packages in `configuration.yaml` aktiviert;
- Pflichtsensoren und SolarEdge-Ziel-Entities bekannt;
- keine ungeklärte zweite Automation auf demselben SolarEdge-Charge-Limit.

Packages müssen so eingebunden sein:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Danach prüfen:

```bash
ha core check
```

Erwartet:

```text
Command completed successfully.
```

## 2. Release-Dateien nach `/share` kopieren

Benötigt werden genau diese beiden Dateien des GitHub-Prereleases:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
```

Die Dateien können beispielsweise über die Samba-Freigabe `share` nach `/share` kopiert werden.

## 3. Release-Prüfsumme verifizieren

```bash
cd /share
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
```

Erwartet:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip: OK
```

Bei `FAILED`, einer fehlenden Prüfsummendatei oder einem abweichenden Dateinamen nicht installieren. ZIP und Prüfsummendatei erneut aus demselben GitHub-Release herunterladen.

## 4. Release sauber entpacken

Für die Installation einen leeren Arbeitsordner verwenden, damit keine Dateien einer älteren Version im Release-Verzeichnis verbleiben:

```bash
rm -rf /share/se_controller_release_rc3
mkdir -p /share/se_controller_release_rc3
unzip -q /share/SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip \
  -d /share/se_controller_release_rc3
cd /share/se_controller_release_rc3/SolarEdge_HA_Energy_Controller
```

Kontrolle:

```bash
pwd
ls -la
```

Der aktuelle Ordner muss enden auf:

```text
/share/se_controller_release_rc3/SolarEdge_HA_Energy_Controller
```

## 5. Controller-Dateien installieren

```bash
bash scripts/install_package.sh
```

Der Installer:

- schaltet den Controller-Master aus;
- legt unter `/share/se_controller_backup_<Zeitstempel>` ein dateibezogenes Backup an;
- kopiert 18 YAML-Dateien nach `/config/packages`;
- kopiert fünf Runtime-/Audit-Dateien nach `/config`;
- erzeugt `/config/.se_controller_runtime_manifest.json`;
- übernimmt Version und Quellcommit aus dem Release-Manifest;
- prüft die Home-Assistant-Konfiguration mit `ha core check`;
- führt bei einem Installationsfehler automatisch den dateibezogenen Rollback aus.

Erwartetes Ende:

```text
Installationsdateien und HA-Konfiguration geprüft.
Backup: /share/se_controller_backup_...
Controller-Master bleibt AUS.
```

Fremde Packages und private Automationen werden nicht gelöscht oder deaktiviert.

## 6. Home Assistant neu starten

```bash
ha core restart
```

Warten, bis die Oberfläche und die API wieder erreichbar sind. Direkt nach dem Neustart können Command-Line-Sensoren kurz `unknown`, `unavailable` oder `warming_up` melden.

## 7. Private Standortkonfiguration anlegen

Im entpackten Release-Ordner:

```bash
cp config/site_config.env.example config/site_config.env
```

`config/site_config.env` mit File Editor, Studio Code Server oder einem Terminal-Editor bearbeiten. Diese Datei enthält lokale Entity-IDs und Adressen und darf nicht in GitHub, ein öffentliches Issue oder ein Release gelangen.

### Pflichtfelder

```dotenv
CHARGE_LIMIT_ENTITY=number.example_storage_charge_limit
BATTERY_SOC_ENTITY=sensor.example_battery_soc
BATTERY_CAPACITY_KWH=14.0
PV_FORECAST_TODAY_REMAINING_ENTITY=sensor.example_pv_today_remaining
PV_FORECAST_TODAY_TOTAL_ENTITY=sensor.example_pv_today_total
PV_FORECAST_TOMORROW_ENTITY=sensor.example_pv_tomorrow
LIVE_PV_POWER_ENTITIES=sensor.example_pv_power
LIVE_CONSUMPTION_POWER_ENTITIES=sensor.example_house_consumption_power
```

Wichtig:

- `CHARGE_LIMIT_ENTITY` muss eine schreibbare `number.*`-Entity in Watt sein;
- `LIVE_PV_POWER_ENTITIES` erwartet aktuelle Leistung in **W**, keinen Energiezähler in `kWh`;
- `LIVE_CONSUMPTION_POWER_ENTITIES` erwartet aktuelle Leistung in **W**;
- mehrere Fallbacksensoren können bei den Live-Leistungen durch Komma getrennt werden;
- ein Sensor mit Namensbestandteil `_filtered` ist optional und keine Voraussetzung.

### Optionale SolarEdge-Ziele

Diese Felder nur befüllen, wenn der Controller alleiniger Writer des jeweiligen Ziels sein soll:

```dotenv
DISCHARGE_LIMIT_ENTITY=
COMMAND_MODE_ENTITY=
COMMAND_MODE_GRID_OPTION=
COMMAND_MODE_DEFAULT_OPTION=
STORAGE_CONTROL_MODE_ENTITY=
STORAGE_CONTROL_REMOTE_OPTION=
BACKUP_RESERVE_ENTITY=
```

Nicht verwendete optionale Ziele bleiben leer.

### EVOpt optional aktivieren

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://homeassistant.local:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
EVOPT_BATTERY_MODE_ENTITY=
```

Die Basis-URL endet nicht auf `/api` und nicht auf `/api/state`. Der Adapter ergänzt den API-Pfad selbst.

Vor dem Anwenden prüfen:

```bash
curl -fsS http://homeassistant.local:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Erwartet:

```text
EVCC_API=OK True
```

## 8. Standortkonfiguration bestätigen und anwenden

Erst nachdem alle Pflichtwerte geprüft wurden, in `config/site_config.env` setzen:

```dotenv
SITE_CONFIG_CONFIRMED=YES
```

Dann ausführen:

```bash
python3 scripts/apply_site_config.py config/site_config.env
```

Erwartet:

```text
Site-Konfiguration angewendet. Standort bestätigt; Controller-Master bleibt AUS.
```

## 9. Vollständige Erstprüfung

```bash
bash scripts/run_first_checks.sh
```

Die Prüfung umfasst:

- Repository-Release-Gate;
- YAML-, Helper-, Automations- und Portabilitätsprüfung;
- `ha core check`;
- Runtime-Manifest-Version;
- SHA256 aller installierten Projektdateien;
- Pflichtentitäten;
- Site-Config, Config Check und Sanity Check;
- Writer-Sperre bei ausgeschaltetem Master;
- Mapping-Ziele;
- Konflikte mit externen Writern.

Erwartetes Ende:

```text
[OK] Runtime-Manifest Version: 0.1.0-rc.3
[OK] Installierte Dateien unverändert: {'checked': 23, 'errors': []}
[OK] Standortkonfiguration bestätigt: on
[OK] Config Check: ok
[OK] Sanity Check: ok
FEHLER=0 WARNUNGEN=0 PASS=True
Erstprüfungen PASS. Controller-Master bleibt AUS.
```

Bei `PASS=False` den Master nicht einschalten. Zuerst den genannten Fehler beheben.

## 10. Betriebsart wählen

In Home Assistant über `input_select.se_nf_optimization_mode` einen Modus wählen:

- `Eigenverbrauch maximieren`;
- `Netzdienlich laden`;
- `Akku schonen`;
- `EVOpt optimiert`.

Für EVOpt müssen zusätzlich gelten:

```text
sensor.se_nf_evopt_status = healthy
Attribut reason = ok
binary_sensor.se_nf_evopt_active_control = on
```

Nach einem Neustart ist `warming_up` für etwa zwei Minuten normal.

## 11. Controller-Master einschalten

Erst jetzt in Home Assistant einschalten:

```text
input_boolean.se_netzdienlich_enabled = on
```

Danach kontrollieren:

```text
input_boolean.se_nf_site_config_confirmed = on
sensor.se_nf_config_check = ok
sensor.se_nf_sanity_check = ok
binary_sensor.se_nf_risk_flag = off
binary_sensor.se_nf_controller_write_enabled = on
```

Im Modus EVOpt zusätzlich:

```text
sensor.se_nf_active_control_label = EVOpt
sensor.se_nf_evopt_status = healthy
binary_sensor.se_nf_evopt_active_control = on
```

`sensor.se_nf_desired_target` und `sensor.se_nf_charge_limit_actual` müssen nach Ablauf von Writer-Cooldown und Toleranz plausibel zueinander passen.

## 12. Rollback

Der letzte Backup-Ordner steht in:

```text
/share/se_controller_last_backup.txt
```

Rollback aus dem Release-Ordner:

```bash
bash scripts/rollback.sh
ha core restart
```

Der Rollback stellt ersetzte Dateien wieder her, entfernt neu angelegte Controller-Dateien und lässt den Master ausgeschaltet. Danach `ha core check` und die relevanten Entities erneut prüfen.
