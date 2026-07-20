# Modus: EVOpt optimiert

## Ziel

Der evcc Optimizer darf die Speicherstrategie vorgeben. Der Controller übersetzt einen gültigen Optimizer-Plan in seine eigenen sicheren Anforderungen.

## Voraussetzungen

- laufendes evcc;
- erreichbare evcc-API;
- aktivierter Optimizer;
- richtige Batterie im Optimizer-Plan;
- `EVOPT_ENABLED=YES`;
- korrekte Basis-URL;
- EVOpt-Adapter installiert.

## Konfiguration

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://evcc-host:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
EVOPT_BATTERY_MODE_ENTITY=
```

`EVOPT_BATTERY_TITLE` und `EVOPT_BATTERY_NAME` dienen dazu, die richtige Batterie im Plan zuzuordnen.

## Verarbeitete Strategien

Der Adapter bewertet je nach evcc-Version und Plan unter anderem:

- normaler Betrieb;
- Laden zurückhalten;
- Entladen sperren;
- gezieltes Laden;
- kombinierte Hold-/Charge-Zustände.

## Sicherheits-Gates

EVOpt wird nur übernommen, wenn:

- API erreichbar;
- Schema erkannt;
- Batterie eindeutig;
- Daten aktuell;
- Plan zeitlich gültig;
- Werte plausibel;
- Stabilitätsprüfung bestanden.

## Fallback

Bei jedem fehlenden oder widersprüchlichen Gate läuft vollständig der Modus `Netzdienlich laden` weiter. EVOpt ist damit kein Single Point of Failure.

## Diagnose

Wichtige Punkte sind EVOpt-Datenstatus, Health-/Schema-/Plan-Gates, Grid-Charge-Anforderung, Discharge-Lock-Anforderung und das effektive Planungsprofil.
