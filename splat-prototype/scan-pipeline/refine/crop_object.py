"""Crop a trained splat of a small object to the object, and work out how to stand it up.

   python crop_object.py <data-dir> <in.ply> <out.ply> [--json object.json]
                         [--floor keep|drop] [--radius R] [--reach 0.05] [--no-fog-rule]

For an object the camera walked round (stage 1b, --subject object). Everything is found
from the cameras and the splats themselves; nothing is typed in:

1. Centre: the point all the cameras look at (closest point to every optical axis).
   Lengths below are in units of d, the median camera distance from it.
2. Solid: a cell 0.02 d wide is solid when the opacities of the small splats in it
   (largest axis under 0.05 d) add up to over 0.5. Splats in solid cells are "solid".
3. Floor: the plane that covers the most ground (with solid splats and the pose
   stage's points) and has almost nothing solid under it. Its normal is taken as true
   "up", which corrects a tilted camera.
4. Object: the largest connected lump of solid cells above the floor and inside the
   camera ring. Solid floaters do not touch it, so they are not part of it. Its radius
   and top are the lump's.
5. Kept: splats inside that cylinder (plus --margin), no fainter than --min-opacity and
   no larger than --max-scale. Above the floor a splat must also lie within --reach of
   the object, which removes floaters and the fog that hangs round it. The floor is
   removed; --floor keep leaves a disc of it under the object (worth it only when the
   floor came out well: on the test chair it was patchy).

Writes the cropped .ply in the same frame as the input (gsplat's normalised one), and
with --json the -r and -t for splat-transform (build-scene.sh's ROTATE and TRANSLATE)
that put the object upright on y = 0 at the origin, its size, and a starting camera.
"""
import argparse, json, os, sys
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
sys.path.insert(0, os.environ["GSPLAT_EXAMPLES"])
from datasets.colmap import Parser  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("data_dir"); ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--json", default="")
ap.add_argument("--floor", choices=["keep", "drop"], default="drop")
ap.add_argument("--radius", type=float, default=0, help="object radius in units of d, instead of the measured one")
ap.add_argument("--margin", type=float, default=0.05)
ap.add_argument("--min-opacity", type=float, default=0.005)
ap.add_argument("--max-scale", type=float, default=0.06)
ap.add_argument("--reach", type=float, default=0.05)
ap.add_argument("--no-fog-rule", action="store_true")
a = ap.parse_args()


def unit(v):
    return v / np.linalg.norm(v)


# ---- cameras ----
p = Parser(a.data_dir, factor=1, normalize=True, test_every=8)
c2w = np.asarray(p.camtoworlds, np.float64)
order = np.argsort(p.image_names)
C, fwd, cam_up = c2w[order, :3, 3], c2w[order, :3, 2], -c2w[order, :3, 1]
A = np.eye(3)[None] - fwd[:, :, None] * fwd[:, None, :]
centre = np.linalg.solve(A.sum(0), (A @ C[:, :, None]).sum(0)[:, 0])
d = float(np.median(np.linalg.norm(C - centre, axis=1)))
up = unit(cam_up.mean(0))

# ---- splats ----
with open(a.inp, "rb") as f:
    header = []
    while True:
        line = f.readline(); header.append(line)
        if line.strip() == b"end_header": break
    props = [h.split()[2].decode() for h in header if h.startswith(b"property")]
    n = int([h for h in header if h.startswith(b"element vertex")][0].split()[2])
    v = np.frombuffer(f.read(n * 4 * len(props)), dtype=[(q, "<f4") for q in props], count=n)
P = np.stack([v["x"], v["y"], v["z"]], 1).astype(np.float64)
op = 1 / (1 + np.exp(-v["opacity"].astype(np.float64)))
smax = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1).astype(np.float64)).max(1)
# "Solid" is judged by cell, not by splat: this trainer builds a surface from many faint
# splats (median opacity can be 0.02), so no single splat is opaque. A cell 0.02 d wide
# is solid when the opacities of the small splats in it add up to over 0.5.
small = smax < 0.05 * d
_, inv = np.unique(np.floor(P[small] / (0.02 * d)).astype(np.int64), axis=0, return_inverse=True)
solid = np.zeros(n, bool)
solid[small] = (np.bincount(inv.ravel(), weights=op[small]) > 0.5)[inv.ravel()]


def frame(up, centre):
    """Height above the centre and distance from the upright axis through it."""
    rel = P - centre
    h = rel @ up
    return h, np.linalg.norm(rel - h[:, None] * up, axis=1)


def area(q, normal):
    """How many 0.04 d squares of the plane with this normal the points q cover."""
    e1 = unit(np.cross(normal, [1.0, 0, 0] if abs(normal[0]) < 0.9 else [0, 1.0, 0])); e2 = np.cross(normal, e1)
    return len(np.unique(np.floor(np.stack([q @ e1, q @ e2], 1) / (0.04 * d)).astype(np.int64), axis=0))


# ---- floor: the widest flat sheet with almost nothing under it ----
# The camera's idea of "up" can be several degrees off, which smears the floor over a
# thick band of heights, so a height histogram does not find it. Instead try planes
# through three random points and keep the one that covers the most ground. A seat or a
# table top is a sheet too, but it has legs and the floor under it, so a plane with more
# than a fifth of the solid splats below it is not the floor. The points are the solid
# splats and the pose stage's own points, which mark a plain floor better than splats do.
h, r = frame(up, centre)
ring = solid & (r < 0.9 * d)
S = np.asarray(p.points, np.float64)
hs = (S - centre) @ up; rs = np.linalg.norm(S - centre - hs[:, None] * up, axis=1)
Q = np.concatenate([P[ring & (h < 0.1 * d)], S[(rs < 0.9 * d) & (hs < 0.1 * d)]])
rng = np.random.default_rng(0)
best_area, floor_tilt = 0, 0.0
for _ in range(600 if len(Q) > 200 else 0):
    q3 = Q[rng.choice(len(Q), 3, replace=False)]
    normal = np.cross(q3[1] - q3[0], q3[2] - q3[0])
    if np.linalg.norm(normal) < 1e-9: continue
    normal = unit(normal); normal = normal if normal @ up > 0 else -normal
    if normal @ up < np.cos(np.radians(30)): continue
    on = np.abs((Q - q3[0]) @ normal) < 0.01 * d
    got = area(Q[on], normal)
    if got > best_area and ((P[ring] - q3[0]) @ normal < -0.04 * d).mean() < 0.2:
        best_area, best_normal, best_point = got, normal, q3[0]
floor_ok = best_area >= 60                              # the whole 0.9 d disc is about 1,600 squares
if floor_ok:
    normal, mid = best_normal, best_point
    for band in (0.02, 0.01, 0.01):
        q = Q[np.abs((Q - mid) @ normal) < band * d]; mid = q.mean(0)
        normal = np.linalg.svd(q - mid, full_matrices=False)[2][2]
        normal = normal if normal @ up > 0 else -normal
    floor_tilt = float(np.degrees(np.arccos(np.clip(normal @ up, -1, 1))))
    up = normal
    h, r = frame(up, centre)
    h_floor = float((mid - centre) @ up)
else:
    h_floor = float(np.percentile(h[solid & (r < 0.9 * d)], 1))
h = h - h_floor                                       # height above the floor from here on

# ---- object: the largest connected lump of solid cells above the floor, inside the camera ring ----
# Floaters and fog can be solid too, but they do not touch the object. Cells count as
# touching across a gap of up to two cells (0.04 d), so a thin leg is not cut off.
rel_cam = C - centre
cam_r = np.linalg.norm(rel_cam - (rel_cam @ up)[:, None] * up, axis=1)
r_max = 0.7 * float(cam_r.min())
above = solid & (h > 0.03 * d) & (r < r_max)
obj = np.zeros(n, bool)
if above.sum() > 50:
    idx = np.floor(P[above] / (0.02 * d)).astype(np.int64); idx -= idx.min(0) - 2
    grid = np.zeros(idx.max(0) + 3, bool); grid[tuple(idx.T)] = True
    lumps, _ = ndimage.label(ndimage.binary_dilation(grid, iterations=1), structure=np.ones((3, 3, 3)))
    sizes = np.bincount(lumps[grid])
    obj[above] = lumps[tuple(idx.T)] == sizes.argmax()
    mid = np.median(P[obj], axis=0)                    # move the axis onto the object's middle
    centre = centre + (mid - centre) - ((mid - centre) @ up) * up
    _, r = frame(up, centre)
    lump_cells, other_cells = int(sizes.max()), int(sizes.sum() - sizes.max())
else:
    lump_cells = other_cells = 0
radius = a.radius * d if a.radius else (float(np.percentile(r[obj], 99.5)) if obj.any() else r_max)
top = float(np.percentile(h[obj], 99.9)) if obj.any() else 0.5 * d

# ---- what to keep ----
m = a.margin * d
inside = (r <= radius + m) & (h <= top + m)
good = (op >= a.min_opacity) & (smax <= a.max_scale * d)
slab = np.abs(h) <= 0.02 * d                           # the floor itself
body = h > 0.02 * d
if a.no_fog_rule or not obj.any():
    near = np.ones(n, bool)
else:
    cells = (np.unique(np.floor(P[obj] / (0.02 * d)).astype(np.int64), axis=0) + 0.5) * 0.02 * d
    dist, _ = cKDTree(cells).query(P, distance_upper_bound=a.reach * d)
    near = np.isfinite(dist)
keep = inside & good & ((body & near) | (slab if a.floor == "keep" else False))

# ---- the viewer's frame: +Y up, the first camera on +Z, object on the floor at the origin ----
first = C[0] - centre
z = unit(first - (first @ up) * up); x = np.cross(up, z)
R = np.stack([x, up, z])
base = centre + h_floor * up                            # the axis at floor height
t = -R @ base
Rs = R @ np.diag([-1.0, -1.0, 1.0])                    # splat-transform's .ply convention (level_to_rotate.py)
rot = np.degrees([np.arctan2(Rs[2, 1], Rs[2, 2]), -np.arcsin(np.clip(Rs[2, 0], -1, 1)), np.arctan2(Rs[1, 0], Rs[0, 0])])
pitch = np.degrees(np.arcsin(np.clip(-(fwd @ up), -1, 1)))        # how far each camera looked down
az = np.degrees(np.arctan2((C - centre) @ x, (C - centre) @ z))
gaps = np.diff(np.r_[np.sort(az), np.sort(az)[0] + 360])
cam_h = float(np.median((C - centre) @ up - h_floor))
# Starting view: far enough that the whole object fits with room to spare on an upright
# phone, and no steeper than 25 degrees, whatever height the camera was held at.
dist = 3.0 * float(np.hypot(radius, top / 2))
elev = np.radians(min(25.0, max(10.0, float(np.median(pitch)))))
res = {
    "splats": n, "kept": int(keep.sum()),
    "removed": {"outside": int((~inside).sum()), "faint_or_large": int((inside & ~good).sum()),
                "fog": int((inside & good & body & ~near).sum()),
                "floor": int((inside & good & slab).sum()) if a.floor == "drop" else 0},
    "floor_found": bool(floor_ok), "floor_squares": int(best_area), "floor_tilt_deg": round(floor_tilt, 1), "d": round(d, 4),
    "object_cells": lump_cells, "other_solid_cells": other_cells,
    "radius": round(radius, 4), "radius_measured": not a.radius and bool(obj.any()), "height": round(top, 4),
    "camera_ring": {"photos": len(C), "radius": round(float(np.median(cam_r)), 3), "height": round(cam_h, 3),
                    "looked_down_deg": [round(float(pitch.min()), 1), round(float(pitch.max()), 1)],
                    "largest_gap_deg": round(float(gaps.max()), 1)},
    "rotate": ",".join(f"{q:.4f}" for q in rot), "translate": ",".join(f"{q + 0.0:.4f}" for q in t),
    "initialCamera": {"position": [0, round(top / 2 + dist * np.sin(elev), 3), round(dist * np.cos(elev), 3)],
                      "target": [0, round(top / 2, 3), 0], "fov": 60},
}
print(json.dumps(res, indent=1))
if a.json:
    json.dump(res, open(a.json, "w"), indent=1)
hdr = b"".join(header).replace(f"element vertex {n}".encode(), f"element vertex {int(keep.sum())}".encode())
with open(a.out, "wb") as f:
    f.write(hdr); f.write(v[keep].tobytes())
