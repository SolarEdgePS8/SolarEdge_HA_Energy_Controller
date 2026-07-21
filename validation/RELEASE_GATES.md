# Release-Gates

Für ein Prerelease müssen erfüllt sein:

- Read-only Audit PASS;
- YAML-, Python- und Shell-Syntax PASS;
- keine privaten oder standortspezifischen Package-Abhängigkeiten;
- keine doppelten Helper oder Automation-IDs;
- alle Site-Config-Schlüssel verarbeitet;
- Writer-Gates vorhanden;
- Installations-/Rollback-Simulation PASS;
- Release-Build, ZIP und Manifest PASS;
- kontrollierte Migration PASS;
- Aktivierung PASS;
- realer Writer-Rundlauf PASS;
- Lizenz vorhanden.
