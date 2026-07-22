# SolarEdge Controller Testbench

Dieser Ordner enthält ausschließlich synthetische Testkomponenten:

- `reference/`: unabhängiges Python-Sollmodell;
- `fake_evcc/`: umschaltbarer `/api/state`-Server;
- `run_scenarios.py`: ausführbarer Szenarioreport;
- `day_replay.py`: vollständiger Vier-Modi-Replay eines anonymisierten Messdatentags;
- `fixtures/`: neutrale, versionierte Szenario- und Tagesdaten;
- `custom_components/se_test_replay/`: ausschließlich für den HA-Container bestimmter Fake-Time-Replayer.

Keine Komponente dieses Ordners wird durch den produktiven Installer nach Home Assistant kopiert. Es gibt keine Verbindung zu realen SolarEdge-Entities.

## Gemessener 24-Stunden-Tag

```bash
python -m testbench.day_replay \
  --fixture testbench/fixtures/real_day_2026-07-21_15m.json \
  --output-dir artifacts/real-day-24h-model

bash scripts/run_ha_24h_replay.sh
```

Der erste Befehl erzeugt einen unabhängigen Vier-Modi-Entscheidungstrace. Der zweite startet Home Assistant 2026.7.3 mit den unveränderten 18 Produktions-Packages und führt 96 Viertelstunden je Modus aus. Die EVOpt-Aktionen sind synthetische Fehler- und Zustandsinjektionen auf realen Energie-Messwerten.

Die vollständige Beschreibung steht in [`docs/14_REAL_DAY_24H_REPLAY.md`](../docs/14_REAL_DAY_24H_REPLAY.md).
