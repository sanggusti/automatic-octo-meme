"""Hi-fi grove generator: 4 seeded variants + charred snags (#65).

Reads ue_gen/{placements,heights}.json + ../firms_tileC.json (hotspot
burn mask, 250 m). Writes merged per-material OBJs with UVs + vertex
tints (v x y z r g b, f v/vt), Z-up, y=-east_cm (import negates Y):

  trunk.obj    all trunks + palm trunks + branches (bark PBR)
  canopy.obj   tiers + blobs + bushes (leaf-card alpha, masked)
  frond.obj    palm fronds + nuts (frond alpha, double-sided)
  charred.obj  snags + branch stubs + fallen logs (dark bark)
  variants.json counts per variant (report + tests)

Per-tree seeded variant/yaw/scale/tint; deterministic (RNG seed 7).
"""

import argparse
import json
import math
import random
from pathlib import Path

SIDES = 10
HOTSPOT_R_M = 250.0


class Part:
    def __init__(self):
        self.v, self.vt, self.f = [], [], []

    def vert(self, x, y, z, u, vv, tint):
        self.v.append((x, y, z, *tint))
        self.vt.append((u, vv))
        return len(self.v)  # 1-based, v[i] <-> vt[i]

    def tri(self, a, b, c):
        self.f.append((a, b, c))

    def write(self, path):
        with open(path, "w") as fh:
            fh.write(f"# peatforest {Path(path).stem}\n")
            for x, y, z, r, g, b in self.v:
                fh.write(f"v {x:.1f} {y:.1f} {z:.1f} {r:.3f} {g:.3f} {b:.3f}\n")
            for u, vv in self.vt:
                fh.write(f"vt {u:.4f} {vv:.4f}\n")
            for a, b, c in self.f:
                fh.write(f"f {a}/{a} {b}/{b} {c}/{c}\n")


def yawed(dx, dy, ang):
    c, s = math.cos(ang), math.sin(ang)
    return dx * c + dy * s, -dx * s + dy * c


def tube(part, cx, cy, cz, r0, r1, h, tint, lean=(0.0, 0.0), vscale=1.0):
    """Tapered cylinder (outward-wound); returns top-center (x, y, z)."""
    rings = [(0.0, r0), (0.55, r0 * 0.82 + r1 * 0.18), (1.0, r1)]
    ids = []
    for t, r in rings:
        ring = []
        for i in range(SIDES):
            a = 2 * math.pi * i / SIDES
            dx, dy = yawed(r * math.cos(a), r * math.sin(a), 0.0)
            ring.append(part.vert(cx + dx + lean[0] * t, cy + dy + lean[1] * t,
                                  cz + h * t, i / SIDES, t * vscale, tint))
        ids.append(ring)
    for r in range(len(ids) - 1):
        for i in range(SIDES):
            a, b = ids[r][i], ids[r][(i + 1) % SIDES]
            c, d = ids[r + 1][i], ids[r + 1][(i + 1) % SIDES]
            part.tri(a, b, c)
            part.tri(b, d, c)
    return (cx + lean[0], cy + lean[1], cz + h)


def blob(part, cx, cy, cz, rx, ry, rz, tint, seed_ang=0.0, detail=(12, 7)):
    """Squashed ellipsoid canopy mass (outward-wound), lat bands."""
    nlon, nlat = detail
    grid = []
    for j in range(1, nlat):
        phi = math.pi * j / nlat
        ring = []
        for i in range(nlon):
            th = 2 * math.pi * i / nlon + seed_ang
            dx = rx * math.sin(phi) * math.cos(th)
            dy = ry * math.sin(phi) * math.sin(th)
            dz = rz * math.cos(phi)
            ring.append(part.vert(cx + dx, cy + dy, cz + dz,
                                  i / nlon, j / nlat, tint))
        grid.append(ring)
    top = part.vert(cx, cy, cz + rz, 0.5, 1.0, tint)
    bot = part.vert(cx, cy, cz - rz, 0.5, 0.0, tint)
    for i in range(nlon):
        part.tri(grid[0][i], grid[0][(i + 1) % nlon], top)
    for r in range(len(grid) - 1):
        for i in range(nlon):
            a, b = grid[r][i], grid[r][(i + 1) % nlon]
            c, d = grid[r + 1][i], grid[r + 1][(i + 1) % nlon]
            part.tri(a, b, c)
            part.tri(b, d, c)
    last = grid[-1]
    for i in range(nlon):
        part.tri(bot, last[(i + 1) % nlon], last[i])


def frond(part, cx, cy, cz, length, width, yaw, pitch0, tint):
    """Drooping palm frond: bent strip, u along, v across."""
    n = 6
    ids = []
    for s in range(n + 1):
        t = s / n
        # Rise then droop; taper width toward the tip.
        along = t * length
        up = math.sin(t * math.pi * 0.55) * length * 0.28 - t * t * length * 0.45
        w = width * (1 - t * 0.8) / 2
        px, py = yawed(along, 0.0, yaw)
        qx, qy = yawed(0.0, 1.0, yaw)
        ids.append((part.vert(cx + px - qx * w, cy + py - qy * w, cz + up,
                              t, 0.0, tint),
                    part.vert(cx + px + qx * w, cy + py + qy * w, cz + up,
                              t, 1.0, tint)))
    for s in range(n):
        a0, a1 = ids[s]
        b0, b1 = ids[s + 1]
        part.tri(a0, b0, a1)
        part.tri(a1, b0, b1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    gen = Path(args.gen)
    rng = random.Random(args.seed)
    trees = json.loads((gen / "placements.json").read_text())["trees"]
    hh = json.loads((gen / "heights.json").read_text())
    step, n, hs = hh["step_m"], hh["n"], hh["heights_cm"]
    hot = json.loads((gen.parent / "firms_tileC.json").read_text())
    hot_m = []
    for h in hot:
        ex = (float(h["longitude"]) - 114.318) * 111320.0 * math.cos(math.radians(-2.86))
        ny = (float(h["latitude"]) - (-2.86)) * 110540.0
        hot_m.append((ex, ny))

    def ground(ex, ny):
        fx = min(n - 1.001, max(0.0, ex / step))
        fy = min(n - 1.001, max(0.0, ny / step))
        x0, y0 = int(fx), int(fy)
        tx, ty = fx - x0, fy - y0
        return (hs[y0][x0] * (1 - tx) * (1 - ty) + hs[y0][x0 + 1] * tx * (1 - ty)
                + hs[y0 + 1][x0] * (1 - tx) * ty + hs[y0 + 1][x0 + 1] * tx * ty)

    trunk, canopy, fronds, charred = Part(), Part(), Part(), Part()
    counts = {"emergent": 0, "palm": 0, "round": 0, "bush": 0, "charred": 0,
              "logs": 0}

    for t in trees:
        ex, ny = t["x_m"], t["y_m"]
        ux, uz = ny * 100.0, -ex * 100.0  # y=-east (import negates Y)
        gz = ground(ex, ny)
        burnt = min(math.hypot(ex - hx, ny - hy) for hx, hy in hot_m) < HOTSPOT_R_M
        yaw = rng.uniform(0, 2 * math.pi)
        sc = rng.uniform(0.85, 1.2)
        tj = rng.uniform(-0.1, 0.1)
        tint = tuple(min(1.0, v) for v in (1.0 + tj, 1.0 + tj, 1.0 + tj * 0.5))
        if burnt:
            counts["charred"] += 1
            top = tube(charred, ux, uz, gz, 32 * sc, 20 * sc, 620 * sc, tint)
            for _ in range(rng.randint(2, 3)):
                ba = rng.uniform(0, 2 * math.pi)
                bx = top[0] + rng.uniform(-40, 40) * sc
                by = top[1] + rng.uniform(-40, 40) * sc
                bz = top[2] - rng.uniform(60, 220) * sc
                dx, dy = math.cos(ba) * 160 * sc, math.sin(ba) * 160 * sc
                tube(charred, bx, by, bz, 9 * sc, 4 * sc, 60 * sc, tint,
                     lean=(dx, dy))
            if rng.random() < 0.3:
                counts["logs"] += 1
                la = rng.uniform(0, 2 * math.pi)
                lx = ux + rng.uniform(150, 400)
                ly = uz + rng.uniform(-200, 200)
                tube(charred, lx, ly, ground(max(0, -(ly) / 100.0),
                                             max(0, lx / 100.0)) + 25,
                     26 * sc, 22 * sc, 30 * sc, tint,
                     lean=(math.cos(la) * 420 * sc, math.sin(la) * 420 * sc))
            continue
        roll = rng.random()
        if roll < 0.40:  # emergent broadleaf: tall trunk + 3 tiers
            counts["emergent"] += 1
            top = tube(trunk, ux, uz, gz, 38 * sc, 24 * sc, 760 * sc, tint)
            for k, (r, dz) in enumerate(((450, 620), (350, 800), (240, 960))):
                blob(canopy, top[0] + rng.uniform(-30, 30),
                     top[1] + rng.uniform(-30, 30), gz + dz * sc,
                     r * sc, r * 0.9 * sc, r * 0.42 * sc, tint,
                     seed_ang=rng.uniform(0, 3))
        elif roll < 0.65:  # palm: curved trunk + 9 fronds + nuts
            counts["palm"] += 1
            lean = (rng.uniform(-90, 90), rng.uniform(-90, 90))
            top = tube(trunk, ux, uz, gz, 26 * sc, 20 * sc, 800 * sc, tint,
                       lean=lean)
            for k in range(9):
                fa = yaw + k * 2 * math.pi / 9 + rng.uniform(-0.1, 0.1)
                frond(fronds, top[0], top[1], top[2], 360 * sc, 95 * sc, fa,
                      0.0, tint)
            for _ in range(3):
                na = rng.uniform(0, 2 * math.pi)
                blob(fronds, top[0] + math.cos(na) * 30 * sc,
                     top[1] + math.sin(na) * 30 * sc, top[2] - 40 * sc,
                     22 * sc, 22 * sc, 22 * sc, (0.55, 0.42, 0.3),
                     detail=(6, 4))
        elif roll < 0.85:  # round canopy: trunk + 2 blobs
            counts["round"] += 1
            top = tube(trunk, ux, uz, gz, 30 * sc, 20 * sc, 420 * sc, tint)
            for dz, r in ((520, 300), (680, 210)):
                blob(canopy, top[0] + rng.uniform(-25, 25),
                     top[1] + rng.uniform(-25, 25), gz + dz * sc,
                     r * sc, r * sc, r * 0.55 * sc, tint,
                     seed_ang=rng.uniform(0, 3))
        else:  # understory bush: dark squashed blob
            counts["bush"] += 1
            dark = (tint[0] * 0.72, tint[1] * 0.75, tint[2] * 0.72)
            blob(canopy, ux, uz, gz + 130 * sc, 190 * sc, 170 * sc, 120 * sc,
                 dark, seed_ang=rng.uniform(0, 3))

    out = Path(args.out)
    trunk.write(out / "trunk.obj")
    canopy.write(out / "canopy.obj")
    fronds.write(out / "frond.obj")
    charred.write(out / "charred.obj")
    (out / "variants.json").write_text(json.dumps(counts, indent=1))
    print(f"{len(trees)} trees -> {out} {counts}")


if __name__ == "__main__":
    main()
