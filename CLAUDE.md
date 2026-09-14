# light-desk

DIY light-desk controller for QLC+ (or similar), based on the PocketBeagle 2.
Repo is currently **documentation-only** (Markdown notes) — no application
code yet. Concept: sACN -> DMX via OLA, DMX out over UART; physical faders
(ADS7830 ADC) exposed as OSC via Python/CircuitPython/Blinka.

## Repo map
- `README.md` — project overview, system/HW list, DMX pinout
- `collection.md` — link dump (QLC+, DMX libs, PocketBeagle 2 docs, OSC, ADC)
- `ola.md`, `setup.md` — OLA install (build-from-source vs. `apt install ola`)
- `ola-pb2-crosscompile-handoff.md` — status/plan for cross-compiling current
  OLA master for the board (native on-device build is impractical: 512MB RAM)
- `olad.service` — systemd unit for olad, adapted from upstream
  `debian/ola.olad.service`, for a from-source build (`/usr/local/bin/olad`)
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
- Docs mix English (technical) with occasional German (e.g. DMX pinout table)
  — match whichever language a given doc already uses.
