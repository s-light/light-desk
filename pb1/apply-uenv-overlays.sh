#!/bin/sh
# Wire the 4 device-tree overlays this project needs on PocketBeagle 1
# into /boot/uEnv.txt's U-Boot overlay slots (uboot_overlay_addr0-7):
#
#   - BB-UART1-00A0.dtbo              stock overlay -> universe 1 (P2.09/P2.11)
#   - BB-UART2-00A0.dtbo              stock overlay -> universe 2 (P1.08/P1.10)
#   - BB-I2C1-00A0.dtbo                stock overlay -> ADS7830 fader ADC (P1.06/P1.12)
#   - BB-UART3-light-desk-00A0.dtbo   this repo's overlay -> universe 3 (P2.29, TX-only)
#
# universe 4 (UART4, P2.05/P2.07) needs no overlay - the base
# am335x-pocketbeagle.dtb already enables it by default. universe 5
# (UART0, P1.30/P1.32) needs no overlay either, just console reassignment
# - see switch-console-to-usb.sh.
#
# Idempotent: only fills in slots that are still at their commented
# default placeholder, and skips any overlay already wired to a slot.
# Never touches slots already in use for something else.
#
# Does NOT reboot - do that yourself once this finishes, then verify with:
#   ls -la /dev/ttyS1 /dev/ttyS2 /dev/ttyS3
#   i2cdetect -y 1   # look for the ADS7830 at 0x48-0x4b
#
# Usage: sudo ./apply-uenv-overlays.sh

set -eu

if [ "$(id -u)" -ne 0 ]; then
    echo "must run as root, e.g.: sudo $0" >&2
    exit 1
fi

UENV_CONF=/boot/uEnv.txt
OVERLAYS="BB-UART1-00A0.dtbo BB-UART2-00A0.dtbo BB-I2C1-00A0.dtbo BB-UART3-light-desk-00A0.dtbo"

python3 - "$UENV_CONF" $OVERLAYS <<'PYEOF'
import re
import sys

conf_path = sys.argv[1]
wanted = sys.argv[2:]

with open(conf_path) as f:
    lines = f.readlines()

addr_re = re.compile(r"^(#?)uboot_overlay_addr(\d+)=(.*)$")

used_slots = {}
free_slots = []
for i, line in enumerate(lines):
    m = addr_re.match(line.strip())
    if not m:
        continue
    commented, slot, value = m.group(1), int(m.group(2)), m.group(3)
    if commented:
        free_slots.append((i, slot))
    else:
        used_slots[value.strip()] = (i, slot)

changed = False
for overlay in wanted:
    if overlay in used_slots:
        print(f"already wired: {overlay} (slot {used_slots[overlay][1]})")
        continue
    if not free_slots:
        sys.exit(f"no free uboot_overlay_addrN slot left for {overlay}")
    i, slot = free_slots.pop(0)
    lines[i] = f"uboot_overlay_addr{slot}={overlay}\n"
    used_slots[overlay] = (i, slot)
    changed = True
    print(f"wired: {overlay} -> uboot_overlay_addr{slot}")

if changed:
    with open(conf_path, "w") as f:
        f.writelines(lines)
else:
    print("no changes needed")
PYEOF

echo "==> done. reboot to apply, then verify with:"
echo "    ls -la /dev/ttyS1 /dev/ttyS2 /dev/ttyS3"
echo "    i2cdetect -y 1"
