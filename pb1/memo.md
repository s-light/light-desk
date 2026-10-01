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

8. ~~Verify the fader ADC works end-to-end on PB1~~ **Done
   (2026-09-28)**: ran `scripts/ads7830_debug_print.py --i2c-bus 1`
   (via `scripts/.venv`, already set up on the board) on real PB1
   hardware - all 8 channels print live, changing values, confirming
   I2C1/P1.06+P1.12 and the ADS7830 wiring end-to-end. Not yet tried
   `ads7830_to_osc.py`/the OSC path itself, but the ADC read path
   underneath it is confirmed.
   - **Quick-check confirmed both ends of the 7-fader range
     (2026-09-28)**: user wired test potentiometers on ADC channels 0
     and 7 (the first/last of the eventual 7). Both showed clear,
     responsive movement when turned - ch0 first, ch7 on a second
     sample after being told to move it (its first sample window
     happened to catch it not-yet-moved, pegged at 0.996 - a false
     alarm, not a wiring issue). One thing noted for later: with ch0
     swung hard, ch7 and the floating ch1-ch6 channels showed
     correlated movement/drift too (mux crosstalk between
     back-to-back ADS7830 channel reads, not a wiring fault) - worth
     re-checking once all 7 fader channels are wired to real
     (low-impedance) pots, which should reduce it.
9. Verify buttons work on PB1. Note: the README's button pin list
   (P2.27/28/29/30/31/32/34) and PB2's "stuck low, unresolved" bug are
   both PB2-specific - PB1 needs its own pin choice, checked against
   what's actually free here. P2.29 is already committed to UART3
   (universe 3) on PB1, unlike PB2, so at minimum that one pin from the
   PB2 list isn't available - re-derive a free-pin set for PB1 rather
   than assuming the PB2 list carries over (same category of mistake as
   the I2C1 pin mix-up above).
   - **Pin selection, real-hardware build has 6 buttons / 7 faders, not
     PB2's 6/8** (per the user, 2026-09-28) - `pb1/pinout-reference.md`
     (new: ground-truth pinmux table, parsed verbatim from the official
     docs HTML, not a model summary - see that file's own note) was
     used to re-derive free pins.
   - **First pick, P2.25/27/28/30/31/32/33, had a dead end**: `P2.27`
     resolves in the pinmux table to `gpio1_08`, but `gpioinfo` on real
     PB1 shows that line named `"[SYSBOOT 8]"`, not `P2.27` - it's a
     boot-strapping pin, not usable as GPIO despite the table listing a
     GPIO mode for it. Found by actually running
     `buttons_debug_print.py` on the board (with no buttons wired -
     just checking the pins resolve) rather than trusting the table
     alone. This also exposed a real bug in both `buttons_debug_print.py`
     and `ads7830_to_osc.py`: their gpio-line-name matching only
     stripped a `(...)`-style suffix (PB2's `gpioinfo` style), not
     PB1's `[...]`-style (e.g. `"P2.25 [SPI1_MOSI]"`) - fixed to strip
     either.
   - **Working 6-pin set (lines resolve, no PB2-style crash)**:
     **P2.25, P2.28, P2.30, P2.31, P2.32, P2.33** - all present as named
     gpio lines on real PB1, none SYSBOOT/reserved, none overlapping any
     other committed PB1 function.
   - **New finding, not yet a green light**: with nothing wired to any
     of these 6 pins, `gpioget -b pull-up|pull-down|disabled` all
     return the *same* fixed value per pin regardless of bias
     (`P2.25` always "active"/high, the other 5 always "inactive"/low) -
     software bias has zero effect. Checked two unrelated, definitely-
     otherwise-free plain-GPIO pins (`P2.02`, `P2.03`, GPMC-mux group,
     nothing to do with the SPI1/PRU cluster the 6 candidates sit in)
     and got the exact same symptom - **so this isn't specific to these
     6 pins or a wiring fault, it reproduces board-wide**. Best current
     explanation: AM335x's `pinctrl-single` driver (used here) is known
     not to support runtime bias changes through the generic Linux
     pinctrl API that `libgpiod`'s `-b`/`Bias` option goes through - the
     pull config has to be baked into the pin's static pinmux value in
     the device tree at boot, not toggled live. That would also explain
     PB2's older "buttons stuck low, unresolved" bug (see the PB2
     history above) as the same root cause, not a PB2-specific wiring
     issue.
   - **Practical implication**: don't rely on `gpiod`'s software
     pull-up for these buttons - either wire an external pull-up
     resistor per button (classic button-to-GND design) or bake a
     pull-up into a small pinmux overlay per button pin (same pattern
     as `pb1/overlays/BB-UART3-light-desk-00A0.dts`). Needs deciding
     before wiring, and re-testing with an actual button (or a
     jumper-to-GND stand-in) once done - a truly floating pin with no
     real pull either way can't be trusted to read meaningfully at all,
     bias override or not.
   - `config-pin` (BeagleBoard's usual pin-mux CLI) isn't installed on
     this image (`command not found`) and `/sys/kernel/debug/pinctrl`
     needs root (no password-less sudo for ad-hoc debugfs reads) -
     either would help confirm the pinctrl-single theory directly, not
     done yet.
   - **Overlay approach chosen and built (2026-09-28)**, per the user's
     preference for the SoC's internal pull-up over external resistors.
     Found the base `am335x-pocketbeagle.dts` (on the board, under
     `/opt/source/dtb-*.x/src/arm/ti/omap/`) already defines a
     ready-made `PIN_INPUT_PULLUP, MUX_MODE7` pinctrl-single node per
     header pin (`P2_02_gpio`, `P2_04_gpio`, `P2_06_gpio`, `P2_22_gpio`,
     `P2_24_gpio`, `P2_33_gpio`, ...) - unused by anything, since
     nothing references them from a `pinctrl-0`. All 6 of our 6 chosen
     button pins happen to have one of these ready-made nodes and sit
     on the same GPIO bank (`gpio1`), so
     `pb1/overlays/BB-GPIO-buttons-light-desk-00A0.dts` (new) is a
     single small fragment on `&gpio1` that adds
     `pinctrl-names/pinctrl-0` referencing those 6 existing labels by
     phandle - no need to hand-compute AM335x padconf values. Targeting
     the GPIO bank controller itself (not a `gpio-keys`/`gpio-leds`
     node) matters: any platform device with a bound driver gets
     `pinctrl-0` applied automatically at probe (generic Linux
     driver-core behavior), and `gpio1`'s own driver already
     probes/binds normally - so this activates the pad config without
     any kernel driver *claiming* the GPIO lines, leaving them free for
     `libgpiod` from userspace (a `gpio-keys` node would also reserve
     the lines and break the existing Python scripts' direct polling).
   - Compiled clean on real PB1 with the same `dtc -@ -O dtb -b 0`
     one-liner the UART3 overlay uses (no C preprocessor/macros needed -
     just phandle references, which `dtc` resolves natively via
     `__fixups__`/`__symbols__`, the same mechanism the already-working
     UART3 overlay relies on). Decompiled the output to confirm the 6
     phandle fixups are present and correctly named.
   - **Installed and boot-tested on real PB1, confirmed working
     (2026-09-28)**: user ran `install-gpio-buttons-overlay.sh` +
     `apply-uenv-overlays.sh` and rebooted. `gpioget -b pull-up P2.02
     P2.04 P2.06 P2.22 P2.24 P2.33` and
     `buttons_debug_print.py --button-pins P2.02,P2.04,P2.06,P2.22,P2.24,P2.33`
     both read a clean, consistent "high"/"active" on all 6 with
     nothing wired - the internal-pull-up overlay works.
     Bonus finding: explicit `gpioget -b pull-down|disabled` on `P2.02`
     now *does* change the reading (low, as expected) - runtime bias
     override works now too, whereas pre-overlay it had zero effect on
     any pin tested (see above). Best explanation: `pinctrl-single`'s
     runtime bias reconfiguration path only works once a pin is already
     claimed/active under *some* pinctrl consumer (here, `&gpio1`'s own
     probe via our overlay) - with no consumer at all, there's no
     active pinctrl state for the dynamic bias request to modify, so it
     silently no-ops. Consistent with, and now fully explaining, the
     earlier board-wide "stuck value regardless of bias" symptom.
   - **Still open**: only tested with nothing wired (no buttons
     physically attached yet) - still need an actual button (or a
     jumper-to-GND stand-in) per pin to confirm each one pulls low on
     press, before calling item 9 fully done.
   - **Pin swap, P2.33 -> P2.20 (2026-09-30)**: at the user's request,
     for a physically tighter header layout (P2.02-P2.24 cluster
     together; P2.33 sat off on its own further down the header, for
     no stronger reason than "it had a ready-made pullup label and
     happened to share gpio1 with the others"). P2.20 also has a
     ready-made `PIN_INPUT_PULLUP, MUX_MODE7` node (`P2_20_gpio`), so
     the swap is clean - the one wrinkle is that P2.20 is `gpio2_00`,
     a different bank than the other 5 (`gpio1_*`), so the overlay now
     has two small fragments (`&gpio1` for 5 pins, `&gpio2` for
     `P2.20` alone) instead of one. Recompiled clean on real PB1 with
     both fragments' phandle fixups present and correctly named. Not
     yet installed/boot-tested - `install-gpio-buttons-overlay.sh`
     needs either the user's sudo password or a re-run of `setup.sh`
     (to pick up the sudoers rule) before it can run non-interactively,
     left for the user to do deliberately along with the reboot.
   - **Installed, rebooted, confirmed on real PB1 (2026-09-30)**: all 6
     pins (`P2.02, P2.04, P2.06, P2.20, P2.22, P2.24`) read a clean
     "high" via `gpioget -b pull-up`. Also found `buttons_debug_print.py`
     run bare defaults to PB2's pins (`P2.27` etc, which error - not a
     bug, just the wrong board's default) - added
     `pb1/buttons-debug-print.sh`, a thin wrapper passing PB1's
     `--button-pins` through, confirmed working on real hardware (`-u`
     needed on the `python3` invocation, same output-buffering quirk
     as every other non-interactive SSH test in this memo).
   - Final button pins: **P2.02, P2.04, P2.06, P2.22, P2.24, P2.33**
     (dropped `P2.30`/`P2.31`/`P2.32` from the earlier PRU/SPI1-cluster
     pick - those don't have a ready-made pullup `_gpio` label in the
     base dts, so using them would mean hand-writing padconf values
     instead of reusing verified ones; not worth it when 6 ready-made
     ones exist and sit on a single bank).
10. Only once both of those are confirmed working in this test setup:
    move to the real hardware/fader setup, step by step (not all at
    once) - per the user's stated plan.
11. ~~PB1-specific `ola-uartdmx.conf` ... `apply-ola-config.sh`~~ **Done
    (2026-09-28), now hardware-verified**: `pb1/ola-config/` (4-universe
    `ola-e131.conf` + `ola-uartdmx.conf` for `ttyS1-4`) and
    `pb1/apply-ola-config.sh` (a thin wrapper around the repo root's
    `apply-ola-config.sh`, passing `OLA_CONFIG_SRC`/`NUM_UNIVERSES=4`)
    written, then the user ran `pb1/setup.sh` and `pb1/apply-ola-config.sh`
    on real PB1 (`pb_6ch`). Confirmed via `systemctl status olad`,
    `ola_plugin_info`, and `ola_dev_info`: olad active, e131 plugin
    loaded, all 4 universes patched E1.31-in -> UART-out
    (`ttyS1`-`ttyS4`, one universe each). DMX output itself (an actual
    fixture on the line) still not checked, but the sACN->UART patch
    path is confirmed working end-to-end.

12. **All 7 real faders wired and confirmed working (2026-09-29)** by
    the user. Follow-up noted for a later session: real potentiometers
    don't quite hit the rails - two faders bottom out at 0.008, not
    0.000, and all of them top out at 0.996, not 1.000. Both
    `ads7830_debug_print.py` and `ads7830_to_osc.py` currently just do
    `chan.value / 65535` with no calibration (see
    `scripts/ads7830_to_osc.py:159`) - `ads7830_to_osc.py` needs a
    per-channel (or one shared, if the offset turns out consistent
    across faders) min/max calibration + clamp so the OSC output
    actually reaches a clean 0.0/1.0 at each fader's physical extremes,
    otherwise QLC+ (or whatever's on the receiving end) never sees a
    true black/full value. Options to weigh next session: hardcoded
    per-channel min/max constants (simple, but brittle if a
    potentiometer is swapped), a `--fader-calibrate` pass that samples
    live and writes out per-channel min/max, or just clamp-and-rescale
    with a fixed small margin (e.g. treat <=0.01 as 0.0, >=0.99 as
    1.0) if the deadzone turns out consistent enough not to need
    per-channel values.
    - **Basic version done (2026-10-01)**: added `--fader-min`/
      `--fader-max` to `ads7830_to_osc.py` (defaults 0.0/1.0, so PB2's
      behavior is unchanged) - the shared clamp-and-rescale option from
      above, not per-channel calibration. PB1's service now passes
      `--fader-min 0.01 --fader-max 0.99` (see next item). Per-channel
      calibration is still open if the shared margin turns out not to
      be enough once QLC+ testing starts.

13. **`ads7830-to-osc.service` found crash-looping on real PB1
    (2026-10-01)**, discovered while checking whether it was running
    for the user's QLC+ test: `journalctl` showed a restart every ~9s,
    `no gpio line named 'P2.27' found` - it was installed from the
    plain PB2-defaults template (`../setup-i2c.sh`), whose
    `--button-pins` default doesn't exist on PB1. Root cause is the
    same class of mistake as item 9's original pin list - PB2 defaults
    silently don't carry over.
    - Extended `../ads7830-to-osc.service`'s template with
      `NUM_CHANNELS`/`BUTTON_PINS`/`FADER_MIN`/`FADER_MAX` environment
      variables (PB2-default values, so the root-level/PB2 behavior is
      unchanged) alongside the existing `OSC_HOST`/`OSC_PORT`/
      `I2C_BUS`.
    - Added `pb1/configure-ads7830-to-osc.sh`: reinstalls the systemd
      unit with PB1's values baked in (7 channels, PB1's 6 button pins,
      host `192.168.17.1` per `pb1_internet_share.md`, fader
      min/max 0.01/0.99) - same placeholder-fill approach
      `setup-i2c.sh` uses, just with PB1-specific `sed` overrides on
      top. Requires `setup-i2c.sh` to have been run at least once
      already (venv/udev setup). Added to `setup.sh`'s NOPASSWD rule.
    - **Run on the board, service stable (2026-10-01)**: user ran
      `sudo ./pb1/configure-ads7830-to-osc.sh` - out of the crash loop,
      `systemctl status` clean.
    - **Follow-up, found while checking the fix**: even the service's
      one-time startup banner never reached the journal - Python
      stdout is block-buffered when not a TTY (systemd's journal
      capture), and the script writes almost nothing after startup
      (OSC sends are network calls, not prints), so the buffer never
      flushed. Same class of issue as every debug-script SSH test in
      this memo needing `python3 -u`. Fixed by adding `-u` to the
      service template's `ExecStart`. Also added `--verbose` to
      `ads7830_to_osc.py` (off by default, not used by the service) to
      print each OSC message as sent - confirmed working manually on
      real PB1 (ran it in the foreground after stopping the service,
      saw the startup banner and all 7 `/fader/N` sends, then restored
      the service via `configure-ads7830-to-osc.sh` again).
    - **Verified end-to-end with QLC+ (2026-10-01)**: user connected
      QLC+ to the running service - faders and buttons both confirmed
      working over OSC. PB1's fader/button bring-up (items 8/9) is
      now fully done, tested with the real downstream consumer, not
      just the debug scripts.

14. **One APA102 strip via OLA's SPI plugin, planned/built (2026-10-01)**,
    at the user's request, with a second SPI device ("maybe later a
    display") noted as a near-future want. Checked and confirmed:
    - OLA's SPI plugin (`plugins/spi/SPIOutput.cpp` upstream) supports
      APA102 natively - standard SPI mode 0, MOSI+SCLK only. Confirmed
      the installed olad (0.10.9) actually has plugin id 15 "SPI" via
      `ola_plugin_info` on real hardware, not just checked upstream
      source.
    - SPI0's 4 header pins are fully consumed already (I2C1 + UART2,
      different modes of the same 4 balls) - SPI1 is the only native
      SPI controller left (AM335x has exactly 2 total). **User asked
      for two independent SPI stacks (one APA102 via OLA, one later
      for a display) that don't share a bus/CS** - OLA's SPI plugin
      apparently doesn't play well with a second device on the same
      bus. Answer: SPI1 (hardware) dedicated solely to the APA102, and
      a future display goes on `spi-gpio` (bit-banged, software,
      different free GPIOs) instead of SPI1's second chip-select -
      fully independent, zero shared pins/timing. Not built yet (the
      user said "maybe later").
    - Pins for SPI1 (all confirmed free against `pinout-reference.md`):
      **P1.36 sclk, P2.32 mosi (`spi1_d1`), P1.33 miso (`spi1_d0`,
      unused by APA102 but muxed for a clean spidev node), P2.30 cs0**
      (also unused electrically by APA102, but needed for the kernel
      to register the spidev channel at all) - all Mode3 of the same
      `mcasp0_*` ball group. This resolves the old SPI1/UART3
      P2.29-clash worry from way above (item 7) - a different ball
      group entirely, no conflict.
    - New `pb1/overlays/BB-SPI1-APA102-light-desk-00A0.dts` - raw
      offset/flags/mode numbers (same convention as the UART3/buttons
      overlays, no macros), derived from
      `/opt/source/dtb-*.x/include/dt-bindings/pinctrl/am33xx.h`'s
      `AM335X_PIN_*` defines on the board (offset = define - 0x800),
      flags 0x30 (`PIN_INPUT_PULLUP`) matching the convention the base
      dts's own (different-ball) `spi1_pins` fragment already uses for
      this exact peripheral. Compiled clean on real PB1, both fixups
      (`am33xx_pinmux`, `spi1`) resolved correctly when decompiled.
      Added `pb1/install-spi1-overlay.sh` (same pattern as the other
      per-overlay install scripts) and wired into
      `apply-uenv-overlays.sh`'s list + `setup.sh`'s NOPASSWD rule.
    - **APA102 universe: dedicated universe 5**, not mirrored onto an
      existing DMX universe (user's explicit choice) - `ola-e131.conf`
      bumped to `input_ports = 5`. New `pb1/ola-config/ola-spi.conf`:
      personality 7 (`PERS_APA102_INDIVIDUAL` - confirmed against the
      actual enum in `plugins/spi/SPIOutput.h`, RDM personality IDs,
      1-based, used directly as the config value, not a guess),
      `pixel-count = 70` (the strip is a 7x10 matrix, confirmed by the
      user, 210 DMX/sACN slots total).
    - Enabling the "spi" plugin shifts olad's device aliases (plugin
      load order is by plugin ID: dummy=1, e131=11, spi=15,
      uartdmx=20 - spi now loads *between* e131 and uartdmx). Made
      `ola-config/patch-sacn-to-uart.sh`'s `E131_DEVICE`/
      `UARTDMX_DEVICE_START` env-overridable for this. Extended the
      shared `apply-ola-config.sh` with an opt-in
      `EXTRA_ENABLED_PLUGINS` (space-separated plugin names, each
      re-enabled + its conf installed if present) - PB2's behavior is
      unchanged (empty by default). `pb1/apply-ola-config.sh` now sets
      `EXTRA_ENABLED_PLUGINS=spi` + `UARTDMX_DEVICE_START=4`, and
      after the shared script's usual universes-1-4 patch, runs the
      new `pb1/ola-config/patch-spi-apa102.sh` (universe 5 -> SPI
      device port 0; expected device alias 3, separate from the
      uartdmx loop since it's a different device shape).
    - **Not yet installed/boot-tested** - overlay only compiled, not
      loaded at boot; OLA config only written, not applied. Needs, in
      order: `sudo ./pb1/install-spi1-overlay.sh`, `sudo
      ./pb1/apply-uenv-overlays.sh`, reboot, confirm `/dev/spidev1.0`
      exists, then `sudo ./pb1/apply-ola-config.sh` and verify device
      aliases with `ola_dev_info` match what `patch-spi-apa102.sh`
      assumes before trusting the patch.
    - **Test script added**: `scripts/apa102_running_dot_test.py` -
      streams a single white pixel sweeping across a configurable
      range (default: pixels 0-9 of a 70-pixel/7x10 strip, 1s/step) to
      a universe (default 5), as a quick visual end-to-end check once
      the overlay/OLA config above are live. **Does not use OLA's
      actual Python client bindings** - checked and confirmed no
      `python3-ola` package exists on this Debian 13 image, and OLA
      doesn't publish them on PyPI either (they're SWIG-built from the
      C++ source tree, which would mean a from-source OLA build just
      for this - see `ola-pb2-crosscompile-handoff.md`'s notes on how
      heavy that is on this board). Uses `ola_streaming_client`
      instead (a CLI tool the plain `ola` apt package already
      installs) as a long-lived subprocess, one CSV DMX frame per
      stdin line. **Verified working against the dummy universe on
      real PB1** (`--universe 1`, safe/no hardware involved): checked
      olad's web API (`/get_dmx?u=1`) mid-run and saw exactly one
      pixel's 3 channels at 255 with correct offset, 210 channels
      total (70*3) - confirms the streaming approach and frame math
      are both correct, independent of the SPI/APA102 side still
      being uninstalled.
