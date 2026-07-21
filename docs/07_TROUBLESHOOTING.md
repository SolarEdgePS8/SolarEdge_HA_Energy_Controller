# Fehlerdiagnose

## Config Check ist nicht `ok`

Prüfen:

- Site-Konfiguration bestätigt;
- Charge-Limit vorhanden und schreibbar;
- Akku-SoE verfügbar und aktuell;
- Akkukapazität größer als null;
- PV-Prognose heute und morgen verfügbar;
- Sensoralter unter dem eingestellten Grenzwert.

## Sanity Check ist nicht `ok`

Typische Ursachen:

- SoE außerhalb `0–100 %`;
- Charge-Limit außerhalb `0–5000 W`;
- Mindest-SoC größer als Maximal-SoC;
- Backup-Reserve größer als zulässiges Ziel.

## Writer bleibt gesperrt

Prüfen:

```text
input_boolean.se_netzdienlich_enabled
input_boolean.se_nf_site_config_confirmed
sensor.se_nf_config_check
sensor.se_nf_sanity_check
binary_sensor.se_nf_write_lock_active
```

## EVOpt fällt zurück

Das ist bei fehlenden, alten oder widersprüchlichen Optimizer-Daten beabsichtigt. Prüfen:

- `EVOPT_ENABLED=YES`;
- `EVOPT_BASE_URL` erreichbar;
- Batterie eindeutig ausgewählt;
- Adapterstatus `ok`;
- Optimizer-Plan aktuell.

## SQL-Auswertung ungültig

- Recorder muss SQLite verwenden;
- Standardpfad ist `/config/home-assistant_v2.db`;
- Tagesverbrauchssensor muss kumulativ sein;
- mindestens drei verwertbare Tage erforderlich.

Ohne gültige SQL-Historie verwendet der Controller seine manuellen Fallbackwerte.

## Rollback

Der letzte Backup-Pfad steht unter:

```text
/share/se_controller_last_backup.txt
```

Rollback:

```bash
bash scripts/rollback.sh "$(cat /share/se_controller_last_backup.txt)"
```
