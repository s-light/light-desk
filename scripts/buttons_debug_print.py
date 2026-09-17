#!/usr/bin/env python3
"""Continuously print all button GPIO states - for checking wiring by hand
(press a button, see which printed column flips).

Hardware: plain momentary switches to GND, read via Blinka's
`board`/`digitalio` with an internal pull-up (same stack as
ads7830_to_osc.py), so a button reads False while pressed. Defaults to
P2.27-P2.32 per README.md's "7x momentary buttons" section.

Usage:
    python3 buttons_debug_print.py [--button-pins P2_27,P2_28,...] [--interval 0.1]

Ctrl-C to stop.
"""

import argparse
import time

import board
import digitalio

DEFAULT_BUTTON_PINS = ["P2_27", "P2_28", "P2_29", "P2_30", "P2_31", "P2_32"]
DEFAULT_INTERVAL = 0.1


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--button-pins", default=",".join(DEFAULT_BUTTON_PINS), help="comma-separated `board` module attribute names for the buttons, in order (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="print interval in seconds (default: %(default)s)")
    return parser.parse_args()


def setup_buttons(pin_names):
    buttons = []
    for name in pin_names:
        pin = getattr(board, name)
        button = digitalio.DigitalInOut(pin)
        button.direction = digitalio.Direction.INPUT
        button.pull = digitalio.Pull.UP
        buttons.append(button)
    return buttons


def main():
    args = parse_args()

    pin_names = args.button_pins.split(",")
    buttons = setup_buttons(pin_names)

    header = "  ".join(f"{name:>7}" for name in pin_names)
    print(header)
    try:
        while True:
            values = ["pressed" if not button.value else "      ." for button in buttons]
            print("  ".join(values))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
