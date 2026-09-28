# PB1 bring-up: current state (2026-09-17)

Work session paused mid-way with the board unreachable after a reboot.
This is a memo to resume from, not finished documentation - `setup.md`
for PB1 hasn't been written yet, deliberately, since the overlay
approach below isn't confirmed working end-to-end yet.

## What's done and confirmed working (on the live board, before the reboot)

All of this ran successfully over SSH, in order, on the real PB1
(`am335x-debian-13.6-base-v6.18-armhf-2026-07-24-4gb.img.xz`, hostname
reachable as `pb_6ch`):

1. `pb1/setup.sh` - created the `light` user (uid 1001), added it to
   `sudo,dialout,i2c,gpio`, copied SSH `authorized_keys`, installed a
   scoped NOPASSWD sudoers rule
   (`/etc/sudoers.d/light-desk-pb1`) covering exactly
   `install-uart3-overlay.sh`, `apply-uenv-overlays.sh`,
   `switch-console-to-usb.sh`. Verified with `visudo -c`.
   - Hit and fixed one real bug: re-running it *as* `light` (not
     `debian`) made the `cp authorized_keys` step fail (src==dst) and
     abort the whole script under `set -eu` before reaching the sudoers
     install. Fixed by skipping the copy when invoking user == new user.
     This fix is applied locally but **not yet committed** (see below).
2. `pb1/install-uart3-overlay.sh` - compiled
   `pb1/overlays/BB-UART3-light-desk-00A0.dts` with `dtc -@ -O dtb -b 0`
   and installed the resulting `.dtbo` to
   `/boot/dtbs/6.18.39-bone44/overlays/`. Compiled clean, fixups
   resolved correctly (`am33xx_pinmux`, `uart3`).
   - Hit and fixed one real bug: original version wrote to a fixed
     `/tmp/BB-UART3-light-desk-00A0.dtbo` path, which collided with a
     leftover file from manual testing earlier in the session (owned by
     `debian`, unwritable by the `light`-invoked root helper in this
     environment) and failed with "Permission denied". Fixed with
     `mktemp`. This fix is applied locally but **not yet committed**.
3. `pb1/apply-uenv-overlays.sh` - wired all 4 needed overlays into
   `/boot/uEnv.txt`'s `uboot_overlay_addr0-3` slots:
   - `uboot_overlay_addr0=BB-UART1-00A0.dtbo` (stock)
   - `uboot_overlay_addr1=BB-UART2-00A0.dtbo` (stock)
   - `uboot_overlay_addr2=BB-I2C1-00A0.dtbo` (stock)
   - `uboot_overlay_addr3=BB-UART3-light-desk-00A0.dtbo` (ours, custom)
4. `pb1/switch-console-to-usb.sh` - disabled
   `serial-getty@ttyS0.service`, confirmed `serial-getty@ttyGS0.service`
   enabled (it already was, by default, on this image), changed
   `console=ttyS0,115200n8` to `console=ttyGS0,115200n8` in
   `/boot/uEnv.txt`.

All four steps reported success with no errors. UART4 (P2.05/P2.07)
needs no overlay at all - confirmed already `status = "okay"` with a
pinctrl group assigned in the stock `am335x-pocketbeagle.dtb`, verified
by decompiling it live on the board before writing anything.

## What broke: reboot hang

`sudo reboot` was run (by the user, interactively - the NOPASSWD rule
deliberately doesn't cover `reboot`). The board never came back:

- No SSH, ever (`ssh: connect ... Connection timed out`), for 10+
  minutes across two attempts (one right after reboot, one after a full
  USB unplug/replug power cycle).
- Host-side USB network interface for the board's IP (`192.168.17.2`)
  disappeared entirely after the reboot - it's a Linux-side gadget
  driver, so this means the kernel never got that far.
- LED pattern on power-cycle: all 4 on briefly -> two blinking -> **USR3
  static on, no further activity**. No USR0 heartbeat ever started. This
  points at a hang before Linux reaches normal multi-user boot - either
  stuck in U-Boot applying one of the 4 overlays, or stuck very early in
  the kernel.

Leading suspect: `BB-UART3-light-desk-00A0.dtbo` (the only *custom*
overlay of the 4 - the other 3 are TI/bb.org-overlays' own shipped,
presumably-well-tested overlays). It compiled clean with `dtc` and its
fixups resolved against the live `__symbols__` table, but that only
proves `dtc` accepted it - it was never actually tested by handing it to
U-Boot's own fdt-overlay-apply code before this reboot. That code can be
pickier than `dtc -@` about fragment shape than a first-principles
overlay author (me) would know to expect.

Runner-up suspect: the `console=ttyGS0` change interacting badly with
whatever script/unit brings up the USB gadget's *network* function
(`g_ether`/composite gadget) - unconfirmed, and less likely, since the
gadget's serial (`ttyGS0`) and network (`usb0`) functions are normally
independent gadget functions, not coupled to the kernel `console=`
argument. Noted here so it isn't lost, not because it's the favored
theory.

**Not** a suspect: the sudoers/user-creation work (step 1) - that's
pure userland config, nothing there touches boot.

## SD card inspection (in progress, paused)

Pulled the card, read via a USB card reader on the dev machine
(`/dev/sda1`, auto-mounted read-only at
`/run/media/stefan/BOOT`). Findings:

- Partition table: `sda1` 256M vfat `BOOT`, `sda2` 1G swap, `sda3` 6G
  ext4 `rootfs`. Card is 14.8G total; ~7.5G unpartitioned beyond `sda3`
  (unexplained, not yet investigated - could be normal for how
  `bb-imager`/`dd` wrote this image, or could be a remnant of an earlier,
  larger image).
- The **content** of `sda1` looks wrong for a PB1 (am335x/BeagleBone)
  image: it has `tiboot3.bin`/`tispl.bin` and an `extlinux/` directory,
  which is the K3/AM62 (PocketBeagle **2**) boot layout, not the
  `MLO`/`u-boot.img`/`uEnv.txt` layout we were editing live over SSH
  minutes earlier on this same card.
- Stronger signal than "wrong image": likely **filesystem corruption**,
  not just stale/leftover files. The OS auto-mounted `sda1` **read-only**
  (a common automatic fallback when a dirty/damaged FAT volume is
  detected), `ls -la` returns unstat-able `d?????????` entries for
  `extlinux/`, `overlays/`, `services/`, `ti/`, and both `ID.txt` and
  `sysconf.txt` return garbled/binary content instead of the plain text
  they should be. `sysconf.txt`'s garbage did contain readable
  `armhf`/`bbb.io-kernel-tasks` substrings though, which *is* consistent
  with a PB1 (armhf) image being in there somewhere, cross-linked or
  overwritten - fits the user's own theory that this card was flashed
  with a PB2 image first and a PB1 image later, and something about
  that history (or the ungraceful `reboot`) left the FAT filesystem in a
  bad state.
- `sda3` (the ext4 rootfs) has **not** been checked yet for corruption -
  open question.

**Nothing destructive has been run.** The proposed next step - `sudo
fsck.vfat -a /dev/sda1` after unmounting it - was proposed but explicitly
**not executed**, pending the user's go-ahead and available time.

## Repo state

- `pb1/setup.sh`, `pb1/install-uart3-overlay.sh` have local uncommitted
  fixes (see bugs above) - `git diff --stat` shows both modified, not
  yet committed. The user commits themselves (per repo CLAUDE.md
  convention) - not committed on their behalf.
- `pb1/apply-uenv-overlays.sh`, `pb1/switch-console-to-usb.sh`,
  `pb1/overlays/BB-UART3-light-desk-00A0.dts` are unchanged from the
  "prepare pb1" commit (`ce89b55`) and worked as committed.
- `pb1/setup.md` does not exist yet - intentionally deferred until the
  overlay/boot approach is confirmed to actually boot.

## Suggested next steps, whenever this resumes

1. Decide: repair (`fsck.vfat -a /dev/sda1`) vs. reflash-and-redo. If the
   original PB1 image file is still around, reflashing fresh and
   re-running just `pb1/setup.sh` + `apply-uenv-overlays.sh` +
   `switch-console-to-usb.sh` again is probably faster and less risky
   than trusting a repaired-but-previously-corrupted card long-term.
2. Once booting again: before touching `console=` or the custom UART3
   overlay again, get a way to see actual boot output - either a
   USB-to-3.3V-serial adapter on P1.30(TX)/P1.32(RX)/GND (this is
   UART0, still untouched at that point) to watch U-Boot + kernel
   messages directly, or add each overlay one at a time with a reboot
   + verify in between, stock ones first:
   - reboot with just `BB-UART1-00A0.dtbo` wired -> confirm it still
     boots and `/dev/ttyS1` appears
   - add `BB-UART2-00A0.dtbo` -> reboot -> confirm
   - add `BB-I2C1-00A0.dtbo` -> reboot -> confirm
   - add `BB-UART3-light-desk-00A0.dtbo` (the untested custom one) ->
     reboot -> **this is the one to watch**
   - only then apply `switch-console-to-usb.sh` separately, as its own
     reboot, so a console-related failure isn't conflated with an
     overlay-related one
3. If the custom UART3 overlay turns out to be the culprit, the likely
   fix is restructuring it closer to how the stock `BB-UART1-00A0.dtbo`
   is shaped (it disables an unrelated `P9_xx_pinmux` node in a separate
   fragment before the pinmux-group fragment - copied from BBB, harmless
   there since the symbol doesn't resolve on PB1, but maybe U-Boot's
   overlay code wants that fragment shape/ordering present regardless).
   Decompile `BB-UART1-00A0.dtbo` again for the exact fragment structure
   to imitate.
4. Once a boot is confirmed stable with all 4 overlays + console switch:
   verify `/dev/ttyS1`, `/dev/ttyS2`, `/dev/ttyS3`, `/dev/ttyS0` (freed),
   `i2cdetect -y 1` (ADS7830 at 0x48-0x4b), `systemctl is-active
   serial-getty@ttyGS0` - then write `pb1/setup.md`.

## Update (2026-09-26)

Card was reflashed fresh (the corrupted-FAT card from the previous
session is set aside, untouched). Progress since:

- `pb1/setup.sh`'s job was already done via the SD card's first-boot
  sysconf/env-file mechanism (`light` user + groups came up correctly on
  first boot) - ran it anyway is unnecessary now, skipped.
- Wired only the 3 **stock** overlays (`BB-UART1-00A0`, `BB-UART2-00A0`,
  `BB-I2C1-00A0`) into `uEnv.txt` by hand, deliberately leaving the
  custom `BB-UART3-light-desk-00A0.dtbo` out, and rebooted - **survived**.
  `/dev/ttyS1`, `/dev/ttyS2`, `/dev/i2c-1` all present.
- Confirmed via `/sys/kernel/debug/pinctrl/...` that `BB-I2C1-00A0`
  really routes I2C1 to `spi0_cs0`/`spi0_d1`, i.e. header pins
  **P1.06/P1.12** - not P1.33/P1.36 (that's PocketBeagle **2**'s I2C1
  pinout, mistakenly assumed at first) and not P2.09/P2.11 either (that
  pin pair does carry an I2C1_SCL/SDA alt-function on the AM335x, but
  it's the `uart1_txd`/`uart1_rxd` pins, already claimed by UART1 for
  universe 1 in this project's overlay set).
- ADS7830 was initially wired to P2.09/P2.11 (per the official PocketBeagle
  pinout table, which does list an I2C1 alt-function there) and failed
  with `i2cget: Error: Read failed` - expected, since that pin pair is
  electrically UART1 in our config, not I2C1. Rewired to P1.06/P1.12 -
  **confirmed working**, `i2cget -y 1 0x48` reads back a value.
- Added `pb1/setup.sh`... er, `pb1/setup.md` (HW pinout + DMX universe/
  overlay pin map, confirmed parts only) and `pb1/install-packages.sh`
  (`ola` + `i2c-tools` via apt, doesn't chain into `apply-ola-config.sh`
  yet - see that script's own header comment for why).

Next steps (continuing from item 2 above, which is now partially done):

5. ~~Add `BB-UART3-light-desk-00A0.dtbo`~~ **Done, confirmed working.**
   Built + installed via `install-uart3-overlay.sh`, wired via
   `apply-uenv-overlays.sh`, rebooted - survived cleanly, `/dev/ttyS3`
   present alongside `ttyS1`/`ttyS2`/`i2c-1`. So item 3's "custom overlay
   might need restructuring" theory was moot - **the custom overlay was
   never the problem**; the earlier hang was the corrupted SD card from
   the previous session, now set aside. Console still untouched
   (`ttyS0`).
6. Apply `switch-console-to-usb.sh` as its own separate reboot (item 2's
   last bullet, still applies) - **attempted, reverted, see below.**

## Update (2026-09-27): console-to-USB switch hangs the board

Ran `switch-console-to-usb.sh` + reboot (item 6). Board went completely
unreachable - no SSH, no ping to `192.168.17.2`, static LEDs (no
heartbeat), for 2+ minutes, reproduced identically on a second
power-cycle. Root-caused via serial (which stayed on UART0/`ttyS0`
throughout - `switch-console-to-usb.sh` only changes the *Linux*
`console=`, U-Boot's own serial console is separate and unaffected):

- U-Boot boots cleanly every time, loads all 4 overlays fine (the
  custom UART3 one still isn't found under this kernel's overlay dir -
  see the kernel-version note below - but that's non-fatal, boot
  continues past it regardless of console= value).
- With `console=ttyGS0`: **zero** bytes appear on the serial terminal
  after `Starting kernel ...` - not even early kernel decompression
  lines.
- With `console=ttyS0` (reverted): the same boot prints
  `[    0.000000] Malformed early option 'earlycon'` - the bare
  `earlycon` kernel arg (no explicit device/address) is rejected by
  this kernel version and produces no output at all. This fully
  explains the ttyGS0 silence: nothing before the real console
  registers is visible either way, and `ttyGS0` doesn't exist as a
  device until `bb-usb-gadgets.service` creates it via configfs, likely
  well into boot.
- `bb-usb-gadgets.service` (stock, sets up the `g_multi` composite
  gadget - ncm+acm+rndis - via configfs, and itself explicitly runs
  `systemctl start serial-getty@ttyGS0.service` as its last step, not a
  normal unit dependency) completed in ~15s on the `console=ttyS0` boot,
  with `usb0` (192.168.17.2) and `ttyGS0` both coming up fine. 15s is
  nowhere near the 2+ minutes of total unreachability seen with
  `console=ttyGS0` - so this isn't just "the gadget is slow", something
  about naming `ttyGS0` as *the* console specifically prevents this from
  completing (or from being visible) within any reasonable time.
  Leading theory: a boot-ordering chicken-and-egg problem - something
  early in boot implicitly wants "the console" ready before letting
  other units proceed, but the requested console (`ttyGS0`) is itself
  only created by a service that runs later. Not confirmed.

**Recovery was non-destructive this time** (unlike the SD-card
corruption incident) - just pulled the card, mounted the FAT boot
partition on a reader, and reverted `console=ttyGS0` back to
`console=ttyS0` in `/boot/uEnv.txt`. No need to re-enable
`serial-getty@ttyS0.service` for this to work - systemd auto-starts a
getty on whatever tty `console=` names, independent of that service's
enabled/disabled state (confirmed: `ttyGS0`'s getty was "active" but
never "enabled" either, started imperatively by
`bb-usb-gadgets.service` instead).

**Current state: reverted to `console=ttyS0`, confirmed working again**
- universes 1-3 (`ttyS1`/`ttyS2`/`ttyS3`) + I2C1 fader all still fine,
  `usb0`/SSH/`ttyGS0` all working normally with `ttyS0` also active as
  console. Universe 5 (freeing UART0) is **not** wired up - deferred.

Next step, for a future session - don't just retry the same swap blind:
set **both** consoles at once
(`console=ttyS0,115200n8 console=ttyGS0,115200n8`) instead of replacing
one with the other. Keeps full serial visibility throughout boot no
matter what the gadget does, so a repeat hang would actually be visible
this time, while still proving out whether `ttyGS0` reliably comes up.
Only drop `ttyS0` from `console=` once that's proven solid.

Separately (unrelated, non-blocking): the custom UART3 overlay is
still only installed under `/boot/dtbs/6.18.39-bone44/overlays/` - the
board is now running `6.18.53-bone55` (an apt-triggered kernel update
happened between sessions, unrelated to anything here). U-Boot's
"unable to find" for it is non-fatal, but universe 3 silently isn't
configured on the current kernel until `install-uart3-overlay.sh` is
re-run to install it under the new kernel's overlay directory too.

**Fixed**: re-ran `install-uart3-overlay.sh` under `6.18.53-bone55`,
rebooted with a full serial capture start-to-finish. Confirmed via
`dmesg`: `481a6000.serial: ttyS3` is a real DT-probed device now (not
the phantom port from before) - universe 3 restored. All 4
UARTs + I2C1 verified against real dmesg MMIO lines, not just
`/dev/ttySN` presence: `ttyS1`=`48022000`, `ttyS2`=`48024000`,
`ttyS3`=`481a6000`, `ttyS4`=`481a8000`, `i2c-1`=`4802a000`.

This boot's full log also sharpens the console-switch hang theory
above: total time from `Starting kernel ...` to SSH/`ttyGS0` getty
ready was only **~45-53 seconds** here (`bb-usb-gadgets.service`,
`network-online.target`, `getty.target` all reached by then), *despite*
the same `VBUS_ERROR in a_wait_vrise (...SessEnd)` retries and a `usb
usb2-port1: over-current condition` warning also present in this dmesg.
That's well under the 2+ minutes of total silence seen twice with
`console=ttyGS0` - so that hang wasn't just "the gadget is slow, be
patient", it was genuinely anomalous. The recurring `VBUS_ERROR`/
over-current messages are themselves worth a look before retrying -
could point to a marginal USB cable or port on the host side, separate
from the console-switch question. Try a different cable/direct port
(no hub) first, *then* retry the console switch with both consoles
active (`console=ttyS0,115200n8 console=ttyGS0,115200n8`) as planned
above - that way a repeat of this exact hang would actually be visible
on serial instead of leaving the board looking dead.

**Gotcha found while checking this**: `/dev/ttyS3` still exists even
with the overlay missing, which looks like it's working but isn't -
the core 8250 driver reserves a few legacy/phantom `ttySN` nodes
regardless of real hardware, and `ttyS3` fell back to being one of
those (traced to `serial8250:0.3` in sysfs, no real MMIO device behind
it) instead of disappearing. `dmesg | grep -i uart3` shows nothing for
this boot - that's the real tell, not `ls /dev/ttyS3`. Confirmed the
other UARTs don't have this ambiguity: `ttyS1`/`ttyS2` (UART1/UART2)
and `ttyS4` (UART4, kept its own number, doesn't shift down to fill
UART3's gap) all show real `NNNNNNNN.serial: ttySN at MMIO ...` dmesg
lines this boot. Written up in `setup.md` as a warning so this doesn't
bite anyone configuring `ola-uartdmx.conf` later - pointing it at a
phantom port would silently do nothing rather than error clearly.
7. **New, from the TFT-display question**: once UART3 is confirmed and
   the final pin set is locked in, check whether SPI1 is actually usable
   for a small SPI TFT. What's known so far: SPI0's all 4 signals are
   already fully consumed (`SPI0_CS0`/`SPI0_D1` by I2C1 at P1.06/P1.12,
   `SPI0_SCLK`/`SPI0_D0` by UART2 at P1.08/P1.10) - dead end. SPI1's
   clock (`SPI1_SCLK`) lands on P2.29, i.e. the same pin as the untested
   UART3 overlay - so SPI1 loses its clock line under the current plan
   unless UART3 moves or `SPI1_SCLK` has a usable alt-routing elsewhere
   (there was a hint of one, unconfirmed). Two automated lookups of the
   official PocketBeagle pinout page gave *inconsistent* answers for
   SPI1's MOSI/MISO/CS0 pin locations (mixed up D0 vs D1, ambiguous
   CS0) - don't trust either without checking the actual PDF/silkscreen
   directly, the same way P1.06/P1.12 vs P2.09/P2.11 got sorted out
   above. Fallback if SPI1 doesn't pan out: bit-banged/software SPI on
   free GPIOs works fine for a small, low-refresh TFT.
   - **Update**: confirmed against the official pinout docs that P1.36
     also carries `spi1_sclk` as an alt-function (currently unused by
     anything in this project) - so `SPI1_SCLK` isn't necessarily stuck
     behind the UART3/P2.29 conflict after all. MOSI/MISO/CS0 pins still
     need the same direct verification before wiring anything.
   - Parked for now - focus is back on the UARTs (item 5).

## Decision (2026-09-27): stopping at 4 universes for PB1

Universe 5 (freeing UART0 via `switch-console-to-usb.sh`) is **not
worth the trouble for now**, given the reproducible multi-minute hang
it caused (see above) - deliberately deprioritized, not forgotten. PB1
ships with 4 DMX universes (1-4, all confirmed working) instead of the
originally-planned 5. Revisit only if/when there's an actual need for
the 5th, using the cable-swap + dual-console approach noted above.

Next priorities, in order:

8. Verify the fader ADC works end-to-end on PB1: `scripts/ads7830_to_osc.py`
   already takes `--i2c-bus`, so `--i2c-bus 1` should just work given
   I2C1 is confirmed live at P1.06/P1.12 - but not yet actually run on
   PB1. Try `scripts/ads7830_debug_print.py` first (simpler, no OSC
   dependency) to confirm live fader reads, same as was done on PB2.
9. Verify buttons work on PB1. Note: the README's button pin list
   (P2.27/28/29/30/31/32/34) and PB2's "stuck low, unresolved" bug are
   both PB2-specific - PB1 needs its own pin choice, checked against
   what's actually free here. P2.29 is already committed to UART3
   (universe 3) on PB1, unlike PB2, so at minimum that one pin from the
   PB2 list isn't available - re-derive a free-pin set for PB1 rather
   than assuming the PB2 list carries over (same category of mistake as
   the I2C1 pin mix-up above).
10. Only once both of those are confirmed working in this test setup:
    move to the real hardware/fader setup, step by step (not all at
    once) - per the user's stated plan.
11. ~~PB1-specific `ola-uartdmx.conf` ... `apply-ola-config.sh`~~ **Done
    (2026-09-28)**: `pb1/ola-config/` (4-universe `ola-e131.conf` +
    `ola-uartdmx.conf` for `ttyS1-4`) and `pb1/apply-ola-config.sh` (a
    thin wrapper around the repo root's `apply-ola-config.sh`, passing
    `OLA_CONFIG_SRC`/`NUM_UNIVERSES=4`) now exist. The shared
    `ola-config/patch-sacn-to-uart.sh` was made universe-count-agnostic
    (`NUM_UNIVERSES` env var, default 5) instead of forking it per
    board. `pb1/setup.sh`'s NOPASSWD sudoers rule was extended to cover
    `apply-ola-config.sh` plus olad/ads7830-to-osc systemctl/journalctl,
    mirroring the repo root's `setup.sh`. **Not yet run on real
    hardware** - still needs `install-packages.sh` + this script
    exercised on PB1 (`pb_6ch`) to confirm olad actually comes up and
    DMX goes out on all 4 UARTs.

12. Item 8 above (fader ADC verification) is still blocked: PB1
    (`pb_6ch`, 192.168.17.2) was unreachable over SSH as of 2026-09-28
    (`connect ... port 22: Connection timed out`) - board likely off/
    disconnected/on a different network. Re-check connectivity before
    resuming items 8-10.
