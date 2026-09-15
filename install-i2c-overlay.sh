#!/bin/sh
# Build and install the light-desk I2C1 device-tree overlay
# (overlays/k3-am62-pocketbeagle2-light-desk-i2c1-adc.dtso), and wire it
# into the currently active extlinux boot label.
#
# Does NOT reboot - the board needs a reboot for a new fdtoverlays entry
# to take effect. Do that yourself once this finishes, then verify with:
#   i2cdetect -y 1
# (look for the ADS7830 at 0x48-0x4b)
#
# Run as your normal user, not root (it calls sudo itself). Safe to
# re-run - both the build and the extlinux.conf edit are idempotent.
#
# Usage: ./install-i2c-overlay.sh
# Override the DTB source tree with:
#   DTB_SRC_DIR=/opt/source/dtb-X.Y.x ./install-i2c-overlay.sh

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OVERLAY_NAME=k3-am62-pocketbeagle2-light-desk-i2c1-adc
EXTLINUX_CONF=/boot/firmware/extlinux/extlinux.conf

if [ "$(id -u)" -eq 0 ]; then
    echo "run this as your normal user, not root/sudo - it calls sudo itself" >&2
    exit 1
fi

if [ -z "${DTB_SRC_DIR:-}" ]; then
    kernel_minor="$(uname -r | grep -oE '^[0-9]+\.[0-9]+')"
    DTB_SRC_DIR="/opt/source/dtb-${kernel_minor}.x"
fi

if [ ! -d "$DTB_SRC_DIR" ]; then
    echo "DTB source tree not found: $DTB_SRC_DIR" >&2
    echo "set DTB_SRC_DIR to the dtb-*.x directory matching \`uname -r\` ($(uname -r))" >&2
    exit 1
fi
echo "==> using DTB source tree: $DTB_SRC_DIR"

cp "$SCRIPT_DIR/overlays/$OVERLAY_NAME.dtso" "$DTB_SRC_DIR/src/arm64/overlays/"

echo "==> building overlay"
(cd "$DTB_SRC_DIR" && make "src/arm64/overlays/$OVERLAY_NAME.dtbo")

echo "==> installing to /boot/firmware/overlays/"
sudo cp "$DTB_SRC_DIR/src/arm64/overlays/$OVERLAY_NAME.dtbo" /boot/firmware/overlays/

echo "==> wiring it into the default extlinux boot label"
sudo python3 - "$EXTLINUX_CONF" "$OVERLAY_NAME" <<'PYEOF'
import re
import sys

conf_path, overlay_name = sys.argv[1], sys.argv[2]
overlay_line = f"/overlays/{overlay_name}.dtbo"

with open(conf_path) as f:
    lines = f.readlines()

m = re.search(r"^default\s+(.+)$", "".join(lines), re.MULTILINE)
if not m:
    sys.exit("no 'default' line found in " + conf_path)
default_label = m.group(1).strip()

label_re = re.compile(r"^label\s+" + re.escape(default_label) + r"\s*$")

start = None
for i, line in enumerate(lines):
    if label_re.match(line.strip()):
        start = i
        break
if start is None:
    sys.exit(f"default label '{default_label}' not found in {conf_path}")

end = len(lines)
for i in range(start + 1, len(lines)):
    if lines[i].strip() == "":
        end = i
        break

block = lines[start:end]
changed = False
found_active = False
for i, line in enumerate(block):
    stripped = line.strip()
    if stripped.startswith("fdtoverlays"):
        found_active = True
        if overlay_line not in stripped:
            block[i] = line.rstrip("\n") + " " + overlay_line + "\n"
            changed = True
        break
    if stripped.startswith("#fdtoverlays"):
        indent = line[: len(line) - len(line.lstrip())]
        block[i] = f"{indent}fdtoverlays {overlay_line}\n"
        found_active = True
        changed = True
        break

if not found_active:
    for i, line in enumerate(block):
        if line.strip().startswith("fdtdir"):
            indent = line[: len(line) - len(line.lstrip())]
            block.insert(i + 1, f"{indent}fdtoverlays {overlay_line}\n")
            changed = True
            break
    else:
        sys.exit("could not find where to insert fdtoverlays in label block")

if changed:
    lines[start:end] = block
    with open(conf_path, "w") as f:
        f.writelines(lines)
    print(f"updated: default label '{default_label}' now loads {overlay_line}")
else:
    print(f"already up to date: default label '{default_label}' already loads {overlay_line}")
PYEOF

echo "==> done. reboot to apply, then verify with:"
echo "    i2cdetect -y 1"
