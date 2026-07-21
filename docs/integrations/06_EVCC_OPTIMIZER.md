# evcc Optimizer / EVOpt

## Voraussetzungen

- laufendes evcc;
- aktivierter Optimizer;
- von Home Assistant erreichbare evcc-API;
- eindeutige Auswahl der Batterie;
- aktueller Optimizer-Plan.

Beispiel für `config/site_config.env`:

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://homeassistant.local:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
```

Eine lokale IP oder ein lokaler Hostname gehört nur in die private `site_config.env`, niemals in Git.

Die Basis-URL enthält nicht `/api` und nicht `/api/state`. Der Adapter ergänzt `/api/state` selbst.

## API vor Aktivierung prüfen

```bash
curl -fsS http://homeassistant.local:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Erwartet:

```text
EVCC_API=OK True
```

Ein HTTP-404 bei direktem Aufruf von `/api/state` deutet auf eine falsche Adresse oder einen falschen Port hin. Ein HTTP-404 nur bei einer selbst zusammengesetzten URL kann entstehen, wenn `/api/state` doppelt an die Basis-URL angehängt wurde.

## Funktionsweise

`se_nf_evopt_shadow_adapter.py` liest den Optimizer-Plan read-only. Der Adapter schreibt nicht auf SolarEdge. Er normalisiert die vier Aktionen:

- `normal` – normaler Speicherbetrieb;
- `hold` – Entladung zurückhalten;
- `charge` – gezieltes Laden anfordern;
- `holdcharge` – Laden sperren beziehungsweise zurückhalten.

Die Verarbeitungskette bleibt:

```text
evcc Optimizer → read-only Adapter → EVOpt-Modus → Safety → Arbiter → Writer
```

Erst Safety und Arbiter entscheiden, ob daraus eine gültige Controller-Anforderung entsteht.

## Slotwechsel in RC3

Der evcc Optimizer arbeitet typischerweise mit 15-Minuten-Slots. Direkt nach einer Neuberechnung kann `battery.devices[].suggestion.action` noch zum ersten Teilslot des letzten Solver-Laufs gehören.

RC3 behandelt deshalb den vollständig validierten aktuellen Slot als maßgeblich, sobald der Plan über den ersten Slot hinausgelaufen ist. Eine veraltete Suggestion darf dann nicht mehr allein den EVOpt-Modus deaktivieren.

Wichtige Diagnoseattribute am Rohsensor `sensor.se_nf_evopt_adapter_raw`:

```text
suggestion_action
suggestion_plan_consistent
suggestion_overridden
slot_action
slot_action_reason
action_raw
action_source
action_plan_consistent
plan_consistent
slot_start
slot_end
```

Bei einem zulässigen Slot-Override kann gelten:

```text
suggestion_overridden = true
action_source = slot
```

Das ist kein Fehler, solange Plan, aktueller Slot und Datenstatus konsistent bleiben.

## Stabilisierung nach Neustart

Nach einem Home-Assistant-Neustart ist für etwa zwei Minuten möglich:

```text
sensor.se_nf_evopt_status = warming_up
sensor.se_nf_active_control_label = Netzdienlicher Fallback
```

Danach sollte gelten:

```text
sensor.se_nf_evopt_status = healthy
Attribut reason = ok
binary_sensor.se_nf_evopt_active_control = on
```

Der Health-Grund ist kein eigener Sensor `sensor.se_nf_evopt_health_reason`. Er steht als Attribut `reason` am Statussensor und als Attribut `health_reason` am Rohsensor.

## Fallback

Bei API-Ausfall, altem Plan, fehlender Batterie, widersprüchlichen Slots oder ungültigen Daten wird der EVOpt-Plan verworfen. Der Controller verwendet dann vollständig den Modus „Netzdienlich laden“.

Diagnose:

```text
binary_sensor.se_nf_evopt_fallback_active
sensor.se_nf_evopt_fallback_code
sensor.se_nf_evopt_status
sensor.se_nf_active_control_label
```

Ein regulärer Slotwechsel mit gültigem Plan darf in RC3 nicht zu einem unnötigen Fallback führen. `binary_sensor.se_nf_evopt_active_control` muss dabei eingeschaltet bleiben.
