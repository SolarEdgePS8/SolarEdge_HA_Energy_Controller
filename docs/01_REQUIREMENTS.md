# Voraussetzungen

## Unterstützte Home-Assistant-Systeme

| System | Konfigurationspfad | Prüfung | API-Zugang |
|---|---|---|---|
| Home Assistant OS | `/config`, `/share` | `ha core check` | `SUPERVISOR_TOKEN` im Terminal-Add-on |
| Supervised | `/config`, `/share` | `ha core check` | `SUPERVISOR_TOKEN` |
| Container | frei über Umgebungsvariablen | HA-Python oder `HA_CHECK_COMMAND` | `HA_TOKEN`, `HA_API_URL` |
| Core | frei über Umgebungsvariablen | HA-Python oder `HA_CHECK_COMMAND` | `HA_TOKEN`, `HA_API_URL` |

Benötigte Werkzeuge:

- Bash;
- Python 3.11 oder neuer;
- `unzip` und `sha256sum`;
- Schreibzugriff auf den HA-Konfigurationsordner;
- Backup-Verzeichnis;
- vollständiges Home-Assistant-Backup.

## Packages aktivieren

```yaml
homeassistant:
  packages: !include_dir_named packages
```

## Erforderliche Datenquellen

Der Controller benötigt fertige Home-Assistant-Entities. Diese können aus unterschiedlichen Integrationen stammen.

### Typischer Kern

| Daten | Einheit | Häufige Quelle |
|---|---|---|
| Storage Charge Limit | `W`, schreibbare `number.*` | SolarEdge Modbus Multi |
| Batterie-SoC/SoE | `%` | SolarEdge Modbus Multi |
| Batteriekapazität | `kWh` oder manueller Wert | SolarEdge Modbus Multi/Datenblatt |
| PV-Leistung aktuell | `W` | SolarEdge, Smart Meter oder Power Flow |
| Hausverbrauch aktuell | `W` | Smart Meter oder Power Flow |
| PV-Prognose heute verbleibend | `kWh` | Forecast-Anbieter/Template |
| PV-Prognose heute gesamt | `kWh` | Forecast-Anbieter/Template |
| PV-Prognose morgen | `kWh` | Forecast-Anbieter/Template |

Die Forecast-Daten werden auch von der zentralen Safety-Prüfung genutzt. Deshalb müssen sie derzeit auch dann gültig sein, wenn später „Eigenverbrauch maximieren“ gewählt wird.

### Nicht zwingend erforderlich

- evcc und ha-evcc: nur für EVOpt beziehungsweise zusätzliche HA-Anzeige;
- Wetter: verbessert Planung, ist aber optional;
- DWD Weather: mögliche Wetterquelle in Deutschland, kein Muss;
- EPEX Spot oder andere Strompreisquelle: derzeit keine Pflicht des Controller-Kerns;
- Dynamic Energy Cost: Kostenanalyse, nicht Steuerkern;
- SQL/Recorder-Auswertung: optionale Lastprognose;
- geglätteter `_filtered`-Sensor: optional und lokal erzeugt.

Ausführlich: [Sensorquellen und Beispiele](12_SENSOR_SOURCES_AND_EXAMPLES.md).

## SolarEdge-Anbindung

Empfohlene Referenz ist SolarEdge Modbus Multi. Für Storage Charge/Discharge Limit müssen die Storage-Control-Optionen der Integration und bei unterstützten Geräten der Remote-Control-Modus verfügbar sein.

Vor der ersten Schreibfreigabe:

1. Charge-Limit als `number.*` in Watt prüfen;
2. zulässigen Min-/Max-Bereich prüfen;
3. ursprüngliche Wechselrichtereinstellungen dokumentieren;
4. sicherstellen, dass keine zweite Automation dasselbe Ziel schreibt;
5. Master ausgeschaltet lassen.

Die erweiterten Steuerfunktionen sind installations- und firmwareabhängig. Nicht jede SolarEdge-Anlage stellt dieselben Entities bereit.

## Leistung ist nicht Energie

```text
W     Momentanleistung
kWh   Energie über einen Zeitraum
```

`LIVE_PV_POWER_ENTITIES` und `LIVE_CONSUMPTION_POWER_ENTITIES` erwarten **Watt**. Quellen in `kW` müssen vorher auf `W` umgerechnet werden. Energiezähler in `Wh`/`kWh` sind dort falsch.

## API-Zugriff

### OS / Supervised

Das Terminal-/SSH-Add-on stellt normalerweise `SUPERVISOR_TOKEN` bereit. Er darf niemals in Dokumentation oder Support-Archive kopiert werden.

### Container / Core

```bash
export HA_TOKEN='DEIN_LONG_LIVED_ACCESS_TOKEN'
export HA_API_URL='http://homeassistant:8123/api'
export CONFIG_ROOT=/config
export SHARE_ROOT=/share
```

Der Token gilt nur für die Shell-Sitzung und wird nicht in das Runtime-Manifest geschrieben.

## Home-Assistant-Konfigurationsprüfung

Reihenfolge des Installers:

1. `HA_CHECK_COMMAND`;
2. `ha core check`;
3. `python3 -m homeassistant --script check_config -c "$CONFIG_ROOT"`.

Beispiel Container:

```bash
export HA_CHECK_COMMAND='docker exec homeassistant python3 -m homeassistant --script check_config -c /config'
```

`SE_CONTROLLER_SKIP_HA_CHECK=YES` ist nur ein bewusster Notfall-Override und nicht für reguläre Installationen vorgesehen.

## Sicherheitsanforderung bei Updates

Bei einer bestehenden Installation muss der Master vor dem Kopieren ausgeschaltet sein. Ohne API-Token bricht der Installer ab. Nur nach manueller Kontrolle:

```bash
export SE_CONTROLLER_MASTER_ALREADY_OFF=YES
```

## Writer-Konflikte

Vor Aktivierung:

```bash
python3 scripts/check_external_writer_conflicts.py "${CONFIG_ROOT:-/config}"
```

Ein optionales SolarEdge-Ziel bleibt leer, wenn eine andere Automation dessen Eigentümer bleiben soll.
