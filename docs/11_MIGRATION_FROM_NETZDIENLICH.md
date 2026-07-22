# Migration von Solaredge_Netzdienlich

Dieses Repository ist der aktive Nachfolger von:

**https://github.com/SolarEdgePS8/Solaredge_Netzdienlich**

Das alte Projekt bleibt nur zur historischen Nachvollziehbarkeit erhalten und wird nicht mehr weiterentwickelt.

## Wichtig

Alte und neue Package-Dateien dürfen nicht gemischt betrieben werden. Verwende für die Umstellung ausschließlich ein vollständiges Release des **SolarEdge HA Energy Controllers**.

## Voraussetzungen

Vor Beginn:

- vollständiges Home-Assistant-Backup erstellen;
- aktuelle Entity-Zuordnungen dokumentieren;
- prüfen, ob weitere lokale Automationen auf dieselben SolarEdge-Ziele schreiben;
- Controller-Master ausschalten.

## Empfohlener Ablauf für Home Assistant OS / Supervised

1. Aktuelles Release-ZIP und die zugehörige `.sha256`-Datei herunterladen.
2. Beide Dateien nach `/share` kopieren.
3. Prüfsumme kontrollieren.
4. ZIP in einen leeren Ordner entpacken.
5. Im entpackten Projektordner ausführen:

```bash
bash scripts/update_package.sh
```

6. Home Assistant neu starten.
7. Site-Mapping prüfen und bei Bedarf mit `config/site_config.env` neu anwenden.
8. Erste Prüfungen ausführen:

```bash
bash scripts/run_first_checks.sh
```

9. Controller-Master erst nach erfolgreicher Prüfung wieder einschalten.

## Was der Installer übernimmt

Der Installer verwaltet:

- 18 Controller-Package-YAMLs;
- Runtime- und Audit-Dateien;
- den read-only Write-Watchdog;
- Terminal-Werkzeuge für Bericht und Live-Trace;
- Runtime-Manifest und dateibezogenes Backup.

Vorhandene verwaltete Dateien werden gesichert. Bei einem Fehler der Home-Assistant-Konfigurationsprüfung erfolgt ein automatischer Rollback.

## Was nicht automatisch übernommen wird

Nicht Bestandteil des öffentlichen Projekts sind private Automationen für beispielsweise:

- Fahrzeuge und Wallboxen;
- Wärmepumpen;
- Shelly-Geräte;
- lokale Strompreislogik;
- weitere anlagenspezifische Verbraucher oder Speicher.

Solche Funktionen bleiben lokal und müssen über die neutralen Eingänge des neuen Controllers angebunden werden.

## Pflichtprüfung nach der Migration

Mindestens folgende Zustände müssen plausibel sein:

```text
sensor.se_nf_config_check = ok
sensor.se_nf_sanity_check = ok
sensor.se_write_watchdog_status = ok
```

Bei EVOpt zusätzlich:

```text
sensor.se_nf_evopt_status = healthy
binary_sensor.se_nf_evopt_active_control = on
sensor.se_nf_evopt_candidate_source = evopt
```

Ziel und Rückmeldung müssen zusammenpassen, zum Beispiel:

```text
sensor.se_nf_desired_target = 0
number.solaredge_i1_storage_charge_limit = 0
```

## Support und neue Issues

Neue Fehlerberichte und Funktionswünsche ausschließlich hier erstellen:

**https://github.com/SolarEdgePS8/SolarEdge_HA_Energy_Controller/issues**
