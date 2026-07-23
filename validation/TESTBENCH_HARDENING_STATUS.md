# Testbench-Hardening – finaler Integrations- und Abnahmestatus

## Zweck

Dieses Dokument beschreibt den final integrierten Teststand. Es verändert keine produktive Home-Assistant-Datei und wird nicht durch den öffentlichen Installer nach `/config` kopiert.

## Sauber integrierte Main-Commits

```text
Deep-Testbench-Squash aus PR #23:
34749c161344b6ed2ea7a8519e6433c1ee1987e8

Testbench-Hardening-Squash aus PR #26:
b7347eb3d256b77eaff27a67073aacf7d7fff6fc

Deterministischer 24h-Startup- und Replay-Fix aus PR #27:
35fc22915251453d08bc3738e5794ed1cf95870c
```

Die fehlgeschlagenen Entwicklungszwischenstände aus den Arbeitsbranches wurden nicht einzeln in `main` übernommen. Die fachlichen Änderungen liegen als Squash-Commits vor.

## Enthaltener Testumfang

- Codespaces-kompatibler Dev Container;
- unabhängiges Referenzmodell für alle vier Betriebsarten;
- feste Szenarien, 9.600 Zustandskombinationen sowie Property- und Zustandsmaschinentests;
- Fake-evcc mit Aktions-, Schema- und Transportfehlern;
- Home-Assistant-Smoke-Tests für 2026.7.3 und 2026.6.3;
- beschleunigter 24h-Replay des unveränderten Main-Controller-Codes durch alle vier Modi;
- Ausführung der produktiven Session-Manager- und Charge-Limit-Writer-Automationen;
- formales JSON-Schema für öffentliche 15-Minuten-Fixtures;
- Privacy-Scanner mit Selbsttest und GitHub-Anmerkungen;
- lokaler Allowlist-Exporter für CSV und Home-Assistant-State-Snapshots;
- zusätzliches, ausdrücklich synthetisches und auf anonymisierte Tagesenergiesummen kalibriertes Fixture;
- nicht blockierender Stable-Preview- und Nightly-Test;
- Installer-, Release-, Manifest-, Prüfsummen- und Rollbacktests;
- standardisierte Diagnose- und Failure-Bundles.

## Während der Post-Merge-Prüfung gefundener Testbench-Fehler

Ein Post-Merge-Lauf erzeugte gelegentlich vor dem ersten Testszenario einen zusätzlichen Writer-Intent:

```text
phase=configure
mode=null
trigger=time_pattern
requested_value=5000
```

Die Ursache lag ausschließlich in der Testvorbereitung: `configure()` schaltete den Controller-Master bereits ein und verschob anschließend die beschleunigte Uhr. Dadurch konnte der echte Time-Pattern-Trigger des produktiven Writers vor `prepare_day()` laufen.

Korrektur:

- Master bleibt während `configure()` aus;
- Aktivierung erst in `prepare_day()` nach Modus-, Ziel-, Cooldown- und Zeitstempel-Reset;
- eigener Vertragstest für dieses Master-Gate;
- Diagnoseartefakte werden über `asyncio.to_thread` außerhalb des HA-Event-Loops gespeichert;
- produktiver Session-Manager und produktiver Charge-Limit-Writer bleiben unverändert im Test aktiv.

## Vollständige Abnahme vor der finalen Main-Nachprüfung

Der korrigierte Stand wurde unter

```text
b11ade9213f85ea625f100de98e0d2edbe1e6b8d
```

vollständig erfolgreich geprüft:

```text
Validate SolarEdge HA Energy Controller       PASS
Deep SolarEdge Controller Testbench           PASS
Codespaces-/Dev-Container                     PASS
statische Architektur, Schema und Privacy     PASS
Modell-, Matrix- und Property-Tests            PASS
Fake-evcc                                     PASS
Home Assistant 2026.7.3 Smoke                 PASS
Home Assistant 2026.6.3 Smoke                 PASS
24h-Main-Code-Replay, vier Modi               PASS
Stable Preview: Smoke und 24h                 PASS
Release, Installer und Rollback               PASS
Deep Release Gate                             PASS
```

Der 24h-Test umfasst:

```text
384 Snapshots
96 Snapshots je Betriebsart
0 harte Konflikte
0 unerwartete Writer
Master nach Replay: aus
reale Hardware verbunden: nein
Writer-Ziel: number.test_storage_charge_limit
```

## Produktionsparität

Die Testbench-Integration verändert nicht:

- die 18 Dateien unter `package/`;
- `custom_components/se_write_watchdog`;
- `scripts/install_package.sh`;
- `scripts/runtime`;
- `audit/runtime`;
- die produktive EVOpt-, Arbiter-, Safety- oder Writer-Logik.

Ein Merge oder ein GitHub-Actions-Lauf installiert daher nichts auf einer bestehenden Home-Assistant-Instanz. Die Testsysteme laufen in GitHub Actions, GitHub Codespaces oder optional lokal in isolierten Docker-Containern. Alle Writer-Ziele innerhalb der Simulation sind synthetisch.

## Verbindliche finale Nachprüfung

Der Commit, der dieses Dokument aktualisiert, muss erneut beide vollständigen Workflows bestehen:

```text
Validate SolarEdge HA Energy Controller
Deep SolarEdge Controller Testbench
```

Nach erfolgreicher Prüfung wird `main` per Fast-Forward exakt auf diesen geprüften Commit gesetzt. Dadurch gehören Dateibaum und sichtbarer CI-Status zur selben Commit-SHA.

## Branch-Regeln

`config/required_checks.json` beschreibt die gewünschte Repository-Policy. Die tatsächliche GitHub-Ruleset- beziehungsweise Branch-Protection-Konfiguration wird in den Repository-Einstellungen verwaltet und nicht allein durch diese Datei aktiviert.
