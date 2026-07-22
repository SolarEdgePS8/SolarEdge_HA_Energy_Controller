# Wetterintegration

Wetter ist optional. Der Controller verwendet keine fest verdrahteten Temperatur- oder Bewölkungssensoren, sondern eine normale Home-Assistant-Weather-Entity.

```dotenv
WEATHER_ENTITY=weather.home
```

## Mindestanforderung

Die Entity muss über Home Assistants Aktion `weather.get_forecasts` einen stündlichen Forecast liefern können.

Prüfung in **Entwicklerwerkzeuge → Aktionen**:

```yaml
action: weather.get_forecasts
target:
  entity_id: weather.home
data:
  type: hourly
response_variable: weather_forecast
```

Die Antwort sollte mehrere Stunden mit Zeitstempel und Wetterdaten enthalten.

## Beispiel: DWD Weather

Für Standorte in Deutschland ist [DWD Weather](https://github.com/FL550/dwd_weather) eine mögliche HACS-Integration. Sie stellt pro konfigurierter Station eine `weather.*`-Entity bereit und kann zusätzlich zahlreiche stündliche Sensoren erzeugen.

Für den Controller reicht normalerweise die Weather-Entity. Die zusätzlichen DWD-Sensoren sind standardmäßig deaktiviert und werden für das Mapping `WEATHER_ENTITY` nicht benötigt.

Typisches, aber installationsabhängiges Muster:

```text
weather.dwd_weather_<stationsname>
```

Nicht den Namen aus einem fremden Beispiel kopieren, sondern die eigene Entity aus Entwicklerwerkzeuge → Zustände auswählen.

## Was der Controller daraus macht

Der Wetteradapter bewertet die stündliche Vorhersage konservativ und leitet einen Planungsfaktor ab. Wetter ersetzt keine PV-Prognose. Es modifiziert nur die Planung, wenn eine verwertbare Vorhersage verfügbar ist.

Bei fehlendem oder ungültigem Wetter greift die dokumentierte Fallbacklogik. Das Charge-Limit wird nicht direkt von einer Wetterintegration geschrieben.

## Datenschutz

Öffentliche Beispiele verwenden `weather.home`. Stationsnamen, Ortsbezug und Koordinaten gehören nicht in Support-Archive, wenn sie Rückschlüsse auf den Standort erlauben.
