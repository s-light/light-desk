#!/bin/sh
# Board setup, step 0: grant the current user passwordless sudo for
# exactly the commands needed to manage olad and run apply-ola-config.sh
# - nothing broader. Lets an assistant/automation drive the rest of the
# setup (systemctl, journalctl, apply-ola-config.sh) without needing an
# interactive sudo password every time.
#
# Run this once per board, as your normal login user (it calls sudo
# itself - don't run this whole script with sudo).
#
# Usage: ./setup.sh

set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo "run this as your normal user, not root/sudo - it calls sudo itself" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SUDOERS_FILE=/etc/sudoers.d/light-desk-ola
USER_NAME="$(id -un)"

RULE="$USER_NAME ALL=(root) NOPASSWD: /usr/sbin/service olad *, /usr/bin/systemctl * olad*, /usr/bin/journalctl -u olad*, $SCRIPT_DIR/apply-ola-config.sh"

echo "==> installing $SUDOERS_FILE"
printf '%s\n' "$RULE" | sudo tee "$SUDOERS_FILE" >/dev/null
sudo chmod 440 "$SUDOERS_FILE"

echo "==> validating sudoers syntax"
sudo visudo -c

echo "==> done. verify with: sudo -n systemctl restart olad.service"
