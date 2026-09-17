#!/bin/sh
# Board setup: make the root filesystem read-only, so a hard power-loss
# (unplugging the board instead of a clean shutdown) can't corrupt it.
#
# NOTE on approach: the obvious tool here would be `overlayroot` (mounts
# a real read-only root under a tmpfs overlay), but it doesn't work on
# this board - it needs an initrd, and this board's U-Boot/extlinux setup
# fails to load one correctly (confirmed on real hardware: enabling
# `initrd /initrd.img` in extlinux.conf's default label causes a kernel
# panic, "Failed to execute /init (error -2)", even though the initrd
# file itself is intact - the initrd's stock labels all ship with `initrd`
# commented out for exactly this reason). This script instead uses the
# classic fstab-based read-only root: no initrd, no bootloader changes,
# nothing that can affect whether the board boots at all.
#
# What it does:
#   - disables docker/containerd - present on the stock BeagleBoard image
#     but unused by this project; even with no containers running,
#     containerd keeps a writable mmap open on /, which blocks the
#     read-only remount below with "mount point is busy"
#   - removes `overlayroot` and /etc/overlayroot.local.conf if present
#     (leftover from investigating the approach above - inert without an
#     initrd, but misleading to leave lying around)
#   - points journald at volatile (RAM-only, /run) storage, so logging
#     needs no disk write
#   - adds `ro` to /etc/fstab's root entry
#
# Root already boots `ro` at the kernel level (see /proc/cmdline) - it's
# /etc/fstab's missing `ro` option that lets systemd-remount-fs.service
# remount it rw right after boot. Adding it there is the whole fix.
#
# NOTE: this does NOT live-test the remount on a running system first -
# confirmed on real hardware that `mount -o remount,ro /` on a fully
# booted system reliably fails with "mount point is busy" regardless of
# docker/containerd, because the kernel refuses a remount-ro while ANY
# process holds ANY file on that filesystem open for writing, which is
# just normal running-system background noise (journald mid-restart,
# D-Bus, sshd session logging, etc.) - not a sign of a real problem. The
# actual mechanism this script relies on is systemd-remount-fs.service
# applying fstab's `ro` very early at boot, before those things have
# started - which is untested until you actually reboot. Do that with
# serial console access ready, the same way you'd watch any boot here.
#
# Recovery if anything looks wrong after rebooting: this never touches
# extlinux.conf or any initrd (unlike the overlayroot dead end mentioned
# above), so it's just editing /etc/fstab back (from a live session if
# it partially comes up, or via the microSD card on another machine) and
# rebooting again.
#
# Not handled here: the swap partition (/dev/mmcblk1p2) still writes to
# the SD card independent of this. Raw partition writes there don't
# corrupt the root filesystem, just add wear - disable separately with
# `sudo swapoff -a` + removing its /etc/fstab line if you want to close
# that gap too (trade-off against this board's 512MB RAM).
#
# Run this once per board, as your normal login user (it calls sudo
# itself - don't run this whole script with sudo).
#
# Usage: ./setup-readonly-root.sh

set -eu

if [ "$(id -u)" -eq 0 ]; then
    echo "run this as your normal user, not root/sudo - it calls sudo itself" >&2
    exit 1
fi

FSTAB=/etc/fstab

echo "==> disabling docker/containerd (unused by this project, holds / busy)"
if systemctl list-unit-files docker.service >/dev/null 2>&1; then
    sudo systemctl disable --now docker.service docker.socket containerd.service
else
    echo "    docker not installed, skipping"
fi

echo "==> removing overlayroot (doesn't work on this board, see script header)"
if dpkg -s overlayroot >/dev/null 2>&1; then
    sudo apt-get remove -y overlayroot
    # overlayroot pulls in cryptsetup for its (unused here) encrypted
    # backing-device option; clean that orphan up too rather than leaving
    # it stranded on what should end up a lean, stock-plus-project image.
    sudo apt-get autoremove -y
else
    echo "    not installed, skipping"
fi
sudo rm -f /etc/overlayroot.local.conf

echo "==> journald: volatile (RAM-only) storage"
sudo mkdir -p /etc/systemd/journald.conf.d
printf '[Journal]\nStorage=volatile\n' | sudo tee /etc/systemd/journald.conf.d/volatile.conf >/dev/null
sudo systemctl restart systemd-journald

if awk '$2=="/" && $4 ~ /(^|,)ro(,|$)/{f=1} END{exit !f}' "$FSTAB"; then
    echo "==> $FSTAB already has 'ro' for /, skipping"
else
    echo "==> persisting: adding 'ro' to /'s entry in $FSTAB"
    sudo cp "$FSTAB" "$FSTAB.bak-$(date +%Y%m%d%H%M%S)"
    awk 'BEGIN{OFS="\t"} $2=="/"{$4=$4",ro"} {print}' "$FSTAB" >/tmp/fstab.new.$$
    sudo cp /tmp/fstab.new.$$ "$FSTAB"
    rm -f /tmp/fstab.new.$$
    grep ' / ' "$FSTAB"
fi

echo "==> done. reboot to confirm it persists: sudo reboot"
