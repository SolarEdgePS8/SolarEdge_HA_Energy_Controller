# Erstinstallation

Diese Anleitung gilt für eine Anlage, auf der der SolarEdge HA Energy Controller noch nicht installiert ist. Für eine bestehende Installation ausschließlich die [Update-Anleitung](05_UPDATE.md) verwenden.

## 1. Voraussetzungen

Vor Beginn müssen erfüllt sein:

- vollständiges Home-Assistant-Backup;
- Terminal-/SSH-Zugriff auf `/share` und `/config`;
- aktivierte Packages;
- bekannte SolarEdge-Ziel-Entities und Pflichtsensoren;
- keine ungeklärte zweite Automation auf demselben Charge-Limit.

Packages müssen eingebunden sein:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Danach:

```bash
ha core check
```

## 2. Release-Dateien nach `/share` kopieren

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
```

## 3. Prüfsumme kontrollieren

```bash
cd /share
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
```

Erwartet:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip: OK
```

Bei `FAILED` nicht installieren.

## 4. In einen leeren Ordner entpacken

```bash
rm -rf /share/se_controller_release_rc4
mkdir -p /share/se_controller_release_rc4
unzip -q /share/SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip \
  -d /share/se_controller_release_rc4
cd /share/se_controller_release_rc4/SolarEdge_HA_Energy_Controller
```

## 5. Installieren

```bash
bash scripts/install_package.sh
```

Der Installer:

- schaltet bei einer bestehenden Installation zuerst den Controller-Master aus;
- erstellt ein dateibezogenes Backup unter `/share/se_controller_backup_<Zeitstempel>`;
- kopiert 18 Package-YAMLs nach `/config/packages`;
- kopiert fünf Runtime-/Audit-Dateien nach `/config`;
- installiert den read-only Write-Watchdog unter `/config/custom_components/se_write_watchdog`;
- installiert Bericht und Live-Trace unter `/config/se_write_watchdog_tools`;
- ergänzt `se_write_watchdog:` genau einmal in `/config/configuration.yaml`;
- erzeugt ein Runtime-Manifest mit 28 projektverwalteten Dateien;
- führt `ha core check` aus;
- rollt bei einem Fehler alle geänderten Dateien einschließlich `configuration.yaml` zurück;
- lässt den Controller-Master ausgeschaltet.

Erwartetes Ende:

```text
Installationsdateien und Home-Assistant-Konfiguration geprüft.
Installiert: 18 Package-Dateien, 5 Runtime-/Audit-Dateien, 3 Watchdog-Dateien und 2 Watchdog-Tools.
Controller-Master bleibt AUS.
```

Private Packages und Automationen werden nicht gelöscht.

## 6. Home Assistant neu starten

```bash
ha core restart
```

Direkt nach dem Neustart können Template- oder Command-Line-Sensoren kurz `unknown`, `unavailable` oder `warming_up` melden.

## 7. Standortkonfiguration erstellen

```bash
cp config/site_config.env.example config/site_config.env
```

Pflichtfelder eintragen:

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

- Charge-Limit muss ein schreibbares `number.*` in Watt sein;
- Live-PV und Verbrauch erwarten Leistung in **W**, keine Energiezähler in `kWh`;
- `_filtered` ist nur ein möglicher Sensorname und keine Voraussetzung;
- optionale Writer-Mappings bleiben leer, wenn sie nicht verwendet werden.

### EVOpt optional aktivieren

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://evcc-host:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
EVOPT_BATTERY_MODE_ENTITY=
```

Die Basis-URL endet nicht auf `/api` und nicht auf `/api/state`.

Prüfung:

```bash
curl -fsS http://evcc-host:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

## 8. Standort bestätigen und anwenden

Erst nach vollständiger Prüfung setzen:

```dotenv
SITE_CONFIG_CONFIRMED=YES
```

Dann:

```bash
python3 scripts/apply_site_config.py config/site_config.env
```

Der Master bleibt dabei aus.

## 9. Erstprüfung

```bash
bash scripts/run_first_checks.sh
```

Erwartet:

```text
[OK] Runtime-Manifest Version: 0.1.0-rc.4
[OK] Installierte Dateien unverändert: {'checked': 28, 'errors': []}
[OK] Standortkonfiguration bestätigt: on
[OK] Config Check: ok
[OK] Sanity Check: ok
FEHLER=0 WARNUNGEN=0 PASS=True
```

Bei `PASS=False` den Master nicht einschalten.

## 10. Modus wählen

```text
Eigenverbrauch maximieren
Netzdienlich laden
Akku schonen
EVOpt optimiert
```

Im Modus EVOpt nach dem Warm-up prüfen:

```text
sensor.se_nf_evopt_status = healthy
binary_sensor.se_nf_evopt_active_control = on
sensor.se_nf_evopt_candidate_source = evopt
```

Während des Start-Warm-ups hält RC4 den zuletzt bestätigten SolarEdge-Zustand. Es wird nicht vorzeitig auf `5000 W` geöffnet.

## 11. Master einschalten

Erst nach `PASS=True`:

```text
input_boolean.se_netzdienlich_enabled = on
```

Kontrollieren:

```text
input_boolean.se_nf_site_config_confirmed = on
sensor.se_nf_config_check = ok
sensor.se_nf_sanity_check = ok
binary_sensor.se_nf_controller_write_enabled = on
```

## 12. Watchdog prüfen

```bash
/config/se_write_watchdog_tools/report.sh 200
```

Erwartet:

```text
possible writers = 1
unexpected writer = 0
roundtrips = 0
evopt mismatch = 0
```

Details: [Write-Watchdog](10_WRITE_WATCHDOG.md).

## 13. Rollback

```bash
bash scripts/rollback.sh "$(cat /share/se_controller_last_backup.txt)"
ha core restart
```

Der Rollback stellt ersetzte Dateien wieder her, entfernt neu angelegte Projektdateien, stellt `configuration.yaml` wieder her und lässt den Master ausgeschaltet.
