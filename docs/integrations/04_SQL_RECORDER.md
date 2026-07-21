# SQL-/Recorder-Auswertung

Die Python-Skripte lesen die Home-Assistant-Recorder-Datenbank ausschließlich im Read-only-Modus.

Standardpfad:

```text
/config/home-assistant_v2.db
```

Benötigt wird ein kumulativer Tagesverbrauchssensor in `kWh`:

```dotenv
CONSUMPTION_TODAY_ENTITY=sensor.house_energy_today
```

Berechnet werden:

- verbleibender Tagesverbrauch aus ähnlichen Tagen;
- Nachtverbrauch;
- Tagesverbrauch;
- Median- und P80-Werte;
- Gültigkeit und Anzahl verwendeter Tage.

Mindestens drei verwertbare Tage werden erwartet. Bei MariaDB oder externer Recorder-Datenbank funktionieren die SQLite-Skripte nicht; dann bleiben die manuellen Fallbackwerte aktiv.
