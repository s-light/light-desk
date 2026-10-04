#!/usr/bin/env python3
"""First test for the Adafruit SSD1306 128x64 monochrome OLED (SPI,
PCB v2.1 - github.com/adafruit/Adafruit-128x64-Monochrome-OLED-PCB):
draws a border rectangle at the outermost pixels and one line of text
centered in the middle, then leaves it showing.

Hardware: SPI OLED, 5 control signals (CLK, DATA/MOSI, CS, DC, RST)
plus VIN/GND - see pb1/setup.md's "OLED display" section for the
wiring table. Deliberately NOT on PB1's real SPI1 bus (already
dedicated to the APA102 strip) and not bit-banged via a kernel
spi-gpio overlay either - this drives the SPI protocol entirely in
userspace, the same "go around Blinka's missing board support,
straight to libgpiod" approach this project already uses for
buttons/ADC. Needs
overlays/BB-GPIO-buttons-light-desk-00A0.dts (mux's these 5 pins into
plain GPIO output mode - U-Boot/ROM doesn't leave them there by
default, same situation as every other custom pin in this project)
installed and booted first.

NOTE on why this uses hand-rolled pin/SPI shims instead of Blinka's
own `digitalio`/`bitbangio`: checked on real hardware (Blinka 9.2.0) -
`adafruit_platformdetect` correctly identifies this SoC as AM33XX,
which routes `digitalio.DigitalInOut` through
`adafruit_blinka.microcontroller.am335x.pin`, which hard-requires the
`Adafruit_BBIO` package (a *different*, sysfs/BeagleBone-P8-P9-header-
based GPIO library this project has never used and whose pin naming
doesn't match PocketBeagle's P1/P2 headers at all). There's no
`BLINKA_FORCECHIP` value that routes to a libgpiod-based generic-Linux
backend instead for this chip family - checked
`adafruit_blinka/microcontroller_imports.json` on the board, no such
fallback entry exists. Rather than pull in Adafruit_BBIO (unverified
here, wrong pin-naming scheme, a second GPIO library alongside the
libgpiod one this whole project already uses), this implements just
the two small interfaces `adafruit_ssd1306`/`adafruit_bus_device`
actually need (a `digitalio.DigitalInOut`-like pin with
`.switch_to_output()`/`.value`, and a `busio.SPI`-like bus with
`.try_lock()`/`.unlock()`/`.configure()`/`.write()`) directly on top
of `gpiod` - the real `adafruit_ssd1306` driver (install, framebuffer,
drawing) is still used as-is, only the bottom pin/bus layer is custom.

Resolves each pin by its `P1.NN` header name via the same
gpioinfo-based lookup buttons_debug_print.py/standalone_mode_toggle.py/
rotary_encoder_test.py use, rather than hardcoding a `/dev/gpiochipN`
number - chip enumeration order is a kernel detail (PB1's own
`/dev/gpiochipN` order doesn't match the SoC's gpio0-3 bank numbers at
all, confirmed on real hardware - see pb1/memo.md).

Usage:
    python3 oled_display_test.py [--text "light-desk"]

Exits immediately after drawing - SSD1306 displays hold the last
frame in their own RAM, no continuous refresh or long-running
process needed.
"""

import argparse
import glob
import re
import sys

import gpiod
from gpiod.line import Direction, Value
import adafruit_ssd1306

WIDTH = 128
HEIGHT = 64
CONSUMER = "oled_display_test"

# role -> P1.NN header pin name (see overlays/BB-GPIO-buttons-light-desk-00A0.dts)
DEFAULT_PINS = {
    "clk": "P1.29",
    "mosi": "P1.28",
    "cs": "P1.26",
    "dc": "P1.34",
    "rst": "P1.35",
}


def find_line_candidates(name):
    """See scripts/buttons_debug_print.py for this helper - duplicated
    per-script rather than shared, same as every other GPIO-reading/
    -driving script in this project."""
    candidates = []
    for chip_path in sorted(glob.glob("/dev/gpiochip*")):
        chip = gpiod.Chip(chip_path)
        try:
            num_lines = chip.get_info().num_lines
            for offset in range(num_lines):
                line_name = chip.get_line_info(offset).name
                if line_name and re.split(r"[\[(]", line_name, maxsplit=1)[0].strip() == name:
                    candidates.append((chip_path, offset))
        finally:
            chip.close()
    return candidates


def resolve_pin(name):
    candidates = find_line_candidates(name)
    if not candidates:
        raise SystemExit(f"no gpio line named {name!r} found (check `gpioinfo` for the exact name) - "
                          "is BB-GPIO-buttons-light-desk-00A0.dtbo installed and booted?")
    return candidates[0]


class GpiodOutputPin:
    """Minimal `digitalio.DigitalInOut`-compatible output pin, backed
    directly by a gpiod line request - see module docstring for why
    this exists instead of using Blinka's digitalio."""

    def __init__(self, chip_path, offset):
        self._offset = offset
        settings = gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)
        self._request = gpiod.request_lines(chip_path, consumer=CONSUMER, config={offset: settings})

    def switch_to_output(self, value=False):
        self.value = value

    @property
    def value(self):
        return self._request.get_value(self._offset) == Value.ACTIVE

    @value.setter
    def value(self, val):
        self._request.set_value(self._offset, Value.ACTIVE if val else Value.INACTIVE)

    def release(self):
        self._request.release()


class BitbangSPI:
    """Minimal `busio.SPI`-compatible software SPI bus (mode 0, MSB
    first, write-only - all `adafruit_ssd1306` needs), clocking
    CLK/MOSI directly via two GpiodOutputPin - see module docstring
    for why this exists instead of Blinka's bitbangio."""

    def __init__(self, clk, mosi):
        self._clk = clk
        self._mosi = mosi
        self._clk.value = False

    def try_lock(self):
        return True

    def unlock(self):
        pass

    def configure(self, baudrate=0, polarity=0, phase=0):
        # Mode 0 only (what SSD1306 needs) - baudrate/polarity/phase
        # accepted for interface compatibility with adafruit_bus_device's
        # SPIDevice, not actually used: a bit-banged bus doesn't have a
        # configurable clock rate the way real hardware SPI does.
        del baudrate, polarity, phase

    def write(self, buffer):
        for byte in buffer:
            for bit_index in range(7, -1, -1):
                self._mosi.value = bool((byte >> bit_index) & 1)
                self._clk.value = True
                self._clk.value = False


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--text", default="light-desk", help="text to center on the display (default: %(default)s)")
    for role, default_pin in DEFAULT_PINS.items():
        parser.add_argument(f"--{role}-pin", default=default_pin, help=f"{role.upper()} header pin name (default: %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()

    clk = GpiodOutputPin(*resolve_pin(args.clk_pin))
    mosi = GpiodOutputPin(*resolve_pin(args.mosi_pin))
    cs = GpiodOutputPin(*resolve_pin(args.cs_pin))
    dc = GpiodOutputPin(*resolve_pin(args.dc_pin))
    rst = GpiodOutputPin(*resolve_pin(args.rst_pin))

    spi = BitbangSPI(clk, mosi)
    oled = adafruit_ssd1306.SSD1306_SPI(WIDTH, HEIGHT, spi, dc, rst, cs)

    oled.fill(0)
    oled.rect(0, 0, WIDTH, HEIGHT, 1)

    text = args.text
    text_w = len(text) * 6  # default framebuf font: 6px advance/char
    text_h = 8
    x = max(0, (WIDTH - text_w) // 2)
    y = (HEIGHT - text_h) // 2
    oled.text(text, x, y, 1)

    oled.show()
    print(f"showing {text!r} on the OLED - the display holds this frame in its own RAM, "
          "no need to keep this process running")


if __name__ == "__main__":
    sys.exit(main())
