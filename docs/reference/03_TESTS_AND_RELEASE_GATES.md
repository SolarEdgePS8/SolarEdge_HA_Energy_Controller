# Tests und Release-Gates

## Automatische Prüfung in GitHub Actions

Jeder Push und Pull Request führt aus:

- Read-only Release Gate;
- YAML-Parsing und Prüfung auf doppelte Schlüssel;
- Python-Syntax ohne Erzeugung von `__pycache__`;
- Shell-Syntax aller Installations- und Audit-Skripte;
- Modus-, Safety-, Arbiter- und Writer-Vertragstests;
- acht EVOpt-Slotwechsel- und Übergangstests;
- Release-Build für `0.1.0-rc.3`;
- SHA256-Prüfung des erzeugten ZIPs;
- ZIP-Integrität;
- internes Release-Manifest und `SHA256SUMS`;
- Prüfung von Version und Quellcommit im Release-Manifest;
- Upload genau des zuvor getesteten ZIPs und seiner `.sha256`-Datei als Workflow-Artefakt.

Nur wenn der vollständige Job erfolgreich ist, kann der Publish-Job laufen.

## Automatische Veröffentlichung

Nach einem erfolgreichen Merge auf `main` veröffentlicht der Workflow einmalig das Prerelease:

```text
v0.1.0-rc.3
```

Veröffentlicht werden exakt die zuvor im selben Workflow geprüften Dateien:

```text
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip
SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
```

Der Release-Tag zeigt auf den geprüften `main`-Commit. Existiert das Release bereits, erzeugt der Workflow kein zweites Release mit demselben Tag.

## Prüfung des Release-ZIPs

Das erzeugte ZIP enthält:

- 18 Controller-Package-YAMLs;
- fünf Runtime-/Audit-Dateien;
- Installations-, Update-, Migrations- und Rollback-Skripte;
- Site-Config-Beispiel;
- Dokumentation;
- internes `validation/release_manifest.json`;
- internes `validation/SHA256SUMS`.

Das Release-Manifest enthält mindestens:

```json
{
  "project": "SolarEdge_HA_Energy_Controller",
  "version": "0.1.0-rc.3",
  "source_commit": "<40-stellige Git-SHA>",
  "files": []
}
```

Der Installer übernimmt Version und Quellcommit in `/config/.se_controller_runtime_manifest.json` und hinterlegt für jede installierte Projektdatei die SHA256-Prüfsumme.

## Referenzinstallation

Für RC3 müssen vor Veröffentlichung bestätigt sein:

```text
INSTALLATION=PASS
HA_CORE_CHECK=PASS
RUNTIME_MANIFEST=PASS
INSTALLED_FILES_23_OF_23=PASS
SITE_CONFIG=PASS
CONFIG_CHECK=PASS
SANITY_CHECK=PASS
EXTERNAL_WRITER_CONFLICTS=PASS
EVOPT_SLOT_LIVE_TEST=PASS
```

Der EVOpt-Live-Test ist read-only. Er verändert keine Helper und schreibt nicht auf SolarEdge. Er muss mehrere reale Planabschnitte einschließlich regulärer Viertelstundenwechsel beobachten.

Erwarteter Abschluss:

```json
{
  "slot_transitions": 2,
  "fallback_samples_after_grace": 0,
  "api_errors": 0,
  "errors": 0,
  "pass": true
}
```

Während des Tests müssen `sensor.se_nf_evopt_status = healthy` und `binary_sensor.se_nf_evopt_active_control = on` bleiben. Ein gültiger Slotwechsel darf keinen unnötigen Fallback und keinen zusätzlichen 0/5000-W-Schreibzyklus verursachen.

## Aussagegrenze

Die Live-Prüfung erfolgt auf einer konkreten SolarEdge-/Home-Assistant-Installation. Andere Hardware-, Firmware- und Integrationsvarianten werden durch das Mapping unterstützt, müssen aber vor Ort separat geprüft werden. Deshalb bleibt die Version ein Release Candidate und wird als GitHub-Prerelease veröffentlicht.
