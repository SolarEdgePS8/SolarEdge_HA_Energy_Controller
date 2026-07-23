# SolarEdge HA Energy Controller

Portabler Home-Assistant-Controller für SolarEdge-Batteriespeicher mit vier Modi, EVCC Optimizer, zentralem Safety-Arbiter, genau einem Writer je SolarEdge-Ziel und einem read-only Write-Watchdog. Planung, Sicherheitsprüfung und Schreibzugriffe sind klar voneinander getrennt.

> **Aktives Nachfolgeprojekt:** Dieses Repository ersetzt [`Solaredge_Netzdienlich`](https://github.com/SolarEdgePS8/Solaredge_Netzdienlich). Das alte Repository bleibt nur zur historischen Nachvollziehbarkeit erhalten. Bestehende Nutzer verwenden die [Migrationsanleitung](docs/11_MIGRATION_FROM_NETZDIENLICH.md).

Der Controller unterstützt vier Betriebsarten:

| Modus | Zweck |
|---|---|
| **Eigenverbrauch maximieren** | Akku für normalen Eigenverbrauch freigeben |
| **Netzdienlich laden** | PV-Ladung zeitlich planen und hohe Leistungsspitzen vermeiden |
| **Akku schonen** | Ladeziel und Ladefenster aus Verbrauch, Reserve und Prognose ableiten |
| **EVOpt optimiert** | gültige Vorgaben des evcc Optimizers übernehmen; bei einem länger anhaltenden Fehler vollständig auf „Netzdienlich laden“ zurückfallen |

## Status

**Version: `v0.1.0-rc.4` – Release Candidate / Prerelease**

RC4 behebt unnötige Charge-Limit-Zyklen beim Home-Assistant-/EVOpt-Startup und veröffentlicht den auf der Referenzinstallation getesteten Write-Watchdog.

Wesentliche Eigenschaften:

- 18 portable Home-Assistant-Package-Dateien;
- genau ein Writer je gemapptem SolarEdge-Ziel;
- EVOpt-Startup-Handover hält bei kurzen Ausfällen den zuletzt bestätigten SolarEdge-Zustand;
- vollständiger Legacy-Fallback erst nach 20 Minuten durchgehendem EVOpt-Ausfall;
- `holdcharge` sperrt sofort und bleibt 180 Sekunden gelatcht;
- Freigabe auf `5000 W` erst nach 90 Sekunden stabilem finalem Sollwert;
- Master, Site-Bestätigung, EVOpt-Aktivierung und EVOpt-URL bleiben über Neustarts erhalten;
- Write-Watchdog `1.0.2` mit Service-Trace, Context-Kette, Writer-Scan, Roundtrip- und EVOpt-Konsistenzprüfung;
- Installation, Update und dateibezogener Rollback;
- SHA256-Paritätsnachweis: alle 18 veröffentlichten YAML-Dateien sind byteidentisch mit dem geprüften Live-Export vom 22.07.2026.

Ein Release Candidate ist bewusst noch kein stabiler `v1.0`-Stand. Andere SolarEdge-Modelle, Integrationen und Entity-Namen müssen über das Site-Mapping angepasst und auf der jeweiligen Anlage geprüft werden.

## Was enthalten ist

- 18 Controller-Package-YAMLs;
- read-only Mapping-Assistent mit bewerteten Entity-Vorschlägen und sicherer `site_config.env`;
- Entity-Mapping für unterschiedliche Installationen;
- zentrale Safety- und Arbiter-Logik;
- Charge-, Discharge-, Storage-Control- und Command-Mode-Writer;
- Write-Watchdog als read-only Custom Integration;
- Terminal-Tools für Bericht und Live-Trace;
- Runtime-Manifest mit Version, Quellcommit und SHA256 aller installierten Projektdateien;
- Installer, Update, Migration und vollständiger dateibezogener Rollback;
- optionale Wetter-, SQL-, evcc-, EVOpt- und Strompreis-/Kosten-Anbindung;
- neutrale Beispiel-Packages für Filter, Energiezähler, Forecast-, evcc- und Preisadapter;
- Installationswege für Home Assistant OS, Supervised, Container und Core;
- reproduzierbarer Deep Testbench mit Codespaces, zwei gepinnten HA-Versionen und einem 24h-Vier-Modi-Replay;
- formales Fixture-Schema, Privacy-Scanner und lokaler Allowlist-Exporter für zusätzliche Testtage.

## Was nicht enthalten ist

Keine privaten Fahrzeug-, Wallbox-, Wärmepumpen-, Shelly-, Strompreis-, Backup-Reserve- oder Akku-Saver-Automationen. Solche Systeme können über neutrale optionale Eingangssignale angebunden werden.

## Unterstützte Home-Assistant-Installationen

| Installation | Unterstützung |
|---|---|
| Home Assistant OS | vollständig automatisiert über `/config`, `/share`, `ha` und `SUPERVISOR_TOKEN` |
| Home Assistant Supervised | automatisiert, sofern Supervisor-CLI und Token verfügbar sind |
| Home Assistant Container | über `CONFIG_ROOT`, `SHARE_ROOT`, `HA_TOKEN`, `HA_API_URL` und `HA_CHECK_COMMAND` |
| Home Assistant Core | über lokale Pfade, Long-Lived Access Token und Python-Konfigurationsprüfung |

Details: [Installation auf verschiedenen Home-Assistant-Systemen](docs/09_INSTALLATION_VARIANTS.md).

## Voraussetzungen

Benötigt werden:

- schreibbares SolarEdge-Charge-Limit als `number.*` in Watt;
- Akku-Ladestand in Prozent und nutzbare Kapazität;
- PV-Prognose heute verbleibend, heute gesamt und morgen in kWh;
- aktuelle PV-Leistung und aktueller Hausverbrauch in Watt;
- aktivierte Home-Assistant-Packages;
- vollständiges Backup;
- eindeutiges Site-Mapping ohne zweiten Writer auf demselben SolarEdge-Ziel.

`LIVE_PV_POWER_ENTITIES` und `LIVE_CONSUMPTION_POWER_ENTITIES` erwarten Momentanleistung in **W**, keine Energiezähler in `kWh`. Ein Sensorname mit `_filtered` ist optional.

Typische SolarEdge-Entities kommen aus SolarEdge Modbus Multi; Prognose, Wetter, evcc und Strompreis können aus getrennten Integrationen oder eigenen Adapter-Sensoren stammen. Der Controller ist nicht an deren Entity-Namen gebunden.

## evcc und Optimizer

**evcc ist nur für den Modus `EVOpt optimiert` erforderlich.** Die übrigen drei Modi funktionieren ohne evcc.

Für EVOpt werden zusätzlich benötigt:

- laufendes evcc;
- eingerichteter Batteriespeicher;
- aktivierter evcc Optimizer mit gültigem Plan;
- von Home Assistant erreichbare evcc-API;
- eindeutiger Batterietitel und bei Bedarf Batteriename.

Die Basis-URL enthält weder `/api` noch `/api/state`:

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://evcc-host:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
```

API vor Aktivierung prüfen:

```bash
curl -fsS http://evcc-host:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Der EVOpt-Adapter liest nur. Er schreibt niemals direkt auf SolarEdge. Safety, Arbiter und der einzige Writer bleiben vorgeschaltet.

## Schnellstart für Home Assistant OS / Supervised

1. Release-Dateien nach `/share` kopieren:

   ```text
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip
   SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
   ```

2. Prüfsumme prüfen und in einen leeren Ordner entpacken:

   ```bash
   cd /share
   sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip.sha256
   rm -rf /share/se_controller_release_rc4
   mkdir -p /share/se_controller_release_rc4
   unzip -q SolarEdge_HA_Energy_Controller_v0.1.0-rc.4.zip \
     -d /share/se_controller_release_rc4
   cd /share/se_controller_release_rc4/SolarEdge_HA_Energy_Controller
   ```

3. Installieren:

   ```bash
   bash scripts/install_package.sh
   ha core restart
   ```

   Der Installer kopiert Controller, Runtime-Dateien, Watchdog und Terminal-Tools, ergänzt den Watchdog-Konfigurationsblock genau einmal und führt `ha core check` aus. Bei einem Fehler erfolgt ein automatischer Rollback.

4. Entity-Vorschläge read-only erzeugen:

   ```bash
   python3 scripts/discover_entities.py \
     --report /share/se_controller_mapping_report.json \
     --output config/site_config.env
   ```

   Der Assistent liest nur Home-Assistant-States, aktiviert keinen Writer und erzeugt immer `SITE_CONFIG_CONFIRMED=NO` sowie `EVOPT_ENABLED=NO`.

5. Vorschläge mit [Entity-Mapping](docs/03_ENTITY_MAPPING.md) und [Sensorquellen](docs/12_SENSOR_SOURCES_AND_EXAMPLES.md) prüfen. Fehlende neutrale Adapter liegen unter [`examples/sensors`](examples/sensors/README.md). Erst danach `SITE_CONFIG_CONFIRMED=YES` setzen und anwenden:

   ```bash
   python3 scripts/apply_site_config.py config/site_config.env
   bash scripts/run_first_checks.sh
   python3 scripts/check_external_writer_conflicts.py "${CONFIG_ROOT:-/config}"
   ```

6. Den Master `input_boolean.se_netzdienlich_enabled` erst nach `PASS=True` einschalten.

Für bestehende Installationen ausschließlich die [Update-Anleitung](docs/05_UPDATE.md) verwenden.

## Write-Watchdog

Nach dem Neustart:

```bash
/config/se_write_watchdog_tools/report.sh 200
/config/se_write_watchdog_tools/watch.sh
```

Der Watchdog protokolliert jeden beobachteten `number.set_value`-Aufruf auf das gemappte Charge-Limit, die zugeordnete Automation beziehungsweise API-Quelle, den Write-Intent, echte Zustandswechsel und schnelle Roundtrips. Details: [Write-Watchdog](docs/10_WRITE_WATCHDOG.md).

## Dokumentation

### Installation und Betrieb

- [Voraussetzungen](docs/01_REQUIREMENTS.md)
- [Erstinstallation](docs/02_FIRST_INSTALL.md)
- [Installation auf OS, Supervised, Container und Core](docs/09_INSTALLATION_VARIANTS.md)
- [Entity-Mapping](docs/03_ENTITY_MAPPING.md)
- [Sensorquellen, Einheiten und eigene Zusatzsensoren](docs/12_SENSOR_SOURCES_AND_EXAMPLES.md)
- [Optionale Sensorbeispiele](examples/sensors/README.md)
- [Erster Start](docs/04_FIRST_START.md)
- [Update](docs/05_UPDATE.md)
- [Migration](docs/06_MIGRATION.md)
- [Migration aus Solaredge_Netzdienlich](docs/11_MIGRATION_FROM_NETZDIENLICH.md)
- [Fehlerdiagnose](docs/07_TROUBLESHOOTING.md)
- [Datenschutz und Sicherheit](docs/08_PRIVACY_AND_SECURITY.md)
- [Write-Watchdog](docs/10_WRITE_WATCHDOG.md)

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
- [Dynamische Strompreise und Kosten](docs/integrations/08_ELECTRICITY_PRICE.md)

### Technische Referenz und Tests

- [Funktion der YAML-Dateien](docs/reference/01_YAML_FILES.md)
- [Safety, Arbiter und Writer](docs/reference/02_SAFETY_ARBITER_WRITERS.md)
- [Tests und Release-Gates](docs/reference/03_TESTS_AND_RELEASE_GATES.md)
- [Deep Testbench, Codespaces und HA-Container-Simulation](docs/13_DEEP_TESTBENCH.md)
- [24h-Replay mit vier vollständigen Modusläufen](docs/14_REAL_DAY_24H_REPLAY.md)
- [Fixture-Schema, Privacy-Exporter, HA-Matrix und Nightly](docs/15_TESTBENCH_HARDENING.md)
- [Technischer Status RC4](docs/reference/04_FINAL_TECHNICAL_STATUS.md)

## Tiefgreifende Testumgebung

Das Repository enthält einen hardwarefreien Deep Testbench mit festen Tag-/Nacht-/PV-/SoC-Szenarien, Property-Tests, Fake-Time-Zustandsmaschinen, einem kontrollierbaren Fake-evcc-Server und Home-Assistant-Container-Tests. Die Pflichtmatrix prüft Home Assistant 2026.7.3 und 2026.6.3; der vollständige 24h-Replay spielt denselben Tagesverlauf durch alle vier Betriebsarten. Codespaces und GitHub Actions verwenden dieselben Einstiegsskripte.

```bash
bash scripts/run_deep_tests.sh all
bash scripts/run_ha_smoke.sh
bash scripts/run_ha_24h_replay.sh
```

Eigene Testtage werden ausschließlich lokal und über ein Rollen-Allowlisting erzeugt. Details:

- [Deep Testbench und GitHub Codespaces](docs/13_DEEP_TESTBENCH.md)
- [Reproduzierbarer 24-Stunden-Test](docs/14_REAL_DAY_24H_REPLAY.md)
- [Testbench-Hardening und lokale Datenerzeugung](docs/15_TESTBENCH_HARDENING.md)

## Sicherheit

- Der Master bleibt nach Installation, Update, Migration und Rollback ausgeschaltet.
- Site-Konfiguration, Config Check und Sanity Check müssen gültig sein.
- Leere optionale Writer-Mappings deaktivieren den jeweiligen Writer.
- EVOpt schreibt nie direkt auf SolarEdge.
- Kurze EVOpt-Ausfälle öffnen den Speicher im EVOpt-Modus nicht automatisch.
- Weitere Automationen dürfen nicht auf dieselben gemappten SolarEdge-Ziele schreiben.
- Der Watchdog ist read-only; er beobachtet Schreibaufrufe, erzeugt aber selbst keine SolarEdge-Befehle.
- Test-Fixtures und HA-Container verwenden ausschließlich synthetische Writer-Ziele; ein Merge der Testbench verändert keine laufende Home-Assistant-Instanz.

## Lizenz

MIT License. Siehe [LICENSE](LICENSE).
