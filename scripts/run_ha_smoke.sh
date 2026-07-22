#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS="${SE_TEST_ARTIFACTS:-$ROOT/artifacts/ha-smoke}"
HA_IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant:2026.7.3}"
PORT="${HA_TEST_PORT:-18123}"
TIMEOUT="${HA_START_TIMEOUT:-150}"
TMP="$(mktemp -d)"
CONFIG="$TMP/config"
SHARE="$TMP/share"
CONTAINER="se-controller-ha-smoke-$$"
START_EPOCH="$(date +%s)"
mkdir -p "$CONFIG/packages" "$SHARE" "$ARTIFACTS"

# Wird indirekt durch den EXIT-Trap aufgerufen.
# shellcheck disable=SC2317
cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  rm -rf "$TMP"
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
YAML

CONFIG_ROOT="$CONFIG" \
SHARE_ROOT="$SHARE" \
SE_CONTROLLER_DRY_RUN=1 \
HA_CHECK_COMMAND=true \
  bash "$ROOT/scripts/install_package.sh" \
  | tee "$ARTIFACTS/installer.log"

# Validate the same files with a pinned Home Assistant image.
docker run --rm \
  --entrypoint python \
  -v "$CONFIG:/config" \
  "$HA_IMAGE" \
  -m homeassistant --script check_config -c /config \
  2>&1 | tee "$ARTIFACTS/check-config.log"

# Runtime startup smoke test. The synthetic configuration never maps a real writer.
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

docker logs "$CONTAINER" >"$ARTIFACTS/home-assistant.log" 2>&1 || true
if [ "$ready" -ne 1 ]; then
  echo "Home Assistant did not become reachable within ${TIMEOUT}s" >&2
  tail -n 200 "$ARTIFACTS/home-assistant.log" >&2
  exit 1
fi

fatal_pattern='Invalid config|Config validation failed|Error during setup of component se_write_watchdog|Setup failed for.*se_write_watchdog'
if grep -E "$fatal_pattern" "$ARTIFACTS/home-assistant.log"; then
  echo "Fatal Home Assistant configuration/setup error found" >&2
  exit 1
fi

END_EPOCH="$(date +%s)"
python - "$ARTIFACTS/report.json" "$HA_IMAGE" "$((END_EPOCH - START_EPOCH))" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
report = {
    "pass": True,
    "home_assistant_image": sys.argv[2],
    "startup_seconds": int(sys.argv[3]),
    "config_check": "PASS",
    "http_ready": True,
    "real_hardware_connected": False,
    "writer_targets": "synthetic/unmapped only",
}
path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, indent=2))
PY

# Verhindert, dass ein vorangegangener absichtlich negativer grep-Status den
# erfolgreichen Smoke-Test als Shell-Fehler nach außen trägt.
exit 0
