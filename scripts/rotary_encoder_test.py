#!/usr/bin/env python3
"""Print a running counter that increases/decreases as the rotary
encoder (pb1/overlays/BB-ROTARY-ENCODER-light-desk-00A0.dts, eQEP0 -
see pb1/memo.md item 16) turns, plus a `*` while its push button is
held - a wiring/direction check before this becomes display menu
navigation later.

Reads the eQEP0 hardware quadrature counter via Linux's generic
"Counter" subsystem sysfs ABI (`/sys/bus/counter/devices/counterN/`),
not GPIO - the overlay enables the real decoder peripheral, so the
kernel already does the quadrature decoding; this script just reads
its running count. Auto-discovers which `counterN` is eqep0 (don't
assume the index) via each device's `name` file.

NOTE: not yet confirmed against the real sysfs layout on booted
hardware (this is new as of the same session that added the overlay,
before its first reboot) - the exact attribute names below
(`count0/count`, `count0/function`, `count0/functions_available`)
are the Linux Counter subsystem's documented ABI for the `ti-eqep`
driver as of recent kernels, but double-check with
`find /sys/bus/counter/devices/ -maxdepth 3` if this errors.

The hardware counter register is a free-running unsigned value that
wraps at 2**32 in both directions (no "ceiling" is configured here) -
this script unwraps that into a plain signed running total starting
at 0 when it starts, by watching for large jumps near the wrap
boundary between polls.

Usage:
    python3 rotary_encoder_test.py [--button-pin P2.19] [--interval 0.05]

Ctrl-C to stop.
"""

import argparse
import glob
import re
import sys
import time
from pathlib import Path

import gpiod
from gpiod.line import Bias, Direction, Value

COUNTER_SYSFS_ROOT = Path("/sys/bus/counter/devices")
WRAP = 2 ** 32
CONSUMER = "rotary_encoder_test"


def find_eqep_count_path():
    """Return the Path to eqep0's count0/count sysfs attribute,
    whichever counterN index the kernel assigned it."""
    for device_dir in sorted(COUNTER_SYSFS_ROOT.glob("counter*")):
        name_file = device_dir / "name"
        if name_file.exists() and "eqep" in name_file.read_text().lower():
            count_path = device_dir / "count0" / "count"
            if count_path.exists():
                return count_path
    raise SystemExit(
        f"no eqep counter found under {COUNTER_SYSFS_ROOT} - "
        "is the BB-ROTARY-ENCODER-light-desk-00A0 overlay installed and booted? "
        f"check with: find {COUNTER_SYSFS_ROOT} -maxdepth 3"
    )


def ensure_quadrature_mode(count_path):
    """Set count0/function to a quadrature mode if it isn't already -
    the eQEP peripheral defaults to a plain pulse-direction mode on
    some kernels, not quadrature decode."""
    function_path = count_path.parent / "function"
    available_path = count_path.parent / "functions_available"
    if not function_path.exists() or not available_path.exists():
        return
    current = function_path.read_text().strip()
    if "quadrature" in current:
        return
    available = available_path.read_text().split()
    quadrature_modes = [f for f in available if "quadrature" in f]
    if not quadrature_modes:
        return
    chosen = next((f for f in quadrature_modes if "x4" in f), quadrature_modes[0])
    print(f"setting {function_path} to {chosen!r} (was {current!r})")
    function_path.write_text(chosen)


def read_count(count_path):
    return int(count_path.read_text().strip())


def find_line_candidates(name):
    """See scripts/buttons_debug_print.py for this helper - duplicated
    per-script rather than shared, same as every other button-reading
    script in this project."""
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


def resolve_button_pin(pin):
    if ":" in pin:
        chip, offset = pin.split(":", 1)
        return chip if chip.startswith("/dev/") else f"/dev/{chip}", int(offset)
    candidates = find_line_candidates(pin)
    if not candidates:
        raise SystemExit(f"no gpio line named {pin!r} found (check `gpioinfo` for the exact name)")
    return candidates[0]


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--button-pin", default="P2.19", help="encoder push button's `P2.NN` header pin name, or `gpiochipN:offset` (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=0.05, help="poll interval in seconds (default: %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()

    count_path = find_eqep_count_path()
    ensure_quadrature_mode(count_path)

    chip_path, offset = resolve_button_pin(args.button_pin)
    settings = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, active_low=True)
    request = gpiod.request_lines(chip_path, consumer=CONSUMER, config={offset: settings})

    print(f"reading {count_path}, button {args.button_pin} ({chip_path}:{offset}) - Ctrl-C to stop")

    raw_prev = read_count(count_path)
    total = 0
    try:
        while True:
            raw = read_count(count_path)
            delta = raw - raw_prev
            if delta > WRAP // 2:
                delta -= WRAP
            elif delta < -WRAP // 2:
                delta += WRAP
            total += delta
            raw_prev = raw

            pressed = request.get_value(offset) == Value.ACTIVE
            print(f"\rcounter: {total:6d}  {'*' if pressed else ' '}", end="", flush=True)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print()
    finally:
        request.release()


if __name__ == "__main__":
    sys.exit(main())
