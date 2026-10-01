#!/usr/bin/env python3
"""Single entry point for PocketBeagle 1 setup - replaces the
previous collection of separate install-*.sh/apply-*.sh/configure-*.sh
scripts in this folder (see pb1/memo.md's "one setup command" item for
why they were consolidated).

    ./setup_pb1.py            # run every step, in order
    ./setup_pb1.py STEP_NAME  # run just one step
    ./setup_pb1.py --list-steps

Every step needs root; run this as your normal user (not already
under sudo) - it re-execs itself through `sudo` once at the top, so
you get exactly one password prompt for the whole run (plus one more
if the "user" step needs to set a new login password), not one per
step.

Every step is idempotent - safe to re-run the whole thing any time,
including after a partial run. The "overlays" step needs a *reboot*
before the "ola"/"standalone-mode" steps below it can work (the
device-tree overlays actually taking effect) - it detects this and
stops cleanly (not an error) with a message to that effect rather
than failing confusingly further down; just reboot and run this
again, already-done steps are skipped automatically.
"""

import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_DIR))
import lightdesk_setup as ld  # noqa: E402

NEW_USER = "light"
VENV_DIR = REPO_DIR / "scripts" / ".venv"


class NeedsReboot(Exception):
    pass


# --- steps -----------------------------------------------------------------

def step_user():
    """Create the 'light' user, groups, SSH keys, login password,
    and this board's NOPASSWD sudoers rule (covers this script
    itself - once this step has run, no other step needs a password,
    since `setup_pb1.py` auto-escalates itself through `sudo`)."""
    invoking = ld.invoking_user() or os.environ.get("USER") or os.environ["LOGNAME"]
    ld.ensure_group("i2c")  # step_i2c (which otherwise owns this) runs after this step
    ld.ensure_user(NEW_USER, ["sudo", "dialout", "i2c", "gpio"], copy_ssh_keys_from=invoking)
    ld.add_nopasswd_sudoers("light-desk-pb1", NEW_USER, [f"{SCRIPT_DIR / 'setup_pb1.py'} *"])
    if invoking != NEW_USER:
        print(f"set a login password for '{NEW_USER}' (needed for sudo prompts the rule above doesn't cover):")
        subprocess.run(["passwd", NEW_USER], check=True)
    print(f"done. from your own machine, verify with a fresh connection: ssh {NEW_USER}@<board-ip> 'id; groups'")


def step_packages():
    """apt packages: ola (sACN->DMX daemon), i2c-tools."""
    ld.apt_install("ola", "i2c-tools")


def step_i2c():
    """i2c group/udev/lgpio/venv - identical on both boards, see
    lightdesk_setup.setup_i2c_and_venv."""
    ld.setup_i2c_and_venv(NEW_USER, VENV_DIR, REPO_DIR / "scripts" / "requirements.txt")


def step_overlays():
    """Compile+install this repo's 4 custom overlays and wire all 7
    (those 4 plus the 3 stock ones) into uEnv.txt's U-Boot overlay
    slots. Needs a reboot before anything below here can use the
    pins/peripherals they enable."""
    custom_overlays = [
        "BB-UART3-light-desk-00A0",
        "BB-GPIO-buttons-light-desk-00A0",
        "BB-SPI1-APA102-light-desk-00A0",
        "BB-ROTARY-ENCODER-light-desk-00A0",
    ]
    for name in custom_overlays:
        ld.compile_and_install_overlay_uboot(SCRIPT_DIR / "overlays" / f"{name}.dts", name)

    all_overlays = ["BB-UART1-00A0", "BB-UART2-00A0", "BB-I2C1-00A0"] + custom_overlays
    ld.wire_overlays_into_uenv([f"{name}.dtbo" for name in all_overlays])

    if not Path("/dev/spidev1.0").exists():
        raise NeedsReboot(
            "overlays installed and wired, but not active yet (/dev/spidev1.0 missing) - "
            "reboot, then re-run ./setup_pb1.py to continue with the remaining steps"
        )


def step_ola():
    """olad config: e131/uartdmx/dummy + spi (for the APA102 output),
    4 DMX universes patched to ttyS1-4, universe 5 patched to the SPI
    device. Needs step_overlays' reboot to have happened already
    (spidev1.0, the uartdmx-capable ttyS nodes)."""
    ola_dir = SCRIPT_DIR / "ola-config"
    olad_running = ld.apply_ola_config(
        ola_dir, num_universes=4, extra_enabled_plugins=["spi"],
    )
    if not olad_running:
        raise NeedsReboot("olad.service isn't installed/running yet - install the `ola` apt package and try again")
    ld.patch_sacn_to_uart(4, e131_device=2, uartdmx_device_start=4)
    ld.patch_spi_apa102(e131_device=2, spi_device=3, spi_universe=5)


def step_fader_osc():
    """ads7830-to-osc.service with PB1's own values baked in (7
    channels, PB1's button pins, PB1's internet-sharing host IP,
    0.01/0.99 fader margin)."""
    ld.install_systemd_unit(
        REPO_DIR / "ads7830-to-osc.service",
        "ads7830-to-osc.service",
        {
            "USER": NEW_USER,
            "REPO_DIR": REPO_DIR,
            "VENV_DIR": VENV_DIR,
        },
        enable_now=False,  # enabled below, after the PB1-specific env overrides are in place
    )
    # install_systemd_unit() above writes the plain template (PB2
    # defaults); patch in PB1's values the same way
    # configure-ads7830-to-osc.sh used to, then enable.
    unit_path = Path("/etc/systemd/system/ads7830-to-osc.service")
    text = unit_path.read_text()
    overrides = {
        "OSC_HOST": "192.168.17.1",
        "NUM_CHANNELS": "7",
        "BUTTON_PINS": "P2.02,P2.04,P2.06,P2.20,P2.22,P2.24",
        "FADER_MIN": "0.01",
        "FADER_MAX": "0.99",
    }
    import re
    for key, value in overrides.items():
        text = re.sub(rf"^Environment={key}=.*$", f"Environment={key}={value}", text, flags=re.MULTILINE)
    unit_path.write_text(text)
    ld.run(["systemctl", "daemon-reload"])
    ld.run(["systemctl", "enable", "--now", "ads7830-to-osc.service"])


def step_standalone_mode():
    """Stand-alone hsv-pixel-strip mode's two units - the toggle
    watcher (always on) and the plasma effect itself (installed,
    left inactive until a P2.33 press). Needs step_overlays' reboot
    (P2.33's pull-up)."""
    if not (VENV_DIR / "bin" / "python3").exists():
        raise NeedsReboot("no venv yet - run step_i2c first")

    substitutions = {"USER": NEW_USER, "REPO_DIR": REPO_DIR, "VENV_DIR": VENV_DIR}
    ld.install_systemd_unit(SCRIPT_DIR / "standalone-plasma.service", "standalone-plasma.service", substitutions)
    ld.install_systemd_unit(SCRIPT_DIR / "standalone-mode-toggle.service", "standalone-mode-toggle.service",
                             substitutions, enable_now=True)
    ld.add_nopasswd_sudoers(
        "light-desk-standalone-mode",
        NEW_USER,
        ["/usr/bin/systemctl start standalone-plasma.service", "/usr/bin/systemctl stop standalone-plasma.service"],
    )


def step_console_to_usb():
    """NOT run by default (not in STEPS below) - freeing UART0 for a
    5th DMX universe by moving the serial console to USB gadget
    (ttyGS0). Deliberately parked: this reproducibly hung the board
    for 2+ minutes during testing (see memo.md) and PB1 ships with 4
    DMX universes instead. Only run this deliberately if revisiting
    that decision."""
    uenv_path = Path("/boot/uEnv.txt")
    ld.run(["systemctl", "disable", "--now", "serial-getty@ttyS0.service"], check=False)
    ld.run(["systemctl", "enable", "--now", "serial-getty@ttyGS0.service"])
    text = uenv_path.read_text()
    if "console=ttyGS0," in text:
        print("    already set to ttyGS0")
    elif "console=ttyS0," in text:
        uenv_path.write_text(text.replace("console=ttyS0,", "console=ttyGS0,"))
        print("    updated console=ttyS0 -> console=ttyGS0")
    else:
        print(f"    warning: no 'console=ttyS0,...' line found in {uenv_path} - check it by hand", file=sys.stderr)


STEPS = [
    ("user", step_user),
    ("packages", step_packages),
    ("i2c", step_i2c),
    ("overlays", step_overlays),
    ("ola", step_ola),
    ("fader-osc", step_fader_osc),
    ("standalone-mode", step_standalone_mode),
]
# console-to-usb is intentionally excluded from the default run - see
# step_console_to_usb's docstring.
ALL_STEPS = dict(STEPS + [("console-to-usb", step_console_to_usb)])


def main():
    args = sys.argv[1:]

    if args and args[0] == "--list-steps":
        for name, _ in STEPS:
            print(name)
        print("console-to-usb  (not run by default - see its docstring)")
        return

    # Every step needs root (user creation, apt, writing to /etc,
    # /boot, systemd) - auto-escalate once here instead of each
    # script/step managing its own sudo calls, like the old separate
    # scripts had to. `sudo` sets SUDO_USER, which
    # ld.invoking_user() reads for step_user's SSH-key copy.
    if os.geteuid() != 0:
        os.execvp("sudo", ["sudo", str(Path(__file__).resolve()), *args])

    if args:
        name = args[0]
        if name not in ALL_STEPS:
            ld.fail(f"unknown step {name!r} - see --list-steps")
        selected = [(name, ALL_STEPS[name])]
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
