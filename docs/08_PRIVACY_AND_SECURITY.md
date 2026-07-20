# Datenschutz und Sicherheit

## Niemals veröffentlichen

- `secrets.yaml`
- `.storage/`
- `home-assistant_v2.db*`
- Logs und Traces
- Backups
- Tokens, Passwörter und API-Schlüssel
- lokale Hostnamen, IP-Adressen und private URLs
- `config/site_config.env`
- `config/private_migration_values.env`

## Schreibsicherheit

Der Controller schreibt nur, wenn gleichzeitig:

- der Master eingeschaltet ist;
- die Site-Konfiguration bestätigt ist;
- Config- und Sanity-Check `ok` sind;
- kein Risk-Flag aktiv ist;
- das jeweilige Ziel gemappt ist;
- kein externer Writer-Konflikt besteht.

## Externe Automationen

Eigene Automationen dürfen außerhalb des Projekts bestehen bleiben. Sie dürfen aber nicht gleichzeitig dasselbe SolarEdge-Ziel wie ein Controller-Writer beschreiben.

## Installation

Der Installer erstellt vor Änderungen ein Backup unter `/share`, hält den Master aus und führt `ha core check` aus. Bei einem Fehler wird zurückgerollt.
