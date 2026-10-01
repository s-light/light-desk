#!/usr/bin/env python3
"""Build and install the light-desk rotary-encoder device-tree
overlay (overlays/BB-ROTARY-ENCODER-light-desk-00A0.dts) into the
running kernel's overlays directory.

Enables eQEP0 (P1.31/P2.34) as a hardware quadrature decoder for one
rotary pulse encoder - see the overlay source for why eqep0
specifically (the only one of AM335x's 3 eQEP units with its full A/B
pair free on this board) and why hardware decoding over GPIO polling.

The encoder's own push button (P2.19) is a plain GPIO pin instead,
added to overlays/BB-GPIO-buttons-light-desk-00A0.dts - re-run
install-gpio-buttons-overlay.sh (not this script) to pick that up if
it hasn't been already.

Does NOT edit /boot/uEnv.txt or reboot - run apply-uenv-overlays.sh
after this to actually wire the overlay into boot, then reboot and
verify with: ls /sys/bus/counter/devices/

Usage: sudo ./install_rotary_encoder_overlay.py
"""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

OVERLAY_NAME = "BB-ROTARY-ENCODER-light-desk-00A0"


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def main():
    if os.geteuid() != 0:
        fail(f"must run as root, e.g.: sudo {sys.argv[0]}")

    script_dir = Path(__file__).resolve().parent
    kernel_ver = subprocess.run(["uname", "-r"], capture_output=True, text=True, check=True).stdout.strip()
    overlay_dir = Path(f"/boot/dtbs/{kernel_ver}/overlays")

    if not overlay_dir.is_dir():
        fail(f"overlays dir not found: {overlay_dir} (unexpected kernel/image layout)")

    source = script_dir / "overlays" / f"{OVERLAY_NAME}.dts"
    with tempfile.NamedTemporaryFile(suffix=".dtbo") as tmp:
        print(f"==> compiling {OVERLAY_NAME}.dts")
        subprocess.run(["dtc", "-@", "-O", "dtb", "-o", tmp.name, "-b", "0", str(source)], check=True)

        dest = overlay_dir / f"{OVERLAY_NAME}.dtbo"
        print(f"==> installing to {dest}")
        dest.write_bytes(Path(tmp.name).read_bytes())

    print(f"==> done: {dest}")
    print("    next: sudo ./apply-uenv-overlays.sh, then reboot")


if __name__ == "__main__":
    main()
