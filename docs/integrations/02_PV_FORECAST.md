# PV-Prognose

Pflicht sind drei Energieprognosen in `kWh`:

- heute verbleibend;
- heute gesamt;
- morgen gesamt.

Optional:

- übermorgen;
- aktuelle prognostizierte PV-Leistung.

Die Quelle ist frei wählbar, etwa Forecast.Solar, Solcast oder eigene Templates. Der Controller erwartet fertige Home-Assistant-Entities; er bindet keinen Anbieter fest ein.

Wichtig:

- Restprognose heute darf nicht mit Gesamtprognose heute verwechselt werden;
- Werte müssen Energie in `kWh` darstellen;
- `unknown` oder `unavailable` sperrt die Safety-Prüfung;
- Bias-/Korrektursensoren sind erlaubt, aber nicht vorgeschrieben.
