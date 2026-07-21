#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[2]

evopt = root / "package/se_controller_50_mode_evopt.yaml"
text = evopt.read_text(encoding="utf-8")
old = """          {% set charge_block = is_state('binary_sensor.se_nf_evopt_charge_block_request', 'on') %}\n\n          {% if source == 'evopt' and charge_block %}\n            {{ closed_w | round(0) }}\n"""
new = """          {% set action_raw = states('sensor.se_nf_evopt_action_raw') %}\n\n          {% set charge_block = is_state('binary_sensor.se_nf_evopt_charge_block_request', 'on') %}\n\n          {% if source == 'evopt' and (action_raw == 'holdcharge' or charge_block) %}\n            {{ closed_w | round(0) }}\n"""
if old not in text:
    raise SystemExit("EVOPT_PATCH_MISMATCH")
evopt.write_text(text.replace(old, new, 1), encoding="utf-8")

writer = root / "package/se_controller_80_charge_writer.yaml"
text = writer.read_text(encoding="utf-8")
old = """            {% set evopt_open = selected == 'EVOpt optimiert'\n               and is_state('binary_sensor.se_nf_evopt_active_control','on')\n               and not is_state('binary_sensor.se_nf_evopt_charge_block_request','on') %}\n"""
new = """            {% set evopt_open = selected == 'EVOpt optimiert'\n               and is_state('binary_sensor.se_nf_evopt_active_control','on')\n               and states('sensor.se_nf_evopt_action_raw') != 'holdcharge'\n               and not is_state('binary_sensor.se_nf_evopt_charge_block_request','on') %}\n"""
if old not in text:
    raise SystemExit("WRITER_PATCH_MISMATCH")
writer.write_text(text.replace(old, new, 1), encoding="utf-8")
print("RC3_RESTRICTIVE_TRANSITION_FIX=PASS")
