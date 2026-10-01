#!/bin/sh
# Build and install the light-desk SPI1/APA102 device-tree overlay
# (overlays/BB-SPI1-APA102-light-desk-00A0.dts) into the running
# kernel's overlays directory.
#
# Enables SPI1 (P1.33/P1.36/P2.30/P2.32) with a single spidev channel
# for one APA102 LED strip, driven by OLA's SPI plugin - see the
# overlay source for the pin choice and why a second SPI device
# shouldn't share this bus via a second chip-select.
#
# Does NOT edit /boot/uEnv.txt or reboot - run apply-uenv-overlays.sh
# after this to actually wire the overlay into boot, then reboot and
# verify with: ls -l /dev/spidev1.0
#
# Usage: sudo ./install-spi1-overlay.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "must run as root, e.g.: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OVERLAY_NAME=BB-SPI1-APA102-light-desk-00A0
KERNEL_VER="$(uname -r)"
OVERLAY_DIR="/boot/dtbs/$KERNEL_VER/overlays"

if [ ! -d "$OVERLAY_DIR" ]; then
    echo "overlays dir not found: $OVERLAY_DIR (unexpected kernel/image layout)" >&2
    exit 1
fi

TMP_DTBO="$(mktemp --suffix=.dtbo)"
trap 'rm -f "$TMP_DTBO"' EXIT

echo "==> compiling $OVERLAY_NAME.dts"
dtc -@ -O dtb -o "$TMP_DTBO" -b 0 "$SCRIPT_DIR/overlays/$OVERLAY_NAME.dts"

echo "==> installing to $OVERLAY_DIR/"
cp "$TMP_DTBO" "$OVERLAY_DIR/$OVERLAY_NAME.dtbo"

echo "==> done: $OVERLAY_DIR/$OVERLAY_NAME.dtbo"
echo "    next: sudo ./apply-uenv-overlays.sh, then reboot"
