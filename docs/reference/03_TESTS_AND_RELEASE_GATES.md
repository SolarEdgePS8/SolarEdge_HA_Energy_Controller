# Tests und Release-Gates

Ein Release darf nur erstellt werden, wenn alle statischen Prüfungen erfolgreich sind und die dokumentierten Live-Gates erfüllt wurden.

## Automatische Prüfungen

GitHub Actions prüft bei jedem Push und Pull Request:

- YAML-Struktur des Packages;
- doppelte Helper und Automations-IDs;
- lokale oder private Entity-Abhängigkeiten;
- lokale URLs und Hostnamen;
- Python-Syntax;
- Shell-Syntax;
- Modusverträge für alle vier Betriebsarten;
- Release-Gate des Read-only-Audits.

## Modusverträge

### Eigenverbrauch maximieren

Muss ohne Wetter, SQL, evcc und externe Signale einen sicheren Eigenverbrauchsbetrieb bereitstellen.

### Netzdienlich laden

Muss mit den Pflichtprognosen eigenständig funktionieren. Wetter und SQL verbessern die Planung, dürfen aber keine Pflichtabhängigkeit sein.

### Akku schonen

Muss bei fehlender SQL-Historie auf dokumentierte manuelle Verbrauchswerte zurückfallen und darf keinen undefinierten Writerzustand erzeugen.

### EVOpt optimiert

Muss bei gültigen Optimizer-Daten EVOpt verwenden und bei fehlenden, veralteten oder widersprüchlichen Daten sicher auf die netzdienliche Planung zurückfallen.

## Live-Gates der Referenzinstallation

| Gate | Ergebnis |
|---|---|
| Installation mit Backup | PASS |
| `ha core check` | PASS |
| Neustart und Entity-Aufbau | PASS |
| Runtime-Manifest, 23 Dateien | PASS |
| Site-Konfiguration | PASS |
| Config Check / Sanity Check | PASS |
| Writer-Konfliktprüfung | PASS |
| Aktivierung, 60 Messungen | PASS |
| Realer Charge-Write 0 → 5000 W | PASS |
| Realer Charge-Write 5000 → 0 W | PASS |
| Ausgangsmodus und Master wiederhergestellt | PASS |

## Noch vor Merge und Prerelease

- Lizenz ausdrücklich auswählen;
- Pull Request abschließend prüfen;
- Release-ZIP und SHA256 aus dem gemergten Commit erzeugen.

Eine zweite leere Home-Assistant-Testinstanz ist für spätere stabile Releases weiterhin sinnvoll. Für `v0.1.0-rc.2` wird die Veröffentlichung ausdrücklich als **Prerelease** vorgesehen.
