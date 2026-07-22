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

Beide Befehle kamen vom einzigen zentralen Charge-Limit-Writer. Während EVOpt startete, übernahm der Legacy-Fallback zu früh. Nach EVOpt-Übernahme mit `holdcharge` wurde wieder geschlossen. Es gab keinen konkurrierenden Writer.

## RC4-Lösung

- restriktiv sofort, permissiv verzögert;
- `holdcharge`-Latch 180 Sekunden;
- Öffnung nach 90 Sekunden stabilem finalem Sollwert;
- aktueller SolarEdge-Zustand wird während kurzer EVOpt-Ausfälle gehalten;
- permissiver Legacy-Fallback erst nach 20 Minuten;
- persistente Restart-Helper;
- Watchdog mit Context- und Intent-Korrelation;
- Fehlalarmvermeidung für rohe `holdcharge`-Daten während Warm-up/Fallback.

## Referenzinstallation

```text
STATIC_CHECKS=19_OK_0_ERRORS
EVOPT_STATUS=healthy
EVOPT_ACTION_RAW=holdcharge
EVOPT_ACTION_STABLE=holdcharge
EVOPT_ACTIVE_CONTROL=on
EVOPT_CHARGE_BLOCK=on
EVOPT_FALLBACK=off
CANDIDATE_SOURCE=evopt
DESIRED_TARGET=0
SOLAREDGE_CHARGE_LIMIT=0
WATCHDOG_STATUS=ok
```

Seit dem Neustart nach Installation des Startup-Handover-Fixes:

```text
write_intent=0
number_set_value_call=0
charge_limit_state_change=0
evopt_mismatch=0
```

## Live-/Git-Parität

`validation/live_package_sha256_rc4.json` enthält SHA256 und Größe aller 18 öffentlichen Package-Dateien des geprüften Live-Exports vom 22.07.2026. Das Release-Gate und ein Pytest vergleichen jede Git-Datei damit. Abweichungen blockieren das Release.

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

GitHub Actions führt Release-Gate, Python-/Shell-Syntax, Pytest, Installer-/Rollbacksimulation, ZIP-Prüfung und Manifestprüfung aus. Erst der erfolgreiche Workflow auf `main` veröffentlicht automatisch das Prerelease `v0.1.0-rc.4` mit genau dem getesteten ZIP und dessen Prüfsumme.

## Einstufung

Technisch geeignet für ein öffentliches Prerelease `v0.1.0-rc.4`. Noch kein stabiler `v1.0`-Stand, da weitere SolarEdge-Modelle, Integrationsversionen und Fremdinstallationen zusätzliche Praxiserfahrung benötigen.
