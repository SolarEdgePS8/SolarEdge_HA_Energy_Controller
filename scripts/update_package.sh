#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/install_package.sh"
echo "Update-Dateien installiert. Nach Neustart bleibt der Controller-Master AUS."
