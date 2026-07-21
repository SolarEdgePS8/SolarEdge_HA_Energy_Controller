# Update einer bestehenden Installation

Diese Anleitung gilt, wenn bereits eine Version des SolarEdge HA Energy Controllers installiert ist. Für eine neue Anlage die [Erstinstallation](02_FIRST_INSTALL.md) verwenden.

## 1. Ausgangszustand dokumentieren

Vor dem Update in Home Assistant notieren oder als Screenshot sichern:

```text
input_boolean.se_netzdienlich_enabled
input_boolean.se_nf_site_config_confirmed
input_select.se_nf_optimization_mode
sensor.se_nf_config_check
sensor.se_nf_sanity_check
sensor.se_nf_desired_target
sensor.se_nf_charge_limit_actual
```

Bei EVOpt zusätzlich:

```text
sensor.se_nf_evopt_status
binary_sensor.se_nf_evopt_active_control
sensor.se_nf_active_control_label
```

## 2. Vollständiges Home-Assistant-Backup erstellen

Das dateibezogene Installer-Backup ersetzt kein vollständiges Home-Assistant-Backup. Vor jedem Versionswechsel ein vollständiges HA-Backup erstellen.

## 3. Private Site-Konfiguration sichern

Die Datei `config/site_config.env` liegt im bisherigen Release-Ordner und gehört nicht zum GitHub-Release. Vor dem Löschen oder Überschreiben dieses Ordners separat sichern.

Aus dem bisherigen Release-Ordner:

```bash
cp config/site_config.env /share/se_controller_site_config.env.backup
```

Prüfen:

```bash
test -s /share/se_controller_site_config.env.backup \
  && echo SITE_CONFIG_BACKUP=OK
```

Erwartet:

```text
SITE_CONFIG_BACKUP=OK
```

## 4. Neues Release und Prüfsumme herunterladen

Für RC3 werden benötigt:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
```

Beide Dateien nach `/share` kopieren.

## 5. ZIP-Prüfsumme kontrollieren

```bash
cd /share
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
```

Erwartet:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip: OK
```

Bei einer abweichenden Prüfsumme nicht fortfahren.

## 6. Neues Release in einen leeren Ordner entpacken

Nicht in den alten Release-Ordner entpacken. Sonst können veraltete Dateien im Arbeitsverzeichnis verbleiben.

```bash
rm -rf /share/se_controller_update_rc3
mkdir -p /share/se_controller_update_rc3
unzip -q /share/SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip \
  -d /share/se_controller_update_rc3
cd /share/se_controller_update_rc3/SolarEdge_HA_Energy_Controller
```

## 7. Site-Konfiguration in das neue Release übernehmen

```bash
cp /share/se_controller_site_config.env.backup config/site_config.env
```

Die Datei prüfen. Neue Felder aus `config/site_config.env.example` bei Bedarf ergänzen. Nicht verwendete optionale Felder bleiben leer.

Für RC3 insbesondere kontrollieren:

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://homeassistant.local:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
SITE_CONFIG_CONFIRMED=YES
```

Die EVOpt-Basis-URL enthält nicht `/api` und nicht `/api/state`.

## 8. Controller-Master ausschalten

Vor dem Update in Home Assistant:

```text
input_boolean.se_netzdienlich_enabled = off
```

Der Update-Installer schaltet den Master ebenfalls aus. Die manuelle Kontrolle verhindert jedoch, dass während der Vorbereitung noch Schreibzugriffe stattfinden.

## 9. Update installieren

```bash
bash scripts/update_package.sh
```

Das Update verwendet denselben sicheren Installer wie die Erstinstallation:

- dateibezogenes Backup unter `/share/se_controller_backup_<Zeitstempel>`;
- Austausch ausschließlich der Controller-Dateien;
- Runtime-Manifest mit Release-Version und Quellcommit;
- `ha core check`;
- automatischer Rollback bei einem Installationsfehler;
- Controller-Master bleibt aus.

Erwartetes Ende:

```text
Installationsdateien und HA-Konfiguration geprüft.
Controller-Master bleibt AUS.
Update-Dateien installiert. Nach Neustart bleibt der Controller-Master AUS.
```

## 10. Home Assistant neu starten

```bash
ha core restart
```

Warten, bis Oberfläche und API wieder erreichbar sind.

## 11. Standortkonfiguration erneut anwenden

```bash
python3 scripts/apply_site_config.py config/site_config.env
```

Erwartet:

```text
Site-Konfiguration angewendet. Standort bestätigt; Controller-Master bleibt AUS.
```

Bestehende Helper-Zustände bleiben bei einem normalen Update üblicherweise erhalten. Das erneute Anwenden stellt trotzdem sicher, dass alle Mappings exakt der gesicherten Site-Konfiguration entsprechen.

## 12. Vollständige Update-Prüfung

```bash
bash scripts/run_first_checks.sh
```

Für RC3 erwartet:

```text
[OK] Runtime-Manifest Version: 0.1.0-rc.3
[OK] Installierte Dateien unverändert: {'checked': 23, 'errors': []}
[OK] Pflichtentitäten vorhanden: vollständig
[OK] Controller-Master AUS: off
[OK] Writer gesperrt: off
[OK] Standortkonfiguration bestätigt: on
[OK] Config Check: ok
[OK] Sanity Check: ok
FEHLER=0 WARNUNGEN=0 PASS=True
Erstprüfungen PASS. Controller-Master bleibt AUS.
```

Bei `PASS=False` nicht aktivieren.

## 13. Vorherigen Modus wiederherstellen

Über `input_select.se_nf_optimization_mode` den vor dem Update verwendeten Modus auswählen.

Bei EVOpt nach dem Neustart bis zu etwa zwei Minuten `warming_up` abwarten. Danach müssen gelten:

```text
sensor.se_nf_evopt_status = healthy
Attribut reason = ok
binary_sensor.se_nf_evopt_active_control = on
```

## 14. Master wieder einschalten

Erst nach erfolgreicher Prüfung:

```text
input_boolean.se_netzdienlich_enabled = on
```

Danach mindestens folgende Werte beobachten:

```text
sensor.se_nf_config_check = ok
sensor.se_nf_sanity_check = ok
binary_sensor.se_nf_risk_flag = off
binary_sensor.se_nf_controller_write_enabled = on
sensor.se_nf_desired_target = plausibler Sollwert
sensor.se_nf_charge_limit_actual = plausibler Istwert
```

## 15. Installierte Version kontrollieren

```bash
cat /config/.se_controller_runtime_manifest.json
```

Erwartet sind mindestens:

```json
{
  "project": "SolarEdge_HA_Energy_Controller",
  "version": "0.1.0-rc.3",
  "source_commit": "<GitHub-Commit des Releases>"
}
```

Die Liste `installed_files` muss 23 Einträge enthalten.

## 16. Rollback

Der letzte Installer-Backupordner steht in:

```text
/share/se_controller_last_backup.txt
```

Rollback aus dem neuen Release-Ordner:

```bash
bash scripts/rollback.sh
ha core restart
```

Der Rollback stellt die vor dem Update vorhandenen Controller-Dateien wieder her und lässt den Master ausgeschaltet. Danach die zur alten Version gehörende Site-Konfiguration anwenden und deren Prüfungen ausführen.
