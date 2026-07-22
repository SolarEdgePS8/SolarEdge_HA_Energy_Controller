# RC4 Release-Status

## Integration

```text
PR=5
MERGE_COMMIT=24ecd09adb7e7413e658c827d9b8f7482e806918
TARGET_BRANCH=main
VERSION=v0.1.0-rc.4
```

Die Release-Änderungen wurden nach vollständig erfolgreichem Pull-Request-Workflow in `main` integriert.

## Parität

Die 18 öffentlichen `package/se_controller_*.yaml` werden durch `live_package_sha256_rc4.json`, das Read-only-Release-Gate und Pytest byteweise gegen den geprüften Referenzexport vom 22.07.2026 verglichen.

## Veröffentlichung

Der `main`-Workflow baut aus dem integrierten Commit das Release-ZIP, prüft äußere und innere SHA256-Manifeste und veröffentlicht anschließend das Prerelease `v0.1.0-rc.4`.
