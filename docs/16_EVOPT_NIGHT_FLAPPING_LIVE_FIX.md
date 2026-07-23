# EVOpt-Nachtflattern: Live-Fehler, fehlgeschlagener erster Fix und neuer Schutz

## Ursprüngliche Beobachtung

Auf der Referenzinstallation wechselte das SolarEdge Storage Charge Limit nachts wiederholt zwischen `0 W` und `5000 W`.

Der Write-Watchdog belegte:

- alle echten Schreibbefehle kamen vom erlaubten zentralen Charge-Limit-Writer;
- es gab keinen zweiten konkurrierenden Writer;
- kurze permissive EVOpt-Phasen waren lang genug, um die bisherige 90-Sekunden-Freigabe zu passieren;
- anschließend setzte `holdcharge` das Limit wieder auf `0 W`.

## Warum der erste Live-Nachweis nicht ausreichte

Nach einem lokalen 20-Minuten-Latch zeigte eine erste Auswertung zunächst:

```text
TEST_BEGINN=2026-07-23T11:00:01+02:00
POST_FIX_WRITE_CALLS=0
```

Dieser Zeitraum war zu kurz für eine endgültige Abnahme. Eine spätere Auswertung desselben Testbeginns zeigte den weiterhin vorhandenen Fehler eindeutig:

```text
POST_FIX_WRITE_CALLS=2
2026-07-23T12:24:03.864816+02:00 Wert=5000 raw=holdcharge stable=holdcharge block=on target_stable_s=90
2026-07-23T12:24:25.614216+02:00 Wert=0    raw=holdcharge stable=holdcharge block=on target_stable_s=0
```

Einfache Bedeutung:

1. EVOpt verlangte eindeutig eine Ladesperre.
2. Trotzdem schrieb der Writer kurzzeitig `5000 W` und öffnete damit die Ladefreigabe.
3. Erst 22 Sekunden später wurde wieder `0 W` geschrieben.
4. Der bisherige Writer-Guard wurde durch den Emergency-/Fail-open-Pfad umgangen.

Der erste Fix ist deshalb **nicht als erfolgreich live abgenommen** zu werten.

## Neue zwingende Writer-Regel

Bei aktivem Modus `EVOpt optimiert` gilt jetzt vor jedem permissiven Schreibzugriff:

> Wenn `raw=holdcharge`, `stable=holdcharge` oder der EVOpt-Charge-Block `on` ist, darf niemals `5000 W` geschrieben werden.

Diese Regel gilt ausdrücklich auch dann, wenn Config, Sanity oder ein anderer Safety-Pfad gleichzeitig Fail-open anfordert.

Unverändert bleiben:

- ein restriktiver Wechsel auf `0 W` wirkt sofort;
- ohne restriktives EVOpt-Signal bleibt ein echter Emergency-Fail-open möglich;
- eine normale EVOpt-Freigabe benötigt weiterhin 20 Minuten stabile Rohaktion und zusätzlich 90 Sekunden stabilen Zielwert;
- es existiert weiterhin genau ein `number.set_value`-Pfad.

## Pflichtregression in der Testumgebung

Die Testumgebung prüft jetzt den exakten Live-Fall in drei Ebenen:

1. **Unabhängiges Python-Sicherheitsmodell**  
   Die Sicherheitsregel wird unabhängig von Home-Assistant-YAML formuliert.

2. **Direkte Auswertung der produktiven Jinja-Logik**  
   Die echten Writer-Ausdrücke werden mit `raw=holdcharge`, `stable=holdcharge`, `block=on`, `emergency_open=true` und `target=5000` ausgeführt. Erwartet wird zwingend `write_allowed=false`.

3. **Vertragstest der produktiven Writer-Datei**  
   Der Test stellt sicher, dass alle drei restriktiven EVOpt-Signale berücksichtigt werden und Emergency-Fail-open sie nicht umgehen kann.

## Abnahmegrenze

Ein grüner GitHub-Test beweist die simulierte und statische Logik. Er ersetzt nicht die reale Hardwareabnahme. Erfolgreich abgeschlossen ist der Fix erst, wenn nach Installation auf der Referenzanlage ein ausreichend langer Watchdog-Zeitraum **keinen weiteren unerwünschten `5000 → 0`-Roundtrip** zeigt.
