# Voraussetzungen

## Unterstützte Home-Assistant-Installationsarten

Der Controller besteht aus normalen Home-Assistant-Packages und Python-/Shell-Skripten. Die Regel- und Writer-Logik ist deshalb nicht an Home Assistant OS gebunden. Der Installer unterstützt folgende Installationsarten:

| Installationsart | Dateipfade | HA-Konfigurationsprüfung | API-Zugriff für Mapping/Runtime-Check |
|---|---|---|---|
| **Home Assistant OS** | `/config`, `/share` | `ha core check` | `SUPERVISOR_TOKEN` aus Terminal-/SSH-Add-on |
| **Home Assistant Supervised** | `/config`, `/share` | `ha core check` | `SUPERVISOR_TOKEN` |
| **Home Assistant Container** | über `CONFIG_ROOT`/`SHARE_ROOT` | `python3 -m homeassistant --script check_config` oder `HA_CHECK_COMMAND` | `HA_TOKEN` und `HA_API_URL` |
| **Home Assistant Core** | über `CONFIG_ROOT`/`SHARE_ROOT` | `python3 -m homeassistant --script check_config` oder `HA_CHECK_COMMAND` | `HA_TOKEN` und `HA_API_URL` |

**Home Assistant OS oder Supervised ist der einfachste und vollständig automatisierte Weg.** Bei Container/Core müssen die lokalen Pfade korrekt in die Shell beziehungsweise den Wartungscontainer gemountet sein.

### Mindestwerkzeuge

Benötigt werden:

- Bash;
- Python 3.11 oder neuer;
- Schreibzugriff auf den Home-Assistant-Konfigurationsordner;
- ein Verzeichnis für Backups, standardmäßig `/share`;
- für das Entpacken des Releases `unzip`;
- für die Release-Prüfung `sha256sum`;
- vollständiges Home-Assistant-Backup vor Installation oder Update.

## Packages aktivieren

In `configuration.yaml` müssen Packages aktiviert sein:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Der Ordner `packages` muss innerhalb des konfigurierten Home-Assistant-Verzeichnisses liegen. Der Installer legt ihn an, falls er fehlt.

## API-Zugriff

### Home Assistant OS / Supervised

Im offiziellen Terminal-/SSH-Add-on steht normalerweise `SUPERVISOR_TOKEN` automatisch bereit. Die Skripte verwenden dann:

```text
http://supervisor/core/api
```

Der Token darf nicht in Dateien, GitHub-Issues oder Support-Archive kopiert werden.

### Home Assistant Container / Core

Erzeuge in deinem Home-Assistant-Benutzerprofil einen **Long-Lived Access Token** und setze ihn nur für die aktuelle Shell-Sitzung:

```bash
export HA_TOKEN='DEIN_LONG_LIVED_ACCESS_TOKEN'
export HA_API_URL='http://127.0.0.1:8123/api'
```

Liegt Home Assistant in einem anderen Container oder auf einem anderen Host, muss `HA_API_URL` auf die aus der Wartungsumgebung erreichbare Adresse zeigen, zum Beispiel:

```bash
export HA_API_URL='http://homeassistant:8123/api'
```

Der Token wird nicht in das Release oder Runtime-Manifest geschrieben.

## Konfigurationsprüfung ohne `ha`-CLI

Der Installer prüft in dieser Reihenfolge:

1. explizites `HA_CHECK_COMMAND`;
2. `ha core check`;
3. `python3 -m homeassistant --script check_config -c "$CONFIG_ROOT"`.

Beispiel für einen Container, dessen Home-Assistant-Konfiguration nach `/config` gemountet ist:

```bash
export CONFIG_ROOT=/config
export SHARE_ROOT=/share
export HA_CHECK_COMMAND='docker exec homeassistant python3 -m homeassistant --script check_config -c /config'
```

`SE_CONTROLLER_SKIP_HA_CHECK=YES` existiert nur als bewusster Notfall-Override. Für eine reguläre Installation oder Veröffentlichung darf die Prüfung nicht übersprungen werden.

## Sicherheitsanforderung bei Updates ohne API-Token

Bei einer bestehenden Installation muss der Installer den Controller-Master vor dem Kopieren ausschalten. Ohne API-Token bricht er deshalb ab.

Nur wenn der Master bereits manuell ausgeschaltet und geprüft wurde, darf ausdrücklich bestätigt werden:

```bash
export SE_CONTROLLER_MASTER_ALREADY_OFF=YES
```

Bei einer echten Erstinstallation ohne vorhandene `se_controller_*.yaml`-Dateien existiert der Master noch nicht; dieser Schritt wird dann nachvollziehbar übersprungen.

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

## Zusätzliche Voraussetzungen für evcc und EVOpt

Der Controller benötigt evcc nur für den Modus **EVOpt optimiert**. Die anderen drei Modi funktionieren ohne evcc.

Für EVOpt werden zusätzlich benötigt:

- laufendes evcc;
- in evcc eingerichteter Batteriespeicher;
- aktivierter evcc Optimizer mit gültigem Plan;
- von Home Assistant erreichbare evcc-API;
- erreichbarer Endpunkt `<EVOPT_BASE_URL>/api/state`;
- eindeutiger Batterietitel und bei mehreren Speichern zusätzlich der Batteriename;
- aktueller, konsistenter Optimizer-Plan.

Die Basis-URL enthält **nicht** `/api/state`. Beispiel:

```dotenv
EVOPT_BASE_URL=http://homeassistant.local:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
EVOPT_ENABLED=YES
```

Vor Aktivierung den Endpunkt prüfen:

```bash
curl -fsS http://homeassistant.local:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Erwartet:

```text
EVCC_API=OK True
```

Der Adapter liest evcc ausschließlich read-only. EVOpt schreibt nicht direkt auf SolarEdge. Erst Safety, Arbiter und der einzige Charge-Writer entscheiden über einen tatsächlichen Schreibzugriff. Bei API-Ausfall, ungültigem Plan oder unklarer Batteriezuordnung fällt der Controller vollständig auf **Netzdienlich laden** zurück.

## Ausschluss von Writer-Konflikten

Vor dem Einschalten des Masters ausführen:

```bash
python3 scripts/check_external_writer_conflicts.py "${CONFIG_ROOT:-/config}"
```

Jeder gemeldete Konflikt auf einem aktiv gemappten SolarEdge-Ziel muss zuerst geklärt werden. Private Wärmepumpen-, Wallbox-, Akku-Saver- oder sonstige Automationen dürfen unabhängig weiterlaufen, solange sie nicht dieselben gemappten SolarEdge-Ziele schreiben.
