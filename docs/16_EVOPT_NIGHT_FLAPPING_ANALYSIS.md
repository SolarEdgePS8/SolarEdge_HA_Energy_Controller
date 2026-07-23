# EVOpt-Nachtflattern 0 ↔ 5000 W

## Beobachtung

Am 23.07.2026 wechselte das SolarEdge Storage Charge Limit über mehrere Stunden regelmäßig zwischen `0 W` und `5000 W`.

Der Write-Watchdog ordnete alle beobachteten Schreibvorgänge demselben erlaubten Writer zu:

```text
automation.solaredge_netzdienlich_v2_8_single_writer
```

Es lag damit kein zweiter Schreiber vor. Der Writer setzte jeweils genau den vom finalen Sollwertsensor angeforderten Wert.

## Ursache

Die Ursache lag vor dem Writer im EVOpt-Adapter:

- `suggestion.action` meldete zeitweise `normal`;
- der aktuell validierte Plan-Slot meldete gleichzeitig `holdcharge`, weil der Slot Batterieentladung oder Netzeinspeisung vorsah;
- für den ersten Slot eines neu berechneten Plans wurde die permissive Suggestion `normal` bevorzugt;
- nach dem Slotwechsel wurde dagegen der restriktive Slotwert `holdcharge` bevorzugt.

Dadurch entstand bei wiederholten Optimizer-Neuberechnungen eine periodische Folge:

```text
normal → 5000 W → holdcharge → 0 W → normal → 5000 W
```

Die Writer-Stabilisierung konnte das nicht verhindern, weil jede permissive Phase länger als 90 Sekunden stabil blieb. Der vorhandene 180-Sekunden-Roundtrip-Alarm erfasste die längeren 5- bis 10-Minuten-Teilintervalle ebenfalls nicht.

## Korrektur

Für die Ladefreigabe gilt eine restriktive Konsensregel:

```text
Wenn Suggestion oder aktueller validierter Plan-Slot holdcharge verlangt,
gilt holdcharge.
```

Erst wenn beide Quellen keine Ladesperre mehr verlangen, darf wieder eine permissive Aktion wie `normal` wirksam werden.

Die Regel betrifft ausschließlich die Aktionsauswahl des read-only EVOpt-Adapters. SolarEdge-Schreibzugriffe bleiben weiterhin ausschließlich beim Single Writer.

## Regressionstest

Der Regressionstest bildet den beobachteten Fehler nach:

- wiederholte neue erste Optimizer-Slots;
- `suggestion.action = normal`;
- validierter Slot mit Entladung oder Export;
- anschließend umgekehrte Abweichung mit Suggestion `holdcharge` und neutralem Slot.

Erwartung:

- während des gesamten Konflikts bleibt die effektive Aktion `holdcharge`;
- kein Wechsel auf `normal`;
- damit kein `0 → 5000 → 0`-Zyklus;
- normale Freigabe erst nach übereinstimmender neutraler Planung.

## Sicherheitsgrenze

Die Korrektur verbindet sich nicht mit einer realen Anlage und ändert keine Modbus-Register direkt. Die endgültige Live-Abnahme erfolgt mit dem Write-Watchdog auf der Referenzinstallation.
