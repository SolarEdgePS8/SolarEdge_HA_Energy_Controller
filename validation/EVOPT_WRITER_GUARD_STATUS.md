# Abnahmestatus EVOpt-Writer-Schutz

## Integrierter Stand

Der Produktionsfix aus PR #37 ist auf `main` integriert. Der zentrale Charge-Limit-Writer verhindert permissive EVOpt-Schreibbefehle, bis die Rohaktion mindestens 20 Minuten stabil ist. Restriktives Schließen auf `0 W` bleibt sofort wirksam.

## Live-Nachweis der Referenzinstallation

```text
TEST_BEGINN=2026-07-23T11:00:01+02:00
POST_FIX_WRITE_CALLS=0
```

Die lokale Referenzinstallation zeigte im beobachteten Zeitraum nach Anwendung derselben 20-Minuten-Sicherheitsgrenze keine echten Charge-Limit-Schreibbefehle mehr.

## Erforderliche GitHub-Abnahme

Dieser Commit verändert keine produktive Steuerungsdatei mehr. Er dient dazu, exakt den bereits integrierten `main`-Dateibaum vollständig zu prüfen:

- normale Validierung und Release-Gate;
- verständlicher YAML- und Installationsbericht;
- Codespaces-/Dev-Container-Test;
- Modell-, Matrix- und Property-Tests;
- Fake-evcc;
- Home Assistant 2026.7.3 und 2026.6.3;
- vollständiges 24-Stunden-Replay aller vier Modi;
- Installer-, Release- und Rollbackprüfung;
- abschließendes Deep Release Gate.

`main` wird erst auf diesen Dokumentationscommit gesetzt, wenn alle verpflichtenden Prüfungen erfolgreich sind.
