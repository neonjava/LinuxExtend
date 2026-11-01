#!/usr/bin/env bash
set -e

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(dirname "$(dirname "$SCRIPT_PATH")")"
cd "$SCRIPT_DIR/server"

# Run the server module
python3 -m linuxextend "$@"
