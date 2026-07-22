# Datenschutz und Sicherheit

## Nicht öffentlich teilen

- `config/site_config.env`;
- `SUPERVISOR_TOKEN`, `HA_TOKEN` oder andere API-Schlüssel;
- Inhalte aus `secrets.yaml`;
- private IP-Adressen und interne Hostnamen;
- Wechselrichter-, Batterie- oder Smart-Meter-Seriennummern;
- MAC-Adressen;
- vollständige Home-Assistant-Backups oder Datenbanken;
- unbereinigte Logdateien und lange Verbrauchsverläufe;
- unbereinigte Mapping- oder State-Berichte;
- Stations-, Wetter- oder Entity-Namen mit eindeutigem Standortbezug.

Der read-only Mapping-Assistent schreibt auf Wunsch:

```text
se_controller_mapping_report.json
config/site_config.env
```

Beide Dateien können lokale Entity-IDs und Infrastrukturhinweise enthalten. Sie sind standardmäßig private Arbeitsdateien und müssen vor einem Upload geprüft und neutralisiert werden.

## Sichere Platzhalter

| Privat | Öffentliches Beispiel |
|---|---|
| `http://192.168.x.x:7070` | `http://EVCC-HOST:7070` |
| lokaler Weather-Name | `weather.home` |
| echte Batteriekapazität | `<BATTERY_KWH>` oder neutraler Beispielwert |
| konkrete private Entity | `sensor.example_*` |
| Long-Lived Token | niemals einfügen |

## Schreibsicherheit

- Master bleibt nach Installation, Update, Migration und Rollback AUS;
- `SITE_CONFIG_CONFIRMED=YES` erst nach manueller Prüfung;
- Config Check und Sanity Check müssen `ok` sein;
- genau ein Writer je gemapptem SolarEdge-Ziel;
- optionale Ziele leer lassen, wenn sie nicht benötigt werden;
- EVOpt schreibt nicht direkt auf SolarEdge;
- der Mapping-Assistent ist read-only und ruft keine Services auf;
- der Write-Watchdog ist read-only und protokolliert Schreibversuche;
- das Runtime-Manifest erkennt veränderte Projektdateien;
- die Konfliktprüfung sucht zusätzliche direkte Writer.

## Fremdintegrationen

HACS- und andere Custom Integrations werden unabhängig von diesem Projekt gepflegt. Vor Installation:

- Repository und Release prüfen;
- Backup erstellen;
- Berechtigungen und Datenquellen verstehen;
- keine Zugangsdaten in YAML-Beispiele kopieren;
- bei Updates die jeweilige Projektdokumentation beachten.

Dieses Projekt steuert elektrische Betriebsmittel. Installation, Inbetriebnahme und Prüfung erfolgen in eigener Verantwortung und müssen zur konkreten Anlage passen.
