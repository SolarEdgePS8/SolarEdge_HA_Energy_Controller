#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise SystemExit(f"PATCH_MISMATCH: {label}")
    return text.replace(old, new, 1)


evopt_path = ROOT / "package/se_controller_50_mode_evopt.yaml"
text = evopt_path.read_text(encoding="utf-8")
text = text.replace(
    "# SolarEdge Energy Controller v0.0.1 · Modus EVOpt optimiert",
    "# SolarEdge HA Energy Controller v0.1.0-rc.3 · Modus EVOpt optimiert",
)
text = replace_once(
    text,
    """        - action_raw
        - action_source
        - action_inference_reason
        - suggested_charge
        - suggested_discharge
        - action_plan_consistent
""",
    """        - action_raw
        - action_source
        - action_inference_reason
        - suggestion_action
        - suggestion_plan_consistent
        - suggestion_overridden
        - slot_action
        - slot_action_reason
        - suggested_charge
        - suggested_discharge
        - action_plan_consistent
""",
    "json attributes",
)
charge_stable = """      - name: SE NF EVOpt Charge Stable
        unique_id: se_nf_evopt_charge_stable
        icon: mdi:battery-charging-high
        state: >-
          {{ is_state('binary_sensor.se_nf_evopt_shadow_ready', 'on')
             and states('sensor.se_nf_evopt_action_raw') == 'charge' }}
        delay_on:
          seconds: 60
"""
text = replace_once(
    text,
    charge_stable,
    charge_stable + """      - name: SE NF EVOpt Charge Block Request
        unique_id: se_nf_evopt_charge_block_request
        icon: mdi:battery-lock
        state: >-
          {{ is_state('binary_sensor.se_nf_evopt_shadow_ready', 'on')
             and states('sensor.se_nf_evopt_action_raw') == 'holdcharge' }}
        delay_off:
          seconds: 60
""",
    "charge block request",
)
text = replace_once(
    text,
    """      - name: SE NF EVOpt Active Control
        unique_id: se_nf_evopt_active_control
        icon: mdi:toggle-switch
        state: "{% set selected = states('sensor.se_nf_optimization_mode_effective') %}\\n{% set action = states('sensor.se_nf_evopt_action_stable')
          %}\\n{% set base = selected == 'EVOpt optimiert'\\n  and is_state('binary_sensor.se_nf_evopt_shadow_ready','on')\\n  and is_state('input_boolean.se_netzdienlich_enabled','on')\\n\\
          \\  and is_state('sensor.se_nf_config_check','ok')\\n  and is_state('sensor.se_nf_sanity_check','ok')\\n  and states('input_select.se_nf_session_state')
          not in ['evcc_override','low_soc','risk'] %}\\n{% set charge_ok = is_state('binary_sensor.se_nf_evopt_charge_control_available','on')
          %}\\n{% set discharge_ok = is_state('binary_sensor.se_nf_evopt_discharge_control_available','on') %}\\n{% set grid_ok = is_state('binary_sensor.se_nf_evopt_grid_charge_control_available','on')
          %}\\n{{ base and (\\n   (action in ['holdcharge','normal'] and charge_ok)\\n   or (action == 'hold' and charge_ok and discharge_ok)\\n \\
          \\  or (action == 'charge' and charge_ok and discharge_ok and grid_ok)\\n) }}"
      - name: SE NF EVOpt Discharge Lock Request
        unique_id: se_nf_evopt_discharge_lock_request
        icon: mdi:battery-lock
        state: "{{ is_state('binary_sensor.se_nf_evopt_active_control','on') and states('sensor.se_nf_evopt_action_stable') in ['hold','charge']
          }}"
      - name: SE NF EVOpt Grid Charge Request
        unique_id: se_nf_evopt_grid_charge_request
        icon: mdi:transmission-tower-import
        state: "{{ is_state('binary_sensor.se_nf_evopt_active_control','on') and states('sensor.se_nf_evopt_action_stable') == 'charge' }}"
""",
    """      - name: SE NF EVOpt Active Control
        unique_id: se_nf_evopt_active_control
        icon: mdi:toggle-switch
        state: >-
          {% set selected = states('sensor.se_nf_optimization_mode_effective') %}
          {% set action = states('sensor.se_nf_evopt_action_raw') %}
          {% set base = selected == 'EVOpt optimiert'
             and is_state('binary_sensor.se_nf_evopt_shadow_ready','on')
             and is_state('input_boolean.se_netzdienlich_enabled','on')
             and is_state('sensor.se_nf_config_check','ok')
             and is_state('sensor.se_nf_sanity_check','ok')
             and states('input_select.se_nf_session_state') not in ['evcc_override','low_soc','risk'] %}
          {% set charge_ok = is_state('binary_sensor.se_nf_evopt_charge_control_available','on') %}
          {% set discharge_ok = is_state('binary_sensor.se_nf_evopt_discharge_control_available','on') %}
          {% set grid_ok = is_state('binary_sensor.se_nf_evopt_grid_charge_control_available','on') %}
          {{ base and (
             (action in ['holdcharge','normal'] and charge_ok)
             or (action == 'hold' and charge_ok and discharge_ok)
             or (action == 'charge' and charge_ok and discharge_ok and grid_ok)
          ) }}
        attributes:
          action_raw: "{{ states('sensor.se_nf_evopt_action_raw') }}"
          action_stable: "{{ states('sensor.se_nf_evopt_action_stable') }}"
          transition_policy: restrictive_immediate_permissive_delayed
      - name: SE NF EVOpt Discharge Lock Request
        unique_id: se_nf_evopt_discharge_lock_request
        icon: mdi:battery-lock
        state: >-
          {{ is_state('binary_sensor.se_nf_evopt_active_control','on')
             and states('sensor.se_nf_evopt_action_raw') in ['hold','charge'] }}
        delay_off:
          seconds: 60
      - name: SE NF EVOpt Grid Charge Request
        unique_id: se_nf_evopt_grid_charge_request
        icon: mdi:transmission-tower-import
        state: >-
          {{ is_state('binary_sensor.se_nf_evopt_active_control','on')
             and states('sensor.se_nf_evopt_action_raw') == 'charge' }}
        delay_on:
          seconds: 60
""",
    "active control",
)
text = replace_once(
    text,
    """        attributes:
          reason: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'health_reason') }}"
          updated: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'updated') }}"
          age_min: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'age_min') }}"
          solver_status: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'solver_status') }}"
          response_ms: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'response_ms') }}"
          fresh_by_update: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'fresh_by_update') }}"
          current_slot_valid: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'current_slot_valid') }}"
          slot_freshness_override: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_freshness_override') }}"
          hard_stale_limit_min: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'hard_stale_limit_min') }}"
          action_source: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_source') }}"
""",
    """        attributes:
          reason: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'health_reason') }}"
          updated: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'updated') }}"
          age_min: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'age_min') }}"
          solver_status: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'solver_status') }}"
          response_ms: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'response_ms') }}"
          fresh_by_update: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'fresh_by_update') }}"
          current_slot_valid: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'current_slot_valid') }}"
          current_slot_index: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_index') }}"
          slot_freshness_override: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_freshness_override') }}"
          hard_stale_limit_min: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'hard_stale_limit_min') }}"
          action_source: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_source') }}"
          suggestion_action: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_action') }}"
          suggestion_plan_consistent: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_plan_consistent') }}"
          suggestion_overridden: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_overridden') }}"
          slot_action: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_action') }}"
          slot_action_reason: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_action_reason') }}"
""",
    "status attributes",
)
text = replace_once(
    text,
    """        attributes:
          actionable: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'battery_actionable') }}"
          action_source: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_source') }}"
          inference_reason: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_inference_reason') }}"
          suggested_charge: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggested_charge') }}"
          suggested_discharge: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggested_discharge') }}"
""",
    """        attributes:
          actionable: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'battery_actionable') }}"
          action_source: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_source') }}"
          inference_reason: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_inference_reason') }}"
          suggestion_action: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_action') }}"
          suggestion_plan_consistent: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_plan_consistent') }}"
          suggestion_overridden: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_overridden') }}"
          slot_action: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_action') }}"
          slot_action_reason: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_action_reason') }}"
          suggested_charge: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggested_charge') }}"
          suggested_discharge: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggested_discharge') }}"
""",
    "action attributes",
)
text = replace_once(
    text,
    """        attributes:
          fallback_profile: Netzdienlich laden
          reason: "{{ states('sensor.se_nf_evopt_shadow_reason') }}"
""",
    """        attributes:
          fallback_profile: Netzdienlich laden
          code: "{{ states('sensor.se_nf_evopt_fallback_code') }}"
          reason: "{{ states('sensor.se_nf_evopt_shadow_reason') }}"
          started_at: >-
            {% if is_state('binary_sensor.se_nf_evopt_fallback_active', 'on') %}
              {{ as_local(states.binary_sensor.se_nf_evopt_fallback_active.last_changed).isoformat() }}
            {% else %}
              {{ none }}
            {% endif %}
          duration_s: >-
            {% if is_state('binary_sensor.se_nf_evopt_fallback_active', 'on') %}
              {{ (now().timestamp() - as_timestamp(states.binary_sensor.se_nf_evopt_fallback_active.last_changed, now().timestamp())) | int(0) }}
            {% else %}
              0
            {% endif %}
""",
    "fallback attributes",
)
text = replace_once(
    text,
    """          {% set source = states('sensor.se_nf_evopt_candidate_source') %}

          {% set action = states('sensor.se_nf_evopt_action_stable') %}

          {% if source == 'evopt' and action == 'holdcharge' %}
            {{ closed_w | round(0) }}
          {% elif source == 'evopt' and action in ['normal','hold','charge'] %}
            {{ open_w | round(0) }}
          {% else %}
            {{ fallback | round(0) }}
          {% endif %}
        attributes:
          action_stable: "{{ states('sensor.se_nf_evopt_action_stable') }}"
          source: "{{ states('sensor.se_nf_evopt_candidate_source') }}"
          charge_control: binary_0_or_5000
          fallback: Netzdienlich laden
""",
    """          {% set source = states('sensor.se_nf_evopt_candidate_source') %}

          {% set charge_block = is_state('binary_sensor.se_nf_evopt_charge_block_request', 'on') %}

          {% if source == 'evopt' and charge_block %}
            {{ closed_w | round(0) }}
          {% elif source == 'evopt' %}
            {{ open_w | round(0) }}
          {% else %}
            {{ fallback | round(0) }}
          {% endif %}
        attributes:
          action_raw: "{{ states('sensor.se_nf_evopt_action_raw') }}"
          action_stable: "{{ states('sensor.se_nf_evopt_action_stable') }}"
          charge_block_request: "{{ states('binary_sensor.se_nf_evopt_charge_block_request') }}"
          source: "{{ states('sensor.se_nf_evopt_candidate_source') }}"
          charge_control: binary_0_or_5000
          transition_policy: restrictive_immediate_permissive_delayed
          fallback: Netzdienlich laden
""",
    "candidate target",
)
marker = """      - name: SE NF EVOpt Shadow Reason
        unique_id: se_nf_evopt_shadow_reason
"""
fallback_code = """      - name: SE NF EVOpt Fallback Code
        unique_id: se_nf_evopt_fallback_code
        icon: mdi:alert-decagram-outline
        state: >-
          {% set selected = states('sensor.se_nf_optimization_mode_effective') %}
          {% set source = states('sensor.se_nf_evopt_candidate_source') %}
          {% set status = states('sensor.se_nf_evopt_status') %}
          {% set action = states('sensor.se_nf_evopt_action_raw') %}
          {% if selected != 'EVOpt optimiert' %}
            inactive
          {% elif source == 'safety' %}
            safety_override
          {% elif source == 'evopt' %}
            none
          {% elif status in ['disabled','unavailable','invalid','schema_blocked','warming_up','action_mismatch','waiting'] %}
            {{ status }}
          {% elif not is_state('binary_sensor.se_nf_evopt_charge_control_available','on') %}
            charge_control_missing
          {% elif action in ['hold','charge'] and not is_state('binary_sensor.se_nf_evopt_discharge_control_available','on') %}
            discharge_control_missing
          {% elif action == 'charge' and not is_state('binary_sensor.se_nf_evopt_grid_charge_control_available','on') %}
            grid_charge_control_missing
          {% elif action not in ['holdcharge','normal','hold','charge'] %}
            action_unavailable
          {% else %}
            active_control_blocked
          {% endif %}
        attributes:
          status: "{{ states('sensor.se_nf_evopt_status') }}"
          health_reason: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'health_reason') }}"
          action_raw: "{{ states('sensor.se_nf_evopt_action_raw') }}"
          action_source: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_source') }}"
          suggestion_action: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_action') }}"
          slot_action: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'slot_action') }}"
          suggestion_overridden: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'suggestion_overridden') }}"
          charge_control: "{{ states('binary_sensor.se_nf_evopt_charge_control_available') }}"
          discharge_control: "{{ states('binary_sensor.se_nf_evopt_discharge_control_available') }}"
          grid_charge_control: "{{ states('binary_sensor.se_nf_evopt_grid_charge_control_available') }}"
      - name: SE NF EVOpt Shadow Reason
        unique_id: se_nf_evopt_shadow_reason
"""
text = replace_once(text, marker, fallback_code, "fallback code")
text = replace_once(
    text,
    """        state: >-
          {% set selected = states('sensor.se_nf_optimization_mode_effective') %}

          {% set source = states('sensor.se_nf_evopt_candidate_source') %}

          {% set action = states('sensor.se_nf_evopt_action_stable') %}

          {% if source == 'safety' %}
            Sicherheitsregel aktiv
          {% elif selected != 'EVOpt optimiert' %}
            EVOpt-Modus nicht gewählt
          {% elif source == 'evopt' and action == 'holdcharge' %}
            EVOpt aktiv · Laden gesperrt
          {% elif source == 'evopt' and action == 'normal' %}
            EVOpt aktiv · normaler Speicherbetrieb
          {% elif source == 'evopt' and action == 'hold' %}
            EVOpt aktiv · Entladung gesperrt
          {% elif source == 'evopt' and action == 'charge' %}
            EVOpt aktiv · Netzladung angefordert
          {% else %}
            EVOpt nicht belastbar · Netzdienlich-Fallback aktiv
          {% endif %}
""",
    """        state: >-
          {% set selected = states('sensor.se_nf_optimization_mode_effective') %}
          {% set source = states('sensor.se_nf_evopt_candidate_source') %}
          {% set action = states('sensor.se_nf_evopt_action_raw') %}
          {% set charge_block = is_state('binary_sensor.se_nf_evopt_charge_block_request', 'on') %}
          {% if source == 'safety' %}
            Sicherheitsregel aktiv
          {% elif selected != 'EVOpt optimiert' %}
            EVOpt-Modus nicht gewählt
          {% elif source == 'evopt' and action == 'holdcharge' %}
            EVOpt aktiv · Laden gesperrt
          {% elif source == 'evopt' and action == 'normal' and charge_block %}
            EVOpt aktiv · Übergang zu normal, Ladefreigabe verzögert
          {% elif source == 'evopt' and action == 'normal' %}
            EVOpt aktiv · normaler Speicherbetrieb
          {% elif source == 'evopt' and action == 'hold' %}
            EVOpt aktiv · Entladung gesperrt
          {% elif source == 'evopt' and action == 'charge' and not is_state('binary_sensor.se_nf_evopt_grid_charge_request','on') %}
            EVOpt aktiv · Netzladung wird stabilisiert
          {% elif source == 'evopt' and action == 'charge' %}
            EVOpt aktiv · Netzladung angefordert
          {% else %}
            EVOpt-Fallback {{ states('sensor.se_nf_evopt_fallback_code') }} · Netzdienlich aktiv
          {% endif %}
        attributes:
          fallback_code: "{{ states('sensor.se_nf_evopt_fallback_code') }}"
          action_raw: "{{ states('sensor.se_nf_evopt_action_raw') }}"
          action_stable: "{{ states('sensor.se_nf_evopt_action_stable') }}"
          action_source: "{{ state_attr('sensor.se_nf_evopt_adapter_raw', 'action_source') }}"
""",
    "shadow reason",
)
evopt_path.write_text(text, encoding="utf-8")

writer_path = ROOT / "package/se_controller_80_charge_writer.yaml"
writer = writer_path.read_text(encoding="utf-8")
writer = writer.replace(
    "# SolarEdge Energy Controller v0.0.1 · Einziger Charge-Limit Writer",
    "# SolarEdge HA Energy Controller v0.1.0-rc.3 · Einziger Charge-Limit Writer",
)
writer = replace_once(
    writer,
    """          - binary_sensor.se_nf_evopt_active_control
          - sensor.se_nf_evopt_action_stable
          - sensor.se_nf_active_control_label
""",
    """          - binary_sensor.se_nf_evopt_active_control
          - sensor.se_nf_evopt_action_raw
          - binary_sensor.se_nf_evopt_charge_block_request
          - sensor.se_nf_evopt_action_stable
          - sensor.se_nf_active_control_label
""",
    "writer triggers",
)
writer = replace_once(
    writer,
    """            {% set evopt_open = selected == 'EVOpt optimiert' and is_state('binary_sensor.se_nf_evopt_active_control','on') and states('sensor.se_nf_evopt_action_stable')
            in ['normal','hold','charge'] %}
""",
    """            {% set evopt_open = selected == 'EVOpt optimiert'
               and is_state('binary_sensor.se_nf_evopt_active_control','on')
               and not is_state('binary_sensor.se_nf_evopt_charge_block_request','on') %}
""",
    "writer EVOpt open",
)
writer_path.write_text(writer, encoding="utf-8")

print("RC3_EVOPT_PATCH=PASS")
