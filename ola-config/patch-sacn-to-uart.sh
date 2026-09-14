#!/bin/sh
# Patch the 5 sACN (E1.31) input ports to universes 1-5, and each of the
# 5 uartdmx output devices to the same universes 1-5, so each incoming
# sACN universe comes straight back out on its own UART/DMX line.
#
# e131 is ONE OLA device with 5 input ports (port i -> universe i+1).
# uartdmx is different: olad creates one SEPARATE device per successfully
# opened UART, each with a single port 0 - not one device with 5 ports.
# Confirmed via `ola_dev_info` after the overlay in ../overlays was
# installed: devices come up in ola-uartdmx.conf's "device = " line order
# (ttyS1, ttyS3, ttyS4, ttyS5, ttyS7), each with just port 0.
#
# olad's port "patching" (which port belongs to which universe) is
# runtime state, not something safely hardcoded in the plugin .conf
# files (device aliases are assigned by olad when it starts and depend
# on plugin load order) - see:
# https://www.openlighting.org/ola/advanced-topics/patch-persistency/
# It IS persisted to $CONFIG_DIR/ola-port.conf + ola-universe.conf on a
# clean olad shutdown, so you normally only need to run this once after
# a fresh install; re-run it any time a config file gets reset.
#
# Requires olad to be running (ola-e131.conf / ola-uartdmx.conf already
# installed, both plugins enabled).
#
# Before running: find the actual device aliases olad assigned with
#   ola_dev_info
# and adjust E131_DEVICE / UARTDMX_DEVICE_START below if they differ -
# alias numbers are assigned in plugin-load order and have been stable
# in practice for a fixed plugin set, but are not a documented guarantee.
#
# Defaults below assume apply-ola-config.sh's plugin set (only dummy,
# e131, uartdmx enabled): dummy loads first and takes alias 1, e131
# loads next (alias 2), then the 5 uartdmx devices take 3-7 in the
# order listed above.

set -e

E131_DEVICE=2          # alias of the E1.31 device (has our 5 input ports)
UARTDMX_DEVICE_START=3 # alias of the first uartdmx device (ttyS1); each
                        # of the 5 uartdmx devices takes the next alias

for i in 0 1 2 3 4; do
    universe=$((i + 1))
    uartdmx_device=$((UARTDMX_DEVICE_START + i))
    ola_patch -d "$E131_DEVICE" -p "$i" -i -u "$universe"
    ola_patch -d "$uartdmx_device" -p 0 -u "$universe"
    echo "universe $universe: e131 in port $i -> uartdmx device $uartdmx_device port 0"
done
