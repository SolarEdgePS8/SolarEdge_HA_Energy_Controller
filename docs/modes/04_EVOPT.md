# Modus: EVOpt optimiert

## Ziel

Der evcc Optimizer gibt zeitabhängige Batterieaktionen vor. Der Controller übernimmt sie nur, wenn Plan, Batteriezuordnung und Datenalter gültig sind.

## Benötigte Daten

- alle Pflichtdaten des Controllers;
- erreichbare evcc-API;
- aktivierter EVOpt-Adapter;
- eindeutige Batterie;
- aktueller Optimizer-Plan.

## Priorität

EVOpt ersetzt nicht Safety, Arbiter oder Writer. Die Kette bleibt:

```text
evcc Optimizer → read-only Adapter → EVOpt-Modus → Safety → Arbiter → Writer
```

## Fallback

Jede Abweichung führt vollständig zu „Netzdienlich laden“. Es gibt keinen undefinierten Mischzustand.

## Diagnose

Prüfen:

- Adapterstatus;
- Datenalter;
- erkannte Aktion;
- gewählte Batterie;
- Fallbackgrund;
- `sensor.se_nf_optimization_mode_effective`.
