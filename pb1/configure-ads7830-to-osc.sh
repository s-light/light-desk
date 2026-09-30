#!/bin/sh
# (Re)install ads7830-to-osc.service with PocketBeagle 1's own values
# baked in: 7 fader channels (not PB2's 8), PB1's own button pins
# (not PB2's P2.27 etc, which don't exist as GPIO here - see
# memo.md item 9), and PB1's own internet-sharing host IP (see
# pb1_internet_share.md).
#
# Without this, the service crash-loops if it was installed from the
# plain ../ads7830-to-osc.service template (e.g. via ../setup-i2c.sh):
# PB2's default --button-pins includes P2.27, which errors immediately
# on PB1 ("no gpio line named 'P2.27' found").
#
# Requires ../setup-i2c.sh to have been run at least once already (it
# creates the venv and the i2c/udev setup this service needs) - this
# only reinstalls the systemd unit itself, filled in with PB1's
# values instead of PB2's, using the exact same
# __USER__/__REPO_DIR__/__VENV_DIR__ placeholder-fill approach
# ../setup-i2c.sh uses. Safe/idempotent to re-run.
#
# Fader min/max below (0.01/0.99) are a conservative margin, not a
# precise per-fader calibration - see memo.md's fader-calibration
# follow-up for the real measured values (two faders bottom out at
# 0.008, all top out at 0.996) and options for tightening this later.
#
# Usage: sudo ./configure-ads7830-to-osc.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "must run as root, e.g.: sudo $0" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$REPO_DIR/scripts/.venv"
SERVICE_NAME=ads7830-to-osc.service
USER_NAME="${SUDO_USER:-light}"

if [ ! -x "$VENV_DIR/bin/python3" ]; then
    echo "no venv at $VENV_DIR - run ../setup-i2c.sh first (as your normal user, not root)" >&2
    exit 1
fi

echo "==> installing $SERVICE_NAME with PB1's values (7 channels, PB1 button pins, host 192.168.17.1)"
sed -e "s|__USER__|$USER_NAME|" \
    -e "s|__REPO_DIR__|$REPO_DIR|" \
    -e "s|__VENV_DIR__|$VENV_DIR|" \
    -e "s|Environment=OSC_HOST=.*|Environment=OSC_HOST=192.168.17.1|" \
    -e "s|Environment=NUM_CHANNELS=.*|Environment=NUM_CHANNELS=7|" \
    -e "s|Environment=BUTTON_PINS=.*|Environment=BUTTON_PINS=P2.02,P2.04,P2.06,P2.20,P2.22,P2.24|" \
    -e "s|Environment=FADER_MIN=.*|Environment=FADER_MIN=0.01|" \
    -e "s|Environment=FADER_MAX=.*|Environment=FADER_MAX=0.99|" \
    "$REPO_DIR/ads7830-to-osc.service" > "/etc/systemd/system/$SERVICE_NAME"

systemctl daemon-reload
systemctl enable --now "$SERVICE_NAME"
sleep 1

echo "==> done. verify with:"
echo "    systemctl status $SERVICE_NAME"
echo "    journalctl -u $SERVICE_NAME -f"
