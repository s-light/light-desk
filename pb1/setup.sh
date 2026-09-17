#!/bin/sh
# PocketBeagle 1 board setup, step 0: creates the 'light' login user
# (mirroring the PocketBeagle 2 board, see the repo root CLAUDE.md) and
# grants it passwordless sudo for exactly the PB1 bring-up scripts in
# this folder - nothing broader. Mirrors the repo root's setup.sh (same
# idea, PB2 board), but scoped to the PB1-specific scripts instead of
# olad/apply-ola-config.sh.
#
# There's nothing project-specific tied to the 'light' username beyond
# what this script sets up: every other script in this repo (the root
# setup.sh, setup-i2c.sh, the ads7830-to-osc.service template) already
# derives the user from `id -un` at run time rather than hardcoding one,
# so once 'light' exists and is in the right groups, everything else
# just works when run as that user - no per-user services to port over
# separately.
#
# What this does:
#   - creates the 'light' user (home dir + bash shell) if missing
#   - adds it to sudo, dialout (UART), i2c, gpio - the same groups the
#     image's default 'debian' user already has, minus the broad 'admin'
#     group (that's what gives 'debian' passwordless sudo on this image;
#     this project's convention is scoped NOPASSWD rules instead of a
#     blanket one, see below)
#   - copies your own authorized_keys so the same SSH key that got you
#     onto this board works for 'light' too
#   - prompts you to set a login password for 'light' (needed for sudo
#     prompts that aren't covered by the NOPASSWD rule below, e.g.
#     one-time overlay installs, apt-get)
#   - installs a NOPASSWD sudoers rule for 'light' covering exactly the
#     other scripts in this folder (install-uart3-overlay.sh,
#     apply-uenv-overlays.sh, switch-console-to-usb.sh)
#
# Run this once per board, as your normal login user (it calls sudo
# itself - don't run this whole script with sudo). It will prompt for
# your sudo password interactively, and then for a new password for
# 'light'.
#
# Usage: ./setup.sh

set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo "run this as your normal user, not root/sudo - it calls sudo itself" >&2
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
NEW_USER=light
INVOKING_USER="$(id -un)"

echo "==> creating user '$NEW_USER' (if missing) and setting up groups/keys"
sudo sh -c "
set -eu
if id '$NEW_USER' >/dev/null 2>&1; then
    echo \"user '$NEW_USER' already exists, skipping creation\"
else
    useradd -m -s /bin/bash '$NEW_USER'
fi
usermod -aG sudo,dialout,i2c,gpio '$NEW_USER'
NEW_HOME=\"\$(getent passwd '$NEW_USER' | cut -d: -f6)\"
mkdir -p \"\$NEW_HOME/.ssh\"
chmod 700 \"\$NEW_HOME/.ssh\"
SRC_KEYS='/home/$INVOKING_USER/.ssh/authorized_keys'
if [ \"\$SRC_KEYS\" = \"\$NEW_HOME/.ssh/authorized_keys\" ]; then
    echo \"invoking user is already '$NEW_USER' - authorized_keys already in place, skipping copy\"
elif [ -f \"\$SRC_KEYS\" ]; then
    cp \"\$SRC_KEYS\" \"\$NEW_HOME/.ssh/authorized_keys\"
    chmod 600 \"\$NEW_HOME/.ssh/authorized_keys\"
else
    echo 'no authorized_keys found for $INVOKING_USER - add one yourself later' >&2
fi
chown -R '$NEW_USER:$NEW_USER' \"\$NEW_HOME/.ssh\"
"

echo "==> set a login password for '$NEW_USER' (needed for sudo prompts not covered below):"
sudo passwd "$NEW_USER"

SUDOERS_FILE=/etc/sudoers.d/light-desk-pb1
RULE="$NEW_USER ALL=(root) NOPASSWD: $SCRIPT_DIR/install-uart3-overlay.sh, $SCRIPT_DIR/apply-uenv-overlays.sh, $SCRIPT_DIR/switch-console-to-usb.sh"

echo "==> installing $SUDOERS_FILE"
printf '%s\n' "$RULE" | sudo tee "$SUDOERS_FILE" >/dev/null
sudo chmod 440 "$SUDOERS_FILE"

echo "==> validating sudoers syntax"
sudo visudo -c

echo "==> done. from your own machine, verify with a fresh connection:"
echo "    ssh $NEW_USER@<board-ip> 'id; groups'"
echo "    then update your local ~/.ssh/config alias to User $NEW_USER"
