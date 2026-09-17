#!/usr/bin/env python3
"""Read the ADS7830 8-channel ADC (faders) and 6 GPIO buttons, send both to
QLC+ via OSC.

Hardware: Adafruit ADS7830 on the PocketBeagle 2's I2C1 bus (see README.md
for pinout). Each ADC channel is expected to carry one 100mm slide
potentiometer. The 6 buttons are plain momentary switches to GND on
P2.27-P2.32 (see README.md's "7x momentary buttons" section - only the
first 6 of those 7 pins are wired/used here).

Usage:
    python3 ads7830_to_osc.py --host 192.168.7.1 --port 7700

Defaults assume the board reaches the host over the USB internet-sharing
setup from pocketbeagle2-internet-sharing.md (host IP 192.168.7.1) and that
QLC+'s OSC plugin listens on its default input port for universe 1 (7700).
Each fader N (1-8) is sent as a float in [0.0, 1.0] to /fader/N; each
button N (1-6) is sent as a float, 1.0 on press and 0.0 on release, to
/button/N. Assign these addresses to VirtualConsole widgets in QLC+ via
"autodetect".

NOTE: this script opens the I2C bus directly by Linux bus number via
`adafruit_extended_bus.ExtendedI2C` rather than `board.I2C()`, since the
`adafruit_ads7830` driver only needs an I2C-like object, not `board`
itself. Use --i2c-bus to point it at the right `/dev/i2c-N` for I2C1
(P1.33/P1.36) - confirmed working on real PB2 hardware, but only after
two fixes documented in setup.md "known issues": the I2C1 pins need
`install-i2c-overlay.sh`'s pin-mux overlay (the base DTS enables the
controller but never routes its pins to the header), and the board's ID
EEPROM needs a udev permission fix for Blinka's board auto-detection
(triggered just by importing this module, regardless of --i2c-bus).

The buttons are read via `libgpiod` (the PyPI `gpiod` package, v2 API),
NOT Blinka's `board`/`digitalio` - `board.P2_27` etc. don't actually
exist: `import board` unconditionally raises `NotImplementedError: Board
not supported BEAGLEBONE_POCKETBEAGLE_2` on this board (confirmed on
real hardware; Blinka's `board` module has no `board_imports.json` entry
for this board id even though `adafruit-platformdetect` identifies it
correctly), which crashed this whole script - faders included, since the
failed import happened at module load. --button-pins takes either a
`P2.NN`-style header pin name (matched against the kernel's named gpio
lines, see `gpioinfo`) or an explicit `gpiochipN:offset` pair, and
defaults to P2.27-P2.32 per README.md.

A `P2.NN` name can resolve to lines on more than one gpiochip (seen for
P2.29 and P2.31 on real hardware) - likely alternate pinmux routes the
device tree exposes as GPIO capability regardless of which is actually
muxed in. Since which one is electrically real can only be confirmed by
pressing the physical button, this script picks the first match
(sorted by chip path) and prints a warning naming the other candidates;
use `scripts/buttons_debug_print.py` to find the right one by hand and
then pin it down with an explicit `gpiochipN:offset` override.
"""

import argparse
import glob
import time

import gpiod
from adafruit_extended_bus import ExtendedI2C
from gpiod.line import Bias, Direction, Value
from pythonosc.udp_client import SimpleUDPClient

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn

DEFAULT_HOST = "192.168.7.1"
DEFAULT_PORT = 7700
DEFAULT_I2C_BUS = 1
NUM_CHANNELS = 8
DEFAULT_BUTTON_PINS = ["P2.27", "P2.28", "P2.29", "P2.30", "P2.31", "P2.32"]
DEFAULT_BUTTON_DEBOUNCE = 3
GPIO_CONSUMER = "ads7830_to_osc"


def find_line_candidates(name):
    """Return [(chip_path, offset), ...] for every gpiochip exposing a
    line named `name` (with any parenthesized ball-name suffix stripped,
    e.g. a line named "P2.29(M22)" matches "P2.29") - normally one, see
    the ambiguity note in the module docstring."""
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


def resolve_button_pin(pin):
    if ":" in pin:
        chip, offset = pin.split(":", 1)
        return chip if chip.startswith("/dev/") else f"/dev/{chip}", int(offset)

    candidates = find_line_candidates(pin)
    if not candidates:
        raise SystemExit(f"no gpio line named {pin!r} found (check `gpioinfo` for the exact name)")
    if len(candidates) > 1:
        chosen_chip, chosen_offset = candidates[0]
        others = ", ".join(f"{c}:{o}" for c, o in candidates[1:])
        print(f"warning: button pin {pin!r} is ambiguous, matches {chosen_chip}:{chosen_offset} and {others} - "
              f"using {chosen_chip}:{chosen_offset}; confirm with buttons_debug_print.py and override with "
              f"--button-pins if that's the wrong one")
    return candidates[0]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST, help="OSC target host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="OSC target port (default: %(default)s)")
    parser.add_argument("--i2c-bus", type=int, default=DEFAULT_I2C_BUS, help="Linux I2C bus number for /dev/i2c-N carrying I2C1 (P1.33/P1.36) - verify on the board, e.g. with `i2cdetect -l` (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=0.02, help="poll interval in seconds, used for both faders and buttons (default: %(default)s)")
    parser.add_argument("--deadband", type=float, default=0.004, help="minimum fader change (0.0-1.0) before resending a channel (default: %(default)s)")
    parser.add_argument("--button-pins", default=",".join(DEFAULT_BUTTON_PINS), help="comma-separated `P2.NN` header pin names (see `gpioinfo`) or explicit `gpiochipN:offset` pairs, in order (default: %(default)s)")
    parser.add_argument("--button-debounce", type=int, default=DEFAULT_BUTTON_DEBOUNCE, help="number of consecutive identical polls required before a button state change is sent (default: %(default)s)")
    return parser.parse_args()


def setup_buttons(pin_names):
    buttons = []
    for pin in pin_names:
        chip_path, offset = resolve_button_pin(pin)
        settings = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, active_low=True)
        request = gpiod.request_lines(chip_path, consumer=GPIO_CONSUMER, config={offset: settings})
        buttons.append((request, offset))
    return buttons


def main():
    args = parse_args()

    i2c = ExtendedI2C(args.i2c_bus)
    adc = ADC.ADS7830(i2c)
    channels = [AnalogIn(adc, i) for i in range(NUM_CHANNELS)]

    button_pin_names = args.button_pins.split(",")
    buttons = setup_buttons(button_pin_names)

    client = SimpleUDPClient(args.host, args.port)
    print(f"sending faders 1-{NUM_CHANNELS} to osc://{args.host}:{args.port}/fader/N")
    print(f"sending buttons 1-{len(buttons)} to osc://{args.host}:{args.port}/button/N")

    last_values = [None] * NUM_CHANNELS
    sent_pressed = [False] * len(buttons)
    pending_pressed = [False] * len(buttons)
    pending_count = [0] * len(buttons)
    try:
        while True:
            for i, chan in enumerate(channels):
                value = chan.value / 65535
                if last_values[i] is None or abs(value - last_values[i]) >= args.deadband:
                    client.send_message(f"/fader/{i + 1}", value)
                    last_values[i] = value

            for i, (request, offset) in enumerate(buttons):
                pressed = request.get_value(offset) == Value.ACTIVE
                if pressed == pending_pressed[i]:
                    pending_count[i] += 1
                else:
                    pending_pressed[i] = pressed
                    pending_count[i] = 1
                if pending_count[i] >= args.button_debounce and pressed != sent_pressed[i]:
                    client.send_message(f"/button/{i + 1}", 1.0 if pressed else 0.0)
                    sent_pressed[i] = pressed

            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        for request, _ in buttons:
            request.release()


if __name__ == "__main__":
    main()
