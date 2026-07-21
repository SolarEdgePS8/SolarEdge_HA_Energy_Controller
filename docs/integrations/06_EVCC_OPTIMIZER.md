# evcc Optimizer / EVOpt

## Voraussetzungen

- laufendes evcc;
- aktivierter Optimizer;
- von Home Assistant erreichbare evcc-API;
- eindeutige Auswahl der Batterie.

Beispiel:

```dotenv
EVOPT_ENABLED=YES
EVOPT_BASE_URL=http://evcc.example:7070
EVOPT_BATTERY_TITLE=SolarEdge Akku
EVOPT_BATTERY_NAME=
```

Eine lokale IP oder ein lokaler Hostname gehört nur in die private `site_config.env`, niemals in Git.

## Funktionsweise

`se_nf_evopt_shadow_adapter.py` liest den Optimizer-Plan read-only. Der Adapter schreibt nicht auf SolarEdge. Er normalisiert die vier Aktionen:

- `normal`;
- `hold`;
- `charge`;
- `holdcharge`.

Erst Safety und Arbiter entscheiden, ob daraus eine gültige Controller-Anforderung entsteht.

## Fallback

Bei API-Ausfall, altem Plan, fehlender Batterie, widersprüchlichen Slots oder ungültigen Daten wird der EVOpt-Plan verworfen. Der Controller verwendet dann vollständig den Modus „Netzdienlich laden“.
