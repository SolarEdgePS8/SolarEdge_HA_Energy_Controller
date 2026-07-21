# Erstinstallation

## 1. Backup

Vor der Installation ein vollständiges Home-Assistant-Backup erstellen.

## 2. Release entpacken

Release-ZIP nach `/share` kopieren und entpacken. Anschließend in den Projektordner wechseln.

## 3. Installation

```bash
bash scripts/install_package.sh
```

Der Installer:

- schaltet den Controller-Master aus;
- sichert bereits vorhandene Controller-Dateien;
- kopiert 18 YAML-Dateien nach `/config/packages`;
- kopiert die Runtime-Skripte nach `/config`;
- erzeugt ein Runtime-Manifest;
- führt `ha core check` aus.

Fremde Automationen werden nicht gelöscht oder deaktiviert.

## 4. Neustart

```bash
ha core restart
```

Warten, bis die Home-Assistant-API wieder erreichbar ist.

## 5. Site-Konfiguration

```bash
cp config/site_config.env.example config/site_config.env
```

`config/site_config.env` mit den eigenen Entity-IDs bearbeiten. Die Datei ist privat und darf nicht in Git oder Support-Anhänge gelangen.

Am Ende:

```dotenv
SITE_CONFIG_CONFIRMED=YES
```

Dann anwenden:

```bash
python3 scripts/apply_site_config.py config/site_config.env
```

Der Master bleibt dabei aus.

## 6. Erstprüfung

```bash
bash scripts/run_first_checks.sh
```

Erwartet:

```text
FEHLER=0
PASS=True
```

Erst danach den Master einschalten.
