# Modus: EVOpt optimiert

## Ziel

Der evcc Optimizer gibt zeitabhängige Batterieaktionen vor. Der Controller übernimmt sie nur, wenn Plan, Batteriezuordnung, Datenalter und aktueller Slot gültig sind.

## Benötigte Daten

- alle Pflichtdaten des Controllers;
- erreichbare evcc-API unter `<EVOPT_BASE_URL>/api/state`;
- aktivierter EVOpt-Adapter;
- eindeutige Batterie;
- aktueller und konsistenter Optimizer-Plan.

## Priorität

EVOpt ersetzt nicht Safety, Arbiter oder Writer. Die Kette bleibt:

```text
evcc Optimizer → read-only Adapter → EVOpt-Modus → Safety → Arbiter → Writer
```

## Aktionen

| EVOpt-Aktion | Bedeutung im Controller |
|---|---|
| `normal` | normaler Speicherbetrieb |
| `hold` | Entladen zurückhalten |
| `charge` | gezieltes Laden anfordern |
| `holdcharge` | Laden sperren beziehungsweise zurückhalten |

Restriktive Änderungen wirken unmittelbar. Freizügigere Übergänge werden stabilisiert, damit kurze API- oder Slotübergänge keine unnötigen SolarEdge-Schreibzyklen auslösen.

## Slotwechsel

RC3 prüft `suggestion.action` gegen den aktuellen Planabschnitt. Gehört die Suggestion noch zum vorherigen ersten Slot, wird die Aktion aus dem vollständig validierten aktuellen Slot abgeleitet. EVOpt bleibt aktiv, solange Plan und Slot konsistent sind.

## Fallback

Jede echte Abweichung führt vollständig zu „Netzdienlich laden“. Es gibt keinen undefinierten Mischzustand.

Typische Fallbackgründe:

- evcc nicht erreichbar;
- Daten zu alt;
- Batterie nicht eindeutig gefunden;
- Schema nicht freigegeben;
- aktueller Slot ungültig;
- Plan- oder Energiebilanz inkonsistent;
- Aktion nicht aus dem Plan ableitbar.

## Diagnose

Prüfen:

```text
sensor.se_nf_evopt_adapter_raw
sensor.se_nf_evopt_status
binary_sensor.se_nf_evopt_active_control
binary_sensor.se_nf_evopt_fallback_active
sensor.se_nf_evopt_fallback_code
sensor.se_nf_active_control_label
sensor.se_nf_optimization_mode_effective
```

Wichtige Attribute des Rohsensors:

```text
health_reason
action_raw
action_source
suggestion_action
suggestion_plan_consistent
suggestion_overridden
slot_action
slot_action_reason
action_plan_consistent
plan_consistent
slot_start
slot_end
```

Nach einem Neustart ist `warming_up` für etwa zwei Minuten normal. Danach sollten `sensor.se_nf_evopt_status = healthy`, dessen Attribut `reason = ok` und `binary_sensor.se_nf_evopt_active_control = on` gelten.
