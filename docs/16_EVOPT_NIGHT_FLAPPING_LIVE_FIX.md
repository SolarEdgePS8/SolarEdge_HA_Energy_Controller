# EVOpt-Nachtflattern: Live-Nachweis und dauerhafter Schutz

## Beobachtung

Auf der Referenzinstallation wechselte das SolarEdge Storage Charge Limit nachts wiederholt zwischen `0 W` und `5000 W`.

Der Write-Watchdog belegte:

- alle echten Schreibbefehle kamen vom erlaubten zentralen Charge-Limit-Writer;
- es gab keinen zweiten konkurrierenden Writer;
- kurze permissive EVOpt-Phasen waren lang genug, um die bisherige 90-Sekunden-Freigabe zu passieren;
- anschließend setzte `holdcharge` das Limit wieder sofort auf `0 W`.

## Live-Nachweis auf der Referenzinstallation

Lokal wurde der EVOpt-Charge-Block auf 20 Minuten Freigabestabilisierung gesetzt. Danach ergab die wiederholte Watchdog-Auswertung:

```text
TEST_BEGINN=2026-07-23T11:00:01+02:00
POST_FIX_WRITE_CALLS=0
```

Seit Testbeginn wurde im beobachteten Zeitraum kein echter `number.set_value`-Aufruf auf das SolarEdge-Charge-Limit registriert.

## Portabler Repository-Fix

Der öffentliche Controller setzt dieselbe Sicherheitsgrenze direkt am einzigen SolarEdge-Writer um:

- `0 W` und damit restriktives Schließen bleiben sofort wirksam;
- eine permissive EVOpt-Freigabe wird erst akzeptiert, wenn die Rohaktion mindestens 20 Minuten unverändert geblieben ist;
- die vorhandene 90-Sekunden-Stabilisierung des finalen Zielwertes bleibt zusätzlich aktiv;
- nach 20 Minuten erfolgt eine gezielte Neuprüfung;
- es entsteht kein zweiter Writer.

Der Writer-Schutz ist gegenüber dem lokalen Latch gleichwertig hinsichtlich der entscheidenden Sicherheitswirkung: kurze EVOpt-Impulse dürfen keinen realen `5000-W`-Schreibbefehl mehr erzeugen. Nach einem Home-Assistant-Neustart ist er bewusst eher konservativer und kann die erste EVOpt-Freigabe verzögern.

## Testgrenze

Der Live-Nachweis gilt für die Referenzinstallation und den beobachteten Zeitraum. Die GitHub-Testumgebung verbindet sich nicht mit realer SolarEdge-Hardware. Der Write-Watchdog bleibt deshalb nach Installation aktiv; der Stand bleibt ein Release Candidate.
