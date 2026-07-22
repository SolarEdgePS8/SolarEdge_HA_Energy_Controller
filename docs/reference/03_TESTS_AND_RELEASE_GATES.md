# Tests und Release-Gates

## Ziel

Ein Release darf nur veröffentlicht werden, wenn Code, YAML, Installer, Rollback, Live-Parität und Release-Artefakt gemeinsam geprüft wurden.

## Read-only Release Gate

```bash
python3 audit/readonly_audit.py . --release-gate
```

Es prüft unter anderem:

- 18 Package-YAML-Dateien;
- YAML- und Python-Syntax;
- keine privaten oder verbotenen Projektdateien;
- keine doppelten Helper oder Automation-IDs;
- vollständiges Site-Mapping;
- zentrale Writer-Gates;
- RC4-EVOpt-/Writer-Verträge;
- Watchdog-Version und Fehlalarm-Gate;
- SHA256-Parität aller 18 YAML-Dateien zum geprüften Live-Export.

## Pytest

```bash
pytest -q -p no:cacheprovider
```

Zusätzlich zu den bisherigen Modus- und EVOpt-Tests enthält RC4:

- Live-Paritätstest für alle 18 Package-Dateien;
- Persistenztest der Restart-Helper;
- 180-Sekunden-Holdcharge-Vertrag;
- 20-Minuten-Startup-Handover-Vertrag;
- 90-Sekunden-Öffnungsvertrag;
- genau einen Charge-Limit-Schreibpfad;
- korrekte Candidate-Entity;
- Watchdog-Fehlalarm-Gate.

## Installer- und Rollbacksimulation

GitHub Actions simuliert eine neue Installation in temporären Verzeichnissen:

```text
18 Package-Dateien
5 Runtime-/Audit-Dateien
3 Watchdog-Dateien
2 Watchdog-Tools
28 Hash-Einträge im Runtime-Manifest
```

Geprüft werden:

- Konfigurationsblock genau einmal ergänzt;
- Hash aller installierten Projektdateien korrekt;
- bestehende Installation ohne Token bricht vor Änderungen ab;
- manueller Rollback entfernt neue Dateien und stellt `configuration.yaml` wieder her;
- fehlgeschlagener HA-Check löst automatischen vollständigen Rollback aus.

## Release-Build

```bash
bash scripts/build_release.sh dist 0.1.0-rc.4
```

Der Workflow prüft:

- äußere `.sha256`-Datei;
- ZIP-Integrität;
- internes Release-Manifest;
- internen `SHA256SUMS`-Satz;
- Quellcommit;
- Watchdog, Dokumentation und Live-Paritätsmanifest im ZIP.

Erst danach veröffentlicht der `main`-Workflow exakt dasselbe getestete Bundle als GitHub-Prerelease.

## Live-Nachweis

Siehe `validation/RC4_EVOPT_WRITE_STABILITY_20260722.md`.
