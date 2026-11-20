#!/usr/bin/env python3
"""Front-panel UI on the SSD1306 OLED, driven by the rotary encoder.

Turning the encoder switches between pages; pressing its push button
toggles stand-alone mode (same effect as the P2.33 mode button - starts
or stops standalone-plasma.service).

Pages:
    status  - mode (control desk / stand-alone), olad alive?, uptime
    faders  - 7 live fader bars (reads the ADS7830 directly, like
              standalone_plasma.py; concurrent reads are fine)
    network - the board's IPv4 addresses

This reuses the pin/SPI shims from oled_display_test.py and the eQEP
counter + button helpers from rotary_encoder_test.py (imported, not
copied - they live in the same folder). Hardware requirements and
caveats are documented there.

The bit-banged SPI is slow (every pixel byte is 16 gpiod calls), so a
full-frame redraw takes a noticeable fraction of a second. The loop
therefore only redraws when the page's content actually changed, and
the faders page is limited to --faders-interval seconds per redraw.

Not yet verified on real hardware as of writing (OLED not wired when
this was written) - see pb1/setup.md "Final verification".

Usage:
    python3 oled_ui.py [--faders-interval 0.5] [--button-pin P2.19]
        [--i2c-bus 1]
"""

import argparse
import socket
import subprocess
import sys
import time

import gpiod
from gpiod.line import Bias, Direction, Value

import rotary_encoder_test as encoder
import oled_display_test as oled_hw

import adafruit_ssd1306

PAGES = ["status", "faders", "network"]
STANDALONE_UNIT = "standalone-plasma.service"
STEP_COUNTS = 4  # raw x4 quadrature counts per encoder detent


def unit_active(unit):
    result = subprocess.run(["systemctl", "is-active", "--quiet", unit])
    return result.returncode == 0


def olad_alive():
    return subprocess.run(["pgrep", "-x", "olad"], capture_output=True).returncode == 0


def uptime_text():
    with open("/proc/uptime") as f:
        seconds = int(float(f.read().split()[0]))
    hours, rem = divmod(seconds, 3600)
    return f"{hours}h{rem // 60:02d}m"


def ipv4_addresses():
    result = subprocess.run(["ip", "-4", "-o", "addr", "show", "scope", "global"],
                            capture_output=True, text=True)
    addresses = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 4:
            addresses.append((fields[1], fields[3].split("/")[0]))
    return addresses


def read_faders(i2c_bus):
    """Return a list of 7 fader values 0..1, or None if the ADC isn't
    reachable (the UI should keep working without it)."""
    try:
        from adafruit_extended_bus import ExtendedI2C
        import adafruit_ads7830.ads7830 as ADC
        from adafruit_ads7830.analog_in import AnalogIn
        adc = ADC.ADS7830(ExtendedI2C(i2c_bus))
        channels = [AnalogIn(adc, i) for i in range(7)]
    except Exception as exc:  # noqa: BLE001 - any failure just disables the page
        print(f"fader page disabled: {exc}", file=sys.stderr)
        return None
    return lambda: [chan.value / 65535 for chan in channels]


def draw_page(display, page, fader_reader):
    display.fill(0)
    display.text(f"[{page}]", 0, 0, 1)
    if page == "status":
        standalone = unit_active(STANDALONE_UNIT)
        display.text("mode:", 0, 16, 1)
        display.text("STAND-ALONE" if standalone else "control desk", 36, 16, 1)
        display.text(f"olad: {'ok' if olad_alive() else 'DOWN'}", 0, 28, 1)
        display.text(f"up:   {uptime_text()}", 0, 40, 1)
        display.text("press = toggle mode", 0, 54, 1)
    elif page == "faders":
        values = fader_reader() if fader_reader else None
        if values is None:
            display.text("no ADC", 0, 24, 1)
        else:
            for i, value in enumerate(values):
                y = 12 + i * 7
                display.text(str(i + 1), 0, y, 1)
                display.rect(10, y, 100, 6, 1)
                display.fill_rect(10, y, round(max(0.0, min(1.0, value)) * 100), 6, 1)
    elif page == "network":
        addresses = ipv4_addresses() or [("-", "no address")]
        display.text(socket.gethostname()[:21], 0, 12, 1)
        for i, (iface, address) in enumerate(addresses[:4]):
            display.text(address[:21], 0, 24 + i * 10, 1)
    display.show()


def set_standalone(on):
    action = "start" if on else "stop"
    subprocess.run(["sudo", "-n", "systemctl", action, STANDALONE_UNIT], check=False)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--button-pin", default="P2.19", help="encoder push button pin (default: %(default)s)")
    parser.add_argument("--i2c-bus", type=int, default=1, help="I2C bus of the ADS7830 (default: %(default)s)")
    parser.add_argument("--faders-interval", type=float, default=0.5, help="min seconds between faders-page redraws (default: %(default)s)")
    parser.add_argument("--interval", type=float, default=0.05, help="poll interval (default: %(default)s)")
    return parser.parse_args()


def main():
    args = parse_args()

    pins = {role: oled_hw.GpiodOutputPin(*oled_hw.resolve_pin(name)) for role, name in oled_hw.DEFAULT_PINS.items()}
    spi = oled_hw.BitbangSPI(pins["clk"], pins["mosi"])
    display = adafruit_ssd1306.SSD1306_SPI(oled_hw.WIDTH, oled_hw.HEIGHT, spi, pins["dc"], pins["rst"], pins["cs"])
    fader_reader = read_faders(args.i2c_bus)

    count_path = encoder.find_eqep_count_path()
    encoder.ensure_quadrature_mode(count_path)
    chip_path, offset = encoder.resolve_button_pin(args.button_pin)
    request = gpiod.request_lines(
        chip_path, consumer="oled_ui",
        config={offset: gpiod.LineSettings(direction=Direction.INPUT, bias=Bias.PULL_UP, active_low=True)},
    )

    page_index = 0
    last_raw = encoder.read_count(count_path)
    accumulated = 0
    was_pressed = False
    last_page = None
    last_draw_time = 0.0

    try:
        while True:
            now = time.monotonic()

            raw = encoder.read_count(count_path)
            delta = raw - last_raw
            if delta > encoder.WRAP // 2:
                delta -= encoder.WRAP
            elif delta < -encoder.WRAP // 2:
                delta += encoder.WRAP
            last_raw = raw
            accumulated += delta
            detents = int(accumulated / STEP_COUNTS)
            accumulated -= detents * STEP_COUNTS
            if detents:
                page_index = (page_index + detents) % len(PAGES)

            pressed = request.get_value(offset) == Value.ACTIVE
            if pressed and not was_pressed:
                set_standalone(not unit_active(STANDALONE_UNIT))
                last_page = None  # force redraw with the new mode
            was_pressed = pressed

            page = PAGES[page_index]
            redraw_every = args.faders_interval if page == "faders" else 1.0
            if page != last_page or now - last_draw_time >= redraw_every:
                draw_page(display, page, fader_reader)
                last_page = page
                last_draw_time = now

            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    finally:
        display.fill(0)
        display.show()
        request.release()


if __name__ == "__main__":
    sys.exit(main())
