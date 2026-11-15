# Lichtpult

übersicht der Komponenten

schon Festgelegt:
- MainController: PocketBeagle2
- Display: Waveshare 2.8inch CapTouch
- Fader: 120mm


## MainController

[PocketBeagle2](https://www.beagleboard.org/boards/pocketbeagle-2)
[mouser 25,16€](https://www.mouser.de/ProductDetail/BeagleBoard-by-Seeed-Studio/102110780?qs=%252BXxaIXUDbq3pDS5bF5qfpw%3D%3D)
[digikey 40,30€](https://www.digikey.de/en/products/detail/beagleboard-by-seeed-studio/102110780/25927193)
[farnell 29,87€](https://de.farnell.com/beagleboard/102110780/entwicklungsboard-64bit-arm-cortex/dp/4628783)

## Display

[Waveshare 2.8inch Capacitive Touch LCD](https://www.waveshare.com/wiki/2.8inch_Capacitive_Touch_LCD)

resolution: 240×320
active: 57x43mm
pcb 73x51mm
color rgb
price [eckstein 20€](https://eckstein-shop.de/WaveShare-28inch-LCD-Display-Module-240x320-with-Touch-Panel-ST7789T3-CST328)



## Input

### Fader

ALSP 100mm (RSA0N1219A03) 
[reichelt 5€](https://www.reichelt.de/de/de/shop/produkt/schiebepotentiometer_stereo_10_kohm_linear-73873)

### others

-   [NeoKey 1x4 QT I2C - Four Mechanical Key Switches with NeoPixels - STEMMA QT / Qwiic](https://www.adafruit.com/product/4980) ([14€](https://eckstein-shop.de/AdafruitNeoKey1x4QTI2C-FourMechanicalKeySwitcheswithNeoPixels))
    -   -   10€ 10x Key Switch
    -   -   8€ 10x KeyCap
-   [Adafruit I2C Stemma QT Rotary Encoder Breakout with Encoder STEMMA QT Qwiic 5880](https://eckstein-shop.de/Adafruit-I2C-Stemma-QT-Rotary-Encoder-Breakout-with-Encoder-STEMMA-QT-Qwiic) 10€ ([docu](https://www.adafruit.com/product/4991))

# DMX

TODO: reicht 1 universe? 
oder sollen es zwei sein?

TODO: Stefan: check if 2 Universes are possible with one controller..

TODO: breakout-board designen
oder einfach eins von stefans fertigen nehmen + level-shifter

-   [3.3V isolated transeiver](https://www.reichelt.de/de/de/shop/produkt/rs-485_rs-422-transceiver_500_kbps_so-20w-185536) 7€
-   [ISOW1412 - Low-emissions, 500-kbps, reinforced isolated RS-485/RS-422 transceiver with integrated power](https://www.ti.com/product/ISOW1412#features)


## USB

do we really need this?
if not - move to collection.

- USB C Stecker auf USB C Buchse
    um die Mikrocontroller (uC) boards freier irgendwo im gehäuse plazieren zu können:
    -   [USB C Small Round Panel Mount Extension Cable Product ID: 6069 ](https://www.adafruit.com/product/6069) 2$
    -   USB-C verlängerungs kabel
        -   [Sync- & Ladekabel, USB-C Verlängerung, 100 W, 1 m](https://www.reichelt.de/de/de/shop/produkt/sync-_ladekabel_usb-c_verlaengerung_100_w_1_m-392823#closemodal) 4€
        -   [USB 10 Gb/s Kabel, Stecker Typ C > Buchse, 0,2 m](https://www.reichelt.de/de/de/shop/produkt/usb_10_gb_s_kabel_stecker_typ_c_buchse_0_2_m-330180) 7€
        -   [USB 10 Gb/s Kabel, C Stecker auf C Buchse, 60 W, 1 m](https://www.reichelt.de/de/de/shop/produkt/usb_10_gb_s_kabel_c_stecker_auf_c_buchse_60_w_1_m-344458) 6€
        -   [USB 10 Gb/s Kabel, Stecker 90° Typ C > Buchse, 0,5 m](https://www.reichelt.de/de/de/shop/produkt/usb_10_gb_s_kabel_stecker_90_typ_c_buchse_0_5_m-392815) 7€ GEWINKELT!
        -   [USB 10 Gb/s Kabel, C-Stecker > C-Buchse, 0,5 m](https://www.reichelt.de/de/de/shop/produkt/usb_10_gb_s_kabel_c-stecker_c-buchse_0_5_m-334205) 13€
        -   [USB 10 Gb/s Kabel, C-Stecker > C-Buchse, 0,5 m](https://www.reichelt.de/de/de/shop/produkt/usb_10_gb_s_kabel_c-stecker_c-buchse_0_5_m-355722) 10€
        -   [Delock Kabel USB 5 Gb/s C-Stecker > C-Buchse schwarz 0,5 m](https://www.reichelt.de/de/de/shop/produkt/delock_kabel_usb_5_gb_s_c-stecker_c-buchse_schwarz_0_5_m-230067) 7€
    -   adapter Buchse Buchse
        -   [USB 3.0 SuperSpeed Adapter Typ-C, schwarz buchse-buchse](https://www.reichelt.de/de/de/shop/produkt/usb_3_0_superspeed_adapter_typ-c_schwarz-220521) 3€
        -   [USB 3.1 Adapter, C Buchse auf C Buchse](https://www.reichelt.de/de/de/shop/produkt/usb_3_1_adapter_c_buchse_auf_c_buchse-334204) 4€
        -   [Keystone Modul USB-C 3.2 Gen 2 Buchse / Buchse, schwarz](https://www.reichelt.de/de/de/shop/produkt/keystone_modul_usb-c_3_2_gen_2_buchse_buchse_schwarz-354766) 6€
        -   [D-Typ Modul, USB 3.2 Gen 1, Typ-C Buchse / Buchse](https://www.reichelt.de/de/de/shop/produkt/d-typ_modul_usb_3_2_gen_1_typ-c_buchse_buchse-373832) 23€
    -   gewinkelt
        -   [Adapter USB 4.0 C-Stecker > C Buchse, silber 90°](https://www.reichelt.de/de/de/shop/produkt/adapter_usb_4_0_c-stecker_c_buchse_silber-382524) 4€
        -   [USB 3.1 Adapter, C Stecker auf C Buchse, 90° li./re.](https://www.reichelt.de/de/de/shop/produkt/usb_3_1_adapter_c_stecker_auf_c_buchse_90_li_re_-294324) 5€
- USB C Stecker auf USB C Stecker
    um das Display intern an den PocketBeagle2 anzuschließen (USB2.0)
    -   [USB 480Mb/s Kabel, C Stecker auf Stecker, 2 x 90° gewinkelt, 1,0](https://www.reichelt.de/de/de/shop/produkt/usb_480mb_s_kabel_c_stecker_auf_stecker_2_x_90_gewinkelt_1_0-429068)
-   []()
-   []()
