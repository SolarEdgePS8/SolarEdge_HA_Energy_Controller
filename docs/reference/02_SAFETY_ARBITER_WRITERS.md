# Safety, Arbiter, Writer und Watchdog

## Safety

Safety prüft Site-Konfiguration, Pflichtentitäten, Datenalter, Wertebereiche und Zielgrenzen. Ungültige Zustände dürfen keinen unkontrollierten Schreibauftrag erzeugen.

Ein Config-/Sanity-Fehler kann grundsätzlich einen sicheren Fail-open-Zustand anfordern. Im aktiven Modus `EVOpt optimiert` gilt jedoch unmittelbar vor einem permissiven Charge-Limit-Write eine zusätzliche harte Regel:

> `raw=holdcharge`, `stable=holdcharge` oder `charge_block=on` dürfen niemals durch Fail-open übergangen werden.

Ein restriktiver Wechsel auf `0 W` bleibt weiterhin sofort möglich.

## Arbiter

Der Arbiter erhält die Anforderungen der vier Modi und wählt genau einen finalen Sollwert. Der Writer reagiert nur auf diesen bereits arbitrierten Endwert und nicht auf kurzlebige Zwischenzustände einzelner Planungssensoren.

Der Arbiter ist nicht die letzte Sicherheitsinstanz für einen SolarEdge-Write. Der jeweilige Writer prüft seine unmittelbar schreibrelevanten Sicherheitsbedingungen erneut.

## Writer

Jedes Ziel besitzt genau einen Controller-Writer:

- Charge-Limit;
- Discharge-Limit;
- Storage Control;
- Command Mode.

Die zentrale Schreibfreigabe verlangt im Normalbetrieb:

```text
Master = on
Site-Konfiguration = on
Config Check = ok
Sanity Check = ok
```

Ein definierter Emergency-/Fail-open-Pfad kann von dieser Normalregel abweichen. Er darf jedoch keine aktive restriktive EVOpt-Sperre umgehen.

Der Charge-Limit-Writer besitzt exakt einen `number.set_value`-Pfad. Er schreibt nur bei einer relevanten Differenz zum Istwert.

### Charge-Limit-Übergänge

#### Restriktiv auf `0 W`

- sofort zulässig;
- darf Cooldown und Write-Lock zur sicheren Schließung umgehen;
- bei EVOpt-`holdcharge` die erwartete Richtung.

#### Permissiv auf `5000 W`

Im Modus `EVOpt optimiert` müssen alle Bedingungen erfüllt sein:

```text
raw != holdcharge
stable != holdcharge
charge_block = off
EVOpt-Rohaktion mindestens 1200 Sekunden stabil
finaler Sollwert mindestens 90 Sekunden stabil
Ziel plausibel
```

Der vorgelagerte Charge-Block besitzt zusätzlich eine 180-Sekunden-Entprellung. Diese ersetzt nicht die 20-Minuten-Prüfung direkt im Writer.

#### Ausfall und Fallback

- kurzer EVOpt-Ausfall: aktuellen Istwert halten;
- vollständiger Fallback: nach 20 Minuten durchgehendem Ausfall grundsätzlich möglich;
- ein noch aktives restriktives EVOpt-Signal blockiert trotzdem jeden `5000-W`-Write;
- periodische Fünf-Minuten-Prüfung: nur Reconciliation, kein Blindschreiben.

Vor jedem echten Schreibaufruf erzeugt der Writer das Audit-Ereignis:

```text
se_charge_limit_write_intent
```

Es enthält Trigger, Soll/Ist, EVOpt-Aktion, Charge-Block, Restriktivstatus, Freigabestatus, Cooldown, Lock und Entscheidungsgrund.

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

Die rohe EVCC-Aktion `holdcharge` ist für die allgemeine Mismatch-Bewertung nur verbindlich, wenn EVOpt aktiv steuert oder der Charge-Block gelatcht ist. Dadurch werden reine Warm-up-Daten nicht vorschnell als allgemeiner Istwertfehler bewertet.

Für einen konkreten Writer-Intent gilt strenger:

```text
requested_value = 5000
UND Modus = EVOpt optimiert
UND raw=holdcharge ODER stable=holdcharge ODER charge_block=on
```

Diese Kombination ist immer fehlerhaft und darf nach dem korrigierten Writer nicht mehr auftreten.

Details: [Write-Watchdog](../10_WRITE_WATCHDOG.md).
