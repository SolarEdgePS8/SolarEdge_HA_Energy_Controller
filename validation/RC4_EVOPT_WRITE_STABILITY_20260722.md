# RC4 EVOpt-/Charge-Limit-Livenachweis vom 22.07.2026

## Ausgangsproblem

Der Verlauf des SolarEdge Charge Limits zeigte wiederholte Wechsel zwischen `0 W` und `5000 W`. Ein zusätzlicher Runtime-Watchdog wurde installiert, um nicht nur Zustandswechsel, sondern jeden `number.set_value`-Aufruf und dessen Home-Assistant-Kontext zu erfassen.

## Schreiberanalyse

Der statische Scan fand genau einen möglichen Schreiber:

```text
packages/se_controller_80_charge_writer.yaml
automation.solaredge_netzdienlich_v2_8_single_writer
```

Der Runtime-Trace bestätigte, dass sowohl der Aufruf auf `5000 W` als auch der spätere Aufruf auf `0 W` von diesem Writer kamen. Es wurde kein konkurrierender Writer gefunden.

## Reproduzierter Zyklus vor RC4

```text
12:25:01  number.set_value: 0 W → 5000 W
12:25:02  SolarEdge bestätigt 5000 W
12:38:59  number.set_value: 5000 W → 0 W
12:39:02  SolarEdge bestätigt 0 W
```

Beim Öffnen war EVOpt noch nicht aktiv:

```text
evopt_action_raw = unavailable
evopt_active_control = off
evopt_candidate_source = legacy
desired_target = 5000
writer_mode = priority_open
```

Beim Schließen hatte EVOpt übernommen:

```text
evopt_action_raw = holdcharge
evopt_active_control = on
evopt_charge_block = on
evopt_candidate_source = evopt
desired_target = 0
```

Ursache war damit das Startup-Handover und nicht ein zweiter Writer.

## Installierte RC4-Regeln

- Master, Site-Bestätigung, EVOpt-Aktivierung und Basis-URL werden nach Neustarts wiederhergestellt;
- `holdcharge` wirkt sofort und bleibt 180 Sekunden gelatcht;
- eine Freigabe auf `5000 W` muss 90 Sekunden als finaler Sollwert stabil sein;
- nur der finale arbitrierte Sollwert triggert den Charge-Limit-Writer;
- während kurzer EVOpt-Ausfälle wird der zuletzt bestätigte SolarEdge-Zustand gehalten;
- ein permissiver Legacy-Fallback wird erst nach 20 Minuten zugelassen;
- der Watchdog bewertet rohe `holdcharge`-Daten nur bei aktiver EVOpt-Steuerung oder gelatchtem Block als verbindlich.

## Statische Abnahme

```text
SolarEdge EVOpt-/Writer-Abschlussprüfung
Ergebnis: 19 OK, 0 Fehler
```

Geprüft wurden unter anderem:

- genau ein `number.set_value` im Charge-Limit-Writer;
- korrekte Entity `sensor.se_nf_evopt_candidate_target_w`;
- 90-Sekunden-Nachtrigger;
- 180-Sekunden-Holdcharge-Latch;
- 20-Minuten-Startup-/Fallback-Grace;
- persistente Helper;
- Watchdog-Version `1.0.2`;
- genau ein statisch möglicher Writer.

## Laufzeitabnahme nach Neustart

```text
sensor.se_nf_evopt_status = healthy
sensor.se_nf_evopt_action_raw = holdcharge
sensor.se_nf_evopt_action_stable = holdcharge
binary_sensor.se_nf_evopt_active_control = on
binary_sensor.se_nf_evopt_charge_block_request = on
binary_sensor.se_nf_evopt_fallback_active = off
sensor.se_nf_evopt_candidate_source = evopt
sensor.se_nf_evopt_candidate_target_w = 0
sensor.se_nf_desired_target = 0
number.solaredge_i1_storage_charge_limit = 0
sensor.se_write_watchdog_status = ok
```

Ereignisse seit dem vor dem Neustart gesetzten Watchdog-Marker:

```text
write_intent:              0
number_set_value_call:     0
charge_limit_state_change: 0
evopt_mismatch:            0
mismatch_cleared:          0
```

## Ergebnis

```text
SINGLE_WRITER=PASS
STARTUP_HANDOVER=PASS
UNNECESSARY_0_5000_0_CYCLE=0
EVOPT_HOLDCHARGE=PASS
WATCHDOG_FALSE_POSITIVE_FIX=PASS
STATIC_CHECKS=19_OK_0_ERRORS
LIVE_TEST=PASS
```

## Aussagegrenze

Der Nachweis gilt für die Referenzinstallation, den beobachteten Neustart und die EVOpt-Aktion `holdcharge`. Die CI-Vertragstests prüfen zusätzlich Struktur, Zeitregeln, Live-Dateiparität, Installer und Rollback. Weitere Anlagen müssen Entity-Mapping und Writer-Konflikte lokal prüfen.
