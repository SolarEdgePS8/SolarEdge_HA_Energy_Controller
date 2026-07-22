# evcc und Home Assistant

## Zwei getrennte Anbindungen

### 1. Direkte EVOpt-Anbindung des Controllers

Der Controller liest den Optimizer direkt von:

```text
<EVOPT_BASE_URL>/api/state
```

Dafür ist keine zusätzliche Home-Assistant-evcc-Integration erforderlich.

```dotenv
EVOPT_BASE_URL=http://EVCC-HOST:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
EVOPT_ENABLED=YES
```

Die Basis-URL enthält weder `/api` noch `/api/state`.

### 2. Optionale ha-evcc-Integration

[marq24/ha-evcc](https://github.com/marq24/ha-evcc) ist eine inoffizielle HACS-Integration, die viele evcc-Daten und Einstellungen als Home-Assistant-Entities bereitstellt.

Sie ist nützlich für:

- Dashboard-Anzeige;
- Fahrzeug- und Ladepunktdaten;
- Home-Assistant-Automationen;
- optionalen Batteriemodus als Zusatzsignal.

Sie ist nicht nötig, damit der Controller den EVOpt-Plan lesen kann.

## Voraussetzungen von ha-evcc

- laufende evcc-Instanz;
- Home Assistant kann den evcc-Host erreichen;
- üblicher Port `7070`;
- Integration über HACS oder manuell installiert;
- Home Assistant nach Installation neu gestartet.

Der bei der Einrichtung vergebene Name beeinflusst die erzeugten Entity-IDs. Einige Entities sind standardmäßig deaktiviert. Deshalb nennt diese Dokumentation keine feste `sensor.evcc_*`-ID als allgemeingültig.

## Optionaler Batteriemodus

```dotenv
EVOPT_BATTERY_MODE_ENTITY=sensor.example_evcc_battery_mode
```

Dieses Mapping ist nur ein defensives Zusatzsignal. Es ist nicht der Optimizer-Plan und nicht die Steuerautorität.

Ein neutraler Normalisierungsadapter liegt unter [`examples/sensors/evcc_battery_mode_adapter.yaml`](../../examples/sensors/evcc_battery_mode_adapter.yaml).

## API prüfen

```bash
curl -fsS http://EVCC-HOST:7070/api/state \
  | python3 -c "import json,sys; data=json.load(sys.stdin); print('EVCC_API=OK', 'evopt' in data)"
```

Wichtig: Es reicht nicht, dass die evcc-Weboberfläche im Browser erreichbar ist. Home Assistant beziehungsweise der HA-Container muss den Endpunkt erreichen können.

## Startreihenfolge

Nach einem gemeinsamen Neustart kann evcc später als Home Assistant verfügbar sein. Der Controller behandelt das über Warm-up, Health-Gates, Handover und Fallback. Die optionale ha-evcc-Integration kann bei einer ungünstigen Startreihenfolge vorübergehend nicht initialisieren; dies ist getrennt vom direkten EVOpt-Adapter zu betrachten.
