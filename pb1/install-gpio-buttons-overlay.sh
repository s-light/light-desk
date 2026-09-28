#!/bin/sh
# Build and install the light-desk button-GPIO device-tree overlay
# (overlays/BB-GPIO-buttons-light-desk-00A0.dts) into the running
# kernel's overlays directory.
#
# Activates internal pull-up input mode (PIN_INPUT_PULLUP, MUX_MODE7)
# for the 6 button pins (P2.02, P2.04, P2.06, P2.22, P2.24, P2.33) -
# see the overlay source for why this needs an overlay at all
# (libgpiod's runtime bias request does nothing on this board/kernel;
# the pull has to be the static boot-time pinmux value instead).
#
# Does NOT edit /boot/uEnv.txt or reboot - run apply-uenv-overlays.sh
# after this to actually wire the overlay into boot, then reboot and
# verify with: gpioget -b pull-up P2.02 P2.04 P2.06 P2.22 P2.24 P2.33
# (or scripts/buttons_debug_print.py --button-pins
# P2.02,P2.04,P2.06,P2.22,P2.24,P2.33) - all should read "high"/inactive
# with nothing wired, and pull low when a button is pressed once wired.
#
# Usage: sudo ./install-gpio-buttons-overlay.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "must run as root, e.g.: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OVERLAY_NAME=BB-GPIO-buttons-light-desk-00A0
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
