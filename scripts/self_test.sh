#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CONFIG="$TMP/config"
SHARE="$TMP/share"
BIN="$TMP/bin"
mkdir -p "$CONFIG/packages" "$SHARE" "$BIN"
printf 'OLD\n' >"$CONFIG/packages/se_controller_00_core.yaml"
printf 'OLD\n' >"$CONFIG/se_nf_evopt_shadow_adapter.py"
cat >"$BIN/ha" <<'EOF'
#!/usr/bin/env sh
echo "FAKE ha $*"
exit 0
EOF
chmod +x "$BIN/ha"
export CONFIG_ROOT="$CONFIG"
export SHARE_ROOT="$SHARE"
export PATH="$BIN:$PATH"
export SE_CONTROLLER_DRY_RUN=1

python3 "$ROOT/audit/readonly_audit.py" "$ROOT" --release-gate
bash "$ROOT/scripts/install_package.sh"
test -f "$CONFIG/.se_controller_runtime_manifest.json"
BACKUP="$(cat "$SHARE/se_controller_last_backup.txt")"
bash "$ROOT/scripts/rollback.sh" "$BACKUP"
test "$(cat "$CONFIG/packages/se_controller_00_core.yaml")" = "OLD"
test "$(cat "$CONFIG/se_nf_evopt_shadow_adapter.py")" = "OLD"
test ! -f "$CONFIG/.se_controller_runtime_manifest.json"

DIST="$TMP/dist"
bash "$ROOT/scripts/build_release.sh" "$DIST"
test -f "$DIST/SolarEdge_HA_Energy_Controller_v0.1.0-rc.2.zip"
echo "SELF_TEST=PASS"
