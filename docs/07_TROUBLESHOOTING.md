# Fehlerdiagnose

## `sensor.se_nf_config_check` ist nicht `ok`

Prüfen:

- alle Pflicht-Mappings vorhanden;
- Ziel-Entities existieren;
- Einheiten stimmen;
- Site-Konfiguration bestätigt;
- Charge-Limit ist schreibbar.

## `sensor.se_nf_sanity_check` ist nicht `ok`

Mögliche Ursachen:

- Akku-SoE außerhalb `0–100`;
- PV-Prognosen ungültig;
- Akkukapazität fehlt;
- Live-Leistung nicht plausibel;
- Daten zu alt.

## Writer bleibt gesperrt

Prüfen:

```text
input_boolean.se_netzdienlich_enabled
input_boolean.se_nf_site_config_confirmed
sensor.se_nf_config_check
sensor.se_nf_sanity_check
binary_sensor.se_nf_risk_flag
input_boolean.se_nf_write_lock
```

## EVOpt fällt auf Netzdienlich zurück

Das ist das vorgesehene Sicherheitsverhalten. Prüfen:

- `EVOPT_ENABLED=YES`;
- evcc erreichbar;
- Basis-URL korrekt;
- Batterie eindeutig zugeordnet;
- Optimizer-Plan aktuell;
- Adapterstatus `ok`.

## SQL-Prognose ungültig

Prüfen:

- Recorder nutzt SQLite;
- Pfad ist korrekt;
- Tagesverbrauchssensor ist kumulativ;
- mindestens drei verwertbare Tage vorhanden;
- Entity befindet sich in der Recorder-Datenbank.

Ohne gültige SQL-Daten verwendet der Controller Fallbackwerte.

## Externer Writer-Konflikt

```bash
python3 scripts/check_external_writer_conflicts.py /config
```

Die gemeldete Automation muss entweder das Ziel nicht mehr direkt schreiben, als alleiniger Eigentümer bleiben während das Controller-Mapping leer ist oder auf einen neutralen Request-Helper umgestellt werden.

## Runtime-Checker

```bash
python3 /config/se_controller_runtime_checker.py \
  --report /share/se_controller_runtime_check.json
```
