#!/bin/sh
# Thin wrapper around ../scripts/buttons_debug_print.py with PB1's own
# button pins (see setup.md's "HW connections" - P2.02, P2.04, P2.06,
# P2.20, P2.22, P2.24), instead of the script's PB2-default
# --button-pins (P2.27-P2.32, which don't exist as GPIO on PB1 - see
# memo.md item 9 for why).
#
# Needs libgpiod (a system package, not scripts/requirements.txt) - see
# buttons_debug_print.py's own docstring for why this runs with the
# system python3, not scripts/.venv.
#
# Usage: ./buttons-debug-print.sh [--interval 0.1]
#   (any extra args are passed straight through to buttons_debug_print.py;
#   pass --button-pins yourself to override the PB1 default)

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PB1_BUTTON_PINS="P2.02,P2.04,P2.06,P2.20,P2.22,P2.24"

exec python3 -u "$SCRIPT_DIR/../scripts/buttons_debug_print.py" --button-pins "$PB1_BUTTON_PINS" "$@"
