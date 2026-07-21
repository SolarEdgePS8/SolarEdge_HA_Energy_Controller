# Writer-Eigentum

| Ziel | Controller-Datei |
|---|---|
| Charge-Limit | `se_controller_80_charge_writer.yaml` |
| Discharge-Limit | `se_controller_82_discharge_writer.yaml` |
| Storage Control | `se_controller_83_storage_control_writer.yaml` |
| Command Mode | `se_controller_84_command_mode_writer.yaml` |

Ein Ziel darf nur gemappt werden, wenn keine andere Automation dasselbe Register direkt schreibt. Leere optionale Mappings sind ausdrücklich zulässig.
