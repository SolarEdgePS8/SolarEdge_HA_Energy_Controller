# Tests und Release-Gates

## Automatische Prüfung

GitHub Actions führt aus:

- Read-only Release Gate;
- YAML-Parsing;
- Python-Syntax;
- Shell-Syntax;
- Modus- und Writer-Vertragstests;
- Release-Build;
- ZIP-Integrität;
- Manifest- und SHA256-Prüfung des erzeugten Release-Bundles.

## Referenzinstallation

Für RC2 wurden bestätigt:

```text
MIGRATION=PASS
ACTIVATION=PASS
OPEN_WRITE=PASS
CLOSE_WRITE=PASS
WRITER_ROUNDTRIP=PASS
```

Der Writer-Rundlauf setzte das reale Charge-Limit kontrolliert von `0 W` auf `5000 W` und wieder auf `0 W`.

## Aussagegrenze

Die Live-Prüfung erfolgte auf einer konkreten SolarEdge-/Home-Assistant-Installation. Andere Hardware- und Integrationsvarianten werden durch das Mapping unterstützt, müssen aber vor Ort separat geprüft werden. Deshalb bleibt die Version ein Release Candidate.
