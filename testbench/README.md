# SolarEdge Controller Testbench

Dieser Ordner enthält ausschließlich synthetische Testkomponenten:

- `reference/`: unabhängiges Python-Sollmodell;
- `fake_evcc/`: umschaltbarer `/api/state`-Server;
- `run_scenarios.py`: ausführbarer Szenarioreport.

Keine Komponente dieses Ordners wird durch den produktiven Installer nach Home Assistant kopiert. Es gibt keine Verbindung zu realen SolarEdge-Entities.
