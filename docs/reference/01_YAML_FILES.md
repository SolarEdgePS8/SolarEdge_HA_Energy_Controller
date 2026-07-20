# Funktion der YAML-Dateien

| Datei | Aufgabe |
|---|---|
| `se_controller_00_core.yaml` | Master, Site-Mappings, zentrale Helper, Modusauswahl und Grundkonfiguration |
| `se_controller_05_external_interfaces.yaml` | neutrale optionale EV-, Entlade- und Peak-Lock-Signale |
| `se_controller_10_base_planning.yaml` | gemeinsame Zeitfenster, Energiebedarf und geplante Startzeiten |
| `se_controller_11_weather_planning.yaml` | stündliche Wetterabfrage, Wetterfaktoren und Vorverlegung |
| `se_controller_12_load_pv_planning.yaml` | Verbrauchsprognose, PV-Verfügbarkeit und Deckungsberechnung |
| `se_controller_14_data_sources.yaml` | read-only SQLite-Abfragen und historische Tages-/Nachtprognosen |
| `se_controller_20_mode_self_consumption.yaml` | Anforderungen für „Eigenverbrauch maximieren“ |
| `se_controller_30_mode_grid_friendly.yaml` | vollständige netzdienliche Planung und EVOpt-Fallback |
| `se_controller_40_mode_battery_care.yaml` | dynamisches Ziel, Schonlogik und Ziel-erreicht-Latch |
| `se_controller_50_mode_evopt.yaml` | EVOpt-Gates, Planbewertung und interne Anforderungen |
| `se_controller_60_safety.yaml` | Config-, Plausibilitäts-, Alters- und Risikoprüfungen |
| `se_controller_70_arbiter.yaml` | Auswahl einer gültigen Modusanforderung und Session-State-Ownership |
| `se_controller_80_charge_writer.yaml` | einziger Charge-Limit-Writer |
| `se_controller_82_discharge_writer.yaml` | optionaler Discharge-Limit-Writer |
| `se_controller_83_storage_control_writer.yaml` | optionaler Storage-Control-Writer |
| `se_controller_84_command_mode_writer.yaml` | optionaler Storage-Command-Mode-Writer |
| `se_controller_90_diagnostics_planning.yaml` | Diagnose, adaptive Korrekturen, Latches und Planungsstatus |
| `se_controller_98_compatibility_automations.yaml` | kompatible Ansichts- und Zustandsaktualisierungen ohne direkte SolarEdge-Writes |

## Python-Helfer

| Datei | Aufgabe |
|---|---|
| `se_nf_evopt_shadow_adapter.py` | evcc-Optimizer-Plan lesen und normalisieren |
| `se_nf_load_forecast_7d_cached.py` | verbleibenden Tagesverbrauch aus SQLite ableiten |
| `se_nf_night_forecast_7d.py` | Nachtverbrauch aus historischen Fenstern ableiten |
| `se_nf_daytime_forecast_7d.py` | Tagesverbrauch aus historischen Fenstern ableiten |
| `se_controller_runtime_checker.py` | installierte Dateien, Entities, Mappings und Runtime-Gates prüfen |
