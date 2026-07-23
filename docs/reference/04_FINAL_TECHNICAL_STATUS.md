# Technischer Status v0.1.0-rc.4

## Umfang

RC4 enthält:

- 18 Home-Assistant-Package-YAMLs;
- fünf Runtime-/Audit-Dateien;
- Write-Watchdog `1.0.2` mit drei Custom-Component-Dateien;
- zwei Terminal-Tools für Bericht und Live-Trace;
- Installer, Update, Migration und dateibezogenen Rollback;
- Site-Config-Mapping;
- statische Audits, Vertragstests und Writer-Konfliktprüfung;
- Release-ZIP, äußere SHA256-Datei, internes Manifest und interne `SHA256SUMS`;
- Live-Paritätsmanifest für alle 18 Package-YAMLs.

## Bestätigte Ursache

Auf der Referenzinstallation wurde ein echter Zyklus beobachtet:

```text
0 W → 5000 W → 0 W
```

Beide Befehle kamen vom einzigen zentralen Charge-Limit-Writer. Ein konkurrierender Writer wurde nicht gefunden.

Der erste Schutz verzögerte eine normale EVOpt-Freigabe zwar auf 20 Minuten, ließ aber einen Emergency-/Fail-open-Pfad weiterhin permissiv öffnen. Der spätere Live-Nachweis zeigte deshalb trotz eindeutig restriktiver EVOpt-Signale:

```text
Wert=5000 raw=holdcharge stable=holdcharge block=on target_stable_s=90
Wert=0    raw=holdcharge stable=holdcharge block=on target_stable_s=0
```

Damit war die erste Abnahme widerlegt.

## Korrigierte RC4-Lösung ab Commit `205c5e8`

- `0 W` bleibt sofort zulässig;
- bei aktivem Modus `EVOpt optimiert` bilden `raw=holdcharge`, `stable=holdcharge` und `charge_block=on` gemeinsam einen harten Writer-Block;
- ein aktiver restriktiver EVOpt-Zustand kann nicht mehr durch Emergency-/Fail-open umgangen werden;
- eine normale EVOpt-Freigabe benötigt mindestens 20 Minuten stabile nicht-restriktive Rohaktion;
- zusätzlich muss der finale Zielwert mindestens 90 Sekunden stabil permissiv sein;
- der vorgelagerte 180-Sekunden-Charge-Block bleibt als Entprellung erhalten, ist aber nicht die alleinige Freigabebedingung;
- aktueller SolarEdge-Zustand wird während kurzer EVOpt-Ausfälle gehalten;
- vollständiger Legacy-Fallback erst nach 20 Minuten;
- persistente Restart-Helper;
- Watchdog mit Context- und Intent-Korrelation.

## GitHub-Abnahme

Der korrigierte Writer wurde nicht nur statisch geprüft. Die geänderte produktive Datei `package/se_controller_80_charge_writer.yaml` lief selbst durch den vollständigen Testbench:

```text
4 Betriebsarten
96 simulierte Stunden
384 Entscheidungen
3 notwendige Writer-Aufrufe
0 nicht erlaubte Writer
0 harte Steuerungsfehler
0 unerwünschte 0↔5000-W-Roundtrips
Controller-Master am Ende: off
```

Zusätzlich bestanden:

- direkte Auswertung der produktiven Jinja-Ausdrücke mit dem echten Live-Fehlerzustand;
- unabhängiges Writer-Sicherheitsmodell;
- Codespaces/Dev Container;
- Home Assistant 2026.6.3 und 2026.7.3;
- aktuelle Stable-Vorschau;
- Release-, Installer- und Rollbackprüfung.

## Referenzinstallation

Der neue Stand ist erst nach Installation auf der Referenzanlage live abgenommen. Erwartet sind im EVOpt-Holdcharge-Zustand:

```text
EVOPT_STATUS=healthy
EVOPT_ACTION_RAW=holdcharge
EVOPT_ACTION_STABLE=holdcharge
EVOPT_ACTIVE_CONTROL=on
EVOPT_CHARGE_BLOCK=on
DESIRED_TARGET=0
SOLAREDGE_CHARGE_LIMIT=0
```

Ein Write-Intent auf `5000 W` bei `raw=holdcharge`, `stable=holdcharge` oder `charge_block=on` ist immer ein Fehler.

## Live-/Git-Parität

`validation/live_package_sha256_rc4.json` enthält SHA256 und Größe aller 18 öffentlichen Package-Dateien. Das Release-Gate und Pytest vergleichen jede Git-Datei damit. Der Writer-Hash wurde nach der korrigierten Live-Regression aktualisiert.

Die Paritätsprüfung belegt die getestete Git-/Paketversion. Sie ersetzt nicht den anschließenden Langzeittest auf der realen SolarEdge-Anlage.

## Installer

Das Runtime-Manifest enthält 28 projektverwaltete Dateien:

```text
18 Package-YAMLs
5 Runtime-/Audit-Dateien
3 Watchdog-Dateien
2 Watchdog-Tools
```

`configuration.yaml` wird gesichert und bei Bedarf um den Watchdog-Block ergänzt, gehört wegen lokaler Inhalte aber nicht zu den 28 Hash-Dateien.

## Veröffentlichung

GitHub Actions führt Release-Gate, Python-/Shell-Syntax, Pytest, Installer-/Rollbacksimulation, ZIP-Prüfung, Manifestprüfung und den vollständigen Deep Testbench aus.

Ein neues öffentliches Prerelease soll erst veröffentlicht werden, wenn der korrigierte Stand zusätzlich auf der Referenzanlage installiert und über einen ausreichend langen Watchdog-Zeitraum ohne unerwünschten `5000 → 0`-Roundtrip gelaufen ist.

## Einstufung

Technisch vollständig in GitHub geprüft, aber weiterhin Release Candidate. Noch kein stabiler `v1.0`-Stand, da die reale Langzeitabnahme des korrigierten Writers sowie zusätzliche SolarEdge-Modelle, Integrationsversionen und Fremdinstallationen weitere Praxiserfahrung benötigen.
