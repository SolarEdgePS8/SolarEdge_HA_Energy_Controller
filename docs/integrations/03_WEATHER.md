# Wetterintegration

## Zweck

Wetterdaten verschieben bei ungünstiger Bewölkung den geplanten Ladebeginn kontrolliert nach vorn. Sie ersetzen keine PV-Prognose.

## Konfiguration

```dotenv
WEATHER_ENTITY=weather.home
```

Danach die Wetterplanung über den vorgesehenen Helper aktivieren.

## Bevorzugte Daten

Der Controller ruft `weather.get_forecasts` mit stündlicher Vorhersage auf. Für Vormittag, Mittag und Nachmittag werden Faktoren gebildet.

## Fallback

Falls keine passenden Stundenwerte vorhanden sind:

- wird der aktuelle Wetterzustand berücksichtigt;
- anschließend greift ein konfigurierbarer konservativer Faktor;
- der Modus bleibt funktionsfähig.

Wetter ist optional. Bei deaktivierter Wetterplanung gilt ein neutraler Faktor.
