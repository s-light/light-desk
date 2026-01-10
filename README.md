# light-desk

diy light desk controller for QLC+ or similar.
based on pocketbeagle2

> [!WARNING]
> WIP
> currently the following points are just targets.

-   sACN to DMX
    -   OLA as management layer
    -   RPU for dmx output
-   physical input to OSC
    -   handled by python scripts running in Blinka / CircuitPython

this repository should contain scripts and documentation for the setup process.


## ToDo

-   ola install
    -   test on pb2
    -   write script
    -   RPU
        -   write code / use

## info collection

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

### links

-   [QLC* custom VID * PID](https://www.qlcplus.org/forum/viewtopic.php?p=80731#p80731)
-   https://github.com/OpenLightingProject/rp2040-dmxsun
-   https://github.com/someweisguy/esp_dmx
-   https://github.com/adafruit/circuitpython/issues/673 (dmx support with examples)
-   https://github.com/mydana/CircuitPython_DMX_Transmitter
- [pocketbeagle 2](https://www.beagleboard.org/boards/pocketbeagle-2)
    - [device tree]( https://github.com/beagleboard/BeagleBoard-DeviceTrees/blob/v6.18.x/src/arm64/overlays/k3-am62-pocketbeagle2-ardupilot-cape.dtso)
    - [mounting](https://forum.beagleboard.org/t/pocketbeagle-2-physical-mounting/43416)
    - [3d step model](https://forum.beagleboard.org/t/pocketbeagle-2-3d-step-file/43415)
    - [analog & pin-current](https://forum.beagleboard.org/t/pin-currents-and-analog-in/43370)
    - [blinka / CircuitPython support](https://forum.beagleboard.org/t/pocket-beagle-2-python-libraries/42840)
- OSC
    - https://github.com/todbot/CircuitPython_MicroOSC/blob/main/examples/microosc_simplesend.py    
- [Adafruit ADS7830 8-Channel 8-Bit ADC with I2C](https://www.adafruit.com/product/5836) ([8€](https://eckstein-shop.de/Adafruit-ADS7830-8-Channel-8-Bit-ADC-with-I2C-STEMMA-QT-Qwiic)) [learn guide](https://learn.adafruit.com/adafruit-ads7830-8-channel-8-bit-adc/circuitpython-and-python)

## HW

just a collection of (possible usable) hardware.
for different real-implementations have a look at these repos:

- [6ch-light-desk](https://github.com/s-light/6ch-light-desk)
- 2ch-control
- 8ch-light-desk

main controller: [pocketbeagle 2](https://www.beagleboard.org/boards/pocketbeagle-2)

[100mm slide-potentiometer](https://tech.alpsalpine.com/e/products/detail/RSA0N1219A03/) ([~5€](https://www.reichelt.de/de/de/shop/produkt/schiebepotentiometer_stereo_10_kohm_linear-73873))