#!/usr/bin/env python3
"""Watch one GPIO button and toggle stand-alone mode (the
standalone-plasma.service unit, see scripts/standalone_plasma.py) on
each press - the physical mode switch for `stand alone mode.md`'s
`hsv-pixel-strip` mode.

This is meant to run continuously (see pb1/standalone-mode-toggle.service),
independently of whatever else is running - it only ever starts/stops
standalone-plasma.service. It deliberately does NOT touch
ads7830-to-osc.service or olad: per `stand alone mode.md`, control-desk
mode (sACN->DMX, fader/button->OSC) keeps running unaffected the whole
time; stand-alone mode is just "also running" on top of it while
toggled on. OLA seeing unrelated sACN traffic, or ads7830-to-osc.service
still sending OSC, while stand-alone mode is on, is fine - left to the
user, not guarded against here.

Current mode state is read live from systemd each press
(`systemctl is-active`), not tracked locally, so this stays correct
even if the service was started/stopped some other way between
presses (e.g. by hand for debugging).

Toggling needs root (systemctl start/stop on a system unit); this
script runs as a normal user (it only needs GPIO group access to read
the button, same as buttons_debug_print.py) and shells out to
`sudo -n systemctl start|stop standalone-plasma.service` for the
toggle itself - see pb1/setup_pb1.py's "standalone-mode" step for the scoped
NOPASSWD sudoers rule that makes the `-n` (non-interactive) work.

Usage:
    python3 standalone_mode_toggle.py [--button-pin P2.33] [--interval 0.05]
        [--debounce 3]

Ctrl-C to stop.
"""

import argparse
import glob
import re
import subprocess
import sys
import time

import gpiod
from gpiod.line import Bias, Direction, Value

SERVICE = "standalone-plasma.service"
CONSUMER = "standalone_mode_toggle"


def find_line_candidates(name):
    """Return [(chip_path, offset), ...] for every gpiochip exposing a
    line named `name` (bracketed/parenthesized alt-function suffix
    stripped) - see scripts/buttons_debug_print.py for the same
    helper and why it's duplicated per-script rather than shared."""
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


def is_mode_active():
    result = subprocess.run(["systemctl", "is-active", "--quiet", SERVICE])
    return result.returncode == 0


def toggle_mode():
    action = "stop" if is_mode_active() else "start"
    print(f"button pressed - {action}ing {SERVICE}")
    subprocess.run(["sudo", "-n", "systemctl", action, SERVICE], check=False)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--button-pin", default="P2.33", help="`P2.NN` header pin name (see `gpioinfo`) or an explicit `gpiochipN:offset` pair (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=0.05, help="poll interval in seconds (default: %(default)s)")
    parser.add_argument("--debounce", type=int, default=3, help="consecutive identical polls required before a press/release is considered real (default: %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()
    chip_path, offset = resolve_button_pin(args.button_pin)
    settings = gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, active_low=True)
    request = gpiod.request_lines(chip_path, consumer=CONSUMER, config={offset: settings})

    print(f"watching {args.button_pin} ({chip_path}:{offset}) for stand-alone mode toggle - Ctrl-C to stop")

    pending_pressed = False
    pending_count = 0
    confirmed_pressed = False
    try:
        while True:
            pressed = request.get_value(offset) == Value.ACTIVE
            if pressed == pending_pressed:
                pending_count += 1
            else:
                pending_pressed = pressed
                pending_count = 1
            if pending_count >= args.debounce and pressed != confirmed_pressed:
                confirmed_pressed = pressed
                if pressed:
                    toggle_mode()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        request.release()


if __name__ == "__main__":
    sys.exit(main())
