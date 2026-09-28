#!/bin/sh
# Install the apt packages this project needs on PocketBeagle 1:
#   - ola        sACN (E1.31) -> DMX daemon
#   - i2c-tools  i2cdetect/i2cget, to verify the ADS7830 fader ADC on I2C1
#
# Neither is installed by the stock am335x-debian image. This is one
# piece of the "run one setup script, everything else follows" goal for
# PB1 - see the other scripts in this folder (setup.sh,
# apply-uenv-overlays.sh, install-uart3-overlay.sh,
# switch-console-to-usb.sh) for the rest of that sequence.
#
# Idempotent - `apt-get install` is a no-op if a package is already at
# the latest available version. Safe to re-run.
#
# NOTE: this does NOT configure olad itself - run ./apply-ola-config.sh
# after this (see that script and ola-config/ in this folder) for PB1's
# own 4-universe config (ttyS1-ttyS4), not PocketBeagle 2's 5-universe
# one at the repo root.
#
# Run as your normal user (it calls sudo itself).
#
# Usage: ./install-packages.sh

set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo "run this as your normal user, not root/sudo - it calls sudo itself" >&2
    exit 1
fi

echo "==> apt-get update"
sudo apt-get update

echo "==> installing ola, i2c-tools"
sudo apt-get install -y ola i2c-tools

echo "==> done. verify with:"
echo "    i2cdetect -l"
echo "    i2cdetect -y 1"
echo "        look for the ADS7830 at 0x48-0x4b in the grid - but note:"
echo "        on this board's OMAP I2C driver, i2cdetect can silently drop"
echo "        the whole 0x40-0x4f row (blank, not even '--') instead of a"
echo "        real probe result (same issue as on PocketBeagle 2, see"
echo "        ../setup.md's 'known issues'). If that row is blank, don't"
echo "        conclude the ADS7830 is missing - check directly instead:"
echo "    i2cget -y 1 0x48"
