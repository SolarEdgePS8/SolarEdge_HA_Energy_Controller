# RC2 – Aktivierung auf der Referenzinstallation

## Ergebnis

Die kontrollierte Aktivierung von `v0.1.0-rc.2` wurde auf der Referenzinstallation erfolgreich abgeschlossen.

- Überwachungsdauer: rund 10 Minuten
- Messintervall: 10 Sekunden
- Messungen: 60
- kritische Messungen: 0
- Controller-Master: durchgehend `on`
- Writer-Freigabe: durchgehend `on`
- Config Check: durchgehend `ok`
- Sanity Check: durchgehend `ok`
- Risk Flag: durchgehend `off`
- Modus: `EVOpt optimiert`
- Session: `done`
- Ergebnis: `ACTIVATION=PASS`

## Beobachteter Betriebszustand

Während des gesamten Tests lag ein stabiler Ruhezustand vor:

- Charge-Sollwert: `0 W`
- Charge-Limit Istwert: `0 W`
- Discharge-Limit Istwert: `5000 W`
- Writer-Modus: `idle`
- Writer-Entscheidung: `Kein Write nötig · Soll 0 W · Ist 0 W`
- Start-Gate: `Tagesfenster erledigt`

Die PV-Restprognose änderte sich im Test plausibel von `6,5 kWh` auf `6,2 kWh`. Der Akku-SoE blieb bei `55,3 %`.

## Mapping im Test

- Charge-Limit: `number.solaredge_i1_storage_charge_limit`
- Discharge-Limit: `number.solaredge_i1_storage_discharge_limit`
- Command-Mode: bewusst nicht gemappt
- Storage-Control: bewusst nicht gemappt

Damit blieben bestehende externe Automationen Eigentümer der nicht gemappten Ziele.

## Einschränkungen

Dieser Test bestätigt:

- stabile Laufzeit bei aktivem Master;
- funktionierende Safety-Gates;
- gültige Site-Konfiguration;
- gültige EVOpt-Daten;
- keine kritischen Zustandsabweichungen;
- korrektes Idle-Verhalten ohne unnötige Schreibvorgänge.

Noch nicht bestätigt ist ein realer Übergang mit geändertem Charge- oder Discharge-Sollwert. Vor Freigabe des Prerelease soll deshalb mindestens ein kontrollierter Writerwechsel beobachtet werden.

## Hinweis zum Aktivierungsskript

Der Master war bereits vor dem Lauf eingeschaltet. Die Vorprüfung meldete deshalb korrekt, dass `Master AUS` und `Writer gesperrt` nicht erfüllt waren. Das Skript setzte den Lauf trotzdem fort. Für die endgültige Version muss der Vorzustand eindeutig behandelt werden:

- bei `--observe` nur beobachten und den tatsächlichen Zustand korrekt bewerten;
- bei `--activate` den Master zuerst kontrolliert ausschalten oder den bereits aktiven Zustand explizit akzeptieren;
- ein fehlgeschlagener Vorcheck darf nicht als erfolgreicher Observe-Lauf ausgegeben werden.

## Release-Gate

Status nach diesem Test:

- statische Prüfungen: PASS
- Migration: PASS
- Neustart und Runtime-Check: PASS
- Aktivierung im Idle-Zustand: PASS
- realer Writerwechsel: OFFEN
- Merge nach `main`: NOCH NICHT
- GitHub-Prerelease: NOCH NICHT
