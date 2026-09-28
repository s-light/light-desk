#!/bin/sh
# One-shot setup: install this project's olad config on PocketBeagle 1.
#
# Thin wrapper around the shared ../apply-ola-config.sh: same plugin set
# (e131/uartdmx/dummy, everything else disabled) and same port-9091
# fix, just pointed at PB1's config (pb1/ola-config/, 4 universes
# instead of PB2's 5 - see memo.md's "Decision (2026-09-27): stopping
# at 4 universes for PB1"). See ../apply-ola-config.sh for what this
# actually does.
#
# Usage: sudo ./apply-ola-config.sh
# Override the config location with: sudo CONFIG_DIR=/path ./apply-ola-config.sh

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

OLA_CONFIG_SRC="$SCRIPT_DIR/ola-config" \
NUM_UNIVERSES=4 \
    exec "$SCRIPT_DIR/../apply-ola-config.sh" "$@"
