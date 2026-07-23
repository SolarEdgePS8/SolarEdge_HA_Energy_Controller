# Testbench-Hardening und lokale Datenerzeugung

## Zweck

Diese Stufe ergänzt den Deep Testbench um formale Datenverträge, Datenschutzprüfungen, eine zweite verpflichtende Home-Assistant-Version und einen nicht blockierenden Nightly-Test. Sie verändert keine produktive Controller-Package-Datei.

## Formales Fixture-Schema

Alle öffentlichen Viertelstunden-Fixtures müssen dieses Schema erfüllen:

```text
testbench/schema/real_day_fixture.schema.json
```

Verbindlich sind unter anderem:

- genau 96 Slots;
- 15 Minuten Abstand;
- vollständige Spaltenreihenfolge;
- Leistungswerte in W und Energiewerte in kWh;
- SoC zwischen 0 und 100 %;
- bekannte EVOpt-Aktionen;
- Energie-Bilanzfehler je Slot höchstens ±20 W;
- ausdrücklich dokumentierte Herkunft und Datenschutzbehandlung.

## Zwei Arten öffentlicher Tagesdaten

### Anonymisierter Messdatentag

```text
testbench/fixtures/real_day_2026-07-21_15m.json
```

Der zeitliche Leistungsverlauf stammt aus Messdaten. Private Dateinamen, Entity-IDs, Adressen, Tokens, Seriennummern und Kontodaten wurden entfernt.

### Tagesbilanzkalibriertes synthetisches Beispiel

```text
testbench/fixtures/daily_balance_calibrated_example_15m.json
```

Dieser Verlauf ist ausdrücklich synthetisch. Nur die anonymisierten Tagesenergiesummen dienen als Kalibrierungsziel. Der Viertelstundenverlauf ist nicht als tatsächlich gemessener Verlauf zu interpretieren.

## Privacy-Scanner

```bash
python scripts/privacy_scan.py --self-test \
  testbench/fixtures \
  --report artifacts/privacy-report.json
```

Der Scanner blockiert in öffentlichen Daten unter anderem:

- private IPv4-Adressen;
- Bearer-Tokens und JWT-artige Werte;
- Zugangsdaten-Schlüssel;
- MAC-Adressen und Gerätekennungen;
- nicht neutrale Home-Assistant-Entity-IDs;
- ungültige JSON-Dateien.

Bei GitHub Actions werden Treffer als Dateianmerkung ausgegeben.

## Lokaler Allowlist-Exporter

Der Exporter lädt nichts hoch. Nur Rollen, die im lokalen Mapping ausdrücklich erlaubt sind, gelangen in die Ausgabedatei.

Vorlage:

```text
config/fixture_export_mapping.example.yaml
```

### CSV mit 96 Viertelstundenzeilen exportieren

```bash
cp config/fixture_export_mapping.example.yaml /share/private_fixture_mapping.yaml
# Nur die rechte Seite der Rollen auf lokale CSV-Spalten anpassen.

python scripts/export_fixture.py csv \
  --input /share/private_day.csv \
  --mapping /share/private_fixture_mapping.yaml \
  --output /share/public_day_15m.json

python scripts/privacy_scan.py \
  /share/public_day_15m.json \
  --report /share/public_day_privacy_report.json
```

Die öffentliche JSON-Datei enthält ausschließlich Rollen wie `pv_w`, `home_w` oder `soc_pct`. Ursprüngliche CSV-Spaltennamen werden verworfen.

### Home-Assistant-State-Snapshot lokal prüfen

Zuerst `/api/states` lokal in eine JSON-Datei schreiben. Danach:

```bash
python scripts/export_fixture.py states \
  --input /share/ha_states_private.json \
  --mapping /share/private_fixture_mapping.yaml \
  --output /share/ha_roles_private_report.json
```

Dieser Report bleibt privat. Er enthält absichtlich die konfigurierten Entity-IDs und ist kein öffentliches Fixture.

## Pflichtmatrix

Jeder Pull Request und jeder Push auf `main` prüft mindestens:

```text
Home Assistant 2026.7.3
Home Assistant 2026.6.3
```

Der vollständige 24h-Produktionscode-Replay bleibt auf der festgelegten Referenzversion 2026.7.3. Dadurch bleibt der zeitkritische Vergleich deterministisch, während die zweite Version grundlegende Kompatibilitätsfehler erkennt.

## Nightly gegen `stable`

Der Workflow

```text
.github/workflows/nightly-stable.yml
```

läuft täglich und kann manuell gestartet werden. Er prüft Smoke-Test und 24h-Replay gegen:

```text
ghcr.io/home-assistant/home-assistant:stable
```

Dieser Lauf ist absichtlich nicht release-blockierend. Bei einem Fehler entsteht eine Warnung und ein Diagnoseartefakt; die fest gepinnte Pflichtmatrix bleibt die verbindliche Freigabegrundlage.

## Failure-Bundles

Bei einem fehlgeschlagenen Pflichtjob erzeugt:

```bash
bash scripts/collect_failure_bundle.sh <stufe> <artefaktordner>
```

folgende Inhalte:

- Testlogs und Reports;
- Git- und Workflow-Kontext;
- Dateiliste, Größen und SHA256-Prüfsummen;
- komprimiertes TAR-GZ-Archiv;
- GitHub-Fehlerannotation mit Stufenname.

## Empfohlene Branch-Regeln

Die Datei `config/required_checks.json` enthält die empfohlenen Pflichtchecks. In GitHub sollte `main` so geschützt werden, dass direkte Änderungen nicht möglich sind und mindestens normale Validierung sowie `deep-release-gate` erfolgreich sein müssen.

## Sicherheitsgrenze

Nicht simuliert werden reale Modbus-Latenzen, SolarEdge-Firmwareunterschiede, Flash-Persistenz oder physische Kommunikationsfehler. Der Testbench ersetzt daher nicht die kontrollierte Hardware-Abnahme.
