#!/bin/sh
# Build and install the light-desk UART3 device-tree overlay
# (overlays/BB-UART3-light-desk-00A0.dts) into the running kernel's
# overlays directory.
#
# UART3 (P2.29, TXD only - no RXD is routed to any P1/P2 header pin on
# this board, confirmed against the full pinmux tables) has no stock
# BB-UART3-00A0.dtbo in bb.org-overlays, unlike uart1/uart2/uart5 - see
# the overlay source for how its pin offset was verified. TX-only is
# fine here: olad's uartdmx plugin only ever transmits.
#
# Does NOT edit /boot/uEnv.txt or reboot - run apply-uenv-overlays.sh
# after this to actually wire the overlay into boot, then reboot and
# verify with: ls -la /dev/ttyS3
#
# Usage: sudo ./install-uart3-overlay.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "must run as root, e.g.: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OVERLAY_NAME=BB-UART3-light-desk-00A0
KERNEL_VER="$(uname -r)"
OVERLAY_DIR="/boot/dtbs/$KERNEL_VER/overlays"

if [ ! -d "$OVERLAY_DIR" ]; then
    echo "overlays dir not found: $OVERLAY_DIR (unexpected kernel/image layout)" >&2
    exit 1
fi

echo "==> compiling $OVERLAY_NAME.dts"
dtc -@ -O dtb -o "/tmp/$OVERLAY_NAME.dtbo" -b 0 "$SCRIPT_DIR/overlays/$OVERLAY_NAME.dts"

echo "==> installing to $OVERLAY_DIR/"
cp "/tmp/$OVERLAY_NAME.dtbo" "$OVERLAY_DIR/$OVERLAY_NAME.dtbo"
rm -f "/tmp/$OVERLAY_NAME.dtbo"

echo "==> done: $OVERLAY_DIR/$OVERLAY_NAME.dtbo"
echo "    next: sudo ./apply-uenv-overlays.sh, then reboot"
