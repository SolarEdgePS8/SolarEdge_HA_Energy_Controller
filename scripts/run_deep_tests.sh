#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GROUP="${1:-all}"
ARTIFACTS="${SE_TEST_ARTIFACTS:-$ROOT/artifacts}"
mkdir -p "$ARTIFACTS"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

run_static() {
  python audit/readonly_audit.py . --release-gate \
    | tee "$ARTIFACTS/readonly_audit.txt"
  python -m compileall -q audit scripts tests testbench custom_components
  python -m ruff check testbench tests/deep \
    --output-format=github \
    | tee "$ARTIFACTS/ruff.txt"
  find scripts audit tools -type f -name '*.sh' -print0 \
    | xargs -0 -r -n1 bash -n
  if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -x -f gcc \
      scripts/run_deep_tests.sh \
      scripts/run_ha_smoke.sh \
      scripts/run_ha_24h_replay.sh \
      .devcontainer/post-create.sh \
      | tee "$ARTIFACTS/shellcheck.txt"
  fi
  python -m pytest -q tests/deep/test_architecture_contracts.py \
    --junitxml="$ARTIFACTS/static-junit.xml" \
    -p no:cacheprovider
}

run_model() {
  python -m testbench.run_scenarios \
    --output "$ARTIFACTS/scenario_report.json"
  python -m testbench.day_replay \
    --fixture testbench/fixtures/real_day_2026-07-21_15m.json \
    --output-dir "$ARTIFACTS/real-day-24h-model"
  python -m pytest -q \
    tests/deep/test_scenario_matrix.py \
    tests/deep/test_cross_mode_matrix.py \
    tests/deep/test_properties.py \
    tests/deep/test_state_machine.py \
    tests/deep/test_real_day_24h.py \
    --junitxml="$ARTIFACTS/model-junit.xml" \
    --cov=testbench.reference \
    --cov-report=term-missing \
    --cov-report=xml:"$ARTIFACTS/coverage.xml" \
    --cov-report=html:"$ARTIFACTS/coverage-html" \
    --cov-fail-under=90 \
    -p no:cacheprovider
}

run_fake_evcc() {
  python -m pytest -q tests/deep/test_fake_evcc.py \
    --junitxml="$ARTIFACTS/fake-evcc-junit.xml" \
    -p no:cacheprovider
}

case "$GROUP" in
  static) run_static ;;
  model) run_model ;;
  fake-evcc) run_fake_evcc ;;
  all)
    run_static
    run_model
    run_fake_evcc
    ;;
  *)
    echo "Usage: $0 [all|static|model|fake-evcc]" >&2
    exit 2
    ;;
esac

python - "$ARTIFACTS" "$GROUP" <<'PY'
from __future__ import annotations
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(sys.argv[1])
group = sys.argv[2]
files = sorted(str(path.relative_to(root)) for path in root.rglob("*") if path.is_file())
report = {
    "group": group,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "pass": True,
    "artifacts": files,
}
(root / f"summary-{group}.json").write_text(
    json.dumps(report, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(report, indent=2))
PY
