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

| ADS7830 pin | PB2 P1 pin | signal          |
| :---------- | :--------- | :-------------- |
| VIN         | P1.14      | VDD_3V3         |
| GND         | P1.22      | GND             |
| SDA         | P1.33      | I2C1_SDA        |
| SCL         | P1.36A     | I2C1_SCL        |

> [!WARNING]
> Double-check pin numbers against the official PocketBeagle 2 pinout /
> silkscreen before wiring power - getting VIN/GND swapped can damage the
> board. The ADS7830 STEMMA QT breakout already has SDA/SCL pull-ups on
> board, so no extra resistors are needed for a single device on the bus.

Each 100mm slide potentiometer is a 3-terminal voltage divider: both end
terminals go to the ADS7830's own supply rails (VIN and GND, so the divider
tracks the ADC's reference), and the wiper goes to one ADS7830 input channel
(IN0-IN7, one fader per channel).

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
