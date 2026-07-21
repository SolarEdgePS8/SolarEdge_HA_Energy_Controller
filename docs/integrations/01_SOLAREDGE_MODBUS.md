# SolarEdge Modbus

Der Controller benötigt mindestens ein schreibbares Charge-Limit. Die konkrete Entity hängt von der verwendeten SolarEdge-Modbus-Integration ab.

Typische Zielarten:

- Charge-Limit: `number.*`;
- Discharge-Limit: `number.*`;
- Command Mode: `select.*`;
- Storage Control Mode: `select.*`;
- Backup-Reserve: `number.*`.

Die Beispielnamen in der Dokumentation sind keine feste Vorgabe. Entscheidend sind Funktion, Einheit und Schreibbarkeit.

Vor dem Mapping prüfen:

1. Entity in den Entwicklerwerkzeugen vorhanden;
2. Wert manuell lesbar;
3. erlaubter Bereich passt;
4. keine zweite Automation schreibt dasselbe Ziel;
5. genaue Select-Optionen aus den Entity-Attributen übernehmen.

Command Mode und Storage Control sind optional. Leer lassen, wenn bestehende Automationen Eigentümer bleiben sollen.
