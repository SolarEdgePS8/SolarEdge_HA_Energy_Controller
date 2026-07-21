# Wetterintegration

Wetter ist optional und verbessert die zeitliche Planung.

```dotenv
WEATHER_ENTITY=weather.home
```

Der Controller verwendet `weather.get_forecasts` und bevorzugt stündliche Vorhersagen. Aus Wettercode, Bewölkung und Niederschlagswahrscheinlichkeit werden konservative Planungsfaktoren abgeleitet.

Bei fehlender Wetter-Entity oder unvollständigen Daten bleibt die Grundplanung aktiv. Wetter darf keinen Writer direkt auslösen und ist kein Pflichtsignal für die Safety-Freigabe.
