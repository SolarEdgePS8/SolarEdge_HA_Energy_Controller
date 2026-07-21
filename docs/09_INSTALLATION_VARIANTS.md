# Installation auf verschiedenen Home-Assistant-Systemen

Diese Anleitung ergänzt die [Erstinstallation](02_FIRST_INSTALL.md). Die Controller-Logik ist identisch; nur Dateipfade, API-Token und die Methode der Home-Assistant-Konfigurationsprüfung unterscheiden sich.

## Gemeinsames Prinzip

Der Installer kopiert ausschließlich Projektdateien:

- 18 Dateien `se_controller_*.yaml` in den Package-Ordner;
- fünf Runtime-/Audit-Dateien in den Home-Assistant-Konfigurationsordner;
- ein commitgebundenes Runtime-Manifest mit SHA256-Prüfsummen.

Vor dem Kopieren wird ein dateibezogenes Backup erstellt. Bei einem Fehler wird automatisch zurückgerollt. Private Packages und fremde Automationen werden nicht verändert.

Der Installer startet Home Assistant nicht automatisch. Dadurch bleibt der Neustart kontrollierbar und installationsspezifisch.

## A. Home Assistant OS

### Voraussetzungen

- Terminal & SSH Add-on;
- Zugriff auf `/config` und `/share`;
- `ha`-CLI verfügbar;
- Packages aktiviert;
- vollständiges HA-Backup.

### Installation

```bash
cd /share
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
rm -rf /share/se_controller_release_rc3
mkdir -p /share/se_controller_release_rc3
unzip -q SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip \
  -d /share/se_controller_release_rc3
cd /share/se_controller_release_rc3/SolarEdge_HA_Energy_Controller
bash scripts/install_package.sh
ha core restart
```

Danach `site_config.env` erstellen, anwenden und `bash scripts/run_first_checks.sh` ausführen.

## B. Home Assistant Supervised

Die Schritte entsprechen Home Assistant OS, sofern `/config`, `/share`, `ha` und `SUPERVISOR_TOKEN` im verwendeten Terminal verfügbar sind.

```bash
cd /share/se_controller_release_rc3/SolarEdge_HA_Energy_Controller
bash scripts/install_package.sh
ha core restart
```

## C. Home Assistant Container

### Voraussetzungen

- der Home-Assistant-Konfigurationsordner ist in die Wartungs-Shell gemountet;
- ein beschreibbarer Backup-Ordner ist vorhanden;
- ein Long-Lived Access Token wurde im HA-Benutzerprofil erzeugt;
- die Wartungs-Shell kann die HA-API erreichen;
- eine ausführbare Konfigurationsprüfung ist festgelegt.

Beispielannahmen:

```text
Host-Konfigurationsordner: /srv/homeassistant/config
Host-Backupordner:         /srv/homeassistant/share
Containername:             homeassistant
```

### Umgebungsvariablen setzen

```bash
export CONFIG_ROOT=/srv/homeassistant/config
export SHARE_ROOT=/srv/homeassistant/share
export HA_API_URL=http://127.0.0.1:8123/api
export HA_TOKEN='DEIN_LONG_LIVED_ACCESS_TOKEN'
export HA_CHECK_COMMAND='docker exec homeassistant python3 -m homeassistant --script check_config -c /config'
```

Zeigt die Wartungs-Shell nicht auf denselben Netzwerk-Namespace, muss `HA_API_URL` auf eine erreichbare IP oder einen Docker-DNS-Namen zeigen.

### Installation

```bash
cd /srv/homeassistant/share
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
rm -rf se_controller_release_rc3
mkdir -p se_controller_release_rc3
unzip -q SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip \
  -d se_controller_release_rc3
cd se_controller_release_rc3/SolarEdge_HA_Energy_Controller
bash scripts/install_package.sh
```

### Neustart

```bash
docker restart homeassistant
```

Danach die API-Erreichbarkeit prüfen:

```bash
curl -fsS \
  -H "Authorization: Bearer $HA_TOKEN" \
  "$HA_API_URL/states/input_boolean.se_netzdienlich_enabled" \
  | python3 -m json.tool
```

### Site-Konfiguration und Erstprüfung

```bash
cp config/site_config.env.example config/site_config.env
# Datei bearbeiten und SITE_CONFIG_CONFIRMED=YES setzen
python3 scripts/apply_site_config.py config/site_config.env
bash scripts/run_first_checks.sh
```

## D. Home Assistant Core in Python-Umgebung

### Umgebungsvariablen

Beispiel:

```bash
export CONFIG_ROOT="$HOME/.homeassistant"
export SHARE_ROOT="$HOME/.homeassistant/share"
export HA_API_URL=http://127.0.0.1:8123/api
export HA_TOKEN='DEIN_LONG_LIVED_ACCESS_TOKEN'
```

Wenn das aktive Python-Umfeld Home Assistant enthält, erkennt der Installer automatisch:

```bash
python3 -m homeassistant --script check_config -c "$CONFIG_ROOT"
```

Alternativ explizit setzen:

```bash
export HA_CHECK_COMMAND="python3 -m homeassistant --script check_config -c '$CONFIG_ROOT'"
```

### Installation

```bash
mkdir -p "$SHARE_ROOT"
cd "$SHARE_ROOT"
sha256sum -c SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip.sha256
rm -rf se_controller_release_rc3
mkdir -p se_controller_release_rc3
unzip -q SolarEdge_HA_Energy_Controller_v0.1.0-rc.3.zip \
  -d se_controller_release_rc3
cd se_controller_release_rc3/SolarEdge_HA_Energy_Controller
bash scripts/install_package.sh
```

Home Assistant anschließend mit der für die Installation üblichen Methode neu starten, etwa über `systemctl --user`, einen Dienst oder den eigenen Prozessmanager.

## Bestehende Installation ohne API-Token

Bei einem Update muss der Master vor dem Kopieren sicher ausgeschaltet sein. Kann der Installer mangels Token nicht auf die API zugreifen, bricht er absichtlich ab.

Nach manueller Kontrolle:

```text
input_boolean.se_netzdienlich_enabled = off
binary_sensor.se_nf_controller_write_enabled = off
```

kann für genau diesen Lauf bestätigt werden:

```bash
export SE_CONTROLLER_MASTER_ALREADY_OFF=YES
bash scripts/update_package.sh
```

Diese Bestätigung ersetzt keine spätere Runtime-Prüfung.

## Benutzerdefinierte Konfigurationsprüfung

`HA_CHECK_COMMAND` wird verwendet, wenn `ha core check` und das lokale Home-Assistant-Python-Modul nicht verfügbar sind.

Beispiele:

```bash
export HA_CHECK_COMMAND='docker exec homeassistant python3 -m homeassistant --script check_config -c /config'
```

oder für Docker Compose:

```bash
export HA_CHECK_COMMAND='docker compose exec -T homeassistant python3 -m homeassistant --script check_config -c /config'
```

Die Prüfung darf für eine reguläre Installation nicht fehlschlagen. Der Override

```bash
export SE_CONTROLLER_SKIP_HA_CHECK=YES
```

ist ausschließlich für kontrollierte Diagnosefälle vorgesehen und darf nicht als normaler Installationsweg dokumentiert oder für ein Release-Gate verwendet werden.

## evcc und Optimizer

EVOpt ist optional. Ohne evcc stehen weiterhin zur Verfügung:

- Eigenverbrauch maximieren;
- Netzdienlich laden;
- Akku schonen.

Für `EVOpt optimiert` müssen evcc und dessen Optimizer laufen. Home Assistant muss erreichen können:

```text
http://<evcc-host>:7070/api/state
```

In `site_config.env` wird nur die Basis-URL eingetragen:

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://evcc-host:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
```

Prüfung:

```bash
curl -fsS http://evcc-host:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Nach dem HA-Neustart kann EVOpt bis zu zwei Minuten `warming_up` anzeigen. Erst danach müssen gelten:

```text
sensor.se_nf_evopt_status = healthy
Attribut reason = ok
binary_sensor.se_nf_evopt_active_control = on
```

## Grenzen der Portabilität

Der Installer kann Dateien, Manifest, Backup, Rollback und Prüfungen installationsartenübergreifend ausführen. Er kann jedoch nicht automatisch erraten:

- Host- und Containerpfade;
- den Namen eines Docker-Containers;
- Netzwerkadressen zwischen Containern;
- lokale SolarEdge-Entity-IDs;
- die richtige Batterieauswahl in evcc;
- fremde Automationen außerhalb des sichtbaren Konfigurationsordners.

Diese Werte müssen über `CONFIG_ROOT`, `SHARE_ROOT`, `HA_API_URL`, `HA_TOKEN`, `HA_CHECK_COMMAND` und `site_config.env` korrekt angegeben werden.
