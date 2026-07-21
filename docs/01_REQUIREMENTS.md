# Voraussetzungen

## Unterstützte Home-Assistant-Umgebung

Empfohlen wird **Home Assistant OS** oder **Home Assistant Supervised** mit:

- Terminal-/SSH-Zugriff auf `/config` und `/share`;
- verfügbarem `ha`-Kommando;
- Python 3;
- `SUPERVISOR_TOKEN` im Terminal-Add-on;
- vollständigem Home-Assistant-Backup vor Installation oder Update.

In `configuration.yaml` müssen Packages aktiviert sein:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Nach einer Änderung an `configuration.yaml` zuerst ausführen:

```bash
ha core check
```

## SolarEdge-Anbindung

Mindestens ein schreibbares SolarEdge-Charge-Limit als `number.*` wird benötigt. Die verwendete SolarEdge-Integration muss den Wert zuverlässig lesen und schreiben können.

SolarEdge weist darauf hin, dass veränderbare Power-Control-Register für langfristige Einstellungen vorgesehen sind. Der Controller reduziert Schreibzugriffe deshalb durch Mindeständerung, Cooldown und genau einen Writer pro Ziel. Trotzdem erfolgt die Verwendung auf eigene Verantwortung.

Vor dem ersten Start muss geprüft werden, dass keine andere Automation dasselbe gemappte Charge-Limit schreibt.

## Pflichtdaten für RC3

| Datenpunkt | Erwartete Einheit | Anforderung |
|---|---:|---|
| SolarEdge Charge-Limit | `W` | schreibbare `number.*`-Entity |
| Akku-Ladestand | `%` | aktueller SoC/SoE-Sensor |
| nutzbare Akkukapazität | `kWh` | Sensor oder manueller Fallbackwert |
| PV-Prognose heute verbleibend | `kWh` | verbleibende Energie des laufenden Tages |
| PV-Prognose heute gesamt | `kWh` | gesamte Tagesprognose |
| PV-Prognose morgen | `kWh` | gesamte Prognose für morgen |
| aktuelle PV-Leistung | `W` | Momentanleistung, kein Energiezähler |
| aktueller Hausverbrauch | `W` | Momentanleistung, kein Energiezähler |

Die zentrale Safety-Prüfung verwendet Prognose- und Akkudaten unabhängig vom ausgewählten Modus. Deshalb müssen die Pflicht-Mappings auch für „Eigenverbrauch maximieren“ gültig sein.

`LIVE_PV_POWER_ENTITIES` und `LIVE_CONSUMPTION_POWER_ENTITIES` erwarten **Watt**. Sensoren mit `kWh` sind dort falsch. Ein Sensorname mit `_filtered` ist nur ein mögliches eigenes Namensschema und keine Voraussetzung.

## Optionale Daten und Writer

Optional sind:

- Discharge-Limit;
- Storage Command Mode;
- Storage Control Mode;
- Backup-Reserve;
- Wetterintegration;
- PV-Prognose übermorgen;
- Tagesverbrauchs- und PV-Ertragszähler;
- Home-Assistant-SQLite-Historie;
- evcc und evcc Optimizer;
- neutrale Signale externer Automationen.

Leere optionale Mappings sind erlaubt und deaktivieren die jeweilige Funktion.

Ein optionales SolarEdge-Ziel darf nur eingetragen werden, wenn dieser Controller der alleinige Writer dafür sein soll. Andernfalls bleibt das Mapping leer.

## Zusätzliche Voraussetzungen für EVOpt

Für den Modus `EVOpt optimiert` werden zusätzlich benötigt:

- laufendes evcc mit aktiviertem Optimizer;
- von Home Assistant erreichbare evcc-API;
- erreichbarer Endpunkt `<EVOPT_BASE_URL>/api/state`;
- eindeutiger Batterietitel und bei Bedarf Batteriename;
- aktueller, konsistenter Optimizer-Plan.

Die Basis-URL enthält **nicht** `/api/state`. Beispiel:

```dotenv
EVOPT_BASE_URL=http://homeassistant.local:7070
```

Vor Aktivierung kann der Endpunkt geprüft werden:

```bash
curl -fsS http://homeassistant.local:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

## Ausschluss von Writer-Konflikten

Vor dem Einschalten des Masters ausführen:

```bash
python3 scripts/check_external_writer_conflicts.py /config
```

Jeder gemeldete Konflikt auf einem aktiv gemappten SolarEdge-Ziel muss zuerst geklärt werden. Private Wärmepumpen-, Wallbox-, Akku-Saver- oder sonstige Automationen dürfen unabhängig weiterlaufen, solange sie nicht dieselben gemappten SolarEdge-Ziele schreiben.
