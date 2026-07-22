# Update einer bestehenden Installation

Diese Anleitung gilt, wenn bereits eine Version des SolarEdge HA Energy Controllers installiert ist.

## 1. Ausgangszustand sichern

Vor dem Update notieren:

```text
input_boolean.se_netzdienlich_enabled
input_boolean.se_nf_site_config_confirmed
input_select.se_nf_optimization_mode
sensor.se_nf_config_check
sensor.se_nf_sanity_check
sensor.se_nf_desired_target
sensor.se_nf_charge_limit_actual
sensor.se_nf_evopt_status
binary_sensor.se_nf_evopt_active_control
```

Zusätzlich ein vollständiges Home-Assistant-Backup erstellen und `config/site_config.env` sichern:

```bash
cp config/site_config.env /share/se_controller_site_config.env.backup
```

## 2. RC4 herunterladen und prüfen

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
```

```bash
cd /share
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
rm -rf /share/se_controller_update_rc4
mkdir -p /share/se_controller_update_rc4
unzip -q /share/SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip \
  -d /share/se_controller_update_rc4
cd /share/se_controller_update_rc4/SolarEdge_HA_Energy_Controller
```

## 3. Site-Konfiguration übernehmen

```bash
cp /share/se_controller_site_config.env.backup config/site_config.env
```

Kontrollieren:

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://evcc-host:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
SITE_CONFIG_CONFIRMED=YES
```

## 4. Master ausschalten

Vor dem Update:

```text
input_boolean.se_netzdienlich_enabled = off
```

Der Installer prüft das ebenfalls und bricht ohne bestätigten sicheren Zustand ab.

## 5. Update installieren

```bash
bash scripts/update_package.sh
```

RC4 aktualisiert:

- `se_controller_00_core.yaml`;
- `se_controller_50_mode_evopt.yaml`;
- `se_controller_80_charge_writer.yaml`;
- Runtime- und Audit-Dateien;
- Write-Watchdog `1.0.2` und Terminal-Tools;
- Runtime-Manifest.

Der Installer sichert alle ersetzten Dateien und `configuration.yaml`, führt `ha core check` aus und rollt bei einem Fehler automatisch zurück.

## 6. Neustart und Site-Konfiguration

```bash
ha core restart
python3 scripts/apply_site_config.py config/site_config.env
bash scripts/run_first_checks.sh
```

Erwartet:

```text
[OK] Runtime-Manifest Version: 0.1.0-rc.4
[OK] Installierte Dateien unverändert: {'checked': 28, 'errors': []}
FEHLER=0 WARNUNGEN=0 PASS=True
```

## 7. Was sich bei EVOpt ändert

RC4 verwendet folgende Übergangsregeln:

- `holdcharge` sperrt sofort;
- der Sperr-Latch bleibt 180 Sekunden aktiv;
- eine Öffnung auf `5000 W` benötigt 90 Sekunden stabilen finalen Sollwert;
- während EVOpt nach einem Neustart aufwärmt, wird der zuletzt bestätigte SolarEdge-Zustand gehalten;
- erst nach 20 Minuten durchgehendem EVOpt-Ausfall übernimmt der vollständige Legacy-Fallback permissiv;
- Safety-Fehler behalten Vorrang.

Dadurch wird der bisher mögliche Startup-Zyklus `0 → 5000 → 0` vermieden.

## 8. Master wieder einschalten

Nur nach `PASS=True`:

```text
input_boolean.se_netzdienlich_enabled = on
```

Im EVOpt-Modus nach dem Warm-up:

```text
sensor.se_nf_evopt_status = healthy
binary_sensor.se_nf_evopt_active_control = on
sensor.se_nf_evopt_candidate_source = evopt
```

## 9. Watchdog prüfen

```bash
/config/se_write_watchdog_tools/report.sh 300
```

Kritisch sind:

```text
unexpected_writer
roundtrip_detected: true
evopt_mismatch
duplicate: true
```

Ein einzelner Wechsel `0 ↔ 5000` ist normal, wenn sich die stabile EVOpt-Aktion tatsächlich ändert.

## 10. Installierte Version prüfen

```bash
cat /config/.se_controller_runtime_manifest.json
```

Erwartet:

```json
{
  "project": "SolarEdge_HA_Energy_Controller",
  "version": "0.1.0-rc.4",
  "source_commit": "<GitHub-Commit>",
  "installed_files": {
    "...": "..."
  }
}
```

`installed_files` enthält 28 Einträge.

## 11. Rollback

```bash
bash scripts/rollback.sh "$(cat /share/se_controller_last_backup.txt)"
ha core restart
```

Danach die zur alten Version gehörende Site-Konfiguration anwenden und deren Prüfungen ausführen.
