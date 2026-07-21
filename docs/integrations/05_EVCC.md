# evcc

evcc ist nur für den Modus „EVOpt optimiert“ erforderlich. Optional kann zusätzlich eine evcc-Batteriemodus-Entity gemappt werden:

```dotenv
EVOPT_BATTERY_MODE_ENTITY=select.example_battery_mode
```

Der Controller interpretiert Ladeanforderungen defensiv. Unbekannte, leere oder nicht unterstützte Werte gelten nicht als sichere Ladeanforderung.

Wallbox-, Fahrzeug- und Ladepunkt-Entities werden nicht direkt vorausgesetzt. Externe Ladeinformationen werden über neutrale Signale angebunden.
