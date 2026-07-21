#!/usr/bin/env bash

# Gemeinsame Laufzeitfunktionen für Home Assistant OS, Supervised,
# Container und Core. Die aufrufenden Skripte setzen CONFIG und ROOT.

ha_api_token_available() {
  [ -n "${SUPERVISOR_TOKEN:-}" ] || [ -n "${HA_TOKEN:-}" ]
}

controller_is_existing_installation() {
  compgen -G "${CONFIG}/packages/se_controller_*.yaml" >/dev/null 2>&1
}

ensure_controller_master_off() {
  if [ "${SE_CONTROLLER_DRY_RUN:-0}" = "1" ] || ha_api_token_available; then
    SE_CONTROLLER_DRY_RUN="${SE_CONTROLLER_DRY_RUN:-0}" \
      python3 "$ROOT/scripts/apply_site_config.py" --master-off-only
    return 0
  fi

  if controller_is_existing_installation; then
    if [ "${SE_CONTROLLER_MASTER_ALREADY_OFF:-}" = "YES" ]; then
      printf '%s\n' "WARN: Kein HA-API-Token verfügbar. Der Benutzer bestätigt mit SE_CONTROLLER_MASTER_ALREADY_OFF=YES, dass der Controller-Master bereits AUS ist."
      return 0
    fi
    printf '%s\n' "FEHLER: Bestehende Controller-Installation erkannt, aber kein HA-API-Token verfügbar."
    printf '%s\n' "Setze auf HA OS/Supervised SUPERVISOR_TOKEN automatisch über das Terminal-Add-on."
    printf '%s\n' "Setze auf Container/Core HA_TOKEN und HA_API_URL oder schalte den Master manuell AUS und starte mit SE_CONTROLLER_MASTER_ALREADY_OFF=YES erneut."
    return 2
  fi

  printf '%s\n' "INFO: Erstinstallation ohne vorhandene Controller-Entities. Das Ausschalten des noch nicht existierenden Masters wird übersprungen."
}

run_ha_config_check() {
  if [ -n "${HA_CHECK_COMMAND:-}" ]; then
    printf '%s\n' "INFO: Home-Assistant-Konfigurationsprüfung über HA_CHECK_COMMAND."
    bash -lc "$HA_CHECK_COMMAND"
    return $?
  fi

  if command -v ha >/dev/null 2>&1; then
    ha core check
    return $?
  fi

  if python3 -c 'import homeassistant' >/dev/null 2>&1; then
    python3 -m homeassistant --script check_config -c "$CONFIG"
    return $?
  fi

  if [ "${SE_CONTROLLER_SKIP_HA_CHECK:-}" = "YES" ]; then
    printf '%s\n' "WARN: Home-Assistant-Konfigurationsprüfung wurde ausdrücklich mit SE_CONTROLLER_SKIP_HA_CHECK=YES übersprungen."
    return 0
  fi

  printf '%s\n' "FEHLER: Keine Methode für die Home-Assistant-Konfigurationsprüfung gefunden."
  printf '%s\n' "HA OS/Supervised: Terminal-/SSH-Add-on mit 'ha' CLI verwenden."
  printf '%s\n' "Container/Core: im HA-Python-Umfeld ausführen oder HA_CHECK_COMMAND setzen."
  return 2
}
