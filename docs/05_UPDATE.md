# Update

1. Vollständiges Backup erstellen.
2. Neues Release entpacken.
3. Master ausschalten.
4. Update ausführen:

```bash
bash scripts/update_package.sh
```

5. `ha core check` und Neustart abwarten.
6. Site-Konfiguration erneut prüfen und anwenden.
7. `bash scripts/run_first_checks.sh` ausführen.
8. Master erst nach erfolgreicher Prüfung einschalten.

Das Update ersetzt nur Dateien des Controllers. Private `site_config.env`-Dateien gehören nicht in das Release und werden nicht veröffentlicht.
