# light-desk

DIY light-desk controller for QLC+ (or similar), based on the PocketBeagle 2.
Concept: sACN -> DMX via OLA, DMX out over UART; physical faders (ADS7830
ADC) exposed as OSC via Python/CircuitPython/Blinka.

## Repo map
- `README.md` — project overview, system/HW list, DMX pinout
- `collection.md` — link dump (QLC+, DMX libs, PocketBeagle 2 docs, OSC, ADC)
- `ola.md`, `setup.md` — OLA install (build-from-source vs. `apt install ola`)
- `ola-pb2-crosscompile-handoff.md` — status/plan for cross-compiling current
  OLA master for the board (native on-device build is impractical: 512MB RAM)
- `olad.service` — systemd unit for olad, adapted from upstream
  `debian/ola.olad.service`, for a from-source build (`/usr/local/bin/olad`).
  **Not currently used on the real board** - it runs the `apt install ola`
  package (0.10.9), managed by its own `/etc/init.d/olad` LSB script; this
  unit is for whenever the cross-compiled newer OLA lands, see the
  crosscompile handoff doc
- `overlays/k3-am62-pocketbeagle2-light-desk-uart-dmx.dtso` — device-tree
  overlay pin-muxing uart1/3/4/5 to header pins for DMX output (uart0 needs
  no overlay, already enabled by the stock base DTS). uart2 has no pin-mux
  entry anywhere on this board (not routable at all) and uart6 is the
  console/debug-probe UART - so 5 DMX outputs is the real ceiling here,
  not 6
- `install-uart-overlay.sh` — builds the overlay above using the DTB
  source/build tree the board image ships under `/opt/source/dtb-*.x`,
  installs the `.dtbo`, and wires it into whichever extlinux label is
  currently `default` (idempotent, doesn't touch other labels). Does not
  reboot - needed once, then reboot manually and re-run
  `apply-ola-config.sh`
- `scripts/ads7830_to_osc.py` — reads the ADS7830 fader ADC via Blinka, sends
  each channel as OSC float `/fader/N` (N=1-8) to QLC+; see
  `scripts/requirements.txt` for the Python deps (`adafruit-blinka`,
  `adafruit-extended-bus`, `adafruit-circuitpython-ads7830`, `python-osc`).
  Uses `adafruit_extended_bus.ExtendedI2C` instead of `board.I2C()` — Blinka
  has no PocketBeagle 2 board support yet, see setup.md "known issues"
- `ads7830-to-osc.service` — systemd unit template for the script above
  (placeholders filled in by `setup-i2c.sh`, not meant to be copied by hand)
- `setup-i2c.sh` — one-shot board setup for the fader->OSC bridge: i2c group
  + udev rule so `/dev/i2c-*` doesn't need root, a venv in `scripts/.venv`
  with `scripts/requirements.txt` installed into it (Debian 13's system
  Python is PEP-668-locked), then installs+enables
  `ads7830-to-osc.service`. Mirrors `setup.sh`/`apply-ola-config.sh`'s
  style (POSIX sh, idempotent, run as normal user - it calls sudo itself)
- `setup.md` — board bring-up steps: clone, install/configure ola, ADS7830
  HW wiring, the Blinka/PocketBeagle 2 "known issues" workaround, and
  running `setup-i2c.sh`
- `setup-readonly-root.sh` — final board-lockdown step, run once
  everything else is stable: disables the stock image's unused
  docker/containerd, points journald at volatile storage, and makes root
  read-only via `/etc/fstab` (not `overlayroot` - see the script header
  for why that doesn't work on this board's U-Boot/extlinux setup)
- `readwrite.sh`, `readonly.sh` — after `setup-readonly-root.sh`, root is
  read-only, so any on-board file change (git pull, deploying a script)
  needs `./readwrite.sh` first and `./readonly.sh` after - both are one
  `mount -o remount` call each, kept as separate scripts so nobody has to
  remember the exact `mount` invocation under pressure
- `setup.sh` — run once per board, first: installs a scoped
  `/etc/sudoers.d/light-desk-ola` NOPASSWD rule (systemctl/journalctl for
  olad, plus running `apply-ola-config.sh`) so the rest of setup doesn't
  need an interactive sudo password each time
- `apply-ola-config.sh` — one-shot board setup: disables every olad plugin
  except e131/uartdmx/dummy, installs the configs below, moves olad's HTTP
  UI to port 9091 (see "known board quirks" below), restarts olad, runs
  the port patching. Run this after `setup.sh`.
- `ola-config/` — olad plugin configs + patch script implementing the
  README's "sACN in -> UART out" bridge, 5 universes (see the overlay
  entry above for why 5, not 6): `ola-e131.conf` (5 sACN input ports),
  `ola-uartdmx.conf` (5 UART output devices - `/dev/ttyS1`, `ttyS3`,
  `ttyS4`, `ttyS5`, `ttyS7`, verified on real hardware),
  `patch-sacn-to-uart.sh` (one-time `ola_patch` call mapping universes 1-5
  straight through input->output; device aliases assumed there are only
  correct when `apply-ola-config.sh`'s reduced plugin set is active)
- `pb1_internet_share.md`, `pocketbeagle2-internet-sharing.md` — near-duplicate
  guides for sharing host internet to the board over USB (NetworkManager +
  systemd-networkd); differ only in IP subnet / board identity — check which
  board you're on before following one

## Known board quirks
- **olad 0.10.9 dies silently if its HTTP UI can't bind port 9090** (fatal,
  not just "no web UI") - and 9090 is also Cockpit's port on the stock
  BeagleBoard Debian image, so a plain `apt install ola` + default config
  never actually stays running. Its LSB init script still reports
  `systemctl status` as "active" regardless (`Type=forking`,
  `RemainAfterExit=yes`, no real PID tracking) - status alone doesn't tell
  you olad is actually alive; check `ola_dev_info`/`ola_plugin_info` or
  `ps -ef | grep olad`. `apply-ola-config.sh` fixes this via
  `/etc/default/ola`'s `DAEMON_ARGS` (`--http-port 9091`).
- The board (hostname `lightdeskniilo`) is reachable as `ssh pb_lightdesk`;
  login user `light` needs a password for `sudo` unless `setup.sh` has
  been run.
- **This board's U-Boot/extlinux setup cannot load an initrd correctly.**
  Enabling `initrd /initrd.img` on any extlinux.conf label (confirmed on
  the "microSD (default)" label) causes a kernel panic on boot -
  `Failed to execute /init (error -2)` - even though the initrd file
  itself is intact on disk (verified by checksum). This is why every
  stock label ships with `initrd` commented out, and why `overlayroot`
  (which needs an initrd) doesn't work here; `setup-readonly-root.sh`
  uses a plain fstab-based read-only root instead. If this ever needs
  revisiting, it means debugging U-Boot's initrd loading at the actual
  U-Boot prompt (serial console, before extlinux even runs) - do that
  deliberately, with a full SD card image backup first, not as a
  follow-on to something else; a bad extlinux.conf label previously left
  the board needing serial-console recovery to the "microSD (failsafe)"
  label.

## Target hardware
- PocketBeagle 2 (AM6254, quad-core A53, **512MB RAM** — this is why native
  on-board builds of anything nontrivial are slow/swap-bound; prefer
  cross-compiling or QEMU-chroot on a dev machine, see the crosscompile doc)
- OS: Debian 13 "trixie" arm64 (plain userland, not Yocto-specific)

## Working conventions
- User handles all git commits themselves — don't commit unless explicitly
  asked.
- No `gh` CLI available in this environment; use WebSearch/WebFetch for
  GitHub content (issues, gists, raw files) instead.
- Docs are English-only — translate any German that creeps back in.
