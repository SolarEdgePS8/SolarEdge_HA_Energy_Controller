# Modus: Eigenverbrauch maximieren

## Ziel

Der Akku wird für den normalen Eigenverbrauch freigegeben. Der Charge-Writer öffnet das Charge-Limit auf den zulässigen Maximalwert.

## Benötigte Daten

Die gemeinsame Controller-Safety verlangt weiterhin alle Pflicht-Mappings aus der Erstinstallation. Wetter, SQL und evcc werden für die Modusentscheidung nicht verwendet.

## Sicherheitsverhalten

- Master aus: kein Writerzugriff;
- Config oder Sanity ungültig: Writer gesperrt;
- optionaler Command-/Storage-Control-Writer nur bei vorhandenem Mapping;
- keine Prognoseentscheidung über Start- oder Endzeit.

## Funktionstest

Bei gültiger Konfiguration und eingeschaltetem Master:

```text
input_select.se_nf_optimization_mode = Eigenverbrauch maximieren
sensor.se_nf_desired_target = 5000
```

Der tatsächliche Wert darf je nach Hardwaregrenze abweichen.
