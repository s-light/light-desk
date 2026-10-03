#!/usr/bin/env python3
"""Generate pinout-diagram.svg - a PocketBeagle 1 component-side
pinout diagram with this project's committed P1/P2 connections
highlighted (fader ADC, 4 DMX UARTs, buttons, APA102/SPI1, rotary
encoder). Companion to pinout-reference.md's full pinmux table - this
is a visual "where do I actually plug things in" reference, not a
replacement for the full table.

Usage:
    python3 generate-pinout-diagram.py
    (writes pinout-diagram.svg next to this script; no dependencies
    beyond the standard library)

Board layout (outline, USB connector, microSD slot, processor
position) and the P1/P2 pin-numbering geometry below are derived from
BeagleBoard.org's official PocketBeagle short-spec PDF component-side
photo (github.com/beagleboard/pocketbeagle/raw/master/docs/
PocketBeagle_Short_Spec.pdf) - cross-checked directly against the
photo at high resolution, not assumed:

  - P1 runs along the board's bottom edge, P2 along the top edge, both
    with pin 1 at the left end.
  - Each header is 2 rows x 18 columns (pins 1,3,5...35 in one row,
    2,4,6...36 in the other). The two headers are **not** mirror
    symmetric in which row holds the odd pins: on P1, pin 1 is on the
    OUTER row (nearer the board edge); on P2, pin 1 is on the INNER
    row (nearer the board center). Confirmed by reading the "1"/"2"
    silkscreen markers directly off the photo for each header
    independently - don't assume symmetry here if this ever needs
    re-deriving.

Pin function/signal data (which pin carries what) comes from
pinout-reference.md, already cross-checked against the base
am335x-pocketbeagle.dts on real hardware earlier in this project's
history - not re-derived here.
"""

from pathlib import Path

COL_SPACING = 48
HEADER_LEFT = 460
BOARD_TOP = 460
BOARD_BOTTOM = 980
BOARD_LEFT = 360
BOARD_RIGHT = 1460
ROW_GAP = 40
PIN_R_SMALL = 5
PIN_R_BIG = 9
TIER_H = 70
MIN_GAP = 148  # minimum horizontal spacing between two label anchors sharing a tier


def col(pin):
    return (pin - 1) // 2


def colx(pin):
    return HEADER_LEFT + col(pin) * COL_SPACING


def pin_xy(header, pin):
    x = colx(pin)
    odd = pin % 2 == 1
    if header == "P1":
        # pin 1 on the OUTER row (nearer the bottom board edge)
        y = BOARD_BOTTOM - ROW_GAP if odd else BOARD_BOTTOM - 2 * ROW_GAP
    else:
        # P2: pin 1 on the INNER row (nearer board center) - not a
        # mirror of P1, see module docstring.
        y = BOARD_TOP + 2 * ROW_GAP if odd else BOARD_TOP + ROW_GAP
    return x, y


COLORS = {
    "i2c1":    "#0891b2",
    "uart1":   "#2563eb",
    "uart2":   "#4f46e5",
    "uart3":   "#db2777",
    "uart4":   "#059669",
    "buttons": "#ea580c",
    "spi1":    "#9333ea",
    "encoder": "#65a30d",
    "power":   "#dc2626",
    "unused":  "#9ca3af",
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
    ("power", "ADS7830 power (VDD_3V3 / GND)"),
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
]


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def assign_tiers(entries):
    """Greedy label placement: put each label (processed left to
    right) in the first vertical tier whose most-recently-placed
    label is at least MIN_GAP away, so labels sharing a tier never
    overlap horizontally - avoids hand-placing ~28 leader lines."""
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
    svg = []

    def put(s):
        svg.append(s)

    W, H = 1920, 1200  # H is a placeholder; corrected below once layout is known
    put(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Helvetica, Arial, sans-serif">')
    put(f'<rect x="0" y="0" width="{W}" height="{H}" fill="#ffffff"/>')

    put(f'<text x="{W/2}" y="48" text-anchor="middle" font-size="30" font-weight="700" fill="#111827">PocketBeagle 1 – light-desk pinout (component side)</text>')
    put(f'<text x="{W/2}" y="78" text-anchor="middle" font-size="17" fill="#4b5563">P1/P2 expansion headers – project-committed connections highlighted – see pb1/pinout-reference.md for the full pinmux table</text>')

    put(f'<rect x="{BOARD_LEFT}" y="{BOARD_TOP}" width="{BOARD_RIGHT-BOARD_LEFT}" height="{BOARD_BOTTOM-BOARD_TOP}" rx="26" ry="26" fill="#1f2430" stroke="#0b0d12" stroke-width="3"/>')

    usb_y = (BOARD_TOP + BOARD_BOTTOM) / 2
    put(f'<rect x="{BOARD_LEFT-34}" y="{usb_y-26}" width="46" height="52" rx="6" fill="#c7cdd6" stroke="#4b5563" stroke-width="2"/>')
    put(f'<text x="{BOARD_LEFT-44}" y="{usb_y+60}" text-anchor="start" font-size="16" fill="#111827" font-weight="600">USB micro-B</text>')
    put(f'<text x="{BOARD_LEFT-44}" y="{usb_y+80}" text-anchor="start" font-size="14" fill="#374151">(X1)</text>')

    sd_x, sd_y, sd_w, sd_h = BOARD_RIGHT - 260, BOARD_TOP + 55, 190, 95
    put(f'<rect x="{sd_x}" y="{sd_y}" width="{sd_w}" height="{sd_h}" rx="6" fill="#30343f" stroke="#9ca3af" stroke-width="2"/>')
    put(f'<text x="{sd_x+sd_w/2}" y="{sd_y+sd_h/2+6}" text-anchor="middle" font-size="15" fill="#e5e7eb">microSD (X2)</text>')

    proc_size = 190
    proc_x, proc_y = BOARD_RIGHT - 300, (BOARD_TOP + BOARD_BOTTOM) / 2 - proc_size / 2 + 30
    put(f'<rect x="{proc_x}" y="{proc_y}" width="{proc_size}" height="{proc_size}" rx="8" fill="#111318" stroke="#6b7280" stroke-width="2"/>')
    put(f'<text x="{proc_x+proc_size/2}" y="{proc_y+proc_size/2-6}" text-anchor="middle" font-size="16" fill="#e5e7eb" font-weight="600">AM3358</text>')
    put(f'<text x="{proc_x+proc_size/2}" y="{proc_y+proc_size/2+16}" text-anchor="middle" font-size="12" fill="#9ca3af">(OSD3358-SM)</text>')

    logo_x, logo_y = BOARD_LEFT + 150, (BOARD_TOP + BOARD_BOTTOM) / 2
    put(f'<text x="{logo_x}" y="{logo_y-10}" font-size="20" fill="#f59e0b" font-weight="700">beagleboard.org</text>')
    put(f'<text x="{logo_x}" y="{logo_y+20}" font-size="22" fill="#f3f4f6" font-weight="700">PocketBeagle</text>')

    put(f'<text x="{HEADER_LEFT-40}" y="{BOARD_BOTTOM-ROW_GAP+6}" text-anchor="end" font-size="20" fill="#e5e7eb" font-weight="700">P1</text>')
    put(f'<text x="{HEADER_LEFT-40}" y="{BOARD_TOP+ROW_GAP+6}" text-anchor="end" font-size="20" fill="#e5e7eb" font-weight="700">P2</text>')

    for header in ("P1", "P2"):
        for pin in range(1, 37):
            x, y = pin_xy(header, pin)
            put(f'<circle cx="{x}" cy="{y}" r="{PIN_R_SMALL}" fill="#6b7280"/>')
    for header in ("P1", "P2"):
        x, y = pin_xy(header, 1)
        put(f'<rect x="{x-9}" y="{y-9}" width="18" height="18" fill="none" stroke="#f59e0b" stroke-width="2"/>')

    put(f'<text x="{colx(1)}" y="{BOARD_BOTTOM+28}" text-anchor="middle" font-size="13" fill="#6b7280">pin 1</text>')
    put(f'<text x="{colx(1)}" y="{BOARD_TOP-18}" text-anchor="middle" font-size="13" fill="#6b7280">pin 1</text>')
    put(f'<text x="{colx(35)}" y="{BOARD_BOTTOM+28}" text-anchor="middle" font-size="13" fill="#6b7280">pin 35/36</text>')
    put(f'<text x="{colx(35)}" y="{BOARD_TOP-18}" text-anchor="middle" font-size="13" fill="#6b7280">pin 35/36</text>')

    p1_pins = sorted((p for p in PINS if p[0] == "P1"), key=lambda p: colx(p[1]))
    p2_pins = sorted((p for p in PINS if p[0] == "P2"), key=lambda p: colx(p[1]))

    def draw_label_block(entries, header, direction):
        tiers = assign_tiers(entries)
        for (hdr, pin, cat, short, note), tier in zip(entries, tiers):
            x, y = pin_xy(hdr, pin)
            color = COLORS[cat]
            put(f'<circle cx="{x}" cy="{y}" r="{PIN_R_BIG}" fill="{color}" stroke="#111318" stroke-width="1.5"/>')

            ly = (BOARD_BOTTOM + 60 + tier * TIER_H) if header == "P1" else (BOARD_TOP - 60 - tier * TIER_H)
            lx = x

            put(f'<line x1="{x}" y1="{y + 16*direction}" x2="{lx}" y2="{ly - 12*direction}" stroke="{color}" stroke-width="1.5"/>')
            put(f'<circle cx="{lx}" cy="{ly}" r="4" fill="{color}"/>')

            pin_name = f"{hdr}.{pin:02d}"
            put(f'<text x="{lx+9}" y="{ly+5}" font-size="14" font-weight="700" fill="#111827">{esc(pin_name)}</text>')
            sub = short if not note else f"{short} ({note})"
            put(f'<text x="{lx+9}" y="{ly+22}" font-size="12" fill="#374151">{esc(sub)}</text>')
        return max(tiers) if tiers else 0

    max_p1_tier = draw_label_block(p1_pins, "P1", +1)
    draw_label_block(p2_pins, "P2", -1)

    leg_x = BOARD_LEFT
    leg_y = BOARD_BOTTOM + 70 + (max_p1_tier + 1) * TIER_H + 70
    put(f'<text x="{leg_x}" y="{leg_y-14}" font-size="16" font-weight="700" fill="#111827">Legend</text>')
    col_w = 620
    for i, (cat, desc) in enumerate(LEGEND):
        cx = leg_x + (i // 5) * col_w
        cy = leg_y + (i % 5) * 28
        put(f'<rect x="{cx}" y="{cy-12}" width="18" height="18" rx="3" fill="{COLORS[cat]}"/>')
        put(f'<text x="{cx+26}" y="{cy+3}" font-size="14" fill="#1f2937">{esc(desc)}</text>')

    put("</svg>")

    h_final = int(leg_y + 5 * 28 + 60)
    svg[0] = svg[0].replace(f"0 0 {W} {H}", f"0 0 {W} {h_final}")
    svg[1] = svg[1].replace(f'height="{H}"', f'height="{h_final}"')

    out_path = Path(__file__).resolve().parent / "pinout-diagram.svg"
    out_path.write_text("\n".join(svg))
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
