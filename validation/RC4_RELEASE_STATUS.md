# RC4 Release-Status

## Integration

```text
PR=5
MERGE_COMMIT=24ecd09adb7e7413e658c827d9b8f7482e806918
TARGET_BRANCH=main
VERSION=v0.1.0-rc.4
```

Die RC4-Änderungen wurden nach vollständig erfolgreichem Pull-Request-Workflow in `main` integriert.

## Parität

Die 18 öffentlichen `package/se_controller_*.yaml` werden durch `validation/live_package_sha256_rc4.json`, das Read-only-Release-Gate und Pytest byteweise gegen den geprüften Referenzexport vom 22.07.2026 verglichen.

Die CI-Korrekturen nach RC4 verändern keine Package-YAML. Die veröffentlichte Controller-Konfiguration bleibt damit byteidentisch zur geprüften Home-Assistant-Referenzinstallation.

## Veröffentlichung

Das Prerelease `v0.1.0-rc.4` einschließlich ZIP und SHA256-Datei wurde einmalig aus einem vollständig validierten Workflow veröffentlicht.

Der dauerhafte Workflow `Validate SolarEdge HA Energy Controller` veröffentlicht RC4 nicht erneut. Er führt bei Pull Requests, bei Änderungen auf `main` und bei manuellen Läufen weiterhin die vollständigen Prüfungen aus:

- Read-only-Release-Gate und Live-Parität;
- Python- und Shell-Syntax;
- EVOpt-, Writer-, Watchdog- und Paritätsverträge;
- portable Installation und Rollbacksimulation;
- Build und Prüfung des Release-ZIP samt Manifest;
- Upload des geprüften Bundles als Workflow-Artefakt.

## Main-Status

Änderungen werden zuerst auf einem Pull-Request-Commit vollständig geprüft. Der freigegebene `main`-Head soll exakt auf einem grün geprüften Commit-SHA basieren, damit Quellstand und sichtbarer CI-Status zusammengehören.
