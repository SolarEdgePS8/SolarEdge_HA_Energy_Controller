# PV-Prognose: Anbieterwerte auf Controller-Sensoren abbilden

Der Controller ist nicht an Forecast.Solar, Solcast oder einen anderen Anbieter gebunden. Er benötigt fertige Home-Assistant-Sensoren mit einer klaren Bedeutung.

## Pflichtwerte

| Mapping | Bedeutung | Einheit |
|---|---|---|
| `PV_FORECAST_TODAY_REMAINING_ENTITY` | noch erwartete PV-Energie von jetzt bis Tagesende | `kWh` |
| `PV_FORECAST_TODAY_TOTAL_ENTITY` | erwartete PV-Energie des gesamten heutigen Tages | `kWh` |
| `PV_FORECAST_TOMORROW_ENTITY` | erwartete PV-Energie des morgigen Tages | `kWh` |

Optional:

| Mapping | Bedeutung | Einheit |
|---|---|---|
| `PV_FORECAST_DAY_AFTER_TOMORROW_ENTITY` | übermorgen gesamt | `kWh` |
| `FORECAST_NOW_ENTITY` | aktuell erwartete PV-Leistung | `W` |

## Warum „heute verbleibend“ wichtig ist

Ein Tageswert von `12 kWh` sagt am Nachmittag nicht, wie viel davon bereits produziert wurde. Der Controller benötigt deshalb zusätzlich die Restenergie.

Viele Anbieter liefern nur Tagesprognose und Morgenprognose. Dann kann eine neutrale Näherung gebildet werden:

```text
heute verbleibend = max(Prognose heute gesamt − PV-Ertrag heute, 0)
```

Beispiel: [`examples/sensors/pv_forecast_adapter.yaml`](../../examples/sensors/pv_forecast_adapter.yaml).

## Anbieter-Entity direkt verwenden

Eine direkte Zuordnung ist sinnvoll, wenn:

- der Sensor genau die benötigte Bedeutung hat;
- die Einheit `kWh` beziehungsweise `W` stimmt;
- `unknown`/`unavailable` korrekt signalisiert wird;
- der Wert regelmäßig aktualisiert wird;
- Tagesgrenzen zur lokalen Zeitzone passen.

## Adapter-Sensor verwenden

Ein Template ist nötig, wenn der Anbieter:

- andere Entity-Namen verwendet;
- Werte in `Wh` oder `MWh` liefert;
- nur Attribute statt eigener Entities bereitstellt;
- „heute verbleibend“ nicht direkt liefert;
- mehrere Dachflächen zusammengeführt werden müssen.

Bei Template-Sensoren:

- `availability` definieren;
- negative Restwerte auf `0` begrenzen;
- Zahlen statt Text liefern;
- `device_class: energy` nur bei Energie verwenden;
- `state_class: measurement` nur bei aktuellen Prognosemesswerten setzen;
- keine private Standort- oder API-Information im YAML veröffentlichen.

## Korrigierte oder „biased“ Prognosen

Namen wie:

```text
sensor.pv_prognose_heute_verbleibend_biased
sensor.pv_prognose_morgen_biased
```

sind lokale Sensoren, keine Standards eines Forecast-Anbieters. Eine Bias-Korrektur kann sinnvoll sein, muss aber dokumentieren:

- Rohquelle;
- Lern- oder Korrekturfaktor;
- Zeitraum;
- Begrenzungen;
- Verhalten bei fehlenden Daten.

Ohne Originaldefinition darf ein solcher Sensor nicht allein aus seinem Namen rekonstruiert werden.

## Prüfung

In Entwicklerwerkzeuge → Zustände kontrollieren:

```text
heute verbleibend: numerisch, >= 0, kWh
heute gesamt:      numerisch, >= 0, kWh
morgen:            numerisch, >= 0, kWh
Prognose jetzt:    numerisch, >= 0, W
```

Anschließend:

```bash
bash scripts/run_first_checks.sh
```
