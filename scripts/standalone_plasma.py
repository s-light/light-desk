#!/usr/bin/env python3
"""Stand-alone mode, "hsv-pixel-strip": a self-contained 1D plasma
effect driven by the fader ADC, needing no computer/sACN source - see
`stand alone mode.md` and pb1/memo.md item 15.

Fader mapping (per `stand alone mode.md`):
    fader 0: hue
    fader 1: saturation
    fader 2: value (brightness, before the master dimmer below)
    fader 3: not used
    fader 4: effect speed
    fader 5: color-window width
    fader 6: master dimmer

Effect (this script's concrete, simple-as-possible first-pass take on
"1d plasma" - the write-up was intentionally open-ended, so treat the
exact formula below as a starting point, not a spec): a single
traveling sine wave in hue space across the strip. At each pixel x
(0..dmx-pixels-1) and time t:

    wave = sin(2*pi * x/dmx_pixels + t * speed)   # -1..1
    hue  = (fader0_hue + wave * 0.5 * fader5_window) % 1.0
    rgb  = hsv_to_rgb(hue, fader1_sat, fader2_val * fader6_dimmer)

fader5 (window) = 0 gives a flat, non-animated solid color (no hue
variation to animate); turning it up spreads hue across the strip and
makes the sine wave's motion visible as a shifting rainbow-ish band.
fader4 (speed) scales how fast that wave travels - 0 freezes it.

Also drives the fader-backlight APA102 strip (default universe 5,
segment-size 10, one segment per fader - see pb1/setup.md's "APA102
output" section) as a simple visualization: each of the first 3
segments (hue/sat/val) shows a bar (pixel count = fader value * 10)
filled with the *resulting* HSV color, so all three agree and you see
what you're dialing in; segment 3 (unused fader) stays off; segments
4-6 (speed/window/dimmer) show a plain white bar proportional to
their fader's value.

NOTE: like scripts/apa102_running_dot_test.py, this does NOT use OLA's
actual Python client bindings (not available on this board's Debian
image, see that script's docstring for why) - it drives two
long-lived `ola_streaming_client` subprocesses instead (one per
universe), each fed one CSV DMX frame per stdin line.

NOTE: reads the ADS7830 directly via the same adafruit_extended_bus/
adafruit_ads7830 path as ads7830_to_osc.py, independently of that
script/service - concurrent reads of the same ADC from two separate
processes are fine (the kernel's I2C driver arbitrates per-transaction,
not per-process), so this can run at the same time as the normal
control-desk OSC bridge without conflict. It does NOT touch any GPIO/
button lines at all, so it also doesn't conflict with
ads7830_to_osc.py's or standalone_mode_toggle.py's button reads.

Usage:
    python3 standalone_plasma.py [--i2c-bus 1]
        [--backlight-universe 5] [--backlight-pixels 70] [--segment-size 10]
        [--dmx-universe 1] [--dmx-pixels 160]
        [--interval 0.03]

Ctrl-C to stop (sends all-off frames to both universes first).
"""

import argparse
import colorsys
import math
import subprocess
import sys
import time

from adafruit_extended_bus import ExtendedI2C

import adafruit_ads7830.ads7830 as ADC
from adafruit_ads7830.analog_in import AnalogIn

SLOTS_PER_PIXEL = 3
NUM_FADERS = 7
WHITE = (255, 255, 255)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--i2c-bus", type=int, default=1, help="Linux I2C bus number for /dev/i2c-N carrying I2C1 (default: %(default)s)")
    parser.add_argument("--backlight-universe", type=int, default=5, help="OLA universe the APA102 fader-backlight is patched to (default: %(default)s)")
    parser.add_argument("--backlight-pixels", type=int, default=70, help="total backlight pixel count (default: %(default)s = 7x10)")
    parser.add_argument("--segment-size", type=int, default=10, help="backlight pixels per fader segment (default: %(default)s)")
    parser.add_argument("--dmx-universe", type=int, default=1, help="OLA universe the 1d effect strip is sent to - in stand-alone mode nothing else should be sACN-sourcing this universe, but that's left to the user to ensure (default: %(default)s)")
    parser.add_argument("--dmx-pixels", type=int, default=160, help="pixel count of the effect strip (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=0.03, help="seconds per animation step (default: %(default)s, ~33 steps/sec)")
    return parser.parse_args()


def read_faders(channels):
    return [chan.value / 65535 for chan in channels]


def hsv_to_rgb255(h, s, v):
    r, g, b = colorsys.hsv_to_rgb(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v)))
    return (round(r * 255), round(g * 255), round(b * 255))


def plasma_frame(num_pixels, t, hue, sat, val, speed, window):
    frame = [0] * (num_pixels * SLOTS_PER_PIXEL)
    for x in range(num_pixels):
        wave = math.sin(2 * math.pi * x / num_pixels + t * speed)
        pixel_hue = hue + wave * 0.5 * window
        r, g, b = hsv_to_rgb255(pixel_hue, sat, val)
        offset = x * SLOTS_PER_PIXEL
        frame[offset:offset + 3] = (r, g, b)
    return frame


def backlight_frame(num_pixels, segment_size, faders, color):
    """One bar per fader segment, length = fader value * segment_size,
    color `color` for faders 0-2 (overridden by the caller with the
    live HSV color) and white for faders 4-6; fader 3's segment stays
    off."""
    frame = [0] * (num_pixels * SLOTS_PER_PIXEL)
    num_segments = num_pixels // segment_size
    for segment, fader_value in enumerate(faders[:num_segments]):
        if segment == 3:
            continue
        bar_color = color if segment < 3 else WHITE
        lit = round(max(0.0, min(1.0, fader_value)) * segment_size)
        for i in range(lit):
            offset = (segment * segment_size + i) * SLOTS_PER_PIXEL
            frame[offset:offset + 3] = bar_color
    return frame


def start_streaming_client(universe):
    return subprocess.Popen(
        ["ola_streaming_client", "--universe", str(universe)],
        stdin=subprocess.PIPE,
        text=True,
    )


def send_frame(proc, frame):
    proc.stdin.write(",".join(str(v) for v in frame) + "\n")
    proc.stdin.flush()


def main():
    args = parse_args()

    i2c = ExtendedI2C(args.i2c_bus)
    adc = ADC.ADS7830(i2c)
    channels = [AnalogIn(adc, i) for i in range(NUM_FADERS)]

    dmx_proc = start_streaming_client(args.dmx_universe)
    backlight_proc = start_streaming_client(args.backlight_universe)

    print(f"stand-alone hsv-pixel-strip: {args.dmx_pixels}px effect on universe {args.dmx_universe}, "
          f"{args.backlight_pixels}px backlight on universe {args.backlight_universe}, "
          f"{args.interval}s/step - Ctrl-C to stop")

    start = time.monotonic()
    try:
        while True:
            t = time.monotonic() - start
            faders = read_faders(channels)
            hue, sat, val = faders[0], faders[1], faders[2]
            speed = faders[4] * 4 * math.pi   # 0 .. 2 full cycles/sec
            window = faders[5]
            dimmer = faders[6]

            send_frame(dmx_proc, plasma_frame(args.dmx_pixels, t, hue, sat, val * dimmer, speed, window))

            live_color = hsv_to_rgb255(hue, sat, val * dimmer)
            send_frame(backlight_proc, backlight_frame(args.backlight_pixels, args.segment_size, faders, live_color))

            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        print("stopping - sending all-off frames")
        for proc, pixels in ((dmx_proc, args.dmx_pixels), (backlight_proc, args.backlight_pixels)):
            try:
                send_frame(proc, [0] * (pixels * SLOTS_PER_PIXEL))
            except (BrokenPipeError, OSError):
                pass
            proc.stdin.close()
            proc.wait()


if __name__ == "__main__":
    sys.exit(main())
