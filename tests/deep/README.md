# Deep Tests

- `test_architecture_contracts.py`: prüft die tatsächlichen Package-Dateien;
- `test_scenario_matrix.py`: feste Sollszenarien aller vier Modi;
- `test_properties.py`: Hypothesis, Grenzwerte und globale Invarianten;
- `test_state_machine.py`: Fake-Time, EVOpt-Handover, Latch und Cooldown;
- `test_fake_evcc.py`: kontrollierbare evcc-API.

Die Tests verwenden ausschließlich synthetische Daten.
