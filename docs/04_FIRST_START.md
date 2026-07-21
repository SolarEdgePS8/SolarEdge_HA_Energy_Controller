# Erster Start

## Vorbedingungen

In Home Assistant prüfen:

```text
input_boolean.se_nf_site_config_confirmed = on
sensor.se_nf_config_check = ok
sensor.se_nf_sanity_check = ok
binary_sensor.se_nf_risk_flag = off
binary_sensor.se_nf_controller_write_enabled = off
```

Der letzte Wert ist bei ausgeschaltetem Master korrekt.

## Modus wählen

Über `input_select.se_nf_optimization_mode` einen Modus auswählen.

## Master einschalten

```text
input_boolean.se_netzdienlich_enabled = on
```

Danach sollte `binary_sensor.se_nf_controller_write_enabled = on` werden.

## Beobachten

Mindestens folgende Entities beobachten:

- `sensor.se_nf_start_gate_reason`;
- `sensor.se_nf_desired_target`;
- `sensor.se_nf_charge_limit_actual`;
- `sensor.se_nf_writer_mode`;
- `sensor.se_nf_writer_last_decision`;
- `binary_sensor.se_nf_risk_flag`.

Bei einem unerwarteten Zustand den Master sofort ausschalten. Die Writer werden damit gesperrt.
