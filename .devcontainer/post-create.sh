#!/usr/bin/env bash
set -Eeuo pipefail
python -m pip install --disable-pip-version-check -r requirements-dev.txt
mkdir -p artifacts .testbench/config
printf '\nCodespace ready. Main commands:\n'
printf '  bash scripts/run_deep_tests.sh all\n'
printf '  bash scripts/run_ha_smoke.sh\n'
printf '  docker compose -f docker/docker-compose.test.yml up --build\n'
