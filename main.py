#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""The World Today - one image summing up the world news of Tuesday
17 November 2026. Pure standard library: draws a newspaper front page
into a 1024x1024 RGB canvas and writes it as a PNG with a hand-rolled
encoder. No network, no clock, no randomness: two runs write byte-identical
files. Writes /output/entry.png, or $MAKEFUN_OUTPUT_DIR/entry.png."""

import os
import struct
import zlib

W = 1024
H = 1024

PAPER = (246, 241, 231)
INK = (20, 20, 20)
RED = (179, 39, 30)
BLUE = (29, 78, 137)
NAVY = (23, 42, 68)
SKY = (183, 205, 224)
SEA = (46, 99, 140)
GREY = (110, 110, 104)
LGREY = (200, 196, 186)
ORANGE = (232, 122, 28)
YELLOW = (240, 196, 60)
WHITE = (250, 250, 248)
GREEN = (46, 125, 70)


class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(w * h * 3)
        r, g, b = bg
        for i in range(0, len(self.px), 3):
            self.px[i] = r
            self.px[i + 1] = g
            self.px[i + 2] = b

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i] = c[0]
            self.px[i + 1] = c[1]
            self.px[i + 2] = c[2]

    def rect(self, x, y, w, h, c):
        x0 = max(0, x)
        y0 = max(0, y)
        x1 = min(self.w, x + w)
        y1 = min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i] = c[0]
                self.px[i + 1] = c[1]
                self.px[i + 2] = c[2]

    def hline(self, x, y, w, c, t=1):
        self.rect(x, y, w, t, c)

    def vline(self, x, y, h, c, t=1):
        self.rect(x, y, t, h, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx = abs(x1 - x0)
        dy = -abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx + dy
        x, y = x0, y0
        while True:
            self.rect(x - t // 2, y - t // 2, t, t, c)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy) <= r * r:
                    self.set(xx, yy, c)

    def disc(self, cx, cy, r, c):
        self.circle(cx, cy, r, c)

    def ring(self, cx, cy, r, c, t=2):
        for yy in range(cy - r - t, cy + r + t + 1):
            for xx in range(cx - r - t, cx + r + t + 1):
                d2 = (xx - cx) * (xx - cx) + (yy - cy) * (yy - cy)
                if (r - t) * (r - t) <= d2 <= (r + t) * (r + t):
                    self.set(xx, yy, c)

    def triangle(self, x0, y0, x1, y1, x2, y2, c):
        minx = max(0, min(x0, x1, x2))
        maxx = min(self.w - 1, max(x0, x1, x2))
        miny = max(0, min(y0, y1, y2))
        maxy = min(self.h - 1, max(y0, y1, y2))
        den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if den == 0:
            return
        for yy in range(miny, maxy + 1):
            for xx in range(minx, maxx + 1):
                a = ((y1 - y2) * (xx - x2) + (x2 - x1) * (yy - y2)) / den
                b = ((y2 - y0) * (xx - x2) + (x0 - x2) * (yy - y2)) / den
                cc = 1 - a - b
                if a >= 0 and b >= 0 and cc >= 0:
                    self.set(xx, yy, c)


# 5x7 bitmap font, one glyph = 7 rows of 5 cells ('#' on, '.' off).
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    ',': ("00000", "00000", "00000", "00000", "01100", "00100", "01000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
    ';': ("00000", "01100", "01100", "00000", "01100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00110", "00100", "00000", "00100"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '+': ("00000", "00100", "00100", "01110", "00100", "00100", "00000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
}


def glyph_rows(ch):
    return FONT.get(ch, FONT['?'] if '?' in FONT else FONT['X'])


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(cv, x, y, s, scale, color):
    cx = x
    for ch in s:
        rows = FONT.get(ch.upper())
        if rows is None:
            rows = FONT['?'] if '?' in FONT else FONT['X']
        for ry in range(7):
            row = rows[ry]
            for rx in range(5):
                if row[rx] == '1':
                    cv.rect(cx + rx * scale, y + ry * scale, scale, scale, color)
        cx += 6 * scale
    return cx


def draw_text_centered(cv, cx, y, s, scale, color):
    x = cx - text_width(s, scale) // 2
    draw_text(cv, x, y, s, scale, color)
    return x


def wrap_text(s, max_chars):
    words = s.split(' ')
    lines = []
    cur = ''
    for w in words:
        if cur == '':
            cur = w
        elif len(cur) + 1 + len(w) <= max_chars:
            cur = cur + ' ' + w
        else:
            lines.append(cur)
            cur = w
    if cur != '':
        lines.append(cur)
    return lines


def para(cv, x, y, w, s, scale, color, leading=None):
    if leading is None:
        leading = 9 * scale
    max_chars = max(1, (w + scale) // (6 * scale))
    lines = wrap_text(s, max_chars)
    for ln in lines:
        draw_text(cv, x, y, ln, scale, color)
        y += leading
    return y


def headline(cv, x, y, w, s, scale, color):
    return para(cv, x, y, w, s, scale, color, leading=9 * scale + 2)


def kicker(cv, x, y, s, color=RED):
    draw_text(cv, x, y, s, 2, color)
    return y + 16


def chunk_crc(chunk_type, data):
    crc = zlib.crc32(chunk_type)
    crc = zlib.crc32(data, crc)
    return struct.pack('>I', crc & 0xFFFFFFFF)


def write_png(path, cv):
    raw = bytearray()
    for yy in range(cv.h):
        raw.append(0)
        raw += cv.px[yy * cv.w * 3:(yy + 1) * cv.w * 3]
    comp = zlib.compress(bytes(raw), 9)
    out = bytearray()
    out += b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', cv.w, cv.h, 8, 2, 0, 0, 0)
    out += struct.pack('>I', 13) + b'IHDR' + ihdr + chunk_crc(b'IHDR', ihdr)
    out += struct.pack('>I', len(comp)) + b'IDAT' + comp + chunk_crc(b'IDAT', comp)
    out += struct.pack('>I', 0) + b'IEND' + chunk_crc(b'IEND', b'')
    with open(path, 'wb') as f:
        f.write(bytes(out))
    return len(out)


# ---- illustrations (all drawn from fixed coordinates) ----

def draw_bridge(cv, x, y, w, h):
    """Kerch bridge over the strait: deck broken, one span down in the water."""
    cv.rect(x, y, w, h, SKY)
    sea_y = y + int(h * 0.62)
    cv.rect(x, sea_y, w, h - int(h * 0.62), SEA)
    # sun haze
    cv.disc(x + w - 46, y + 26, 14, YELLOW)
    # land on both banks
    cv.rect(x, sea_y - 26, 70, 26, LGREY)
    cv.rect(x + w - 70, sea_y - 26, 70, 26, LGREY)
    # deck: left part, gap, right part
    deck_y = sea_y - 34
    cv.rect(x + 8, deck_y, 190, 7, INK)
    cv.rect(x + w - 198, deck_y, 190, 7, INK)
    # fallen span, tilted into the water
    cv.line(x + 205, deck_y + 3, x + 300, sea_y + 34, INK, 6)
    cv.line(x + 205, deck_y + 3, x + 300, sea_y + 34, WHITE, 2)
    # pylons
    cv.rect(x + 60, deck_y - 52, 6, 52, INK)
    cv.rect(x + w - 66, deck_y - 52, 6, 52, INK)
    cv.line(x + 63, deck_y - 52, x + 150, deck_y, GREY, 2)
    cv.line(x + w - 63, deck_y - 52, x + w - 150, deck_y, GREY, 2)
    # supports in the water
    cv.rect(x + 96, deck_y + 7, 8, sea_y - deck_y + 22, INK)
    cv.rect(x + w - 104, deck_y + 7, 8, sea_y - deck_y + 22, INK)
    # waves
    for i in range(9):
        wx = x + 12 + i * 58
        cv.line(wx, sea_y + 18, wx + 22, sea_y + 12, WHITE, 2)
        cv.line(wx + 22, sea_y + 12, wx + 44, sea_y + 18, WHITE, 2)
    # smoke over the gap
    cv.disc(x + 250, deck_y - 26, 16, GREY)
    cv.disc(x + 272, deck_y - 44, 20, (140, 140, 132))
    cv.disc(x + 292, deck_y - 66, 14, (170, 170, 162))
    # blast flash
    cv.triangle(x + 236, deck_y - 6, x + 258, deck_y - 34, x + 268, deck_y - 2, ORANGE)
    cv.triangle(x + 244, deck_y - 2, x + 262, deck_y - 26, x + 276, deck_y - 4, YELLOW)


def draw_tanker(cv, x, y, w, h):
    """Oil tanker on fire with a spiked naval mine beside it."""
    cv.rect(x, y, w, h, SKY)
    sea_y = y + 80
    cv.rect(x, sea_y, w, h - 80, SEA)
    cv.disc(x + w - 40, y + 22, 12, YELLOW)
    # tanker hull
    hx, hy, hw, hh = x + 18, y + 50, 190, 30
    cv.rect(hx, hy, hw, hh, (150, 42, 32))
    cv.triangle(hx + hw, hy, hx + hw + 26, hy + hh // 2, hx + hw, hy + hh, (150, 42, 32))
    cv.rect(hx, hy + hh - 6, hw, 6, INK)
    # deckhouse + funnel
    cv.rect(hx + 22, hy - 26, 34, 26, WHITE)
    cv.rect(hx + 66, hy - 36, 12, 36, (150, 42, 32))
    cv.rect(hx + 66, hy - 36, 12, 6, INK)
    # fire on deck
    cv.triangle(hx + 110, hy - 2, hx + 128, hy - 34, hx + 146, hy - 2, ORANGE)
    cv.triangle(hx + 122, hy - 2, hx + 136, hy - 26, hx + 152, hy - 2, YELLOW)
    cv.triangle(hx + 96, hy - 2, hx + 108, hy - 22, hx + 120, hy - 2, ORANGE)
    # smoke
    cv.disc(hx + 126, hy - 40, 9, GREY)
    cv.disc(hx + 140, hy - 48, 7, (140, 140, 132))
    # naval mine, lower right
    mx, my = x + w - 52, sea_y + 12
    cv.disc(mx, my, 11, INK)
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, -1), (-1, 1), (1, 1)):
        cv.line(mx, my, mx + dx * 17, my + dy * 17, INK, 2)
    cv.disc(mx, my, 4, GREY)
    # waves
    for i in range(6):
        wx = x + 10 + i * 42
        cv.line(wx, sea_y + 14, wx + 16, sea_y + 10, WHITE, 2)
        cv.line(wx + 16, sea_y + 10, wx + 32, sea_y + 14, WHITE, 2)


def draw_flags(cv, x, y, w, h):
    """Three flags on poles: United States, China, Russia."""
    cv.rect(x, y, w, h, (232, 226, 214))
    pole_y = y + 18
    pole_h = 74
    fw, fh = 74, 46
    # US flag
    fx = x + 12
    for i in range(7):
        cv.rect(fx, pole_y + i * 6, fw, 6, RED if i % 2 == 0 else WHITE)
    cv.rect(fx, pole_y, 30, 24, BLUE)
    for sy in range(3):
        for sx in range(4):
            cv.set(fx + 4 + sx * 7, pole_y + 4 + sy * 7, WHITE)
    cv.rect(fx, pole_y, 2, pole_h, INK)
    cv.vline(fx, pole_y, pole_h, INK, 2)
    # China flag
    fx = x + w // 2 - fw // 2
    cv.rect(fx, pole_y, fw, fh, RED)
    cv.disc(fx + 14, pole_y + 12, 5, YELLOW)
    for sx, sy in ((30, 8), (38, 14), (38, 24), (30, 30)):
        cv.set(fx + sx, pole_y + sy, YELLOW)
        cv.set(fx + sx + 1, pole_y + sy, YELLOW)
    cv.vline(fx, pole_y, pole_h, INK, 2)
    # Russia flag
    fx = x + w - 12 - fw
    cv.rect(fx, pole_y, fw, 15, WHITE)
    cv.rect(fx, pole_y + 15, fw, 15, BLUE)
    cv.rect(fx, pole_y + 30, fw, 16, RED)
    cv.vline(fx, pole_y, pole_h, INK, 2)
    # ground line + caption
    cv.hline(x + 8, pole_y + pole_h + 2, w - 16, INK, 2)
    draw_text_centered(cv, x + w // 2, pole_y + pole_h + 10, "SHENZHEN - THU 19 NOV", 1, INK)


def draw_bank(cv, x, y, w, h):
    """Classical bank front with a glitch bolt across it."""
    cv.rect(x, y, w, h, (232, 226, 214))
    bx, by = x + 30, y + 10
    bw = w - 60
    # pediment + columns + steps
    cv.triangle(bx, by + 24, bx + bw // 2, by, bx + bw, by + 24, NAVY)
    cv.rect(bx, by + 24, bw, 6, NAVY)
    for i in range(4):
        cx = bx + 18 + i * ((bw - 36) // 3)
        cv.rect(cx, by + 30, 12, 48, NAVY)
    cv.rect(bx, by + 78, bw, 6, NAVY)
    cv.rect(bx - 8, by + 84, bw + 16, 6, GREY)
    # door
    cv.rect(bx + bw // 2 - 10, by + 52, 20, 26, INK)
    # glitch bolt
    pts = [(x + 46, y + 8), (x + 86, y + 40), (x + 66, y + 40), (x + 100, y + 76),
           (x + 76, y + 76), (x + 100, y + 100), (x + 60, y + 56), (x + 82, y + 56),
           (x + 52, y + 24)]
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], YELLOW, 5)
    for i in range(len(pts) - 1):
        cv.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], ORANGE, 2)


def draw_route(cv, x, y, w, h):
    """Europe to Rwanda: two labelled boxes joined by a dotted route."""
    cv.rect(x, y, w, h, (232, 226, 214))
    cv.rect(x + 10, y + 34, 74, 44, BLUE)
    draw_text_centered(cv, x + 47, y + 50, "EU", 2, WHITE)
    cv.rect(x + w - 108, y + 34, 98, 44, GREEN)
    draw_text_centered(cv, x + w - 59, y + 50, "RWANDA", 2, WHITE)
    x0 = x + 92
    x1 = x + w - 116
    yy = y + 56
    for dx in range(0, x1 - x0, 12):
        cv.rect(x0 + dx, yy - 2, 7, 4, RED)
    cv.triangle(x1, yy - 8, x1 + 14, yy, x1, yy + 8, RED)
    draw_text_centered(cv, x + w // 2, y + 92, "5 STATES - 1 HUB", 1, INK)


def draw_warning(cv, x, y, w, h):
    """Warning triangle over a broken wall: Gaza ceasefire under strain."""
    cv.rect(x, y, w, h, (232, 226, 214))
    cx, cy = x + w // 2, y + h // 2 - 6
    cv.triangle(cx, cy - 44, cx - 44, cy + 34, cx + 44, cy + 34, YELLOW)
    cv.triangle(cx, cy - 34, cx - 34, cy + 26, cx + 34, cy + 26, INK)
    cv.triangle(cx, cy - 28, cx - 28, cy + 20, cx + 28, cy + 20, YELLOW)
    cv.rect(cx - 3, cy - 16, 6, 26, INK)
    cv.rect(cx - 3, cy + 14, 6, 6, INK)
    draw_text_centered(cv, cx, y + h - 22, "WINTER BITES", 1, INK)


def draw_page(cv):
    # outer frame
    cv.rect(14, 14, W - 28, 3, INK)
    cv.rect(14, H - 17, W - 28, 3, INK)
    cv.rect(14, 14, 3, H - 28, INK)
    cv.rect(W - 17, 14, 3, H - 28, INK)

    # masthead
    draw_text_centered(cv, W // 2, 30, "THE WORLD TODAY", 7, INK)
    cv.hline(28, 94, W - 56, INK, 3)
    draw_text(cv, 28, 104, "TUESDAY, 17 NOVEMBER 2026", 2, INK)
    right = "ONE DAY - ONE IMAGE"
    draw_text(cv, W - 28 - text_width(right, 2), 104, right, 2, INK)
    cv.hline(28, 130, W - 56, INK, 2)

    # ---- lead story: the Crimean bridge ----
    kicker(cv, 28, 142, "UKRAINE - WAR IN EUROPE")
    headline(cv, 28, 164, 940, "CRIMEAN BRIDGE HIT: SPAN FALLS INTO THE SEA", 4, INK)
    draw_bridge(cv, 28, 232, 572, 190)
    para(cv, 620, 232, 376,
         "Ukraine struck the Kerch bridge for the second straight day. "
         "A road span collapsed into the strait, Kyiv said, calling it an "
         "unprecedented operation weeks in the making. The Kremlin vowed to "
         "rebuild. Overnight, Russian missiles hit two bridges over the "
         "Dnipro in Kyiv.",
         2, INK)
    cv.hline(28, 438, W - 56, INK, 2)

    # ---- middle row: three stories ----
    cols = [(28, "MIDDLE EAST - HORMUZ", draw_tanker,
             "TANKERS HIT BY MINES OFF HORMUZ",
             "Two tankers caught fire after hitting mines in the Strait of "
             "Hormuz. A third US carrier arrived in the region."),
            (364, "ASIA - DIPLOMACY", draw_flags,
             "TRUMP IN MANILA, SUMMIT THURSDAY",
             "China confirmed the first Xi-Trump-Putin meeting, set for "
             "Thursday in Shenzhen on the APEC sidelines."),
            (700, "BUSINESS - BANKING", draw_bank,
             "CHASE BUG HALTS ZELLE",
             "JPMorgan blamed a software bug, not a cyberattack, for "
             "Monday's outage that slowed banking.")]
    for x, kick, art, head, deck in cols:
        kicker(cv, x, 452, kick)
        art(cv, x, 470, 296, 110)
        headline(cv, x, 588, 296, head, 3, INK)
        para(cv, x, 648, 296, deck, 2, INK)
        if x < 700:
            cv.vline(x + 308, 452, 286, LGREY, 1)
    cv.hline(28, 744, W - 56, INK, 2)

    # ---- bottom row: two stories ----
    kicker(cv, 28, 758, "EUROPE - MIGRATION")
    headline(cv, 28, 778, 464, "FIVE EU STATES PLAN RWANDA RETURN HUB", 3, INK)
    para(cv, 28, 838, 464,
         "Germany, Denmark, Austria, Greece and the Netherlands plan a "
         "joint facility in Rwanda for rejected asylum seekers.",
         2, INK)
    cv.vline(508, 758, 152, LGREY, 1)
    kicker(cv, 532, 758, "GAZA - CEASEFIRE")
    headline(cv, 532, 778, 464, "GAZA - PEACE BOARD WARNS DEAL MAY COLLAPSE", 3, INK)
    para(cv, 532, 838, 464,
         "The Board of Peace gave a bleak first report to the UN Security "
         "Council. Agencies warn 1.4 million face acute hunger as winter bites.",
         2, INK)
    cv.hline(28, 916, W - 56, INK, 2)

    # ---- also today strip ----
    draw_text(cv, 28, 926, "ALSO TODAY", 2, RED)
    para(cv, 28, 948, 968,
         "Deutsche Bank leak: 15m files, shares down 4.7%. Nvidia reports "
         "after the Huang exit. Vulcan rocket fails, 40 Amazon satellites "
         "lost. COP31 talks go on in Turkiye. Japan scrambles jets.",
         2, INK)


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    cv = Canvas(W, H, PAPER)
    draw_page(cv)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, cv)
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
