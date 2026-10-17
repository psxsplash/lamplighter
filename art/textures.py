# Procedural 64x64 textures, deterministic (fixed seeds).
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


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    noise_tile(1, (88, 104, 72), 70).save(os.path.join(out, "grass.png"))
    noise_tile(2, (120, 116, 108), 80).save(os.path.join(out, "stone.png"))


main()
