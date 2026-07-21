# Datenschutz und Sicherheit

Nicht veröffentlichen:

- `config/site_config.env`;
- IP-Adressen und lokale Hostnamen;
- `secrets.yaml`;
- Datenbanken und Logdateien;
- private Entity-IDs, wenn sie Rückschlüsse auf Personen oder Geräte zulassen;
- Backups und Runtime-Berichte ohne vorherige Prüfung.

Das Repository enthält nur Beispielwerte. EVOpt nutzt standardmäßig eine nicht erreichbare Beispieldomain.

## Schreibsicherheit

- Master nach Installation aus;
- Site-Konfiguration muss bestätigt sein;
- Config und Sanity müssen `ok` sein;
- ein Writer je Ziel;
- optionale Ziele dürfen leer bleiben;
- Runtime-Manifest erkennt nachträglich veränderte Installationsdateien;
- Konfliktprüfung sucht weitere direkte Writer.

Dieses Projekt steuert elektrische Betriebsmittel. Nutzung und Prüfung erfolgen in eigener Verantwortung.
