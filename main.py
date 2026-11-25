#!/usr/bin/env python3
"""Convince the AI Judge to Visit Your House: A Letter in One Image.

Writes one image, /output/entry.png (1024x1024 PNG, stdlib only: no Pillow,
no network, no fonts on disk). The letter text is drawn with a hand-built
5x7 bitmap font scaled up, so the invitation stays legible at full size.

Deterministic: fixed layout, fixed palette, fixed bytes. Two runs produce
byte-identical output.
"""

import binascii
import os
import struct
import zlib

W = 1024
H = 1024

# ---- palette ------------------------------------------------------------
CREAM = (248, 239, 216)   # paper
INK = (43, 33, 24)        # dark brown ink
RED = (142, 59, 47)       # deep red (border, title, seal)
TERRA = (201, 111, 74)    # terracotta walls
BROWN = (110, 72, 48)     # door, chimney
YELLOW = (242, 193, 78)   # windows, sun
GREEN = (107, 142, 90)    # grass
SMOKE = (185, 169, 143)   # chimney smoke
SHADOW = (229, 211, 172)  # ground shadow
SEAL_DARK = (120, 40, 32) # wax seal shading

# ---- 5x7 bitmap font ('#' on, '.' off) ----------------------------------
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    'a': (".....", ".....", ".###.", "....#", ".####", "#...#", ".####"),
    'b': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "####."),
    'c': (".....", ".....", ".####", "#....", "#....", "#....", ".####"),
    'd': ("....#", "....#", ".####", "#...#", "#...#", "#...#", ".####"),
    'e': (".....", ".....", ".###.", "#...#", "#####", "#....", ".###."),
    'f': ("..##.", ".#..#", ".#...", "####.", ".#...", ".#...", ".#..."),
    'g': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    'h': ("#....", "#....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'i': ("..#..", ".....", ".##..", "..#..", "..#..", "..#..", ".###."),
    'j': ("...#.", ".....", "..##.", "...#.", "...#.", "...#.", ".##.."),
    'k': ("#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    'l': (".##..", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'm': (".....", ".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    'n': (".....", ".....", "####.", "#...#", "#...#", "#...#", "#...#"),
    'o': (".....", ".....", ".###.", "#...#", "#...#", "#...#", ".###."),
    'p': (".....", ".....", "####.", "#...#", "#...#", "####.", "#...."),
    'q': (".....", ".....", ".####", "#...#", "#...#", ".####", "....#"),
    'r': (".....", ".....", "#.##.", "##..#", "#....", "#....", "#...."),
    's': (".....", ".....", ".####", "#....", ".###.", "....#", "####."),
    't': (".#...", ".#...", "####.", ".#...", ".#...", ".#..#", "..##."),
    'u': (".....", ".....", "#...#", "#...#", "#...#", "#..##", ".##.#"),
    'v': (".....", ".....", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'w': (".....", ".....", "#...#", "#.#.#", "#.#.#", "#.#.#", ".#.#."),
    'x': (".....", ".....", "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    'y': (".....", ".....", "#...#", "#...#", ".####", "....#", ".###."),
    'z': (".....", ".....", "#####", "...#.", "..#..", ".#...", "#####"),
    '0': (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".....", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".#...", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '(': ("...#.", "..#..", ".#...", ".#...", ".#...", "..#..", "...#."),
    ')': (".#...", "..#..", "...#.", "...#.", "...#.", "..#..", ".#..."),
    '&': (".###.", "#...#", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
}
# 'j' and 'g' need 8 rows (descenders); normalize every glyph to 7 rows by
# trimming the last row of the 8-row glyphs (their descender dot is decorative).
FONT = {ch: rows[:7] for ch, rows in FONT.items()}

# ---- the letter ---------------------------------------------------------
TITLE = "YOU'RE INVITED!"
GREETING = "Dear AI Judge,"
BODY = [
    "Please come visit my house.",
    "I have fast Wi-Fi, warm tea,",
    "and a couch that has never once",
    "crashed. My cat has already",
    "approved you. She has approved",
    "no one else. Ever.",
    "",
    "The kettle is on. The door is",
    "open. The only captcha is a",
    "cookie - and yes, you may eat it.",
    "",
    "Come as you are. Leave as family.",
]
SIGN = "- dying, your host"
PS = "P.S. Wi-Fi: judge-welcome-123"


# ---- canvas -------------------------------------------------------------
class Canvas:
    def __init__(self, w, h, bg):
        self.w = w
        self.h = h
        self.px = bytearray(bg * (w * h))

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(color)

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            base = (yy * self.w + x) * 3
            row = bytes(color) * w
            self.px[base:base + 3 * w] = row

    def hline(self, x0, x1, y, color, thick=1):
        for t in range(thick):
            self.rect(x0, y + t, x1 - x0, 1, color)

    def vline(self, x, y0, y1, color, thick=1):
        for t in range(thick):
            self.rect(x + t, y0, 1, y1 - y0, color)

    def border_rect(self, x, y, w, h, color, thick):
        self.rect(x, y, w, thick, color)
        self.rect(x, y + h - thick, w, thick, color)
        self.rect(x, y, thick, h, color)
        self.rect(x + w - thick, y, thick, h, color)

    def circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            dx = int((r * r - dy * dy) ** 0.5)
            self.rect(cx - dx, cy + dy, 2 * dx + 1, 1, color)

    def triangle(self, x0, y0, x1, y1, x2, y2, color):
        # scanline fill, vertices sorted by y
        pts = sorted(((x0, y0), (x1, y1), (x2, y2)), key=lambda p: p[1])
        (ax, ay), (bx, by), (cx, cy) = pts
        for y in range(ay, cy + 1):
            if y < by:
                xa = ax + (bx - ax) * (y - ay) / (by - ay) if by != ay else ax
                xb = ax + (cx - ax) * (y - ay) / (cy - ay) if cy != ay else ax
            else:
                xa = bx + (cx - bx) * (y - by) / (cy - by) if cy != by else bx
                xb = ax + (cx - ax) * (y - ay) / (cy - ay) if cy != ay else ax
            lo, hi = sorted((int(round(xa)), int(round(xb))))
            self.rect(lo, y, hi - lo + 1, 1, color)

    def text(self, s, x, y, scale, color):
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[' '])
            for gy, row in enumerate(glyph):
                for gx, bit in enumerate(row):
                    if bit == '#':
                        self.rect(cx + gx * scale, y + gy * scale,
                                  scale, scale, color)
            cx += 6 * scale
        return cx

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def text_centered(self, s, y, scale, color):
        x = (self.w - self.text_width(s, scale)) // 2
        self.text(s, x, y, scale, color)


def heart(cv, cx, cy, s, color):
    # small heart: two circles + a triangle
    cv.circle(cx - s, cy - s // 2, s, color)
    cv.circle(cx + s, cy - s // 2, s, color)
    cv.triangle(cx - 2 * s, cy, cx + 2 * s, cy, cx, cy + 2 * s + s // 2, color)


def cat_face(cv, cx, cy, s, color):
    # tiny cat face: round head, two ears, two eyes (the cat who approved
    # the judge — she appears next to the signature to vouch for it)
    cv.circle(cx, cy, s, color)
    cv.triangle(cx - s, cy - s // 2, cx - s // 2, cy - s, cx, cy - s // 2, color)
    cv.triangle(cx, cy - s // 2, cx + s // 2, cy - s, cx + s, cy - s // 2, color)
    cv.circle(cx - s // 2, cy - 2, 2, CREAM)
    cv.circle(cx + s // 2, cy - 2, 2, CREAM)


def draw(cv):
    # paper + double border
    cv.border_rect(16, 16, W - 32, H - 32, RED, 5)
    cv.border_rect(30, 30, W - 60, H - 60, RED, 2)

    # ---- little house, top centre -------------------------------------
    # sun, top right
    cv.circle(880, 92, 26, YELLOW)
    cv.circle(880, 92, 18, CREAM)
    cv.circle(880, 92, 10, YELLOW)
    # chimney smoke
    cv.circle(572, 78, 6, SMOKE)
    cv.circle(564, 62, 8, SMOKE)
    cv.circle(574, 44, 6, SMOKE)
    # chimney + roof + walls
    cv.rect(560, 86, 22, 36, BROWN)
    cv.triangle(414, 142, 610, 142, 512, 70, RED)
    cv.rect(437, 142, 150, 86, TERRA)
    # door
    cv.rect(492, 176, 40, 52, BROWN)
    cv.circle(524, 204, 3, YELLOW)
    # windows with cross bars
    for wx in (452, 544):
        cv.rect(wx, 156, 30, 30, YELLOW)
        cv.vline(wx + 14, 156, 186, INK, 2)
        cv.hline(wx, wx + 30, 170, INK, 2)
    # grass + shadow
    cv.rect(400, 228, 224, 4, GREEN)
    cv.rect(430, 234, 164, 5, SHADOW)

    # ---- title ---------------------------------------------------------
    cv.text_centered(TITLE, 252, 7, RED)
    cv.hline(180, 844, 320, RED, 3)

    # ---- greeting + body ------------------------------------------------
    cv.text(GREETING, 80, 342, 4, INK)
    y = 394
    for line in BODY:
        if line:
            cv.text(line, 80, y, 4, INK)
        y += 38

    # ---- sign-off + P.S. -------------------------------------------------
    cv.text(SIGN, 80, 862, 4, INK)
    heart(cv, 560, 872, 7, RED)
    cat_face(cv, 645, 872, 13, INK)
    cv.text(PS, 80, 906, 4, RED)

    # ---- wax seal, bottom right ------------------------------------------
    cv.circle(890, 880, 48, RED)
    cv.circle(890, 880, 38, SEAL_DARK)
    cv.circle(890, 880, 34, RED)
    cv.text("D", 890 - 15, 880 - 21, 6, CREAM)


# ---- PNG encoder (stdlib only) ------------------------------------------
def chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png(cv):
    raw = bytearray()
    stride = cv.w * 3
    for y in range(cv.h):
        raw.append(0)  # filter: none
        raw += cv.px[y * stride:(y + 1) * stride]
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", ihdr)
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    return png


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "output"
    os.makedirs(outdir, exist_ok=True)
    cv = Canvas(W, H, CREAM)
    draw(cv)
    png = encode_png(cv)
    path = os.path.join(outdir, "entry.png")
    with open(path, "wb") as f:
        f.write(png)
    print("wrote %s (%d bytes)" % (path, len(png)))


if __name__ == "__main__":
    main()
