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
   last bullet, still applies) - **not done yet, next up**.
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
