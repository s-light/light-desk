#!/usr/bin/env python3
"""Read the ADS7830 8-channel ADC (faders) and send values to QLC+ via OSC.

Hardware: Adafruit ADS7830 on the PocketBeagle 2's I2C1 bus (see README.md
for pinout). Each channel is expected to carry one 100mm slide potentiometer.

Usage:
    python3 ads7830_to_osc.py --host 192.168.7.1 --port 7700

Defaults assume the board reaches the host over the USB internet-sharing
setup from pocketbeagle2-internet-sharing.md (host IP 192.168.7.1) and that
QLC+'s OSC plugin listens on its default input port for universe 1 (7700).
Each fader N (1-8) is sent as a float in [0.0, 1.0] to /fader/N; assign that
address to a VirtualConsole slider in QLC+ via "autodetect".
"""

import argparse
import time

import board
from pythonosc.udp_client import SimpleUDPClient

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn

DEFAULT_HOST = "192.168.7.1"
DEFAULT_PORT = 7700
NUM_CHANNELS = 8


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=DEFAULT_HOST, help="OSC target host (default: %(default)s)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="OSC target port (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=0.02, help="poll interval in seconds (default: %(default)s)")
    parser.add_argument("--deadband", type=float, default=0.004, help="minimum change (0.0-1.0) before resending a channel (default: %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()

    i2c = board.I2C()
    adc = ADC.ADS7830(i2c)
    channels = [AnalogIn(adc, i) for i in range(NUM_CHANNELS)]

    client = SimpleUDPClient(args.host, args.port)
    print(f"sending faders 1-{NUM_CHANNELS} to osc://{args.host}:{args.port}/fader/N")

    last_values = [None] * NUM_CHANNELS
    try:
        while True:
            for i, chan in enumerate(channels):
                value = chan.value / 65535
                if last_values[i] is None or abs(value - last_values[i]) >= args.deadband:
                    client.send_message(f"/fader/{i + 1}", value)
                    last_values[i] = value
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
