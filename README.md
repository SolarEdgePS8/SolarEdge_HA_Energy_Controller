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
- Home-Assistant-Konfigurationsprüfung, Config Check und Sanity Check erfolgreich;
- Runtime-Manifest und alle 23 installierten Projektdateien per SHA256 geprüft;
- reale EVOpt-Slotwechsel ohne Ausfall von `active_control` und ohne unnötigen 0/5000-W-Fallback;
- GitHub Actions mit Release-Gate, Syntax-, Vertrags-, Installer-, ZIP- und Manifestprüfung.

Ein Release Candidate ist bewusst noch kein stabiler `v1.0`-Stand. Andere SolarEdge-Modelle, Integrationen und Entity-Namen müssen über das Site-Mapping angepasst und auf der jeweiligen Anlage geprüft werden.

## Was enthalten ist

- 18 Home-Assistant-Package-Dateien;
- Entity-Mapping für unterschiedliche Installationen;
- zentrale Safety- und Arbiter-Logik;
- genau ein Writer je gemapptem SolarEdge-Ziel;
- Installation, Update, Migration und vollständiger Rollback;
- Runtime-, Datei- und Konfliktprüfung;
- optionale Wetter-, SQL-, evcc- und EVOpt-Anbindung;
- Installationswege für Home Assistant OS, Supervised, Container und Core;
- Dokumentation für Erstinstallation und Update.

## Was nicht enthalten ist

Keine privaten Fahrzeug-, Wallbox-, Wärmepumpen-, Shelly-, Strompreis-, Backup-Reserve- oder Akku-Saver-Automationen. Solche Systeme können nur über neutrale optionale Eingangssignale angebunden werden.

## Unterstützte Home-Assistant-Installationen

| Installation | Unterstützung |
|---|---|
| Home Assistant OS | vollständig automatisiert über `/config`, `/share`, `ha` und `SUPERVISOR_TOKEN` |
| Home Assistant Supervised | vollständig automatisiert, sofern Supervisor-CLI und Token verfügbar sind |
| Home Assistant Container | unterstützt über `CONFIG_ROOT`, `SHARE_ROOT`, `HA_TOKEN`, `HA_API_URL` und `HA_CHECK_COMMAND` |
| Home Assistant Core | unterstützt über lokale Pfade, Long-Lived Access Token und Python-Konfigurationsprüfung |

Die genauen Befehle stehen unter [Installation auf verschiedenen Home-Assistant-Systemen](docs/09_INSTALLATION_VARIANTS.md).

## Was benötigt wird

Unabhängig vom gewählten Modus werden benötigt:

- schreibbares SolarEdge-Charge-Limit als `number.*` in Watt;
- Akku-Ladestand in Prozent;
- nutzbare Akkukapazität;
- PV-Prognose heute verbleibend, heute gesamt und morgen in kWh;
- aktuelle PV-Leistung in Watt;
- aktueller Hausverbrauch in Watt;
- aktivierte Home-Assistant-Packages;
- vollständiges Backup;
- eindeutiges Site-Mapping ohne zweiten Writer auf demselben SolarEdge-Ziel.

`LIVE_PV_POWER_ENTITIES` und `LIVE_CONSUMPTION_POWER_ENTITIES` erwarten Momentanleistung in **W**, keine Energiezähler in `kWh`. Ein Sensorname mit `_filtered` ist optional und kein Pflichtsensor.

## evcc und Optimizer

**evcc ist nur für den Modus `EVOpt optimiert` erforderlich.** Die übrigen drei Modi funktionieren ohne evcc.

Für EVOpt werden zusätzlich benötigt:

- laufendes evcc;
- eingerichteter Batteriespeicher;
- aktivierter evcc Optimizer mit gültigem Plan;
- von Home Assistant erreichbare evcc-API;
- eindeutiger Batterietitel und bei Bedarf Batteriename.

Die konfigurierte Basis-URL enthält weder `/api` noch `/api/state`:

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://evcc-host:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
```

Prüfung vor Aktivierung:

```bash
curl -fsS http://evcc-host:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Erwartet:

```text
EVCC_API=OK True
```

Der EVOpt-Adapter liest nur. Er schreibt niemals direkt auf SolarEdge. Erst Safety, Arbiter und der einzige Writer erzeugen eine freigegebene Anforderung. Bei ungültigen oder nicht erreichbaren EVOpt-Daten fällt der Controller vollständig auf `Netzdienlich laden` zurück.

## Schnellstart für Home Assistant OS / Supervised

1. Die beiden Release-Dateien nach `/share` kopieren:

   ```text
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
   ```

2. Prüfsumme kontrollieren und in einen leeren Ordner entpacken:

   ```bash
   cd /share
   sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
   rm -rf /share/se_controller_release_rc3
   mkdir -p /share/se_controller_release_rc3
   unzip -q SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip \
     -d /share/se_controller_release_rc3
   cd /share/se_controller_release_rc3/SolarEdge_HA_Energy_Controller
   ```

   Erwartet:

   ```text
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip: OK
   ```

3. Controller-Dateien installieren und Home Assistant neu starten:

   ```bash
   bash scripts/install_package.sh
   ha core restart
   ```

4. Nach dem Neustart die private Standortkonfiguration erstellen:

   ```bash
   cp config/site_config.env.example config/site_config.env
   ```

   Eigene Entity-IDs eintragen. Erst nach vollständiger Kontrolle setzen:

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

## Installer-Sicherheitsmechanismen

Der Installer:

- erkennt Erstinstallation und bestehende Installation;
- schaltet bei einer bestehenden Installation zuerst den Controller-Master aus;
- bricht ohne API-Token ab, wenn der sichere Masterzustand nicht bestätigt werden kann;
- erstellt vor jeder Änderung ein dateibezogenes Backup;
- kopiert ausschließlich Projektdateien;
- erzeugt ein Runtime-Manifest mit Version, Quellcommit und SHA256 aller 23 installierten Dateien;
- führt eine Home-Assistant-Konfigurationsprüfung aus;
- rollt bei Fehlern automatisch zurück;
- lässt den Controller-Master ausgeschaltet.

## Dokumentation

### Installation und Betrieb

- [Voraussetzungen](docs/01_REQUIREMENTS.md)
- [Erstinstallation](docs/02_FIRST_INSTALL.md)
- [Installation auf OS, Supervised, Container und Core](docs/09_INSTALLATION_VARIANTS.md)
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
- Fehlende oder ungültige EVOpt-Daten führen zum Fallback `Netzdienlich laden`.
- Vor jedem Installations- oder Updatevorgang wird ein dateibezogenes Backup erzeugt.
- Weitere Automationen dürfen nicht auf dieselben gemappten SolarEdge-Ziele schreiben.

## Lizenz

MIT License. Siehe [LICENSE](LICENSE).
