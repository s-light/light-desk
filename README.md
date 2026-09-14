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
- python 

## system overview
- main controller: [pocketbeagle 2](https://www.beagleboard.org/boards/pocketbeagle-2)
- analog to digital converter - [Adafruit ADS7830 8-Channel 8-Bit ADC with I2C](https://www.adafruit.com/product/5836) ([8€](https://eckstein-shop.de/Adafruit-ADS7830-8-Channel-8-Bit-ADC-with-I2C-STEMMA-QT-Qwiic))
    - I2C: 
        - P1.33 (GPIO1_29) I2C1_SDA
        - P1.36A (GPIO1_28) I2C1_SCL
- fader [100mm slide-potentiometer](https://tech.alpsalpine.com/e/products/detail/RSA0N1219A03/) ([~5€](https://www.reichelt.de/de/de/shop/produkt/schiebepotentiometer_stereo_10_kohm_linear-73873))


### DMX

https://de.wikipedia.org/wiki/DMX_(Lichttechnik)

based on RS485

| function                   | XLR 5p. | XLR 3p. | RJ45 | T-568A            | RJ45 T-568B \*    |
| :------------------------- | ------: | ------: | ---: | ----------------- | ----------------- |
| Masse (Abschirmung)        |       1 |       1 | 7, 8 | weiß/braun; braun | weiß/braun; braun |
| Signal inv. (DMX−, „Cold“) |       2 |       2 |    2 | grün              | orange            |
| Signal (DMX+, „Hot“)       |       3 |       3 |    1 | weiß/grün         | weiß/orange       |
| optional Data 2 -          |       4 |         |    3 | weiß/orange       | grün              |
| optional Data 2 +          |       5 |         |    6 | orange            | weiß/grün         |
|                            |         |         |      |                   |                   |

\* in Deutschland gebräuchlich

## HW

just a collection of (possible usable) hardware.
for different real-implementations have a look at these repos:

- 2ch-control
- 8ch-light-desk
- [6ch-light-desk](https://github.com/s-light/6ch-light-desk)


