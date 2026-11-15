#!/usr/bin/env python3
"""Generate pinout-diagram.svg - a PocketBeagle 1 component-side
pinout diagram with this project's committed P1/P2 connections
highlighted (fader ADC, 4 DMX UARTs, buttons, APA102/SPI1, rotary
encoder) plus every power/ground/reference pin on the header.
Companion to pinout-reference.md's full pinmux table - this is a
visual "where do I actually plug things in" reference, not a
replacement for the full table.

Usage:
    python3 generate-pinout-diagram.py
    (writes pinout-diagram.svg next to this script; no dependencies
    beyond the standard library)

Layout, at the user's request: landscape canvas, dark page background,
legend as a right-hand sidebar, P1/P2 headers spanning the full board
width (centered, evenly spaced). Board proportions here are schematic
(stretched vertically for label room), not to true mm scale.

Board geometry (header edges, pin-1 corners, USB/microSD/processor
placement) is derived from BeagleBoard.org's official PocketBeagle
short-spec PDF's component-side photo (github.com/beagleboard/
pocketbeagle/raw/master/docs/PocketBeagle_Short_Spec.pdf) - inspected
at high resolution, not assumed:

  - P1 runs along the board's bottom edge, P2 along the top edge, both
    with pin 1 at the left end.
  - Each header is 2 rows x 18 columns (pins 1,3,5...35 in one row,
    2,4,6...36 in the other). The two headers are **not** mirror
    symmetric in which row holds the odd pins: on P1, pin 1 is on the
    OUTER row (nearer the board edge); on P2, pin 1 is on the INNER
    row (nearer the board center). Confirmed by reading the "1"/"2"
    silkscreen markers directly off the photo for each header
    independently - don't assume symmetry if this ever needs
    re-deriving.

Label placement: labels are rotated 90 degrees (reading bottom-to-top
for labels pointing "up"/"inward-up", top-to-bottom for labels pointing
"down"/"inward-down") and run straight out from their own pin's column,
one label per column. This replaced an earlier horizontal-tiering
scheme (stacking same-side labels into vertical tiers, each a
horizontal text line) that, at the user's observation, let a tier's
label text overhang sideways far enough to visually cross a
*different* pin's straight leader line. A vertical label never needs
to leave its own pin's column, so that collision class can't happen
at all - the column spacing (COL_SPACING, ~83px) comfortably exceeds a
rotated label's on-screen width (just the font size), and each column's
label simply grows outward only as far as its own text needs, with no
coordination needed between neighboring columns.
OUTER-row pins (the row nearer the board edge on whichever header) get
their label outside the board (above P2, below P1). INNER-row pins
(nearer board center) get their label INSIDE the board, in a band
between that header's inner row and the central processor/microSD/logo
strip - otherwise their leader lines would have to cross the outer row.

Pin function/signal data (which pin carries what) comes from
pinout-reference.md, already cross-checked against the base
am335x-pocketbeagle.dts on real hardware earlier in this project's
history - not re-derived here. The "available, not wired" power/
ground/reference pins (drawn as hollow rings, vs. filled dots for
pins this project actually uses) are every other VIN/VOUT/GND/VREF/
battery/power-button pin on the header, included for reference even
though nothing here wires them up.

Color scheme, at the user's request: all four UART categories (DMX
universes 1-4) share one hue family (blue, darkening by universe
number) since they're "the same kind of thing" - everything else
(buttons, SPI1/APA102, the rotary encoder, I2C1) gets a visually
distinct, high-contrast hue so it doesn't get lost among the UARTs.
Power pins are colored by actual voltage rather than by "is this a
power pin": 5V-class pins (VIN, VIN-USB, VOUT-5V) get a fully
saturated pink-red *dashed* leader line (dashes read as "look closer,
this isn't like the others" - deliberately the most alarming-looking
one, since wiring 5V into something expecting 3.3V is the easiest way
to let the smoke out), 3.3V-class pins (VDD_3V3, VOUT-3.3V) get a
solid, slightly less saturated red, GND gets a neutral dark gray, and
the handful of pins that are power-adjacent but neither a clean 5V nor
3.3V rail (VREFN/VREFP analog reference, the power-button pin,
VIN-BAT, BAT-TEMP) get a muted neutral so they don't compete visually
with the two rails that actually matter for level-shifting decisions.

A "Peripherals (schematic)" section occupies its own third column (at
the user's request, separate from the Legend column rather than
stacked below it), and draws one small schematic box per connected
peripheral (ADS7830 fader
ADC, one representative DMX UART->RS485 stage - all 4 universes wire
up identically, so only one is drawn - the buttons, the APA102 strip,
the rotary encoder), each listing its pins by the same "P1.NN  SIGNAL"
label used on the header, colored the same way. At the user's request
these are connected to the main header only by that shared label text,
not by a drawn wire running across the page - tracing a long path
across a diagram that already spans the full page width would add
visual clutter without adding information the label doesn't already
carry.
"""

from pathlib import Path

ROW_GAP = 34
STUB = 64               # straight colored leader-line segment from pin outward (longer = easier to read the color)
LABEL_GAP = 10          # blank space between the end of the leader line and where the label text starts
PIN_R_SMALL = 5
PIN_R_BIG = 9

BG = "#0b0d12"
BOARD_FILL = "#1f2430"
BOARD_STROKE = "#05060a"
TEXT_MAIN = "#e5e7eb"
TEXT_SUB = "#9aa3b2"
TEXT_FAINT = "#5b6472"
PIN_DOT = "#5b6472"

# Voltage-class colors for power-ish pins (see module docstring), keyed
# by the CSS class-name suffix each one gets (".fill-v5"/".stroke-v5",
# etc - see the generated <style> block in main()).
V5_DASH = "6,5"
VOLTAGE_COLORS = {
    "v5": "#ec4899",      # saturated pink-red, dashed leader line
    "v3v3": "#dc2626",    # solid red
    "gnd": "#506080",     # dark gray
    "pwrmisc": "#9ca3af",  # neutral (VREF/PWR BTN/VIN-BAT/BAT-TEMP)
}

COLORS = {
    "i2c1":    "#22d3ee",
    "uart1":   "#60a5fa",
    "uart2":   "#3b82f6",
    "uart3":   "#2563eb",
    "uart4":   "#1d4ed8",
    "buttons": "#fb923c",
    "spi1":    "#c084fc",
    "encoder": "#a3e635",
    "unused":  "#8b94a3",
}

LEGEND = [
    ("i2c1", "I2C1 – fader ADC (ADS7830)"),
    ("uart1", "UART1 – DMX universe 1"),
    ("uart2", "UART2 – DMX universe 2"),
    ("uart3", "UART3 – DMX universe 3 (custom overlay, TX only)"),
    ("uart4", "UART4 – DMX universe 4"),
    ("buttons", "buttons (6 control-desk + 1 stand-alone-mode toggle)"),
    ("spi1", "SPI1 – APA102 pixel strip (OLA SPI plugin)"),
    ("encoder", "eQEP0 – rotary encoder A/B + its push button"),
    ("unused", "parked / not pursued (UART0 console-swap universe 5)"),
]

# Separate legend block for power pins, drawn as leader-line swatches
# (so the dash pattern itself is visible) rather than solid rects.
POWER_LEGEND = [
    ("v5", V5_DASH, "5V class (VIN / VIN-USB / VOUT-5V) – dashed: check level-shifting before wiring"),
    ("v3v3", None, "3.3V class (VDD_3V3 / VOUT-3.3V)"),
    ("gnd", None, "GND"),
    ("pwrmisc", None, "other (VREF, power button, VIN-BAT, BAT-TEMP)"),
]

# (header, pin, category, short_label, note_or_None) - kept in sync
# with pinout-reference.md's "committed pins" summary by hand; there's
# no single machine-readable source of truth for this project's pin
# assignments to generate it from automatically.
PINS = [
    ("P1", 6,  "i2c1", "I2C1_SCL", None),
    ("P1", 12, "i2c1", "I2C1_SDA", None),
    ("P1", 14, "power", "VDD_3V3", "ADS7830 VIN"),
    ("P1", 22, "power", "GND", "ADS7830 GND"),
    ("P1", 8,  "uart2", "UART2 CLK/TXD", None),
    ("P1", 10, "uart2", "UART2 MISO/RXD", None),
    ("P1", 30, "unused", "UART0 TXD", "console"),
    ("P1", 32, "unused", "UART0 RXD", "console"),
    ("P1", 31, "encoder", "eQEP0 A", None),
    ("P1", 33, "spi1", "SPI1 MISO", "unused"),
    ("P1", 36, "spi1", "SPI1 SCLK", None),

    ("P2", 2,  "buttons", "button 1", None),
    ("P2", 4,  "buttons", "button 2", None),
    ("P2", 6,  "buttons", "button 3", None),
    ("P2", 20, "buttons", "button 6", None),
    ("P2", 22, "buttons", "button 4", None),
    ("P2", 24, "buttons", "button 5", None),
    ("P2", 33, "buttons", "mode toggle", "stand-alone"),
    ("P2", 9,  "uart1", "UART1 TXD", None),
    ("P2", 11, "uart1", "UART1 RXD", None),
    ("P2", 5,  "uart4", "UART4 RXD", None),
    ("P2", 7,  "uart4", "UART4 TXD", None),
    ("P2", 29, "uart3", "UART3 TXD", "TX only"),
    ("P2", 30, "spi1", "SPI1 CS0", "unused"),
    ("P2", 32, "spi1", "SPI1 MOSI", None),
    ("P2", 19, "encoder", "encoder button", None),
    ("P2", 34, "encoder", "eQEP0 B", None),

    # Every other power/ground/reference pin on the header - available
    # on the board but not wired to anything by this project (unlike
    # P1.14/P1.22 above, which ARE wired - drawn filled vs. these
    # outline-only "power_avail" dots, see draw_labels()).
    ("P1", 1,  "power_avail", "VIN", None),
    ("P1", 7,  "power_avail", "VIN-USB", None),
    ("P1", 15, "power_avail", "GND", "USB1"),
    ("P1", 16, "power_avail", "GND", None),
    ("P1", 17, "power_avail", "VREFN", None),
    ("P1", 18, "power_avail", "VREFP", None),
    ("P1", 24, "power_avail", "VOUT-5V", None),
    ("P2", 12, "power_avail", "PWR BTN", None),
    ("P2", 13, "power_avail", "VOUT-5V", None),
    ("P2", 14, "power_avail", "VIN-BAT", None),
    ("P2", 15, "power_avail", "GND", None),
    ("P2", 16, "power_avail", "BAT-TEMP", None),
    ("P2", 21, "power_avail", "GND", None),
    ("P2", 23, "power_avail", "VOUT-3.3V", None),
]

# Peripheral schematic boxes drawn in the right-hand sidebar, below the
# legend - see module docstring. Pin tuples are (category, "P1.NN"
# header-pin label, signal name) - the label text is deliberately the
# same text used on the main header drawing, since that shared text is
# the only "connection" drawn between a peripheral box and the header
# (no wire traced across the page - see module docstring).
# Each peripheral: title, optional level-shifter chip note, the PB1
# header pins it uses (signal + power - real "P1.NN"/"P2.NN" pins,
# colored/labeled the same as the main header drawing), and
# "extra_power" - power connections the peripheral/chip needs that are
# NOT PB1 header pins (e.g. a strip's own 5V injection from an external
# supply) - these get a voltage-colored swatch too (via power_style()
# matching on the note text) but no pin-name, so they don't read as if
# they were a header pin.
PERIPHERALS = [
    {
        "title": "ADS7830 fader ADC (I2C1)",
        "chip": None,
        "pins": [
            ("i2c1", "P1.06", "I2C1_SCL"),
            ("i2c1", "P1.12", "I2C1_SDA"),
            ("power", "P1.14", "VDD_3V3"),
            ("power", "P1.22", "GND"),
        ],
        "extra_power": [],
    },
    {
        "title": "DMX UART -> RS485 (x4, UART1-4 - UART2 shown)",
        "chip": "TXB0108 – 3.3V<->5V auto-direction level shifter (1 channel/signal: TXD, RXD)",
        "pins": [
            ("uart2", "P1.08", "TXD"),
            ("uart2", "P1.10", "RXD"),
            ("power_avail", "P2.23", "VOUT 3.3V (TXB0108 VCCA)"),
            ("power_avail", "P1.24", "VOUT 5V (TXB0108 VCCB)"),
            ("power_avail", "P2.21", "GND (common)"),
        ],
        "extra_power": [
            "RS485 driver's own 5V + GND (same 5V/GND rail as VCCB above)",
        ],
    },
    {
        "title": "control-desk buttons (x6) + mode toggle",
        "chip": None,
        "pins": [
            ("buttons", "P2.02", "button 1"),
            ("buttons", "P2.04", "button 2"),
            ("buttons", "P2.06", "button 3"),
            ("buttons", "P2.22", "button 4"),
            ("buttons", "P2.24", "button 5"),
            ("buttons", "P2.20", "button 6"),
            ("buttons", "P2.33", "mode toggle"),
            ("power", "P1.22", "GND"),
        ],
        "extra_power": [],
    },
    {
        "title": "rotary encoder (eQEP0)",
        "chip": None,
        "pins": [
            ("encoder", "P1.31", "A"),
            ("encoder", "P2.34", "B"),
            ("encoder", "P2.19", "button"),
            ("power", "P1.22", "GND"),
        ],
        "extra_power": [],
    },
    {
        "title": "APA102 pixel strip (SPI1)",
        "chip": "74HCT125 / 74AHCT125 – 3.3V->5V buffer (1 gate/signal: CLK, DATA)",
        "pins": [
            ("spi1", "P1.36", "SCLK"),
            ("spi1", "P2.32", "MOSI"),
            ("power_avail", "P1.24", "VOUT-5V (74HCT125 VCC)"),
            ("power_avail", "P2.21", "GND (common)"),
        ],
        "extra_power": [
            "strip's own 5V + GND injected from an external supply, not PB1's VOUT-5V – that pin is logic-only, not rated for LED current",
        ],
    },
]

# --- geometry (x): headers span the full board width, centered -------
BOARD_LEFT = 130
BOARD_RIGHT = 1660
HEADER_MARGIN = 55
HEADER_LEFT = BOARD_LEFT + HEADER_MARGIN
HEADER_RIGHT = BOARD_RIGHT - HEADER_MARGIN
COL_SPACING = (HEADER_RIGHT - HEADER_LEFT) / 17


def col(pin):
    return (pin - 1) // 2


def colx(pin):
    return HEADER_LEFT + col(pin) * COL_SPACING


def is_outer(header, pin):
    odd = pin % 2 == 1
    # P1: pin 1 on the row nearer the edge (outer=odd).
    # P2: pin 1 on the row nearer the board center (outer=even) -
    # NOT a mirror of P1, confirmed against the real board photo.
    return odd if header == "P1" else not odd


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def label_text(entry):
    _hdr, pin, _cat, short, note = entry
    pin_name = f"{entry[0]}.{pin:02d}"
    sub = short if not note else f"{short} ({note})"
    return f"{pin_name}  {sub}"


def label_px_len(text):
    """Rough text-length estimate (Helvetica/Arial, ~15-16px, mixed
    bold+regular) for sizing how far a *rotated* label needs to run -
    doesn't need to be exact, just consistently a bit generous."""
    return 8.3 * len(text) + 10


def power_style(short):
    """CSS color-class name + dash pattern for a power-ish pin, chosen
    by actual voltage class rather than just "is this power" - see
    module docstring. The returned name is a key into VOLTAGE_COLORS,
    used as the ".fill-<name>"/".stroke-<name>" class suffix."""
    if "3.3V" in short or "3V3" in short:
        return "v3v3", None
    if short in ("VIN", "VIN-USB", "VOUT-5V") or "5V" in short:
        return "v5", V5_DASH
    if "GND" in short:
        return "gnd", None
    return "pwrmisc", None


def category_style(cat, short):
    """Returns (css_color_class_name, dash_pattern_or_None) - the name
    is a key into COLORS (signal categories) or VOLTAGE_COLORS (power
    pins), used as the ".fill-<name>"/".stroke-<name>" class suffix."""
    if cat in ("power", "power_avail"):
        return power_style(short)
    return cat, None


def main():
    svg_body = []

    def put(s):
        svg_body.append(s)

    p1 = [p for p in PINS if p[0] == "P1"]
    p2 = [p for p in PINS if p[0] == "P2"]
    p1_outer = sorted((p for p in p1 if is_outer("P1", p[1])), key=lambda p: colx(p[1]))
    p1_inner = sorted((p for p in p1 if not is_outer("P1", p[1])), key=lambda p: colx(p[1]))
    p2_outer = sorted((p for p in p2 if is_outer("P2", p[1])), key=lambda p: colx(p[1]))
    p2_inner = sorted((p for p in p2 if not is_outer("P2", p[1])), key=lambda p: colx(p[1]))

    def band_h(entries):
        if not entries:
            return 0
        return max(label_px_len(label_text(e)) for e in entries)

    p2_outer_band = band_h(p2_outer)
    p2_inner_band = band_h(p2_inner)
    p1_inner_band = band_h(p1_inner)
    p1_outer_band = band_h(p1_outer)

    # --- geometry (y), built as stacked bands top to bottom -------------
    # Padding constants kept tight (not the generous ~30-60px slack an
    # earlier version used) - at the user's request the whole diagram
    # needs to fit a ~4K browser window's height without scrolling, and
    # the title-to-board gap in particular was bigger than it needed to
    # be: STUB+LABEL_GAP already reserve the real travel distance a
    # rotated label needs, so the extra per-band pad only has to absorb
    # rounding slack, not a second margin.
    BAND_PAD = 12
    TITLE_H = 64
    y = TITLE_H + 16

    y += STUB + LABEL_GAP + p2_outer_band + BAND_PAD   # P2 outer labels (above board, rotated, growing upward)

    BOARD_TOP = y
    p2_outer_y = BOARD_TOP + ROW_GAP
    p2_inner_y = BOARD_TOP + 2 * ROW_GAP
    y = p2_inner_y

    y += STUB + LABEL_GAP + p2_inner_band + BAND_PAD   # P2 inner labels (inside board, growing downward)
    graphics_top = y
    GRAPHICS_H = 220
    y += GRAPHICS_H
    graphics_bottom = y

    y += STUB + LABEL_GAP + p1_inner_band + BAND_PAD   # P1 inner labels (inside board, growing upward)
    p1_inner_y = y
    p1_outer_y = p1_inner_y + ROW_GAP
    BOARD_BOTTOM = p1_outer_y + ROW_GAP
    y = BOARD_BOTTOM

    y += STUB + LABEL_GAP + p1_outer_band + BAND_PAD   # P1 outer labels (below board, growing downward)
    bottom_margin_bottom = y

    def pin_xy(header, pin):
        x = colx(pin)
        outer = is_outer(header, pin)
        if header == "P2":
            yy = p2_outer_y if outer else p2_inner_y
        else:
            yy = p1_outer_y if outer else p1_inner_y
        return x, yy

    BOARD_H = BOARD_BOTTOM - BOARD_TOP
    LEGEND_W = 560
    PERIPH_W = 560
    COL_GAP = 50
    DIAGRAM_W = BOARD_RIGHT + 90
    W = DIAGRAM_W + LEGEND_W + COL_GAP + PERIPH_W

    put(f'<text x="{DIAGRAM_W/2}" y="48" text-anchor="middle" class="title fill-text-main">PocketBeagle 1 – light-desk pinout (component side)</text>')
    put(f'<text x="{DIAGRAM_W/2}" y="78" text-anchor="middle" class="subtitle fill-text-sub">P1/P2 expansion headers – project-committed connections highlighted – see pb1/pinout-reference.md for the full pinmux table</text>')

    put(f'<rect x="{BOARD_LEFT}" y="{BOARD_TOP}" width="{BOARD_RIGHT-BOARD_LEFT}" height="{BOARD_H}" rx="26" ry="26" class="fill-board stroke-board" stroke-width="3"/>')

    usb_y = (BOARD_TOP + BOARD_BOTTOM) / 2
    put(f'<rect x="{BOARD_LEFT-34}" y="{usb_y-26}" width="46" height="52" rx="6" class="fill-usb stroke-usb" stroke-width="2"/>')
    put(f'<text x="{BOARD_LEFT-44}" y="{usb_y+60}" text-anchor="start" class="label-usb fill-text-main">USB micro-B</text>')
    put(f'<text x="{BOARD_LEFT-44}" y="{usb_y+80}" text-anchor="start" class="sub-usb fill-text-sub">(X1)</text>')

    # central graphics strip: logo (left) - processor (center) - microSD (right)
    gy_mid = (graphics_top + graphics_bottom) / 2
    logo_x = BOARD_LEFT + 110
    put(f'<text x="{logo_x}" y="{gy_mid-10}" class="brand-logo fill-accent">beagleboard.org</text>')
    put(f'<text x="{logo_x}" y="{gy_mid+20}" class="name-logo fill-text-main">PocketBeagle</text>')

    proc_size = min(GRAPHICS_H - 20, 200)
    proc_cx = BOARD_LEFT + (BOARD_RIGHT - BOARD_LEFT) * 0.54
    proc_x, proc_y = proc_cx - proc_size / 2, gy_mid - proc_size / 2
    put(f'<rect x="{proc_x}" y="{proc_y}" width="{proc_size}" height="{proc_size}" rx="8" class="fill-proc stroke-proc" stroke-width="2"/>')
    put(f'<text x="{proc_cx}" y="{gy_mid-6}" text-anchor="middle" class="label-proc fill-text-main">AM3358</text>')
    put(f'<text x="{proc_cx}" y="{gy_mid+16}" text-anchor="middle" class="sub-proc fill-text-sub">(OSD3358-SM)</text>')

    sd_w, sd_h = 340, min(GRAPHICS_H - 30, 170)
    sd_x = BOARD_RIGHT - HEADER_MARGIN - sd_w - 20
    sd_y = gy_mid - sd_h / 2
    put(f'<rect x="{sd_x}" y="{sd_y}" width="{sd_w}" height="{sd_h}" rx="6" class="fill-sd stroke-sd" stroke-width="2"/>')
    put(f'<text x="{sd_x+sd_w/2}" y="{sd_y+sd_h/2+6}" text-anchor="middle" class="label-sd fill-text-main">microSD (X2)</text>')

    put(f'<text x="{HEADER_LEFT-20}" y="{p1_outer_y+6}" text-anchor="end" class="label-board fill-text-main">P1</text>')
    put(f'<text x="{HEADER_LEFT-20}" y="{p2_outer_y+6}" text-anchor="end" class="label-board fill-text-main">P2</text>')

    # outline box around each header's pin grid (both rows), separate
    # from the overall board outline, so the header itself reads as
    # its own component
    header_box_pad = 16
    put(f'<rect x="{HEADER_LEFT-header_box_pad}" y="{p2_outer_y-header_box_pad}" '
        f'width="{HEADER_RIGHT-HEADER_LEFT+2*header_box_pad}" height="{p2_inner_y-p2_outer_y+2*header_box_pad}" '
        f'fill="none" class="stroke-text-faint" stroke-width="1.5" rx="8"/>')
    put(f'<rect x="{HEADER_LEFT-header_box_pad}" y="{p1_inner_y-header_box_pad}" '
        f'width="{HEADER_RIGHT-HEADER_LEFT+2*header_box_pad}" height="{p1_outer_y-p1_inner_y+2*header_box_pad}" '
        f'fill="none" class="stroke-text-faint" stroke-width="1.5" rx="8"/>')

    for header in ("P1", "P2"):
        for pin in range(1, 37):
            x, yy = pin_xy(header, pin)
            put(f'<circle cx="{x}" cy="{yy}" r="{PIN_R_SMALL}" class="fill-pin-dot"/>')
    for header in ("P1", "P2"):
        x, yy = pin_xy(header, 1)
        put(f'<rect x="{x-9}" y="{yy-9}" width="18" height="18" fill="none" class="stroke-accent" stroke-width="2"/>')

    put(f'<text x="{colx(1)}" y="{BOARD_TOP-14}" text-anchor="middle" class="corner-pin fill-text-faint">pin 1</text>')
    put(f'<text x="{colx(1)}" y="{BOARD_BOTTOM+24}" text-anchor="middle" class="corner-pin fill-text-faint">pin 1</text>')
    put(f'<text x="{colx(35)}" y="{BOARD_TOP-14}" text-anchor="middle" class="corner-pin fill-text-faint">pin 35/36</text>')
    put(f'<text x="{colx(35)}" y="{BOARD_BOTTOM+24}" text-anchor="middle" class="corner-pin fill-text-faint">pin 35/36</text>')

    def draw_labels(entries, placement):
        """placement: 'above' (outside, above P2), 'below' (outside,
        below P1), 'inward-down' (inside band below P2 inner row,
        toward board center), 'inward-up' (inside band above P1 inner
        row, toward board center). Labels are rotated 90 degrees and
        run straight out from their own pin's column - see module
        docstring for why this replaced the old horizontal tiering."""
        flow_up = placement in ("above", "inward-up")
        rotate = -90 if flow_up else 90
        for (hdr, pin, cat, short, note) in entries:
            x, yy = pin_xy(hdr, pin)
            cls, dash = category_style(cat, short)
            if cat == "power_avail":
                put(f'<circle cx="{x}" cy="{yy}" r="{PIN_R_BIG}" fill="none" class="stroke-{cls}" stroke-width="2.5"/>')
            else:
                put(f'<circle cx="{x}" cy="{yy}" r="{PIN_R_BIG}" class="fill-{cls} stroke-outline-dark" stroke-width="1.5"/>')

            line_y2 = yy - STUB if flow_up else yy + STUB
            text_y = line_y2 - LABEL_GAP if flow_up else line_y2 + LABEL_GAP
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            put(f'<line x1="{x}" y1="{yy}" x2="{x}" y2="{line_y2}" class="stroke-{cls}" stroke-width="3"{dash_attr}/>')
            put(f'<circle cx="{x}" cy="{line_y2}" r="4" class="fill-{cls}"/>')

            pin_name = f"{hdr}.{pin:02d}"
            sub = short if not note else f"{short} ({note})"
            put(f'<text x="{x}" y="{text_y}" transform="rotate({rotate} {x} {text_y})" class="fill-text-main">'
                f'<tspan class="main-pin">{esc(pin_name)}</tspan>'
                f'<tspan class="sub-pin fill-text-sub">{"&#160;&#160;"}{esc(sub)}</tspan></text>')

    draw_labels(p2_outer, "above")
    draw_labels(p2_inner, "inward-down")
    draw_labels(p1_inner, "inward-up")
    draw_labels(p1_outer, "below")

    # --- column 2: legend sidebar ---------------------------------------
    leg_x = DIAGRAM_W + 40 + PERIPH_W + COL_GAP   # legend is the 3rd column now, peripherals the 2nd
    leg_y = 44
    put(f'<text x="{leg_x}" y="{leg_y}" class="heading-section fill-text-main">Legend</text>')
    leg_y += 30

    def wrap(desc, width=40):
        words = desc.split(" ")
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if len(trial) > width:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        return lines

    for cat, desc in LEGEND:
        put(f'<rect x="{leg_x}" y="{leg_y-17}" width="24" height="24" rx="5" class="fill-{cat}"/>')
        lines = wrap(desc)
        for li, line in enumerate(lines):
            put(f'<text x="{leg_x+34}" y="{leg_y+li*23}" class="text-legend fill-text-main">{esc(line)}</text>')
        leg_y += max(1, len(lines)) * 23 + 16

    leg_y += 6
    put(f'<text x="{leg_x}" y="{leg_y}" class="subheading-legend fill-text-main">power pins (colored by voltage, not just "is power"):</text>')
    leg_y += 28
    for cls, dash, desc in POWER_LEGEND:
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        put(f'<line x1="{leg_x}" y1="{leg_y-6}" x2="{leg_x+36}" y2="{leg_y-6}" class="stroke-{cls}" stroke-width="5"{dash_attr}/>')
        lines = wrap(desc, width=42)
        for li, line in enumerate(lines):
            put(f'<text x="{leg_x+48}" y="{leg_y+li*23}" class="text-legend fill-text-main">{esc(line)}</text>')
        leg_y += max(1, len(lines)) * 23 + 14

    leg_y += 6
    put(f'<circle cx="{leg_x+11}" cy="{leg_y-6}" r="10" class="fill-text-sub"/>')
    put(f'<text x="{leg_x+34}" y="{leg_y}" class="text-legend fill-text-main">filled = wired by this project</text>')
    leg_y += 28
    put(f'<circle cx="{leg_x+11}" cy="{leg_y-6}" r="10" fill="none" class="stroke-text-sub" stroke-width="3"/>')
    put(f'<text x="{leg_x+34}" y="{leg_y}" class="text-legend fill-text-main">outline = available, not wired</text>')
    leg_y += 30

    # --- column 3: peripheral schematic boxes -----------------------------
    def draw_peripheral(x, y, peripheral):
        # Content height isn't known until it's laid out, but the box
        # background rect has to be the FIRST element drawn (SVG paints
        # in document order) or it would paint over its own content -
        # so content goes into a local buffer first, the rect gets
        # inserted ahead of it once the height is known, then both are
        # appended to svg_body together.
        box_w = PERIPH_W - 40
        row_h = 27
        content = []

        def cput(s):
            content.append(s)

        title_lines = wrap(peripheral["title"], width=36)
        chip_lines = wrap(peripheral["chip"], width=40) if peripheral["chip"] else []
        extra_lines = []
        for note in peripheral["extra_power"]:
            extra_lines.extend((note, line) for line in wrap(note, width=38))

        yy = y + 22
        for li, line in enumerate(title_lines):
            cput(f'<text x="{x+16}" y="{yy+li*21}" class="title-peripheral fill-text-main">{esc(line)}</text>')
        yy += (len(title_lines) - 1) * 21 + 24

        if chip_lines:
            for li, line in enumerate(chip_lines):
                cput(f'<text x="{x+16}" y="{yy+li*18}" class="note-ic fill-ic">IC: {esc(line)}</text>')
            yy += len(chip_lines) * 18 + 8

        for cat, pin_label, sig in peripheral["pins"]:
            cls, dash = category_style(cat, sig if cat in ("power", "power_avail") else "")
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            cput(f'<line x1="{x+16}" y1="{yy-6}" x2="{x+40}" y2="{yy-6}" class="stroke-{cls}" stroke-width="5"{dash_attr}/>')
            cput(f'<text x="{x+50}" y="{yy}" class="fill-text-main"><tspan class="main-periph-pin">{esc(pin_label)}</tspan><tspan class="sub-periph-pin fill-text-sub">{"&#160;&#160;"}{esc(sig)}</tspan></text>')
            yy += row_h

        if extra_lines:
            yy += 4
            prev_note = None
            for note, line in extra_lines:
                if note != prev_note:
                    cls, dash = category_style("power", note)
                    dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
                    cput(f'<line x1="{x+16}" y1="{yy-6}" x2="{x+40}" y2="{yy-6}" class="stroke-{cls}" stroke-width="5"{dash_attr}/>')
                    prev_note = note
                cput(f'<text x="{x+50}" y="{yy}" class="note-periph fill-text-sub">{esc(line)}</text>')
                yy += 20

        h = yy - y + 14
        put(f'<rect x="{x}" y="{y}" width="{box_w}" height="{h}" rx="10" class="fill-board stroke-text-faint" stroke-width="1.5"/>')
        svg_body.extend(content)
        return h

    peri_x = DIAGRAM_W + 40
    peri_y = 44
    put(f'<text x="{peri_x}" y="{peri_y}" class="heading-section fill-text-main">Peripherals (schematic)</text>')
    peri_y += 22
    subtitle_lines = wrap("connected to the header at left only via matching pin labels, not a drawn wire – power pins included for soldering", width=70)
    for li, line in enumerate(subtitle_lines):
        put(f'<text x="{peri_x}" y="{peri_y+li*18}" class="subtitle-peripheral fill-text-sub">{esc(line)}</text>')
    peri_y += len(subtitle_lines) * 18 + 14
    for peripheral in PERIPHERALS:
        h = draw_peripheral(peri_x, peri_y, peripheral)
        peri_y += h + 16

    H = max(bottom_margin_bottom + 30, peri_y + 30, leg_y + 30, 760)

    font_family = "Helvetica, Arial, sans-serif"
    style = "background:black; width:100%; height:100%"
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="{font_family}" style="{style}">'
    ]

    # Text sizing AND coloring both live here as CSS classes (one per
    # semantic role, not just per pixel/hex value - e.g. legend text and
    # peripheral-note text happen to both be 14px today, and the
    # processor outline happens to match GND's gray, but keeping them
    # separate classes means any one of them can be tuned without
    # affecting the other) instead of scattered inline font-size="N"/
    # fill="#hex" attributes, so tweaking a size or color is a one-line
    # edit in this block rather than a hunt through the f-strings below.
    #
    # The per-pin/per-category color classes (.fill-i2c1, .stroke-v5,
    # etc.) are generated from COLORS/VOLTAGE_COLORS below rather than
    # hand-written twice, so the <style> block can't drift out of sync
    # with the dicts the drawing code actually looks colors up from.
    category_color_css = []
    for name, hexval in {**COLORS, **VOLTAGE_COLORS}.items():
        category_color_css.append(f'.fill-{name} {{ fill: {hexval}; }}')
        category_color_css.append(f'.stroke-{name} {{ stroke: {hexval}; }}')

    size_css = '''
.title { font-size: 30px; font-weight: 700; }
.subtitle { font-size: 16px; }
.label-usb { font-size: 16px; font-weight: 600; }
.sub-usb { font-size: 14px; }
.brand-logo { font-size: 19px; font-weight: 700; }
.name-logo { font-size: 21px; font-weight: 700; }
.label-proc { font-size: 16px; font-weight: 600; }
.sub-proc { font-size: 12px; }
.label-sd { font-size: 15px; }
.label-board { font-size: 20px; font-weight: 700; }
.corner-pin { font-size: 13px; }
.main-pin { font-size: 20px; font-weight: 700; }
.sub-pin { font-size: 18px; }
.heading-section { font-size: 24px; font-weight: 700; }
.text-legend { font-size: 18px; }
.subheading-legend { font-size: 20px; font-weight: 700; }
.subtitle-peripheral { font-size: 18px; }
.title-peripheral { font-size: 20px; font-weight: 700; }
.note-ic { font-size: 18px; font-style: italic; }
.main-periph-pin { font-size: 20px; font-weight: 700; }
.sub-periph-pin { font-size: 18px; }
.note-periph { font-size: 18px; }
'''

    ui_color_css = f'''
.fill-text-main {{ fill: {TEXT_MAIN}; }}
.stroke-text-main {{ stroke: {TEXT_MAIN}; }}
.fill-text-sub {{ fill: {TEXT_SUB}; }}
.stroke-text-sub {{ stroke: {TEXT_SUB}; }}
.fill-text-faint {{ fill: {TEXT_FAINT}; }}
.stroke-text-faint {{ stroke: {TEXT_FAINT}; }}
.fill-pin-dot {{ fill: {PIN_DOT}; }}
.fill-board {{ fill: {BOARD_FILL}; }}
.stroke-board {{ stroke: {BOARD_STROKE}; }}
.stroke-outline-dark {{ stroke: #05060a; }}
.fill-usb {{ fill: #c7cdd6; }}
.stroke-usb {{ stroke: #4b5563; }}
.fill-accent {{ fill: #f59e0b; }}
.stroke-accent {{ stroke: #f59e0b; }}
.fill-proc {{ fill: #111318; }}
.stroke-proc {{ stroke: #6b7280; }}
.fill-sd {{ fill: #30343f; }}
.stroke-sd {{ stroke: #9ca3af; }}
.fill-ic {{ fill: #d1a9f7; }}
'''

    svg.append('<style>' + size_css + ui_color_css + "\n".join(category_color_css) + '</style>')

    # we do not need the *page background rect* anymore. as we now have the svg itself set to black background.
    # svg.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>')

    svg += svg_body
    
    svg.append("</svg>")

    out_path = Path(__file__).resolve().parent / "pinout-diagram.svg"
    out_path.write_text("\n".join(svg))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
