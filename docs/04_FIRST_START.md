# Erster Start

Der erste Start erfolgt erst nach erfolgreicher Installation, angewendeter Site-Konfiguration und vollständig bestandener Erstprüfung.

## 1. Sicheren Ausgangszustand prüfen

In Home Assistant müssen bei ausgeschaltetem Master gelten:

```text
input_boolean.se_netzdienlich_enabled = off
input_boolean.se_nf_site_config_confirmed = on
sensor.se_nf_config_check = ok
sensor.se_nf_sanity_check = ok
binary_sensor.se_nf_risk_flag = off
binary_sensor.se_nf_controller_write_enabled = off
```

`binary_sensor.se_nf_controller_write_enabled = off` ist bei ausgeschaltetem Master korrekt und beabsichtigt.

Zusätzlich muss `bash scripts/run_first_checks.sh` zuvor mit `PASS=True` beendet worden sein.

## 2. Betriebsart auswählen

Über `input_select.se_nf_optimization_mode` einen Modus auswählen:

- `Eigenverbrauch maximieren`;
- `Netzdienlich laden`;
- `Akku schonen`;
- `EVOpt optimiert`.

## 3. EVOpt vor Aktivierung prüfen

Dieser Abschnitt ist nur für `EVOpt optimiert` erforderlich.

Nach einem Home-Assistant-Neustart kann der Adapter zunächst ungefähr zwei Minuten stabilisieren. In dieser Zeit ist folgender Zustand normal:

```text
sensor.se_nf_evopt_status = warming_up
sensor.se_nf_active_control_label = Netzdienlicher Fallback
```

Vor dem Einschalten des Masters sollten danach gelten:

```text
sensor.se_nf_evopt_status = healthy
Attribut reason = ok
binary_sensor.se_nf_evopt_active_control = on
binary_sensor.se_nf_evopt_action_plan_consistent = on
binary_sensor.se_nf_evopt_plan_consistent = on
```

Der separate Entity-Name `sensor.se_nf_evopt_health_reason` existiert nicht. Der Health-Grund steht als Attribut `reason` am Sensor `sensor.se_nf_evopt_status` und als Attribut `health_reason` am Rohsensor `sensor.se_nf_evopt_adapter_raw`.

## 4. Controller-Master einschalten

In Home Assistant:

```text
input_boolean.se_netzdienlich_enabled = on
```

Danach sollte gelten:

```text
binary_sensor.se_nf_controller_write_enabled = on
```

Falls der Writer gesperrt bleibt, `sensor.se_nf_start_gate_reason` und `binary_sensor.se_nf_risk_flag` prüfen.

## 5. Relevante Werte beobachten

Mindestens folgende Entities beobachten:

```text
sensor.se_nf_start_gate_reason
sensor.se_nf_desired_target
sensor.se_nf_charge_limit_actual
sensor.se_nf_writer_mode
sensor.se_nf_writer_last_decision
binary_sensor.se_nf_risk_flag
binary_sensor.se_nf_controller_write_enabled
```

Im Modus EVOpt zusätzlich:

```text
sensor.se_nf_evopt_status
binary_sensor.se_nf_evopt_active_control
binary_sensor.se_nf_evopt_fallback_active
sensor.se_nf_evopt_fallback_code
sensor.se_nf_active_control_label
sensor.se_nf_evopt_action_raw
```

## 6. Sollwert und SolarEdge-Rückmeldung bewerten

`sensor.se_nf_desired_target` ist der vom Arbiter freigegebene Sollwert. `sensor.se_nf_charge_limit_actual` ist die von SolarEdge zurückgelesene Einstellung.

Die Werte müssen nicht in jeder Sekunde identisch sein. Mindeständerung, Cooldown, Lock und Integrationsverzögerung verhindern unnötige Modbus-Schreibzugriffe. Nach Ablauf dieser Schutzzeiten müssen Sollwert und Rückmeldung jedoch plausibel zueinander passen.

## 7. EVOpt-Fallback richtig einordnen

Ein Fallback auf „Netzdienlich laden“ ist korrekt, wenn EVOpt-Daten fehlen, veraltet oder inkonsistent sind. Prüfen:

```text
binary_sensor.se_nf_evopt_fallback_active
sensor.se_nf_evopt_fallback_code
sensor.se_nf_evopt_status
Attribut reason von sensor.se_nf_evopt_status
```

Ein regulärer 15-Minuten-Slotwechsel darf bei gültigem Plan nicht mehr zu einem falschen Fallback führen. `binary_sensor.se_nf_evopt_active_control` muss dabei eingeschaltet bleiben.

## 8. Sofortmaßnahmen bei unerwartetem Zustand

Bei einem unerwarteten Sollwert, Writer-Konflikt oder unplausiblen SolarEdge-Wert sofort ausschalten:

```text
input_boolean.se_netzdienlich_enabled = off
```

Damit werden die Controller-Writer gesperrt. Anschließend Diagnosewerte und Home-Assistant-Protokoll sichern, ohne manuell weitere SolarEdge-Werte zu verändern.
