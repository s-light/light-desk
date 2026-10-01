"""Shared setup/install helpers for both boards (setup_pb1.py,
setup_pb2.py) - the single place that knows *how* to do each kind of
system-level operation (compile+install an overlay, fill+install a
systemd unit, write a scoped sudoers rule, edit the bootloader config,
apply olad's config), so each board's entrypoint only has to say
*what* it needs, as a short sequence of calls into here.

Before this module existed, every one of these operations was
reimplemented per-script (in a mix of POSIX sh and Python, slightly
differently each time) across ~20 files. Consolidated at the user's
request for one consistent form and, ultimately, one setup command
per board.

Not a general-purpose library - every function here is exactly what
this project's own setup needs, no more. Import it as:

    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    import lightdesk_setup as ld
"""

import grp
import os
import pwd
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parent


# --- basics ------------------------------------------------------------

def require_root(prog):
    if os.geteuid() != 0:
        fail(f"must run as root, e.g.: sudo {prog}")


def require_non_root(prog):
    if os.geteuid() == 0:
        fail(f"run {prog} as your normal user, not root/sudo - it calls sudo itself")


def fail(message):
    print(message, file=sys.stderr)
    sys.exit(1)


def step(title):
    print(f"==> {title}")


def run(cmd, **kwargs):
    """subprocess.run with check=True by default and the command
    echoed first, matching every setup script's own "==> " style."""
    kwargs.setdefault("check", True)
    print(f"    $ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, **kwargs)


def invoking_user():
    """The user who ran `sudo` to get here, or the current user if
    not running under sudo at all - mirrors the `${SUDO_USER:-light}`
    pattern used throughout the old shell scripts, but without
    hardcoding "light" as the fallback; callers pass their own
    default."""
    return os.environ.get("SUDO_USER")


# --- users / groups / sudoers ------------------------------------------

def ensure_user(username, groups, copy_ssh_keys_from=None):
    """Create `username` (home + bash) if missing, add it to
    `groups`, and copy `copy_ssh_keys_from`'s authorized_keys if that
    user has one and isn't `username` itself. Does not set a
    password - the caller prompts for that separately (interactive,
    can't be made idempotent/non-interactive safely)."""
    require_root("ensure_user")
    try:
        pwd.getpwnam(username)
        print(f"    user {username!r} already exists, skipping creation")
    except KeyError:
        run(["useradd", "-m", "-s", "/bin/bash", username])

    run(["usermod", "-aG", ",".join(groups), username])

    new_home = Path(pwd.getpwnam(username).pw_dir)
    ssh_dir = new_home / ".ssh"
    ssh_dir.mkdir(mode=0o700, exist_ok=True)

    if copy_ssh_keys_from and copy_ssh_keys_from != username:
        src_keys = Path(pwd.getpwnam(copy_ssh_keys_from).pw_dir) / ".ssh" / "authorized_keys"
        dest_keys = ssh_dir / "authorized_keys"
        if src_keys.exists():
            dest_keys.write_bytes(src_keys.read_bytes())
            dest_keys.chmod(0o600)
        else:
            print(f"    no authorized_keys found for {copy_ssh_keys_from!r} - add one yourself later")

    uid, gid = pwd.getpwnam(username).pw_uid, pwd.getpwnam(username).pw_gid
    for root, dirs, files in os.walk(ssh_dir):
        for name in dirs + files:
            os.chown(Path(root) / name, uid, gid)
    os.chown(ssh_dir, uid, gid)


def ensure_group(name, system=True):
    try:
        grp.getgrnam(name)
        return
    except KeyError:
        pass
    require_root("ensure_group")
    cmd = ["groupadd"]
    if system:
        cmd.append("--system")
    cmd.append(name)
    run(cmd)


def add_nopasswd_sudoers(filename, user, rules):
    """Write /etc/sudoers.d/<filename> granting `user` NOPASSWD for
    exactly `rules` (a list of command patterns), validate with
    `visudo -c`, same scoped-rule convention this project has used
    from the start - never a blanket NOPASSWD."""
    require_root("add_nopasswd_sudoers")
    path = Path("/etc/sudoers.d") / filename
    rule = f"{user} ALL=(root) NOPASSWD: " + ", ".join(rules) + "\n"
    step(f"installing {path}")
    path.write_text(rule)
    path.chmod(0o440)
    step("validating sudoers syntax")
    run(["visudo", "-c"])


# --- i2c + lgpio + venv (identical on both boards) -------------------------

def setup_i2c_and_venv(username, venv_dir, requirements_path):
    """i2c group + udev rules (bus access + EEPROM nvmem readable for
    board auto-detection via adafruit-blinka), the lgpio C library
    (adafruit-blinka's dependency on generic Linux boards, not
    packaged for pip - neither Debian nor PyPI ship it, see
    https://github.com/joan2937/lg), and the Python venv. Identical
    on PB1/PB2, used by both entrypoints."""
    ensure_group("i2c")
    install_udev_rule(
        "/etc/udev/rules.d/60-light-desk-i2c.rules",
        'SUBSYSTEM=="i2c-dev", GROUP="i2c", MODE="0660"\n',
    )
    # the EEPROM's "nvmem" file is a bare sysfs attribute, not a /dev
    # node, so GROUP=/MODE= (udev's own device-node chmod) do nothing
    # here - RUN+= actively chmod/chgrp the sysfs file itself.
    install_udev_rule(
        "/etc/udev/rules.d/60-light-desk-eeprom.rules",
        'SUBSYSTEM=="nvmem", KERNEL=="0-0050*", '
        'RUN+="/bin/chgrp i2c /sys%p/nvmem", RUN+="/bin/chmod g+r /sys%p/nvmem"\n',
    )
    udevadm_reload_and_trigger(["i2c-dev", "nvmem"])
    run(["usermod", "-aG", "i2c", username])

    run(["apt-get", "install", "-y", "swig", "python3-dev", "build-essential"])
    if Path("/usr/local/lib/liblgpio.so").exists():
        print("    liblgpio.so already installed, skipping lgpio C library build")
    else:
        with tempfile.TemporaryDirectory() as build_dir:
            run(["git", "clone", "--depth", "1", "https://github.com/joan2937/lg.git", build_dir])
            run(["make", "-C", build_dir])
            run(["make", "-C", build_dir, "install"])
            run(["ldconfig"])

    ensure_venv(venv_dir, requirements_path)


# --- python venv ---------------------------------------------------------

def ensure_venv(venv_dir, requirements_path):
    venv_dir = Path(venv_dir)
    if (venv_dir / "bin" / "python3").exists():
        print(f"    venv already exists at {venv_dir}, skipping creation")
    else:
        step(f"creating venv: {venv_dir}")
        run([sys.executable, "-m", "venv", str(venv_dir)])
    run([str(venv_dir / "bin" / "pip"), "install", "--upgrade", "pip"], stdout=subprocess.DEVNULL)
    run([str(venv_dir / "bin" / "pip"), "install", "-r", str(requirements_path)])


# --- apt -----------------------------------------------------------------

def apt_install(*packages):
    require_root("apt_install")
    step("apt-get update")
    run(["apt-get", "update"])
    step(f"installing {', '.join(packages)}")
    run(["apt-get", "install", "-y", *packages])


# --- udev ------------------------------------------------------------------

def install_udev_rule(path, content):
    require_root("install_udev_rule")
    path = Path(path)
    step(f"installing udev rule: {path}")
    path.write_text(content)


def udevadm_reload_and_trigger(subsystems):
    run(["udevadm", "control", "--reload-rules"])
    for subsystem in subsystems:
        run(["udevadm", "trigger", "--action=add", f"--subsystem-match={subsystem}"])


# --- systemd units ----------------------------------------------------------

def install_systemd_unit(template_path, unit_name, substitutions, enable_now=False):
    """Fill __PLACEHOLDER__-style substitutions into a unit template
    and install it as /etc/systemd/system/<unit_name>, then
    daemon-reload (and enable --now if asked)."""
    require_root("install_systemd_unit")
    text = Path(template_path).read_text()
    for key, value in substitutions.items():
        text = text.replace(f"__{key}__", str(value))
    dest = Path("/etc/systemd/system") / unit_name
    step(f"installing {dest}")
    dest.write_text(text)
    run(["systemctl", "daemon-reload"])
    if enable_now:
        run(["systemctl", "enable", "--now", unit_name])


def is_unit_active(unit_name):
    result = subprocess.run(["systemctl", "is-active", "--quiet", unit_name])
    return result.returncode == 0


# --- device-tree overlays: PocketBeagle 1 (U-Boot uEnv.txt, dtc -@ direct) --

def compile_and_install_overlay_uboot(dts_path, overlay_name):
    """PB1-style: `dtc -@` compiles the overlay directly (no C
    preprocessor - this board's overlays use raw offset/flags/mode
    numbers for exactly that reason, see any overlays/BB-*.dts
    header), installed to /boot/dtbs/$(uname -r)/overlays/."""
    require_root("compile_and_install_overlay_uboot")
    kernel_ver = subprocess.run(["uname", "-r"], capture_output=True, text=True, check=True).stdout.strip()
    overlay_dir = Path(f"/boot/dtbs/{kernel_ver}/overlays")
    if not overlay_dir.is_dir():
        fail(f"overlays dir not found: {overlay_dir} (unexpected kernel/image layout)")

    with tempfile.NamedTemporaryFile(suffix=".dtbo") as tmp:
        step(f"compiling {overlay_name}.dts")
        run(["dtc", "-@", "-O", "dtb", "-o", tmp.name, "-b", "0", str(dts_path)])
        dest = overlay_dir / f"{overlay_name}.dtbo"
        step(f"installing to {dest}")
        dest.write_bytes(Path(tmp.name).read_bytes())
    return dest


def wire_overlays_into_uenv(overlay_dtbo_names, uenv_path="/boot/uEnv.txt"):
    """PB1-style: fill unused `#uboot_overlay_addrN=` slots in
    uEnv.txt with the given .dtbo filenames. Idempotent - skips
    overlays already wired to a slot, never touches slots already in
    use for something else."""
    require_root("wire_overlays_into_uenv")
    uenv_path = Path(uenv_path)
    lines = uenv_path.read_text().splitlines(keepends=True)

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
    for overlay in overlay_dtbo_names:
        if overlay in used_slots:
            print(f"    already wired: {overlay} (slot {used_slots[overlay][1]})")
            continue
        if not free_slots:
            fail(f"no free uboot_overlay_addrN slot left for {overlay}")
        i, slot = free_slots.pop(0)
        lines[i] = f"uboot_overlay_addr{slot}={overlay}\n"
        used_slots[overlay] = (i, slot)
        changed = True
        print(f"    wired: {overlay} -> uboot_overlay_addr{slot}")

    if changed:
        uenv_path.write_text("".join(lines))
    else:
        print("    no changes needed")


# --- device-tree overlays: PocketBeagle 2 (extlinux, full dtb-tree build) --

def compile_and_install_overlay_extlinux(dtso_path, overlay_name, dtb_src_dir=None):
    """PB2-style: copies the .dtso into the full kernel DTB source
    tree under /opt/source/dtb-X.Y.x and builds it with `make`
    (unlike PB1, this board's overlays DO use the C
    preprocessor/AM33XX_PADCONF-style macros, so they need the real
    build tree, not a bare `dtc -@`), installed to
    /boot/firmware/overlays/."""
    require_non_root("compile_and_install_overlay_extlinux (run as your normal user - it calls sudo itself for the install step)")
    if dtb_src_dir is None:
        kernel_minor = re.match(r"^(\d+\.\d+)", subprocess.run(["uname", "-r"], capture_output=True, text=True, check=True).stdout).group(1)
        dtb_src_dir = Path(f"/opt/source/dtb-{kernel_minor}.x")
    else:
        dtb_src_dir = Path(dtb_src_dir)

    if not dtb_src_dir.is_dir():
        fail(f"DTB source tree not found: {dtb_src_dir} - pass dtb_src_dir= explicitly if it's named differently")
    step(f"using DTB source tree: {dtb_src_dir}")

    overlays_src = dtb_src_dir / "src" / "arm64" / "overlays"
    dest_dtso = overlays_src / f"{overlay_name}.dtso"
    dest_dtso.write_bytes(Path(dtso_path).read_bytes())

    step("building overlay")
    run(["make", f"src/arm64/overlays/{overlay_name}.dtbo"], cwd=dtb_src_dir)

    built = overlays_src / f"{overlay_name}.dtbo"
    dest = Path("/boot/firmware/overlays") / f"{overlay_name}.dtbo"
    step(f"installing to {dest}")
    run(["sudo", "cp", str(built), str(dest)])
    return dest


def wire_overlay_into_extlinux(overlay_name, extlinux_conf="/boot/firmware/extlinux/extlinux.conf"):
    """PB2-style: add `fdtoverlays /overlays/<name>.dtbo` to the
    default extlinux label's block, or append it to an existing
    fdtoverlays line. Idempotent."""
    extlinux_conf = Path(extlinux_conf)
    overlay_line = f"/overlays/{overlay_name}.dtbo"

    lines = extlinux_conf.read_text().splitlines(keepends=True)

    m = re.search(r"^default\s+(.+)$", "".join(lines), re.MULTILINE)
    if not m:
        fail(f"no 'default' line found in {extlinux_conf}")
    default_label = m.group(1).strip()

    label_re = re.compile(r"^label\s+" + re.escape(default_label) + r"\s*$")
    start = next((i for i, line in enumerate(lines) if label_re.match(line.strip())), None)
    if start is None:
        fail(f"default label '{default_label}' not found in {extlinux_conf}")

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
            fail("could not find where to insert fdtoverlays in label block")

    if changed:
        lines[start:end] = block
        run(["sudo", "tee", str(extlinux_conf)], input="".join(lines), text=True, stdout=subprocess.DEVNULL)
        print(f"    updated: default label '{default_label}' now loads {overlay_line}")
    else:
        print(f"    already up to date: default label '{default_label}' already loads {overlay_line}")


# --- OLA config -------------------------------------------------------------

# Every plugin olad ships, minus e131/uartdmx/dummy (those get
# explicitly enabled by apply_ola_config). Source of truth:
# https://docs.openlighting.org/ola/conf/
_OLA_DISABLED_PLUGINS = [
    "artnet", "dmx4linux", "espnet", "ftdidmx", "gpio", "karate", "kinet",
    "milinst", "nanoleaf", "opendmx", "openpixelcontrol", "osc", "pathport",
    "renard", "sandnet", "shownet", "spi", "spidmx", "stageprofi", "usbdmx",
    "usbserial",
]


def apply_ola_config(config_src, num_universes, config_dir="/etc/ola", extra_enabled_plugins=()):
    """Install olad config: e131 (num_universes input ports) +
    uartdmx + dummy enabled, every other plugin explicitly disabled,
    plus whatever's in extra_enabled_plugins (e.g. PB1's "spi") -
    each of those gets `enabled = true` and, if
    config_src/ola-<plugin>.conf exists, that file installed too.
    Also fixes olad's HTTP port (9090 collides with Cockpit on this
    image) and restarts olad.service if it's installed."""
    require_root("apply_ola_config")
    config_src = Path(config_src)
    config_dir = Path(config_dir)
    step(f"config dir: {config_dir} (source: {config_src}, {num_universes} universes)")
    config_dir.mkdir(parents=True, exist_ok=True)

    for plugin in _OLA_DISABLED_PLUGINS:
        (config_dir / f"ola-{plugin}.conf").write_text("enabled = false\n")
    print(f"    disabled {len(_OLA_DISABLED_PLUGINS)} unused plugins")

    (config_dir / "ola-e131.conf").write_bytes((config_src / "ola-e131.conf").read_bytes())
    (config_dir / "ola-uartdmx.conf").write_bytes((config_src / "ola-uartdmx.conf").read_bytes())
    (config_dir / "ola-dummy.conf").write_text("enabled = true\n")
    print("    installed ola-e131.conf, ola-uartdmx.conf, ola-dummy.conf")

    for plugin in extra_enabled_plugins:
        extra_conf = config_src / f"ola-{plugin}.conf"
        if extra_conf.exists():
            (config_dir / f"ola-{plugin}.conf").write_bytes(extra_conf.read_bytes())
            print(f"    re-enabled + installed ola-{plugin}.conf")
        else:
            (config_dir / f"ola-{plugin}.conf").write_text("enabled = true\n")
            print(f"    re-enabled ola-{plugin}.conf (no {extra_conf} to install - plugin defaults apply)")

    try:
        import pwd as _pwd
        olad_uid, olad_gid = _pwd.getpwnam("olad").pw_uid, _pwd.getpwnam("olad").pw_gid
        for root, dirs, files in os.walk(config_dir):
            for name in dirs + files:
                os.chown(Path(root) / name, olad_uid, olad_gid)
        os.chown(config_dir, olad_uid, olad_gid)
    except KeyError:
        pass

    # olad 0.10.9's HTTP UI defaults to port 9090, which collides with
    # Cockpit on this image; a failed bind there is fatal (kills the
    # whole daemon, LSB init script still reports "active" regardless).
    default_ola = Path("/etc/default/ola")
    if default_ola.exists() or Path("/etc/init.d/olad").exists():
        step("setting olad HTTP UI port to 9091 (9090 is Cockpit) via /etc/default/ola")
        default_ola.write_text(f'DAEMON_ARGS="--syslog --log-level 3 --config-dir {config_dir} --http-port 9091"\n')

    result = subprocess.run(["systemctl", "list-unit-files", "olad.service"], capture_output=True)
    if result.returncode == 0:
        step("restarting olad.service")
        run(["systemctl", "restart", "olad.service"])
        import time
        time.sleep(2)
        return True
    else:
        print("!! olad.service not installed - start olad manually, then patch universes by hand", file=sys.stderr)
        return False


def patch_sacn_to_uart(num_universes, e131_device=2, uartdmx_device_start=3):
    """Patch sACN input ports 0..num_universes-1 to universes
    1..num_universes, and each uartdmx device (aliases
    uartdmx_device_start..+num_universes-1) to the same universes -
    see any of the old patch-sacn-to-uart.sh headers for the full
    "why" (device aliasing isn't a documented guarantee, etc)."""
    for i in range(num_universes):
        universe = i + 1
        uartdmx_device = uartdmx_device_start + i
        run(["ola_patch", "-d", str(e131_device), "-p", str(i), "-i", "-u", str(universe)])
        run(["ola_patch", "-d", str(uartdmx_device), "-p", "0", "-u", str(universe)])
        print(f"    universe {universe}: e131 in port {i} -> uartdmx device {uartdmx_device} port 0")


def patch_spi_apa102(e131_device, spi_device, spi_universe):
    e131_port = spi_universe - 1
    run(["ola_patch", "-d", str(e131_device), "-p", str(e131_port), "-i", "-u", str(spi_universe)])
    run(["ola_patch", "-d", str(spi_device), "-p", "0", "-u", str(spi_universe)])
    print(f"    universe {spi_universe}: e131 in port {e131_port} -> spi device {spi_device} port 0")
