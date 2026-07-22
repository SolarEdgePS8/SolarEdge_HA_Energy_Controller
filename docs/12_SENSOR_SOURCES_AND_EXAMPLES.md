# Sensorquellen, Mapping und eigene Zusatzsensoren

Diese Anleitung erklärt, **welche Daten der Controller benötigt, woher sie typischerweise kommen und wie eigene Sensoren sicher angepasst werden**. Sie ergänzt die kurze [Entity-Mapping-Anleitung](03_ENTITY_MAPPING.md).

Der Controller ist absichtlich nicht an einen festen Forecast-, Wetter-, Strompreis- oder evcc-Anbieter gebunden. Er erwartet fertige Home-Assistant-Entities mit klarer Einheit und Bedeutung.

## 1. Drei Arten von Entities

### A. SolarEdge-Entities

Diese Entities kommen direkt aus einer SolarEdge-Modbus-Integration. Für dieses Projekt ist [SolarEdge Modbus Multi](https://github.com/WillCodeForCats/solaredge-modbus-multi) die am besten dokumentierte Referenz.

Typische Entity-Namen einer Installation mit Wechselrichterindex `i1` und Batterieindex `b1`:

```text
number.solaredge_i1_storage_charge_limit
number.solaredge_i1_storage_discharge_limit
number.solaredge_i1_backup_reserve
sensor.solaredge_i1_b1_state_of_energy
sensor.solaredge_i1_b1_maximum_energy
sensor.solaredge_i1_ac_power
```

Diese Namen sind **Beispiele, keine Garantie**. Index, Gerätename und manuelle Umbenennungen verändern die Entity-ID.

### B. Entities anderer Integrationen

Beispiele:

- `weather.*` aus einer Wetterintegration;
- Forecast-Sensoren aus Forecast.Solar, Solcast oder einem anderen PV-Prognosedienst;
- evcc-Entities aus [marq24/ha-evcc](https://github.com/marq24/ha-evcc);
- Preis-Sensoren aus [EPEX Spot](https://github.com/mampfes/ha_epex_spot);
- Kosten-Sensoren aus [Dynamic Energy Cost](https://github.com/martinarva/dynamic_energy_cost).

Diese Integrationen sind nicht Teil des Controllers und erzeugen installationsabhängige Entity-Namen.

### C. Selbst gebaute Sensoren

Dazu gehören Template-, Filter-, Integral- und Utility-Meter-Sensoren. Häufige Zwecke:

- Rohleistung in eine einheitliche Einheit umrechnen;
- eine geglättete PV-Leistung bereitstellen;
- aus Leistung einen Energiezähler in kWh erzeugen;
- einen Tageszähler bilden;
- Prognosen eines Anbieters auf die benötigte Bedeutung abbilden;
- einen evcc-Batteriemodus normalisieren.

Neutrale Beispiele liegen unter [`examples/sensors`](../examples/sensors/README.md).

> Die Namen der Referenzinstallation wie `sensor.pv_prognose_heute_verbleibend_biased` oder `sensor.power_solar_generation_filtered` sind keine allgemeinen Standards. Der bereitgestellte Konfigurationsexport belegt ihre Verwendung, aber die hochgeladene Package-Sammlung enthält nicht alle ursprünglichen Definitionen. Deshalb werden diese Sensoren nicht als vermeintlich universeller Originalcode veröffentlicht.

## 2. Pflicht-Mappings

| Mapping | Bedeutung | Domain/Einheit | Typische Quelle |
|---|---|---|---|
| `CHARGE_LIMIT_ENTITY` | maximales Laden des Speichers | `number.*`, `W` | SolarEdge Modbus Multi |
| `BATTERY_SOC_ENTITY` | aktueller SoC/SoE | `sensor.*`, `%` | SolarEdge Modbus Multi |
| `BATTERY_CAPACITY_ENTITY` | erkannte Kapazität | `sensor.*`, bevorzugt `kWh` | SolarEdge Modbus Multi |
| `BATTERY_CAPACITY_KWH` | manueller Kapazitäts-Fallback | Zahl in `kWh` | Datenblatt/Anlagenkonfiguration |
| `PV_FORECAST_TODAY_REMAINING_ENTITY` | noch erwartete PV-Energie heute | `sensor.*`, `kWh` | Forecast-Integration oder Template |
| `PV_FORECAST_TODAY_TOTAL_ENTITY` | gesamte PV-Prognose heute | `sensor.*`, `kWh` | Forecast-Integration oder Template |
| `PV_FORECAST_TOMORROW_ENTITY` | gesamte PV-Prognose morgen | `sensor.*`, `kWh` | Forecast-Integration oder Template |
| `LIVE_PV_POWER_ENTITIES` | aktuelle PV-Leistung | Liste von `sensor.*`, **`W`** | Wechselrichter, Smart Meter, Power Flow |
| `LIVE_CONSUMPTION_POWER_ENTITIES` | aktueller Hausverbrauch | Liste von `sensor.*`, **`W`** | Smart Meter, Power Flow |

### Leistung und Energie nicht verwechseln

```text
W       = aktuelle Leistung für die LIVE-Mappings
kW      = Leistung, muss vor dem Mapping auf W normiert werden
Wh/kWh  = Energie über einen Zeitraum
```

Ein Tagesenergiezähler in `kWh` ist kein Ersatz für `LIVE_PV_POWER_ENTITIES`.

## 3. Priorisierte Fallbacklisten

`LIVE_PV_POWER_ENTITIES` und `LIVE_CONSUMPTION_POWER_ENTITIES` sind kommagetrennte **Prioritätslisten**. Die Werte werden nicht addiert. Der Controller verwendet den ersten aktuell gültigen Sensor.

Beispiel:

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.pv_power_raw,sensor.pv_power_filtered,sensor.solaredge_i1_ac_power
```

Prüfen:

1. erster Sensor: beste und schnellste Quelle;
2. zweiter Sensor: sinnvolle Ersatzquelle;
3. dritter Sensor: robuster letzter Fallback;
4. alle Werte müssen dieselbe physikalische Größe darstellen;
5. Quellen in `kW` müssen vor dem Mapping mit einem Template auf `W` normiert werden; der Controller interpretiert den Zahlenwert der LIVE-Liste direkt als Watt.

Ein geglätteter `_filtered`-Sensor ist optional. Er kann für Planung und Anzeige nützlich sein, reagiert aber langsamer. Für schnelle Sicherheitsentscheidungen sollte eine ungefilterte, plausible Quelle priorisiert werden.

## 4. SolarEdge Modbus Multi

Die Integration arbeitet lokal über Modbus/TCP. Batterie- und Steuerfunktionen müssen in den Integrationsoptionen aktiviert werden. Die Integration weist darauf hin, dass Batterie- und Kontrollfunktionen teilweise auf nicht öffentlich verfügbarer Dokumentation oder Nutzererkenntnissen beruhen und möglicherweise nicht offiziell von SolarEdge unterstützt werden.

Für den Controller besonders relevant:

| SolarEdge-Funktion | Erwartete HA-Entity | Verhalten |
|---|---|---|
| Storage Charge Limit | `number.*`, W | `0` stoppt Laden |
| Storage Discharge Limit | `number.*`, W | `0` stoppt Entladen |
| Backup Reserve | `number.*`, % | optionale Reserve |
| Battery State of Energy | `sensor.*`, % | Ladestand |
| Battery Maximum Energy | `sensor.*`, kWh | Kapazität |
| Inverter AC Power | `sensor.*`, W | möglicher PV-Leistungs-Fallback |

Storage Charge/Discharge Limit sind in SolarEdge Modbus Multi nur im Storage-Control-Modus **Remote Control** verfügbar. Power-Control-Optionen sind aus Sicherheitsgründen standardmäßig deaktiviert.

Vor dem Mapping:

```text
Einstellungen → Geräte & Dienste → SolarEdge Modbus Multi → Konfigurieren
```

Dann:

1. Batterieerkennung prüfen;
2. Storage Control aktivieren;
3. Entity öffnen und Einheit prüfen;
4. erlaubten Min-/Max-Bereich notieren;
5. ursprüngliche SolarEdge-Einstellungen sichern;
6. noch keinen Controller-Master aktivieren.

Weitere Details:

- [SolarEdge Modbus Multi Wiki](https://github.com/WillCodeForCats/solaredge-modbus-multi/wiki)
- [Storage Control Options](https://github.com/WillCodeForCats/solaredge-modbus-multi/wiki/Storage-Control-Options)
- [Power Control Options](https://github.com/WillCodeForCats/solaredge-modbus-multi/wiki/Power-Control-Options-%E2%80%90-Configuration)

## 5. PV-Prognosen

Der Controller benötigt drei Energieprognosen:

```text
heute verbleibend  kWh
heute gesamt       kWh
morgen gesamt      kWh
```

Viele Anbieter liefern nur „heute gesamt“ und „morgen gesamt“. Dann kann „heute verbleibend“ aus Tagesprognose minus bereits erzeugter PV-Energie berechnet werden. Ein neutrales Beispiel steht in [`pv_forecast_adapter.yaml`](../examples/sensors/pv_forecast_adapter.yaml).

Wichtig:

- niemals Prognoseleistung in W als Tagesenergie in kWh mappen;
- negative Restprognosen auf `0` begrenzen;
- `availability` verwenden;
- `unknown` und `unavailable` nicht stillschweigend in eine scheinbar gültige Prognose umwandeln;
- Anbieterwerte und lokal korrigierte „biased“-Werte klar unterscheiden.

## 6. Wetter

Wetter ist optional. Der Controller benötigt keine separaten Temperatur-, Niederschlags- oder Bewölkungssensoren, sondern eine `weather.*`-Entity, die über Home Assistants Aktion `weather.get_forecasts` eine stündliche Vorhersage liefern kann.

Beispiel:

```dotenv
WEATHER_ENTITY=weather.home
```

Mögliche Quellen:

- eingebaute oder andere Home-Assistant-Wetterintegrationen;
- [DWD Weather](https://github.com/FL550/dwd_weather) in Deutschland.

DWD Weather stellt eine normale Weather-Entity bereit. Zusätzliche stündliche DWD-Sensoren sind für den Controller nicht erforderlich. Entscheidend ist, dass die gewählte `weather.*`-Entity einen stündlichen Forecast unterstützt.

Prüfung in Entwicklerwerkzeuge → Aktionen:

```yaml
action: weather.get_forecasts
target:
  entity_id: weather.home
data:
  type: hourly
response_variable: weather_forecast
```

## 7. evcc und ha-evcc

Der Controller liest EVOpt direkt aus:

```text
<EVOPT_BASE_URL>/api/state
```

Dafür ist die Home-Assistant-Integration [marq24/ha-evcc](https://github.com/marq24/ha-evcc) **nicht erforderlich**. Sie ist optional, wenn evcc-Daten zusätzlich als HA-Entities in Dashboards oder Automationen genutzt werden sollen.

Die ha-evcc-Integration ist ein inoffizielles Projekt. Der bei der Einrichtung vergebene Name beeinflusst die erzeugten Entity-IDs; außerdem sind einige Sensoren standardmäßig deaktiviert. Deshalb darf die Dokumentation keine feste `sensor.evcc_*`-ID voraussetzen.

Optionales Mapping:

```dotenv
EVOPT_BATTERY_MODE_ENTITY=sensor.example_evcc_battery_mode
```

Dieses Mapping ist nicht der EVOpt-Plan. Es ist nur ein zusätzliches defensives Signal für eine mögliche Netzladeanforderung. EVOpt selbst wird weiterhin über `/api/state` geprüft.

## 8. Dynamische Strompreise und Kosten

EPEX Spot und Dynamic Energy Cost sind nützliche Zusatzintegrationen, aber derzeit **keine Pflichtquelle des Controller-Kerns**.

### EPEX Spot

[EPEX Spot für Home Assistant](https://github.com/mampfes/ha_epex_spot) kann unter anderem liefern:

- aktuellen Gesamtpreis;
- reinen Marktpreis;
- Tagesmittel, Median, Minimum und Maximum;
- Preisrang und Quantil;
- Zeitreihen für heute und morgen als Attribute.

Für Entscheidungen sollte normalerweise der **Gesamtpreis inklusive eigener Zuschläge und Steuern** verwendet werden, nicht nur der Börsenpreis.

### Dynamic Energy Cost

[Dynamic Energy Cost](https://github.com/martinarva/dynamic_energy_cost) verbindet:

- einen Preis-Sensor;
- genau einen Leistungs- oder Energieverbrauchssensor;

und erzeugt daraus aktuelle und periodische Kosten. Diese Sensoren eignen sich für Dashboard, Statistik und Erfolgskontrolle. Sie sind kein Ersatz für `LIVE_CONSUMPTION_POWER_ENTITIES` oder eine PV-Prognose.

Ein neutraler Preisadapter steht in [`electricity_price_adapter.yaml`](../examples/sensors/electricity_price_adapter.yaml).

## 9. Read-only Mapping-Assistent

Der Assistent liest `/api/states`, bewertet Kandidaten nach Domain, Einheit und Namensmuster und kann eine **nicht aktivierte** `site_config.env` erzeugen.

Home Assistant OS / Supervised:

```bash
python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

Container / Core:

```bash
export HA_TOKEN='DEIN_TOKEN'
export HA_API_URL='http://homeassistant:8123/api'

python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

Offline mit zuvor exportierten States:

```bash
python3 scripts/discover_entities.py \
  --states-file /share/ha_states.json \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

Sicherheitsmerkmale:

- ruft keinen Home-Assistant-Schreibservice auf;
- aktiviert keinen Writer;
- erzeugt immer `SITE_CONFIG_CONFIRMED=NO`;
- setzt `EVOPT_ENABLED=NO`;
- lässt unsichere oder mehrdeutige Felder leer;
- zeigt Kandidaten und Vertrauenswert;
- Bericht kann lokale Entity-IDs enthalten und darf nicht ungeprüft veröffentlicht werden.

## 10. Was aus der Referenzinstallation übernommen werden darf

Der private Rückwärtsexport zeigt, welche Bedeutungen in einer realen, geprüften Anlage gemappt waren. Öffentlich übertragbar sind vor allem die **Sensorrollen und Einheiten**, nicht die private IP-Adresse, die konkrete Batteriegröße oder lokale Namen.

Beispiel einer neutralisierten SolarEdge-Minimalkonfiguration:

```dotenv
SITE_CONFIG_CONFIRMED=NO
CHARGE_LIMIT_ENTITY=number.solaredge_i1_storage_charge_limit
BATTERY_SOC_ENTITY=sensor.solaredge_i1_b1_state_of_energy
BATTERY_CAPACITY_ENTITY=sensor.solaredge_i1_b1_maximum_energy
BATTERY_CAPACITY_KWH=14.0
LIVE_PV_POWER_ENTITIES=sensor.solaredge_i1_ac_power
LIVE_CONSUMPTION_POWER_ENTITIES=sensor.example_house_power_w
EVOPT_ENABLED=NO
EVOPT_BASE_URL=http://EVCC-HOST:7070
```

Die folgenden Namen der Referenzinstallation sind dagegen lokale Zusatzsensoren und dürfen nicht als Integrationsstandard bezeichnet werden:

```text
sensor.power_solar_generation_filtered
sensor.pv_prognose_heute_verbleibend_biased
sensor.pv_prognose_heute_06_24_biased
sensor.pv_prognose_morgen_biased
sensor.pv_prognose_ubermorgen_biased
sensor.pv_prognose_leistung_jetzt_biased_interpoliert
sensor.gesamtverbrauch_tag
sensor.energy_solar_generation_dashboard
sensor.evcc_battery_mode_value
```

Die bereitgestellte Package-Sammlung enthält Referenzen auf diese Entities, aber nicht alle ursprünglichen Definitionen. Deshalb veröffentlicht dieses Repository neutrale Beispieladapter statt erfundener „Originalsensoren“.

## 11. Controller-interner Tages-PV-Zähler

Der Controller enthält bereits einen eigenen Utility Meter:

```yaml
utility_meter:
  se_nf_pv_actual_today_meter:
    source: sensor.se_nf_pv_actual_meter_source_energy
    cycle: daily
```

Damit dieser Sensor funktioniert, muss `PV_LIFETIME_ENTITY` auf einen gültigen, monoton steigenden PV-Energiezähler in `Wh`, `kWh` oder `MWh` zeigen. Der Controller normiert diese Quelle intern auf `kWh` und bildet daraus den Tageswert.

Ein zusätzlicher selbst gebauter Tageszähler ist nur nötig, wenn die Anlage noch keinen geeigneten Lifetime-Energiezähler bereitstellt. Siehe [`daily_energy_helpers.yaml`](../examples/sensors/daily_energy_helpers.yaml).

## 12. Prüfliste pro Sensor

Vor Übernahme in `site_config.env`:

```text
[ ] Entity existiert
[ ] Zustand ist numerisch, wenn ein Zahlenwert erwartet wird
[ ] Einheit ist korrekt
[ ] device_class/state_class passen fachlich
[ ] Aktualisierungsintervall ist ausreichend
[ ] unknown/unavailable werden behandelt
[ ] Quelle misst genau die benötigte Größe
[ ] keine doppelte Zählung oder Addition von Fallbackquellen
[ ] bei einem SolarEdge-Ziel existiert kein zweiter Writer
[ ] private IPs, Tokens und Seriennummern sind nicht in öffentlichen Beispielen
```

Erst danach:

```dotenv
SITE_CONFIG_CONFIRMED=YES
```

und anschließend:

```bash
python3 scripts/apply_site_config.py config/site_config.env
bash scripts/run_first_checks.sh
```

Der Controller-Master bleibt bis zum erfolgreichen Abschluss ausgeschaltet.
