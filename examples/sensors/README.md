# Optionale Zusatzsensoren – Beispiele

Diese Dateien sind **keine Pflichtbestandteile** des Controllers und werden vom Installer **nicht automatisch nach `/config/packages` kopiert**. Sie zeigen neutrale, portable Bausteine für Installationen, denen eine passende Leistung, Tagesenergie, Prognose, evcc-Status- oder Preis-Entity fehlt.

## Vor dem Kopieren

1. Datei öffnen und alle `sensor.example_*`-Platzhalter ersetzen.
2. In **Entwicklerwerkzeuge → Zustände** Einheit, Wertebereich und Aktualisierung der Quelle prüfen.
3. Die Datei einzeln nach `/config/packages/` kopieren.
4. Konfiguration prüfen:

   ```bash
   ha core check
   ```

5. Home Assistant neu starten.
6. Die neue Entity mindestens einige Aktualisierungen beobachten.
7. Erst danach in `site_config.env` mappen.

> Kein Beispiel in diesem Ordner schreibt auf SolarEdge. Die Dateien erzeugen ausschließlich Sensoren oder Energiezähler.

## Übersicht

| Datei | Zweck | Ergebnis |
|---|---|---|
| [`pv_power_filtered.yaml`](pv_power_filtered.yaml) | optionale Glättung einer PV-Leistung | Leistung in `W` |
| [`daily_energy_helpers.yaml`](daily_energy_helpers.yaml) | Leistung in Energie integrieren und täglich zählen | Energie in `kWh` |
| [`pv_forecast_adapter.yaml`](pv_forecast_adapter.yaml) | Anbieter-Prognosen auf Controller-Bedeutungen abbilden | Prognosen in `kWh`/`W` |
| [`evcc_battery_mode_adapter.yaml`](evcc_battery_mode_adapter.yaml) | fremden evcc-Modus auf stabile Textwerte normalisieren | Textstatus |
| [`electricity_price_adapter.yaml`](electricity_price_adapter.yaml) | Gesamtpreis auf `ct/kWh` normieren | Preis in `ct/kWh` |

## Wichtige Grenzen

- Ein Filter kann die Reaktion verzögern. Für `LIVE_PV_POWER_ENTITIES` ist eine plausible Rohquelle meist der bessere erste Eintrag.
- Ein Integral aus Leistung ist eine Näherung. Ein echter Energiezähler aus Wechselrichter oder Smart Meter ist vorzuziehen.
- Forecast-Entity-Namen und Attribute unterscheiden sich je Anbieter. Das Beispiel muss an den konkreten Anbieter angepasst werden.
- Die ha-evcc-Integration erzeugt installationsabhängige Entity-IDs. Das Beispiel setzt keine feste ID voraus.
- Ein Börsenpreis ist nicht automatisch dein Endkundenpreis. Zuschläge, Steuern und Mehrwertsteuer müssen fachlich korrekt berücksichtigt sein.
