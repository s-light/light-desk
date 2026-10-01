#!/bin/sh
# One-shot setup: install this project's olad config on PocketBeagle 1.
#
# Wrapper around the shared ../apply-ola-config.sh: e131/uartdmx/dummy
# as usual, plus the "spi" plugin re-enabled for one APA102 output on
# a dedicated universe 5 (see pb1/ola-config/ola-spi.conf and
# ../overlays/BB-SPI1-APA102-light-desk-00A0.dts) - pointed at PB1's
# config (pb1/ola-config/), 4 DMX universes same as before (see
# memo.md's "Decision (2026-09-27): stopping at 4 universes for PB1")
# plus the 1 dedicated pixel universe. See ../apply-ola-config.sh for
# what the shared part actually does.
#
# Enabling "spi" shifts olad's device aliases: plugins load in
# ascending plugin-ID order (dummy=1, e131=11, spi=15, uartdmx=20), so
# with spi enabled the alias order becomes dummy=1, e131=2, spi=3,
# then the 4 uartdmx devices take 4-7 (not 3-6 like the plain
# e131/uartdmx/dummy set) - UARTDMX_DEVICE_START below accounts for
# that. After the shared script patches universes 1-4 -> uartdmx as
# usual, this wrapper separately patches universe 5 -> the spi device
# (ola-config/patch-spi-apa102.sh) - a different kind of patch
# (1 device/1 port, not 1 device per UART), so it isn't part of the
# shared NUM_UNIVERSES loop.
#
# Usage: sudo ./apply-ola-config.sh
# Override the config location with: sudo CONFIG_DIR=/path ./apply-ola-config.sh

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

OLA_CONFIG_SRC="$SCRIPT_DIR/ola-config" \
NUM_UNIVERSES=4 \
EXTRA_ENABLED_PLUGINS=spi \
UARTDMX_DEVICE_START=4 \
    "$SCRIPT_DIR/../apply-ola-config.sh" "$@"

echo "==> patching sACN universe 5 through to the SPI/APA102 output"
E131_DEVICE=2 SPI_DEVICE=3 SPI_UNIVERSE=5 "$SCRIPT_DIR/ola-config/patch-spi-apa102.sh"
