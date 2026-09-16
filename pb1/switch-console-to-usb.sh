#!/bin/sh
# Free UART0 (P1.30/P1.32) for use as DMX universe 5 by moving the serial
# debug console off it - onto the USB gadget-serial console (ttyGS0)
# instead, which this board image already runs alongside ttyS0 out of the
# box (serial-getty@ttyGS0.service is enabled+active by default on the
# am335x-debian-13.6 image - confirmed on this board before making any
# changes). Unlike PocketBeagle 2, PB1's console *is* UART0 (no separate
# console UART instance), so this tradeoff is specific to PB1.
#
# Does two things:
#   - disables+stops serial-getty@ttyS0.service (no more login prompt
#     holding /dev/ttyS0 open)
#   - changes the `console=` line in /boot/uEnv.txt from ttyS0 to ttyGS0,
#     so the kernel stops treating ttyS0 as a boot console too
#
# ttyGS0 stays reachable exactly as before this script runs - over the
# same USB cable, no separate hardware needed. Idempotent.
#
# Does NOT reboot - the /boot/uEnv.txt change needs a reboot to take
# effect (the getty change is immediate). Do that yourself once this
# finishes, then verify with:
#   systemctl is-active serial-getty@ttyGS0
#   ls -la /dev/ttyS0   # now free for olad's uartdmx plugin
#
# Usage: sudo ./switch-console-to-usb.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "must run as root, e.g.: sudo $0" >&2
    exit 1
fi

UENV_CONF=/boot/uEnv.txt

echo "==> disabling serial-getty@ttyS0.service"
systemctl disable --now serial-getty@ttyS0.service 2>&1 || true

echo "==> confirming serial-getty@ttyGS0.service is enabled"
systemctl enable --now serial-getty@ttyGS0.service

echo "==> updating console= line in $UENV_CONF"
if grep -qE '^console=ttyGS0,' "$UENV_CONF"; then
    echo "already set to ttyGS0"
elif grep -qE '^console=ttyS0,' "$UENV_CONF"; then
    sed -i 's/^console=ttyS0,/console=ttyGS0,/' "$UENV_CONF"
    echo "updated console=ttyS0 -> console=ttyGS0"
else
    echo "warning: no 'console=ttyS0,...' line found in $UENV_CONF - check it by hand" >&2
fi

echo "==> done. reboot to apply, then verify UART0 is free:"
echo "    ls -la /dev/ttyS0"
