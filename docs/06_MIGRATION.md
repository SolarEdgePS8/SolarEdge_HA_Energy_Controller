# Migration einer bestehenden Installation

Die Migration ist für Installationen gedacht, auf denen frühere Controller-Dateien bereits vorhanden sind.

```bash
bash scripts/migrate_live.sh
```

Der Ablauf:

- Master ausschalten;
- bestehende Mapping-Werte privat nach `/share` exportieren;
- vollständiges Backup erstellen;
- RC2 installieren;
- Home Assistant neu starten;
- Mapping wieder anwenden;
- Runtime- und Writer-Konfliktprüfung durchführen;
- bei einem Fehler automatisch zurückrollen.

Andere Projekte wie Fahrzeug-, Wallbox-, Wärmepumpen-, Preis- oder Backup-Reserve-Automationen werden nicht migriert. Direkte Schreibkonflikte müssen separat bereinigt oder die betreffenden Controller-Mappings leer gelassen werden.
