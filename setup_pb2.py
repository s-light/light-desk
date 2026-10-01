#!/usr/bin/env python3
"""Single entry point for PocketBeagle 2 setup - replaces the
previous collection of separate setup.sh/setup-i2c.sh/apply-ola-
config.sh/install-*-overlay.sh scripts at the repo root (see
pb1/memo.md's "one setup command" item for why these were
consolidated, mirroring pb1/setup_pb1.py).

    ./setup_pb2.py            # run every step, in order
    ./setup_pb2.py STEP_NAME  # run just one step
    ./setup_pb2.py --list-steps

Unlike PB1, PB2 doesn't create a separate login user - it just grants
NOPASSWD sudo to whoever's already logged in. Every step needs root;
run this as your normal user (not already under sudo) - it re-execs
itself through `sudo` once at the top, so you get one password
prompt for the whole run.

Every step is idempotent - safe to re-run the whole thing any time,
including after a partial run. The "overlays" step needs a *reboot*
before "ola" below it can work (the device-tree overlays actually
taking effect) - it detects this and stops cleanly with a message to
that effect; just reboot and run this again.
"""

import os
import sys
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_DIR))
import lightdesk_setup as ld  # noqa: E402

VENV_DIR = REPO_DIR / "scripts" / ".venv"


class NeedsReboot(Exception):
    pass


# --- steps -----------------------------------------------------------------

def step_packages():
    """apt packages: ola (sACN->DMX daemon), i2c-tools."""
    ld.apt_install("ola", "i2c-tools")


def step_sudoers():
    """NOPASSWD sudo for the current user, scoped to exactly this
    script, olad/ads7830-to-osc service management."""
    username = ld.invoking_user() or os.environ.get("USER") or os.environ["LOGNAME"]
    ld.add_nopasswd_sudoers(
        "light-desk-ola",
        username,
        [
            f"{Path(__file__).resolve()} *",
            "/usr/sbin/service olad *",
            "/usr/bin/systemctl * olad*",
            "/usr/bin/journalctl -u olad*",
            "/usr/bin/systemctl * ads7830-to-osc*",
            "/usr/bin/journalctl -u ads7830-to-osc*",
        ],
    )


def step_i2c():
    """i2c group/udev/lgpio/venv - identical on both boards, see
    lightdesk_setup.setup_i2c_and_venv."""
    username = ld.invoking_user() or os.environ.get("USER") or os.environ["LOGNAME"]
    ld.setup_i2c_and_venv(username, VENV_DIR, REPO_DIR / "scripts" / "requirements.txt")


def step_overlays():
    """Compile+install this repo's 2 custom overlays (I2C1, UART-DMX)
    into the full kernel DTB source tree and wire them into the
    default extlinux boot label. Needs a reboot before "ola" below
    can work."""
    overlays = [
        "k3-am62-pocketbeagle2-light-desk-i2c1-adc",
        "k3-am62-pocketbeagle2-light-desk-uart-dmx",
    ]
    for name in overlays:
        ld.compile_and_install_overlay_extlinux(REPO_DIR / "overlays" / f"{name}.dtso", name)
        ld.wire_overlay_into_extlinux(name)

    if not Path("/dev/ttyS1").exists():
        raise NeedsReboot(
            "overlays installed and wired, but not active yet (/dev/ttyS1 missing) - "
            "reboot, then re-run ./setup_pb2.py to continue with the remaining steps"
        )


def step_ola():
    """olad config: e131/uartdmx/dummy, 5 DMX universes patched to
    ttyS1/ttyS3/ttyS4/ttyS5/ttyS7."""
    olad_running = ld.apply_ola_config(REPO_DIR / "ola-config", num_universes=5)
    if not olad_running:
        raise NeedsReboot("olad.service isn't installed/running yet - install the `ola` apt package and try again")
    ld.patch_sacn_to_uart(5)


def step_fader_osc():
    """ads7830-to-osc.service with the template's own (PB2) defaults -
    no overrides needed, unlike PB1."""
    username = ld.invoking_user() or os.environ.get("USER") or os.environ["LOGNAME"]
    ld.install_systemd_unit(
        REPO_DIR / "ads7830-to-osc.service",
        "ads7830-to-osc.service",
        {"USER": username, "REPO_DIR": REPO_DIR, "VENV_DIR": VENV_DIR},
        enable_now=True,
    )


STEPS = [
    ("packages", step_packages),
    ("sudoers", step_sudoers),
    ("i2c", step_i2c),
    ("overlays", step_overlays),
    ("ola", step_ola),
    ("fader-osc", step_fader_osc),
]


def main():
    args = sys.argv[1:]

    if args and args[0] == "--list-steps":
        for name, _ in STEPS:
            print(name)
        return

    if os.geteuid() != 0:
        os.execvp("sudo", ["sudo", str(Path(__file__).resolve()), *args])

    steps_by_name = dict(STEPS)
    if args:
        name = args[0]
        if name not in steps_by_name:
            ld.fail(f"unknown step {name!r} - see --list-steps")
        selected = [(name, steps_by_name[name])]
    else:
        selected = STEPS

    for name, func in selected:
        print(f"\n===== {name} =====")
        try:
            func()
        except NeedsReboot as e:
            print(f"\n{e}")
            sys.exit(0)


if __name__ == "__main__":
    main()
