# Testbench-Hardening – Integrations- und Abnahmestatus

## Zweck

Dieses Dokument hält den nach dem Squash-Merge erneut zu prüfenden Repository-Stand fest. Es verändert keine produktive Home-Assistant-Datei und wird nicht durch den öffentlichen Installer nach `/config` kopiert.

## Integrierte Stände

```text
Deep-Testbench-Squash aus PR #23:
34749c161344b6ed2ea7a8519e6433c1ee1987e8

Testbench-Hardening-Squash aus PR #26:
b7347eb3d256b77eaff27a67073aacf7d7fff6fc
```

## Enthaltener Testumfang

- Codespaces-kompatibler Dev Container;
- unabhängiges Referenzmodell für alle vier Betriebsarten;
- feste Szenarien, 9.600 Zustandskombinationen sowie Property- und Zustandsmaschinentests;
- Fake-evcc mit Aktions-, Schema- und Transportfehlern;
- Home-Assistant-Smoke-Tests für 2026.7.3 und 2026.6.3;
- beschleunigter 24h-Replay des unveränderten Main-Controller-Codes durch alle vier Modi;
- formales JSON-Schema für öffentliche 15-Minuten-Fixtures;
- Privacy-Scanner mit Selbsttest und GitHub-Anmerkungen;
- lokaler Allowlist-Exporter für CSV und Home-Assistant-State-Snapshots;
- zusätzliches, ausdrücklich synthetisches und auf anonymisierte Tagesenergiesummen kalibriertes Fixture;
- nicht blockierender Stable-Preview- und Nightly-Test;
- Installer-, Release-, Manifest-, Prüfsummen- und Rollbacktests;
- standardisierte Diagnose- und Failure-Bundles.

## Abnahme vor dem Squash-Merge

Der vollständige Quellstand des Testbench-Hardenings wurde vor dem Squash-Merge unter

```text
fceace9cb4829f703a21daba0ca71d74c542266f
```

mit folgenden Ergebnissen geprüft:

```text
Validate SolarEdge HA Energy Controller       PASS
Deep SolarEdge Controller Testbench           PASS
Codespaces-/Dev-Container                     PASS
statische Architektur und Privacy-Gate        PASS
Modell-, Matrix- und Property-Tests            PASS
Fake-evcc                                     PASS
Home Assistant 2026.7.3 Smoke                 PASS
Home Assistant 2026.6.3 Smoke                 PASS
24h-Main-Code-Replay, vier Modi               PASS
Release, Installer und Rollback               PASS
Deep Release Gate                             PASS
aktueller Home-Assistant-Stable-Container     PASS
```

Der Stable-Test umfasste Smoke-Test und vollständigen 24h-Replay:

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

## Verbindliche Nachprüfung

Der Commit, der dieses Dokument ergänzt, muss erneut beide vollständigen Workflows bestehen:

```text
Validate SolarEdge HA Energy Controller
Deep SolarEdge Controller Testbench
```

Erst danach darf `main` auf exakt diesen geprüften Commit gesetzt werden.

## Branch-Regeln

`config/required_checks.json` beschreibt die gewünschte Repository-Policy. Die tatsächliche GitHub-Ruleset- beziehungsweise Branch-Protection-Konfiguration wird in den Repository-Einstellungen verwaltet und nicht allein durch diese Datei aktiviert.
