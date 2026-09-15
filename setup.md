# Setup all needed things

## clone this repo to the board

```bash
git clone https://github.com/s-light/light-desk.git
cd light-desk
```


## install ola

```bash
sudo apt install ola
```

## configure ola

copy these config files to the correct places.

## HW connections

Fader ADC (Adafruit ADS7830, I2C) to the PocketBeagle 2 P1 header:

| ADS7830 pin | Qwick Kabel | PB2 P1 pin | signal   |
| :---------- | :---------- | :--------- | :------- |
| VIN         | red         | P1.14      | VDD_3V3  |
| GND         | black       | P1.22      | GND      |
| SDA         | blue        | P1.33      | I2C1_SDA |
| SCL         | yellow      | P1.36A     | I2C1_SCL |

> [!WARNING]
> Double-check pin numbers against the official PocketBeagle 2 pinout /
> silkscreen before wiring power - getting VIN/GND swapped can damage the
> board. The ADS7830 STEMMA QT breakout already has SDA/SCL pull-ups on
> board, so no extra resistors are needed for a single device on the bus.

Each 100mm slide potentiometer is a 3-terminal voltage divider: both end
terminals go to the ADS7830's own supply rails (VIN and GND, so the divider
tracks the ADC's reference), and the wiper goes to one ADS7830 input channel
(IN0-IN7, one fader per channel).

### DMX outputs (UART)

5 of the PocketBeagle 2's UARTs are usable as DMX outputs via olad's
uartdmx plugin (see `ola-config/ola-uartdmx.conf`) - that's the ceiling on
this board, not an arbitrary choice: it only has 7 UART instances total,
`uart2` has no pin-mux entry anywhere in the device tree (not routable to
any header pin), and `uart6` is reserved as the console/debug-probe UART
(see next section). 4 of the 5 need a device tree overlay to reach a
header pin at all; `uart0` is already enabled by the stock base DTS.

| universe | ttyS  | UART  | PB2 TXD pin | PB2 RXD pin | needs the overlay? |
| :------- | :---- | :---- | :---------- | :---------- | :------------------ |
| 1        | ttyS1 | UART1 | P1.08       | P1.06       | yes                  |
| 2        | ttyS3 | UART3 | P2.08       | P2.06       | yes                  |
| 3        | ttyS4 | UART4 | P1.20       | P2.20       | yes                  |
| 4        | ttyS5 | UART5 | P2.33       | P2.24       | yes                  |
| 5        | ttyS7 | UART0 | P1.30       | P1.32       | no (already enabled) |

> [!WARNING]
> These are 3.3V TTL UART pins, not the RS485 differential signal DMX
> actually runs on - each one needs an RS485 transceiver (e.g. MAX485/
> SN75176) between the PB2 pin and the DMX XLR, wired per the pinout in
> `README.md`'s DMX section. uartdmx only transmits, so RXD only matters
> if you want to test the line or add RDM later.

#### RS485 level shifting (verified working)

Confirmed on real hardware with one channel: old DIY opto-isolated
RS485 boards (no schematic available - designed years ago) built around
a `MAX485E` driver, a `6N137` optocoupler on the unused RX/receive side,
and a dual `HCPL-2631` optocoupler carrying TX and the combined `DE`/`RE`
enable line ("EN"). Both optos' LED inputs were sized for 5V logic, so
driving them straight from a PB2 UART's 3.3V TX needs a level shift up
first - the opto LED still gets *some* current at 3.3V, just not enough
to guarantee the fast, clean switching DMX's 250kbaud timing wants.

- **TX**: PB2 UART TX (3.3V) -> `TXB0108` (3.3V side to 5V side) -> opto
  input. TXB0108/TXB0104-family auto-direction-sensing shifters have a
  reputation for being finicky, but that's mainly on genuinely
  bidirectional lines (e.g. I2C) where the sensing logic has to guess
  direction on every transition; a UART TX line only ever drives one
  way, which sidesteps that failure mode.
- **EN** (`DE`+`/RE` tied together on the isolated board, active-high =
  permanent transmit / receiver disabled): doesn't need to toggle at
  all, so instead of routing it through the shifter it's tied directly
  to the isolated board's own 5V rail on the input side. Cheaper than it
  sounds like it should be to get right - without a schematic, the
  opto stage's polarity (does driving the input high actually produce
  the intended high, or does an open-collector-with-pull-up output stage
  invert it) had to be confirmed by testing rather than assumed.
- **RX**: the `6N137` side is unused - this setup is transmit-only, no
  RDM.

Same approach should carry over to the other 4 channels; TXB0108 has
8 channels, so one chip covers all 5 PB2 TX lines.

`uart6` (ttyS2) is deliberately left alone - it's the Linux console
(`console=ttyS2` in `extlinux.conf`) and doubles as a reliable
last-resort access route via a debug probe on its own header, independent
of network/SSH access.

#### building the overlay

```bash
./install-uart-overlay.sh
```

Builds `overlays/k3-am62-pocketbeagle2-light-desk-uart-dmx.dtso` using the
device-tree source/build tooling the board image already ships (no
cross-compiling needed), installs the resulting `.dtbo` to
`/boot/firmware/overlays/`, and adds it to the `fdtoverlays` line of
whichever label `/boot/firmware/extlinux/extlinux.conf`'s `default`
currently points at (the "microSD (default)" label, unless you changed
it) - without touching any other label. Idempotent; auto-detects the
`/opt/source/dtb-*.x` tree matching `uname -r` (override with
`DTB_SRC_DIR=` if that guess is wrong).

Does **not** reboot - do that yourself once it finishes, then confirm with
`ls -la /dev/ttyS1 /dev/ttyS3 /dev/ttyS4 /dev/ttyS5` and
`dmesg | grep -i uart`, and re-run `apply-ola-config.sh` to patch the
newly-available UARTs.

## known issues

- **Blinka does not support the PocketBeagle 2 yet.** Its AM625x SoC is
  recognized by Blinka's chip detector but has no implemented board/pin
  mapping, so plain `board.I2C()` (and anything else importing `board`)
  fails. See
  [Adafruit_Blinka#1031](https://github.com/adafruit/Adafruit_Blinka/issues/1031),
  the [Adafruit forum thread](https://forums.adafruit.com/viewtopic.php?t=223870),
  and the [BeagleBoard forum thread](https://forum.beagleboard.org/t/pocket-beagle-2-python-libraries/42840).
  - **Workaround**: skip `board`/per-board detection entirely and open the
    I2C bus directly by Linux bus number with
    [`adafruit_extended_bus.ExtendedI2C(N)`](https://github.com/adafruit/Adafruit_Python_Extended_Bus)
    (`N` = the number in `/dev/i2c-N`, find it with `i2cdetect -l`). It talks
    straight to `/dev/i2c-N` via the generic Linux driver, so it doesn't
    depend on Blinka's PB2 board support at all - and CircuitPython device
    drivers like `adafruit_ads7830` work unchanged, since they only need an
    I2C-like object, not `board` itself. `scripts/ads7830_to_osc.py` already
    uses this approach (`--i2c-bus`, default `1` - **not yet confirmed
    against real PB2 hardware**, verify with `i2cdetect -l` on the board).

## run the fader -> OSC bridge as a service

```bash
./setup-i2c.sh
```

Sets up everything `scripts/ads7830_to_osc.py` needs and installs it as
`ads7830-to-osc.service`: an `i2c` group + udev rule (so the script doesn't
need to run as root to reach `/dev/i2c-*`), a venv in `scripts/.venv` with
`scripts/requirements.txt` installed, and the enabled+running systemd
service itself. See `ads7830-to-osc.service` for how to check status/logs
or override the OSC host/port/I2C bus afterwards. Safe to re-run.
