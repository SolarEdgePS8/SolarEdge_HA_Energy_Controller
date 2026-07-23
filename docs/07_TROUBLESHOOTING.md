# Fehlerdiagnose

## Config Check ist nicht `ok`

Prüfen:

- `input_boolean.se_nf_site_config_confirmed = on`;
- Charge-Limit vorhanden und schreibbar;
- Akku-SoE verfügbar und aktuell;
- Akkukapazität größer null;
- PV-Prognosen vorhanden;
- Sensoralter innerhalb der Grenzwerte.

## Sanity Check ist nicht `ok`

Typische Ursachen:

- SoE außerhalb `0–100 %`;
- Charge-Limit außerhalb `0–5000 W`;
- Mindest-SoC größer als Maximal-SoC;
- Backup-Reserve größer als zulässiges Ziel.

## Writer bleibt gesperrt

```text
input_boolean.se_netzdienlich_enabled
input_boolean.se_nf_site_config_confirmed
sensor.se_nf_config_check
sensor.se_nf_sanity_check
binary_sensor.se_nf_controller_write_enabled
binary_sensor.se_nf_write_lock_active
```

Im Modus `EVOpt optimiert` zusätzlich prüfen:

```text
sensor.se_nf_evopt_action_raw
sensor.se_nf_evopt_action_stable
binary_sensor.se_nf_evopt_charge_block_request
```

Eine normale EVOpt-Freigabe erfolgt erst, wenn kein restriktives Signal mehr aktiv ist, die Rohaktion mindestens 20 Minuten stabil nicht-restriktiv war und der finale Sollwert zusätzlich 90 Sekunden stabil ist. Eine längere Wartezeit kann daher korrekt sein.

## EVOpt fällt zurück

Direkt nach einem Neustart kann `warming_up` normal sein. RC4 hält währenddessen den aktuellen SolarEdge-Zustand. Prüfen:

```text
input_boolean.se_nf_evopt_shadow_enabled
input_text.se_nf_evopt_base_url
sensor.se_nf_evopt_status
binary_sensor.se_nf_evopt_active_control
binary_sensor.se_nf_evopt_fallback_active
sensor.se_nf_evopt_candidate_source
```

Ein vollständiger permissiver Legacy-Fallback wird erst nach 20 Minuten durchgehendem EVOpt-Ausfall zugelassen.

Ein noch aktives `raw=holdcharge`, `stable=holdcharge` oder `charge_block=on` darf trotzdem keinen `5000-W`-Write zulassen.

## Charge-Limit wechselt häufig

Zuerst den Watchdog-Bericht lesen:

```bash
/config/se_write_watchdog_tools/report.sh 300
```

Nur echte Aufrufe:

```bash
grep -E '"event": "(number_set_value_call|charge_limit_state_change|flapping_detected)"' \
  /config/se_write_watchdog/events-$(date +%F).jsonl
```

Entscheidend:

- `allowed_writer=true`: Aufruf kam vom zentralen Writer;
- `allowed_writer=false`: fremder Schreiber;
- `duplicate=true`: derselbe Wert wurde erneut angefordert;
- `roundtrip_detected=true`: schneller Rücklauf wie `0→5000→0`;
- `source.entity_id`: erkannte Automation oder Script;
- `intent.data`: Trigger und Controllerzustand beim Aufruf.

## Kritischer EVOpt-Fall: 5000 W trotz holdcharge

Diese Kombination ist immer fehlerhaft:

```text
requested_value = 5000
optimization_mode = EVOpt optimiert
raw = holdcharge
```

Dasselbe gilt bei:

```text
stable = holdcharge
```

oder:

```text
block = on
```

Beispiel des am 23.07.2026 beobachteten Fehlers:

```text
Wert=5000 raw=holdcharge stable=holdcharge block=on target_stable_s=90
Wert=0    raw=holdcharge stable=holdcharge block=on target_stable_s=0
```

Einfache Bedeutung: Der Writer öffnete falsch auf `5000 W` und korrigierte den Fehler erst anschließend wieder auf `0 W`.

Prüfen:

1. Ist der korrigierte Stand ab Commit `205c5e8` installiert?
2. Zeigt `/config/.se_controller_runtime_manifest.json` den erwarteten Quellcommit und unveränderte Dateien?
3. Gibt es nur genau einen möglichen Writer?
4. Wurde nach dem Update Home Assistant neu gestartet?
5. Taucht der Fehler nach einem neuen Testmarker erneut auf?

Bis zur Klärung den Controller-Master ausgeschaltet lassen.

## Watchdog meldet EVOpt-Widerspruch

Ein allgemeiner Mismatch liegt vor, wenn EVOpt aktiv steuert oder der Charge-Block gelatcht ist und Soll/Ist nach der Karenzzeit offen bleiben.

Aktuellen Zustand prüfen:

```text
sensor.se_nf_evopt_action_raw
sensor.se_nf_evopt_action_stable
binary_sensor.se_nf_evopt_active_control
binary_sensor.se_nf_evopt_charge_block_request
sensor.se_nf_desired_target
number.solaredge_i1_storage_charge_limit
sensor.se_write_watchdog_status
```

Ein konkreter `5000-W`-Write-Intent bei einem restriktiven EVOpt-Signal ist dagegen sofort kritisch und benötigt keine zusätzliche Mismatch-Karenzzeit.

## Watchdog-Setup dauert länger als zehn Sekunden

Der statische Writer-Scan durchsucht die aktive Konfiguration. Die Home-Assistant-Meldung `Setup ... is taking over 10 seconds` ist eine Zeitwarnung, solange danach `sensor.se_write_watchdog_status = ok` vorhanden ist und kein Setup-Traceback erscheint.

## SQL-Auswertung ungültig

- Recorder muss SQLite verwenden;
- Standardpfad `/config/home-assistant_v2.db`;
- Tagesverbrauchssensor kumulativ;
- mindestens drei verwertbare Tage.

Ohne gültige SQL-Historie verwendet der Controller manuelle Fallbackwerte.

## Rollback

```bash
bash scripts/rollback.sh "$(cat /share/se_controller_last_backup.txt)"
ha core restart
```
