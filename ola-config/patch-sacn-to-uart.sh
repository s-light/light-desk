#!/bin/sh
# Patch the 5 sACN (E1.31) input ports to universes 1-5, and the 5
# uartdmx output ports to the same universes 1-5, so each incoming
# sACN universe comes straight back out on its own UART/DMX line.
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
# and adjust E131_DEVICE / UARTDMX_DEVICE below if they differ - alias
# numbers are assigned in plugin-load order and have been stable in
# practice for a fixed plugin set, but are not a documented guarantee.
#
# Defaults below assume apply-ola-config.sh's plugin set (only dummy,
# e131, uartdmx enabled): dummy loads first and takes alias 1, e131
# loads before uartdmx (lower plugin ID), giving 2 and 3.

set -e

E131_DEVICE=2     # alias of the E1.31 device (has our 5 input ports)
UARTDMX_DEVICE=3  # alias of the uartdmx device (has our 5 output ports)

for i in 0 1 2 3 4; do
    universe=$((i + 1))
    ola_patch -d "$E131_DEVICE" -p "$i" -i -u "$universe"
    ola_patch -d "$UARTDMX_DEVICE" -p "$i" -u "$universe"
    echo "universe $universe: e131 in port $i -> uartdmx out port $i"
done
