#!/usr/bin/env bash
set -Eeuo pipefail

APP_NAME="ntc-code-map"
DEFAULT_INSTALL_DIR="${HOME}/.local/share/ntc-code-map"
INSTALL_DIR="${NTC_CODE_MAP_INSTALL_DIR:-$DEFAULT_INSTALL_DIR}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
SOURCE_PATH="${NTC_CODE_MAP_SOURCE_PATH:-}"

STATE_DIR="${XDG_STATE_HOME:-$HOME/.local/state}/ntc-code-map"
mkdir -p "$STATE_DIR"
LOG_FILE="$STATE_DIR/install-$(date +%Y%m%d-%H%M%S).log"

BOLD='\033[1m'
BLUE='\033[1;34m'
GREEN='\033[1;32m'
YELLOW='\033[1;33m'
RED='\033[1;31m'
RESET='\033[0m'

log() {
  printf "${BLUE}[ntc-code-map]${RESET} %s\n" "$*"
}

ok() {
  printf "${GREEN}[OK]${RESET} %s\n" " $*"
}

warn() {
  printf "${YELLOW}[WARN]${RESET} %s\n" " $*"
}

fail() {
  printf "${RED}[FAIL]${RESET} %s\n" " $*" >&2
  printf "Log file: %s\n" "$LOG_FILE" >&2
  exit 1
}

run_quiet() {
  local title="$1"
  shift

  log "$title"
  {
    printf "\n===== %s =====\n" "$title"
    printf "Command:"
    printf " %q" "$@"
    printf "\n\n"
    "$@"
  } >>"$LOG_FILE" 2>&1 || fail "$title failed"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

printf "${BOLD}NTC Code Map Installer${RESET}\n"
printf "Install dir : %s\n" "$INSTALL_DIR"
printf "Log file    : %s\n\n" "$LOG_FILE"

log "Checking requirements"
need_cmd "$PYTHON_BIN"
ok "$PYTHON_BIN found"

if command -v rg >/dev/null 2>&1; then
  ok "ripgrep/rg found"
else
  warn "ripgrep/rg not found. Install it for better search."
fi

if command -v ctags >/dev/null 2>&1; then
  ok "ctags found"
else
  warn "ctags not found. Symbol index will fallback to regex."
fi

mkdir -p "$INSTALL_DIR"

run_quiet "Creating virtual environment" "$PYTHON_BIN" -m venv "$INSTALL_DIR/.venv"

# shellcheck disable=SC1091
source "$INSTALL_DIR/.venv/bin/activate"

run_quiet "Upgrading pip tooling" python -m pip install --upgrade pip setuptools wheel

if [[ -n "$SOURCE_PATH" ]]; then
  run_quiet "Installing from source path: $SOURCE_PATH" python -m pip install "$SOURCE_PATH"
elif [[ -f "./pyproject.toml" && -d "./src/ntc_code_map" ]]; then
  run_quiet "Installing from current source checkout" python -m pip install .
else
  fail "No source found. Run this script from ntc-code-map repo or set NTC_CODE_MAP_SOURCE_PATH."
fi

log "Installed version"
"$INSTALL_DIR/.venv/bin/ntc-code-map" version || fail "Version check failed"

run_quiet \
  "Configuring Codex MCP" \
  "$INSTALL_DIR/.venv/bin/ntc-code-map" init-codex --command "$INSTALL_DIR/.venv/bin/ntc-code-map"

log "Doctor"
"$INSTALL_DIR/.venv/bin/ntc-code-map" doctor || warn "Doctor reported warnings"

printf "\n${GREEN}Done.${RESET}\n"
printf "Codex MCP command: %s serve\n" "$INSTALL_DIR/.venv/bin/ntc-code-map"
printf "Log file: %s\n" "$LOG_FILE"
