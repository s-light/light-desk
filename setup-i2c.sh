#!/bin/sh
# Board setup: everything needed to run scripts/ads7830_to_osc.py as a
# systemd service.
#
#   - creates/enables an "i2c" group with a udev rule so /dev/i2c-* is
#     group-accessible (not just root), and adds the current user to it
#   - creates a Python venv in scripts/.venv and installs
#     scripts/requirements.txt into it (Debian 13's system Python refuses
#     plain `pip install` - PEP 668 "externally managed environment")
#   - installs ads7830-to-osc.service from the template in this repo,
#     filling in the current user/repo path/venv, then enables + starts it
#
# Re-running this script is safe (idempotent).
#
# Run this once per board, as your normal login user (it calls sudo
# itself - don't run this whole script with sudo). Log out/in afterwards
# (or `newgrp i2c`) for the new group membership to take effect in your
# own shell - the systemd service itself doesn't need that, it gets the
# group from a fresh login session.
#
# Usage: ./setup-i2c.sh

set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo "run this as your normal user, not root/sudo - it calls sudo itself" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_NAME="$(id -un)"
GROUP_NAME=i2c
UDEV_RULE=/etc/udev/rules.d/60-light-desk-i2c.rules
VENV_DIR="$SCRIPT_DIR/scripts/.venv"
SERVICE_NAME=ads7830-to-osc.service

echo "==> ensuring group '$GROUP_NAME' exists"
getent group "$GROUP_NAME" >/dev/null || sudo groupadd --system "$GROUP_NAME"

echo "==> installing udev rule: $UDEV_RULE"
printf 'SUBSYSTEM=="i2c-dev", GROUP="%s", MODE="0660"\n' "$GROUP_NAME" | sudo tee "$UDEV_RULE" >/dev/null
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=i2c-dev

echo "==> adding $USER_NAME to '$GROUP_NAME'"
sudo usermod -aG "$GROUP_NAME" "$USER_NAME"

echo "==> creating venv: $VENV_DIR"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/scripts/requirements.txt"

echo "==> installing $SERVICE_NAME"
sed -e "s|__USER__|$USER_NAME|" \
    -e "s|__REPO_DIR__|$SCRIPT_DIR|" \
    -e "s|__VENV_DIR__|$VENV_DIR|" \
    "$SCRIPT_DIR/ads7830-to-osc.service" | sudo tee "/etc/systemd/system/$SERVICE_NAME" >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now "$SERVICE_NAME"

echo "==> done. verify with:"
echo "    sudo systemctl status $SERVICE_NAME"
echo "    sudo journalctl -u $SERVICE_NAME -f"
echo "    i2cdetect -l   # confirm I2C_BUS=1 in the service is the right /dev/i2c-N"
