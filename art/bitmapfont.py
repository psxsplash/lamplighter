# The menu's bitmap font: a glyph sheet PNG for a UI font's "bitmap" field.
#   python3 -P art/bitmapfont.py <outdir>
# Glyphs 0x20..0x7F in ASCII order, CELL_W x CELL_H cells, 256 px wide (16
# cells a row), white ink on a transparent ground. They come from Pillow's
# built-in 6 x 11 bitmap font drawn at twice its size, which keeps the hard
# pixel edges of a console font. The scene gives every glyph ADVANCE pixels.
import os
import sys

from PIL import Image, ImageDraw, ImageFont

CELL_W, CELL_H = 16, 24
ADVANCE = 12
SCALE = 2


def sheet():
    font = getattr(ImageFont, "load_default_imagefont", ImageFont.load_default)()
    cols = 256 // CELL_W
    img = Image.new("RGBA", (256, CELL_H * (96 // cols)), (0, 0, 0, 0))
    for i in range(96):
        ch = chr(0x20 + i)
        small = Image.new("L", (CELL_W // SCALE, CELL_H // SCALE), 0)
        ImageDraw.Draw(small).text((0, 0), ch, fill=255, font=font)
        big = small.resize((CELL_W, CELL_H), Image.NEAREST)
        ink = Image.new("RGBA", big.size, (255, 255, 255, 255))
        img.paste(ink, ((i % cols) * CELL_W, (i // cols) * CELL_H), big.point(lambda v: 255 if v >= 128 else 0))
    return img


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    sheet().save(os.path.join(out, "menu.png"))


main()
