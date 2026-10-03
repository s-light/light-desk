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
width (centered, evenly spaced - not squeezed into part of it like the
first draft). Board proportions here are schematic (stretched
vertically for label room), not to true mm scale.

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

Label placement: OUTER-row pins (the row nearer the board edge on
whichever header) get their leader-line label outside the board (above
P2, below P1) - same side labels have always been on. INNER-row pins
(nearer board center) get their label INSIDE the board instead, in a
dedicated band between that header's inner row and the central
processor/microSD/logo strip - otherwise their leader lines would have
to cross the outer row and collide with those labels. A greedy
left-to-right tiering algorithm (assign_tiers()) stacks same-side
labels into enough vertical tiers that none overlap horizontally,
rather than hand-placing each one.

Pin function/signal data (which pin carries what) comes from
pinout-reference.md, already cross-checked against the base
am335x-pocketbeagle.dts on real hardware earlier in this project's
history - not re-derived here. The "available, not wired" power/
ground/reference pins (drawn as hollow rings, vs. filled dots for
pins this project actually uses) are every other VIN/VOUT/GND/VREF/
battery/power-button pin on the header, included for reference even
though nothing here wires them up.
"""

from pathlib import Path

ROW_GAP = 34
TIER_H = 92           # vertical spacing between stacked label tiers
MIN_GAP = 150          # min horizontal gap between two labels sharing a tier
PIN_R_SMALL = 5
PIN_R_BIG = 9

BG = "#0b0d12"
BOARD_FILL = "#1f2430"
BOARD_STROKE = "#05060a"
TEXT_MAIN = "#e5e7eb"
TEXT_SUB = "#9aa3b2"
TEXT_FAINT = "#5b6472"
PIN_DOT = "#5b6472"

COLORS = {
    "i2c1":    "#22d3ee",
    "uart1":   "#60a5fa",
    "uart2":   "#818cf8",
    "uart3":   "#f472b6",
    "uart4":   "#34d399",
    "buttons": "#fb923c",
    "spi1":    "#c084fc",
    "encoder": "#a3e635",
    "power":   "#f87171",
    "power_avail": "#f87171",
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
    ("power", "ADS7830 power (VDD_3V3 / GND) – wired"),
    ("power_avail", "other power/GND/VREF pins – available, not wired"),
    ("unused", "parked / not pursued (UART0 console-swap universe 5)"),
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


def assign_tiers(entries):
    """Greedy label placement: put each label (processed left to
    right) in the first vertical tier whose most-recently-placed
    label is at least MIN_GAP away, so labels sharing a tier never
    overlap horizontally - avoids hand-placing ~40 leader lines."""
    tier_last_x = []
    assignment = []
    for entry in entries:
        x = colx(entry[1])
        for t, last_x in enumerate(tier_last_x):
            if x - last_x >= MIN_GAP:
                tier_last_x[t] = x
                assignment.append(t)
                break
        else:
            tier_last_x.append(x)
            assignment.append(len(tier_last_x) - 1)
    return assignment


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

    p1_outer_tiers = assign_tiers(p1_outer)
    p1_inner_tiers = assign_tiers(p1_inner)
    p2_outer_tiers = assign_tiers(p2_outer)
    p2_inner_tiers = assign_tiers(p2_inner)

    n_p1_outer = (max(p1_outer_tiers) + 1) if p1_outer_tiers else 0
    n_p1_inner = (max(p1_inner_tiers) + 1) if p1_inner_tiers else 0
    n_p2_outer = (max(p2_outer_tiers) + 1) if p2_outer_tiers else 0
    n_p2_inner = (max(p2_inner_tiers) + 1) if p2_inner_tiers else 0

    # --- geometry (y), built as stacked bands top to bottom -------------
    TITLE_H = 90
    y = TITLE_H + 30

    top_margin_top = y
    y += n_p2_outer * TIER_H + 50          # P2 outer labels (above board)

    BOARD_TOP = y
    p2_outer_y = BOARD_TOP + ROW_GAP
    p2_inner_y = BOARD_TOP + 2 * ROW_GAP
    y = p2_inner_y

    y += 55
    p2_inner_band_top = y
    y += n_p2_inner * TIER_H               # P2 inner labels (inside board, below P2 inner row)

    y += 40
    graphics_top = y
    GRAPHICS_H = 260
    y += GRAPHICS_H
    graphics_bottom = y

    y += 40
    p1_inner_band_top = y
    y += n_p1_inner * TIER_H               # P1 inner labels (inside board, above P1 inner row)
    y += 55

    p1_inner_y = y
    p1_outer_y = p1_inner_y + ROW_GAP
    BOARD_BOTTOM = p1_outer_y + ROW_GAP
    y = BOARD_BOTTOM

    y += 50
    y += n_p1_outer * TIER_H + 20          # P1 outer labels (below board)
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
    LEGEND_W = 620
    DIAGRAM_W = BOARD_RIGHT + 90
    W = DIAGRAM_W + LEGEND_W
    H = max(bottom_margin_bottom + 30, 760)

    put(f'<rect x="0" y="0" width="{W}" height="{H}" fill="{BG}"/>')

    put(f'<text x="{DIAGRAM_W/2}" y="48" text-anchor="middle" font-size="30" font-weight="700" fill="{TEXT_MAIN}">PocketBeagle 1 – light-desk pinout (component side)</text>')
    put(f'<text x="{DIAGRAM_W/2}" y="78" text-anchor="middle" font-size="16" fill="{TEXT_SUB}">P1/P2 expansion headers – project-committed connections highlighted – see pb1/pinout-reference.md for the full pinmux table</text>')

    put(f'<rect x="{BOARD_LEFT}" y="{BOARD_TOP}" width="{BOARD_RIGHT-BOARD_LEFT}" height="{BOARD_H}" rx="26" ry="26" fill="{BOARD_FILL}" stroke="{BOARD_STROKE}" stroke-width="3"/>')

    usb_y = (BOARD_TOP + BOARD_BOTTOM) / 2
    put(f'<rect x="{BOARD_LEFT-34}" y="{usb_y-26}" width="46" height="52" rx="6" fill="#c7cdd6" stroke="#4b5563" stroke-width="2"/>')
    put(f'<text x="{BOARD_LEFT-44}" y="{usb_y+60}" text-anchor="start" font-size="16" fill="{TEXT_MAIN}" font-weight="600">USB micro-B</text>')
    put(f'<text x="{BOARD_LEFT-44}" y="{usb_y+80}" text-anchor="start" font-size="14" fill="{TEXT_SUB}">(X1)</text>')

    # central graphics strip: logo (left) - processor (center) - microSD (right)
    gy_mid = (graphics_top + graphics_bottom) / 2
    logo_x = BOARD_LEFT + 110
    put(f'<text x="{logo_x}" y="{gy_mid-10}" font-size="19" fill="#f59e0b" font-weight="700">beagleboard.org</text>')
    put(f'<text x="{logo_x}" y="{gy_mid+20}" font-size="21" fill="{TEXT_MAIN}" font-weight="700">PocketBeagle</text>')

    proc_size = min(GRAPHICS_H - 20, 200)
    proc_cx = BOARD_LEFT + (BOARD_RIGHT - BOARD_LEFT) * 0.54
    proc_x, proc_y = proc_cx - proc_size / 2, gy_mid - proc_size / 2
    put(f'<rect x="{proc_x}" y="{proc_y}" width="{proc_size}" height="{proc_size}" rx="8" fill="#111318" stroke="#6b7280" stroke-width="2"/>')
    put(f'<text x="{proc_cx}" y="{gy_mid-6}" text-anchor="middle" font-size="16" fill="{TEXT_MAIN}" font-weight="600">AM3358</text>')
    put(f'<text x="{proc_cx}" y="{gy_mid+16}" text-anchor="middle" font-size="12" fill="{TEXT_SUB}">(OSD3358-SM)</text>')

    sd_w, sd_h = 340, min(GRAPHICS_H - 30, 170)
    sd_x = BOARD_RIGHT - HEADER_MARGIN - sd_w - 20
    sd_y = gy_mid - sd_h / 2
    put(f'<rect x="{sd_x}" y="{sd_y}" width="{sd_w}" height="{sd_h}" rx="6" fill="#30343f" stroke="#9ca3af" stroke-width="2"/>')
    put(f'<text x="{sd_x+sd_w/2}" y="{sd_y+sd_h/2+6}" text-anchor="middle" font-size="15" fill="{TEXT_MAIN}">microSD (X2)</text>')

    put(f'<text x="{HEADER_LEFT-20}" y="{p1_outer_y+6}" text-anchor="end" font-size="20" fill="{TEXT_MAIN}" font-weight="700">P1</text>')
    put(f'<text x="{HEADER_LEFT-20}" y="{p2_outer_y+6}" text-anchor="end" font-size="20" fill="{TEXT_MAIN}" font-weight="700">P2</text>')

    for header in ("P1", "P2"):
        for pin in range(1, 37):
            x, yy = pin_xy(header, pin)
            put(f'<circle cx="{x}" cy="{yy}" r="{PIN_R_SMALL}" fill="{PIN_DOT}"/>')
    for header in ("P1", "P2"):
        x, yy = pin_xy(header, 1)
        put(f'<rect x="{x-9}" y="{yy-9}" width="18" height="18" fill="none" stroke="#f59e0b" stroke-width="2"/>')

    put(f'<text x="{colx(1)}" y="{BOARD_TOP-14}" text-anchor="middle" font-size="13" fill="{TEXT_FAINT}">pin 1</text>')
    put(f'<text x="{colx(1)}" y="{BOARD_BOTTOM+24}" text-anchor="middle" font-size="13" fill="{TEXT_FAINT}">pin 1</text>')
    put(f'<text x="{colx(35)}" y="{BOARD_TOP-14}" text-anchor="middle" font-size="13" fill="{TEXT_FAINT}">pin 35/36</text>')
    put(f'<text x="{colx(35)}" y="{BOARD_BOTTOM+24}" text-anchor="middle" font-size="13" fill="{TEXT_FAINT}">pin 35/36</text>')

    def draw_labels(entries, tiers, header, placement):
        """placement: 'above' (outside, label above pin), 'below'
        (outside, label below pin), 'inward-down' (inside band below
        a top-edge inner row), 'inward-up' (inside band above a
        bottom-edge inner row)."""
        for (hdr, pin, cat, short, note), tier in zip(entries, tiers):
            x, yy = pin_xy(hdr, pin)
            color = COLORS[cat]
            if cat == "power_avail":
                put(f'<circle cx="{x}" cy="{yy}" r="{PIN_R_BIG}" fill="none" stroke="{color}" stroke-width="2.5"/>')
            else:
                put(f'<circle cx="{x}" cy="{yy}" r="{PIN_R_BIG}" fill="{color}" stroke="#05060a" stroke-width="1.5"/>')

            if placement == "above":
                ly = top_margin_top + tier * TIER_H + 14
                line_y2 = ly + TIER_H - 26
                text_y = ly
            elif placement == "below":
                ly = bottom_margin_bottom - (n_p1_outer - tier) * TIER_H + 14
                line_y2 = ly - 6
                text_y = ly + TIER_H - 20
            elif placement == "inward-down":
                ly = p2_inner_band_top + tier * TIER_H + 14
                line_y2 = ly - 10
                text_y = ly
            else:  # inward-up
                ly = p1_inner_band_top + tier * TIER_H + 14
                line_y2 = ly + TIER_H - 10
                text_y = ly

            put(f'<line x1="{x}" y1="{yy}" x2="{x}" y2="{line_y2}" stroke="{color}" stroke-width="1.5"/>')
            put(f'<circle cx="{x}" cy="{line_y2}" r="3.5" fill="{color}"/>')

            pin_name = f"{hdr}.{pin:02d}"
            put(f'<text x="{x+9}" y="{text_y}" font-size="14" font-weight="700" fill="{TEXT_MAIN}">{esc(pin_name)}</text>')
            sub = short if not note else f"{short} ({note})"
            put(f'<text x="{x+9}" y="{text_y+17}" font-size="12" fill="{TEXT_SUB}">{esc(sub)}</text>')

    draw_labels(p2_outer, p2_outer_tiers, "P2", "above")
    draw_labels(p2_inner, p2_inner_tiers, "P2", "inward-down")
    draw_labels(p1_inner, p1_inner_tiers, "P1", "inward-up")
    draw_labels(p1_outer, p1_outer_tiers, "P1", "below")

    # --- legend sidebar -------------------------------------------------
    leg_x = DIAGRAM_W + 40
    leg_y = 110
    put(f'<text x="{leg_x}" y="{leg_y}" font-size="20" font-weight="700" fill="{TEXT_MAIN}">Legend</text>')
    leg_y += 36
    for cat, desc in LEGEND:
        if cat == "power_avail":
            put(f'<rect x="{leg_x}" y="{leg_y-15}" width="20" height="20" rx="4" fill="none" stroke="{COLORS[cat]}" stroke-width="2.5"/>')
        else:
            put(f'<rect x="{leg_x}" y="{leg_y-15}" width="20" height="20" rx="4" fill="{COLORS[cat]}"/>')
        words = desc.split(" ")
        lines, cur = [], ""
        for w in words:
            trial = (cur + " " + w).strip()
            if len(trial) > 44:
                lines.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            lines.append(cur)
        for li, line in enumerate(lines):
            put(f'<text x="{leg_x+30}" y="{leg_y+li*20}" font-size="14" fill="{TEXT_MAIN}">{esc(line)}</text>')
        leg_y += max(1, len(lines)) * 20 + 22

    svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Helvetica, Arial, sans-serif">']
    svg += svg_body
    svg.append("</svg>")

    out_path = Path(__file__).resolve().parent / "pinout-diagram.svg"
    out_path.write_text("\n".join(svg))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
