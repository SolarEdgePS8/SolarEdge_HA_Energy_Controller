# Voraussetzungen

## Unterstützte Umgebung

Der Controller ist als Home-Assistant-Package-Bundle aufgebaut. Er ist keine HACS-Integration.

Empfohlen:

- Home Assistant OS oder Home Assistant Supervised;
- aktuelle Home-Assistant-Version;
- Terminal & SSH Add-on;
- aktivierte Packages in `configuration.yaml`;
- Zugriff auf `/config` und `/share`;
- Python 3 innerhalb der Home-Assistant-Umgebung.

Beispiel für die Package-Einbindung:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

Nach Änderungen immer prüfen:

```bash
ha core check
```

## Pflichtdaten

### SolarEdge Charge-Limit

Eine schreibbare `number.*`-Entity für die maximale Ladeleistung des Speichers.

```dotenv
CHARGE_LIMIT_ENTITY=number.example_storage_charge_limit
```

Der Controller erwartet Werte in Watt. Das Projektmodell verwendet üblicherweise `0 W` zum Sperren und `5000 W` zum Freigeben. Die tatsächlichen Grenzen müssen zur eigenen Anlage passen.

### Akku-SoE

Ein Sensor mit dem Ladezustand in Prozent:

```dotenv
BATTERY_SOC_ENTITY=sensor.example_battery_soc
```

Erwartet werden Einheit `%`, Werte ungefähr zwischen `0` und `100` sowie regelmäßige Aktualisierung.

### Nutzbare Akkukapazität

Als feste Zahl:

```dotenv
BATTERY_CAPACITY_KWH=14.0
```

oder optional als Sensor:

```dotenv
BATTERY_CAPACITY_ENTITY=sensor.example_battery_capacity
```

### PV-Prognosen

Mindestens:

```dotenv
PV_FORECAST_TODAY_REMAINING_ENTITY=sensor.example_pv_today_remaining
PV_FORECAST_TODAY_TOTAL_ENTITY=sensor.example_pv_today_total
PV_FORECAST_TOMORROW_ENTITY=sensor.example_pv_tomorrow
```

Erwartete Einheit: `kWh`.

### Aktuelle PV-Leistung und Hausverbrauch

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.example_pv_power
LIVE_CONSUMPTION_POWER_ENTITIES=sensor.example_house_power
```

Diese Einträge erwarten **Momentanleistung** in `W` oder `kW`, keine Energiezähler in `kWh`.

Mehrere Sensoren können kommasepariert angegeben werden. Der Controller verwendet den ersten gültigen Wert.

## Optionale SolarEdge-Ziele

```dotenv
DISCHARGE_LIMIT_ENTITY=
COMMAND_MODE_ENTITY=
STORAGE_CONTROL_MODE_ENTITY=
BACKUP_RESERVE_ENTITY=
```

Ein leerer Eintrag deaktiviert den jeweiligen Writer. Das ist sinnvoll, wenn die Integration die Funktion nicht anbietet oder eine bestehende Automation Eigentümer bleiben soll.

## Optionale Integrationen

- Wetter verbessert die zeitliche Planung, ist aber kein Pflichtbestandteil.
- Die SQLite-Recorder-Auswertung verbessert Verbrauchsprognosen; ohne Historie gelten Fallbackwerte.
- evcc und EVOpt sind ausschließlich für den vierten Modus erforderlich.
- Fahrzeug-, Preis- oder Wärmepumpenlogik wird nur über neutrale externe Signale angebunden.
