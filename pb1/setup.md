# PocketBeagle 1 setup

> [!WARNING]
> WIP - overlay/boot bring-up is not fully confirmed yet, see `memo.md`
> for current status and next steps. This file only documents what's
> confirmed working so far.

## HW connections

Fader ADC (Adafruit ADS7830, I2C) to the PocketBeagle 1 P1 header:

| ADS7830 pin | PB1 P1 pin | signal   |
| :---------- | :--------- | :------- |
| VIN         | P1.14      | VDD_3V3  |
| GND         | P1.22      | GND      |
| SDA         | P1.12      | I2C1_SDA |
| SCL         | P1.06      | I2C1_SCL |

> [!WARNING]
> Double-check pin numbers against the official PocketBeagle (1) pinout /
> silkscreen before wiring power - getting VIN/GND swapped can damage the
> board. **Do not assume PB1 and PB2 share pin numbers for the same
> signal** - they don't (confirmed the hard way: I2C1 is P1.33/P1.36 on
> PB2 but P1.06/P1.12 on PB1). The ADS7830 STEMMA QT breakout already has
> SDA/SCL pull-ups on board, so no extra resistors are needed for a
> single device on the bus.
>
> P1.06/P1.12 is where `BB-I2C1-00A0.dtbo` (see `apply-uenv-overlays.sh`)
> actually routes I2C1. The AM335x also exposes an I2C1_SCL/SDA
> alt-function on P2.09/P2.11 (the `uart1_txd`/`uart1_rxd` pins) - but
> that pin pair is already muxed to UART1 (DMX universe 1) in this
> project's overlay set, so it's not usable for I2C1 here. Confirmed on
> real hardware: wiring the ADC to P2.09/P2.11 instead of P1.06/P1.12
> gives `i2cget: Error: Read failed` - the bus exists but nothing is
> electrically connected to it at those pins while UART1 owns them.

This PB1 build has **7 faders** (not PB2's 8 - one ADS7830 channel goes
unused) and **6 buttons** (same count as PB2). Pass
`--num-channels 7` to `scripts/ads7830_debug_print.py`/
`scripts/ads7830_to_osc.py` accordingly.

Buttons (plain momentary switches, each wired between its P2 pin and
GND) to the PocketBeagle 1 P2 header:

| button | PB1 P2 pin |
| :----- | :--------- |
| 1      | P2.02      |
| 2      | P2.04      |
| 3      | P2.06      |
| 4      | P2.22      |
| 5      | P2.24      |
| 6      | P2.20      |

GND: any GND pin on the P2 header works, e.g. P2.15 or P2.21.

Using the SoC's internal pull-up (no external resistor needed).
AM335x's `pinctrl-single` driver doesn't honor `libgpiod`'s runtime
bias requests until a pin is already
claimed by some pinctrl consumer (confirmed on real hardware), so the
pull-up is baked into the boot-time pinmux via
`overlays/BB-GPIO-buttons-light-desk-00A0.dts`, installed with
`sudo ./pb1/install-gpio-buttons-overlay.sh` +
`sudo ./pb1/apply-uenv-overlays.sh` and a reboot.

**Confirmed on real PB1 hardware (2026-09-30), final pin set
(P2.02, P2.04, P2.06, P2.20, P2.22, P2.24)**: with nothing wired, all
6 pins read a clean "high" via `gpioget -b pull-up` and
`./buttons-debug-print.sh` (this folder's wrapper around
`../scripts/buttons_debug_print.py`, pointed at PB1's own pins instead
of the script's PB2-default `--button-pins`). No button physically
wired yet - see `memo.md` item 9.

See `pb1/pinout-reference.md` for the full P1/P2 pinmux table this and
other pin choices are checked against.

## DMX universe / overlay pin map

Confirmed on real hardware unless noted:

| universe | UART  | overlay                                                          | pins            | status                                                                                                                        |
| :------- | :---- | :--------------------------------------------------------------- | :-------------- | :---------------------------------------------------------------------------------------------------------------------------- |
| 1        | UART1 | `BB-UART1-00A0.dtbo` (stock)                                     | P2.09/P2.11     | confirmed - `/dev/ttyS1` present                                                                                              |
| 2        | UART2 | `BB-UART2-00A0.dtbo` (stock)                                     | P1.08/P1.10     | confirmed - `/dev/ttyS2` present                                                                                              |
| 3        | UART3 | `BB-UART3-light-desk-00A0.dtbo` (this repo's, custom)            | P2.29 (TX-only) | confirmed - `481a6000.serial: ttyS3` in dmesg (re-installed for kernel `6.18.53-bone55` via `install-uart3-overlay.sh`)       |
| 4        | UART4 | none needed (enabled in base dts)                                | P2.05/P2.07     | confirmed - `481a8000.serial: ttyS4` in dmesg                                                                                 |
| 5        | UART0 | none (console reassignment only, see `switch-console-to-usb.sh`) | P1.30/P1.32     | **not pursued** - the console switch reproducibly hung the board for 2+ min (see `memo.md`); PB1 stops at 4 universes for now |

> [!WARNING]
> **`/dev/ttyS3` existing does NOT mean UART3/universe 3 is actually
> enabled.** The kernel's core 8250 driver always reserves a handful of
> legacy/phantom `ttySN` device nodes regardless of real hardware; when
> the real DT-probed UART3 isn't loaded, `/dev/ttyS3` silently falls
> back to being one of those inert phantom ports instead - it still
> exists, but isn't connected to any pin. Don't trust `ls /dev/ttyS3`
> alone. Check `dmesg | grep -i uart3` for a real MMIO probe line (e.g.
> `481aa000.serial: ttyS3 at MMIO ...`) instead - if that line is
> missing, the overlay isn't loaded, whatever `/dev/ttyS3` says.
> (The other UARTs don't have this ambiguity: each keeps a fixed
> DT-alias-based `ttySN` number rather than shifting when another UART
> is missing, so `ttyS1`/`ttyS2`/`ttyS4` reliably mean what they say.)

I2C1 (fader ADC): `BB-I2C1-00A0.dtbo` (stock) - P1.06/P1.12 - **confirmed working**, ADS7830 answers at `i2cget -y 1 0x48`.

## olad config (sACN -> UART DMX)

`apply-ola-config.sh` (this folder) installs PB1's own 4-universe olad
config: `ola-config/ola-e131.conf` (4 sACN input ports) and
`ola-config/ola-uartdmx.conf` (`ttyS1`-`ttyS4`, matching the pin map
above). It's a thin wrapper around the repo root's
`../apply-ola-config.sh` (same plugin set, same port-9091 fix) with
`OLA_CONFIG_SRC`/`NUM_UNIVERSES` pointed at PB1's config instead of
PocketBeagle 2's 5-universe one. **Confirmed on real PB1 hardware
(2026-09-28)**: olad active, all 4 universes patched E1.31-in ->
`ttyS1`-`ttyS4`-out (`ola_plugin_info`/`ola_dev_info`).

Fader ADC (I2C1, ADS7830) also confirmed end-to-end on real hardware
(2026-09-28) via `scripts/ads7830_debug_print.py --i2c-bus 1`.

## APA102 output (SPI1)

One APA102 strip (7x10 = 70 pixels, laid out as 7 fader-backlight
segments of 10 pixels each) on SPI1, to the PocketBeagle 1 P1/P2
header:

| APA102 signal | PB1 pin | SPI1 signal | note    |
| :------------ | :------ | :---------- | :------ |
| CLK           | P1.36   | `spi1_sclk` |         |
| DI (data in)  | P2.32   | `spi1_d1`   | MOSI    |
| -             | P1.33   | `spi1_d0`   | MISO *1 |
| -             | P2.30   | `spi1_cs0`  | CS0  *2 |
|               |         |             |         |

*1: not wired to anything, muxed only for a clean spidev node
*2: not wired to anything, needed for the kernel to register the spidev channel at all

Only CLK and DI need to actually be wired to the strip - APA102 is a
write-only chipset, no MISO/CS involved electrically. SPI0 is already
fully consumed (I2C1 + UART2 share its 4 pins on different modes), and
AM335x only has 2 SPI controllers total, so a future second SPI
device (e.g. a display) goes on `spi-gpio` (bit-banged, separate free
GPIOs) rather than sharing this bus via a second chip-select - see
`memo.md` item 14's "second-SPI-device question" for why.

Install: `sudo ./pb1/install-spi1-overlay.sh`, `sudo
./pb1/apply-uenv-overlays.sh`, reboot, confirm `/dev/spidev1.0`
exists, then `sudo ./pb1/apply-ola-config.sh` (re-enables OLA's "spi"
plugin on top of the usual set, patches sACN universe 5 - a dedicated
universe for the pixel strip, not mirrored onto universes 1-4 - to
the SPI device via `pb1/ola-config/ola-spi.conf` +
`patch-spi-apa102.sh`).

**Confirmed working on real PB1 hardware (2026-10-01)**: verified via
the olad web UI and `scripts/apa102_running_dot_test.py`, which lights
one shared position across all 7 segments at once and steps it every
second (e.g. position 3 -> pixels 3, 13, 23, ..., 63) - a quick way to
eyeball all 7 segments' wiring/order together.

## Rotary pulse encoder

One rotary pulse encoder with integrated push button, to the
PocketBeagle 1 P1/P2 header:

| encoder signal | PB1 pin | note                                                      |
| :-------------- | :------ | :--------------------------------------------------------- |
| A                | P1.31   | `eqep0A_in` - AM335x's hardware quadrature decoder, not GPIO |
| B                | P2.34   | `eqep0B_in`                                                  |
| push button      | P2.19   | plain GPIO, internal pull-up, same as the other buttons      |
| common/GND       | -       | any GND pin on the P1/P2 header                              |

Uses AM335x's `eqep0` hardware quadrature-decode peripheral (checked:
the only one of its 3 eQEP units with a full free A+B pair on this
board - `eqep1` has no B channel broken out anywhere, `eqep2`'s
channels land on pins already committed to other buttons) instead of
software GPIO polling, so a fast spin doesn't risk missed pulses from
poll-rate jitter.

Install: `sudo ./pb1/install_rotary_encoder_overlay.py`, re-run
`sudo ./pb1/install-gpio-buttons-overlay.sh` (picks up the push
button pin, added to that overlay), `sudo ./pb1/apply-uenv-overlays.sh`,
reboot, confirm with `ls /sys/bus/counter/devices/`.

**Not yet installed/boot-tested** - overlays compile clean but the
reboot hasn't happened yet; no consumer script written either (what
the encoder should actually do is still open - see memo.md item 16).

## Stand-alone mode (`hsv-pixel-strip`)

See `../stand alone mode.md` for the spec and `memo.md` item 15 for
the implementation decisions. A self-contained fader-driven effect
(no computer/sACN needed) that runs *alongside* control-desk mode,
toggled by a 7th button:

| button       | PB1 P2 pin |
| :----------- | :--------- |
| mode toggle  | P2.33      |

Install (after the 6-button overlay above has been rebuilt to include
P2.33 and rebooted):

```
sudo ./pb1/install_standalone_mode.py
```

This enables+starts `standalone-mode-toggle.service` (always-on
button watcher); `standalone-plasma.service` (the effect itself) is
installed but stays inactive until a P2.33 press starts it - or
start/stop it by hand for testing:

```
sudo systemctl start standalone-plasma.service
sudo systemctl stop standalone-plasma.service
```

**Not yet installed/boot-tested as a whole system** - the overlay
change needs a reboot first, see `memo.md` item 15 for what's left.

See `memo.md` for full bring-up history and remaining open steps
(button press verification with an actual button, an actual DMX
fixture on the line, the future `spi-gpio` display, stand-alone mode
above).
