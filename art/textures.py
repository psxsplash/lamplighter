# Procedural 64x64 textures, the 16x16 memory card icon and the lantern
# sprite sheet, deterministic (fixed seeds).
#   python3 -P art/textures.py <outdir>
import os
import random
import sys

from PIL import Image


def noise_tile(seed, base, spread, size=64, cell=8):
    rnd = random.Random(seed)
    grid = [[rnd.random() for _ in range(size // cell + 1)] for _ in range(size // cell + 1)]
    img = Image.new("RGB", (size, size))
    px = img.load()
    for y in range(size):
        for x in range(size):
            gx, gy = x / cell, y / cell
            ix, iy = int(gx), int(gy)
            fx, fy = gx - ix, gy - iy
            n = (grid[iy % (size // cell)][ix % (size // cell)] * (1 - fx) * (1 - fy)
                 + grid[iy % (size // cell)][(ix + 1) % (size // cell)] * fx * (1 - fy)
                 + grid[(iy + 1) % (size // cell)][ix % (size // cell)] * (1 - fx) * fy
                 + grid[(iy + 1) % (size // cell)][(ix + 1) % (size // cell)] * fx * fy)
            n += (rnd.random() - 0.5) * 0.25
            px[x, y] = tuple(max(0, min(255, int(c + (n - 0.5) * spread))) for c in base)
    return img


def sea_tile(seed, size=64):
    # Dark water: the noise squashed into horizontal streaks, with a few
    # brighter crests.
    img = noise_tile(seed, (26, 38, 62), 34, size=size).resize((size, size // 8)).resize(
        (size, size), Image.BILINEAR)
    rnd = random.Random(seed)
    px = img.load()
    for _ in range(18):
        x, y, n = rnd.randrange(size), rnd.randrange(size), rnd.randrange(3, 9)
        for i in range(n):
            r, g, b = px[(x + i) % size, y]
            px[(x + i) % size, y] = (r + 22, g + 28, b + 34)
    return img


# The memory card icon, 16 x 16 and one 16-colour palette: a lit beacon on a
# night sky. One character per pixel, keyed into ICON_COLOURS.
ICON = [
    "................",
    "......ffff......",
    ".....fFFFFf.....",
    "....fFYYYYFf....",
    "....fFYWWYFf....",
    ".....fFYYFf.....",
    "......ffff......",
    ".....cccccc.....",
    "......ssss......",
    "......sSSs......",
    "......ssss......",
    "......sSSs......",
    ".....ssssss.....",
    "....rrrrrrrr....",
    "...rrRRRRRRrr...",
    "..rrrrrrrrrrrr..",
]
ICON_COLOURS = {
    ".": (12, 16, 40, 255), "f": (160, 56, 16, 255), "F": (232, 120, 24, 255),
    "Y": (252, 200, 64, 255), "W": (255, 248, 200, 255), "c": (96, 92, 88, 255),
    "s": (120, 116, 108, 255), "S": (84, 80, 76, 255), "r": (52, 56, 64, 255),
    "R": (76, 80, 92, 255),
}


def icon():
    img = Image.new("RGBA", (16, 16))
    for y, row in enumerate(ICON):
        for x, ch in enumerate(row):
            img.putpixel((x, y), ICON_COLOURS[ch])
    return img


# The lantern sprite sheet, five 16 x 16 cells in a row and one 16-colour
# palette: cell 0 an unlit lantern, cells 1-4 the same lantern lit, its flame
# flickering. The valley's beacon tally plays them (`dark`, `flame`) and the
# title's menu cursor shows cell 0 (tools/scenes.py). "." is transparent.
LANTERN = [
    "......RRRR......",
    ".....R....R.....",
    "......RRRR......",
    "....rRRRRRRr....",
    "...rRRRRRRRRr...",
    "...R########R...",
    "...R########R...",
    "...R########R...",
    "...R########R...",
    "...R########R...",
    "...R########R...",
    "...R########R...",
    "...rRRRRRRRRr...",
    "....rRRRRRRr....",
    "....rr....rr....",
    "................",
]
# What fills the glass (the "#" block, 8 x 7): dark glass with a glint, then
# the flame in four shapes over a red glow.
LANTERN_GLASS = [
    ["gggggggg", "hggggggg", "hggggggg", "hggggggg", "gggggggg", "gggggggg", "gggggggg"],
    ["ffffffff", "fffFffff", "ffFYFfff", "ffFYYFff", "fFYWWYFf", "fFYWWYFf", "ffFYYFff"],
    ["ffffFfff", "ffffFfff", "fffFYFff", "ffFYYFff", "ffFYWYFf", "fFYWWYFf", "ffFYYFff"],
    ["ffffffff", "ffffffff", "fffFFfff", "ffFYYFff", "fFYWWYFf", "fFYWWYFf", "ffFYYFff"],
    ["fffFffff", "fffFffff", "ffFYFfff", "ffFYYFff", "fFYWYFff", "fFYWWYFf", "ffFYYFff"],
]
LANTERN_COLOURS = {
    ".": (0, 0, 0, 0), "r": (84, 80, 76, 255), "R": (132, 126, 116, 255),
    "g": (36, 44, 70, 255), "h": (110, 124, 160, 255), "f": (120, 44, 14, 255),
    "F": (232, 120, 24, 255), "Y": (252, 200, 64, 255), "W": (255, 248, 200, 255),
}


def lantern_sheet():
    img = Image.new("RGBA", (16 * len(LANTERN_GLASS), 16))
    for cell, glass in enumerate(LANTERN_GLASS):
        for y, row in enumerate(LANTERN):
            for x, ch in enumerate(row):
                if ch == "#":
                    ch = glass[y - 5][x - 4]
                img.putpixel((16 * cell + x, y), LANTERN_COLOURS[ch])
    return img


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    noise_tile(1, (88, 104, 72), 70).save(os.path.join(out, "grass.png"))
    noise_tile(2, (120, 116, 108), 80).save(os.path.join(out, "stone.png"))
    noise_tile(3, (70, 72, 82), 64).save(os.path.join(out, "rock.png"))
    sea_tile(4).save(os.path.join(out, "sea.png"))
    icon().save(os.path.join(out, "icon.png"))
    lantern_sheet().save(os.path.join(out, "lantern.png"))


main()
