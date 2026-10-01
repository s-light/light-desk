#!/bin/sh
# Patch the N sACN (E1.31) input ports to universes 1-N, and each of the
# N uartdmx output devices to the same universes 1-N, so each incoming
# sACN universe comes straight back out on its own UART/DMX line.
#
# N = NUM_UNIVERSES (default 5, PocketBeagle 2). PocketBeagle 1 uses 4 -
# pb1/apply-ola-config.sh sets that; it must match both input_ports in
# ola-e131.conf and the number of "device =" lines in ola-uartdmx.conf.
#
# e131 is ONE OLA device with N input ports (port i -> universe i+1).
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
# loads next (alias 2), then the N uartdmx devices take 3..N+2 in the
# order listed in ola-uartdmx.conf.

set -e

NUM_UNIVERSES="${NUM_UNIVERSES:-5}"
E131_DEVICE="${E131_DEVICE:-2}"          # alias of the E1.31 device (has our N input ports)
UARTDMX_DEVICE_START="${UARTDMX_DEVICE_START:-3}" # alias of the first uartdmx device (ttyS1); each
                        # of the N uartdmx devices takes the next alias -
                        # override if another plugin (e.g. PB1's "spi",
                        # see pb1/apply-ola-config.sh) loads between e131
                        # and uartdmx and shifts this

i=0
while [ "$i" -lt "$NUM_UNIVERSES" ]; do
    universe=$((i + 1))
    uartdmx_device=$((UARTDMX_DEVICE_START + i))
    ola_patch -d "$E131_DEVICE" -p "$i" -i -u "$universe"
    ola_patch -d "$uartdmx_device" -p 0 -u "$universe"
    echo "universe $universe: e131 in port $i -> uartdmx device $uartdmx_device port 0"
    i=$((i + 1))
done
