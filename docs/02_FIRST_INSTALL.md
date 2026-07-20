# Erstinstallation

Diese Anleitung richtet sich an Nutzer, die den Controller erstmals installieren.

## 1. Vollständiges Backup

In Home Assistant: **Einstellungen → System → Backups → Backup erstellen**.

Zusätzlich erzeugt der Installer ein separates Dateibackup unter `/share`.

## 2. Release entpacken

```bash
cd /share
unzip SolarEdge_HA_Energy_Controller_v0.1.0-rc.2.zip
cd SolarEdge_HA_Energy_Controller
```

## 3. Package-Einbindung prüfen

In `/config/configuration.yaml` muss eine Package-Einbindung existieren:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Eine vorhandene Einbindung nicht doppelt anlegen.

## 4. Installer ausführen

```bash
bash scripts/install_package.sh
```

Der Installer:

- schaltet den Controller-Master aus;
- erstellt ein Backup unter `/share/se_controller_backup_<Zeit>`;
- kopiert ausschließlich Controllerdateien;
- erzeugt ein Runtime-Manifest;
- führt `ha core check` aus;
- führt bei einem Fehler automatisch ein Rollback durch.

## 5. Home Assistant neu starten

```bash
ha core restart
```

## 6. Passende Entities suchen

```bash
python3 scripts/discover_entities.py
```

Die Ausgabe gruppiert mögliche Kandidaten für Charge-Limit, Discharge-Limit, Command Mode, Storage Control Mode, Akku-SoE, PV-Leistung, Hausverbrauch, PV-Prognose und Wetter.

Die Vorschläge müssen fachlich geprüft werden. Ein ähnlicher Name allein reicht nicht aus.

## 7. Site-Konfiguration erstellen

```bash
cp config/site_config.env.example config/site_config.env
nano config/site_config.env
```

Zuerst alle Pflichtwerte eintragen. Optionale Funktionen können leer bleiben.

Am Ende:

```dotenv
SITE_CONFIG_CONFIRMED=YES
```

## 8. Site-Konfiguration anwenden

```bash
python3 scripts/apply_site_config.py config/site_config.env
```

Das Skript überträgt die Mappings, bestätigt die Standortkonfiguration und lässt den Master ausgeschaltet.

## 9. Erstprüfungen

```bash
bash scripts/run_first_checks.sh
```

Erwartet:

```text
Config Check: ok
Sanity Check: ok
Controller-Master: AUS
Writer gesperrt
Runtime-Manifest: PASS
Writer-Konflikte: keine
```

## 10. Modus wählen und Master aktivieren

Zunächst empfohlen: `Eigenverbrauch maximieren`.

Den Master `input_boolean.se_netzdienlich_enabled` erst einschalten, wenn alle Prüfungen erfolgreich sind.

## 11. Rückweg

```bash
bash scripts/rollback.sh "$(cat /share/se_controller_last_backup.txt)"
ha core restart
```
