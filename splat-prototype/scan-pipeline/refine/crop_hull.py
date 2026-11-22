"""Crop a levelled splat to a 3D boundary round the display, following its stepped shape.

   python crop_hull.py <levelled.ply> <out.ply>                       everything worked out from the model
   python crop_hull.py <levelled.ply> <out.ply> [--margin 0.25] [--box x0,y0,z0,x1,y1,z1 ...]
                       [--fringe-box x0,..|none] [--keep-box x0,..] [--band 0.25] [--reach 0.35]
                       [--outline-json outline.json] [--report crop.json]

Works on the .ply that splat-transform writes after levelling (`-r ... -t ...`); the viewer
shows that file rotated 180° about Z, so the viewer's (x, y, z) is (-x, -y, z) of the file.
All numbers here are in the viewer frame (ground y = 0, straight on looks toward -Z).

1. "Solid" splats: opacity over 0.5 and largest axis under 0.05 units. These are surfaces
   the photos saw clearly; floaters and haze are faint or large.
2. Which of them are the display. With no --box: the largest connected lump of 0.1-unit
   cells holding a solid splat (cells touch across a one-cell gap). The display is one
   lump; the hall's walls, ceiling and furniture are other, smaller lumps unless they
   touch it. With --box (repeatable): only those inside one of the boxes, as loose limits
   set by hand (a second box can admit the domes above the canopy without admitting the
   ceiling beside them). Either way, only cells holding at least --min-cell of them shape
   the boundary (drops stray solid splats).
3. The boundary is a stack of footprints. Heights are cut into bands --band units tall;
   each band's footprint is the convex outline, seen from above, of the solid splats within
   --reach of the band's middle height, grown outward by --margin. The display is a
   staircase (low trays at the front, tall canopy at the back), so a single convex hull
   would keep the empty wedges in front of each tier; the stack follows the tiers.
4. A splat is kept if it lies within the footprint of its own band, and between the lowest
   and highest solid splat (plus the margin).
5. The fringe box: outside it (the fringe, where the display's real edges meet haze:
   the dome tips above the canopy, the front edge of the table below its top), a splat is
   kept only if it is no larger than --fringe-scale and lies within --fringe-reach of a
   0.1-unit cell holding at least --min-cell solid splats. Haze between the domes and under
   the table goes; the domes and the table edge stay. With no --box the fringe box is
   measured too: along each axis, the 0.25-unit slices holding at least 2% as many of the
   display's solid splats as the fullest slice (measure_box.py's first guess).
   --fringe-box none turns the rule off. --keep-box names a region the rule must leave
   alone: a real part drawn with thin faint splats, which no measure tells from haze.
"""
import argparse, json
import numpy as np
from scipy import ndimage
from scipy.spatial import ConvexHull

ap = argparse.ArgumentParser()
ap.add_argument("inp"); ap.add_argument("out")
ap.add_argument("--margin", type=float, default=0.25)
ap.add_argument("--box", action="append", default=None,
                help="x0,y0,z0,x1,y1,z1; repeatable (solid splats inside any box count)")
ap.add_argument("--min-cell", type=int, default=3)
ap.add_argument("--band", type=float, default=0.25)
ap.add_argument("--reach", type=float, default=0.35)
ap.add_argument("--outline-json", default="")
ap.add_argument("--report", default="", help="write the printed result, with the boxes used, to this file")
ap.add_argument("--fringe-box", default="", help="x0,y0,z0,x1,y1,z1; outside it only splats next to solid ones stay. "
                "Measured when no --box is given; 'none' turns the rule off")
ap.add_argument("--fringe-reach", type=float, default=0.15)
ap.add_argument("--fringe-scale", type=float, default=0.1)
ap.add_argument("--keep-box", action="append", default=[], help="x0,y0,z0,x1,y1,z1; exempt from the fringe rule")
a = ap.parse_args()

with open(a.inp, "rb") as f:
    header = []
    while True:
        l = f.readline(); header.append(l)
        if l.strip() == b"end_header": break
    props = [h.split()[2].decode() for h in header if h.startswith(b"property")]
    n = int([h for h in header if h.startswith(b"element vertex")][0].split()[2])
    v = np.frombuffer(f.read(n * 4 * len(props)), dtype=[(q, "<f4") for q in props], count=n)
P = np.stack([-v["x"], -v["y"], v["z"]], 1).astype(np.float64)       # viewer frame
op = 1 / (1 + np.exp(-v["opacity"].astype(np.float64)))
smax = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1).astype(np.float64)).max(1)

solid = (op > 0.5) & (smax < 0.05)
auto = {}
if a.box:
    inbox = np.zeros(n, bool)
    for box in a.box:
        b = np.array([float(x) for x in box.split(",")])
        inbox |= np.all((P >= b[:3]) & (P <= b[3:]), 1)
    solid &= inbox
else:
    idx = np.floor(P[solid] / 0.1).astype(np.int64); idx -= idx.min(0) - 2
    grid = np.zeros(idx.max(0) + 3, bool); grid[tuple(idx.T)] = True
    lumps, _ = ndimage.label(ndimage.binary_dilation(grid, iterations=1), structure=np.ones((3, 3, 3)))
    sizes = np.bincount(lumps[grid])
    in_lump = lumps[tuple(idx.T)] == sizes.argmax()
    auto = {"lump_cells": int(sizes.max()), "other_solid_cells": int(sizes.sum() - sizes.max()),
            "solid_outside_lump": int((~in_lump).sum())}
    solid[np.flatnonzero(solid)[~in_lump]] = False
    q = P[solid]
    auto["lump_box"] = ",".join(f"{x:.2f}" for x in np.r_[q.min(0), q.max(0)])
    if not a.fringe_box:                              # measure_box.py's first guess, on the lump
        lo_hi = []
        for i in range(3):
            lo, hi = np.floor(q[:, i].min() / 0.25) * 0.25, np.ceil(q[:, i].max() / 0.25) * 0.25
            counts, edges = np.histogram(q[:, i], bins=int(round((hi - lo) / 0.25)), range=(lo, hi))
            full = np.flatnonzero(counts >= 0.02 * counts.max())
            lo_hi.append((edges[full[0]], edges[full[-1] + 1]))
        a.fringe_box = ",".join(f"{x:g}" for x in [lo_hi[0][0], lo_hi[1][0], lo_hi[2][0], lo_hi[0][1], lo_hi[1][1], lo_hi[2][1]])
        auto["fringe_box"] = a.fringe_box
if a.fringe_box == "none":
    a.fringe_box = ""
cells = np.floor(P[solid] / 0.1).astype(np.int64)
_, inv, counts = np.unique(cells, axis=0, return_inverse=True, return_counts=True)
core = P[solid][counts[inv.ravel()] >= a.min_cell]
y_lo, y_hi = core[:, 1].min() - a.margin, core[:, 1].max() + a.margin

keep = np.zeros(n, bool)
outline = []
band_of = np.floor((P[:, 1] - y_lo) / a.band).astype(int)
for k in range(int(np.ceil((y_hi - y_lo) / a.band))):
    mid = y_lo + (k + 0.5) * a.band
    near = core[np.abs(core[:, 1] - mid) <= a.reach][:, [0, 2]]
    if len(near) < 3:
        continue
    hull = ConvexHull(near)
    eq = hull.equations                       # (nx, nz, offset): inside when n·p + offset <= 0
    sel = band_of == k
    keep[sel] = (P[sel][:, [0, 2]] @ eq[:, :2].T + eq[:, 2] <= a.margin).all(1)
    if a.outline_json:
        # the grown footprint's corners: where neighbouring edges, moved out by the margin, meet
        ring = near[hull.vertices]; m = len(ring); grown = []
        for i in range(m):
            lines = []
            for p0, p1 in ((ring[i - 1], ring[i]), (ring[i], ring[(i + 1) % m])):
                d = (p1 - p0) / np.linalg.norm(p1 - p0); nrm = np.array([d[1], -d[0]])
                if nrm @ (p0 - ring.mean(0)) < 0: nrm = -nrm
                lines.append((nrm, nrm @ p0 + a.margin))
            A = np.array([lines[0][0], lines[1][0]]); c = np.array([lines[0][1], lines[1][1]])
            try: q = np.linalg.solve(A, c)
            except np.linalg.LinAlgError: q = ring[i] + lines[0][0] * a.margin
            grown.append(q.round(3).tolist())
        outline.append({"y0": round(y_lo + k * a.band, 3), "y1": round(y_lo + (k + 1) * a.band, 3), "ring": grown})
keep &= (P[:, 1] >= y_lo) & (P[:, 1] <= y_hi)
fringe_dropped = 0
if a.fringe_box:
    from scipy.spatial import cKDTree
    b = np.array([float(x) for x in a.fringe_box.split(",")])
    fringe = keep & ~np.all((P >= b[:3]) & (P <= b[3:]), 1)
    for box in a.keep_box:
        k = np.array([float(x) for x in box.split(",")])
        fringe &= ~np.all((P >= k[:3]) & (P <= k[3:]), 1)
    cell_ctr = (np.unique(np.floor(core / 0.1).astype(np.int64), axis=0) + 0.5) * 0.1
    d, _ = cKDTree(cell_ctr).query(P[fringe], distance_upper_bound=a.fringe_reach + 0.0866)
    ok = (d <= a.fringe_reach + 0.0866) & (smax[fringe] <= a.fringe_scale)   # 0.0866: half a cell's diagonal
    idx = np.flatnonzero(fringe)
    keep[idx[~ok]] = False
    fringe_dropped = int((~ok).sum())

res = {"splats": n, "solid": int(solid.sum()), "core": len(core), "bands": len(outline) or None,
       "fringe_dropped": fringe_dropped, "kept": int(keep.sum()), "removed": int((~keep).sum()),
       "height": [round(y_lo, 2), round(y_hi, 2)], **auto}
print(json.dumps(res))
if a.report:
    json.dump(res, open(a.report, "w"), indent=1)
if a.outline_json:
    json.dump({"margin": a.margin, "bands": outline}, open(a.outline_json, "w"))
hdr = b"".join(header).replace(f"element vertex {n}".encode(), f"element vertex {int(keep.sum())}".encode())
with open(a.out, "wb") as f:
    f.write(hdr); f.write(v[keep].tobytes())
