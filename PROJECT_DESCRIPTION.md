# Projektbeschreibung

Der **SolarEdge HA Energy Controller** ist ein portabler Home-Assistant-Controller für SolarEdge-Batteriespeicher.

Er unterstützt vier Betriebsarten:

- Eigenverbrauch maximieren;
- netzdienlich laden;
- Akku schonen;
- EVOpt optimiert mit dem evcc Optimizer.

Planung, Sicherheitsprüfung und Schreibzugriffe sind klar getrennt. Der Controller verwendet einen zentralen Safety-Arbiter, genau einen Writer je gemapptem SolarEdge-Ziel und einen read-only Write-Watchdog zur Analyse von Service-Aufrufen, Zustandswechseln und unerwarteten Schreibern.

Dieses Repository ist der aktive Nachfolger von:

https://github.com/SolarEdgePS8/Solaredge_Netzdienlich

Kurzbeschreibung für den GitHub-Bereich **About**:

> Portabler Home-Assistant-Controller für SolarEdge-Batteriespeicher mit vier Modi, EVCC Optimizer, Safety-Arbiter, Single Writer und Write-Watchdog.
