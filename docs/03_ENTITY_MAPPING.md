# Entity-Mapping

Die Controllerlogik verwendet stabile interne `se_nf_*`-Entities. Lokale Geräte- und Prognosesensoren werden nur über die Site-Konfiguration zugeordnet.

## Grundregeln

- Entity-IDs vollständig und kleingeschrieben eintragen.
- Keine Anzeigenamen verwenden.
- Pflichtfelder dürfen nicht leer sein.
- Optionale Writer nur mappen, wenn der Controller dieses Ziel wirklich besitzen soll.
- Vor der Aktivierung jeden Sensor in **Entwicklerwerkzeuge → Zustände** prüfen.

## Pflichtfelder

| Schlüssel | Erwartung | Einheit |
|---|---|---|
| `CHARGE_LIMIT_ENTITY` | schreibbare Ladegrenze | W |
| `BATTERY_SOC_ENTITY` | Akku-Ladezustand | % |
| `BATTERY_CAPACITY_KWH` | nutzbare Kapazität | kWh |
| `PV_FORECAST_TODAY_REMAINING_ENTITY` | Restprognose heute | kWh |
| `PV_FORECAST_TODAY_TOTAL_ENTITY` | Gesamtprognose heute | kWh |
| `PV_FORECAST_TOMORROW_ENTITY` | Prognose morgen | kWh |
| `LIVE_PV_POWER_ENTITIES` | aktuelle PV-Leistung | W oder kW |
| `LIVE_CONSUMPTION_POWER_ENTITIES` | aktueller Hausverbrauch | W oder kW |

## Momentanleistung ist keine Energie

Richtig:

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.inverter_ac_power
LIVE_CONSUMPTION_POWER_ENTITIES=sensor.house_power
```

Falsch:

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.pv_energy_today
LIVE_CONSUMPTION_POWER_ENTITIES=sensor.daily_consumption
```

Ein Sensor mit `kWh` zählt Energie über einen Zeitraum. Für die Live-Leistung wird `W` oder `kW` benötigt.

## Fallbacklisten

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.pv_power_filtered,sensor.pv_power
```

Der Controller prüft die Liste von links nach rechts. `_filtered` ist nur ein mögliches Namensmuster und keine Voraussetzung.

## Optionale Writer

### Discharge-Limit

```dotenv
DISCHARGE_LIMIT_ENTITY=number.example_storage_discharge_limit
```

Leer lassen, wenn keine Entladesperre benötigt wird oder eine andere Automation Eigentümer bleibt.

### Command Mode

```dotenv
COMMAND_MODE_ENTITY=select.example_storage_command_mode
COMMAND_MODE_GRID_OPTION=Charge from Solar Power and Grid
COMMAND_MODE_DEFAULT_OPTION=Maximize Self Consumption
```

Die Optionswerte müssen exakt so geschrieben sein, wie sie im Attribut `options` der `select.*`-Entity stehen.

### Storage Control Mode

```dotenv
STORAGE_CONTROL_MODE_ENTITY=select.example_storage_control_mode
STORAGE_CONTROL_REMOTE_OPTION=Remote Control
```

## Optionale Datenquellen

| Schlüssel | Bedeutung |
|---|---|
| `BATTERY_CAPACITY_ENTITY` | dynamischer Kapazitätssensor |
| `PV_FORECAST_DAY_AFTER_TOMORROW_ENTITY` | Prognose übermorgen |
| `WEATHER_ENTITY` | Wetterintegration |
| `PV_YIELD_TODAY_ENTITY` | tatsächlicher PV-Ertrag heute |
| `CONSUMPTION_TODAY_ENTITY` | kumulierter Tagesverbrauch |
| `PV_LIFETIME_ENTITY` | fortlaufender PV-Gesamtzähler |
| `FORECAST_NOW_ENTITY` | prognostizierte PV-Leistung aktuell |

## Externe Signale

```dotenv
EXTERNAL_EV_CHARGING_ENTITY=binary_sensor.ev_charging
EXTERNAL_DISCHARGE_LOCK_ENTITY=input_boolean.external_discharge_lock
EXTERNAL_PEAK_LOCK_ENTITY=binary_sensor.price_peak
```

Die gemappte Entity muss mit `on` und `off` arbeiten. Ein leerer Wert wird als sicherer Zustand `off` behandelt.

## Konfiguration prüfen

```bash
bash scripts/run_first_checks.sh
```

Die aktuell übernommenen Mappings erscheinen im Runtime-Bericht.
