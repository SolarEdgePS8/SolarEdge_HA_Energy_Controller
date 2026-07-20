# SQL- und Recorder-Auswertung

## Zweck

Historische Verbrauchsdaten verbessern den verbleibenden Tagesverbrauch, den Nachtverbrauch und den Tagesverbrauch in einem Zeitfenster.

## Aktuell unterstützt

Die mitgelieferten Skripte lesen die lokale Home-Assistant-SQLite-Datenbank:

```text
/config/home-assistant_v2.db
```

Der Zugriff erfolgt ausschließlich read-only mit `mode=ro` beziehungsweise `PRAGMA query_only=ON`.

## Benötigter Sensor

Ein kumulierter Tagesverbrauchssensor, der innerhalb eines Tages ansteigt und täglich zurückgesetzt wird:

```dotenv
CONSUMPTION_TODAY_ENTITY=sensor.daily_consumption
```

Einheit: `kWh` bevorzugt; `Wh` und `MWh` werden umgerechnet.

## Auswertungen

- Restverbrauch: Vergleich des aktuellen Zeitpunkts mit bis zu sieben vergangenen vollständigen Tagen.
- Nachtverbrauch: historische Werte zwischen dynamischem Abend- und Morgenzeitpunkt, ausgewertet mit Median und Sicherheitsperzentil.
- Tagesverbrauch: Median gültiger historischer Tagesfenster.

In der Regel werden mindestens drei verwertbare Tage oder Nächte benötigt.

## Fallback

Bei fehlender Datenbank, nicht unterstütztem Recorder-Schema, zu wenig Historie oder fehlendem Sensor bleibt der Controller funktionsfähig und verwendet manuelle Fallbackwerte.

## Externe Datenbanken

Die aktuelle Version greift nicht direkt auf MariaDB oder PostgreSQL zu. Nutzer externer Recorder-Datenbanken lassen die SQL-Funktion deaktiviert oder stellen geeignete Prognosesensoren selbst bereit.
