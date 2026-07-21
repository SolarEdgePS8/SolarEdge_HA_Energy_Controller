# Technischer Status v0.1.0-rc.3

## Umfang

Der Release Candidate enthält:

- 18 Home-Assistant-Package-YAMLs;
- fünf Runtime-/Audit-Dateien, die nach `/config` installiert werden;
- Installer, Update, Migration und vollständigen dateibezogenen Rollback;
- Site-Config-Mapping;
- statische Audits, Runtime-Checker und Writer-Konfliktprüfung;
- vollständige Erstinstallations- und Update-Dokumentation;
- Release-ZIP, äußere SHA256-Datei, internes Manifest und interne `SHA256SUMS`.

## Automatisch bestätigt

GitHub Actions bestätigt für den RC3-Branch:

- Read-only Release Gate;
- alle 18 Package-YAMLs gültig;
- keine verbotenen Altprojekt- oder privaten Anlagendateien;
- keine doppelten Helper, Automations-IDs oder `unique_id`-Werte;
- Python- und Shell-Syntax;
- Modus-, Safety-, Arbiter- und Writer-Verträge;
- acht EVOpt-Slotwechsel- und Übergangstests;
- Release-Build `0.1.0-rc.3`;
- äußere ZIP-Prüfsumme;
- ZIP-Integrität;
- internes Release-Manifest;
- vorhandene Version und vorhandenen Quellcommit;
- Upload genau des geprüften Release-Bundles als Workflow-Artefakt.

## Release-Installer bestätigt

Der aus GitHub Actions heruntergeladene Release-Build wurde zusätzlich isoliert geprüft:

```text
RELEASE_SHA256=PASS
ZIP_INTEGRITY=PASS
RELEASE_MANIFEST=PASS
PACKAGE_YAMLS_18_OF_18=PASS
RUNTIME_FILES_5_OF_5=PASS
INSTALL_SIMULATION=PASS
INSTALLED_HASHES_23_OF_23=PASS
MANUAL_ROLLBACK=PASS
AUTOMATIC_FAILURE_ROLLBACK=PASS
```

Der Installer erzeugt ein Runtime-Manifest mit:

```text
version = 0.1.0-rc.3
source_commit = GitHub-Commit des Release-Builds
installed_files = 23
```

## Referenzinstallation bestätigt

Auf der Referenzinstallation wurden bestätigt:

```text
HA_CORE_CHECK=PASS
SITE_CONFIG=PASS
CONFIG_CHECK=PASS
SANITY_CHECK=PASS
RUNTIME_MANIFEST=PASS
INSTALLED_FILES_23_OF_23=PASS
ACTIVE_MODE=EVOpt optimiert
EVOPT_STATUS=healthy
EVOPT_ACTIVE_CONTROL=on
```

Die 18 auf der Referenzinstallation verwendeten `se_controller_*.yaml`-Dateien sind byteidentisch mit den 18 Package-Dateien des geprüften RC3-Release-Builds.

## RC3-spezifischer Live-Nachweis

Vor dem Merge auf `main` muss der read-only EVOpt-Live-Test vollständig enden mit:

```json
{
  "fallback_samples_after_grace": 0,
  "api_errors": 0,
  "errors": 0,
  "pass": true
}
```

Der Test muss mehrere reale Planabschnitte einschließlich regulärer Viertelstundenwechsel erfassen. Währenddessen müssen `sensor.se_nf_evopt_status = healthy` und `binary_sensor.se_nf_evopt_active_control = on` bleiben.

## Veröffentlichung

Nach bestandenem Live-Test wird PR #3 per Squash nach `main` übernommen. Der erfolgreiche `main`-Workflow erstellt danach automatisch das GitHub-Prerelease `v0.1.0-rc.3` und hängt exakt das im Workflow geprüfte ZIP sowie dessen `.sha256`-Datei an.

## Einstufung

Technisch geeignet für ein öffentliches **Prerelease `v0.1.0-rc.3`**, sobald der abschließende EVOpt-Live-Bericht `pass=true` meldet. Noch nicht als stabiler `v1.0`-Stand einzustufen, weil weitere Installationen, SolarEdge-Varianten und Integrationsversionen zusätzliche Praxiserfahrung benötigen.
