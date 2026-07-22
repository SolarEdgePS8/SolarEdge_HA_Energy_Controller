# Dynamische Strompreise und Energiekosten

Diese Integrationen sind **optional**. Der öffentliche Controller-Kern besitzt derzeit kein Pflicht-Mapping für einen Strompreis-Sensor. Preis- und Kostendaten können für Dashboards, Auswertung oder eigene externe Automationen genutzt werden, dürfen aber nicht mit den Pflichtdaten für PV-Leistung, Hausverbrauch oder PV-Prognose verwechselt werden.

## EPEX Spot

Projekt: [mampfes/ha_epex_spot](https://github.com/mampfes/ha_epex_spot)

Die Integration kann Marktpreise aus mehreren Datenquellen beziehen und stellt unter anderem bereit:

- Gesamtpreis;
- Marktpreis;
- Tagesdurchschnitt und Median;
- niedrigsten und höchsten Preis;
- Quantil und Rang des aktuellen Preises;
- Preiszeitreihe für heute und morgen als Sensorattribute.

### Gesamtpreis oder Marktpreis?

Der reine Marktpreis enthält üblicherweise nicht alle Zuschläge, Steuern und die Umsatzsteuer. Für eine reale Kostenentscheidung ist ein korrekt konfigurierter Gesamtpreis meist geeigneter.

Prüfen:

```text
Einheit: €/kWh, EUR/kWh oder ct/kWh
Zeitauflösung: passend zum Tarif
Attribute: enthalten heute/morgen und korrekte Zeitzonen
Zuschläge/Steuern: vollständig und vertragsspezifisch
```

## Dynamic Energy Cost

Projekt: [martinarva/dynamic_energy_cost](https://github.com/martinarva/dynamic_energy_cost)

Die Integration verwendet:

1. einen Preis-Sensor;
2. einen Energie- oder alternativ Leistungssensor;

und erzeugt daraus unter anderem:

- aktuelle Kostenrate;
- 15-Minuten-, Stunden-, Tages-, Wochen-, Monats- und Jahreskosten;
- manuell rücksetzbare Kostensensoren.

Wenn ein verlässlicher Energiezähler vorhanden ist, ist er für Abrechnung und Statistik in der Regel genauer als eine nachträgliche Integration von Momentanleistung.

## Einordnung zum SolarEdge HA Energy Controller

| Datenpunkt | Für Controller-Kern geeignet? |
|---|---|
| aktueller Gesamtpreis | nur für eigene Erweiterungen/externe Signale |
| Marktpreis | nur nach Ergänzung aller Vertragsbestandteile |
| dynamische Kosten heute | Diagnose/Dashboard |
| Leistungs-Sensor aus Kostenintegration | nein, ursprüngliche Leistungsquelle verwenden |
| Energie-Sensor aus Kostenintegration | Diagnose, nicht als Live-Leistung |
| Preisrang/Quantil | mögliche externe Automation, nicht Pflicht-Mapping |

## Neutraler Preisadapter

Das Beispiel [`examples/sensors/electricity_price_adapter.yaml`](../../examples/sensors/electricity_price_adapter.yaml) normalisiert einen Preis-Sensor auf `ct/kWh`.

Vor Nutzung muss genau eine Quelle eingetragen werden. Der Adapter ist optional und wird vom Installer nicht automatisch installiert.

## Datenschutz

Nicht veröffentlichen:

- API-Tokens;
- Vertragsnummern;
- konkrete private Preisaufschläge, wenn diese vertraulich sind;
- lange Verbrauchs- oder Preisverläufe mit Rückschluss auf Anwesenheit;
- private Hostnamen oder interne IP-Adressen.
