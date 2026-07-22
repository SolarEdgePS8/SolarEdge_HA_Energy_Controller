#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ARTIFACTS="${SE_TEST_ARTIFACTS:-$ROOT/artifacts/ha-24h}"
HA_IMAGE="${HA_IMAGE:-ghcr.io/home-assistant/home-assistant:2026.7.3}"
HA_TEST_IMAGE="se-controller-ha-faketime:${GITHUB_SHA:-local}-$$"
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
  docker image rm -f "$HA_TEST_IMAGE" >/dev/null 2>&1 || true
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
printf '2026-07-21 00:00:00\n' > "$CONFIG/faketime.txt"

# Patch only the copied test component. Production packages remain byte-identical
# to main. The patch makes the OS-level fake clock follow each replay slot and
# explicitly invokes the real session-manager and writer automations after their
# time/stability gates have elapsed.
python - "$CONFIG/custom_components/se_test_replay/__init__.py" <<'PY'
from __future__ import annotations
import sys
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text = text.replace("datetime(2031, 7, 21", "datetime(2026, 7, 21")

old_clock = '''    async def clock(self, value: datetime) -> None:
        self.now = value
        self.hass.bus.async_fire(EVENT_TIME_CHANGED, {"now": value.astimezone(UTC)})
        await self.settle()
'''
new_clock = '''    async def clock(self, value: datetime) -> None:
        self.now = value
        await asyncio.to_thread(
            Path("/config/faketime.txt").write_text,
            value.strftime("%Y-%m-%d %H:%M:%S") + "\\n",
            encoding="utf-8",
        )
        self.hass.bus.async_fire(EVENT_TIME_CHANGED, {"now": value.astimezone(UTC)})
        await self.settle()
'''
if old_clock not in text:
    raise SystemExit("clock patch anchor not found")
text = text.replace(old_clock, new_clock)

old_svc = '''    async def svc(self, domain: str, service: str, entity: str, **data: Any) -> None:
        await self.hass.services.async_call(domain, service, {"entity_id": entity, **data}, blocking=True)
        await self.settle()

    def state(self, entity: str) -> str:
'''
new_svc = '''    async def svc(self, domain: str, service: str, entity: str, **data: Any) -> None:
        await self.hass.services.async_call(domain, service, {"entity_id": entity, **data}, blocking=True)
        await self.settle()

    async def trigger_automation(self, entity: str) -> None:
        if self.hass.states.get(entity) is None:
            raise RuntimeError(f"missing production automation: {entity}")
        await self.hass.services.async_call(
            "automation",
            "trigger",
            {"entity_id": entity, "skip_condition": False},
            blocking=True,
        )
        await self.settle()

    async def refresh_controller(self) -> None:
        entities = [
            "sensor.se_controller_eigenverbrauch_next_session_state",
            "sensor.se_controller_netzdienlich_next_session_state",
            "sensor.se_controller_akku_schonen_next_session_state",
            "sensor.se_nf_optimization_mode_effective",
            "sensor.se_nf_desired_target",
            "sensor.se_nf_decision_reason",
            "sensor.se_nf_writer_mode",
        ]
        await self.hass.services.async_call(
            "homeassistant",
            "update_entity",
            {"entity_id": entities},
            blocking=True,
        )
        await self.settle()

    def state(self, entity: str) -> str:
'''
if old_svc not in text:
    raise SystemExit("service patch anchor not found")
text = text.replace(old_svc, new_svc)

old_loop = '''                    await self.clock(start)
                    await self.measurements(row)
                    for seconds in (60, 120, 180, 300):
                        await self.clock(start + timedelta(seconds=seconds))
                    snap = self.snapshot(row)
'''
new_loop = '''                    await self.clock(start)
                    await self.measurements(row)
                    await self.refresh_controller()
                    await self.trigger_automation(
                        "automation.solaredge_energy_controller_session_manager"
                    )
                    for seconds in (60, 120, 180, 300):
                        await self.clock(start + timedelta(seconds=seconds))
                        await self.refresh_controller()
                        if seconds in (120, 300):
                            await self.trigger_automation(
                                "automation.solaredge_energy_controller_session_manager"
                            )
                            await self.refresh_controller()
                            await self.trigger_automation(
                                "automation.solaredge_energy_controller_charge_limit_writer"
                            )
                    snap = self.snapshot(row)
'''
if old_loop not in text:
    raise SystemExit("replay-loop patch anchor not found")
text = text.replace(old_loop, new_loop)
path.write_text(text, encoding="utf-8")
PY

python -m py_compile "$CONFIG/custom_components/se_test_replay/__init__.py"

docker build \
  --build-arg "HA_IMAGE=$HA_IMAGE" \
  -f "$ROOT/testbench/Dockerfile.ha_faketime" \
  -t "$HA_TEST_IMAGE" \
  "$ROOT" \
  2>&1 | tee "$ARTIFACTS/faketime-image-build.log"

docker run --rm --entrypoint sh "$HA_TEST_IMAGE" -c \
  'cat /etc/os-release; readlink -f /usr/local/lib/libfaketime.so.1' \
  > "$ARTIFACTS/faketime-image-info.txt"

# Validate the exact installed main production packages plus the test-only replay.
docker run --rm \
  -e PYTHONPATH=/config \
  --entrypoint python \
  -v "$CONFIG:/config" \
  "$HA_TEST_IMAGE" \
  -m homeassistant --script check_config -c /config \
  2>&1 | tee "$ARTIFACTS/check-config.log"

docker run -d \
  -e PYTHONPATH=/config \
  -e TZ=Europe/Berlin \
  -e LD_PRELOAD=/usr/local/lib/libfaketime.so.1 \
  -e FAKETIME_TIMESTAMP_FILE=/config/faketime.txt \
  -e FAKETIME_NO_CACHE=1 \
  -e FAKETIME_DONT_FAKE_MONOTONIC=1 \
  -e FAKETIME_DONT_RESET=1 \
  -e NO_FAKE_STAT=1 \
  --name "$CONTAINER" \
  -p "127.0.0.1:${PORT}:8123" \
  -v "$CONFIG:/config" \
  "$HA_TEST_IMAGE" >/dev/null

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

python - "$ARTIFACTS/results/summary.json" "$ARTIFACTS/results/snapshots.jsonl" <<'PY'
from __future__ import annotations
from collections import defaultdict
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
snapshot_path = Path(sys.argv[2])
report = json.loads(summary_path.read_text(encoding="utf-8"))
snapshots = [json.loads(line) for line in snapshot_path.read_text(encoding="utf-8").splitlines() if line]
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
assert report["write_intents"] > 0, report
assert report["write_calls"] == report["write_intents"], report
assert report["actual_changes"] > 0, report
assert report["master_after_replay"] == "off", report
assert report["real_hardware_connected"] is False, report
assert report["writer_target"] == "number.test_storage_charge_limit", report

values: dict[str, dict[str, set[float]]] = defaultdict(lambda: {"target": set(), "actual": set()})
for row in snapshots:
    for key in ("target", "actual"):
        try:
            values[row["mode"]][key].add(float(row["controller"][key]))
        except (TypeError, ValueError):
            pass

assert 5000.0 in values["Eigenverbrauch maximieren"]["target"], values
for mode in ("Netzdienlich laden", "Akku schonen", "EVOpt optimiert"):
    assert 0.0 in values[mode]["target"], (mode, values[mode])
    assert 5000.0 in values[mode]["target"], (mode, values[mode])
for mode in report["modes"]:
    assert len(report["writes"][mode]) >= 1, (mode, report["writes"])

report["observed_values"] = {
    mode: {key: sorted(vals) for key, vals in item.items()}
    for mode, item in values.items()
}
summary_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
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
            "os_level_fake_time": True,
            "production_automations_triggered": True,
            "real_hardware_connected": False,
        },
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)
PY

exit 0
