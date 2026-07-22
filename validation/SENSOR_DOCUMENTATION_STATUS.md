# Abnahmestatus: Sensorquellen, Mapping und portable Installation

## Integrierter Umfang

Die Dokumentation unterscheidet nun klar zwischen:

1. SolarEdge-Entities aus einer Modbus-Integration;
2. Entities anderer Integrationen wie PV-Prognose, Wetter, evcc und Strompreis;
3. optionalen lokal gebauten Template-, Filter-, Integral- und Utility-Meter-Sensoren.

Enthalten sind außerdem:

- ein read-only Mapping-Assistent für Home Assistant OS, Supervised, Container, Core und Offline-State-Dateien;
- sichere Erzeugung einer unbestätigten `site_config.env`;
- neutrale YAML-Beispiele ohne private Referenzwerte;
- ein geführter Erstinstallationsablauf;
- dokumentierte Quellen für SolarEdge Modbus Multi, DWD Weather, ha-evcc, EPEX Spot und Dynamic Energy Cost.

## Sicherheitsgrenzen

```text
SITE_CONFIG_CONFIRMED=NO
EVOPT_ENABLED=NO
Controller-Master wird nicht automatisch aktiviert
Mapping-Assistent ruft keine HA-Schreibservices auf
Beispiel-Sensoren schreiben nicht auf SolarEdge
18 produktive Package-YAMLs unverändert
```

## Prüfergebnis

Der Pull-Request-Stand wurde vollständig geprüft:

- read-only Release-Gate und Live-Package-Parität;
- Python- und Shell-Syntax;
- Mapping-, Writer-, Watchdog- und Paritätsverträge;
- Tests des read-only Mapping-Assistenten;
- Installer-, Manifest- und Rollbacksimulation;
- Release-Build, ZIP- und Manifestprüfung;
- Upload des geprüften Workflow-Artefakts.

Alle Prüfungen waren erfolgreich.

## Grenze der Referenzdaten

Der private Rückwärtsexport belegt die verwendeten Entity-Namen und Einheiten der Referenzinstallation. Die bereitgestellte Package-Sammlung enthält jedoch nicht sämtliche Originaldefinitionen der lokalen `*_biased`- und `*_filtered`-Sensoren. Deshalb veröffentlicht das Repository neutrale, kommentierte Adapterbeispiele und keinen anhand von Namen geratenen Originalcode.
