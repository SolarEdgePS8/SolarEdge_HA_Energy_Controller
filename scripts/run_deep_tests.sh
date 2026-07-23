#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
GROUP="${1:-all}"
ARTIFACTS="${SE_TEST_ARTIFACTS:-$ROOT/artifacts}"
mkdir -p "$ARTIFACTS"
cd "$ROOT"
export PYTHONPATH="$ROOT${PYTHONPATH:+:$PYTHONPATH}"

explain_group() {
  case "$1" in
    static)
      cat <<'EOF'

=== EINFACHE ERKLÄRUNG: DATEI- UND ARCHITEKTURTEST ===
Dieser Test prüft, ob YAML, Python, Shell-Skripte, Datenschutzregeln und die
Single-Writer-Architektur grundsätzlich korrekt aufgebaut sind.
GRÜN bedeutet: Die Dateien sind lesbar und die Sicherheitsverträge passen.
ROT bedeutet: Eine konkrete Datei oder Regel ist fehlerhaft; der Release bleibt gesperrt.
EOF
      ;;
    model)
      cat <<'EOF'

=== EINFACHE ERKLÄRUNG: STEUERUNGS- UND GRENZFALLTEST ===
Dieser Test rechnet viele normale und absichtlich problematische Situationen durch.
Dazu gehört jetzt ausdrücklich der echte Fehler vom 23.07.2026:
EVOpt meldet holdcharge, der Charge-Block ist an, gleichzeitig versucht Fail-open 5000 W.
GRÜN bedeutet: Kein solcher permissiver Schreibzugriff ist möglich.
ROT bedeutet: Die Steuerlogik könnte den SolarEdge-Wert falsch öffnen.
EOF
      ;;
    fake-evcc)
      cat <<'EOF'

=== EINFACHE ERKLÄRUNG: EVCC-/EVOPT-SCHNITTSTELLENTEST ===
Dieser Test ersetzt evcc durch einen kontrollierten Testserver und liefert normale,
fehlerhafte und unvollständige Antworten.
GRÜN bedeutet: Der Controller reagiert auf diese Antworten wie vorgesehen.
ROT bedeutet: Eine evcc-Antwort kann zu einer falschen Steuerentscheidung führen.
EOF
      ;;
  esac
}

run_static() {
  explain_group static
  python audit/readonly_audit.py . --release-gate \
    | tee "$ARTIFACTS/readonly_audit.txt"
  python -m compileall -q audit scripts tests testbench custom_components
  python -m ruff check testbench tests/deep scripts/export_fixture.py scripts/privacy_scan.py \
    --output-format=github \
    | tee "$ARTIFACTS/ruff.txt"
  find scripts audit tools -type f -name '*.sh' -print0 \
    | xargs -0 -r -n1 bash -n
  if command -v shellcheck >/dev/null 2>&1; then
    shellcheck -x -f gcc \
      scripts/run_deep_tests.sh \
      scripts/run_ha_smoke.sh \
      scripts/run_ha_24h_replay.sh \
      scripts/collect_failure_bundle.sh \
      .devcontainer/post-create.sh \
      | tee "$ARTIFACTS/shellcheck.txt"
  fi
  python scripts/privacy_scan.py --self-test \
    testbench/fixtures \
    --report "$ARTIFACTS/privacy-report.json"
  python -m pytest -q \
    tests/deep/test_architecture_contracts.py \
    tests/deep/test_fixture_contracts.py \
    tests/deep/test_ha_24h_patch_contracts.py \
    --junitxml="$ARTIFACTS/static-junit.xml" \
    -p no:cacheprovider
}

run_model() {
  explain_group model
  python -m testbench.run_scenarios \
    --output "$ARTIFACTS/scenario_report.json"
  python -m testbench.day_replay \
    --fixture testbench/fixtures/real_day_2026-07-21_15m.json \
    --output-dir "$ARTIFACTS/real-day-24h-model"
  python -m testbench.day_replay \
    --fixture testbench/fixtures/daily_balance_calibrated_example_15m.json \
    --output-dir "$ARTIFACTS/calibrated-day-24h-model"
  python -m pytest -q \
    tests/deep/test_scenario_matrix.py \
    tests/deep/test_cross_mode_matrix.py \
    tests/deep/test_properties.py \
    tests/deep/test_state_machine.py \
    tests/deep/test_real_day_24h.py \
    tests/deep/test_fixture_contracts.py \
    tests/deep/test_writer_policy.py \
    tests/deep/test_writer_template_regression.py \
    --junitxml="$ARTIFACTS/model-junit.xml" \
    --cov=testbench.reference \
    --cov-report=term-missing \
    --cov-report=xml:"$ARTIFACTS/coverage.xml" \
    --cov-report=html:"$ARTIFACTS/coverage-html" \
    --cov-fail-under=90 \
    -p no:cacheprovider
}

run_fake_evcc() {
  explain_group fake-evcc
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
