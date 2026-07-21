# Entity-Mapping

Die Datei `config/site_config.env` verbindet den portablen Controller mit den Entities der eigenen Anlage.

## Pflichtfelder

| Schlüssel | Erwartet | Einheit |
|---|---|---|
| `CHARGE_LIMIT_ENTITY` | schreibbare SolarEdge-Entity | `number.*`, W |
| `BATTERY_SOC_ENTITY` | aktueller Akku-Ladestand | `%` |
| `BATTERY_CAPACITY_KWH` | manuelle nutzbare Kapazität | `kWh` |
| `PV_FORECAST_TODAY_REMAINING_ENTITY` | Restprognose heute | `kWh` |
| `PV_FORECAST_TODAY_TOTAL_ENTITY` | Gesamtprognose heute | `kWh` |
| `PV_FORECAST_TOMORROW_ENTITY` | Prognose morgen | `kWh` |
| `LIVE_PV_POWER_ENTITIES` | aktuelle PV-Leistung | `W` |
| `LIVE_CONSUMPTION_POWER_ENTITIES` | aktueller Hausverbrauch | `W` |

### Leistung ist nicht Energie

`LIVE_PV_POWER_ENTITIES` und `LIVE_CONSUMPTION_POWER_ENTITIES` erwarten Momentanleistung in **Watt**. Energiezähler in `kWh` sind dafür ungeeignet.

Mehrere Fallbackquellen können durch Komma getrennt werden:

```dotenv
LIVE_PV_POWER_ENTITIES=sensor.pv_power,sensor.pv_power_filtered
```

`_filtered` ist nur ein mögliches eigenes Namensschema und keine Pflicht.

## Optionale SolarEdge-Ziele

| Schlüssel | Bedeutung |
|---|---|
| `DISCHARGE_LIMIT_ENTITY` | Entladegrenze |
| `COMMAND_MODE_ENTITY` | Storage Command Mode |
| `COMMAND_MODE_GRID_OPTION` | Option für Netzladen |
| `COMMAND_MODE_DEFAULT_OPTION` | normale Standardoption |
| `STORAGE_CONTROL_MODE_ENTITY` | Storage Control Mode |
| `STORAGE_CONTROL_REMOTE_OPTION` | Option für Remote Control |
| `BACKUP_RESERVE_ENTITY` | Backup-Reserve |

Nur mappen, wenn der Controller alleiniger Writer dieses Ziels sein soll. Sonst leer lassen.

## Entitäten finden

```bash
python3 scripts/discover_entities.py /config
```

Danach immer Konflikte prüfen:

```bash
python3 scripts/check_external_writer_conflicts.py /config
```
