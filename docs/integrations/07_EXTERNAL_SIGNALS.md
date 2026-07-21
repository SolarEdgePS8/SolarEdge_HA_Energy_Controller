# Externe Signale

Andere Projekte bleiben unabhängig. Sie dürfen neutrale Eingangssignale bereitstellen:

```dotenv
EXTERNAL_EV_CHARGING_ENTITY=binary_sensor.example_ev_charging
EXTERNAL_DISCHARGE_LOCK_ENTITY=binary_sensor.example_discharge_lock
EXTERNAL_PEAK_LOCK_ENTITY=binary_sensor.example_peak_lock
```

Erwartet werden `binary_sensor.*`- oder andere Entities mit Zustand `on`/`off`.

Diese Signale sind Anforderungen, keine direkten SolarEdge-Writer. Eine externe Automation darf nicht gleichzeitig dasselbe gemappte SolarEdge-Register schreiben.
