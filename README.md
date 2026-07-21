# SolarEdge HA Energy Controller

Ein portabler Home-Assistant-Controller für SolarEdge-Batteriespeicher. Das Projekt trennt Planung, Sicherheitsprüfung und Schreibzugriffe in klaren Modulen und unterstützt vier Betriebsarten:

| Modus | Zweck |
|---|---|
| **Eigenverbrauch maximieren** | Akku für den normalen Eigenverbrauch freigeben |
| **Netzdienlich laden** | PV-Ladung zeitlich planen und hohe Leistungsspitzen vermeiden |
| **Akku schonen** | Ladeziel und Ladefenster aus Verbrauch, Reserve und Prognose ableiten |
| **EVOpt optimiert** | gültige Vorgaben des evcc Optimizers übernehmen; bei Fehlern vollständig auf „Netzdienlich laden“ zurückfallen |

## Status

**Version: `v0.1.0-rc.3` – Release Candidate / Prerelease**

RC3 behebt falsche EVOpt-Rückfälle an 15-Minuten-Slotwechseln. Die Suggestion des letzten Solver-Laufs wird nur verwendet, solange sie zum aktuellen Planabschnitt passt; danach ist der vollständig validierte aktuelle Slot maßgeblich.

Der Stand wurde auf einer Referenzinstallation installiert und mit folgenden Prüfungen bestätigt:

- 18 Package-YAML-Dateien und fünf Runtime-/Audit-Dateien installiert;
- `ha core check`, Config Check und Sanity Check erfolgreich;
- Runtime-Manifest und alle 23 installierten Projektdateien per SHA256 geprüft;
- reale EVOpt-Slotwechsel ohne Ausfall von `active_control` und ohne unnötigen 0/5000-W-Fallback;
- GitHub Actions mit Release-Gate, Syntax-, Vertrags-, ZIP- und Manifestprüfung.

Ein Release Candidate ist bewusst noch kein stabiler `v1.0`-Stand. Andere SolarEdge-Modelle, Integrationen und Entity-Namen müssen über das Site-Mapping angepasst und auf der jeweiligen Anlage geprüft werden.

## Was enthalten ist

- 18 Home-Assistant-Package-Dateien;
- Entity-Mapping für unterschiedliche Installationen;
- zentrale Safety- und Arbiter-Logik;
- genau ein Writer je gemapptem SolarEdge-Ziel;
- Installation, Update, Migration und vollständiger Rollback;
- Runtime-, Datei- und Konfliktprüfung;
- optionale Wetter-, SQL-, evcc- und EVOpt-Anbindung;
- Dokumentation für Erstinstallation und Update.

## Was nicht enthalten ist

Keine privaten Fahrzeug-, Wallbox-, Wärmepumpen-, Shelly-, Strompreis-, Backup-Reserve- oder Akku-Saver-Automationen. Solche Systeme können nur über neutrale optionale Eingangssignale angebunden werden.

## Schnellstart für eine Erstinstallation

Voraussetzung: Home Assistant OS oder Supervised mit Terminal-/SSH-Zugriff, aktivierten Packages und einem vollständigen Backup.

1. Die beiden Release-Dateien nach `/share` kopieren:

   ```text
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
   ```

2. Release-Prüfsumme kontrollieren und entpacken:

   ```bash
   cd /share
   sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
   unzip -q SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip
   cd /share/SolarEdge_HA_Energy_Controller
   ```

   Erwartet:

   ```text
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip: OK
   ```

3. Controller-Dateien installieren:

   ```bash
   bash scripts/install_package.sh
   ha core restart
   ```

4. Nach dem Neustart die private Standortkonfiguration erstellen:

   ```bash
   cp config/site_config.env.example config/site_config.env
   ```

   `config/site_config.env` mit den eigenen Entity-IDs bearbeiten und erst nach vollständiger Prüfung setzen:

   ```dotenv
   SITE_CONFIG_CONFIRMED=YES
   ```

5. Mapping anwenden und Erstprüfung starten:

   ```bash
   python3 scripts/apply_site_config.py config/site_config.env
   bash scripts/run_first_checks.sh
   ```

6. Den Master `input_boolean.se_netzdienlich_enabled` erst einschalten, wenn die Erstprüfung mit `PASS=True` endet.

Die vollständigen Schritte, Pflichtsensoren, EVOpt-Konfiguration, erwarteten Zustände und der Rollback stehen in der [Erstinstallation](docs/02_FIRST_INSTALL.md). Bestehende Installationen verwenden ausschließlich die [Update-Anleitung](docs/05_UPDATE.md).

## Dokumentation

### Installation und Betrieb

- [Voraussetzungen](docs/01_REQUIREMENTS.md)
- [Erstinstallation](docs/02_FIRST_INSTALL.md)
- [Entity-Mapping](docs/03_ENTITY_MAPPING.md)
- [Erster Start](docs/04_FIRST_START.md)
- [Update](docs/05_UPDATE.md)
- [Migration](docs/06_MIGRATION.md)
- [Fehlerdiagnose](docs/07_TROUBLESHOOTING.md)
- [Datenschutz und Sicherheit](docs/08_PRIVACY_AND_SECURITY.md)

### Betriebsarten

- [Eigenverbrauch maximieren](docs/modes/01_SELF_CONSUMPTION.md)
- [Netzdienlich laden](docs/modes/02_GRID_FRIENDLY.md)
- [Akku schonen](docs/modes/03_BATTERY_CARE.md)
- [EVOpt optimiert](docs/modes/04_EVOPT.md)

### Integrationen

- [SolarEdge Modbus](docs/integrations/01_SOLAREDGE_MODBUS.md)
- [PV-Prognose](docs/integrations/02_PV_FORECAST.md)
- [Wetter](docs/integrations/03_WEATHER.md)
- [SQL/Recorder](docs/integrations/04_SQL_RECORDER.md)
- [evcc](docs/integrations/05_EVCC.md)
- [evcc Optimizer](docs/integrations/06_EVCC_OPTIMIZER.md)
- [Externe Signale](docs/integrations/07_EXTERNAL_SIGNALS.md)

### Technische Referenz

- [Funktion der YAML-Dateien](docs/reference/01_YAML_FILES.md)
- [Safety, Arbiter und Writer](docs/reference/02_SAFETY_ARBITER_WRITERS.md)
- [Tests und Release-Gates](docs/reference/03_TESTS_AND_RELEASE_GATES.md)
- [Technischer Status RC3](docs/reference/04_FINAL_TECHNICAL_STATUS.md)

## Sicherheit

- Der Master bleibt nach Installation, Update, Migration und Rollback ausgeschaltet.
- Site-Konfiguration, Config Check und Sanity Check müssen gültig sein.
- Leere optionale Writer-Mappings deaktivieren den jeweiligen Writer.
- EVOpt schreibt nie direkt auf SolarEdge; der Adapter liefert nur eine Anforderung.
- Fehlende oder ungültige EVOpt-Daten führen zum Fallback „Netzdienlich laden“.
- Vor jedem Installations- oder Updatevorgang wird ein dateibezogenes Backup erzeugt.
- Weitere Automationen dürfen nicht auf dieselben gemappten SolarEdge-Ziele schreiben.

## Lizenz

MIT License. Siehe [LICENSE](LICENSE).
