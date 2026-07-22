# Entity-Mapping: die eigenen Sensoren richtig zuordnen

Der Controller enthält bewusst keine fest verdrahteten Entity-IDs. Eine SolarEdge-Anlage mit einem Wechselrichter, eine Anlage mit mehreren Wechselrichtern und eine Installation mit umbenannten Entities sehen in Home Assistant unterschiedlich aus. Deshalb werden die lokalen Entities einmalig in `config/site_config.env` zugeordnet.

## Grundregel

Ein Mapping beschreibt immer **Bedeutung und Einheit**, nicht einen bestimmten Hersteller-Sensornamen.

```text
Leistung: W
Energie:  kWh
Ladestand: %
Preis:    derzeit kein Pflicht-Mapping des Controller-Kerns
```

`LIVE_PV_POWER_ENTITIES` darf beispielsweise keinen Tageszähler in `kWh` enthalten.

Ausführliche Quellen, Integrationen und optionale YAML-Beispiele: [Sensorquellen und eigene Zusatzsensoren](12_SENSOR_SOURCES_AND_EXAMPLES.md).

## Sicherster Weg: read-only Mapping-Assistent

Der Assistent liest ausschließlich `/api/states`. Er ruft keinen Home-Assistant-Service auf, ändert keinen Helper und aktiviert keinen Writer.

### Home Assistant OS / Supervised

Im Terminal- oder SSH-Add-on:

```bash
cd /share/se_controller_release_rc4/SolarEdge_HA_Energy_Controller

python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

### Home Assistant Container / Core

```bash
export HA_TOKEN='DEIN_LONG_LIVED_ACCESS_TOKEN'
export HA_API_URL='http://homeassistant:8123/api'

python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

### Offline mit exportierter State-Liste

```bash
python3 scripts/discover_entities.py \
  --states-file /pfad/ha_states.json \
  --report /pfad/mapping_report.json \
  --output config/site_config.env
```

Die erzeugte Datei bleibt absichtlich gesperrt:

```dotenv
SITE_CONFIG_CONFIRMED=NO
EVOPT_ENABLED=NO
```

Der Assistent bewertet Kandidaten mit `high`, `medium` oder `low`. Das ist nur eine fachliche Vorauswahl. Entity, Einheit, Aktualisierung und Writer-Eigentümerschaft müssen vor der Aktivierung manuell geprüft werden.

> Der JSON-Bericht enthält lokale Entity-IDs. Vor dem Hochladen in ein öffentliches Issue bereinigen.

## Pflicht-Mappings

| Variable | Erwartung | Typische Quelle | Prüfung |
|---|---|---|---|
| `CHARGE_LIMIT_ENTITY` | schreibbare `number.*`, `W` | SolarEdge Modbus Multi | Service `number.set_value`, Min/Max, Rückmeldung |
| `BATTERY_SOC_ENTITY` | `sensor.*`, `%`, 0–100 | SolarEdge-Batterie | aktuelle plausible Werte |
| `BATTERY_CAPACITY_ENTITY` | optionaler Sensor, bevorzugt `kWh` | SolarEdge-Batterie | Gesamtkapazität, nicht SoC |
| `BATTERY_CAPACITY_KWH` | manueller Fallback in `kWh` | Datenblatt/Anlagenkonfiguration | tatsächlich nutzbare Gesamtkapazität |
| `PV_FORECAST_TODAY_REMAINING_ENTITY` | `sensor.*`, `kWh` | Forecast-Anbieter oder Template | Restenergie ab jetzt bis Tagesende |
| `PV_FORECAST_TODAY_TOTAL_ENTITY` | `sensor.*`, `kWh` | Forecast-Anbieter oder Template | komplette Tagesprognose |
| `PV_FORECAST_TOMORROW_ENTITY` | `sensor.*`, `kWh` | Forecast-Anbieter oder Template | komplette Prognose morgen |
| `LIVE_PV_POWER_ENTITIES` | priorisierte Sensorliste, **W** | Wechselrichter/Power-Flow | Momentanleistung, keine Energie |
| `LIVE_CONSUMPTION_POWER_ENTITIES` | priorisierte Sensorliste, **W** | Smart Meter/Power-Flow | Hausverbrauch, keine Energie |

### Typische SolarEdge-Modbus-Multi-Namen

Bei einem Wechselrichter `i1` und einer Batterie `b1` werden häufig folgende IDs erzeugt:

```dotenv
CHARGE_LIMIT_ENTITY=number.solaredge_i1_storage_charge_limit
DISCHARGE_LIMIT_ENTITY=number.solaredge_i1_storage_discharge_limit
BACKUP_RESERVE_ENTITY=number.solaredge_i1_backup_reserve
BATTERY_SOC_ENTITY=sensor.solaredge_i1_b1_state_of_energy
BATTERY_CAPACITY_ENTITY=sensor.solaredge_i1_b1_maximum_energy
LIVE_PV_POWER_ENTITIES=sensor.solaredge_i1_ac_power
```

Das sind **Muster**, keine garantierten IDs. Wechselrichterindex, Batterieindex, Gerätename und manuelle Umbenennung verändern die Entity-ID.

## Priorisierte Listen: nicht addieren

Beispiel:

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.pv_power_raw,sensor.solaredge_i1_ac_power
```

Der Controller verwendet den ersten Sensor, dessen Zustand gültig ist. Die Werte werden nicht summiert.

Empfehlung:

1. direkte, schnelle und plausible Quelle;
2. zweite unabhängige Quelle;
3. optional ein geglätteter Sensor als später Fallback.

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.pv_power_raw,sensor.pv_power_filtered,sensor.solaredge_i1_ac_power
```

Alle Einträge müssen **Watt** liefern. Ein Sensor in `kW` muss vorher mit einem Template auf `W` normiert werden. Ein Sensor in `kWh` ist grundsätzlich falsch.

## Optionale SolarEdge-Ziele

```dotenv
DISCHARGE_LIMIT_ENTITY=
COMMAND_MODE_ENTITY=
COMMAND_MODE_GRID_OPTION=
COMMAND_MODE_DEFAULT_OPTION=
STORAGE_CONTROL_MODE_ENTITY=
STORAGE_CONTROL_REMOTE_OPTION=
BACKUP_RESERVE_ENTITY=
```

Leer bedeutet: Der zugehörige Writer ist deaktiviert.

Nur eintragen, wenn:

- die Entity wirklich vorhanden ist;
- ihre Optionen und Einheit geprüft sind;
- der Controller der einzige Writer für dieses Ziel sein darf;
- ein Rollback auf den ursprünglichen Zustand möglich ist.

## Optionale Datenquellen

```dotenv
PV_FORECAST_DAY_AFTER_TOMORROW_ENTITY=
WEATHER_ENTITY=weather.home
PV_YIELD_TODAY_ENTITY=
CONSUMPTION_TODAY_ENTITY=
PV_LIFETIME_ENTITY=
FORECAST_NOW_ENTITY=
```

| Mapping | Einheit/Bedeutung | Bemerkung |
|---|---|---|
| übermorgen | `kWh` | verbessert mehrtägige Planung |
| Wetter | `weather.*` | muss stündlichen Forecast unterstützen |
| PV heute | `kWh` | Tagesenergie, nicht Momentanleistung |
| Verbrauch heute | `kWh` | Tagesenergie |
| PV Lifetime | `Wh`, `kWh` oder `MWh` | monoton steigender Energiezähler bevorzugt |
| Prognose jetzt | `W` | optionale aktuelle Prognoseleistung |

## evcc/EVOpt

```dotenv
EVOPT_ENABLED=NO
EVOPT_BASE_URL=http://EVCC-HOST:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
EVOPT_BATTERY_MODE_ENTITY=
```

- `EVOPT_BASE_URL` enthält weder `/api` noch `/api/state`.
- Die Home-Assistant-Integration `ha-evcc` ist für EVOpt nicht erforderlich; der Controller liest `/api/state` direkt.
- `EVOPT_BATTERY_MODE_ENTITY` ist nur ein optionales Zusatzsignal und ersetzt nicht den Optimizer-Plan.
- EVOpt erst nach erfolgreichem API- und Batterie-Matching aktivieren.

## Eigene Sensoren

Neutrale, optionale Beispiele liegen unter [`examples/sensors`](../examples/sensors/README.md). Sie werden nicht automatisch installiert und schreiben nicht auf SolarEdge.

Die Namen der Referenzinstallation wie `sensor.power_solar_generation_filtered` oder `sensor.pv_prognose_heute_verbleibend_biased` sind keine allgemeinen Standards. Ohne die originale Definition dürfen sie nicht anhand des Namens nachgebaut und als Original veröffentlicht werden.

## Konfiguration anwenden

Nach manueller Prüfung:

1. alle Pflichtfelder ausfüllen;
2. `SITE_CONFIG_CONFIRMED=YES` setzen;
3. Master weiterhin AUS lassen;
4. anwenden:

```bash
python3 scripts/apply_site_config.py config/site_config.env
```

5. prüfen:

```bash
bash scripts/run_first_checks.sh
python3 scripts/check_external_writer_conflicts.py "${CONFIG_ROOT:-/config}"
```

Erst nach `PASS=True`, `sensor.se_nf_config_check=ok` und `sensor.se_nf_sanity_check=ok` darf der Master eingeschaltet werden.

## Datenschutz

Nicht veröffentlichen:

- `SUPERVISOR_TOKEN` oder Long-Lived Access Token;
- private IP-Adressen und interne Hostnamen;
- Seriennummern, MAC-Adressen und Standortdaten;
- `secrets.yaml`;
- unbereinigte State- oder Mapping-Berichte.
