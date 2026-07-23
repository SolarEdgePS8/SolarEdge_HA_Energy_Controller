# SolarEdge Write-Watchdog

## Zweck

Der Watchdog beantwortet drei Fragen:

1. Wurde tatsächlich `number.set_value` auf das SolarEdge-Charge-Limit aufgerufen?
2. Wer hat den Aufruf ausgelöst?
3. Passten EVOpt, finaler Sollwert und SolarEdge-Istwert zusammen?

Er ist read-only und erzeugt selbst keinen SolarEdge-Schreibbefehl.

## Installation

Der RC4-Installer installiert automatisch:

```text
/config/custom_components/se_write_watchdog/
/config/se_write_watchdog_tools/report.sh
/config/se_write_watchdog_tools/watch.sh
```

Außerdem ergänzt er bei Bedarf den Block `se_write_watchdog:` in `configuration.yaml`. Ein vorhandener Block bleibt unverändert.

## Erfasste Ereignisse

| Ereignis | Bedeutung |
|---|---|
| `write_intent` | der zentrale Writer plant einen echten Aufruf und dokumentiert Trigger sowie Entscheidung |
| `number_set_value_call` | Home Assistant hat `number.set_value` auf das Ziel aufgerufen |
| `charge_limit_state_change` | das Number-Entity hat seinen Zustand geändert |
| `flapping_detected` | schneller Roundtrip oder Burst erkannt |
| `evopt_mismatch` | aktives EVOpt/Block, Soll und Ist bleiben nach Karenz widersprüchlich |
| `evopt_mismatch_cleared` | Widerspruch behoben |
| `static_writer_scan` | mögliche YAML-/Python-Schreiber gefunden |

## Wichtige Entitäten

```text
sensor.se_write_watchdog_status
sensor.se_write_watchdog_last_writer
sensor.se_write_watchdog_last_change
sensor.se_write_watchdog_write_calls_today
sensor.se_write_watchdog_duplicate_write_calls_today
sensor.se_write_watchdog_state_changes_today
sensor.se_write_watchdog_roundtrips_today
sensor.se_write_watchdog_unexpected_write_calls_today
sensor.se_write_watchdog_unattributed_state_changes_today
sensor.se_write_watchdog_evopt_mismatches_today
sensor.se_write_watchdog_possible_writers
binary_sensor.se_write_watchdog_flapping
binary_sensor.se_write_watchdog_evopt_mismatch
binary_sensor.se_write_watchdog_unexpected_writer
```

## Dateien

```text
/config/se_write_watchdog/events-YYYY-MM-DD.jsonl
/config/se_write_watchdog/latest.json
/config/se_write_watchdog/writer_scan.json
/config/se_write_watchdog/report.json
```

Tagesprotokolle werden standardmäßig 14 Tage aufbewahrt.

## Bericht

```bash
/config/se_write_watchdog_tools/report.sh 300
```

Der Zahlenwert legt fest, wie viele der neuesten Ereignisse in den Bericht einfließen.

## Live-Trace

```bash
/config/se_write_watchdog_tools/watch.sh
```

Abbruch mit `Strg+C`.

## Erwartung im normalen Betrieb

```text
possible_writers = 1
unexpected_write_calls_today = 0
roundtrips_today = 0
evopt_mismatches_today = 0
duplicate_write_calls_today = 0
last_writer = automation.solaredge_netzdienlich_v2_8_single_writer
```

Die Zahl der Write-Aufrufe kann größer sein als die Zahl der Zustandswechsel, wenn derselbe Wert erneut geschrieben wurde. Genau diese Blindwrites erkennt der Watchdog.

## EVOpt-Prüfung

Bei `holdcharge` und aktiver EVOpt-Steuerung wird erwartet:

```text
sensor.se_nf_evopt_action_raw = holdcharge
sensor.se_nf_evopt_action_stable = holdcharge
binary_sensor.se_nf_evopt_active_control = on
binary_sensor.se_nf_evopt_charge_block_request = on
sensor.se_nf_desired_target = 0
number.solaredge_i1_storage_charge_limit = 0
sensor.se_write_watchdog_status = ok
```

### Allgemeiner Mismatch-Alarm

Die rohe Aktion `holdcharge` allein reicht während reinem Warm-up nicht automatisch für einen allgemeinen Mismatch-Alarm. Für diese Bewertung wird sie verbindlich, wenn EVOpt aktiv steuert oder der Charge-Block gelatcht ist. Dadurch werden noch nicht vollständig initialisierte Diagnosewerte nicht vorschnell als Fehler gewertet.

### Konkreter Writer-Intent

Bei einem tatsächlichen geplanten `5000-W`-Write gilt eine strengere Regel. Im Modus `EVOpt optimiert` ist jede dieser Kombinationen immer kritisch:

```text
requested_value = 5000 und raw = holdcharge
requested_value = 5000 und stable = holdcharge
requested_value = 5000 und block = on
```

Auch `config_check != ok`, `sanity_check != ok` oder ein anderer Emergency-/Fail-open-Grund machen diese Kombination nicht zulässig.

Der korrigierte Writer soll einen solchen Intent bereits vor dem `number.set_value`-Aufruf verhindern. Taucht die Kombination trotzdem in einem neuen Protokoll auf, ist die laufende Installation nicht auf dem korrigierten Stand oder es liegt ein neuer Fehler vor.

## So liest man einen Write-Intent

Beispiel eines problematischen alten Ereignisses:

```text
Wert=5000 raw=holdcharge stable=holdcharge block=on target_stable_s=90
```

Einfache Bedeutung:

- `Wert=5000`: Laden sollte freigegeben werden;
- `raw=holdcharge`: EVOpt verlangte unmittelbar eine Ladesperre;
- `stable=holdcharge`: auch die stabilisierte Aktion verlangte eine Ladesperre;
- `block=on`: der Charge-Block war aktiv;
- Ergebnis: Der permissive Write war falsch.

Ein anschließend auftretendes `Wert=0` korrigiert zwar den Zustand, macht den vorherigen falschen Write aber nicht unkritisch. Es handelt sich dann um einen unerwünschten Roundtrip.

## Writer-Scan

Der statische Scan sucht nach `number.set_value` zusammen mit dem exakten Ziel oder dem Mapping-Helper. Erwartet wird genau:

```text
package/se_controller_80_charge_writer.yaml
```

Ein weiterer Treffer muss vor Aktivierung geklärt werden.

## Datenschutz

Die JSONL-Dateien können Entity-IDs, Automationsnamen, Context-IDs und Zustände enthalten. Vor Veröffentlichung in einem öffentlichen Issue private Namen und interne Adressen prüfen.
