#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS="${SE_TEST_ARTIFACTS:-$ROOT/artifacts/ha-smoke}"
HA_IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant:2026.7.3}"
PORT="${HA_TEST_PORT:-18123}"
TIMEOUT="${HA_START_TIMEOUT:-150}"
SUITE_TIMEOUT="${HA_MODE_SUITE_TIMEOUT:-75}"
TMP="$(mktemp -d)"
CONFIG="$TMP/config"
SHARE="$TMP/share"
CONTAINER="se-controller-ha-smoke-$$"
START_EPOCH="$(date +%s)"
mkdir -p "$CONFIG/packages" "$SHARE" "$ARTIFACTS"

# Wird indirekt durch den EXIT-Trap aufgerufen. Home Assistant legt im
# gemounteten Testordner Dateien als root an; deren Bereinigung darf den
# fachlich erfolgreichen Test nicht nachträglich fehlschlagen lassen.
# shellcheck disable=SC2317
cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  sudo rm -rf "$TMP" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cat > "$CONFIG/configuration.yaml" <<'YAML'
homeassistant:
  name: SolarEdge Controller Testbench
  latitude: 0
  longitude: 0
  elevation: 0
  unit_system: metric
  time_zone: Europe/Berlin
  packages: !include_dir_named packages

http:
api:
frontend:
logger:
  default: warning
  logs:
    custom_components.se_write_watchdog: info
    se_controller_testbench: warning
YAML

CONFIG_ROOT="$CONFIG" \
SHARE_ROOT="$SHARE" \
SE_CONTROLLER_DRY_RUN=1 \
HA_CHECK_COMMAND=true \
  bash "$ROOT/scripts/install_package.sh" \
  | tee "$ARTIFACTS/installer.log"

# Die Testdatei liegt außerhalb von package/ und wird vom öffentlichen Installer
# niemals ausgeliefert. Alle Mappings zeigen ausschließlich auf synthetische
# Template-Entities innerhalb dieses Containers.
cp "$ROOT/testbench/ha_runtime_package.yaml" \
  "$CONFIG/packages/se_testbench_runtime.yaml"

# Validate the exact installed configuration plus the synthetic runtime package.
docker run --rm \
  --entrypoint python \
  -v "$CONFIG:/config" \
  "$HA_IMAGE" \
  -m homeassistant --script check_config -c /config \
  2>&1 | tee "$ARTIFACTS/check-config.log"

# Runtime startup and mode-switch test. No physical integration is loaded.
docker run -d \
  --name "$CONTAINER" \
  -p "127.0.0.1:${PORT}:8123" \
  -v "$CONFIG:/config" \
  "$HA_IMAGE" >/dev/null

ready=0
for _ in $(seq 1 "$TIMEOUT"); do
  code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${PORT}/" || true)"
  if [ "$code" = "200" ] || [ "$code" = "302" ] || [ "$code" = "401" ]; then
    ready=1
    break
  fi
  sleep 1
done

if [ "$ready" -ne 1 ]; then
  docker logs "$CONTAINER" >"$ARTIFACTS/home-assistant.log" 2>&1 || true
  echo "Home Assistant did not become reachable within ${TIMEOUT}s" >&2
  tail -n 200 "$ARTIFACTS/home-assistant.log" >&2
  exit 1
fi

suite_ready=0
for _ in $(seq 1 "$SUITE_TIMEOUT"); do
  docker logs "$CONTAINER" >"$ARTIFACTS/home-assistant.log" 2>&1 || true
  if grep -q 'SE_TESTBENCH_DONE|' "$ARTIFACTS/home-assistant.log"; then
    suite_ready=1
    break
  fi
  sleep 1
done

if [ "$suite_ready" -ne 1 ]; then
  echo "Home Assistant mode-switch suite did not finish within ${SUITE_TIMEOUT}s" >&2
  tail -n 250 "$ARTIFACTS/home-assistant.log" >&2
  exit 1
fi

fatal_pattern='Invalid config|Config validation failed|Error during setup of component se_write_watchdog|Setup failed for.*se_write_watchdog'
if grep -E "$fatal_pattern" "$ARTIFACTS/home-assistant.log"; then
  echo "Fatal Home Assistant configuration/setup error found" >&2
  exit 1
fi

END_EPOCH="$(date +%s)"
python - \
  "$ARTIFACTS/report.json" \
  "$ARTIFACTS/home-assistant.log" \
  "$HA_IMAGE" \
  "$((END_EPOCH - START_EPOCH))" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

report_path = Path(sys.argv[1])
log_path = Path(sys.argv[2])
image = sys.argv[3]
duration = int(sys.argv[4])
ansi = re.compile(r"\x1b\[[0-9;]*m")
text = ansi.sub("", log_path.read_text(encoding="utf-8", errors="replace"))


def fields(payload: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in payload.strip().split("|"):
        if "=" in item:
            key, value = item.split("=", 1)
            result[key] = value
    return result


mode_rows = [
    fields(line.split("SE_TESTBENCH_MODE|", 1)[1])
    for line in text.splitlines()
    if "SE_TESTBENCH_MODE|" in line
]
done_rows = [
    fields(line.split("SE_TESTBENCH_DONE|", 1)[1])
    for line in text.splitlines()
    if "SE_TESTBENCH_DONE|" in line
]

expected_modes = [
    "Eigenverbrauch maximieren",
    "Netzdienlich laden",
    "Akku schonen",
    "EVOpt optimiert",
]
selected_modes = [row.get("selected") for row in mode_rows]
assert selected_modes == expected_modes, mode_rows
assert len(done_rows) == 1, done_rows
final = done_rows[0]
assert final.get("config") == "ok", final
assert final.get("sanity") == "ok", final
assert final.get("master") == "off", final

for row in mode_rows:
    assert row.get("effective") not in {None, "unknown", "unavailable"}, row
    assert row.get("control") not in {None, "unknown", "unavailable"}, row
    assert row.get("target") in {"0", "0.0", "5000", "5000.0"}, row
    assert row.get("actual") in {"0", "0.0", "5000", "5000.0"}, row

report = {
    "pass": True,
    "home_assistant_image": image,
    "duration_seconds": duration,
    "config_check": final["config"],
    "sanity_check": final["sanity"],
    "master_after_suite": final["master"],
    "http_ready": True,
    "modes_switched": selected_modes,
    "mode_results": mode_rows,
    "real_hardware_connected": False,
    "writer_target": "number.test_storage_charge_limit",
}
report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2, ensure_ascii=False))
PY

exit 0
