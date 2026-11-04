"""Seeded procedural alpha textures for the peat hi-fi pass (#65).

Writes tex/*.png under --out: leaf_card, frond, flame, smoke, glow,
burn_patch, clouds. Deterministic (RNG seed 7); PIL only. UE imports
them as masked/translucent material inputs (see ue_build_peat.py).

BGR pre-swap: the UE import path renders texture R/B swapped
(probed: PIL-correct orange flames rendered blue until the bytes
were pre-swapped; see tests/test_terrain_gen.py). Every RGB output
here is saved R/B-swapped so it renders as authored. Grayscale and
white-alpha masks are unaffected but go through the same helper.
"""

import argparse
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

SIZE = 512


def blank():
    return Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))


def bgr(img):
    """Swap R/B channels (alpha untouched) for the UE import path."""
    r, g, b, a = img.convert("RGBA").split()
    return Image.merge("RGBA", (b, g, r, a))


def leaf_card(rng):
    # Dense cluster fill: each canopy blob maps the whole card ONCE, so
    # a sparse card (28% cover) masked whole crowns away (trees rendered
    # as sticks). Opaque dark base + layered leaflets + a few punched
    # depth holes (~8%): reads as a closed crown with interior shadow.
    img = Image.new("RGBA", (SIZE, SIZE), (14, 42, 18, 255))
    dr = ImageDraw.Draw(img)
    for _ in range(460):
        cx, cy = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
        a, b = rng.uniform(10, 26), rng.uniform(5, 11)
        g = rng.uniform(0.3, 0.75)
        col = (int(40 * g / 0.5), int(128 * g / 0.5), int(54 * g / 0.5), 255)
        dr.ellipse([cx - a, cy - b, cx + a, cy + b], fill=col, outline=None)
    for _ in range(90):
        x, y = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
        dr.line([x - 7, y, x + 7, y], fill=(18, 58, 24, 255), width=2)
    # Punch depth holes (wrapped, so blob UV seams stay clean).
    for _ in range(70):
        cx, cy = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
        r = rng.uniform(6, 16)
        for ox in (-SIZE, 0, SIZE):
            for oy in (-SIZE, 0, SIZE):
                dr.ellipse([cx - r + ox, cy - r + oy, cx + r + ox, cy + r + oy],
                           fill=(0, 0, 0, 0), outline=None)
    return img.filter(ImageFilter.GaussianBlur(0.6))


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


def clouds(rng):
    # Tileable cloud bank for the sky dome (wrapped blobs, soft alpha).
    # White is R/B-invariant; still saved via bgr() for uniformity.
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    layer = Image.new("L", (SIZE, SIZE), 0)
    dl = ImageDraw.Draw(layer)
    for _ in range(46):
        cx, cy = rng.uniform(0, SIZE), rng.uniform(0, SIZE)
        a, b = rng.uniform(34, 96), rng.uniform(15, 38)
        v = rng.randint(110, 230)
        for ox in (-SIZE, 0, SIZE):
            for oy in (-SIZE, 0, SIZE):
                dl.ellipse([cx - a + ox, cy - b + oy, cx + a + ox, cy + b + oy],
                           fill=v)
    layer = layer.filter(ImageFilter.GaussianBlur(6))
    # Broken cover (~45%): remap soft mids to transparent.
    layer = layer.point(lambda v: 0 if v < 70 else int((v - 70) * 1.35))
    shade = Image.new("RGB", (SIZE, SIZE), (244, 240, 232))
    img.paste(shade, (0, 0), layer)
    return img


PBR_FILES = ("bark_diff.jpg", "bark_nor.png", "mud_diff.jpg", "mud_nor.png",
             "burn_diff.jpg")


def swap_pbr(src_dir, out_dir):
    """BGR pre-swap vendored PBR bytes into derived ue_gen/pbr/.

    assets_raw/ stays pristine (hash-pinned in manifest.yaml); the
    swapped copies are derived artifacts the builder imports.
    """
    src, dst = Path(src_dir), Path(out_dir) / "pbr"
    dst.mkdir(parents=True, exist_ok=True)
    for name in PBR_FILES:
        img = Image.open(src / name)
        mode = img.mode
        out = bgr(img).convert(mode)
        kw = {"quality": 95} if name.endswith(".jpg") else {}
        out.save(dst / name, **kw)
        print("swapped", name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", required=True)
    ap.add_argument("--pbr-src", default=None,
                    help="assets_raw dir; when given, write BGR-swapped "
                         "copies to <out>/pbr/")
    args = ap.parse_args()
    tex = Path(args.out) / "tex"
    tex.mkdir(parents=True, exist_ok=True)
    # Per-texture sub-seeds: adding a texture never reshuffles the rest.
    jobs = (("leaf_card", lambda rng: leaf_card(rng)),
            ("frond", lambda rng: frond(rng)),
            ("flame", lambda rng: flame(rng)),
            ("smoke", lambda rng: smoke(rng)),
            ("glow", lambda rng: glow()),
            ("burn_patch", lambda rng: burn_patch()),
            ("clouds", lambda rng: clouds(rng)))
    for i, (name, fn) in enumerate(jobs):
        img = bgr(fn(random.Random(args.seed * 131 + i)))
        img.save(tex / f"{name}.png")
        print("wrote", name)
    if args.pbr_src:
        swap_pbr(args.pbr_src, args.out)


if __name__ == "__main__":
    main()
