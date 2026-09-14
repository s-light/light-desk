#!/bin/sh
# One-shot setup: install this project's olad config on the board.
#
# Leaves only 3 plugins active:
#   e131    - sACN input   (6 universes, see ola-config/ola-e131.conf)
#   uartdmx - DMX output over UART (6 devices, see ola-config/ola-uartdmx.conf)
#   dummy   - a virtual universe, handy for testing (e.g. via the olad web
#             UI) before any real sACN source or DMX fixture is wired up
#
# Every other plugin olad ships gets an explicit "enabled = false" stub, so
# a fresh olad on the board never scans for USB/network hardware that isn't
# part of this project. Re-running this script is safe (idempotent) - use
# it whenever CONFIG_DIR needs to be reset to the project's known-good state.
#
# Usage: sudo ./apply-ola-config.sh
# Override the config location with: sudo CONFIG_DIR=/path ./apply-ola-config.sh

set -eu

CONFIG_DIR="${CONFIG_DIR:-/etc/ola}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "must run as root, e.g.: sudo $0" >&2
    exit 1
fi

echo "==> config dir: $CONFIG_DIR"
mkdir -p "$CONFIG_DIR"

# Every plugin olad ships, minus e131/uartdmx/dummy (handled below).
# Source of truth: https://docs.openlighting.org/ola/conf/
DISABLED_PLUGINS="
artnet
dmx4linux
espnet
ftdidmx
gpio
karate
kinet
milinst
nanoleaf
opendmx
openpixelcontrol
osc
pathport
renard
sandnet
shownet
spi
spidmx
stageprofi
usbdmx
usbserial
"

count=0
for plugin in $DISABLED_PLUGINS; do
    printf 'enabled = false\n' > "$CONFIG_DIR/ola-$plugin.conf"
    count=$((count + 1))
done
echo "==> disabled $count unused plugins"

cp "$SCRIPT_DIR/ola-config/ola-e131.conf" "$CONFIG_DIR/ola-e131.conf"
cp "$SCRIPT_DIR/ola-config/ola-uartdmx.conf" "$CONFIG_DIR/ola-uartdmx.conf"
printf 'enabled = true\n' > "$CONFIG_DIR/ola-dummy.conf"
echo "==> installed ola-e131.conf, ola-uartdmx.conf, ola-dummy.conf"

if id olad >/dev/null 2>&1; then
    chown -R olad:olad "$CONFIG_DIR" 2>/dev/null || true
fi

if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files olad.service >/dev/null 2>&1; then
    echo "==> restarting olad.service"
    systemctl restart olad.service
    sleep 2
else
    echo "!! olad.service not installed (see ../olad.service) - start olad manually, then run:" >&2
    echo "     $SCRIPT_DIR/ola-config/patch-sacn-to-uart.sh" >&2
    exit 0
fi

echo "==> patching sACN universes 1-6 through to their UART outputs"
if ! "$SCRIPT_DIR/ola-config/patch-sacn-to-uart.sh"; then
    echo "!! patching failed - check the device aliases with 'ola_dev_info' and" >&2
    echo "   adjust E131_DEVICE/UARTDMX_DEVICE in ola-config/patch-sacn-to-uart.sh" >&2
    exit 1
fi

echo "==> done. verify with:"
echo "    ola_plugin_info"
echo "    ola_universe_info"
