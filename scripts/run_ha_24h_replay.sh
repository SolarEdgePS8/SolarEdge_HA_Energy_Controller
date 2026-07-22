#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS="${SE_TEST_ARTIFACTS:-$ROOT/artifacts/ha-24h}"
HA_IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant:2026.7.3}"
PORT="${HA_24H_TEST_PORT:-18124}"
TIMEOUT="${HA_START_TIMEOUT:-180}"
REPLAY_TIMEOUT="${HA_24H_REPLAY_TIMEOUT:-480}"
TMP="$(mktemp -d)"
CONFIG="$TMP/config"
SHARE="$TMP/share"
CONTAINER="se-controller-ha-24h-$$"
START_EPOCH="$(date +%s)"
mkdir -p "$CONFIG/packages" "$CONFIG/custom_components" "$CONFIG/testbench" "$SHARE" "$ARTIFACTS"

# Called indirectly through the EXIT trap.
# shellcheck disable=SC2317
cleanup() {
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  sudo rm -rf "$TMP" >/dev/null 2>&1 || true
}
trap cleanup EXIT

cat > "$CONFIG/configuration.yaml" <<'YAML'
homeassistant:
  name: SolarEdge Controller 24h Replay
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
    custom_components.se_test_replay: info

se_test_replay:
  fixture: /config/testbench/real_day_2026-07-21_15m.json
  output_dir: /config/se_24h_results
YAML

# Home Assistant 2026.7 no longer exports this historical test-event constant.
# The replay uses the unchanged event name only inside the isolated container.
cat > "$CONFIG/sitecustomize.py" <<'PY'
import homeassistant.const as const

if not hasattr(const, "EVENT_TIME_CHANGED"):
    const.EVENT_TIME_CHANGED = "time_changed"
PY

CONFIG_ROOT="$CONFIG" \
SHARE_ROOT="$SHARE" \
SE_CONTROLLER_DRY_RUN=1 \
HA_CHECK_COMMAND=true \
  bash "$ROOT/scripts/install_package.sh" \
  | tee "$ARTIFACTS/installer.log"

cp "$ROOT/testbench/ha_24h_runtime_package.yaml" \
  "$CONFIG/packages/se_testbench_24h_runtime.yaml"
cp "$ROOT/testbench/fixtures/real_day_2026-07-21_15m.json" \
  "$CONFIG/testbench/real_day_2026-07-21_15m.json"
cp -a "$ROOT/testbench/custom_components/se_test_replay" \
  "$CONFIG/custom_components/se_test_replay"
# Keep simulated time safely before real entity timestamps, so freshness checks
# exercise the production formulas without being tripped by the accelerated clock.
sed -i 's/datetime(2031, 7, 21/datetime(2024, 7, 15/g' \
  "$CONFIG/custom_components/se_test_replay/__init__.py"

# Validate the exact installed main production packages plus the test-only replay.
docker run --rm \
  -e PYTHONPATH=/config \
  --entrypoint python \
  -v "$CONFIG:/config" \
  "$HA_IMAGE" \
  -m homeassistant --script check_config -c /config \
  2>&1 | tee "$ARTIFACTS/check-config.log"

docker run -d \
  -e PYTHONPATH=/config \
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
  tail -n 250 "$ARTIFACTS/home-assistant.log" >&2
  exit 1
fi

replay_done=0
for _ in $(seq 1 "$REPLAY_TIMEOUT"); do
  docker logs "$CONTAINER" >"$ARTIFACTS/home-assistant.log" 2>&1 || true
  if [ -f "$CONFIG/se_24h_results/summary.json" ] \
     && grep -q 'SE_24H_REPLAY_DONE|' "$ARTIFACTS/home-assistant.log"; then
    replay_done=1
    break
  fi
  sleep 1
done

mkdir -p "$ARTIFACTS/results"
if [ -d "$CONFIG/se_24h_results" ]; then
  cp -a "$CONFIG/se_24h_results/." "$ARTIFACTS/results/"
fi

if [ "$replay_done" -ne 1 ]; then
  echo "24h Home Assistant replay did not finish within ${REPLAY_TIMEOUT}s" >&2
  tail -n 350 "$ARTIFACTS/home-assistant.log" >&2
  exit 1
fi

fatal_pattern='Invalid config|Config validation failed|Error during setup of component se_test_replay|Setup failed for.*se_test_replay'
if grep -E "$fatal_pattern" "$ARTIFACTS/home-assistant.log"; then
  echo "Fatal Home Assistant replay setup error found" >&2
  exit 1
fi

python - "$ARTIFACTS/results/summary.json" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
report = json.loads(path.read_text(encoding="utf-8"))
assert report["pass"] is True, report
assert report["snapshots"] == 384, report
assert report["snapshots_per_mode"] == {
    "Eigenverbrauch maximieren": 96,
    "Netzdienlich laden": 96,
    "Akku schonen": 96,
    "EVOpt optimiert": 96,
}, report
assert report["hard_conflict_count"] == 0, report
assert report["unexpected_writers"] == 0, report
assert report["master_after_replay"] == "off", report
assert report["real_hardware_connected"] is False, report
assert report["writer_target"] == "number.test_storage_charge_limit", report
print(json.dumps(report, indent=2, ensure_ascii=False))
PY

END_EPOCH="$(date +%s)"
python - "$ARTIFACTS/run.json" "$HA_IMAGE" "$((END_EPOCH - START_EPOCH))" <<'PY'
from __future__ import annotations
import json
import sys
from pathlib import Path

Path(sys.argv[1]).write_text(
    json.dumps(
        {
            "pass": True,
            "home_assistant_image": sys.argv[2],
            "duration_seconds": int(sys.argv[3]),
            "fixture": "real_day_2026-07-21_15m_anonymized",
            "modes": 4,
            "snapshots": 384,
            "real_hardware_connected": False,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY

exit 0
