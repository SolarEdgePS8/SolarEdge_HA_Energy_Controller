# Voraussetzungen

## Home Assistant

Empfohlen wird Home Assistant OS oder Supervised mit Terminal-/SSH-Zugriff auf `/config` und `/share`.

In `configuration.yaml` müssen Packages aktiviert sein:

```yaml
homeassistant:
  packages: !include_dir_named packages
```

## Pflichtdaten

Für RC2 werden benötigt:

- schreibbares SolarEdge-Charge-Limit als `number.*`;
- Akku-Ladestand in `%`;
- nutzbare Akkukapazität als Sensor oder manueller Wert in `kWh`;
- PV-Prognose heute verbleibend in `kWh`;
- PV-Prognose heute gesamt in `kWh`;
- PV-Prognose morgen in `kWh`;
- aktuelle PV-Leistung in `W`;
- aktueller Hausverbrauch in `W`.

Die zentrale Safety-Prüfung verwendet die Prognose- und Akkudaten unabhängig vom ausgewählten Modus. Deshalb müssen die Pflicht-Mappings auch für „Eigenverbrauch maximieren“ gültig sein.

## Optionale Daten

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
