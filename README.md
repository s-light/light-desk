# light-desk

diy light desk controller for QLC+ or similar.
based on pocketbeagle2

> [!WARNING]
> WIP
> currently the following points are just targets.

-   sACN to DMX
    -   OLA as management layer
    -   UART for dmx output
-   physical input to OSC
    -   handled by python scripts running in Blinka / CircuitPython

this repository should contain scripts and documentation for the setup process.


## ToDo

-   ola install
    -   test on pb2
    -   write script
-   python
    -   ADS7830 -> OSC: `scripts/ads7830_to_osc.py` (needs testing on pb2)
    -   buttons -> OSC: `scripts/ads7830_to_osc.py` reads them via
        libgpiod (not Blinka's `board`/`digitalio` - `board.P2_27` etc.
        don't actually exist, Blinka has no `board` module support for
        `BEAGLEBONE_POCKETBEAGLE_2` even though platformdetect correctly
        identifies the board id), confirmed running as a service on real
        pb2 hardware; the P2.29/P2.31 pin ambiguity noted in the script's
        docstring still needs a physical button press to resolve
    -   buttons wiring check: `scripts/buttons_debug_print.py` - reads
        the buttons directly via libgpiod (bypassing Blinka's `board`
        module entirely), confirmed running on real pb2 hardware; still
        needs a physical button press to confirm the P2.27-P2.32 wiring
        and pull-up polarity

## system overview
- main controller: [pocketbeagle 2](https://www.beagleboard.org/boards/pocketbeagle-2)
- analog to digital converter - [Adafruit ADS7830 8-Channel 8-Bit ADC with I2C](https://www.adafruit.com/product/5836) ([8€](https://eckstein-shop.de/Adafruit-ADS7830-8-Channel-8-Bit-ADC-with-I2C-STEMMA-QT-Qwiic))
    - I2C: 
        - P1.33 (GPIO1_29) I2C1_SDA
        - P1.36A (GPIO1_28) I2C1_SCL
- fader [100mm slide-potentiometer](https://tech.alpsalpine.com/e/products/detail/RSA0N1219A03/) ([~5€](https://www.reichelt.de/de/de/shop/produkt/schiebepotentiometer_stereo_10_kohm_linear-73873))
- 7x momentary buttons -> plain GPIO, read via `libgpiod` (`gpioget`/`gpiomon`
  with `--bias=pull-up`, button to GND) - no device-tree overlay needed,
  these pins are free by default (unlike I2C1/UART which needed
  overlays/*.dtso, see below)
    - P2.27, P2.28, P2.29, P2.30, P2.31, P2.32 - six in a row on the P2
      header
    - P2.34 - seventh button; P2.33 sits between this and the row above
      but is already committed to DMX universe 5 (UART5 TXD), so it can't
      be reused - this is the closest 7th free pin to the P2.27-32 group


### DMX

https://en.wikipedia.org/wiki/DMX512

based on RS485

| function                   | XLR 5p. | XLR 3p. | RJ45 | T-568A            | RJ45 T-568B \*    |
| :------------------------- | ------: | ------: | ---: | ----------------- | ----------------- |
| Ground (shield)            |       1 |       1 | 7, 8 | white/brown; brown | white/brown; brown |
| Signal inv. (DMX−, "Cold") |       2 |       2 |    2 | green              | orange             |
| Signal (DMX+, "Hot")       |       3 |       3 |    1 | white/green        | white/orange       |
| optional Data 2 -          |       4 |         |    3 | white/orange       | green              |
| optional Data 2 +          |       5 |         |    6 | orange             | white/green        |
|                            |         |         |      |                    |                    |

\* common in Germany

## HW

just a collection of (possible usable) hardware.
for different real-implementations have a look at these repos:

- 2ch-control
- 8ch-light-desk
- [6ch-light-desk](https://github.com/s-light/6ch-light-desk)


