# Modus: EVOpt optimiert

## Ziel

Der evcc Optimizer liefert zeitabhängige Batterieaktionen. Der Controller übernimmt sie nur, wenn Plan, Batteriezuordnung, Datenalter, Schema und aktueller Slot gültig sind.

## Steuerkette

```text
evcc Optimizer → read-only Adapter → EVOpt-Modus → Safety → Arbiter → einziger Writer
```

EVOpt schreibt niemals direkt auf SolarEdge.

## Aktionen

| EVOpt-Aktion | Bedeutung im Controller |
|---|---|
| `normal` | normaler Speicherbetrieb |
| `hold` | Entladen zurückhalten |
| `charge` | gezieltes Laden anfordern |
| `holdcharge` | Laden sperren |

## Übergangsregel RC4

Die Übergänge sind absichtlich asymmetrisch:

```text
restriktiv: sofort
permissiv: verzögert und stabilisiert
```

- `holdcharge` setzt das Charge-Limit sofort auf `0 W`;
- der Charge-Block bleibt nach Wegfall der Rohaktion 180 Sekunden gelatcht;
- eine Freigabe auf `5000 W` muss 90 Sekunden als finaler Sollwert stabil sein;
- der Writer besitzt für diese 90 Sekunden einen eigenen Nachtrigger;
- Upstream- und Diagnosesensoren lösen den Writer nicht mehr direkt aus.

## Startup-Handover

Während Home Assistant oder der EVOpt-Adapter startet, können Rohdaten kurz `unknown`, `unavailable` oder `warming_up` sein. Im Modus `EVOpt optimiert` gilt dann:

1. Safety hat immer Vorrang.
2. Ein bereits gelatchtes `holdcharge` bleibt wirksam.
3. Bei kurzem EVOpt-Ausfall wird der zuletzt bestätigte SolarEdge-Charge-Limit-Zustand gehalten.
4. Erst nach 20 Minuten durchgehendem Fallback darf die Legacy-Planung permissiv öffnen.
5. Sobald EVOpt wieder `healthy` ist, übernimmt die validierte EVOpt-Aktion.

Damit entsteht nach einem Neustart kein unnötiger Zyklus `0 → 5000 → 0`.

## Persistente Helper

Diese Zustände werden nach einem Neustart wiederhergestellt und nicht mehr durch `initial: false` überschrieben:

```text
input_boolean.se_netzdienlich_enabled
input_boolean.se_nf_site_config_confirmed
input_boolean.se_nf_evopt_shadow_enabled
input_text.se_nf_evopt_base_url
```

## Slotwechsel

Die Suggestion wird gegen den aktuellen Planabschnitt geprüft. Gehört sie noch zum vorherigen Slot, wird die Aktion aus dem vollständig validierten aktuellen Slot abgeleitet. Reguläre Slotwechsel und Solver-Replans dürfen nicht als Fehler interpretiert werden.

## Fallback

Nach 20 Minuten durchgehendem EVOpt-Ausfall fällt der Modus vollständig auf „Netzdienlich laden“ zurück. Typische Gründe:

- evcc nicht erreichbar;
- Daten zu alt;
- Batterie nicht eindeutig;
- Schema nicht freigegeben;
- aktueller Slot ungültig;
- Plan- oder Energiebilanz inkonsistent;
- Aktion nicht aus dem Plan ableitbar.

## Diagnose

```text
sensor.se_nf_evopt_status
sensor.se_nf_evopt_action_raw
sensor.se_nf_evopt_action_stable
binary_sensor.se_nf_evopt_active_control
binary_sensor.se_nf_evopt_charge_block_request
binary_sensor.se_nf_evopt_fallback_active
sensor.se_nf_evopt_candidate_source
sensor.se_nf_evopt_candidate_target_w
sensor.se_nf_desired_target
sensor.se_nf_charge_limit_actual
```

Bei `holdcharge` im gesunden Betrieb:

```text
status = healthy
active_control = on
charge_block = on
candidate_source = evopt
candidate_target = 0
desired_target = 0
charge_limit_actual = 0
```
