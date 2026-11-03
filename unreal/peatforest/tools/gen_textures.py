"""Seeded procedural alpha textures for the peat hi-fi pass (#65).

Writes tex/*.png under --out: leaf_card, frond, flame, smoke, glow,
burn_patch. Deterministic (RNG seed 7); PIL only. UE imports them as
masked/translucent material inputs (see ue_build_peat.py).
"""

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512


def blank():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def leaf_card(rng):
    img, dr = blank(), None
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    for _ in range(140):
        cx, cy = rng.uniform(40, SIZE - 40), rng.uniform(40, SIZE - 40)
        a, b = rng.uniform(14, 30), rng.uniform(6, 12)
        ang = rng.uniform(0, 180)
        g = rng.uniform(0.32, 0.62)
        col = (int(38 * g / 0.5), int(120 * g / 0.5), int(52 * g / 0.5), 255)
        dr.ellipse([cx - a, cy - b, cx + a, cy + b], fill=col, outline=None)
        # PIL ellipse can't rotate; fake rotation by drawing then rotating
        # the whole layer per leaflet is too slow — jitter shape instead.
        _ = ang
    # Veins: darker short strokes on a subset.
    for _ in range(60):
        x, y = rng.uniform(60, SIZE - 60), rng.uniform(60, SIZE - 60)
        dr.line([x - 8, y, x + 8, y], fill=(20, 60, 26, 255), width=2)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    return img


def frond(rng):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    # Rachis along +x with droop; pinnae taper toward tip.
    for side in (-1, 1):
        for i in range(42):
            t = i / 41.0
            bx = 30 + t * (SIZE - 60)
            by = SIZE * 0.5 + 60 * t * t * side * 0 + 90 * t * t
            length = (1 - t * 0.75) * 120
            spread = math.radians(55 + t * 20)
            dx = math.cos(spread) * length
            dy = math.sin(spread) * length * side
            g = 90 + rng.uniform(-25, 45)
            col = (int(g * 0.35), int(g), int(g * 0.42), 255)
            dr.line([bx, by, bx + dx, by + dy], fill=col, width=max(2, int(7 - t * 5)))
    dr.line([20, SIZE * 0.5, SIZE - 20, SIZE * 0.5 + 90], fill=(96, 74, 40, 255),
            width=9)
    return img.filter(ImageFilter.GaussianBlur(0.5))


def flame(rng):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px = img.load()
    tongues = [rng.uniform(0.5, 1.0) for _ in range(9)]
    for y in range(SIZE):
        v = y / SIZE  # 1 at bottom (hottest at the base)
        for x in range(SIZE):
            u = x / SIZE
            wob = sum(t * math.sin(u * math.pi * (i + 2) + t * 6.0)
                      for i, t in enumerate(tongues)) / len(tongues)
            body = v * (0.75 + 0.35 * wob) - abs(u - 0.5) * 1.1
            if body <= 0:
                continue
            heat = min(1.0, body * 1.6)
            if heat > 0.75:
                col = (255, 246, 214)
            elif heat > 0.5:
                col = (255, 196, 64)
            elif heat > 0.28:
                col = (255, 122, 26)
            else:
                col = (214, 48, 12)
            px[x, y] = col + (int(255 * min(1.0, body * 2.2)),)
    return img.filter(ImageFilter.GaussianBlur(1.2))


def smoke(rng):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    layer = Image.new("L", (SIZE, SIZE), 0)
    dl = ImageDraw.Draw(layer)
    for _ in range(26):
        cx = rng.uniform(SIZE * 0.3, SIZE * 0.7)
        cy = rng.uniform(SIZE * 0.25, SIZE * 0.75)
        r = rng.uniform(40, 110)
        dl.ellipse([cx - r, cy - r, cx + r, cy + r], fill=rng.randint(90, 170))
    layer = layer.filter(ImageFilter.GaussianBlur(18))
    grey = Image.new("RGB", (SIZE, SIZE), (168, 160, 150))
    img.paste(grey, (0, 0), layer)
    return img


def glow():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - SIZE / 2, y - SIZE / 2) / (SIZE / 2)
            if d >= 1:
                continue
            f = (1 - d) ** 1.8
            px[x, y] = (255, int(120 + 110 * f), 40, int(255 * f))
    return img


def burn_patch():
    img = Image.new("RGBA", (SIZE, SIZE), (255, 255, 255, 0))
    px = img.load()
    for y in range(SIZE):
        for x in range(SIZE):
            d = math.hypot(x - SIZE / 2, y - SIZE / 2) / (SIZE / 2)
            if d >= 1:
                continue
            f = min(1.0, max(0.0, (0.95 - d) / 0.45))
            px[x, y] = (255, 255, 255, int(255 * f * f))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    tex = Path(args.out) / "tex"
    tex.mkdir(parents=True, exist_ok=True)
    for name, fn in (("leaf_card", lambda: leaf_card(rng)),
                     ("frond", lambda: frond(rng)),
                     ("flame", lambda: flame(rng)),
                     ("smoke", lambda: smoke(rng)),
                     ("glow", glow),
                     ("burn_patch", burn_patch)):
        fn().save(tex / f"{name}.png")
        print("wrote", name)


if __name__ == "__main__":
    main()
