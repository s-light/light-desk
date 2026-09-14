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
  `debian/ola.olad.service`, for a from-source build (`/usr/local/bin/olad`)
- `scripts/ads7830_to_osc.py` — reads the ADS7830 fader ADC via Blinka, sends
  each channel as OSC float `/fader/N` (N=1-8) to QLC+; see
  `scripts/requirements.txt` for the Python deps (`adafruit-blinka`,
  `adafruit-extended-bus`, `adafruit-circuitpython-ads7830`, `python-osc`).
  Uses `adafruit_extended_bus.ExtendedI2C` instead of `board.I2C()` — Blinka
  has no PocketBeagle 2 board support yet, see setup.md "known issues"
- `setup.md` — board bring-up steps: clone, install/configure ola, ADS7830
  HW wiring, and the Blinka/PocketBeagle 2 "known issues" workaround
- `setup.sh` — run once per board, first: installs a scoped
  `/etc/sudoers.d/light-desk-ola` NOPASSWD rule (systemctl/journalctl for
  olad, plus running `apply-ola-config.sh`) so the rest of setup doesn't
  need an interactive sudo password each time
- `apply-ola-config.sh` — one-shot board setup: disables every olad plugin
  except e131/uartdmx/dummy, installs the configs below, restarts olad,
  runs the port patching. Run this on the board after `olad.service` is
  installed.
- `ola-config/` — olad plugin configs + patch script implementing the
  README's "6 sACN in -> 6 UART out" bridge: `ola-e131.conf` (6 sACN input
  ports), `ola-uartdmx.conf` (6 UART output devices, **placeholder
  `/dev/ttyS1..6` paths need verifying against actual PB2 overlays**),
  `patch-sacn-to-uart.sh` (one-time `ola_patch` call mapping universes 1-6
  straight through input->output; device aliases assumed there are only
  correct when `apply-ola-config.sh`'s reduced plugin set is active)
- `pb1_internet_share.md`, `pocketbeagle2-internet-sharing.md` — near-duplicate
  guides for sharing host internet to the board over USB (NetworkManager +
  systemd-networkd); differ only in IP subnet / board identity — check which
  board you're on before following one

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
