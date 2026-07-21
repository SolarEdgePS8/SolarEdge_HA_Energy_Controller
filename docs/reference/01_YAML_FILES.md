# Funktion der YAML-Dateien

| Datei | Aufgabe |
|---|---|
| `00_core` | Helper, Site-Mappings, Modusauswahl und Grundnormalisierung |
| `05_external_interfaces` | neutrale externe Signale und zentrale Schreibfreigabe |
| `10_base_planning` | Energiebedarf, Ziel-SoC und Zeitfenster |
| `11_weather_planning` | optionale Wetterprognose und Wetterfaktoren |
| `12_load_pv_planning` | Live-Leistung, Verbrauch und PV-Planung |
| `14_data_sources` | read-only SQL-Auswertung und PV-Tageszähler |
| `20_mode_self_consumption` | Eigenverbrauch maximieren |
| `30_mode_grid_friendly` | netzdienliche Ladeplanung |
| `40_mode_battery_care` | dynamisches Akku-Ziel und Schonlogik |
| `50_mode_evopt` | EVOpt-Auswertung und Fallback |
| `60_safety` | Config-, Sanity-, Alters- und Risikoprüfung |
| `70_arbiter` | Auswahl der gültigen Modusanforderung |
| `80_charge_writer` | alleiniger Charge-Limit-Writer |
| `82_discharge_writer` | alleiniger Discharge-Limit-Writer |
| `83_storage_control_writer` | optionaler Storage-Control-Writer |
| `84_command_mode_writer` | optionaler Command-Mode-Writer |
| `90_diagnostics_planning` | Diagnose- und Planungssensoren |
| `98_compatibility_automations` | kontrollierte Kompatibilitäts- und Startfunktionen |
