#!/usr/bin/env python3
"""Continuously print ADS7830 channel values - for checking wiring by hand
(move a fader, see which printed column moves).

Usage:
    python3 ads7830_debug_print.py [--i2c-bus 1] [--num-channels 8] [--interval 0.25]

The ADS7830 always has 8 physical channels; --num-channels only limits
how many this script reads/prints, for boards that don't wire up all of
them (e.g. PocketBeagle 1's 7-fader build - use --num-channels 7 there).

Ctrl-C to stop.
"""

import argparse
import time

from adafruit_extended_bus import ExtendedI2C

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn

DEFAULT_I2C_BUS = 1
DEFAULT_INTERVAL = 0.25
DEFAULT_NUM_CHANNELS = 8


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--i2c-bus", type=int, default=DEFAULT_I2C_BUS, help="Linux I2C bus number for /dev/i2c-N carrying I2C1 (P1.33/P1.36) (default: %(default)s)")
    parser.add_argument("--num-channels", type=int, default=DEFAULT_NUM_CHANNELS, help="number of ADS7830 channels to read, 1-8 (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=DEFAULT_INTERVAL, help="print interval in seconds (default: %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()

    i2c = ExtendedI2C(args.i2c_bus)
    adc = ADC.ADS7830(i2c)
    channels = [AnalogIn(adc, i) for i in range(args.num_channels)]

    header = "  ".join(f"ch{i}" for i in range(args.num_channels))
    print(header)
    try:
        while True:
            values = [chan.value / 65535 for chan in channels]
            print("  ".join(f"{v:.3f}" for v in values))
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
