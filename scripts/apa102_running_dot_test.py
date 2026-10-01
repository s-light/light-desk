#!/usr/bin/env python3
"""Send a single running white dot across an APA102 strip via OLA, as a
quick end-to-end visual test of the olad -> SPI -> APA102 chain.

NOTE: this does NOT use OLA's actual Python client bindings
(`ola.ClientWrapper` et al, the "python-ola"/SWIG bindings) - those
need a `python3-ola` package that isn't available on this board's
Debian 13 image (checked: no such apt package, and OLA doesn't publish
them on PyPI either - they're built from the OLA C++ source tree via
SWIG, which would mean rebuilding OLA from source just for this, see
ola-pb2-crosscompile-handoff.md's notes on how heavy that build is on
this board). Instead, this drives `ola_streaming_client` (a CLI tool
that ships with the plain `ola` apt package, already installed) as a
long-lived subprocess, writing one CSV DMX frame per line to its
stdin - confirmed on real hardware that olad applies each line
immediately and holds it (checked via the web UI's /get_dmx API).
Functionally equivalent to the real bindings for a one-way streaming
test like this.

Hardware assumed: a PB1-style single APA102 output on OLA's SPI
plugin, personality 7 (APA102_INDIVIDUAL - 3 DMX/sACN slots per pixel,
R/G/B, no separate brightness slot), patched to its own universe (see
pb1/ola-config/ola-spi.conf, pb1/ola-config/patch-spi-apa102.sh).

Usage:
    python3 apa102_running_dot_test.py [--universe 5] [--pixels 70]
        [--dot-range 0:10] [--interval 1.0]

Default strip shape is PB1's 7x10 = 70 pixels; the dot itself only
runs across the first 10 (one row) per the user's ask - override
--dot-range (start:end, end exclusive) to sweep a different section,
or set it to 0:<pixels> to sweep the whole strip.

Ctrl-C to stop (sends an all-off frame first).
"""

import argparse
import subprocess
import sys
import time

SLOTS_PER_PIXEL = 3
WHITE = (255, 255, 255)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--universe", type=int, default=5, help="OLA universe the APA102 output is patched to (default: %(default)s - PB1's dedicated pixel universe)")
    parser.add_argument("--pixels", type=int, default=70, help="total pixel count of the strip, matches ola-spi.conf's pixel-count (default: %(default)s = PB1's 7x10)")
    parser.add_argument("--dot-range", default="0:10", help="start:end pixel range (end exclusive) the dot runs across, e.g. 0:10 for just the first row (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds per step (default: %(default)s)")
    args = parser.parse_args()

    try:
        start_str, end_str = args.dot_range.split(":", 1)
        args.dot_start, args.dot_end = int(start_str), int(end_str)
    except ValueError:
        parser.error("--dot-range must be START:END, e.g. 0:10")
    if not (0 <= args.dot_start < args.dot_end <= args.pixels):
        parser.error(f"--dot-range {args.dot_range!r} must satisfy 0 <= start < end <= --pixels ({args.pixels})")

    return args


def frame_for_pixel(num_pixels, lit_pixel, color):
    """Return a list of num_pixels*3 DMX values with exactly one pixel
    set to `color`, everything else off."""
    frame = [0] * (num_pixels * SLOTS_PER_PIXEL)
    offset = lit_pixel * SLOTS_PER_PIXEL
    frame[offset:offset + SLOTS_PER_PIXEL] = color
    return frame


def send_frame(proc, frame):
    proc.stdin.write(",".join(str(v) for v in frame) + "\n")
    proc.stdin.flush()


def main():
    args = parse_args()

    proc = subprocess.Popen(
        ["ola_streaming_client", "--universe", str(args.universe)],
        stdin=subprocess.PIPE,
        text=True,
    )

    print(f"streaming a white dot across pixels {args.dot_start}-{args.dot_end - 1} "
          f"of {args.pixels} on universe {args.universe}, {args.interval}s/step - Ctrl-C to stop")

    try:
        pixel = args.dot_start
        while True:
            send_frame(proc, frame_for_pixel(args.pixels, pixel, WHITE))
            pixel += 1
            if pixel >= args.dot_end:
                pixel = args.dot_start
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        print("stopping - sending all-off frame")
        try:
            send_frame(proc, [0] * (args.pixels * SLOTS_PER_PIXEL))
        except (BrokenPipeError, OSError):
            pass
        proc.stdin.close()
        proc.wait()


if __name__ == "__main__":
    sys.exit(main())
