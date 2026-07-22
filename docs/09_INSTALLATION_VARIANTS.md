# Installation auf Home Assistant OS, Supervised, Container und Core

Die Controller-YAMLs sind normale Home-Assistant-Packages. Unterschiede betreffen vor allem Pfade, API-Token und die Konfigurationsprüfung.

## Gemeinsamer Sicherheitsablauf

Unabhängig vom System:

1. Backup erstellen;
2. Release-SHA256 prüfen;
3. Installer ausführen;
4. Home Assistant neu starten;
5. Mapping-Assistent read-only ausführen;
6. `site_config.env` manuell prüfen;
7. Site-Konfiguration anwenden;
8. First Checks und Writer-Konflikte prüfen;
9. Master zuletzt einschalten.

Der Installer aktiviert den Master nie.

## Home Assistant OS

```bash
cd /share/se_controller_release_rc4/SolarEdge_HA_Energy_Controller
bash scripts/install_package.sh
ha core restart

python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

`SUPERVISOR_TOKEN` und `ha`-CLI werden normalerweise vom Terminal-/SSH-Add-on bereitgestellt.

## Home Assistant Supervised

Der Ablauf entspricht Home Assistant OS, sofern `/config`, `/share`, Supervisor-API und `ha`-CLI verfügbar sind.

## Home Assistant Container

Das Release muss in einer Wartungsumgebung ausgeführt werden, die den echten HA-Konfigurationsordner beschreibbar gemountet hat.

```bash
export CONFIG_ROOT=/config
export SHARE_ROOT=/share
export HA_TOKEN='DEIN_LONG_LIVED_ACCESS_TOKEN'
export HA_API_URL='http://homeassistant:8123/api'
export HA_CHECK_COMMAND='docker exec homeassistant python3 -m homeassistant --script check_config -c /config'

bash scripts/install_package.sh

python3 scripts/discover_entities.py \
  --report /share/se_controller_mapping_report.json \
  --output config/site_config.env
```

Der Name `homeassistant` ist nur ein Beispiel für den Container-/DNS-Namen.

## Home Assistant Core

```bash
export CONFIG_ROOT="$HOME/.homeassistant"
export SHARE_ROOT="$HOME/se_controller_backups"
export HA_TOKEN='DEIN_LONG_LIVED_ACCESS_TOKEN'
export HA_API_URL='http://127.0.0.1:8123/api'
export HA_CHECK_COMMAND="python3 -m homeassistant --script check_config -c $CONFIG_ROOT"

bash scripts/install_package.sh
python3 scripts/discover_entities.py \
  --report "$SHARE_ROOT/se_controller_mapping_report.json" \
  --output config/site_config.env
```

## Offline-Mapping

Kann das Wartungssystem die HA-API nicht erreichen, kann eine zuvor exportierte `/api/states`-JSON-Datei verwendet werden:

```bash
python3 scripts/discover_entities.py \
  --states-file /pfad/ha_states.json \
  --report /pfad/mapping_report.json \
  --output config/site_config.env
```

Der Export enthält lokale Entity-IDs und möglicherweise Standortbezüge. Nicht ungeprüft öffentlich teilen.

## Konfigurationsprüfung

Der Installer verwendet:

1. `HA_CHECK_COMMAND`, falls gesetzt;
2. sonst `ha core check`;
3. sonst ein vorhandenes Home-Assistant-Pythonmodul.

Ohne mögliche Prüfung bricht er sicher ab. `SE_CONTROLLER_SKIP_HA_CHECK=YES` ist kein normaler Installationsweg.
