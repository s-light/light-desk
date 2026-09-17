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

The buttons are read via Blinka's `board`/`digitalio` (same stack as the
ADC, no libgpiod dependency needed) with an internal pull-up, so a button
reads False while pressed. --button-pins names the board module attributes
to use and defaults to P2.27-P2.32 per README.md; override if Blinka's
PocketBeagle 2 pin names differ on your image. Unverified on real
hardware - confirm the pin names exist (`python3 -c "import board;
print(board.P2_27)"`) and that press/release is reported correctly before
relying on it.
"""

import argparse
import time

import board
import digitalio
from adafruit_extended_bus import ExtendedI2C
from pythonosc.udp_client import SimpleUDPClient

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn

DEFAULT_HOST = "192.168.7.1"
DEFAULT_PORT = 7700
DEFAULT_I2C_BUS = 1
NUM_CHANNELS = 8
DEFAULT_BUTTON_PINS = ["P2_27", "P2_28", "P2_29", "P2_30", "P2_31", "P2_32"]
DEFAULT_BUTTON_DEBOUNCE = 3


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST, help="OSC target host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="OSC target port (default: %(default)s)")
    parser.add_argument("--i2c-bus", type=int, default=DEFAULT_I2C_BUS, help="Linux I2C bus number for /dev/i2c-N carrying I2C1 (P1.33/P1.36) - verify on the board, e.g. with `i2cdetect -l` (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=0.02, help="poll interval in seconds, used for both faders and buttons (default: %(default)s)")
    parser.add_argument("--deadband", type=float, default=0.004, help="minimum fader change (0.0-1.0) before resending a channel (default: %(default)s)")
    parser.add_argument("--button-pins", default=",".join(DEFAULT_BUTTON_PINS), help="comma-separated `board` module attribute names for the 6 buttons, in order (default: %(default)s)")
    parser.add_argument("--button-debounce", type=int, default=DEFAULT_BUTTON_DEBOUNCE, help="number of consecutive identical polls required before a button state change is sent (default: %(default)s)")
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

            for i, button in enumerate(buttons):
                pressed = not button.value
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


if __name__ == "__main__":
    main()
