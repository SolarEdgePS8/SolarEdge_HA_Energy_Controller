# SolarEdge HA Energy Controller

Ein portabler Home-Assistant-Controller für SolarEdge-Batteriespeicher. Das Projekt bündelt Planung, Sicherheitslogik und kontrollierte Schreibzugriffe in einer nachvollziehbaren Package-Struktur.

## Status

**Entwicklungsstand `v0.1.0-rc.2`**

Der Release Candidate wurde auf einer Referenzinstallation installiert, mit `ha core check`, Manifestprüfung und Runtime-Checker geprüft. Die öffentliche Bereitstellung wird zunächst über einen Draft Pull Request vorbereitet. Der Master ist nach Installation und Migration grundsätzlich ausgeschaltet.

## Die vier Betriebsarten

| Modus | Zweck | Zusätzliche Daten |
|---|---|---|
| **Eigenverbrauch maximieren** | Speicher für den normalen Eigenverbrauch freigeben | nur Grunddaten und SolarEdge-Mapping |
| **Netzdienlich laden** | Laden zeitlich planen, PV besser nutzen und Leistungsspitzen vermeiden | PV-Prognosen, PV-Leistung, Hausverbrauch |
| **Akku schonen** | Ziel-SoC und Ladefenster aus Bedarf, Reserve und Prognose ableiten | Verbrauchsannahmen, optional SQL-Historie und Wetter |
| **EVOpt optimiert** | gültigen evcc-Optimizer-Plan übernehmen | evcc, Optimizer, API-Verbindung; sicherer Fallback auf „Netzdienlich laden“ |

Jeder Modus liefert zunächst nur eine Anforderung. **Safety** und **Arbiter** prüfen diese Anforderung, bevor ein Writer ein SolarEdge-Ziel beschreibt.

## Was nicht enthalten ist

Das Repository enthält keine privaten oder standortspezifischen Automationen für:

- Fahrzeuge oder Wallboxen;
- Wärmepumpen oder Shelly-Geräte;
- dynamische Strompreise;
- eigene Backup-Reserve- oder Akku-Saver-Projekte;
- lokale Hostnamen, IP-Adressen oder private Entity-IDs.

Solche Systeme können optional über neutrale Eingangssignale angebunden werden.

## Schnellstart

1. In Home Assistant ein vollständiges Backup erstellen.
2. Release-ZIP nach `/share` kopieren und entpacken.
3. Installer ausführen:

   ```bash
   bash scripts/install_package.sh
   ```

4. Home Assistant neu starten.
5. `config/site_config.env.example` nach `config/site_config.env` kopieren.
6. Eigene Entity-IDs eintragen.
7. `SITE_CONFIG_CONFIRMED=YES` setzen.
8. Konfiguration anwenden:

   ```bash
   python3 scripts/apply_site_config.py config/site_config.env
   ```

9. Erstprüfungen starten:

   ```bash
   bash scripts/run_first_checks.sh
   ```

10. Den Master erst einschalten, wenn alle Prüfungen erfolgreich sind.

Die vollständige Anleitung steht in [Erstinstallation](docs/02_FIRST_INSTALL.md).

## Voraussetzungen

Pflicht:

- Home Assistant OS oder Supervised mit Zugriff auf `/config` und `/share`;
- aktivierte Home-Assistant-Packages;
- eine SolarEdge-Integration mit schreibbarem Charge-Limit;
- Akku-SoE in Prozent;
- PV-Prognosen für heute und morgen;
- aktuelle PV-Leistung und Hausverbrauch als **Momentanleistung in W**.

Optional:

- Discharge-Limit;
- Storage Command Mode;
- Storage Control Mode;
- Wetterintegration;
- SQLite-Recorder-Auswertung;
- evcc und evcc Optimizer;
- externe Sperr- oder EV-Ladesignale.

## Dokumentation

### Installation und Betrieb

- [Voraussetzungen](docs/01_REQUIREMENTS.md)
- [Erstinstallation](docs/02_FIRST_INSTALL.md)
- [Entity-Mapping](docs/03_ENTITY_MAPPING.md)
- [Erster Start und Aktivierung](docs/04_FIRST_START.md)
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
- [PV-Prognosen](docs/integrations/02_PV_FORECAST.md)
- [Wetter](docs/integrations/03_WEATHER.md)
- [SQL/Recorder](docs/integrations/04_SQL_RECORDER.md)
- [evcc](docs/integrations/05_EVCC.md)
- [evcc Optimizer](docs/integrations/06_EVCC_OPTIMIZER.md)
- [Externe Signale](docs/integrations/07_EXTERNAL_SIGNALS.md)

### Technische Referenz

- [Funktion der YAML-Dateien](docs/reference/01_YAML_FILES.md)
- [Safety, Arbiter und Writer](docs/reference/02_SAFETY_ARBITER_WRITERS.md)
- [Tests und Release-Gates](docs/reference/03_TESTS_AND_RELEASE_GATES.md)

## Sicherheit

- Der Master ist nach Installation und Migration aus.
- Leere optionale Mappings deaktivieren den jeweiligen Writer.
- Genau ein Writer ist für jedes aktiv gemappte SolarEdge-Ziel vorgesehen.
- Fehlende oder ungültige EVOpt-Daten führen zum vollständigen Fallback auf „Netzdienlich laden“.
- Vor jeder Installation und jedem Update wird ein Backup erzeugt.
- Fremde Automationen werden nicht automatisch gelöscht oder deaktiviert.

## Lizenz

Die endgültige Open-Source-Lizenz wird vor dem ersten öffentlichen Release festgelegt. Bis dahin gilt der Repository-Inhalt als Entwicklungsstand ohne erteilte Nutzungslizenz.
