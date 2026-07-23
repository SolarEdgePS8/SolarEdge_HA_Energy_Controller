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

Der Stand ab Commit `205c5e8` schützt die reale SolarEdge-Schreibstelle zusätzlich gegen kurze oder widersprüchliche Freigaben.

### Restriktiv: sofort

Bei aktivem Modus `EVOpt optimiert` verhindert jedes dieser Signale einen permissiven `5000-W`-Write:

```text
sensor.se_nf_evopt_action_raw = holdcharge
sensor.se_nf_evopt_action_stable = holdcharge
binary_sensor.se_nf_evopt_charge_block_request = on
```

Das gilt ausdrücklich auch dann, wenn Config, Sanity oder ein anderer Safety-Pfad gleichzeitig Fail-open anfordert. Ein restriktiver Wechsel auf `0 W` bleibt dagegen sofort zulässig.

### Permissiv: zweifach stabilisiert

Eine EVOpt-Freigabe auf `5000 W` benötigt:

1. mindestens **20 Minuten** durchgehend nicht-restriktive EVOpt-Rohaktion;
2. zusätzlich mindestens **90 Sekunden** stabilen finalen Sollwert.

Der vorgelagerte Charge-Block besitzt weiterhin eine kurze Entprellung. Er allein entscheidet aber nicht mehr über die SolarEdge-Freigabe. Unmittelbar vor dem einzigen `number.set_value`-Aufruf prüft der Writer alle drei restriktiven EVOpt-Signale erneut.

### Startup und Fallback

- Während EVOpt nach einem Neustart aufwärmt, wird der zuletzt bestätigte SolarEdge-Zustand gehalten.
- Ein vollständiger Legacy-Fallback wird erst nach 20 Minuten durchgehendem EVOpt-Ausfall permissiv.
- Auch der Fallback darf eine noch eindeutige `holdcharge`-Sperre nicht umgehen.
- Ohne aktives restriktives EVOpt-Signal bleibt ein echter Emergency-Fail-open möglich.

Damit wird der live beobachtete Fehlerfall verhindert:

```text
Wert=5000 raw=holdcharge stable=holdcharge block=on
Wert=0    raw=holdcharge stable=holdcharge block=on
```

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

Zusätzlich immer kritisch:

```text
requested_value = 5000
raw = holdcharge
```

oder

```text
requested_value = 5000
stable = holdcharge
```

oder

```text
requested_value = 5000
block = on
```

Ein einzelner Wechsel `0 ↔ 5000` ist nur dann normal, wenn sich die stabile EVOpt-Aktion tatsächlich und ausreichend lange geändert hat.

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
