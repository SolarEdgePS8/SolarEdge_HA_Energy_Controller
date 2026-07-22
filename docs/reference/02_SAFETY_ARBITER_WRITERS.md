# Safety, Arbiter, Writer und Watchdog

## Safety

Safety prüft Site-Konfiguration, Pflichtentitäten, Datenalter, Wertebereiche und Zielgrenzen. Ungültige Zustände dürfen keinen normalen Schreibauftrag erzeugen. Ein echter Safety-/Config-Fehler behält Vorrang vor EVOpt und Fallback.

## Arbiter

Der Arbiter erhält die Anforderungen der vier Modi und wählt genau einen finalen Sollwert. Der Writer reagiert nur auf diesen bereits arbitrierten Endwert und nicht auf kurzlebige Zwischenzustände einzelner Planungssensoren.

## Writer

Jedes Ziel besitzt genau einen Controller-Writer:

- Charge-Limit;
- Discharge-Limit;
- Storage Control;
- Command Mode.

Die zentrale Schreibfreigabe verlangt:

```text
Master = on
Site-Konfiguration = on
Config Check = ok
Sanity Check = ok
```

Der Charge-Limit-Writer besitzt exakt einen `number.set_value`-Pfad. Er schreibt nur bei einer relevanten Differenz zum Istwert.

### Charge-Limit-Übergänge

- `0 W`: restriktiv, sofort;
- `5000 W`: permissiv, erst nach 90 Sekunden stabilem finalem Sollwert;
- kurzer EVOpt-Ausfall: aktuellen Istwert halten;
- vollständiger Fallback: nach 20 Minuten durchgehendem Ausfall;
- periodische Fünf-Minuten-Prüfung: nur Reconciliation, kein Blindschreiben.

Vor jedem echten Schreibaufruf erzeugt der Writer das Audit-Ereignis:

```text
se_charge_limit_write_intent
```

Es enthält Trigger, Soll/Ist, EVOpt-Aktion, aktive Steuerung, Candidate Source, Cooldown, Lock und Entscheidungsgrund.

## Watchdog

Der Watchdog ist read-only. Er beobachtet:

- jeden `number.set_value`-Aufruf auf das gemappte Charge-Limit;
- Automation, Script, Benutzer/API oder nicht auflösbare lokale Quelle;
- Context-ID und Parent-ID;
- Write-Intent des regulären Writers;
- echte Zustandswechsel;
- doppelte Writes;
- schnelle Roundtrips;
- unerwartete Schreiber;
- EVOpt-/Soll-/Ist-Widersprüche.

Die rohe EVCC-Aktion `holdcharge` ist für den Watchdog nur verbindlich, wenn EVOpt aktiv steuert oder der Charge-Block gelatcht ist. Dadurch werden Warm-up- und Fallback-Zustände nicht fälschlich als Fehler gemeldet.

Details: [Write-Watchdog](../10_WRITE_WATCHDOG.md).
