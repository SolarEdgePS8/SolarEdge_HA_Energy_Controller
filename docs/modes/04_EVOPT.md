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
permissiv: erst nach eindeutiger und stabiler Freigabe
```

### Laden sperren

`0 W` ist die sichere, restriktive Richtung. Sie darf sofort geschrieben werden.

Im aktiven Modus `EVOpt optimiert` gilt ein **harter Ladeblock**, sobald mindestens eines dieser Signale restriktiv ist:

```text
sensor.se_nf_evopt_action_raw = holdcharge
sensor.se_nf_evopt_action_stable = holdcharge
binary_sensor.se_nf_evopt_charge_block_request = on
```

Solange eines dieser Signale aktiv ist, darf der Charge-Limit-Writer **niemals `5000 W` schreiben**. Das gilt auch dann, wenn gleichzeitig ein Config-, Sanity- oder anderer Emergency-Pfad normalerweise Fail-open anfordern würde.

### Laden wieder freigeben

Eine Freigabe auf `5000 W` benötigt im EVOpt-Modus beides:

1. die rohe EVOpt-Aktion ist mindestens **20 Minuten** ohne Unterbrechung nicht mehr `holdcharge`;
2. der finale Sollwert ist zusätzlich mindestens **90 Sekunden** stabil permissiv.

Der frühere 180-Sekunden-Charge-Block bleibt als vorgelagerte Entprellung erhalten. Er ist aber nicht mehr die alleinige Freigabebedingung. Entscheidend ist die zusätzliche harte Writer-Prüfung unmittelbar vor jedem SolarEdge-Schreibzugriff.

Der Writer besitzt eigene Nachtrigger nach 90 Sekunden Zielwertstabilität und nach 20 Minuten stabiler EVOpt-Rohaktion. Upstream- und Diagnosesensoren lösen keinen direkten SolarEdge-Write aus.

## Startup-Handover

Während Home Assistant oder der EVOpt-Adapter startet, können Rohdaten kurz `unknown`, `unavailable` oder `warming_up` sein. Im Modus `EVOpt optimiert` gilt dann:

1. Ein eindeutig aktives `holdcharge` oder ein aktiver Charge-Block bleibt immer restriktiv.
2. Ein restriktiver Wechsel auf `0 W` bleibt sofort möglich.
3. Bei kurzem EVOpt-Ausfall wird der zuletzt bestätigte SolarEdge-Charge-Limit-Zustand gehalten.
4. Erst nach 20 Minuten durchgehendem Fallback darf die Legacy-Planung grundsätzlich permissiv werden.
5. Auch dann verhindert ein noch aktives restriktives EVOpt-Signal jeden `5000-W`-Write.
6. Sobald EVOpt wieder `healthy` ist, übernimmt die validierte EVOpt-Aktion.

Damit soll weder beim Neustart noch bei einem kurzen Adapter-/Safety-Wechsel ein unnötiger Zyklus `0 → 5000 → 0` entstehen.

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

Der Fallback darf die harte Writer-Regel nicht umgehen: Solange `raw`, `stable` oder Charge-Block noch eindeutig `holdcharge` melden, bleibt ein permissiver Write gesperrt.

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

Ein Write-Intent mit `requested_value=5000`, während `raw=holdcharge`, `stable=holdcharge` oder `charge_block=on` gilt, ist immer ein Fehler und muss im Write-Watchdog untersucht werden.
