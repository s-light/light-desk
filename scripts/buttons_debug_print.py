#!/usr/bin/env python3
"""Continuously print all button GPIO states - for checking wiring by hand
(press a button, see which printed column flips).

Hardware: plain momentary switches to GND, read via `libgpiod` (v2 Python
bindings, package `python3-libgpiod`) with the SoC's internal pull-up
requested on each line. If that pull-up is actually honored and the
button is wired as documented, expect "high" while unpressed and "low"
while pressed - but this script prints the raw level rather than
assuming that polarity, since on a from-scratch board the pull-up
request, the pin's actual mux route, and the physical wiring are all
still unverified. Watch the column for the pin you're pressing and see
which way it actually flips. Defaults to P2.27-P2.32 per README.md's
"7x momentary buttons" section.

NOTE: this deliberately does NOT go through Blinka's `board`/`digitalio`
like ads7830_to_osc.py's button code does - `board.P2_27` etc. don't
actually exist: adafruit-platformdetect correctly identifies this board
as BEAGLEBONE_POCKETBEAGLE_2, but Blinka's `board` module (as of 9.2.0)
has no board_imports.json entry for that id, so `import board` itself
raises `NotImplementedError: Board not supported`. This script instead
resolves each `P2.NN` name directly against the kernel's named gpio
lines (visible via `gpioinfo`) and reads them through libgpiod - no
Blinka involved. ads7830_to_osc.py's button reading is broken the same
way and needs the same fix before it'll work on real hardware.

Since this only needs libgpiod (a system package, not in
scripts/requirements.txt), run it with the system python3, not
scripts/.venv - the venv doesn't have --system-site-packages and won't
see the `gpiod` module. `light`'s membership in the `gpio` group is
enough to access /dev/gpiochip*, no sudo needed.

Some P2.NN names are ambiguous - the same physical pin shows up as a
named line on more than one gpiochip (e.g. P2.29 and P2.31 here, likely
alternate pinmux routes exposed as GPIO capability regardless of which
is actually muxed in). When that happens this script reads and prints
*all* candidates for that name, suffixed with their chip/offset, so you
can press the physical button and see which column actually moves.

Usage:
    python3 buttons_debug_print.py [--button-pins P2.27,P2.28,...] [--interval 0.1]

Ctrl-C to stop.
"""

import argparse
import glob
import time

import gpiod
from gpiod.line import Bias, Direction, Value

DEFAULT_BUTTON_PINS = ["P2.27", "P2.28", "P2.29", "P2.30", "P2.31", "P2.32"]
DEFAULT_INTERVAL = 0.1
CONSUMER = "buttons_debug_print"


def find_line_candidates(name):
    """Return [(chip_path, offset), ...] for every gpiochip exposing a
    line named `name` - normally one, but see the ambiguity note above.

    Matches the line's name with any parenthesized ball-name suffix
    stripped (e.g. a line literally named "P2.29(M22)" matches "P2.29"),
    since that's how some of these header pins are labeled by the kernel
    (see `gpioinfo`)."""
    candidates = []
    for chip_path in sorted(glob.glob("/dev/gpiochip*")):
        chip = gpiod.Chip(chip_path)
        try:
            num_lines = chip.get_info().num_lines
            for offset in range(num_lines):
                line_name = chip.get_line_info(offset).name
                if line_name and line_name.split("(", 1)[0] == name:
                    candidates.append((chip_path, offset))
        finally:
            chip.close()
    return candidates


def request_line(chip_path, offset):
    settings = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP)
    return gpiod.request_lines(chip_path, consumer=CONSUMER, config={offset: settings})


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--button-pins", default=",".join(DEFAULT_BUTTON_PINS), help="comma-separated `P2.NN`-style header pin names, as shown by `gpioinfo` (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="print interval in seconds (default: %(default)s)")
    args = parser.parse_args()

    pin_names = args.button_pins.split(",")

    columns = []  # (label, request, offset)
    for name in pin_names:
        candidates = find_line_candidates(name)
        if not candidates:
            parser.error(f"no gpio line named {name!r} found (check `gpioinfo` for the exact name)")
        for chip_path, offset in candidates:
            label = name if len(candidates) == 1 else f"{name}@{chip_path.rsplit('/', 1)[-1]}:{offset}"
            request = request_line(chip_path, offset)
            columns.append((label, request, offset))

    print("  ".join(f"{label:>14}" for label, _, _ in columns))
    try:
        while True:
            values = ["high" if request.get_value(offset) == Value.ACTIVE else "low " for _, request, offset in columns]
            print("  ".join(f"{v:>14}" for v in values))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        for _, request, _ in columns:
            request.release()


if __name__ == "__main__":
    main()
