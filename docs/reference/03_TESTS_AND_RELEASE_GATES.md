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
- den read-only EVOpt-Slot-Livetest;
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

## Read-only EVOpt-Slot-Livetest

Der Test verändert keine Helper und schreibt nicht auf SolarEdge. Er unterscheidet ausdrücklich zwischen:

- **echter Slot-Fortschaltung:** `slot_index` steigt innerhalb desselben Optimizer-Plans;
- **Solver-Replan:** `updated` ändert sich und `slot_index` beginnt wieder bei 0.

Dadurch zählt eine bloße Neuberechnung nicht fälschlich als bestandener 15-Minuten-Slotwechsel.

Aus dem entpackten Release-Ordner:

```bash
python3 scripts/rc3_evopt_slot_live_test.py \
  --minutes 50 \
  --interval 10 \
  --minimum-slot-advances 2
```

Der vollständige Bericht wird geschrieben nach:

```text
/share/rc3_evopt_slot_live_test_report.json
```

Erwarteter Abschluss:

```json
{
  "slot_advances": 2,
  "fallback_samples_after_grace": 0,
  "api_errors": 0,
  "errors": 0,
  "pass": true
}
```

`slot_advances` darf größer als 2 sein. Entscheidend ist, dass mindestens zwei echte Index-Fortschaltungen innerhalb eines unveränderten Plans beobachtet wurden.

Während des Tests müssen `sensor.se_nf_evopt_status = healthy` und `binary_sensor.se_nf_evopt_active_control = on` bleiben. Ein gültiger Slotwechsel darf keinen unnötigen Fallback und keinen zusätzlichen 0/5000-W-Schreibzyklus verursachen.

## Aussagegrenze

Die Live-Prüfung erfolgt auf einer konkreten SolarEdge-/Home-Assistant-Installation. Andere Hardware-, Firmware- und Integrationsvarianten werden durch das Mapping unterstützt, müssen aber vor Ort separat geprüft werden. Deshalb bleibt die Version ein Release Candidate und wird als GitHub-Prerelease veröffentlicht.
