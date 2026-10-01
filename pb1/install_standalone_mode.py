#!/usr/bin/env python3
"""Install stand-alone mode's two systemd units
(standalone-plasma.service, standalone-mode-toggle.service - see
`stand alone mode.md` and pb1/memo.md item 15), filled in with this
board's user/repo/venv paths, plus the scoped NOPASSWD sudoers rule
scripts/standalone_mode_toggle.py needs to start/stop the plasma
service from a plain user account.

Requires scripts/.venv to already exist (see ../setup-i2c.sh) -
standalone-plasma.service runs through it, same as
ads7830-to-osc.service.

Only standalone-mode-toggle.service is enabled+started here (it's the
always-on button watcher) - standalone-plasma.service is installed
but left inactive, only started/stopped by that watcher (or by hand,
`sudo systemctl start|stop standalone-plasma.service`, for testing).

Also needs the BB-GPIO-buttons-light-desk-00A0.dtbo overlay rebuilt
and reloaded with P2.33 added (see
overlays/BB-GPIO-buttons-light-desk-00A0.dts) - run
install-gpio-buttons-overlay.sh + apply-uenv-overlays.sh + reboot
first if that hasn't happened yet; this script doesn't touch overlays
itself.

Usage: sudo ./install_standalone_mode.py
"""

import os
import subprocess
import sys
from pathlib import Path

SUDOERS_FILE = Path("/etc/sudoers.d/light-desk-standalone-mode")
SYSTEMD_DIR = Path("/etc/systemd/system")
UNITS = ["standalone-plasma.service", "standalone-mode-toggle.service"]


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def run(cmd, **kwargs):
    print(f"==> {' '.join(cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def main():
    if os.geteuid() != 0:
        fail(f"must run as root, e.g.: sudo {sys.argv[0]}")

    script_dir = Path(__file__).resolve().parent
    repo_dir = script_dir.parent
    venv_dir = repo_dir / "scripts" / ".venv"
    user_name = os.environ.get("SUDO_USER", "light")

    if not (venv_dir / "bin" / "python3").exists():
        fail(f"no venv at {venv_dir} - run ../setup-i2c.sh first (as your normal user, not root)")

    print(f"==> installing {', '.join(UNITS)} (user={user_name}, repo={repo_dir})")
    for unit in UNITS:
        template = (script_dir / unit).read_text()
        filled = (
            template
            .replace("__USER__", user_name)
            .replace("__REPO_DIR__", str(repo_dir))
            .replace("__VENV_DIR__", str(venv_dir))
        )
        (SYSTEMD_DIR / unit).write_text(filled)

    sudoers_rule = (
        f"{user_name} ALL=(root) NOPASSWD: "
        f"/usr/bin/systemctl start standalone-plasma.service, "
        f"/usr/bin/systemctl stop standalone-plasma.service\n"
    )
    print(f"==> installing {SUDOERS_FILE}")
    SUDOERS_FILE.write_text(sudoers_rule)
    SUDOERS_FILE.chmod(0o440)

    print("==> validating sudoers syntax")
    run(["visudo", "-c"])

    run(["systemctl", "daemon-reload"])
    run(["systemctl", "enable", "--now", "standalone-mode-toggle.service"])

    print("==> done. standalone-mode-toggle.service is running (watching P2.33).")
    print("    standalone-plasma.service is installed but inactive until toggled.")
    print("    verify with:")
    print("        systemctl status standalone-mode-toggle.service")
    print("        journalctl -u standalone-mode-toggle.service -f")


if __name__ == "__main__":
    main()
