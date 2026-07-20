# Update

## Vorbereitung

1. Changelog lesen.
2. Vollständiges Home-Assistant-Backup erstellen.
3. Controller-Master ausschalten.
4. Aktuelle `config/site_config.env` sichern.

## Update durchführen

Release entpacken und im neuen Projektordner:

```bash
bash scripts/update_package.sh
```

Das Update erstellt ein Dateibackup, ersetzt nur manifestierte Controllerdateien, erhält lokale Helperwerte, führt `ha core check` aus und lässt den Master ausgeschaltet.

Danach:

```bash
ha core restart
bash scripts/run_first_checks.sh
```

## Rollback

```bash
bash scripts/rollback.sh "$(cat /share/se_controller_last_backup.txt)"
ha core restart
```

Der Rollback stellt vorher vorhandene Dateien wieder her und entfernt Dateien, die durch das Update neu installiert wurden.
