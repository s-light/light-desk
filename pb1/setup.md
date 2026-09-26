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

## DMX universe / overlay pin map

Confirmed on real hardware unless noted:

| universe | UART  | overlay                          | pins           | status                |
| :------- | :---- | :-------------------------------- | :------------- | :--------------------- |
| 1        | UART1 | `BB-UART1-00A0.dtbo` (stock)       | P2.09/P2.11    | confirmed - `/dev/ttyS1` present |
| 2        | UART2 | `BB-UART2-00A0.dtbo` (stock)       | P1.08/P1.10    | confirmed - `/dev/ttyS2` present |
| 3        | UART3 | `BB-UART3-light-desk-00A0.dtbo` (this repo's, custom) | P2.29 (TX-only) | confirmed - `481a6000.serial: ttyS3` in dmesg (re-installed for kernel `6.18.53-bone55` via `install-uart3-overlay.sh`) |
| 4        | UART4 | none needed (enabled in base dts) | P2.05/P2.07    | confirmed - `481a8000.serial: ttyS4` in dmesg |

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
| 5        | UART0 | none (console reassignment only, see `switch-console-to-usb.sh`) | P1.30/P1.32 | not yet tested |

I2C1 (fader ADC): `BB-I2C1-00A0.dtbo` (stock) - P1.06/P1.12 - **confirmed
working**, ADS7830 answers at `i2cget -y 1 0x48`.

See `memo.md` for full bring-up history and remaining open steps
(custom UART3 overlay retest, console switch, olad config for PB1's
UART device list).
