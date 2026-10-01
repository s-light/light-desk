#!/usr/bin/env python3
"""Send one running white dot per fader-backlight segment on an
APA102 strip via OLA, as a quick end-to-end visual test of the
olad -> SPI -> APA102 chain.

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

The strip is laid out as one 10-pixel backlight segment per fader (7
faders x 10 pixels = 70 total) - see pb1/memo.md's stand-alone-mode
notes. This test lights the *same* position in every segment at once
(e.g. position 3 lit on pixels 3, 13, 23, ..., 63 simultaneously) and
steps that shared position every interval, rather than a single dot
sweeping the whole strip - a quick way to eyeball all 7 segments'
wiring/order at once.

Usage:
    python3 apa102_running_dot_test.py [--universe 5] [--pixels 70]
        [--segment-size 10] [--pos-range 0:10] [--interval 1.0]

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
    parser.add_argument("--segment-size", type=int, default=10, help="pixels per repeating segment (one per fader) - the same position lights up in every segment at once (default: %(default)s)")
    parser.add_argument("--pos-range", default="0:10", help="start:end position-within-segment range (end exclusive) that steps (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=1.0, help="seconds per step (default: %(default)s)")
    args = parser.parse_args()

    try:
        start_str, end_str = args.pos_range.split(":", 1)
        args.pos_start, args.pos_end = int(start_str), int(end_str)
    except ValueError:
        parser.error("--pos-range must be START:END, e.g. 0:10")
    if not (0 <= args.pos_start < args.pos_end <= args.segment_size):
        parser.error(f"--pos-range {args.pos_range!r} must satisfy 0 <= start < end <= --segment-size ({args.segment_size})")
    if args.pixels % args.segment_size != 0:
        parser.error(f"--pixels ({args.pixels}) must be a whole multiple of --segment-size ({args.segment_size})")

    return args


def frame_for_position(num_pixels, segment_size, position, color):
    """Return a list of num_pixels*3 DMX values with `position` lit in
    every segment of `segment_size` pixels, everything else off."""
    frame = [0] * (num_pixels * SLOTS_PER_PIXEL)
    for segment_start in range(0, num_pixels, segment_size):
        offset = (segment_start + position) * SLOTS_PER_PIXEL
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

    num_segments = args.pixels // args.segment_size
    print(f"streaming a white dot across positions {args.pos_start}-{args.pos_end - 1} "
          f"in each of {num_segments} segments ({args.segment_size} px each, {args.pixels} px total) "
          f"on universe {args.universe}, {args.interval}s/step - Ctrl-C to stop")

    try:
        position = args.pos_start
        while True:
            send_frame(proc, frame_for_position(args.pixels, args.segment_size, position, WHITE))
            position += 1
            if position >= args.pos_end:
                position = args.pos_start
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
