#!/bin/sh
# Patch sACN universe 5 (the dedicated APA102 universe, see
# ola-e131.conf's input_ports=5) to the SPI device's port 0.
#
# Run after ../../ola-config/patch-sacn-to-uart.sh (which only handles
# universes 1-4 -> uartdmx, NUM_UNIVERSES=4 on PB1) - this covers the
# 5th input port separately since the SPI device is a different kind
# of thing entirely (one pixel-strip port, not one port per universe
# like e131, and not one device per UART like uartdmx).
#
# Requires olad running with the "spi" plugin enabled (see
# ../apply-ola-config.sh) and the BB-SPI1-APA102-light-desk-00A0.dtbo
# overlay installed+booted (/dev/spidev1.0 present).
#
# Before running: find the actual device aliases with `ola_dev_info`
# and adjust E131_DEVICE/SPI_DEVICE below if they differ - see
# ../../ola-config/patch-sacn-to-uart.sh's own note on why these
# aren't a documented guarantee. Expected with PB1's plugin set
# (dummy, e131, spi, uartdmx, in that plugin-ID order): dummy=1,
# e131=2, spi=3, then the 4 uartdmx devices take 4-7.

set -e

E131_DEVICE="${E131_DEVICE:-2}"
SPI_DEVICE="${SPI_DEVICE:-3}"
SPI_UNIVERSE="${SPI_UNIVERSE:-5}"

e131_port=$((SPI_UNIVERSE - 1))

ola_patch -d "$E131_DEVICE" -p "$e131_port" -i -u "$SPI_UNIVERSE"
ola_patch -d "$SPI_DEVICE" -p 0 -u "$SPI_UNIVERSE"
echo "universe $SPI_UNIVERSE: e131 in port $e131_port -> spi device $SPI_DEVICE port 0"
