# RC3 EVOpt Incident – 21.07.2026

## Befund

Das Incident-Archiv `evopt_incident_20260721T112612Z.tar.gz` zeigt keinen sporadischen API-Ausfall. Der Fehler trat reproduzierbar an jedem 15-Minuten-Slotwechsel auf.

| Fallback-Beginn (lokal) | Plan wieder konsistent | Action-Mismatch | EVOpt wieder aktiv | EVOpt-Unterbrechung |
|---|---|---:|---|---:|
| 11:00:16 | 11:04:16 | 4:00 | 11:05:17 | 5:00 |
| 11:15:16 | 11:19:16 | 4:00 | 11:20:17 | 5:00 |
| 11:30:17 | 11:35:17 | 5:00 | 11:36:17 | 6:00 |
| 11:45:18 | 11:50:18 | 5:00 | 11:51:18 | 6:00 |
| 12:00:18 | 12:06:18 | 6:00 | 12:07:18 | 7:00 |
| 12:15:18 | 12:20:18 | 5:00 | 12:21:18 | 6:00 |
| 12:30:18 | 12:36:18 | 6:00 | 12:37:18 | 7:00 |
| 12:45:18 | 12:51:18 | 6:00 | 12:52:18 | 7:00 |
| 13:00:18 | 13:06:18 | 6:00 | 13:07:18 | 7:00 |
| 13:15:18 | 13:17:18 | 2:00 | 13:18:18 | 3:00 |

Zwischen 11:00 und 13:18 Uhr gab es zehn Rückfälle. Der Adapter blieb dabei erreichbar, `data_healthy=true`, das Schema war freigegeben, der Solver meldete `Optimal`, ein aktueller Slot war vorhanden und Config sowie Sanity blieben `ok`.

Das einzige ausfallende Gate war:

```text
action_plan_consistent=false
health_reason=failed_checks:action_plan_consistent
```

## Ursache

Der Adapter verwendete `battery.devices[].suggestion.action` unabhängig davon, welcher Slot des bestehenden Optimizer-Plans gerade aktiv war.

Die evcc-Suggestion wurde mit dem letzten Solver-Lauf erzeugt und blieb bis zum nächsten Solver-Lauf unverändert. Beim nächsten Viertelstundenwechsel rückte der Plan bereits in den folgenden Slot, während die Suggestion noch zum ersten Teilslot des alten Solver-Laufs gehörte.

Beispiel 13:15 Uhr:

```text
letzter Optimizer-Lauf: 13:05:40
Slotwechsel:             13:15:00
Suggestion weiterhin:    holdcharge
aktueller Slot:           PV-Ladung / normal
Ergebnis RC2:             action_plan_consistent=false
neuer Optimizer-Lauf:     13:16:32
EVOpt wieder aktiv:       13:18:18
```

RC2 schaltete deshalb zuerst auf den netzdienlichen Fallback. Nach dem nächsten Solver-Lauf wartete es zusätzlich 60 Sekunden auf `action_stable`.

## RC3-Fix

1. `suggestion.action` wird nur noch für den ersten Slot eines frisch berechneten Optimizer-Plans als autoritativ behandelt.
2. Sobald der Plan in einen Folgeslot wechselt, wird die Aktion aus dem vollständig validierten aktuellen Slot abgeleitet.
3. Eine veraltete oder widersprüchliche Suggestion wird als Diagnose `slot_override_suggestion_mismatch` erfasst, aber nicht mehr als EVOpt-Ausfall behandelt.
4. Restriktive Änderungen wirken sofort: Laden sperren, Entladen sperren und Netzladung beenden.
5. Freizügigere Änderungen werden 60 Sekunden verzögert: Laden freigeben, Entladen freigeben und Netzladung starten.
6. Während dieser Stabilisierung bleibt EVOpt die aktive Steuerquelle; es gibt keinen Wechsel zum Legacy-/Netzdienlich-Fallback.
7. Fallbacks erhalten eindeutige Fehlercodes, Startzeit und Dauer.

## Sicherheitsverhalten

Widersprüchliche Slotflüsse bleiben weiterhin blockierend:

```text
gleichzeitig Laden und Entladen
gleichzeitig Netzbezug und Einspeisung
kein aktueller Slot
ungültiger oder inkonsistenter Gesamtplan
```

In diesen Fällen bleibt der vollständige netzdienliche Fallback aktiv.
