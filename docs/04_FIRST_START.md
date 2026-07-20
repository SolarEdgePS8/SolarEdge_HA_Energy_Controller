# Erster Start und Aktivierung

## Ausgangszustand

Nach Installation und Mapping muss gelten:

```text
input_boolean.se_netzdienlich_enabled = off
input_boolean.se_nf_site_config_confirmed = on
sensor.se_nf_config_check = ok
sensor.se_nf_sanity_check = ok
binary_sensor.se_nf_controller_write_enabled = off
binary_sensor.se_nf_risk_flag = off
```

## Erster Modus

Für den ersten Funktionstest empfiehlt sich `Eigenverbrauch maximieren`. Dieser Modus benötigt keine Wetter-, SQL- oder EVOpt-Daten.

## Master einschalten

Erst danach `input_boolean.se_netzdienlich_enabled` einschalten. Die Writer-Freigabe `binary_sensor.se_nf_controller_write_enabled` muss auf `on` wechseln.

## Beobachten

| Entity | Erwartung |
|---|---|
| `sensor.se_nf_config_check` | `ok` |
| `sensor.se_nf_sanity_check` | `ok` |
| `binary_sensor.se_nf_risk_flag` | `off` |
| `sensor.se_nf_desired_target` | plausibler Wert in W |
| `sensor.se_nf_charge_limit_actual` | entspricht dem Gerät |
| `sensor.se_nf_writer_mode` | `idle`, `write` oder dokumentierter Sperrgrund |
| `sensor.se_nf_writer_last_decision` | nachvollziehbare Entscheidung |
| `sensor.se_nf_start_gate_reason` | kurzer verständlicher Grund |

## Sofort ausschalten

Master ausschalten, wenn Config oder Sanity nicht `ok` sind, das Risk-Flag `on` ist, Zielwerte außerhalb des erlaubten Bereichs liegen oder mehrere Automationen dasselbe SolarEdge-Ziel beschreiben.

Command-Mode oder Storage-Control nur aktivieren, wenn die jeweilige Entity und die Optionswerte sicher zugeordnet wurden.
